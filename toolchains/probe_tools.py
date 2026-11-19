#!/usr/bin/env python3
"""Read-only Python Eye toolchain doctor.

Only successful *local executable probes* count as ready. Catalog entries,
download links, and GitHub CI runs never count as installed on a phone.
No network activity, APK execution, downloads, or mutations are performed.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

BASE = Path(__file__).resolve().parents[1]
CODES = {
    "openjdk-17", "gradle", "android-sdk-36", "aapt2-zipalign",
    "d8-apksigner", "kotlin-compiler", "android-gradle-plugin", "chaquopy-build"
}
READY = "ready_local_probe_passed"
MISSING = "missing_or_probe_failed"
MANAGED = "requires_real_gradle_apk_build"


def android_host() -> bool:
    return bool(os.environ.get("ANDROID_ROOT") or sys.platform == "android"
                or hasattr(sys, "getandroidapilevel"))


def exe(name: str, *, env: str = "", extra: list[Path] | None = None) -> str | None:
    found = os.environ.get(env) if env else None
    if found and Path(found).is_file():
        return found
    for p in extra or []:
        if p.is_file():
            return str(p)
    return shutil.which(name)


def probe(command: list[str], *, contains: str | None = None, timeout: int = 25) -> dict:
    if not command or not command[0]:
        return {"ok": False, "detail": "executable not installed"}
    try:
        done = subprocess.run(command, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, errors="replace", timeout=timeout, check=False)
        output = done.stdout[-2500:]
        ok = done.returncode == 0 and (contains is None or contains.lower() in output.lower())
        return {"ok": ok, "exit_code": done.returncode,
                "detail": output.strip()[:350] if output.strip() else "(no output)"}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "detail": str(exc)[:350]}


def java_major(text: str) -> int | None:
    match = re.search(r'(?:openjdk|java) version\s+"?(1\.)?(\d+)', text, re.I)
    if match:
        return int(match.group(2))
    match = re.search(r"\bopenjdk\s+(\d+)\.", text, re.I)
    if match:
        return int(match.group(1))
    return None


def record(tool_id: str, result: dict, *, prerequisite: str = "", evidence: str = "local-process-exit") -> dict:
    return {"id": tool_id, "ready": bool(result.get("ok")),
            "status": READY if result.get("ok") else MISSING,
            "evidence": evidence if result.get("ok") else "none",
            "prerequisite": prerequisite, "probe": result}


def java_at_major(major: int) -> dict:
    home = os.environ.get(f"JAVA{major}_HOME")
    paths = [Path(home) / "bin/java"] if home else []
    if major == 17:
        home = os.environ.get("JAVA_HOME")
        if home:
            paths.append(Path(home) / "bin/java")
    tool = exe("java", env="JAVA_BIN" if major == 17 else "", extra=paths)
    status = probe([tool, "-version"] if tool else [])
    actual = java_major(status.get("detail", ""))
    status["detected_major"] = actual
    status["ok"] = status.get("ok", False) and actual == major
    return record(f"jdk-{major}" if major != 17 else "openjdk-17", status,
                  prerequisite=f"Android-compatible JDK {major} for on-phone builds")


def check_sdk(sdk: Path) -> dict[str, dict]:
    result = {}
    jar = sdk / "platforms/android-36/android.jar"
    result["android-sdk-36"] = record("android-sdk-36", {"ok": jar.is_file() and jar.stat().st_size > 1024 if jar.is_file() else False, "detail": str(jar)}, evidence="sdk-android-jar-exists")
    jarlist = list((sdk / "platforms").glob("android-*/android.jar")) if (sdk / "platforms").is_dir() else []
    result["android-sdk-platforms"] = record("android-sdk-platforms", {"ok": any(p.stat().st_size > 1024 for p in jarlist), "detail": ", ".join(p.parent.name for p in jarlist) or "none"}, evidence="sdk-platform-files-present")
    bt = sdk / "build-tools/35.0.0"
    aapt = exe("aapt2", env="AAPT2_BIN", extra=[bt / "aapt2"])
    aapt_status = probe([aapt, "version"] if aapt else [])
    align = exe("zipalign", env="ZIPALIGN_BIN", extra=[bt / "zipalign"])
    # zipalign -h may exit 1 while printing useful help, so verify both the executable
    # and its actual invocation response, not just an expected exit 0.
    zip_status = probe([align, "-h"] if align else [])
    zip_status["ok"] = bool(align and "Zip alignment utility" in zip_status.get("detail", ""))
    result["aapt2-zipalign"] = record("aapt2-zipalign", {"ok": aapt_status["ok"] and zip_status["ok"], "detail": {"aapt2": aapt_status, "zipalign": zip_status}})
    btp = (bt / "source.properties").is_file()
    result["android-build-tools"] = record("android-build-tools", {"ok": btp and aapt_status["ok"], "detail": f"35.0.0 source.properties={btp}; aapt2={aapt_status['ok']}"})
    adb = exe("adb", env="ADB_BIN", extra=[sdk / "platform-tools/adb"])
    result["android-platform-tools"] = record("android-platform-tools", probe([adb, "version"] if adb else []))
    manager = exe("sdkmanager", env="SDKMANAGER_BIN",
                  extra=[sdk / "cmdline-tools/latest/bin/sdkmanager",
                         sdk / "cmdline-tools/bin/sdkmanager"])
    result["android-cmdline-tools"] = record("android-cmdline-tools", probe([manager, "--version"] if manager else [], timeout=40))
    ndklist = list((sdk / "ndk").glob("*/toolchains/llvm/prebuilt/*/bin/clang")) if (sdk / "ndk").is_dir() else []
    ndk = exe("clang", env="NDK_CLANG_BIN", extra=ndklist)
    result["android-ndk"] = record("android-ndk", probe([ndk, "--version"] if ndk else [], contains="clang"))
    cmakes = list((sdk / "cmake").glob("*/bin/cmake")) if (sdk / "cmake").is_dir() else []
    cmake = exe("cmake", env="CMAKE_BIN", extra=cmakes)
    result["android-cmake"] = record("android-cmake", probe([cmake, "--version"] if cmake else [], contains="cmake"))
    d8 = exe("d8", env="D8_BIN", extra=[bt / "d8"])
    d8_test = probe([d8, "--version"] if d8 else [])
    apk = exe("apksigner", env="APKSIGNER_BIN", extra=[bt / "apksigner"])
    apk_test = probe([apk, "version"] if apk else [])
    result["d8-apksigner"] = record("d8-apksigner", {"ok": d8_test["ok"] and apk_test["ok"], "detail": {"d8": d8_test, "apksigner": apk_test}})
    result["r8-d8"] = record("r8-d8", d8_test, prerequisite="R8 separately supplied by Android Gradle Plugin")
    result["apk-signing"] = record("apk-signing", {"ok": apk_test["ok"] and zip_status["ok"], "detail": {"apksigner": apk_test, "zipalign": zip_status}})
    return result


def doctor(sdk_root: Path) -> dict:
    sdk = sdk_root.resolve()
    result = {i["id"]: i for i in [java_at_major(n) for n in (8, 11, 17, 21)]}
    result.update(check_sdk(sdk))
    gradle = exe("gradle", env="GRADLE_BIN",
                 extra=[Path(os.environ["GRADLE_HOME"]) / "bin/gradle"] if "GRADLE_HOME" in os.environ else [])
    gradle_res = probe([gradle, "--version"] if gradle else [], contains="Gradle", timeout=60)
    result["gradle"] = record("gradle", gradle_res)
    result["gradle-wrapper"] = record("gradle-wrapper", {"ok": False, "detail": "per-project wrapper: never executed by global audit"},
                                      prerequisite="project wrapper scripts must be reviewed before execution")
    kotlinc = exe("kotlinc", env="KOTLINC_BIN")
    result["kotlin-compiler"] = record("kotlin-compiler", probe([kotlinc, "-version"] if kotlinc else [], contains="kotlinc"))
    flutter = exe("flutter", env="FLUTTER_BIN")
    result["flutter-dart"] = record("flutter-dart", probe([flutter, "--version"] if flutter else [], contains="Flutter", timeout=60))
    buildozer = exe("buildozer", env="BUILDOZER_BIN")
    result["buildozer"] = record("buildozer", probe([buildozer, "--version"] if buildozer else [], timeout=30))
    p4a = exe("p4a", env="P4A_BIN")
    result["python-for-android"] = record("python-for-android", probe([p4a, "--version"] if p4a else [], timeout=30))
    # Native project Gradle plugins are not "installed" merely because a jar is in cache.
    for tool_id, detail in [
        ("android-gradle-plugin", "verify successful Gradle assembleDebug in target project"),
        ("chaquopy-build", "verify successful Python Android APK build"),
        ("android-gradle-plugin-resolver", "verify AGP project build on same host"),
        ("kotlin-gradle-plugin-resolver", "verify Kotlin Android project build on same host"),
        ("android-lint", "run :app:lintDebug on same host"),
        ("bundletool", "run official bundletool JAR and verify AAB if needed"),
        ("chaquopy-python", "run Chaquopy Android APK build on same host"),
    ]:
        result[tool_id] = {"id": tool_id, "ready": False, "status": MANAGED,
                           "prerequisite": detail, "evidence": "none"}
    return {
        "host_os": platform.system(),
        "host_arch": platform.machine(),
        "android_bionic_host": android_host(),
        "sdk_root": str(sdk),
        "ready_count": sum(bool(x["ready"]) for x in result.values()),
        "tools": sorted(result.values(), key=lambda row: row["id"]),
        "notice": "Readiness is local to this process host; GitHub CI does not prove Android phone compatibility.",
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Read-only executable toolchain doctor")
    p.add_argument("--sdk-root", type=Path, default=Path(
        os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or "./android-sdk"))
    p.add_argument("--only-ready", action="store_true")
    args = p.parse_args()
    data = doctor(args.sdk_root)
    if args.only_ready:
        data["tools"] = [row for row in data["tools"] if row["ready"]]
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
