#!/usr/bin/env python3
"""Publish manually approved upstream archive with SHA-256 verification.

Only archive tool IDs are allowed. SDK Platform / Gradle plugins must stay managed.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, quote
from urllib.request import Request, urlopen

CATALOG=Path("tools.json")
DIST=Path("dist")
MAX_BYTES=2*1024*1024*1024-1024*1024

def inputs():
    tool_id=os.environ["TOOL_ID"].strip()
    version=os.environ["TOOL_VERSION"].strip()
    source=os.environ["SOURCE_URL"].strip()
    name=os.environ["ASSET_NAME"].strip()
    expected=os.environ["EXPECTED_SHA256"].lower().strip()
    if os.environ.get("TESTED_ON_ANDROID_ARM64")!="yes":
        raise ValueError("Approval required: phone-tested before publication")
    if os.environ.get("REDISTRIBUTION_RIGHTS_CHECKED")!="yes":
        raise ValueError("Approval required: redistribution license checked")
    if not re.fullmatch(r"[a-z0-9-]{1,80}",tool_id):
        raise ValueError("Invalid tool id")
    if not re.fullmatch(r"[A-Za-z0-9._+-]{1,80}",version):
        raise ValueError("Invalid version")
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,180}\.(?:zip|tar\.xz)",name):
        raise ValueError("File must be a plain zip or tar.xz filename")
    parsed=urlsplit(source)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username:
        raise ValueError("Direct public HTTPS link required")
    if not re.fullmatch(r"[a-f0-9]{64}",expected):
        raise ValueError("Expected SHA-256 must be 64 hex chars")
    catalog=json.loads(CATALOG.read_text(encoding="utf-8"))
    tools={t["id"]:t for t in catalog["tools"]}
    if tool_id not in tools:
        raise ValueError("Tool id does not exist")
    tool=tools[tool_id]
    if tool.get("install",{}).get("method")!="archive":
        raise ValueError("Managed SDK/Gradle plugins cannot be published as fake ZIP tools")
    fmt="zip" if name.endswith(".zip") else "tar.xz"
    return tool_id,version,source,name,expected,catalog,fmt

def download():
    tool_id,version,source,name,expected,_,_=inputs()
    DIST.mkdir(exist_ok=True)
    dst=DIST/name
    total=0
    sha=hashlib.sha256()
    req=Request(source,headers={"User-Agent":"PythonEyeToolchain-Publisher/2.0"})
    with urlopen(req,timeout=120) as resp,dst.open("wb") as output:
        if urlsplit(resp.geturl()).scheme!="https":
            raise ValueError("Redirected to non-HTTPS URL")
        while True:
            chunk=resp.read(1024*1024)
            if not chunk:break
            total+=len(chunk)
            if total>MAX_BYTES:raise ValueError("GitHub Release size limit exceeded")
            sha.update(chunk)
            output.write(chunk)
    if total<1024 or sha.hexdigest()!=expected:
        dst.unlink(missing_ok=True)
        raise ValueError("Empty/invalid archive or SHA-256 mismatch")
    if name.endswith(".zip"):
        import zipfile
        if not zipfile.is_zipfile(dst):raise ValueError("Downloaded file is not a ZIP")
    else:
        import tarfile
        if not tarfile.is_tarfile(dst):raise ValueError("Downloaded file is not a TAR")
    print(f"Verified {tool_id} {version}, {total} bytes, sha256 {expected}")

def mark():
    tool_id,version,source,name,expected,catalog,fmt=inputs()
    dst=DIST/name
    if not dst.is_file():raise ValueError("Verified local archive is missing")
    count=dst.stat().st_size
    digest=hashlib.file_digest(dst.open("rb"),"sha256").hexdigest()
    if digest!=expected:raise ValueError("Archive changed after download")
    repo=os.environ["GITHUB_REPOSITORY"]
    for tool in catalog["tools"]:
        if tool["id"]==tool_id:
            tool.update(
                version=version,
                published=True,
                catalog_state="downloadable_not_device_verified",
                status="published_unverified_on_device",
                url=f"https://github.com/{repo}/releases/download/toolchain-v1/{quote(name)}",
                sha256=expected,
                file_size_bytes=count,
                size_mb_estimate=round(count/1e6,1),
                archive_format=fmt,
                source_url=source,
                verified_upstream_digest=False,
                device_build_verified=False,
                note="Archive published after operator approval; on-phone test evidence is not recorded in catalog."
            )
            tool["install"]["device_verified"]=False
            break
    CATALOG.write_text(json.dumps(catalog,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Updated catalog download metadata: {tool_id}")

if __name__=="__main__":
    try:
        if len(sys.argv)!=2 or sys.argv[1] not in ("download","mark"):
            raise ValueError("Usage: publish_release.py download|mark")
        {"download":download,"mark":mark}[sys.argv[1]]()
    except Exception as e:
        print(f"BLOCKED: {e}",file=sys.stderr)
        sys.exit(1)
