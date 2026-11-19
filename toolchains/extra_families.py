#!/usr/bin/env python3
"""Read-only detection and opt-in real builds for extra Python Eye ZIP families.

No source/project code is executed during detection. Running any build is an
explicit trusted-project action. This module does not synthesize empty APKs.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

try:
    import tomllib
except ImportError:
    tomllib = None


def read_small(path: Path, limit: int = 350_000) -> str:
    if not path.is_file() or path.stat().st_size > limit:
        return ""
    return path.read_text("utf-8", errors="replace")


def nested_android(root: Path) -> bool:
    a = root / "android"
    return a.is_dir() and any((a / x).is_file() for x in ("settings.gradle", "settings.gradle.kts"))


def pkg(root: Path) -> dict:
    try:
        raw = read_small(root / "package.json")
        data = json.loads(raw) if raw else {}
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def detect_addon(root: Path) -> dict:
    """Match exact framework clues; do not mistake ordinary npm/Java for an APK."""
    if (root / "buildozer.spec").is_file():
        return {"project_type": "unknown", "reason": "handled by legacy Buildozer route"}
    data = pkg(root)
    dependencies = {}
    for key in ("dependencies", "devDependencies"):
        section = data.get(key)
        if isinstance(section, dict):
            dependencies.update(section)
    briefcase = bool((root / "pyproject.toml").is_file() and
                    re.search(r"(?m)^\[tool\.briefcase(?:\.|\])", read_small(root / "pyproject.toml")))
    flet = bool((root / "pyproject.toml").is_file() and
                re.search(r"(?m)^\[tool\.flet(?:\.|\])", read_small(root / "pyproject.toml")))
    if briefcase:
        kind = "beeware-briefcase"
    elif flet:
        kind = "flet-python"
    elif "@capacitor/core" in dependencies or any((root / x).is_file() for x in ("capacitor.config.ts", "capacitor.config.json", "capacitor.config.js")):
        kind = "capacitor"
    elif (root / "config.xml").is_file() and "<widget" in read_small(root / "config.xml"):
        kind = "cordova"
    elif "expo" in dependencies or (root / "app.json").is_file() and "expo" in read_small(root / "app.json"):
        kind = "expo"
    elif "react-native" in dependencies:
        kind = "react-native"
    elif (root / "pom.xml").is_file():
        kind = "maven-java-library"
    elif (root / "build.xml").is_file():
        kind = "ant-java-library"
    elif (root / "Cargo.toml").is_file():
        kind = "rust-library"
    elif data:
        kind = "node-project"
    else:
        kind = "unknown"
    requires = {
        "beeware-briefcase": ["beeware-briefcase", "jdk-17", "android-sdk-platforms"],
        "flet-python": ["flet-cli", "flutter-dart", "android-sdk-platforms"],
        "capacitor": ["nodejs", "npm", "capacitor-cli", "android-sdk-platforms", "gradle"],
        "cordova": ["nodejs", "npm", "cordova-cli", "android-sdk-platforms", "gradle"],
        "expo": ["nodejs", "npm", "expo-cli", "android-sdk-platforms", "gradle"],
        "react-native": ["nodejs", "npm", "react-native-cli", "android-sdk-platforms", "gradle"],
        "maven-java-library": ["apache-maven"],
        "ant-java-library": ["apache-ant"],
        "rust-library": ["rust-cargo", "android-ndk"],
        "node-project": ["nodejs", "npm"]
    }
    blockers = []
    if kind in ("capacitor", "react-native", "expo") and not nested_android(root):
        blockers.append("Android Gradle project not generated (android/ folder absent); project-specific prebuild required")
    if kind == "cordova" and not (root / "platforms/android").is_dir():
        blockers.append("cordova-android platform missing; explicitly add a compatible version with Cordova first")
    if kind in ("maven-java-library", "ant-java-library", "rust-library", "node-project", "unknown"):
        blockers.append("Not a directly recognized Android APK packaging project")
    return {"project_type": kind,
            "apk_build_supported": kind in ("beeware-briefcase", "flet-python", "capacitor", "cordova", "expo", "react-native") and not blockers,
            "required_tool_ids": requires.get(kind, []),
            "blockers": blockers,
            "host_execution_verified": False, "android_phone_verified": False}


def plugin_features(root: Path) -> list[str]:
    """Detect Android Gradle plugins and native tools without invoking Gradle."""
    files = [
        root / "build.gradle", root / "build.gradle.kts", root / "settings.gradle",
        root / "settings.gradle.kts", root / "gradle/libs.versions.toml",
        *list(root.glob("*/build.gradle*"))[:50]
    ]
    text = "\n".join(read_small(p) for p in files)
    features = []
    tests = {
        "ksp-gradle-plugin": (r"com\.google\.devtools\.ksp", r"(?m)^ksp\s*="),
        "kapt-gradle-plugin": (r"org\.jetbrains\.kotlin\.kapt", r"kotlin-kapt", r"\bkapt\s*\("),
        "compose-compiler-plugin": (r"org\.jetbrains\.kotlin\.plugin\.compose", r"androidx\.compose"),
        "android-aidl": (r"(?m)^\s*aidl\s*\{",),
        "ninja-build": (r"externalNativeBuild", r"CMakeLists\.txt"),
        "llvm-clang": (r"externalNativeBuild", r"ndkVersion"),
    }
    for key, patterns in tests.items():
        if any(re.search(pattern, text) for pattern in patterns):
            features.append(key)
    if list(root.glob("**/*.aidl"))[:1] and "android-aidl" not in features:
        features.append("android-aidl")
    if (root / "Cargo.toml").is_file() and "rust-cargo" not in features:
        features.append("rust-cargo")
    return features


def actual_apks(root: Path, kind: str) -> list[Path]:
    dirs = {
        "capacitor": [root / "android"],
        "react-native": [root / "android"],
        "expo": [root / "android"],
        "cordova": [root / "platforms/android"],
        "flet-python": [root / "build", root / "dist"],
        "beeware-briefcase": [root / "dist", root / "build"],
    }.get(kind, [])
    candidates = []
    for folder in dirs:
        if not folder.exists():
            continue
        for file in folder.rglob("*.apk"):
            # Do not accidentally collect arbitrary archived APK files.
            if any(part in ("node_modules", ".gradle", ".git") for part in file.parts):
                continue
            if file.is_file() and file.stat().st_size > 2000 and zipfile.is_zipfile(file):
                with zipfile.ZipFile(file) as apk:
                    if "AndroidManifest.xml" in apk.namelist() and apk.testzip() is None:
                        candidates.append(file)
    return candidates


def run_build(root: Path, result: dict, output: Path, use_wrapper: bool) -> dict:
    kind = result["project_type"]
    if not result["apk_build_supported"]:
        raise RuntimeError("Project is not APK-ready: " + "; ".join(result["blockers"]))
    if kind in ("beeware-briefcase", "flet-python") and (
        sys.platform not in ("linux", "darwin", "win32") or "ANDROID_ROOT" in os.environ):
        raise RuntimeError("No verified Bionic host for this packaging framework")
    if kind in ("capacitor", "expo", "react-native"):
        build_root = root / "android"
        if use_wrapper:
            wrapper = build_root / ("gradlew.bat" if os.name == "nt" else "gradlew")
            if not wrapper.is_file():
                raise RuntimeError("Android Gradle wrapper not in android/ directory")
            cmd = ["cmd", "/c", str(wrapper), "--no-daemon", "assembleDebug"] if os.name == "nt" else ["sh", str(wrapper), "--no-daemon", "assembleDebug"]
        else:
            gradle = os.environ.get("GRADLE_BIN") or shutil.which("gradle")
            if not gradle:
                raise RuntimeError("Gradle missing; set GRADLE_BIN or explicitly allow the reviewed project wrapper")
            cmd = [gradle, "--no-daemon", "assembleDebug"]
    elif kind == "cordova":
        executable = os.environ.get("CORDOVA_BIN") or shutil.which("cordova")
        if not executable:
            raise RuntimeError("Cordova CLI missing")
        build_root = root
        cmd = [executable, "build", "android", "--debug"]
    elif kind == "flet-python":
        executable = os.environ.get("FLET_BIN") or shutil.which("flet")
        if not executable:
            raise RuntimeError("Flet CLI missing")
        build_root = root
        cmd = [executable, "build", "apk"]
    elif kind == "beeware-briefcase":
        executable = os.environ.get("BRIEFCASE_BIN") or shutil.which("briefcase")
        if not executable:
            raise RuntimeError("Briefcase CLI missing")
        build_root = root
        # Briefcase generates Gradle project before packaging. Noninteractive mode
        # may fail for newly created projects; report rather than fake success.
        cmd = [executable, "package", "android", "-p", "apk", "--no-input"]
    else:
        raise RuntimeError("Unsupported add-on build family")
    run = subprocess.run(cmd, cwd=build_root, check=False, timeout=3600)
    if run.returncode:
        raise RuntimeError(f"Real {kind} build failed (exit {run.returncode})")
    candidates = actual_apks(root, kind)
    if not candidates:
        raise RuntimeError("Command returned zero but no valid Android APK found")
    output.mkdir(parents=True, exist_ok=True)
    result_paths = []
    for n, path in enumerate(candidates[:25]):
        target = output / (path.name if n == 0 else f"{n}-{path.name}")
        shutil.copy2(path, target)
        result_paths.append(str(target.resolve()))
    return {"ok": True, "apk_paths": result_paths, "actual_command": cmd,
            "host_verified": True, "phone_verified": False}


def main() -> None:
    from zip_builder import safe_unpack, find_root
    p = argparse.ArgumentParser(description="Python Eye extra Android ZIP families")
    p.add_argument("action", choices=("inspect", "build"))
    p.add_argument("path", type=Path)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--use-wrapper", action="store_true")
    p.add_argument("--output", type=Path, default=Path("built-apks"))
    args = p.parse_args()
    src = args.path.expanduser().resolve()
    if not src.exists():
        p.error("Project file does not exist")
    with tempfile.TemporaryDirectory(prefix="pyeye-extras-") as temp:
        if src.is_dir():
            root = src
        elif src.is_file() and src.suffix.lower() == ".zip":
            safe_unpack(src, Path(temp))
            root = find_root(Path(temp))
        else:
            p.error("Only directories or .zip project archives")
        result = detect_addon(root)
        result["gradle_features"] = plugin_features(root)
        if args.action == "build":
            if not args.execute:
                p.error("--execute required before running untrusted project code")
            result["build_result"] = run_build(root, result, args.output.resolve(), args.use_wrapper)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
