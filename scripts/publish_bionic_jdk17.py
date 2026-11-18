#!/usr/bin/env python3
"""Optional Android/Bionic OpenJDK 17 distribution for Python Eye IDE.

Integrity-checks the upstream GitHub Release SHA-256, ARM64 ELF, and bundle
layout before uploading to Python Eye. Does not claim on-device compatibility.
"""
import hashlib,io,json,os,pathlib,subprocess,tarfile,urllib.request
SOURCE="https://github.com/MobileStudio-AndroidIDE/MobileStudio_AndroidIDE/releases/download/MobileStudio-JDK17-Android-ARM64/jdk17-android.tar.gz"
ORIGINAL_SHA="81a99a2d2dad588e618cd1851e6b96cd3c044c236a1cd06956b19bd2530d54e5"
FILE=pathlib.Path("jdk17-android-bionic-17.0.11.tar.gz")
sha=hashlib.sha256();total=0
with urllib.request.urlopen(urllib.request.Request(SOURCE,headers={"User-Agent":"PythonEye/2.0"}),timeout=120) as src, FILE.open("wb") as out:
    while True:
        buf=src.read(1024*1024)
        if not buf:break
        total+=len(buf)
        if total>300*1024*1024:raise RuntimeError("Unexpected large JDK archive")
        sha.update(buf);out.write(buf)
digest=sha.hexdigest()
if digest!=ORIGINAL_SHA:raise RuntimeError(f"Upstream JDK SHA-256 mismatch: {digest}")
with tarfile.open(FILE,mode="r:gz") as archive:
    names=[m.name for m in archive.getmembers() if m.isfile()]
    java=[n for n in names if n.rstrip("/").endswith("/bin/java") or n=="bin/java"]
    javac=[n for n in names if n.rstrip("/").endswith("/bin/javac") or n=="bin/javac"]
    jvm=[n for n in names if n.endswith("/lib/server/libjvm.so")]
    if not java or not javac or not jvm:raise RuntimeError(f"Missing java/javac/libjvm: {java=} {javac=} {jvm=}")
    for f in [java[0],javac[0],jvm[0]]:
        member=archive.getmember(f)
        stream=archive.extractfile(member)
        head=stream.read(20)
        if head[:4]!=b"\x7fELF" or int.from_bytes(head[18:20],"little")!=183:
            raise RuntimeError(f"{f} is not ARM64 ELF")
    parts=java[0].removeprefix("./").split("/")
    root="/".join(parts[:-2])
    important={"java":java[0],"javac":javac[0],"libjvm":jvm[0]}
info={"source":SOURCE,"source_release_sha256":ORIGINAL_SHA,"github_asset_name":FILE.name,
      "file_size_bytes":total,"sha256":digest,"java_archive_root":root,
      "important_paths":important,"verified_aarch64_elf":True,
      "test_status":"Verified archive, not tested on user phone",
      "license_note":"OpenJDK GPLv2 with Classpath Exception; preserve upstream license notices."}
pathlib.Path("JDK17_BIONIC_AUDIT.json").write_text(json.dumps(info,indent=2)+"\n")
print(json.dumps(info,indent=2),flush=True)
subprocess.run(["gh","release","upload","toolchain-v1",FILE.name,"--repo",os.environ["GITHUB_REPOSITORY"]],check=True)
subprocess.run(["git","config","user.name","github-actions[bot]"],check=True)
subprocess.run(["git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],check=True)
subprocess.run(["git","add","JDK17_BIONIC_AUDIT.json"],check=True)
subprocess.run(["git","commit","-m","Audit optional Android Bionic JDK17 ARM64 release candidate"],check=True)
subprocess.run(["git","push"],check=True)
