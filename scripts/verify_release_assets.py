#!/usr/bin/env python3
"""Validate catalog against *actual* GitHub release metadata and SHA-256 digests.

No release archives need downloading, and this cannot mark any tool as installed.
"""
import json
import os
from pathlib import Path
import urllib.request

REPOSITORY="magic616star666-bot/python-eye-toolchain"
TAGS=("toolchain-v1","jdk-awt-v1")
BASE=f"https://github.com/{REPOSITORY}/releases/download/"

def run():
    headers={"Accept":"application/vnd.github+json", "User-Agent":"PythonEyeToolchain-Integrity-Check"}
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"]="Bearer "+os.environ["GITHUB_TOKEN"]
    assets={}
    for tag in TAGS:
        api=f"https://api.github.com/repos/{REPOSITORY}/releases/tags/{tag}"
        with urllib.request.urlopen(urllib.request.Request(api,headers=headers),timeout=30) as response:
            for asset in json.load(response)["assets"]:
                assets[BASE+tag+"/"+asset["name"]]=asset
    data=json.loads(Path("tools.json").read_text("utf-8"))
    expected={"openjdk-17","gradle","aapt2-zipalign","d8-apksigner","kotlin-compiler"}
    seen=set()
    for tool in data["tools"]:
        if not tool["published"]:
            continue
        tool_id=tool["id"]
        assert tool_id in expected, f"Unexpected downloadable id: {tool_id}"
        seen.add(tool_id)
        assert tool["url"].startswith(BASE), f"{tool_id}: not our Release URL"
        name=tool["url"][len(BASE):]
        assert tool["url"] in assets, f"{tool_id}: asset {name} not found"
        asset=assets[tool["url"]]
        assert tool["file_size_bytes"]==asset["size"], f"{tool_id}: wrong file size"
        assert asset["digest"]==f"sha256:{tool['sha256']}", f"{tool_id}: SHA-256 mismatch with GitHub"
        print(f"PASS {tool_id}: {name} ({asset['size']:,} bytes), digest verified")
    assert seen==expected, f"Published tools mismatch: {seen}"
    print("PASS: all 5 downloadable catalog entries match live GitHub release assets.")
    print("NOTE: checksum metadata check is NOT an install or binary execution test.")

if __name__=="__main__":
    run()
