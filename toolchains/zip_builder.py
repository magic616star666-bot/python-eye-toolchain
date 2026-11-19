#!/usr/bin/env python3
"""Inspect ZIP projects and optionally build supported Android APK types.

No project code is executed by 'inspect'. A build ALWAYS requires --execute.
Uses only the Python standard library; no fake APK output is generated.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

MAX_FILES = 12000
MAX_UNCOMPRESSED = 2_000_000_000
MAX_MEMBER = 500_000_000
MAX_NAME_LENGTH = 500


class BuildError(Exception):
    pass


def safe_unpack(archive: Path, destination: Path) -> None:
    """Protect against traversal, symlinks, duplicated entries, and ZIP bombs."""
    with zipfile.ZipFile(archive) as zf:
        items = zf.infolist()
        if len(items) > MAX_FILES:
            raise BuildError("ZIP contains too many entries")
        total = 0
        used = set()
        for entry in items:
            name = entry.filename.replace("\\", "/")
            path = PurePosixPath(name)
            if (not name or len(name) > MAX_NAME_LENGTH or name.startswith("/")
                    or re.match(r"^[A-Za-z]:", name)
                    or any(part in ("..", "") for part in path.parts)):
                raise BuildError(f"Unsafe ZIP member path: {name!r}")
            normalized = str(path).rstrip("/")
            if normalized in used:
                raise BuildError(f"Duplicate ZIP member: {normalized}")
            used.add(normalized)
            mode = entry.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise BuildError(f"ZIP links and special files are forbidden: {name}")
            if entry.file_size > MAX_MEMBER:
                raise BuildError(f"Oversize ZIP member: {name}")
            total += entry.file_size
            if total > MAX_UNCOMPRESSED:
                raise BuildError("ZIP exceeds uncompressed size limit")
        for entry in items:
            target = destination.joinpath(*PurePosixPath(entry.filename.replace("\\", "/")).parts)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(entry) as source, target.open("xb") as output:
                remaining = entry.file_size
                while True:
                    chunk = source.read(min(1024 * 1024, remaining + 1))
                    if not chunk:
                        break
                    if len(chunk) > remaining:
                        raise BuildError("ZIP decompressed size changed unexpectedly")
                    output.write(chunk)
                    remaining -= len(chunk)
                if remaining:
                    raise BuildError("Incomplete ZIP member")


def find_root(directory: Path) -> Path:
    root = directory
    for _ in range(5):
        children = [p for p in root.iterdir() if p.name not in ("__MACOSX", ".DS_Store")]
        if len(children) == 1 and children[0].is_dir():
            root = children[0]
        else:
            break
    return root


def android_app_plugin(root: Path) -> bool:
    candidates = [root / "build.gradle", root / "build.gradle.kts",
                  root / "app/build.gradle", root / "app/build.gradle.kts"]
    # Allow common multi-module projects, but only inspect small Gradle text files.
    candidates.extend(p for p in root.glob("*/build.gradle*") if p.is_file())
    for file in candidates[:100]:
        if not file.is_file() or file.stat().st_size > 1_000_000:
            continue
        contents = file.read_text(encoding="utf-8", errors="replace")
        if "com.android.application" in contents:
            return True
    return False


def inspect_project(root: Path) -> dict:
    root = find_root(root)
    buildozer = (root / "buildozer.spec").is_file()
    pubspec = root / "pubspec.yaml"
    flutter = pubspec.is_file() and re.search(r"(?m)^flutter\s*:", pubspec.read_text("utf-8", errors="replace")[:100_000]) is not None
    gradle = any((root / x).exists() for x in ("settings.gradle", "settings.gradle.kts", "build.gradle", "build.gradle.kts"))
    android = gradle and android_app_plugin(root)
    if flutter:
        project_type = "flutter"
    elif android:
        has_python = (root / "app/src/main/python").is_dir() or any(
            p.is_file() and "com.chaquo.python" in p.read_text("utf-8", errors="replace")[:1_000_000]
            for p in (root / "build.gradle", root / "build.gradle.kts", root / "app/build.gradle", root / "app/build.gradle.kts") if p.is_file()
        )
        project_type = "android-gradle-python" if has_python else "android-gradle"
    elif buildozer:
        project_type = "buildozer-python"
    elif gradle:
        project_type = "non-android-gradle"
    elif any((root / x).is_file() for x in ("main.py", "app.py", "pyproject.toml", "requirements.txt")):
        project_type = "plain-python"
    else:
        project_type = "unknown"

    # Buildozer is a supported Linux/macOS route, not an Android/Bionic host tool.
    support = {
        "flutter": ("flutter build apk --debug", "Flutter SDK and Android SDK"),
        "android-gradle": ("gradle --no-daemon assembleDebug", "Android SDK, compatible Gradle, JDK and AGP"),
        "android-gradle-python": ("gradle --no-daemon assembleDebug", "Android SDK, compatible Gradle/JDK/AGP and Chaquopy"),
        "buildozer-python": ("buildozer android debug", "Buildozer, python-for-android, Linux/macOS, NDK, SDK"),
    }
    command, needs = support.get(project_type, (None, "Android app source project or Android packaging definition"))
    return {
        "project_type": project_type,
        "apk_build_supported": command is not None,
        "planned_command": command,
        "required_toolchains": needs,
        "host_execution_verified": False,
        "note": ("Executable Gradle/Flutter/Buildozer builds require an explicit trusted-project "
                 "--execute flag; results depend on actual host toolchain availability.")
                if command else "No Android packaging definition detected; cannot convert arbitrary code to APK.",
    }


def run_build(root: Path, result: dict, *, use_wrapper: bool, output_dir: Path) -> dict:
    kind = result["project_type"]
    if not result["apk_build_supported"]:
        raise BuildError("This project has no recognized APK build route")
    if kind == "buildozer-python" and (sys.platform not in ("linux", "darwin")
                                       or "ANDROID_ROOT" in os.environ):
        raise BuildError("Buildozer packaging requires supported Linux/macOS host; not Android Bionic")
    if kind == "flutter":
        executable = os.environ.get("FLUTTER_BIN") or shutil.which("flutter")
        if not executable:
            raise BuildError("Flutter SDK executable not found")
        cmd = [executable, "build", "apk", "--debug"]
    elif kind == "buildozer-python":
        executable = os.environ.get("BUILDOZER_BIN") or shutil.which("buildozer")
        if not executable:
            raise BuildError("Buildozer executable not found")
        cmd = [executable, "android", "debug"]
    else:
        if use_wrapper:
            wrapper = root / "gradlew"
            if not wrapper.is_file():
                raise BuildError("Gradle wrapper missing; omit --use-wrapper to select installed Gradle")
            if sys.platform == "win32":
                bat = root / "gradlew.bat"
                if not bat.is_file():
                    raise BuildError("Windows Gradle wrapper missing")
                cmd = ["cmd", "/c", str(bat), "--no-daemon", "assembleDebug"]
            else:
                cmd = ["sh", str(wrapper), "--no-daemon", "assembleDebug"]
        else:
            executable = os.environ.get("GRADLE_BIN") or shutil.which("gradle")
            if not executable:
                raise BuildError("Gradle not found; set GRADLE_BIN or explicitly use --use-wrapper")
            cmd = [executable, "--no-daemon", "assembleDebug"]
    proc = subprocess.run(cmd, cwd=root, check=False)
    if proc.returncode:
        raise BuildError(f"Real build failed with exit code {proc.returncode}")
    output_dir.mkdir(parents=True, exist_ok=True)
    if kind == "flutter":
        candidates = list((root / "build/app/outputs/flutter-apk").glob("*.apk"))
    elif kind == "buildozer-python":
        candidates = list((root / "bin").glob("*.apk"))
    else:
        candidates = list(root.glob("*/build/outputs/apk/**/*.apk")) + list(root.glob("build/outputs/apk/**/*.apk"))
    found = []
    for apk in candidates[:30]:
        if apk.is_file() and apk.stat().st_size > 0:
            target = output_dir / apk.name
            if target.exists():
                target = output_dir / (apk.parent.name + "-" + apk.name)
            shutil.copy2(apk, target)
            found.append(str(target.resolve()))
    if not found:
        raise BuildError("Build exited 0 but no nonempty APK was found; no fake success reported")
    return {"ok": True, "actual_apk_files": found, "command": cmd}


def inspect_or_build(args) -> dict:
    target = args.path.expanduser().resolve()
    if not target.exists():
        raise BuildError(f"Project not found: {target}")
    if not target.is_file() and not target.is_dir():
        raise BuildError("Input must be a ZIP file or project directory")
    if target.is_file() and target.suffix.lower() != ".zip":
        raise BuildError("Only .zip project archives are accepted")
    with tempfile.TemporaryDirectory(prefix="python-eye-project-") as td:
        if target.is_dir():
            root = target
        else:
            safe_unpack(target, Path(td))
            root = find_root(Path(td))
        result = inspect_project(root)
        result["source"] = str(target)
        if args.action == "build":
            if not args.execute:
                raise BuildError("Build blocked: add --execute only after you trust/review project code")
            output = args.output.expanduser().resolve()
            # Never choose an output inside a temporary extracted project.
            result["build_result"] = run_build(root, result, use_wrapper=args.use_wrapper, output_dir=output)
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Python Eye IDE safe ZIP project detector / real APK build CLI")
    sub = parser.add_subparsers(dest="action", required=True)
    inspect_p = sub.add_parser("inspect", help="Read ZIP/project structure without executing project code")
    inspect_p.add_argument("path", type=Path)
    build_p = sub.add_parser("build", help="Execute an Android APK build only with explicit consent")
    build_p.add_argument("path", type=Path)
    build_p.add_argument("--execute", action="store_true", help="Explicit approval to run untrusted project build scripts")
    build_p.add_argument("--use-wrapper", action="store_true", help="Opt in to running the project's Gradle wrapper")
    build_p.add_argument("--output", type=Path, default=Path("built-apks"))
    args = parser.parse_args()
    try:
        result = inspect_or_build(args)
        print(json.dumps(result, indent=2))
    except (BuildError, zipfile.BadZipFile, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
