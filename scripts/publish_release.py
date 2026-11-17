#!/usr/bin/env python3
"""Download, checksum-verify, and register GitHub Release tool assets."""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, quote
from urllib.request import Request, urlopen
import hashlib

MAX_BYTES = 2 * 1024 ** 3 - 1024 ** 2
CATALOG = Path("tools.json")

def inputs():
    tool_id = os.environ["TOOL_ID"].strip()
    version = os.environ["TOOL_VERSION"].strip()
    source = os.environ["SOURCE_URL"].strip()
    name = os.environ["ASSET_NAME"].strip()
    expected = os.environ["EXPECTED_SHA256"].strip().lower()
    if not re.fullmatch(r"[a-z0-9-]{1,80}", tool_id):
        raise ValueError("Invalid tool id")
    if not re.fullmatch(r"[A-Za-z0-9._+-]{1,60}", version):
        raise ValueError("Invalid version")
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,180}\\.(zip|jar|tgz|tar\\.gz)", name):
        raise ValueError("Asset must be a simple .zip, .jar, .tgz or .tar.gz name")
    if urlsplit(source).scheme != "https" or not urlsplit(source).hostname:
        raise ValueError("Only public HTTPS downloads are accepted")
    if not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise ValueError("SHA-256 must be exactly 64 hex characters")
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    if tool_id not in {x["id"] for x in data["tools"]}:
        raise ValueError("Unknown catalog tool id")
    if os.getenv("TESTED_ON_ANDROID_ARM64") != "yes":
        raise ValueError("Confirm the archive was tested on Android ARM64 before publication")
    return tool_id, version, source, name, expected, data

def download():
    tool_id, version, source, name, expected, _ = inputs()
    folder = Path("dist")
    folder.mkdir(exist_ok=True)
    path = folder / name
    digest = hashlib.sha256()
    count = 0
    req = Request(source, headers={"User-Agent": "PythonEyeToolchain-Publisher/1.0"})
    with urlopen(req, timeout=120) as response, path.open("wb") as output:
        if urlsplit(response.geturl()).scheme != "https":
            raise ValueError("Download redirected to an insecure scheme")
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            count += len(chunk)
            if count > MAX_BYTES:
                raise ValueError("Asset exceeds GitHub Release upload limit")
            digest.update(chunk)
            output.write(chunk)
    if count == 0:
        raise ValueError("Downloaded file is empty")
    if digest.hexdigest() != expected:
        path.unlink(missing_ok=True)
        raise ValueError("SHA-256 mismatch; upload blocked")
    print(f"Verified {tool_id} {version}: {count} bytes, SHA-256 {expected}")

def mark():
    tool_id, version, source, name, expected, data = inputs()
    repo = os.environ["GITHUB_REPOSITORY"]
    for item in data["tools"]:
        if item["id"] == tool_id:
            item.update(
                version=version,
                published=True,
                status="published",
                url=f"https://github.com/{repo}/releases/download/toolchain-v1/{quote(name)}",
                sha256=expected,
            )
            break
    CATALOG.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated catalog for {tool_id}")

if __name__ == "__main__":
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in ("download", "mark"):
            raise ValueError("Usage: publish_release.py download|mark")
        {"download": download, "mark": mark}[sys.argv[1]]()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
