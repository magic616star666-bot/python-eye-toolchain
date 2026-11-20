#!/usr/bin/env python3
"""Actual on-device Android Gradle APK smoke builder for Python Eye IDE.

A real APK build is the ONLY basis for marking a toolchain project-build
verified. This script deliberately refuses Linux/GitHub CI desktop execution
as evidence of phone readiness. It never runs a project Gradle wrapper and
requires an explicit --approve-build for build-script execution.
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

from mobile_installer import device_host
from android_gradle_versions import jar_for, resolve_java
from versions_manager import InstallError
from zip_builder import safe_unpack, find_root, inspect_project
from plan_project import declared_plugins


def require_android_jdk(java: Path) -> str:
    if not device_host():
        raise InstallError("Actual APK smoke testing is allowed only on real Android ARM64/Bionic device")
    try:
        proc = subprocess.run([str(java), "-version"], text=True, capture_output=True,
                              timeout=30, check=False, errors="replace")
    except (OSError, subprocess.TimeoutExpired) as e:
        raise InstallError(f"Android JDK could not start: {e}") from e
    version = proc.stdout + proc.stderr
    match = re.search(r'(?:openjdk|java) version\s+"?(1\.)?(\d+)', version, re.I)
    if match:
        major = int(match.group(2))
    else:
        match = re.search(r'\bopenjdk\s+(\d+)(?:\.\d+)?', version, re.I)
        major = int(match.group(1)) if match else -1
    if proc.returncode or major < 17:
        raise InstallError(f"Android Gradle smoke needs working JDK 17+ (detected {major}): {version[-300:]}")
    return str(major)


def actual_apks(project: Path) -> list[Path]:
    files = [
        apk for apk in project.glob("*/build/outputs/apk/**/*.apk")
        if apk.is_file() and apk.stat().st_size > 2000
    ]
    verified = []
    for apk in files:
        if not zipfile.is_zipfile(apk):
            continue
        with zipfile.ZipFile(apk) as file:
            members = file.namelist()
            if ("AndroidManifest.xml" in members and
                    any(re.fullmatch(r"classes\d*\.dex", m) for m in members) and
                    file.testzip() is None):
                verified.append(apk)
    return verified


def run_smoke(project: Path, gradle_root: Path, version: str,
              sdk_root: Path, java: Path, aapt2: Path, output: Path,
              *, approve_build: bool, apksigner: Path | None = None) -> dict:
    if not device_host():
        raise InstallError("APK project build must run on actual Android ARM64/Bionic")
    if not approve_build:
        raise InstallError("Gradle project can execute arbitrary code; explicit --approve-build required")
    path = project.expanduser().resolve()
    if not path.is_dir():
        raise InstallError("Pass an Android Gradle project directory (or CLI ZIP handling)")
    project_type = inspect_project(path)["project_type"]
    if project_type not in ("android-gradle", "android-gradle-python"):
        raise InstallError(f"Not a recognized Android Gradle APK project: {project_type}")
    if not sdk_root.is_dir():
        raise InstallError("Android SDK directory missing")
    config = declared_plugins(path)
    compiled_api = config.get("compile_sdk") or 36
    if not (sdk_root / f"platforms/android-{compiled_api}/android.jar").is_file():
        raise InstallError(f"Android SDK platform API {compiled_api} android.jar missing")
    if not aapt2.is_file():
        raise InstallError("Bionic-native aapt2 file not found; never run Linux desktop aapt2 on Android")
    try:
        aapt2_check = subprocess.run([str(aapt2), "version"], text=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     timeout=30, check=False, errors="replace")
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InstallError(f"aapt2 cannot execute on Android device: {exc}") from exc
    if aapt2_check.returncode or "aapt2" not in aapt2_check.stdout.lower():
        raise InstallError("Android-native aapt2 version probe failed")
    jdk_major = require_android_jdk(java)
    jar = jar_for(gradle_root, version)
    output = output.expanduser().resolve()
    if output == path or path in output.parents:
        raise InstallError("APK output folder must be separate from project source")
    gradle_env = dict(os.environ)
    gradle_env["ANDROID_HOME"] = str(sdk_root)
    gradle_env["ANDROID_SDK_ROOT"] = str(sdk_root)
    gradle_env["JAVA_HOME"] = str(java.parent.parent)
    gradle_env.setdefault("GRADLE_USER_HOME", str(gradle_root.parent / ".gradle-user-home"))
    # AGP's AAPT2 from Maven is ordinarily a desktop host binary. Force a known
    # probed Android/Bionic AAPT2. Do not inject flags into project source.
    cmd = [str(java), "-cp", str(jar), "org.gradle.launcher.GradleMain",
           "--no-daemon", "--stacktrace",
           "-Pandroid.aapt2FromMavenOverride=" + str(aapt2),
           "assembleDebug"]
    before = {str(p): p.stat().st_mtime_ns for p in actual_apks(path)}
    try:
        result = subprocess.run(cmd, cwd=path, env=gradle_env, capture_output=True,
                                text=True, errors="replace", check=False, timeout=2400)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InstallError(f"Actual on-device Gradle build did not complete: {exc}") from exc
    if result.returncode:
        raise InstallError(f"Android APK build FAILED (exit {result.returncode}): {(result.stdout + result.stderr)[-2600:]}")
    built = [p for p in actual_apks(path) if str(p) not in before or p.stat().st_mtime_ns != before[str(p)]]
    if not built:
        raise InstallError("Gradle exited zero but did not produce a new valid APK with classes.dex")
    output.mkdir(parents=True, exist_ok=True)
    copies = []
    for i, file in enumerate(built[:20]):
        dest = output / (file.name if i == 0 else f"{i}-{file.name}")
        if dest.exists():
            raise InstallError(f"Would overwrite existing APK: {dest}")
        shutil.copy2(file, dest)
        signed_verified = False
        if apksigner is not None:
            run = subprocess.run([str(apksigner), "verify", "--verbose", str(dest)],
                                 capture_output=True, text=True, errors="replace",
                                 timeout=120, check=False)
            if run.returncode:
                raise InstallError(f"Built APK signature check failed: {(run.stdout + run.stderr)[-500:]}")
            signed_verified = True
        copies.append({"path": str(dest), "size_bytes": dest.stat().st_size,
                       "signature_verification_performed": signed_verified})
    return {"build_completed": True, "host": "actual-android-arm64-bionic",
            "local_device_apk_build_verified": True, "gradle_version": version,
            "java_major": jdk_major, "compile_sdk": compiled_api,
            "aapt2_executable_probed": True, "apks": copies,
            "install_launch_verified": False,
            "disclaimer": "Compilation and APK structural checks only; installing/launching on device needs an independent test."}


def main() -> None:
    p = argparse.ArgumentParser(description="Real Bionic ARM64 Gradle Android APK build smoke")
    p.add_argument("--project", type=Path, required=True)
    p.add_argument("--gradle-version", required=True)
    p.add_argument("--gradle-root", type=Path, default=Path.home() / ".python-eye" / "mobile-tools" / "gradle-versions")
    p.add_argument("--sdk-root", type=Path, required=True)
    p.add_argument("--java", help="Android Bionic JDK executable path; otherwise JAVA_HOME/bin/java")
    p.add_argument("--aapt2", type=Path, required=True, help="Android/Bionic-native aapt2 executable")
    p.add_argument("--apksigner", type=Path, help="Optional existing Android-native apksigner")
    p.add_argument("--output", type=Path, default=Path("android-smoke-apks"))
    p.add_argument("--approve-build", action="store_true")
    args = p.parse_args()
    try:
        path = args.project.expanduser().resolve()
        with tempfile.TemporaryDirectory(prefix="pyeye-apk-smoke-") as temp:
            if path.is_file() and path.suffix.lower() == ".zip":
                safe_unpack(path, Path(temp))
                project = find_root(Path(temp))
            else:
                project = path
            data = run_smoke(project, args.gradle_root.expanduser().resolve() / args.gradle_version,
                             args.gradle_version, args.sdk_root.expanduser().resolve(),
                             resolve_java(args.java), args.aapt2.expanduser().resolve(),
                             args.output, approve_build=args.approve_build,
                             apksigner=args.apksigner)
        print(json.dumps(data, indent=2))
    except (InstallError, ValueError, OSError, zipfile.BadZipFile) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
