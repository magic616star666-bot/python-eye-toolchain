#!/usr/bin/env python3
"""Android/Bionic-side official Gradle version installer via installed Android JDK.

Gradle is a Java distribution, not a Linux native executable. This downloads
only official distributions with SHA-256 from services.gradle.org, stores
side-by-side versions, then calls GradleMain directly using the selected
Android/Bionic java binary. It NEVER calls a Linux x86_64 Gradle launcher.
Successful Gradle --version is NOT an Android APK build.
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

from mobile_installer import device_host
from versions_manager import download_verified, https_get, safe_unpack, InstallError

BASE = "https://services.gradle.org/distributions"
MAX_BYTES = 600_000_000
VERSION = re.compile(r"^[0-9]+(?:\.[0-9]+){1,3}$")


def gradle_metadata(version: str) -> dict:
    if not VERSION.fullmatch(version):
        raise InstallError("Version must be an exact numeric Gradle release")
    filename = f"gradle-{version}-bin.zip"
    digest = https_get(f"{BASE}/{filename}.sha256", max_size=200).decode("ascii", "strict").strip().split()[0].lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise InstallError("Official Gradle distribution SHA-256 missing or invalid")
    return {"id": "gradle", "version": version, "download_url": f"{BASE}/{filename}",
            "sha256": digest, "asset_name": filename,
            "android_phone_apk_build_verified": False}


def resolve_java(explicit: str | None) -> Path:
    if explicit:
        java = Path(explicit).expanduser().resolve()
    elif os.environ.get("JAVA_HOME"):
        java = (Path(os.environ["JAVA_HOME"]) / "bin/java").resolve()
    else:
        location = shutil.which("java")
        java = Path(location).resolve() if location else Path("/nonexistent")
    if not java.is_file():
        raise InstallError("Android/Bionic Java binary is missing; install and probe JDK 17 first")
    return java


def jar_for(root: Path, version: str) -> Path:
    location = root / f"gradle-{version}" / "lib" / f"gradle-launcher-{version}.jar"
    if not location.is_file() or location.stat().st_size < 1024:
        raise InstallError("Official Gradle launcher JAR missing from archive")
    return location


def run_launcher(java: Path, root: Path, version: str) -> dict:
    if not device_host():
        raise InstallError("Android Gradle execution must run on Android ARM64/Bionic")
    launcher = jar_for(root, version)
    env = dict(os.environ)
    # Startup uses the installed Bionic JDK and pure-Java launcher, not Linux scripts.
    try:
        done = subprocess.run([str(java), "-cp", str(launcher),
                               "org.gradle.launcher.GradleMain", "--version"],
                              cwd=root, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              errors="replace", check=False, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InstallError(f"Gradle launcher process failure: {exc}") from exc
    if done.returncode or f"Gradle {version}" not in done.stdout:
        raise InstallError(f"Gradle {version} did not start in Android JVM: {done.stdout[-700:]}")
    return {"local_android_jvm_version_probe_passed": True,
            "gradle_version": version, "android_apk_build_verified": False,
            "output_excerpt": done.stdout[-700:]}


def install(version: str, root: Path, java: Path, *, approve: bool, execute_probe: bool) -> dict:
    if not device_host():
        raise InstallError("This Gradle version installer is Android ARM64/Bionic only")
    if not approve:
        raise InstallError("Explicit --approve-download required")
    metadata = gradle_metadata(version)
    path = root / version
    if path.exists():
        raise InstallError("Version already installed; use status or probe; no silent overwrite")
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gradle-bionic-", dir=root) as temp:
        folder = Path(temp)
        archive = folder / metadata["asset_name"]
        download_verified(metadata, archive, MAX_BYTES)
        extracted = folder / "unpacked"
        extracted.mkdir()
        safe_unpack(archive, extracted, limit=1_200_000_000)
        jar_for(extracted, version)
        extracted.rename(path)
    observed = {"id": "gradle", "version": version, "installed_archive": True,
                "sha256": metadata["sha256"], "android_apk_build_verified": False,
                "local_android_jvm_version_probe_passed": False}
    if execute_probe:
        try:
            observed.update(run_launcher(java, path, version))
        except InstallError as exc:
            observed["probe_error"] = str(exc)
    (path / ".python-eye-gradle.json").write_text(json.dumps(observed, indent=2) + "\n")
    return observed


def status(version: str, root: Path, java: Path | None = None, execute_probe: bool = False) -> dict:
    if not VERSION.fullmatch(version):
        raise InstallError("Invalid Gradle version")
    path = root / version
    state = path / ".python-eye-gradle.json"
    if not state.is_file():
        return {"id": "gradle", "version": version, "installed": False,
                "local_android_jvm_version_probe_passed": False,
                "android_apk_build_verified": False}
    data = json.loads(state.read_text("utf-8"))
    if data.get("version") != version or data.get("id") != "gradle":
        raise InstallError("Stored Gradle manifest mismatch")
    data["android_apk_build_verified"] = False
    data["ready_without_current_probe"] = False
    if execute_probe:
        if java is None:
            raise InstallError("Android JDK required")
        data.update(run_launcher(java, path, version))
        state.write_text(json.dumps(data, indent=2) + "\n")
    return data


def main() -> None:
    p = argparse.ArgumentParser(description="Android/Bionic Java-only official Gradle version installer")
    p.add_argument("action", choices=("list", "resolve", "install", "status", "probe"))
    p.add_argument("--version", help="Exact released Gradle version, e.g. 8.14.3")
    p.add_argument("--java", help="Executable path to Android/Bionic java binary")
    p.add_argument("--root", type=Path, default=Path.home() / ".python-eye" / "android-gradle")
    p.add_argument("--approve-download", action="store_true")
    p.add_argument("--execute-probe", action="store_true")
    args = p.parse_args()
    try:
        if args.action == "list":
            data = {"source": BASE,
                    "versions": "Any official numbered Gradle distribution with official SHA256",
                    "requires": "Android Bionic Java 17+ (version compatibility is per Gradle release)",
                    "device_apk_build_verified": False}
        elif not args.version:
            raise InstallError("--version required")
        elif args.action == "resolve":
            data = {**gradle_metadata(args.version), "downloaded": False}
        else:
            root = args.root.expanduser().resolve()
            if args.action == "install":
                java = resolve_java(args.java)
                data = install(args.version, root, java, approve=args.approve_download,
                               execute_probe=args.execute_probe)
            else:
                java = resolve_java(args.java) if args.action == "probe" else None
                data = status(args.version, root, java=java, execute_probe=args.action == "probe")
        print(json.dumps(data, indent=2))
    except (InstallError, OSError, ValueError) as err:
        print(json.dumps({"ok": False, "error": str(err)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
