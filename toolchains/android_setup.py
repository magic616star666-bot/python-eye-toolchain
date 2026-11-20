#!/usr/bin/env python3
"""Android-only Python Eye extensions setup interface.

This is the entry point for the upcoming Android IDE extension UI. It NEVER
downloads Linux desktop binaries and does not assume that a Termux installed
command is executable inside the IDE's app sandbox. Real APK builds still
require a separate local project smoke test.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import zipfile

from mobile_installer import (device_host, install as native_install,
                              load_index, run_probe, status as native_status)
from versions_manager import InstallError

HERE = Path(__file__).resolve().parent
PROFILE = HERE / "android-only-profile.json"
DEFAULT_ROOT = Path.home() / ".python-eye" / "mobile-tools"


def android_profile() -> dict:
    data = json.loads(PROFILE.read_text("utf-8"))
    if (data.get("schema_version") != 1 or data.get("target_os") != "android"
            or data.get("target_abi") != "arm64-v8a"):
        raise ValueError("Invalid Android-only extension profile")
    seen: set[str] = set()
    for key in ("core_android_workflow", "optional_android_native",
                "blocked_on_android_until_ported"):
        for entry in data[key]:
            if entry["id"] in seen:
                raise ValueError("Duplicate Android extension ID")
            seen.add(entry["id"])
            if entry.get("device_ready") is not False:
                raise ValueError("Static profile must not declare devices ready")
    if len(seen) != 53:
        raise ValueError("Expected exactly 53 classified legacy/addon entries")
    return data


def android_catalog(root: Path) -> dict:
    profile = android_profile()
    sources = load_index()["assets"]
    records = []
    for item in sources:
        observed = native_status(root, item, execute_probe=False)
        # A persisted state, even one with earlier successful probes, is not
        # a fresh phone execution proof. UI displays it as a recorded event.
        records.append({
            "asset_id": item["id"], "family": item["family"],
            "version": item["version"], "source": item["url"],
            "sha256": item["sha256"], "file_size_bytes": item["file_size_bytes"],
            "device_ready": False, "android_apk_build_verified": False,
            "download_state": observed["status"],
            "previous_local_probe_recorded": bool(observed.get("local_device_probe_passed")) and device_host(),
            "source_verified_not_runnable_proof": True,
        })
    return {
        "target": "android-arm64-v8a-bionic", "on_android_device": device_host(),
        "core_workflow_count": len(profile["core_android_workflow"]),
        "optional_native_count": len(profile["optional_android_native"]),
        "desktop_or_unported_hidden_count": len(profile["blocked_on_android_until_ported"]),
        "available_upstream_native_archives": len(records),
        "native_sources": records,
        "apk_build_tested_on_this_phone": False,
        "policy": "Only Android Bionic native assets or compatible Java/Gradle project dependencies; desktop-only routes hidden.",
    }


def android_plan(project: Path) -> dict:
    from plan_project import propose
    from zip_builder import safe_unpack, find_root
    from tempfile import TemporaryDirectory

    profile = android_profile()
    target = project.expanduser().resolve()
    if target.is_dir():
        data = propose(target)
    elif target.is_file() and target.suffix.lower() == ".zip":
        with TemporaryDirectory(prefix="pyeye-android-plan-") as tmp:
            safe_unpack(target, Path(tmp))
            data = propose(find_root(Path(tmp)))
    else:
        raise ValueError("Use an Android project directory or trusted .zip")
    valid = {x["id"] for x in profile["core_android_workflow"]}
    optional = {x["id"] for x in profile["optional_android_native"]}
    excluded = {x["id"] for x in profile["blocked_on_android_until_ported"]}
    required = set(data["recommended_legacy_tool_ids"]) | set(data["recommended_extended_tool_ids"])
    return {
        "project_type": data["project_type"],
        "recognized_android_packaging_project": bool(data["supported_apk_route"]),
        "android_core_requirements": sorted(required & valid),
        "android_native_port_requirements": sorted(required & optional),
        "blocked_desktop_unported_requirements": sorted(required & excluded),
        "unknown_requirements": sorted(required - valid - optional - excluded),
        "can_start_build_without_checks": False,
        "phone_real_executable_probes_required": True,
        "phone_real_apk_build_required": True,
        "warnings": data["warnings"],
    }


def do_probe(asset_id: str, root: Path) -> dict:
    if not device_host():
        raise InstallError("Device probe is Android ARM64/Bionic ONLY")
    index = {x["id"]: x for x in load_index()["assets"]}
    if asset_id not in index:
        raise ValueError("Unknown Android native asset ID")
    # Only locally installed archive can be probed; never auto-download.
    return native_status(root, index[asset_id], execute_probe=True)


def do_install(asset_id: str, root: Path, approve_download: bool,
               approve_third_party: bool, execute_probe: bool) -> dict:
    if not device_host():
        raise InstallError("Android native installation must run inside real Android ARM64/Bionic process")
    if not approve_download:
        raise InstallError("Explicit --approve-download is required")
    index = {x["id"]: x for x in load_index()["assets"]}
    if asset_id not in index:
        raise ValueError("Unknown Android native asset ID")
    return native_install(root, index[asset_id],
                          approve_third_party=approve_third_party,
                          execute_probe=execute_probe)


def main() -> None:
    parser = argparse.ArgumentParser(description="Python Eye ANDROID-only ARM64/Bionic toolchain setup")
    parser.add_argument("action", choices=("catalog", "plan", "status", "probe", "install",
                                          "gradle-list", "gradle-resolve", "gradle-status",
                                          "gradle-install", "gradle-probe"))
    parser.add_argument("--project", type=Path, help="Android project directory or ZIP for dependency plan")
    parser.add_argument("--asset", help="Exact Android native asset ID")
    parser.add_argument("--version", help="Exact official Gradle release number, e.g. 8.14.3")
    parser.add_argument("--java", help="Path to working Android/Bionic JDK java binary")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                        help="IDE-private executable-writable tool directory")
    parser.add_argument("--approve-download", action="store_true")
    parser.add_argument("--approve-third-party", action="store_true")
    parser.add_argument("--execute-probe", action="store_true")
    args = parser.parse_args()
    try:
        root = args.root.expanduser().resolve()
        if args.action.startswith("gradle-"):
            from android_gradle_versions import (
                gradle_metadata, resolve_java,
                install as gradle_install, status as gradle_status,
            )
            if args.action == "gradle-list":
                data = {"source": "https://services.gradle.org/distributions",
                        "versions": "Any real released Gradle numeric version with SHA-256",
                        "android_phone_apk_build_verified": False}
            else:
                if not args.version:
                    parser.error("Gradle actions require --version")
                if args.action == "gradle-resolve":
                    data = gradle_metadata(args.version)
                elif args.action == "gradle-status":
                    data = gradle_status(args.version, root / "gradle-versions")
                else:
                    java = resolve_java(args.java)
                    if args.action == "gradle-probe":
                        data = gradle_status(args.version, root / "gradle-versions",
                                             java=java, execute_probe=True)
                    else:
                        data = gradle_install(args.version, root / "gradle-versions",
                                              java=java, approve=args.approve_download,
                                              execute_probe=args.execute_probe)
        elif args.action == "catalog":
            data = android_catalog(root)
        elif args.action == "plan":
            if args.project is None:
                parser.error("plan requires --project")
            data = android_plan(args.project)
        elif args.action == "status":
            if args.asset:
                asset = {x["id"]: x for x in load_index()["assets"]}.get(args.asset)
                if not asset:
                    raise ValueError("Unknown Android native asset ID")
                data = native_status(root, asset, execute_probe=False)
            else:
                data = android_catalog(root)
        elif args.action == "probe":
            if not args.asset:
                parser.error("probe requires --asset")
            data = do_probe(args.asset, root)
        else:
            if not args.asset:
                parser.error("install requires --asset")
            data = do_install(args.asset, root, args.approve_download,
                              args.approve_third_party, args.execute_probe)
        print(json.dumps(data, indent=2))
    except (InstallError, RuntimeError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
