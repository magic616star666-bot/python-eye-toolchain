#!/usr/bin/env python3
"""Inspect Google official SDK Platform 36 ZIP and record integrity metadata, without mirroring."""
import hashlib,io,json,os,pathlib,subprocess,urllib.request,zipfile
url="https://dl.google.com/android/repository/platform-36_r02.zip"
request=urllib.request.Request(url,headers={"User-Agent":"PythonEyeIDE-PlatformAudit/1.0"})
path=pathlib.Path("sdk36-original.zip")
sha=hashlib.sha256();size=0
with urllib.request.urlopen(request,timeout=120) as response,path.open("wb") as dst:
    if not response.geturl().startswith("https://"):raise RuntimeError("Insecure redirect")
    while True:
        chunk=response.read(1024*1024)
        if not chunk:break
        sha.update(chunk);size+=len(chunk)
        if size>200_000_000:raise RuntimeError("Unexpected archive size")
        dst.write(chunk)
with zipfile.ZipFile(path) as z:
    if corrupt:=z.testzip():raise RuntimeError("Corrupt ZIP: "+corrupt)
    names=z.namelist()
    jars=[n for n in names if n.endswith("/android.jar") or n=="android.jar"]
    if not jars:raise RuntimeError("Cannot find android.jar")
    roots=sorted(set(n.split("/")[0] for n in jars))
    r=roots[0]
    required=[n for n in names if n.endswith("/source.properties") or n=="source.properties"]
    result={"source_url":url,"sha256":sha.hexdigest(),"size_bytes":size,"archive_format":"zip","top_level_entries":sorted(set(n.split("/")[0] for n in names))[:18],"android_jar_paths":jars,"source_properties_paths":required,"file_count":len(names),"license_required":True,"redistributable_by_project":False,"tested_on_android_phone":False}
p=pathlib.Path("sdk36-official-package.json")
p.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2),flush=True)
subprocess.run(["git","config","user.name","github-actions[bot]"],check=True)
subprocess.run(["git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],check=True)
subprocess.run(["git","add",str(p)],check=True)
subprocess.run(["git","commit","-m","Record official Google Android SDK 36 checksum and ZIP root (no SDK mirroring)"],check=True)
subprocess.run(["git","push"],check=True)
