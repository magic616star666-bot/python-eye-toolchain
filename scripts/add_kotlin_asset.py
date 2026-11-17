#!/usr/bin/env python3
"""Publish JetBrains official JVM Kotlin compiler distribution."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.request import Request, urlopen

repo = os.environ["GITHUB_REPOSITORY"]
name = "kotlin-compiler-2.1.20.zip"
url = "https://github.com/JetBrains/kotlin/releases/download/v2.1.20/" + name
sha_url = url + ".sha256"
with urlopen(Request(sha_url, headers={"User-Agent":"PythonEyeToolchain/1.0"}), timeout=60) as r:
    expected = r.read(512).decode("ascii").strip().split()[0].lower()
if not re.fullmatch(r"[0-9a-f]{64}", expected):
    raise RuntimeError("JetBrains SHA-256 is malformed")
target = Path(name)
sha = hashlib.sha256()
count = 0
with urlopen(Request(url, headers={"User-Agent":"PythonEyeToolchain/1.0"}), timeout=100) as r, target.open("wb") as out:
    while True:
        b=r.read(1024*1024)
        if not b:
            break
        count+=len(b)
        if count > 150*1024*1024:
            raise RuntimeError("Archive oversized")
        out.write(b)
        sha.update(b)
if sha.hexdigest()!=expected:
    target.unlink(missing_ok=True)
    raise RuntimeError("Kotlin archive SHA-256 mismatch")
print("Verified Kotlin from official JetBrains checksum: ",count,"bytes",expected,flush=True)
subprocess.run(["gh","release","upload","toolchain-v1",name,"--clobber","--repo",repo],check=True)
p=Path("tools.json")
data=json.loads(p.read_text(encoding="utf-8"))
for tool in data["tools"]:
    if tool["id"]=="kotlin-compiler":
        tool.update(version="2.1.20",published=True,status="published_unverified_on_device",
                    url=f"https://github.com/{repo}/releases/download/toolchain-v1/{name}",
                    sha256=expected,source_url=url,verified_upstream_digest=True)
        break
else:
    raise RuntimeError("Kotlin catalog entry missing")
data["notes"]="5 entries have real GitHub Release assets, installation not device-tested. SDK36, AGP and Chaquopy still require official package installation."
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
subprocess.run(["python","scripts/validate_catalog.py"],check=True)
subprocess.run(["git","config","user.name","github-actions[bot]"],check=True)
subprocess.run(["git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],check=True)
subprocess.run(["git","add","tools.json"],check=True)
subprocess.run(["git","commit","-m","Publish official JetBrains Kotlin compiler archive"],check=True)
subprocess.run(["git","push"],check=True)
