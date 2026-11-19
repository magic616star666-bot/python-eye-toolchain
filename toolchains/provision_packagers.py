#!/usr/bin/env python3
"""Install REAL Buildozer + python-for-android CLI into a dedicated venv.

This installs packages from PyPI only after --approve-install. It is for
compatible Linux/macOS build hosts, not an Android/Bionic phone host.
Installation is not proof that an arbitrary Python project can build an APK.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

BUILD_PACKAGES = ["buildozer==1.6.0", "python-for-android==2026.5.9"]


def supported() -> bool:
    return (sys.platform in ("linux", "darwin") and
            not (os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA")))


def venv_python(prefix: Path) -> Path:
    return prefix / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def command_check(python: Path) -> dict:
    if not python.is_file():
        return {"ready": False, "detail": "isolated environment missing"}
    code = ("import importlib.metadata as m; import buildozer, pythonforandroid; "
            "print('buildozer='+m.version('buildozer'));"
            "print('python-for-android='+m.version('python-for-android'))")
    try:
        result = subprocess.run([str(python), "-c", code], capture_output=True,
                                text=True, timeout=30, check=False)
        ready = (result.returncode == 0 and
                 "buildozer=1.6.0" in result.stdout and
                 "python-for-android=2026.5.9" in result.stdout)
        return {"ready": ready, "detail": (result.stdout + result.stderr)[-1500:].strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"ready": False, "detail": str(error)}


def main() -> None:
    p = argparse.ArgumentParser(description="Provision isolated Python Android packaging CLIs")
    p.add_argument("action", choices=("status", "install"))
    p.add_argument("--prefix", type=Path, required=True, help="Target directory for isolated venv, not the IDE's Python itself")
    p.add_argument("--approve-install", action="store_true", help="Approve internet downloads and PyPI package installation")
    args = p.parse_args()
    target = args.prefix.expanduser().resolve()
    python = venv_python(target)
    try:
        if args.action == "install":
            if not supported():
                raise RuntimeError("Buildozer/python-for-android host install is only supported on compatible Linux/macOS; not an Android/Bionic host")
            if not args.approve_install:
                raise RuntimeError("Explicit --approve-install required before installing third-party packages")
            if target.exists() and not python.is_file():
                raise RuntimeError("Refusing to overwrite unrelated existing directory")
            if not python.is_file():
                subprocess.run([sys.executable, "-m", "venv", str(target)], check=True)
            subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check",
                            "--no-input", *BUILD_PACKAGES], check=True, timeout=900)
            subprocess.run([str(python), "-m", "pip", "check"], check=True, timeout=30)
        observed = command_check(python)
        print(json.dumps({"ok": observed["ready"],
                          "venv": str(target), "host_supported": supported(),
                          "packages": BUILD_PACKAGES,
                          "readiness": "local_cli_import_passed" if observed["ready"] else "not_ready",
                          "apk_build_verified": False, "android_phone_verified": False,
                          "detail": observed["detail"]}, indent=2))
        if args.action == "install" and not observed["ready"]:
            raise RuntimeError("Package import/version checks did not pass")
    except (RuntimeError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
