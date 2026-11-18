#!/usr/bin/env python3
"""Sanity check that the CI APK actually contains Android + ARM64 Python runtime."""
import sys
import zipfile
from pathlib import Path

apk=Path(sys.argv[1] if len(sys.argv)>1 else "apk-smoke-test/app/build/outputs/apk/debug/app-debug.apk")
if not apk.is_file() or apk.stat().st_size<1024*1024:
    raise SystemExit(f"FAIL: APK missing or unexpectedly small: {apk}")
with zipfile.ZipFile(apk) as z:
    bad=z.testzip()
    if bad:
        raise SystemExit(f"FAIL: corrupt ZIP entry {bad}")
    names=z.namelist()
    required={
        "AndroidManifest.xml": "Android manifest",
        "classes.dex": "compiled Java/Android bridge"
    }
    for file,description in required.items():
        if file not in names:
            raise SystemExit(f"FAIL: {description} missing ({file})")
    arm64=[name for name in names if name.startswith("lib/arm64-v8a/") and name.endswith(".so")]
    python_libs=[name for name in arm64 if "python" in name.lower()]
    if not python_libs:
        raise SystemExit("FAIL: no ARM64 Python shared library bundled")
    foreign=[name for name in names if name.startswith(("lib/x86/","lib/x86_64/","lib/armeabi-v7a/"))]
    if foreign:
        raise SystemExit(f"FAIL: unexpected other ABI native libraries: {foreign[:8]}")
    print("PASS: AndroidManifest.xml and classes.dex present")
    print(f"PASS: {len(arm64)} ARM64 native libraries, Python runtime present: {python_libs[:4]}")
    print("INFO: Chaquopy assets:",[x for x in names if "chaquopy" in x.lower()][:10])
    print("NOTE: Validates packaging in GitHub CI, not runtime execution on user's phone.")
