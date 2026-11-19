#!/usr/bin/env python3
"""Official Android SDK Manager adapter for Python Eye external tool routes.

This is a real SDK installer for supported DESKTOP build hosts. Standard Google
Linux SDK host binaries are NOT Android ARM64/Bionic executables.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys


class ToolError(Exception):
    pass


def desktop_host() -> bool:
    if os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA"):
        return False
    architecture = platform.machine().lower()
    return ((sys.platform == "linux" and architecture in ("x86_64", "amd64"))
            or (sys.platform == "darwin" and architecture in
                ("x86_64", "arm64", "aarch64")))


def parse_package(name: str) -> str:
    """Reject arbitrary sdkmanager switches, shell syntax and unknown paths."""
    if name in ("platform-tools", "cmdline-tools;latest"):
        return name
    checks = (
        r"platforms;android-(?:2[1-9]|3[0-6])",
        r"build-tools;[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}",
        r"ndk;[0-9]+(?:\.[0-9]+){2,3}",
        r"cmake;[0-9]+(?:\.[0-9]+){2,3}",
    )
    if any(re.fullmatch(pattern, name) for pattern in checks):
        return name
    raise ToolError(f"Unsupported SDK package ID: {name!r}")


def package_probe(root: Path, name: str) -> Path:
    if name.startswith("platforms;android-"):
        return root / "platforms" / name.split(";", 1)[1] / "android.jar"
    if name.startswith("build-tools;"):
        return root / "build-tools" / name.split(";", 1)[1] / "source.properties"
    if name.startswith("ndk;"):
        return root / "ndk" / name.split(";", 1)[1] / "source.properties"
    if name.startswith("cmake;"):
        return root / "cmake" / name.split(";", 1)[1] / "source.properties"
    if name == "platform-tools":
        return root / "platform-tools" / "source.properties"
    if name == "cmdline-tools;latest":
        return root / "cmdline-tools" / "latest" / "source.properties"
    raise ToolError(f"No check known for package {name}")


def get_sdkmanager(root: Path) -> str:
    env = os.environ.get("SDKMANAGER_BIN")
    paths = [Path(env)] if env else []
    paths += [root / "cmdline-tools" / "latest" / "bin" / "sdkmanager",
              root / "cmdline-tools" / "bin" / "sdkmanager"]
    for path in paths:
        if path.is_file():
            return str(path)
    found = shutil.which("sdkmanager")
    if found:
        return found
    raise ToolError("sdkmanager missing. Install official Android Command-line Tools first.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Official Google Android SDK manager adapter (desktop build hosts)")
    parser.add_argument("action", choices=("status", "install"))
    parser.add_argument("--sdk-root", type=Path, default=Path(os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or ""))
    parser.add_argument("--package", dest="packages", action="append", default=[],
                        help="Repeat: --package 'platforms;android-36', --package 'ndk;27.0.12077973'")
    parser.add_argument("--accept-sdk-license", action="store_true",
                        help="Affirms that user has already reviewed and explicitly accepted Google SDK license terms")
    args = parser.parse_args()
    try:
        if not args.packages:
            raise ToolError("At least one --package is required; no bulk/install-everything mode")
        packages = [parse_package(item) for item in args.packages]
        root = args.sdk_root.expanduser().resolve()
        if str(args.sdk_root) in ("", ".") and not (os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")):
            raise ToolError("Provide --sdk-root or set ANDROID_HOME")
        if args.action == "install":
            if not desktop_host():
                raise ToolError("Official desktop SDK host binaries cannot run directly in Android ARM64/Bionic; use a verified Android-native port or Linux CI.")
            if not args.accept_sdk_license:
                raise ToolError("SDK license not accepted. Review Google's SDK terms, then explicitly pass --accept-sdk-license")
            sdkmanager = get_sdkmanager(root)
            root.mkdir(parents=True, exist_ok=True)
            # Explicit approval: this acknowledges Google SDK terms, not any unrelated third-party license.
            command = [sdkmanager, f"--sdk_root={root}"] + packages
            subprocess.run(command, check=True)
        items = [{"id": name, "path": str(package_probe(root, name)),
                  "files_present": package_probe(root, name).is_file(),
                  "tested_on_user_phone": False} for name in packages]
        print(json.dumps({"ok": True, "sdk_root": str(root),
                          "host_supported_for_install": desktop_host(),
                          "result": items,
                          "all_files_present": all(i["files_present"] for i in items),
                          "device_build_verified": False}, indent=2))
        if args.action == "install" and not all(item["files_present"] for item in items):
            raise ToolError("sdkmanager exited successfully but required files were not found")
    except (ToolError, subprocess.CalledProcessError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
