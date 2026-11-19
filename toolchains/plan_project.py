#!/usr/bin/env python3
"""Plan exact Android build tool dependencies from a project or ZIP, safely.

Produces machine-readable recommendations for future Python Eye extension UI.
Does not execute project code, install packages, accept licenses, or build APKs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import tempfile
import zipfile

from zip_builder import safe_unpack, inspect_project, find_root, BuildError

AGP_811 = "8.11.0"
KOTLIN_2120 = "2.1.20"


def small_text(path: Path) -> str:
    if not path.is_file() or path.stat().st_size > 500_000:
        return ""
    return path.read_text("utf-8", errors="replace")


def declared_plugins(project: Path) -> dict:
    # Keep source inspection bounded; never execute Gradle or project scripts.
    files = [
        project / "settings.gradle.kts", project / "settings.gradle",
        project / "build.gradle.kts", project / "build.gradle",
        project / "gradle/libs.versions.toml",
    ] + list(project.glob("*/build.gradle*"))[:50]
    text = "\n".join(small_text(p) for p in files)
    agp = re.search(r'com\.android\.application["\x27]?\s*\)?\s*version\s*["\x27]([0-9.]+)', text)
    kotlin = re.search(r'org\.jetbrains\.kotlin\.android["\x27]?\s*\)?\s*version\s*["\x27]([0-9.]+)', text)
    wrapper = small_text(project / "gradle/wrapper/gradle-wrapper.properties")
    gradle = re.search(r"gradle-([0-9.]+)-(?:bin|all)\.zip", wrapper)
    sdk = re.search(r"compileSdk\s*(?:=|\s)\s*(\d{2})", text)
    ndk_version = re.search(r'ndkVersion\s*(?:=|\s)\s*["\x27]([0-9.]+)', text)
    return {
        "android_gradle_plugin": agp.group(1) if agp else None,
        "kotlin_plugin": kotlin.group(1) if kotlin else None,
        "project_gradle_wrapper": gradle.group(1) if gradle else None,
        "compile_sdk": int(sdk.group(1)) if sdk else None,
        "ndk_version": ndk_version.group(1) if ndk_version else None,
        "has_native_build_script": ("externalNativeBuild" in text or
                                    bool(list(project.glob("**/CMakeLists.txt"))[:1])),
    }


def propose(project: Path) -> dict:
    project = find_root(project)
    kind = inspect_project(project)["project_type"]
    plugins = declared_plugins(project)
    android_native = any(k in kind for k in ("android-gradle",)) and plugins["has_native_build_script"]
    mapping = {
        "android-gradle": ["openjdk-17", "gradle", "android-sdk-36",
                           "aapt2-zipalign", "d8-apksigner", "android-gradle-plugin"],
        "android-gradle-python": ["openjdk-17", "gradle", "android-sdk-36",
                                  "aapt2-zipalign", "d8-apksigner",
                                  "android-gradle-plugin", "chaquopy-build"],
        "flutter": ["flutter-dart", "openjdk-17", "android-sdk-platforms",
                    "android-build-tools", "android-platform-tools"],
        "buildozer-python": ["buildozer", "python-for-android", "android-ndk",
                             "android-sdk-platforms", "android-build-tools"],
    }
    requires = list(mapping.get(kind, []))
    if kind.startswith("android-gradle"):
        uses_kotlin = (plugins["kotlin_plugin"] or
                       any(project.rglob("*.kt")))
        if uses_kotlin:
            requires.extend(["kotlin-compiler", "kotlin-gradle-plugin-resolver"])
        if android_native:
            requires.extend(["android-ndk", "android-cmake"])
    warnings = []
    if plugins["android_gradle_plugin"] and plugins["android_gradle_plugin"] != AGP_811:
        warnings.append("AGP differs from the verified 8.11.0 CI profile; use the project version with a compatible JDK and Gradle instead of silently replacing it.")
    if plugins["project_gradle_wrapper"] and plugins["project_gradle_wrapper"] != "8.14.3":
        warnings.append("Project Gradle wrapper differs from 8.14.3; respect project-pinned version and check its AGP/JDK compatibility.")
    if plugins["kotlin_plugin"] and plugins["kotlin_plugin"] != KOTLIN_2120:
        warnings.append("Kotlin plugin differs from the verified 2.1.20 profile; do not force another version.")
    if not requires:
        warnings.append("Not a recognized Android APK packaging project. Plain Python or Java source needs a matching Android app/project configuration.")
    if kind == "buildozer-python":
        warnings.append("Buildozer/python-for-android requires supported Linux/macOS host; direct Android Bionic hosting is not verified.")
    if any("android-ndk" == t for t in requires):
        warnings.append("Google Linux x86_64 NDK clang will not run directly on Android Bionic ARM64.")
    # No public registry entry by itself indicates a successful phone installation.
    return {
        "project_type": kind,
        "supported_apk_route": bool(requires),
        "recommended_legacy_tool_ids": [x for x in requires if x in {
            "openjdk-17", "gradle", "android-sdk-36", "aapt2-zipalign",
            "d8-apksigner", "kotlin-compiler", "android-gradle-plugin", "chaquopy-build"
        }],
        "recommended_extended_tool_ids": [x for x in requires if x not in {
            "openjdk-17", "gradle", "android-sdk-36", "aapt2-zipalign",
            "d8-apksigner", "kotlin-compiler", "android-gradle-plugin", "chaquopy-build"
        }],
        "project_declarations": plugins,
        "host_runtime_test_required": True,
        "android_phone_verified": False,
        "warnings": warnings,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Generate non-executing JSON install plan from ZIP or Android project")
    p.add_argument("project", type=Path)
    args = p.parse_args()
    path = args.project.expanduser().resolve()
    try:
        if path.is_dir():
            result = propose(path)
        elif path.is_file() and path.suffix.lower() == ".zip":
            with tempfile.TemporaryDirectory(prefix="pyeye-plan-") as folder:
                safe_unpack(path, Path(folder))
                result = propose(Path(folder))
        else:
            raise BuildError("Provide a project directory or .zip project archive")
        print(json.dumps(result, indent=2))
    except (OSError, BuildError, zipfile.BadZipFile) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
