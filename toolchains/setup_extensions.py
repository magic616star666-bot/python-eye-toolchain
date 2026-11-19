#!/usr/bin/env python3
"""Python Eye unified Extensions/setup manifest + safe local CLI readiness probes.

Combines 8 legacy + 20 extended + 25 new add-on routes by exact ID. Nothing
is marked Ready by GitHub CI, a URL, a JSON entry or mere file presence.
No app settings are changed. Probes run only with --probe and are user-scoped.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ROOT / "tools.json",
    ROOT / "toolchains/extended-tools.json",
    ROOT / "toolchains/addons-catalog.json"
)

# No shell and no network. Only fixed version/help commands for known programs.
EXECUTABLES = {
    "apache-maven": ("mvn", "-version"),
    "apache-ant": ("ant", "-version"),
    "ninja-build": ("ninja", "--version"),
    "llvm-clang": ("clang", "--version"),
    "rustup": ("rustup", "--version"),
    "rust-cargo": ("cargo", "--version"),
    "nodejs": ("node", "--version"),
    "npm": ("npm", "--version"),
    "git-cli": ("git", "--version"),
    "logcat-debug": ("adb", "version"),
    "release-signing": ("apksigner", "version"),
    "android-aidl": ("aidl", "--version"),
    "apk-analyzer": ("apkanalyzer", "version"),
    "eas-cli": ("eas", "--version"),
    "cordova-cli": ("cordova", "--version"),
    "beeware-briefcase": ("briefcase", "--version"),
    "flet-cli": ("flet", "--version"),
    "capacitor-cli": ("cap", "--version"),
}


def load_all() -> dict:
    seen: set[str] = set()
    rows = []
    for source in FILES:
        data = json.loads(source.read_text("utf-8"))
        for tool in data["tools"]:
            ident = tool["id"]
            if ident in seen:
                raise ValueError(f"Duplicate extension ID across catalogs: {ident}")
            seen.add(ident)
            rows.append({"id": ident, "name": tool["name"],
                         "catalog": source.name,
                         "downloadable_archive": bool(tool.get("published", False)),
                         "ready": False, "cli_probe_passed": False,
                         "apk_build_verified_on_this_host": False,
                         "android_phone_verified": False,
                         "install_method": (tool.get("install", {}) or {}).get("method") or tool.get("method"),
                         "requires": tool.get("requires", [])})
    return {"schema_version": 1, "count": len(rows), "tools": rows,
            "readiness_definition": "CLI Ready only from successful execution on the SAME host; never from catalog metadata.",
            "android_phone_apk_build_verified": False,
            "legacy_catalog_unmodified": True}


def cli_probe(tool: dict) -> dict:
    command = EXECUTABLES.get(tool["id"])
    if not command:
        return {"id": tool["id"], "ready": False,
                "probe": "per-project-package-or-unsupported-global-probe"}
    exe = shutil.which(command[0])
    if not exe:
        return {"id": tool["id"], "ready": False, "probe": "executable_missing"}
    try:
        result = subprocess.run([exe, command[1]], capture_output=True,
                                text=True, check=False, timeout=20, errors="replace",
                                stdin=subprocess.DEVNULL)
        observed = (result.stdout + result.stderr).strip()
        ok = result.returncode == 0 and bool(observed)
        return {"id": tool["id"], "ready": ok,
                "probe": "actual_local_cli_exit_success" if ok else "probe_failed",
                "exit_code": result.returncode, "output_excerpt": observed[:180]}
    except (OSError, subprocess.TimeoutExpired) as err:
        return {"id": tool["id"], "ready": False, "probe": "probe_failed",
                "error": str(err)[:180]}


def manifest(probe: bool = False, project: Path | None = None) -> dict:
    data = load_all()
    if probe:
        for tool in data["tools"]:
            result = cli_probe(tool)
            tool["ready"] = result["ready"]
            tool["cli_probe_passed"] = result["ready"]
            tool["probe"] = result["probe"]
            # Build/test statuses must remain separate from a CLI --version check.
            tool["apk_build_verified_on_this_host"] = False
            tool["android_phone_verified"] = False
        data["cli_probed"] = True
    if project is not None:
        from plan_project import propose
        from zip_builder import safe_unpack, find_root, BuildError
        from tempfile import TemporaryDirectory
        import zipfile
        path = project.expanduser().resolve()
        if path.is_dir():
            plan = propose(path)
        elif path.is_file() and path.suffix.lower() == ".zip":
            with TemporaryDirectory(prefix="pyeye-addon-plan-") as temp:
                safe_unpack(path, Path(temp))
                plan = propose(find_root(Path(temp)))
        else:
            raise BuildError("Expected a project directory or .zip archive")
        required = set(plan["recommended_legacy_tool_ids"]) | set(plan["recommended_extended_tool_ids"])
        data["project"] = plan
        data["project_required_ids"] = sorted(required)
        catalog_ids = {item["id"] for item in data["tools"]}
        data["project_unmapped_requirements"] = sorted(required - catalog_ids)
        data["project_supported_apk_route"] = plan["supported_apk_route"]
    data["ready_cli_count"] = sum(t["cli_probe_passed"] for t in data["tools"])
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified Python Eye Extensions setup status")
    parser.add_argument("--probe", action="store_true", help="Run fixed read-only local CLI version commands")
    parser.add_argument("--project", type=Path, help="Read-only project dependency planner (.zip or folder)")
    parser.add_argument("--compact", action="store_true", help="Output only summary and required IDs")
    args = parser.parse_args()
    try:
        data = manifest(probe=args.probe, project=args.project)
        if args.compact:
            data.pop("tools")
        print(json.dumps(data, indent=2))
    except (ValueError, OSError, ImportError, RuntimeError) as err:
        print(json.dumps({"ok": False, "error": str(err)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
