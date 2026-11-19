#!/usr/bin/env python3
"""Discover all official SDK versions on a supported host, without installing.

- scans already-installed platforms, Build Tools, NDK, CMake and debugger tools
- optionally queries Google's sdkmanager --list for ACTUALLY available packages
- delegates installation to sdk_installer.py for explicit version selection

Android Bionic support must be supplied by separately verified native ports.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from sdk_installer import desktop_host, get_sdkmanager, parse_package, package_probe


def scan(root: Path) -> list[dict]:
    results: list[dict] = []
    for category, pattern, required in (
        ("android-platform", "platforms/android-*", "android.jar"),
        ("build-tools", "build-tools/*", "source.properties"),
        ("ndk", "ndk/*", "source.properties"),
        ("cmake", "cmake/*", "source.properties"),
        ("platform-tools", "platform-tools", "source.properties"),
        ("cmdline-tools", "cmdline-tools/*", "source.properties"),
    ):
        for candidate in sorted(root.glob(pattern)):
            if not candidate.is_dir() or not (candidate / required).is_file():
                continue
            if category == "android-platform":
                package = f"platforms;{candidate.name}"
            elif category == "platform-tools":
                package = "platform-tools"
            elif category == "cmdline-tools":
                package = f"cmdline-tools;{candidate.name}"
            else:
                package = f"{category};{candidate.name}"
            results.append({"package_id": package, "path": str(candidate),
                            "metadata_present": True, "runnable_on_android_phone": False})
    return results


def sdk_available(manager: str, root: Path) -> list[dict]:
    if not desktop_host():
        raise RuntimeError("Google desktop sdkmanager is not an Android Bionic binary")
    command = [manager, f"--sdk_root={root}", "--list", "--channel=0"]
    result = subprocess.run(command, capture_output=True, text=True,
                            errors="replace", timeout=180, check=False)
    if result.returncode:
        raise RuntimeError(f"sdkmanager --list exited {result.returncode}: {result.stderr[-600:]}")
    entries = []
    seen = set()
    for line in result.stdout.splitlines():
        if "|" not in line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 2:
            continue
        name = parts[0]
        if not re.fullmatch(r"(?:platforms;android-\d{2,3}|build-tools;\d+\.\d+\.\d+|ndk;\d+(?:\.\d+){2,3}|cmake;\d+(?:\.\d+){2,3}|platform-tools|cmdline-tools;(?:latest|\d+(?:\.\d+){1,3}))", name):
            continue
        if name in seen:
            continue
        seen.add(name)
        entries.append({"package_id": name, "version": parts[1],
                        "description": parts[2][:130] if len(parts) > 2 else ""})
    return entries


def main() -> None:
    p = argparse.ArgumentParser(description="List installed and available Android SDK versions")
    p.add_argument("action", choices=("installed", "available"))
    p.add_argument("--sdk-root", type=Path, default=Path(os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or "./android-sdk"))
    args = p.parse_args()
    root = args.sdk_root.expanduser().resolve()
    try:
        installed = scan(root)
        result = {"sdk_root": str(root), "host_supported_for_desktop_install": desktop_host(),
                  "android_phone_build_verified": False,
                  "installed_metadata_packages": installed}
        if args.action == "available":
            manager = get_sdkmanager(root)
            result["official_available_packages"] = sdk_available(manager, root)
            result["note"] = "Available is sourced from live Google sdkmanager, not pre-downloaded or phone-tested binaries."
        else:
            result["note"] = "Installed metadata does not prove executables work; run probe_tools.py."
        print(json.dumps(result, indent=2))
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as err:
        print(json.dumps({"ok": False, "error": str(err)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
