#!/usr/bin/env python3
"""Audit the published Android ARM64 archives; do NOT execute foreign binaries on the CI host."""
import hashlib
import io
import json
import struct
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ASSETS = {
 "35": "https://github.com/magic616star666-bot/python-eye-toolchain/releases/download/toolchain-v1/android-sdk-tools-static-aarch64.zip",
 "34": "https://github.com/magic616star666-bot/python-eye-toolchain/releases/download/toolchain-v1/build-tools-34.0.4-aarch64.tar.xz",
}
catalog=json.loads(Path("tools.json").read_text(encoding="utf-8"))
by_id={t["id"]:t for t in catalog["tools"]}
def fetch(url, max_size=90*1024*1024):
    request=urllib.request.Request(url,headers={"User-Agent":"PythonEyeToolchain-Audit/1.0"})
    buf=io.BytesIO()
    with urllib.request.urlopen(request,timeout=120) as r:
        while True:
            piece=r.read(1024*1024)
            if not piece:break
            if buf.tell()+len(piece)>max_size:raise RuntimeError("Asset too large")
            buf.write(piece)
    return buf.getvalue()
def binary_arch(data):
    if data.startswith(b"\x7fELF") and len(data)>20:
        # e_machine is 2 bytes at offset 18. 183 = AArch64
        return "ELF-aarch64" if int.from_bytes(data[18:20],"little")==183 else "ELF-other"
    if data.startswith(b"PK"):return "ZIP"
    if data.startswith(b"#!"):return "script"
    if data.startswith(b"\xca\xfe\xba\xbe"):return "class"
    return "other"
def check_archive(label, archive, expected):
    sha=hashlib.sha256(archive).hexdigest()
    if sha!=expected:raise RuntimeError(f"{label} checksum mismatch {sha} != {expected}")
    contents={}
    if label=="35":
        with zipfile.ZipFile(io.BytesIO(archive)) as f:
            for p in f.infolist():
                if p.is_dir():continue
                contents[p.filename]=f.read(p)
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:xz") as f:
            for p in f:
                if p.isfile():
                    if p.size>40*1024*1024:continue
                    contents[p.name]=f.extractfile(p).read()
    names=sorted(contents)
    matches={key:[n for n in names if Path(n).name==key] for key in ["aapt2","zipalign","d8","d8.jar","apksigner","apksigner.jar","source.properties","dx","lib64"]}
    relevant={name:binary_arch(contents[name]) for name in names if Path(name).name in ["aapt2","zipalign","d8","apksigner"]}
    return {"archive":label,"sha256":sha,"files_count":len(names),"matches":matches,"executable_architecture":relevant,"example_paths":names[:18]}
archive35=fetch(ASSETS["35"])
archive34=fetch(ASSETS["34"])
report={
 "purpose":"Package contents inventory, not proof that installed ARM64 Android build works",
 "tests":{
  "35":check_archive("35",archive35,by_id["aapt2-zipalign"]["sha256"]),
  "34":check_archive("34",archive34,by_id["d8-apksigner"]["sha256"])
 },
 "catalog_duplicates_risk":"Two separate catalog entries reference different Android Build Tools generation; avoid intermixing 34 and 35 host binaries.",
 "android_app_catalog_reader_source_available":False
}
Path("archive_audit.json").write_text(json.dumps(report,indent=2)+"\n")
for label,entry in report["tests"].items():
    print("ARCHIVE",label,"count",entry["files_count"])
    print("MATCHES",entry["matches"])
    print("ELF",entry["executable_architecture"])
