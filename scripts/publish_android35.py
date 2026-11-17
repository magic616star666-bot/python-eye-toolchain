#!/usr/bin/env python3
"""Import upstream Android ARM64 SDK tools 35.0.2 after verifying archive contents."""
import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

name="android-sdk-tools-static-aarch64.zip"
src="https://github.com/lzhiyong/android-sdk-tools/releases/download/35.0.2/"+name
repo=os.environ["GITHUB_REPOSITORY"]
dst=Path(name)
sha=hashlib.sha256()
size=0
with urlopen(Request(src,headers={"User-Agent":"PythonEyeToolchain/1.0"}),timeout=100) as r, dst.open("wb") as out:
    if not r.geturl().startswith("https://"):
        raise RuntimeError("Insecure redirect")
    while True:
        block=r.read(1024*1024)
        if not block:
            break
        size+=len(block)
        if size > 80*1024*1024:
            raise RuntimeError("Size unexpectedly large")
        sha.update(block)
        out.write(block)
if not zipfile.is_zipfile(dst):
    raise RuntimeError("Upstream archive not a ZIP")
with zipfile.ZipFile(dst) as f:
    files=[x.filename for x in f.infolist() if not x.is_dir()]
    basenames={Path(x).name for x in files}
    print("Zip entries:",files[:70],flush=True)
    required={"aapt2","zipalign"}
    if not required.issubset(basenames):
        raise RuntimeError("Required Android tools not present: "+str(required-basenames))
print("Downloaded file verified by SHA256",sha.hexdigest(),"bytes",size,flush=True)
subprocess.run(["gh","release","upload","toolchain-v1",str(dst),"--clobber","--repo",repo],check=True)
p=Path("tools.json")
data=json.loads(p.read_text(encoding="utf-8"))
for t in data["tools"]:
    if t["id"]=="aapt2-zipalign":
        t.update(version="35.0.2 (upstream Android ARM64 static tools)",
                 published=True,
                 status="published_unverified_on_device",
                 url=f"https://github.com/{repo}/releases/download/toolchain-v1/{name}",
                 sha256=sha.hexdigest(),source_url=src,
                 verified_upstream_digest=False)
        break
else:
    raise RuntimeError("No catalog entry")
p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
subprocess.run(["python","scripts/validate_catalog.py"],check=True)
subprocess.run(["git","config","user.name","github-actions[bot]"],check=True)
subprocess.run(["git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],check=True)
subprocess.run(["git","add","tools.json"],check=True)
subprocess.run(["git","commit","-m","Upgrade AAPT2 and Zipalign to Android ARM64 35.0.2"],check=True)
subprocess.run(["git","push"],check=True)
