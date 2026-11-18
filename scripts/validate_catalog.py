#!/usr/bin/env python3
"""Offline validation of Python Eye's public tool catalog (stdlib only)."""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

EXPECTED = {
    "openjdk-17", "gradle", "android-sdk-36", "aapt2-zipalign",
    "d8-apksigner", "kotlin-compiler", "android-gradle-plugin", "chaquopy-build"
}
MANAGED = {"android-sdk-36", "android-gradle-plugin", "chaquopy-build"}
RELEASE_PREFIX = (
    "https://github.com/magic616star666-bot/python-eye-toolchain/"
    "releases/download/toolchain-v1/"
)
INSTALL_KINDS = {"archive", "sdkmanager", "gradle_plugin_resolution"}

def check(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    tools = data.get("tools")
    if not isinstance(tools, list):
        raise ValueError('The root JSON must contain a "tools" list')
    if data.get("schema_version") != 1:
        raise ValueError("Expected backwards-compatible schema_version 1")
    if data.get("architecture") != "arm64-v8a":
        raise ValueError("Catalog must target Android arm64-v8a")
    if len(tools) != 8:
        raise ValueError(f"Expected exactly 8 tools, got {len(tools)}")
    by_id = {}
    for item in tools:
        if not isinstance(item, dict):
            raise ValueError("Every tool must be an object")
        tool_id = item.get("id")
        if not isinstance(tool_id, str) or not re.fullmatch(r"[a-z0-9-]+", tool_id):
            raise ValueError(f"Invalid tool ID: {tool_id!r}")
        if tool_id in by_id:
            raise ValueError(f"Duplicate tool ID: {tool_id}")
        by_id[tool_id] = item
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            raise ValueError(f"{tool_id}: tool name missing")
        if not isinstance(item.get("version"), str) or not item["version"].strip():
            raise ValueError(f"{tool_id}: version missing")
        if not isinstance(item.get("requires"), list):
            raise ValueError(f"{tool_id}: requires must be a list")
        if not isinstance(item.get("install"), dict):
            raise ValueError(f"{tool_id}: install metadata missing")
        install = item["install"]
        kind = install.get("method")
        if kind not in INSTALL_KINDS:
            raise ValueError(f"{tool_id}: unknown install method {kind!r}")
        if install.get("device_verified") is not False:
            raise ValueError(f"{tool_id}: no Android-device verification has happened")
        if item.get("device_build_verified") is not False:
            raise ValueError(f"{tool_id}: on-device build verification not established")
        if tool_id in MANAGED:
            if kind == "archive":
                raise ValueError(f"{tool_id}: managed tool cannot be a standalone release archive")
            if item.get("published") is not False or item.get("url") or item.get("sha256"):
                raise ValueError(f"{tool_id}: cannot pretend a managed dependency is an uploaded archive")
            if item.get("catalog_state") != "managed_via_official_tool_not_integrated":
                raise ValueError(f"{tool_id}: invalid managed state")
        else:
            if kind != "archive" or item.get("published") is not True:
                raise ValueError(f"{tool_id}: expected downloadable archive")
            url = item.get("url", "")
            if not isinstance(url, str) or not url.startswith(RELEASE_PREFIX):
                raise ValueError(f"{tool_id}: only published release asset URL allowed")
            filename = url[len(RELEASE_PREFIX):]
            if "/" in filename or not filename or urlparse(url).query:
                raise ValueError(f"{tool_id}: invalid release asset filename")
            if not filename.endswith((".zip", ".tar.xz")):
                raise ValueError(f"{tool_id}: unsupported compressed archive format")
            if item.get("archive_format") != ("zip" if filename.endswith(".zip") else "tar.xz"):
                raise ValueError(f"{tool_id}: archive format mismatch")
            if not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))):
                raise ValueError(f"{tool_id}: SHA-256 is missing or malformed")
            if not isinstance(item.get("file_size_bytes"), int) or item["file_size_bytes"] < 1024:
                raise ValueError(f"{tool_id}: file size is missing")
            if not isinstance(install.get("required_paths"), list) or not install["required_paths"]:
                raise ValueError(f"{tool_id}: extracted required_paths missing")
            if item.get("catalog_state") != "downloadable_not_device_verified":
                raise ValueError(f"{tool_id}: invalid archive status")
    if set(by_id) != EXPECTED:
        raise ValueError(f"Unexpected or missing tools: expected {sorted(EXPECTED)}, got {sorted(by_id)}")
    for k, deps in ((k, v["requires"]) for k, v in by_id.items()):
        if k in deps or len(set(deps)) != len(deps):
            raise ValueError(f"{k}: duplicate or self-referential dependency")
        unknown = set(deps) - EXPECTED
        if unknown:
            raise ValueError(f"{k}: unknown dependencies {unknown}")
    visited, stack = set(), set()
    def visit(key):
        if key in stack:
            raise ValueError(f"Dependency cycle around {key}")
        if key in visited:
            return
        stack.add(key)
        for dep in by_id[key]["requires"]:
            visit(dep)
        stack.remove(key)
        visited.add(key)
    for key in sorted(by_id):
        visit(key)
    profile = data["compatible_build_profile"]
    if (profile["gradle"], profile["android_gradle_plugin"], profile["kotlin"],
        profile["chaquopy"], profile["compile_sdk"]) != ("8.14.3", "8.11.0", "2.1.20", "17.2.0", 36):
        raise ValueError("Unsupported build-profile drift")
    print("PASS: 8 unique tool IDs; 5 real release archives, 3 managed installs;")
    print("      SHA-256 metadata, stable schema, ARM64 profile, dependencies all consistent.")
    print("      NOTE: Device installation and APK building inside Python Eye IDE NOT verified.")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(check(Path(sys.argv[1] if len(sys.argv) > 1 else "tools.json")))
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
