#!/usr/bin/env python3
"""Python Eye IDE: official managed Android tool installer + readiness checks.

This does NOT mirror the Google SDK or Maven plugin files.
It invokes the device/host's real SDK Manager and Gradle executables.

On-device use is possible only after the IDE exposes a working Android-compatible
JDK, Gradle, SDK command-line tools, environment and filesystem. A green switch
must not be set by metadata alone; confirm the command exit status.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

COMPONENTS=("android-sdk-36","android-gradle-plugin","chaquopy-build")
VERSION={"sdk":"36","build_tools":"35.0.0","agp":"8.11.0","chaquopy":"17.2.0","gradle":"8.14.3","java":"17"}
ROOT=Path(__file__).resolve().parents[1]
SMOKE=ROOT/"apk-smoke-test"

def executable(value,env):
    if value:
        path=Path(value).expanduser()
        if path.is_file():
            return str(path.resolve())
        resolved=shutil.which(value,path=env.get("PATH"))
        return resolved
    return None

def locate_java(env):
    j=executable(env.get("JAVA_BIN"),env)
    if j:return j
    if env.get("JAVA_HOME"):
        j=executable(str(Path(env["JAVA_HOME"])/"bin"/"java"),env)
        if j:return j
    return executable("java",env)

def locate_gradle(env):
    g=executable(env.get("GRADLE_BIN"),env)
    if g:return g
    if env.get("GRADLE_HOME"):
        g=executable(str(Path(env["GRADLE_HOME"])/"bin"/"gradle"),env)
        if g:return g
    return executable("gradle",env)

def locate_sdkmanager(env,sdk_root):
    v=executable(env.get("SDKMANAGER_BIN"),env)
    if v:return v
    candidates=[
        sdk_root/"cmdline-tools"/"latest"/"bin"/"sdkmanager",
        sdk_root/"cmdline-tools"/"bin"/"sdkmanager",
        sdk_root/"cmdline-tools"/"16.0"/"bin"/"sdkmanager",
        sdk_root/"tools"/"bin"/"sdkmanager"
    ]
    for c in candidates:
        if c.is_file():return str(c)
    return executable("sdkmanager",env)

def run(command,*,env,cwd=None,input_text=None,timeout=1800):
    argv=[str(x) for x in command]
    if not argv:
        raise RuntimeError("Missing command")
    p=subprocess.run(argv,cwd=cwd,env=env,input=input_text,text=True,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                     timeout=timeout,check=False)
    print(p.stdout[-12000:],file=sys.stderr)
    if p.returncode:
        raise RuntimeError(f"{Path(argv[0]).name} exited {p.returncode}")
    return p.stdout

def sdk_root_from_args(args,env):
    raw=args.sdk_root or env.get("ANDROID_HOME") or env.get("ANDROID_SDK_ROOT")
    if not raw:
        raise RuntimeError("Set --sdk-root or ANDROID_HOME to the IDE-writable Android SDK folder")
    return Path(raw).expanduser().resolve()

def check_sdk(sdk):
    platform=sdk/"platforms"/"android-36"/"android.jar"
    # D8/apksigner 34.x alone doesn't satisfy AGP 8.11:
    required=sdk/"build-tools"/"35.0.0"/"source.properties"
    return {
        "id":"android-sdk-36",
        "ready":platform.is_file() and required.is_file(),
        "platform36_android_jar":platform.is_file(),
        "build_tools_35_source_properties":required.is_file(),
        "requires_device_arm64_build_tools_execution_test":True
    }

def status(args,env):
    sdk=sdk_root_from_args(args,env)
    sdk_status=check_sdk(sdk)
    # Presence of Gradle in PATH or cache does not prove the plugins resolved:
    agp={"id":"android-gradle-plugin","ready":False,
         "requires":"Successful :app:assembleDebug with plugin com.android.application 8.11.0"}
    cha={"id":"chaquopy-build","ready":False,
         "requires":"Successful :app:assembleDebug with plugin com.chaquo.python 17.2.0"}
    marker=Path(args.state_dir or sdk/".python-eye-toolchain")/"last_successful_build.json"
    if marker.is_file() and sdk_status["ready"]:
        try:
            result=json.loads(marker.read_text("utf-8"))
            if (result.get("sdk_root")==str(sdk) and
                result.get("agp")=="8.11.0" and
                result.get("chaquopy")=="17.2.0" and
                result.get("java")=="17" and
                result.get("gradle")=="8.14.3" and
                result.get("verified_by_real_build") is True):
                agp["ready"]=True
                cha["ready"]=True
        except (ValueError,OSError):
            pass
    return {"sdk_root":str(sdk),"components":[sdk_status,agp,cha],
            "note":"Only a completed local Gradle build records managed plugin readiness; CI proof applies to GitHub runner only."}

def main(args):
    env=os.environ.copy()
    sdk=sdk_root_from_args(args,env)
    env["ANDROID_HOME"]=str(sdk)
    env["ANDROID_SDK_ROOT"]=str(sdk)
    if args.action=="status":
        print(json.dumps(status(args,env),indent=2))
        return
    if not locate_java(env):
        raise RuntimeError("Android-compatible Java 17 not available; install JDK first")
    if args.action in ("sdk","all"):
        manager=locate_sdkmanager(env,sdk)
        if not manager:
            raise RuntimeError("Android sdkmanager not found: install official command-line tools")
        sdk.mkdir(parents=True,exist_ok=True)
        if args.accept_sdk_license:
            # Explicit user opt-in: sdkmanager requires input 'y' for each license.
            run([manager,"--sdk_root="+str(sdk),"--licenses"],env=env,
                input_text="y\n"*100,timeout=600)
        elif not check_sdk(sdk)["ready"]:
            raise RuntimeError("SDK license consent required. Review Google's SDK license and rerun with --accept-sdk-license after user approves.")
        run([manager,"--sdk_root="+str(sdk),"--install",
             "platforms;android-36","build-tools;35.0.0"],env=env)
        result=check_sdk(sdk)
        if not result["ready"]:
            raise RuntimeError("SDK installed but android.jar or Build Tools 35.0.0 missing")
    if args.action in ("plugins","all"):
        if not check_sdk(sdk)["ready"]:
            raise RuntimeError("Install Android SDK Platform 36 and Build Tools 35.0.0 first")
        gradle=locate_gradle(env)
        if not gradle:
            raise RuntimeError("Gradle 8.14.3 not found; set GRADLE_BIN or PATH")
        if not SMOKE.is_dir():
            raise RuntimeError("apk-smoke-test project is missing. Keep it beside managed_installer.py")
        # A successful build proves dependency resolution, but only for the
        # detected Java and Gradle versions. Never stamp readiness for unknown ones.
        java=locate_java(env)
        java_info=run([java,"-version"],env=env,timeout=30)
        gradle_info=run([gradle,"--version"],env=env,timeout=60)
        if not any(x in java_info for x in ('version "17.', 'openjdk 17.', 'java 17.')):
            raise RuntimeError("Expected JDK 17; actual Java version must be checked")
        if "Gradle 8.14.3" not in gradle_info:
            raise RuntimeError("Expected Gradle 8.14.3; actual Gradle version must be checked")
        # Actually compiles an Android APK, so transitive Maven dependencies,
        # Chaquopy Python runtime, and AGP have all been resolved.
        run([gradle,"--no-daemon",":app:assembleDebug"],env=env,cwd=SMOKE,timeout=1800)
        apk=SMOKE/"app"/"build"/"outputs"/"apk"/"debug"/"app-debug.apk"
        if not apk.is_file() or apk.stat().st_size<1_000_000:
            raise RuntimeError("Gradle finished without producing a real debug APK")
        state=Path(args.state_dir or sdk/".python-eye-toolchain")
        state.mkdir(parents=True,exist_ok=True)
        out={
            "sdk_root":str(sdk),"java":"17","gradle":"8.14.3","agp":"8.11.0",
            "chaquopy":"17.2.0","verified_by_real_build":True,
            "apk_size_bytes":apk.stat().st_size
        }
        (state/"last_successful_build.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(status(args,env),indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("status","sdk","plugins","all"),
                   help="status/SDK install/plugin resolution by actual APK compilation")
    p.add_argument("--sdk-root",help="IDE-writable SDK root, defaults to ANDROID_HOME")
    p.add_argument("--state-dir",help="IDE-writable directory for verified install state")
    p.add_argument("--accept-sdk-license",action="store_true",
                   help="Only after the user has reviewed and explicitly accepted Google's SDK license")
    try:
        main(p.parse_args())
    except Exception as e:
        print(json.dumps({"ok":False,"error":str(e)}),file=sys.stderr)
        sys.exit(1)
