#!/usr/bin/env python3
"""Pin the Ubuntu ARM64 rootfs used by Python Eye's Linux runtime.

Looks through termux/proot-distro GitHub Releases (the rootfs tarballs Termux users
run under PRoot), prefers Ubuntu 24.04 "noble", downloads the asset, checks its size
and the SHA-256 digest GitHub publishes for release assets, and records how many
leading path components to strip. The IDE downloads from the ORIGINAL upstream URL
(no re-hosting) and verifies the same SHA-256.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

API = "https://api.github.com/repos/termux/proot-distro/releases?per_page=40"
PREFERRED = [
    re.compile(r"^ubuntu-noble-aarch64-pd-v[\d.]+\.tar\.xz$"),
    re.compile(r"^ubuntu-[a-z]+-aarch64-pd-v[\d.]+\.tar\.xz$"),
    re.compile(r"^ubuntu.*aarch64.*\.tar\.xz$"),
]


def request(url: str):
    headers = {"User-Agent": "python-eye-toolchain-ci", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=300)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with request(API) as resp:
        releases = json.load(resp)
    releases = [r for r in releases if not r.get("draft") and not r.get("prerelease")]
    chosen = None
    for pattern in PREFERRED:
        for rel in releases:  # API returns newest first
            for asset in rel.get("assets", []):
                if pattern.match(asset["name"]):
                    chosen = (rel, asset)
                    break
            if chosen:
                break
        if chosen:
            break
    if not chosen:
        raise SystemExit("No Ubuntu aarch64 rootfs found in termux/proot-distro releases")
    rel, asset = chosen
    name = asset["name"]
    url = asset["browser_download_url"]
    print(f"rootfs: {rel['tag_name']} {name} {asset['size']} bytes")
    path = out / name
    h = hashlib.sha256()
    with request(url) as resp, path.open("wb") as f:
        for chunk in iter(lambda: resp.read(1 << 20), b""):
            f.write(chunk)
            h.update(chunk)
    digest = h.hexdigest()
    if path.stat().st_size != asset["size"]:
        raise SystemExit("rootfs size mismatch")
    upstream = (asset.get("digest") or "").lower()
    if upstream.startswith("sha256:") and upstream[7:] != digest:
        raise SystemExit(f"rootfs SHA-256 mismatch: {digest} != {upstream}")

    tops, members, has_os_release = set(), 0, False
    with tarfile.open(path, "r:xz") as tar:
        for m in tar:
            members += 1
            parts = [p for p in m.name.split("/") if p not in ("", ".")]
            if parts:
                tops.add(parts[0])
            if m.name.rstrip("/").endswith("etc/os-release"):
                has_os_release = True
    strip = 1 if len(tops) == 1 and next(iter(tops)) not in ("etc", "usr", "bin") else 0
    codename = (re.search(r"^ubuntu-([a-z]+)-", name) or [None, "ubuntu"])[1]
    known = {"noble": "Ubuntu 24.04 LTS (Noble Numbat)", "jammy": "Ubuntu 22.04 LTS (Jammy Jellyfish)",
             "oracular": "Ubuntu 24.10", "plucky": "Ubuntu 25.04", "questing": "Ubuntu 25.10"}
    info = {
        "id": f"ubuntu-{codename}",
        "name": known.get(codename, f"Ubuntu ({codename})"),
        "provider": "termux/proot-distro",
        "release_tag": rel["tag_name"],
        "asset_name": name,
        "url": url,
        "sha256": digest,
        "file_size_bytes": asset["size"],
        "upstream_digest_checked": upstream.startswith("sha256:"),
        "format": "tar.xz",
        "strip_components": strip,
        "top_level": sorted(tops)[:5],
        "members": members,
        "has_os_release": has_os_release,
    }
    if not has_os_release:
        raise SystemExit("rootfs has no etc/os-release")
    (out / "rootfs.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    sys.exit(main())
