#!/usr/bin/env python3
"""Verify pinned Android-native artifacts against REAL GitHub Release metadata.

Offline mode checks schema; --live confirms matching upstream asset name,
size, sha256 digest and asset URL. No binaries downloaded or executed.
"""
from __future__ import annotations

from collections import defaultdict
import argparse
import json
import os
from pathlib import Path
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "mobile-artifacts.json"


def validate_offline(index: dict) -> dict:
    if index.get("schema_version") != 1 or index.get("host_abi") != "arm64-v8a":
        raise ValueError("Unsupported mobile catalog schema/ABI")
    ids = set()
    assets = index.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("Mobile assets missing")
    for a in assets:
        if a["id"] in ids:
            raise ValueError(f"Duplicate: {a['id']}")
        ids.add(a["id"])
        if not re.fullmatch(r"[0-9a-f]{64}", a["sha256"]):
            raise ValueError(f"Invalid SHA: {a['id']}")
        if not isinstance(a["file_size_bytes"], int) or a["file_size_bytes"] < 1024:
            raise ValueError(f"Invalid size: {a['id']}")
        if any(a.get(flag) is not False for flag in ("installed", "local_device_probe_passed", "android_apk_build_verified")):
            raise ValueError(f"Fake Ready state in {a['id']}")
        if a.get("redistribution_permitted") != "not_assessed_no_mirroring":
            raise ValueError("Do not claim licensing rights without independent review")
        url = f"https://github.com/{a['provider']}/releases/download/"
        if not a["url"].startswith(url):
            raise ValueError(f"Provider URL mismatch {a['id']}")
    return {"assets": len(assets), "unique_ids": len(ids), "device_ready_claims": 0}


def fetch_release(provider: str, tag: str) -> dict:
    url = f"https://api.github.com/repos/{provider}/releases/tags/{quote(tag, safe='')}"
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "PythonEye-Release-SHA256-Verifier/1.0"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urlopen(Request(url, headers=headers), timeout=45) as response:
        blob = response.read(3_000_000)
    data = json.loads(blob)
    if data.get("tag_name") != tag:
        raise ValueError(f"Wrong upstream tag {provider}/{tag}")
    return data


def verify_live(index: dict) -> dict:
    grouped = defaultdict(list)
    for item in index["assets"]:
        url = item["url"]
        after = url.split("/releases/download/", 1)[1]
        tag, filename = after.split("/", 1)
        if filename != item["asset_name"]:
            raise ValueError(f"Asset name mismatch: {item['id']}")
        grouped[(item["provider"], tag)].append(item)
    validated = 0
    for (provider, tag), elements in sorted(grouped.items()):
        release = fetch_release(provider, tag)
        byname = {a["name"]: a for a in release.get("assets", [])}
        for item in elements:
            actual = byname.get(item["asset_name"])
            if not actual:
                raise ValueError(f"Upstream asset not found: {item['id']}")
            if actual.get("size") != item["file_size_bytes"]:
                raise ValueError(f"Asset size mismatch: {item['id']}")
            github_digest = actual.get("digest")
            if github_digest:
                if github_digest != "sha256:" + item["sha256"]:
                    raise ValueError(f"Asset SHA-256 differs from original GitHub release: {item['id']}")
            else:
                vetted_runs = {
                    "https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44616843832",
                    "https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44677089383",
                }
                if (item.get("sha256_evidence") != "downloaded_and_sha256_hashed_in_github_ci"
                        or item.get("sha256_evidence_run") not in vetted_runs):
                    raise ValueError(f"Missing independently recorded upstream asset SHA-256: {item['id']}")
            if actual.get("browser_download_url") != item["url"]:
                raise ValueError(f"Asset download URL mismatch: {item['id']}")
            if actual.get("state") != "uploaded":
                raise ValueError(f"Asset upload incomplete: {item['id']}")
            validated += 1
    return {"real_upstream_release_metadata_verified": validated,
            "scope": "metadata SHA256 and exact asset identity only; NOT binary execution or Android phone APK build"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    index = json.loads(CATALOG.read_text("utf-8"))
    result = validate_offline(index)
    if args.live:
        result.update(verify_live(index))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
