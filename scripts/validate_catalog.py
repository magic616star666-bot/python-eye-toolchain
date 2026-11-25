#!/usr/bin/env python3
"""Offline validation of Python Eye's public tool catalog (stdlib only)."""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# The original eight must always stay. NEW tools may be added freely (no app update):
# a Maven JAR tool only needs the generic rules in check_maven_tool() below.
EXPECTED = {
    "openjdk-17", "gradle", "android-sdk-36", "aapt2-zipalign",
    "d8-apksigner", "kotlin-compiler", "android-gradle-plugin", "chaquopy-build",
}
# Same rules as the IDE's MavenTools (ToolStore.kt) - keep them in step.
MAVEN_COORD = re.compile(r"[A-Za-z0-9_.-]{2,120}:[A-Za-z0-9_.-]{1,120}")
MAVEN_VERSION = re.compile(r"[0-9][0-9A-Za-z.+-]{0,40}")
JAVA_PROBE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*(\.[A-Za-z_$][A-Za-z0-9_$]*)+( [A-Za-z0-9_.=:/+-]+){0,6}")


def check_maven_tool(tool_id, item, install):
    if item.get("published") is not False or item.get("url") or item.get("sha256"):
        raise ValueError(f"{tool_id}: Maven tool must not advertise a release archive URL/checksum")
    coord, version = install.get("plugin_id", ""), item.get("version", "")
    if not MAVEN_COORD.fullmatch(coord) or not MAVEN_VERSION.fullmatch(version):
        raise ValueError(f"{tool_id}: invalid Maven coordinate {coord}:{version}")
    probes = item.get("required_probes")
    if not isinstance(probes, list) or not 1 <= len(probes) <= 6 or not all(
            isinstance(x, str) and JAVA_PROBE.fullmatch(x.strip()) for x in probes):
        raise ValueError(f"{tool_id}: required_probes must be 1-6 'java.main.Class [args]' strings")
    paths = install.get("required_paths", [])
    if not isinstance(paths, list) or not all(re.fullmatch(r"lib/[A-Za-z0-9_.-]+\.jar", x) for x in paths):
        raise ValueError(f"{tool_id}: required_paths must be lib/<name>.jar")
    if item.get("catalog_state") != "maven_resolution_not_device_verified":
        raise ValueError(f"{tool_id}: Maven tool cannot be marked device ready before actual Test")
MANAGED = {"android-sdk-36", "android-gradle-plugin", "chaquopy-build"}
RELEASE_BASE = "https://github.com/magic616star666-bot/python-eye-toolchain/releases/download/"
# Fixed allow-list of our own immutable release tags (no arbitrary tags or hosts)
RELEASE_TAGS = ("toolchain-v1", "jdk-awt-v1")
INSTALL_KINDS = {"archive", "sdkmanager", "gradle_plugin_resolution", "maven_artifact_resolution"}

def check(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    tools = data.get("tools")
    if not isinstance(tools, list):
        raise ValueError('The root JSON must contain a "tools" list')
    if data.get("schema_version") != 1:
        raise ValueError("Expected backwards-compatible schema_version 1")
    if data.get("architecture") != "arm64-v8a":
        raise ValueError("Catalog must target Android arm64-v8a")
    if not 8 <= len(tools) <= 200:
        raise ValueError(f"Unexpected tool count {len(tools)}")
    by_id = {}
    for item in tools:
        if not isinstance(item, dict):
            raise ValueError("Every tool must be an object")
        tool_id = item.get("id")
        if not isinstance(tool_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", tool_id):
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
        elif kind == "maven_artifact_resolution":
            check_maven_tool(tool_id, item, install)
        else:
            if kind != "archive" or item.get("published") is not True:
                raise ValueError(f"{tool_id}: expected downloadable archive")
            url = item.get("url", "")
            prefix = next((RELEASE_BASE + t + "/" for t in RELEASE_TAGS
                           if isinstance(url, str) and url.startswith(RELEASE_BASE + t + "/")), None)
            if prefix is None:
                raise ValueError(f"{tool_id}: only published release asset URL allowed")
            filename = url[len(prefix):]
            if "/" in filename or not filename or urlparse(url).query:
                raise ValueError(f"{tool_id}: invalid release asset filename")
            if not filename.endswith((".zip", ".tar.xz", ".tar.gz")):
                raise ValueError(f"{tool_id}: unsupported compressed archive format")
            if item.get("archive_format") != ("zip" if filename.endswith(".zip") else "tar.xz" if filename.endswith(".tar.xz") else "tar.gz"):
                raise ValueError(f"{tool_id}: archive format mismatch")
            if not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))):
                raise ValueError(f"{tool_id}: SHA-256 is missing or malformed")
            if not isinstance(item.get("file_size_bytes"), int) or item["file_size_bytes"] < 1024:
                raise ValueError(f"{tool_id}: file size is missing")
            if not isinstance(install.get("required_paths"), list) or not install["required_paths"]:
                raise ValueError(f"{tool_id}: extracted required_paths missing")
            if item.get("catalog_state") != "downloadable_not_device_verified":
                raise ValueError(f"{tool_id}: invalid archive status")
    if not EXPECTED <= set(by_id):
        raise ValueError(f"Original tools missing: {sorted(EXPECTED - set(by_id))}")
    for k, deps in ((k, v["requires"]) for k, v in by_id.items()):
        if k in deps or len(set(deps)) != len(deps):
            raise ValueError(f"{k}: duplicate or self-referential dependency")
        unknown = set(deps) - set(by_id)
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
    # Keep duplicate metadata files consistent with the public catalog.
    managed = json.loads(Path("managed-tools.json").read_text("utf-8"))
    routes = json.loads(Path("official_install_routes.json").read_text("utf-8"))
    managed_index = {t["id"]: t for t in managed["tools"]}
    if set(managed_index) != MANAGED:
        raise ValueError("managed-tools.json must contain exactly 3 managed IDs")
    for key in MANAGED:
        if managed_index[key]["version"] != by_id[key]["version"]:
            raise ValueError(f"Managed version mismatch: {key}")
        if managed_index[key].get("ready_on_android_phone") is not False:
            raise ValueError(f"{key}: false mobile Ready flag")
        if key != "android-sdk-36" and routes[key]["version"] != by_id[key]["version"]:
            raise ValueError(f"Official installation version mismatch: {key}")
    version_keys = {
        "gradle": "gradle", "kotlin": "kotlin",
        "android_gradle_plugin": "android_gradle_plugin",
        "chaquopy": "chaquopy", "compile_sdk": "compile_sdk",
    }
    for key, expected_key in version_keys.items():
        if routes["build_version_recommendation"][key] != profile[expected_key]:
            raise ValueError(f"Build profile mismatch: {key}")
    kinds = [t["install"]["method"] for t in tools]
    print(f"PASS: {len(tools)} unique tool IDs; {kinds.count('archive')} real release archives, "
          f"{len(MANAGED)} existing managed tools, {kinds.count('maven_artifact_resolution')} Maven JAR tool(s);")
    print("      SHA-256 metadata, stable schema, ARM64 profile, dependencies all consistent.")
    print("      NOTE: Device installation and APK building inside Python Eye IDE NOT verified.")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(check(Path(sys.argv[1] if len(sys.argv) > 1 else "tools.json")))
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
