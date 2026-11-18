#!/usr/bin/env python3
"""Read-only inspection of ALL five published release archives (includes Bionic JDK17 tar.gz).

Downloads every file, checks real SHA-256 and file size, inventories the
required executables/JARs, and inspects ELF e_machine without executing code.
"""
import hashlib
import json
import os
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen
import zipfile

MAX_BYTES=230*1024*1024
CATALOG=Path("tools.json")
ARCHIVES={"zip":".zip","tar.xz":".tar.xz","tar.gz":".tar.gz"}

def download(url,target):
    h=hashlib.sha256()
    size=0
    with urlopen(Request(url,headers={"User-Agent":"PythonEyeToolchain-Audit/2.0"}),timeout=120) as response,target.open("wb") as file:
        if not response.geturl().startswith("https://"):
            raise ValueError("Non-HTTPS redirect")
        while True:
            part=response.read(1024*1024)
            if not part:break
            size+=len(part)
            if size>MAX_BYTES:raise ValueError("Archive unexpectedly large")
            h.update(part)
            file.write(part)
    return size,h.hexdigest()

def archive_files(path,fmt):
    if fmt=="zip":
        with zipfile.ZipFile(path) as z:
            if bad:=z.testzip(): raise ValueError(f"Bad ZIP entry: {bad}")
            return [name for name in z.namelist() if not name.endswith("/")]
    with tarfile.open(path, "r:gz" if fmt=="tar.gz" else "r:xz") as t:
        return [m.name for m in t if m.isfile()]

def small_entry(path,fmt,name):
    if fmt=="zip":
        with zipfile.ZipFile(path) as z:
            with z.open(name) as f:return f.read(64)
    with tarfile.open(path, "r:gz" if fmt=="tar.gz" else "r:xz") as t:
        m=t.getmember(name)
        with t.extractfile(m) as f:return f.read(64)

def elf_arch(data):
    if data[:4]!=b"\x7fELF" or len(data)<20:return "not_ELF"
    machine=int.from_bytes(data[18:20],"little")
    return {183:"aarch64",62:"x86_64",40:"arm32"}.get(machine,f"machine_{machine}")

def main():
    catalog=json.loads(CATALOG.read_text("utf-8"))
    published=[t for t in catalog["tools"] if t["published"]]
    results={}
    with TemporaryDirectory() as temp:
        for tool in published:
            fmt=tool["archive_format"]
            if fmt not in ARCHIVES:raise RuntimeError("Unsupported archive: "+fmt)
            name=tool["url"].rsplit("/",1)[-1]
            if not name.endswith(ARCHIVES[fmt]):raise ValueError("Archive extension mismatch")
            dest=Path(temp)/name
            if not dest.exists():
                count,sha=download(tool["url"],dest)
                print(f"Downloaded {name} ({count:,} bytes)",flush=True)
            else:
                b=dest.read_bytes()
                count,sha=len(b),hashlib.sha256(b).hexdigest()
            if sha!=tool["sha256"] or count!=tool["file_size_bytes"]:
                raise ValueError(f"{tool['id']}: SHA-256 / size does not match manifest")
            files=archive_files(dest,fmt)
            required=tool["install"]["required_paths"]
            matched={}
            for want in required:
                hits=[f for f in files if f==want or f.endswith("/"+want)]
                if not hits:raise ValueError(f"{tool['id']}: required file not found: {want}")
                matched[want]=hits[:3]
            probe_keys=["aapt2","zipalign","java","javac","adb"]
            elf={}
            for fname in files:
                if Path(fname).name in probe_keys:
                    elf[fname]=elf_arch(small_entry(dest,fmt,fname))
            for k in ["aapt2","zipalign"]:
                if tool["id"]=="aapt2-zipalign":
                    if not any(Path(n).name==k and arch=="aarch64" for n,arch in elf.items()):
                        raise ValueError(f"Invalid/non-ARM64 {k}: {elf}")
            if tool["id"]=="openjdk-17":
                if not any(Path(n).name=="java" and arch=="aarch64" for n,arch in elf.items()):
                    raise ValueError(f"No Android ARM64 Java ELF in JDK: {elf}")
            results[tool["id"]]={
                "asset":name,"sha256":sha,"size_bytes":count,
                "total_archive_files":len(files),"required_path_matches":matched,"elf_architectures":elf,
                "assessment":"SHA256, archive readability, required paths checked; not run on phone"
            }
            print("PASS",tool["id"],json.dumps(matched),flush=True)
    Path("archive_audit.json").write_text(json.dumps({
        "audit_version":2,
        "purpose":"Verified all five downloaded archives. This audit does NOT execute tools or test mobile APK build.",
        "catalog_architecture":"arm64-v8a",
        "tests":results,
        "phone_build_verified":False
    },indent=2)+"\n",encoding="utf-8")
    print("PASS: all five release archives have matching hashes and required contents.")

if __name__=="__main__":
    main()
