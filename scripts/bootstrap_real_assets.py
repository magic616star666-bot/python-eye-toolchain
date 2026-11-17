#!/usr/bin/env python3
"""Fetch selected public upstream binaries and publish to Python Eye GitHub Releases.

This runs in GitHub Actions; it does NOT claim device-level install compatibility.
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

REPO = os.environ["GITHUB_REPOSITORY"]
TAG = "toolchain-v1"
DIST = pathlib.Path("dist")
CATALOG = pathlib.Path("tools.json")
MAX_SIZE = 230 * 1024 * 1024
SOURCES = [
    {
        "filename": "gradle-8.14.3-bin.zip",
        "url": "https://services.gradle.org/distributions/gradle-8.14.3-bin.zip",
        "sha256": "bd71102213493060956ec229d946beee57158dbd89d0e62b91bca0fa2c5f3531",
        "tool_ids": ["gradle"],
        "version": "8.14.3",
    },
    {
        "filename": "jdk17-arm64.tar.xz",
        "url": "https://github.com/itsaky/openjdk-17-android/releases/download/01-01-2022/jdk17-arm64.tar.xz",
        "sha256": None,  # Upstream release predates GitHub asset digests: record downloaded SHA-256.
        "tool_ids": ["openjdk-17"],
        "version": "17 (Android ARM64, 2022 upstream build)",
    },
    {
        "filename": "build-tools-34.0.4-aarch64.tar.xz",
        "url": "https://github.com/AndroidIDEOfficial/androidide-tools/releases/download/v34.0.4/build-tools-34.0.4-aarch64.tar.xz",
        "sha256": None,  # Upstream release predates GitHub asset digests: record downloaded SHA-256.
        "tool_ids": ["aapt2-zipalign", "d8-apksigner"],
        "version": "34.0.4 (Android ARM64)",
    },
    {
        "filename": "aapt2-arm64-v8a",
        "url": "https://github.com/AndroidIDE-Dev/platform-tools/releases/download/v35.0.2/aapt2-arm64-v8a",
        "sha256": "db737b3bbee99dd8a9e56108cc05d032597874d3f8ac557a69f3c5de5efaf57f",
        "tool_ids": [],  # Supplemental binary, not the combined AAPT2+Zipalign package.
        "version": "35.0.2 (Android ARM64)",
    },
]

def download(source):
    DIST.mkdir(exist_ok=True)
    name = source["filename"]
    url = source["url"]
    print(f"Fetching {name} from {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "PythonEyeToolchain/1.0"})
    target = DIST / name
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(req, timeout=90) as response, target.open("wb") as fp:
        if not response.geturl().startswith("https://"):
            raise RuntimeError(f"Insecure redirect for {name}")
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            size += len(block)
            if size > MAX_SIZE:
                raise RuntimeError(f"Too large: {name}")
            fp.write(block)
            digest.update(block)
    sha = digest.hexdigest()
    if not size:
        raise RuntimeError(f"Empty download: {name}")
    if source["sha256"] and source["sha256"] != sha:
        target.unlink(missing_ok=True)
        raise RuntimeError(f"Checksum mismatch for {name}: got {sha}")
    print(f"Verified {name}: {size} bytes, sha256={sha}", flush=True)
    return {"file": name, "sha256": sha, "size": size, "source_url": url,
            "upstream_digest_pinned": source["sha256"] is not None}

def run(*cmd):
    print(">", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)

def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    roles = {i["id"]: i for i in catalog["tools"]}
    results = []
    for src in SOURCES:
        result = download(src)
        results.append(result)
    (DIST / "SOURCE_SHA256SUMS.txt").write_text(
        "".join(f'{r["sha256"]}  {r["file"]}\n' for r in results),
        encoding="utf-8")
    (DIST / "PROVENANCE.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8")
    # Upload only after ALL archives are fetched successfully.
    exists = subprocess.run(["gh", "release", "view", TAG, "--repo", REPO],
                            capture_output=True).returncode == 0
    if not exists:
        run("gh", "release", "create", TAG, "--repo", REPO,
            "--title", "Python Eye IDE: real upstream toolchain packages",
            "--notes", "Upstream Android ARM64 binaries and Gradle distribution. See PROVENANCE.json and SOURCE_SHA256SUMS.txt. **NOT YET DEVICE-TESTED IN PYTHON EYE IDE.**")
    for f in list(DIST.iterdir()):
        run("gh", "release", "upload", TAG, str(f), "--clobber", "--repo", REPO)
    # Only now advertise working download URLs; installation remains unverified.
    for src in SOURCES:
        file_result = next(r for r in results if r["file"] == src["filename"])
        for tool_id in src["tool_ids"]:
            item = roles[tool_id]
            item.update({
                "version": src["version"],
                "published": True,
                "status": "published_unverified_on_device",
                "url": f"https://github.com/{REPO}/releases/download/{TAG}/{src['filename']}",
                "sha256": file_result["sha256"],
                "source_url": src["url"],
                "verified_upstream_digest": bool(src["sha256"])
            })
    catalog["updated"] = "2026-11-18"
    catalog["notes"] = ("4 catalog entries have actual GitHub Release downloads, but Android device "
                        "installation and APK build remain unverified. 4 entries still unpublished. "
                        "Catalog schema compatibility with the app has not yet been checked.")
    CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    run("python", "scripts/validate_catalog.py")
    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run("git", "add", "tools.json")
    run("git", "commit", "-m", "Register real published Android ARM64 and Gradle assets")
    run("git", "push")
    print("All assets uploaded; tools.json updated.", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"BOOTSTRAP FAILED: {err}", file=sys.stderr)
        sys.exit(1)
