#!/usr/bin/env python3
"""Opt-in isolated install and live CLI verification for JS/Python APK builders.

Does not install Android SDK/NDK, run project scripts, create signing keys,
contact Expo EAS cloud, or pretend Android phone compatibility. npm installs
use --ignore-scripts by default; some upstream packages may fail verification.
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

PACKAGES = {
    "capacitor-cli": ("npm", "@capacitor/cli", "cap"),
    "cordova-cli": ("npm", "cordova", "cordova"),
    "eas-cli": ("npm", "eas-cli", "eas"),
    "expo-cli": ("npm", "expo", "expo"),
    "react-native-cli": ("npm", "@react-native-community/cli", "rnc-cli"),
    "beeware-briefcase": ("pip", "briefcase", "briefcase"),
    "flet-cli": ("pip", "flet", "flet"),
}
VERSION = re.compile(r"^\d+(?:\.\d+){1,3}(?:[a-zA-Z0-9._-]*)?$")
ANDROID = lambda: bool(os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA")
                       or sys.platform == "android")


def cmd_version(command: list[str]) -> dict:
    try:
        done = subprocess.run(command + ["--version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=45, check=False, errors="replace")
        output = done.stdout.strip()[-1000:]
        return {"ok": done.returncode == 0 and bool(output),
                "exit_code": done.returncode, "output": output}
    except (OSError, subprocess.TimeoutExpired) as err:
        return {"ok": False, "error": str(err)}


def bin_path(root: Path, kind: str, executable: str) -> Path:
    suffix = ".cmd" if os.name == "nt" and kind == "npm" else ".exe" if os.name == "nt" else ""
    return root / ("node_modules/.bin" if kind == "npm" else "venv/Scripts" if os.name == "nt" else "venv/bin") / (executable + suffix)


def status(target: Path, item: str, version: str) -> dict:
    kind, package, executable = PACKAGES[item]
    binfile = bin_path(target, kind, executable)
    if not binfile.is_file():
        return {"id": item, "version": version, "ready": False,
                "status": "not_installed_or_missing_cli"}
    manifest = target / ".python-eye-addon.json"
    if not manifest.is_file():
        return {"id": item, "version": version, "ready": False,
                "status": "installation_not_verified"}
    record = json.loads(manifest.read_text("utf-8"))
    if record.get("id") != item or record.get("version") != version or record.get("kind") != kind:
        raise ValueError("Installed tool manifest mismatch")
    probe = cmd_version([str(binfile)])
    return {"id": item, "version": version, "ready": probe["ok"],
            "probe": probe, "status": "host_cli_verified" if probe["ok"] else "probe_failed",
            "host": platform.platform(), "android_phone_verified": False,
            "apk_build_verified": False}


def install(target: Path, item: str, version: str, approve: bool) -> dict:
    if ANDROID():
        raise RuntimeError("Only desktop-host CLI installation tested. Android Bionic requires separate validation.")
    if not approve:
        raise RuntimeError("Explicit --approve-install required")
    if not VERSION.fullmatch(version):
        raise ValueError("Version must be an explicit numeric release, not latest or an npm/git spec")
    kind, package, executable = PACKAGES[item]
    manifest = target / ".python-eye-addon.json"
    if manifest.exists():
        return status(target, item, version)
    if target.exists() and list(target.iterdir()):
        raise RuntimeError("Target folder already contains data. Never overwrite automatically.")
    target.mkdir(parents=True, exist_ok=True)
    if kind == "npm":
        npm = shutil.which("npm")
        if not npm:
            raise RuntimeError("Node/npm not found")
        command = [npm, "install", "--prefix", str(target), "--no-save", "--ignore-scripts",
                   "--no-audit", "--no-fund", "--package-lock=false", f"{package}@{version}"]
    else:
        venv = target / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, timeout=180)
        interpreter = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        command = [str(interpreter), "-m", "pip", "install", "--disable-pip-version-check",
                   "--no-input", f"{package}=={version}"]
    subprocess.run(command, check=True, timeout=1200)
    actual = bin_path(target, kind, executable)
    result = cmd_version([str(actual)]) if actual.is_file() else {"ok": False, "error": "CLI executable missing"}
    if not result["ok"]:
        raise RuntimeError(f"Package downloaded but real CLI probe failed: {result}")
    manifest.write_text(json.dumps({"id": item, "version": version, "kind": kind,
                                    "package": package, "host_cli_verified": True,
                                    "android_phone_verified": False, "apk_build_verified": False},
                                   indent=2) + "\n", "utf-8")
    return status(target, item, version)


def main() -> None:
    p = argparse.ArgumentParser(description="Add-on Android build CLI installer, isolated and explicit")
    p.add_argument("action", choices=("list", "status", "install"))
    p.add_argument("--id", choices=sorted(PACKAGES))
    p.add_argument("--version", help="Exact numeric package release version")
    p.add_argument("--prefix", type=Path, default=Path.home() / ".python-eye" / "addons")
    p.add_argument("--approve-install", action="store_true")
    args = p.parse_args()
    try:
        if args.action == "list":
            print(json.dumps({"available": PACKAGES, "android_phone_verified": False,
                              "install_requires_explicit_version": True}, indent=2))
            return
        if not args.id or not args.version or not VERSION.fullmatch(args.version):
            p.error("--id and explicit numeric --version are required")
        target = (args.prefix.expanduser().resolve() / args.id / args.version)
        if args.action == "install":
            outcome = install(target, args.id, args.version, args.approve_install)
        else:
            outcome = status(target, args.id, args.version)
        print(json.dumps(outcome, indent=2))
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
