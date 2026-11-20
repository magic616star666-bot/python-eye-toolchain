#!/usr/bin/env python3
"""Regenerate the official metadata-only version list, without mirroring binaries."""
import json, re, urllib.request, hashlib, xml.etree.ElementTree as ET
from pathlib import Path
GRADLE="https://services.gradle.org/versions/all"
SDK="https://dl.google.com/android/repository/repository2-1.xml"
def get(url, cap):
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"PythonEyeIDE-index/1.0"}),timeout=50) as r:
        b=r.read(cap+1)
        if len(b)>cap: raise ValueError("Oversize official metadata")
        return b
def gradle_parse(b):
    found={}
    for a in json.loads(b):
        v=str(a.get("version",""))
        u=a.get("downloadUrl","")
        s=str(a.get("checksum","")).lower()
        if (re.fullmatch(r"(?:7\.[3-6]|8\.\d{1,2}|9\.\d{1,2})(?:\.\d{1,2})?",v) and a.get("final") is True
          and a.get("released") is True and not a.get("broken")
          and u==f"https://services.gradle.org/distributions/gradle-{v}-bin.zip"
          and re.fullmatch(r"[0-9a-f]{64}",s)):
            found[v]={"id":f"gradle-{v}","version":v,"url":u,"sha256":s,"phone_verified":False}
    return list(found.values())
def tag(x): return x.tag.rsplit("}",1)[-1]
def sdk_parse(b):
    found={}
    root=ET.fromstring(b)
    for pkg in root.iter():
        if tag(pkg)!="remotePackage":continue
        path=pkg.get("path","")
        m=re.fullmatch(r"platforms;android-(\d{2})",path)
        if not m or not 21<=int(m.group(1))<=40:continue
        for a in pkg.iter():
            if tag(a)!="complete":continue
            data={tag(c):c for c in a}
            h=data.get("checksum")
            sha=(h.text or "").strip().lower() if h is not None and h.get("type","").lower() in ("","sha1") else ""
            name=(data["url"].text or "").strip() if "url" in data else ""
            size=(data["size"].text or "").strip() if "size" in data else ""
            if (re.fullmatch(r"[0-9a-f]{40}",sha) and re.fullmatch(r"platform-[A-Za-z0-9._+-]+\.zip",name)
               and size.isdecimal() and 1024<=int(size)<=1500000000):
                api=int(m.group(1))
                found[api]={"id":f"android-sdk-{api}","api":api,
                            "url":"https://dl.google.com/android/repository/"+name,
                            "sha1":sha,"file_size_bytes":int(size),
                            "license_approval_required":True,"phone_verified":False}
    return [found[k] for k in sorted(found)]
def main():
    raw_g=get(GRADLE,3500000);raw_s=get(SDK,25000000)
    gv=gradle_parse(raw_g);sv=sdk_parse(raw_s)
    if len(gv)<25 or len(sv)<10:raise ValueError(f"Suspicious catalogue: {len(gv)} Gradle, {len(sv)} SDK")
    output={"schema_version":1,"catalogue_only":True,"downloaded_binaries":0,"target":"Android ARM64/Bionic",
     "sources":{"gradle":GRADLE,"sdk":SDK},"source_sha256":{"gradle":hashlib.sha256(raw_g).hexdigest(),"sdk":hashlib.sha256(raw_s).hexdigest()},
     "gradle_count":len(gv),"sdk_count":len(sv),"gradle":gv,"sdk_platforms":sv,
     "note":"Gradle official SHA-256. Google Android SDK official SHA-1 where published; confirm checksum over HTTPS. Device CLI and APK builds require on-phone testing."}
    p=Path("toolchains/official-on-demand.json")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(output,indent=2)+"\n")
    print("Indexed",len(gv),"Gradle and",len(sv),"Android SDK releases")
if __name__=="__main__":main()
