#!/usr/bin/env python3
"""Verified Android/Bionic ARM64 upstream archive installer for Python Eye.

This is a standalone CLI, NOT yet wired into the Android Kotlin Extensions UI.
SHA-256 and file size are checked against pinned GitHub Release metadata.
The installer never labels a tool APK-build-ready on download or extraction.
Binary execution needs a separate --execute-probe opt-in and a real phone host.
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
import tempfile

from versions_manager import safe_unpack, download_verified, InstallError

INDEX = Path(__file__).with_name("mobile-artifacts.json")
MAX_COMPRESSED = 1_400_000_000


def device_host() -> bool:
    return bool(os.environ.get("ANDROID_ROOT") or sys.platform == "android"
                or hasattr(sys, "getandroidapilevel")) and platform.machine().lower() in ("aarch64", "arm64")


def load_index() -> dict:
    catalog = json.loads(INDEX.read_text("utf-8"))
    if catalog["schema_version"] != 1 or catalog["host_abi"] != "arm64-v8a":
        raise InstallError("Unsupported Android native catalog schema")
    found = set()
    for item in catalog["assets"]:
        if item["id"] in found:
            raise InstallError("Duplicate mobile tool IDs")
        found.add(item["id"])
        if item["installed"] or item["local_device_probe_passed"] or item["android_apk_build_verified"]:
            raise InstallError(f"Untrusted ready status in static catalog: {item['id']}")
        if not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise InstallError("Missing SHA-256 in pinned upstream release")
        if (not item["url"].startswith("https://github.com/") or
                not item["file_size_bytes"] or item["file_size_bytes"] > MAX_COMPRESSED):
            raise InstallError("Invalid upstream download metadata")
        if item["provider"] not in item["url"] or "/releases/download/" not in item["url"]:
            raise InstallError("Upstream provider mismatch")
        if not item["asset_name"].endswith((".tar.gz", ".tar.xz", ".zip")):
            raise InstallError("Unsupported artifact format")
    return catalog


def locate_binary(root: Path, executable: str) -> Path:
    candidates = [p for p in root.rglob(executable) if p.is_file()
                  and p.parent.name == "bin"]
    if not candidates:
        candidates = [p for p in root.rglob(executable) if p.is_file()]
    if not candidates:
        raise InstallError(f"Required executable {executable} not found")
    candidates.sort(key=lambda p: (len(p.parts), str(p)))
    return candidates[0]


def command(argv: list[str], *, stdin: str | None = None,
            code_must_be_zero: bool = True, expected: str = "") -> str:
    try:
        p = subprocess.run(argv, input=stdin, capture_output=True, text=True,
                           timeout=50, check=False, errors="replace")
    except (OSError, subprocess.TimeoutExpired) as e:
        raise InstallError(f"Native process failed: {e}") from e
    output = (p.stdout + "\n" + p.stderr)[-1500:]
    if (code_must_be_zero and p.returncode != 0) or (expected and expected.lower() not in output.lower()):
        raise InstallError(f"Native binary did not pass: {Path(argv[0]).name} exit={p.returncode}: {output[:450]}")
    return output


def run_probe(path: Path, item: dict) -> dict:
    if not device_host():
        raise InstallError("Native executable verification must be performed on Android ARM64/Bionic itself")
    family = item["family"]
    verified = []
    if family == "jdk":
        java = locate_binary(path, "java")
        javac = locate_binary(path, "javac")
        version = command([str(java), "-version"])
        major = re.search(r'(?:openjdk|java) version\s+"?(1\.)?(\d+)', version, re.I)
        if not major:
            major = re.search(r"openjdk\s+(\d+)\.", version, re.I)
            num = int(major.group(1)) if major else -1
        else:
            num = int(major.group(2))
        requested = (11 if item["id"].startswith("openjdk-11")
                     else 17 if item["id"].startswith("openjdk-17") else 21)
        if num != requested:
            raise InstallError(f"Java major mismatch: {num} != {requested}")
        command([str(javac), "-version"])
        verified.extend(["java -version", "javac -version"])
    elif family == "cmake":
        cmake = locate_binary(path, "cmake")
        command([str(cmake), "--version"], expected="cmake version")
        verified.append("cmake --version")
    elif family == "ndk":
        clang = locate_binary(path, "clang")
        command([str(clang), "--version"], expected="clang version")
        command([str(clang), "--target=aarch64-linux-android24", "-x", "c",
                 "-fsyntax-only", "-"], stdin="int test(void) { return 0; }\n")
        verified.extend(["clang --version", "clang -target aarch64-linux-android24 syntax test"])
    elif family == "aapt2-zipalign":
        aapt = locate_binary(path, "aapt2")
        align = locate_binary(path, "zipalign")
        command([str(aapt), "version"], expected="aapt2")
        info = command([str(align), "-h"], code_must_be_zero=False)
        if "Zip alignment utility" not in info and "zipalign" not in info.lower():
            raise InstallError("zipalign does not respond with recognizable usage")
        verified.extend(["aapt2 version", "zipalign -h"])
    elif family == "platform-tools":
        adb = locate_binary(path, "adb")
        command([str(adb), "version"], expected="Android Debug Bridge")
        verified.append("adb version")
    elif family == "d8-apksigner":
        jars = list(path.rglob("d8.jar")) + list(path.rglob("apksigner.jar"))
        if not any(p.name == "d8.jar" for p in jars) or not any(p.name == "apksigner.jar" for p in jars):
            raise InstallError("D8/ApkSigner Java JARs absent")
        javabin = (Path(os.environ["JAVA_HOME"]) / "bin/java"
                   if os.environ.get("JAVA_HOME") else Path(shutil.which("java") or ""))
        if not javabin.is_file():
            raise InstallError("Android-native Java runtime required for D8 and apksigner")
        d8jar = next(p for p in jars if p.name == "d8.jar")
        apksigner = next(p for p in jars if p.name == "apksigner.jar")
        command([str(javabin), "-cp", str(d8jar), "com.android.tools.r8.D8", "--version"])
        command([str(javabin), "-cp", str(apksigner), "com.android.apksigner.ApkSignerTool", "version"])
        verified.extend(["D8 Java JAR", "ApkSigner Java JAR"])
    else:
        raise InstallError(f"Unknown Android native probe family: {family}")
    return {"local_device_probe_passed": True, "commands": verified,
            "android_apk_build_verified": False}


def install(root: Path, item: dict, *, approve_third_party: bool,
            execute_probe: bool) -> dict:
    if not device_host():
        raise InstallError("This archive installer only runs on Android ARM64/Bionic")
    if item["provider"] != "magic616star666-bot/python-eye-toolchain" and not approve_third_party:
        raise InstallError("Third-party native binary source requires --approve-third-party")
    target = root / item["id"]
    state = target / ".python-eye-mobile-state.json"
    if target.exists():
        raise InstallError("Target already exists; refusing silent overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pyeye-bionic-", dir=target.parent) as tmp:
        workspace = Path(tmp)
        archive = workspace / item["asset_name"]
        download_verified({"download_url": item["url"], "sha256": item["sha256"]},
                          archive, MAX_COMPRESSED)
        if archive.stat().st_size != item["file_size_bytes"]:
            raise InstallError("Verified archive size differs from upstream release metadata")
        extracted = workspace / "unpacked"
        extracted.mkdir()
        safe_unpack(archive, extracted, limit=3_000_000_000)
        extracted.rename(target)
    outcome = {"id": item["id"], "archive_sha256": item["sha256"],
               "download_and_extract_verified": True,
               "local_device_probe_passed": False,
               "android_apk_build_verified": False,
               "status": "installed_archive_unverified"}
    if execute_probe:
        try:
            outcome.update(run_probe(target, item))
            outcome["status"] = "local_device_cli_probe_passed_not_apk_verified"
        except InstallError as e:
            outcome["probe_error"] = str(e)
            outcome["status"] = "probe_failed_not_ready"
    state.write_text(json.dumps(outcome, indent=2) + "\n", "utf-8")
    return outcome


def status(root: Path, item: dict, *, execute_probe: bool) -> dict:
    path = root / item["id"] / ".python-eye-mobile-state.json"
    if not path.is_file():
        return {"id": item["id"], "status": "not_installed", "local_device_probe_passed": False}
    observed = json.loads(path.read_text("utf-8"))
    if observed.get("archive_sha256") != item["sha256"]:
        raise InstallError("Installed archive state digest differs from catalog")
    if execute_probe:
        observed.update(run_probe(path.parent, item))
        observed["status"] = "local_device_cli_probe_passed_not_apk_verified"
        path.write_text(json.dumps(observed, indent=2) + "\n", "utf-8")
    observed["android_apk_build_verified"] = False
    return observed


def main() -> None:
    p = argparse.ArgumentParser(description="Verified Android/Bionic package installer (not yet a Kotlin IDE extension)")
    p.add_argument("action", choices=("list", "install", "status"))
    p.add_argument("--id", dest="tool_id", help="Exact tool ID from mobile-artifacts.json")
    p.add_argument("--root", type=Path, default=Path.home() / ".python-eye" / "mobile-tools")
    p.add_argument("--approve-download", action="store_true", help="Explicitly request downloading this upstream asset")
    p.add_argument("--approve-third-party", action="store_true", help="Explicitly allow third-party compiled executables")
    p.add_argument("--execute-probe", action="store_true", help="Explicitly execute downloaded binaries after verifying SHA-256")
    args = p.parse_args()
    try:
        catalog = load_index()
        index = {item["id"]: item for item in catalog["assets"]}
        if args.action == "list":
            print(json.dumps({"assets": catalog["assets"],
                              "android_phone_apk_build_verified": False,
                              "notice": "Only source assets and SHA256 are proven, not runnable phone builds."}, indent=2))
            return
        if args.tool_id not in index:
            raise InstallError("Specify an existing --id from the mobile artifact catalog")
        root = args.root.expanduser().resolve()
        item = index[args.tool_id]
        if args.action == "install":
            if not args.approve_download:
                raise InstallError("Explicit --approve-download required for any executable archive")
            outcome = install(root, item, approve_third_party=args.approve_third_party,
                              execute_probe=args.execute_probe)
        else:
            outcome = status(root, item, execute_probe=args.execute_probe)
        print(json.dumps(outcome, indent=2))
    except (InstallError, OSError, ValueError) as err:
        print(json.dumps({"ok": False, "error": str(err)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
