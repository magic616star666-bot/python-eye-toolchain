#!/usr/bin/env python3
"""Offline tests for add-on framework detection, APK constraints and installers."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).parent))
import extra_families as ext
import provision_addons as addons
from zip_builder import inspect_project, inspect_or_build, BuildError
from plan_project import propose


class FamilyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")
        return path

    def npm(self, packages):
        self.write("package.json", json.dumps({"name": "example", "version": "1.0.0",
                                               "dependencies": packages}))

    def has_android(self):
        self.write("android/settings.gradle", "include ':app'")

    def test_react_native_android_gradle(self):
        self.npm({"react-native": "0.80.0"})
        self.has_android()
        result = inspect_project(self.root)
        self.assertEqual(result["project_type"], "react-native")
        self.assertTrue(result["apk_build_supported"])
        self.assertIn("react-native-cli", propose(self.root)["recommended_extended_tool_ids"])

    def test_react_native_without_android_not_falsely_ready(self):
        self.npm({"react-native": "0.80.0"})
        result = inspect_project(self.root)
        self.assertFalse(result["apk_build_supported"])
        self.assertFalse(propose(self.root)["supported_apk_route"])
        self.assertTrue(result["framework_blockers"])

    def test_expo_is_not_confused_with_react_native(self):
        self.npm({"expo": "^54.0.0", "react-native": "0.81.0"})
        self.has_android()
        self.assertEqual(inspect_project(self.root)["project_type"], "expo")

    def test_capacitor_android_project(self):
        self.npm({"@capacitor/core": "7.0.0"})
        self.has_android()
        self.assertEqual(inspect_project(self.root)["project_type"], "capacitor")
        self.assertTrue(inspect_project(self.root)["apk_build_supported"])

    def test_capacitor_without_generated_android_is_not_ready(self):
        self.npm({"@capacitor/core": "7.0.0"})
        self.assertFalse(inspect_project(self.root)["apk_build_supported"])

    def test_cordova_project_needs_android_platform(self):
        self.write("config.xml", '<widget id="com.example.test"></widget>')
        self.assertEqual(inspect_project(self.root)["project_type"], "cordova")
        self.assertFalse(inspect_project(self.root)["apk_build_supported"])
        (self.root / "platforms/android").mkdir(parents=True)
        self.assertTrue(inspect_project(self.root)["apk_build_supported"])

    def test_briefcase_project(self):
        self.write("pyproject.toml", '[tool.briefcase]\nproject_name="Example"\n')
        self.assertEqual(inspect_project(self.root)["project_type"], "beeware-briefcase")
        self.assertTrue(inspect_project(self.root)["apk_build_supported"])

    def test_flet_project(self):
        self.write("pyproject.toml", '[tool.flet]\nproduct="Example"\n')
        self.assertEqual(inspect_project(self.root)["project_type"], "flet-python")
        self.assertIn("flet-cli", propose(self.root)["recommended_extended_tool_ids"])

    def test_regular_python_not_auto_app(self):
        self.write("main.py", "print('no android config')")
        self.assertEqual(inspect_project(self.root)["project_type"], "plain-python")
        self.assertFalse(inspect_project(self.root)["apk_build_supported"])

    def test_maven_not_apk_automatically(self):
        self.write("pom.xml", "<project/>")
        self.assertEqual(inspect_project(self.root)["project_type"], "maven-java-library")
        self.assertFalse(propose(self.root)["supported_apk_route"])

    def test_ant_not_apk_automatically(self):
        self.write("build.xml", "<project/>")
        self.assertEqual(inspect_project(self.root)["project_type"], "ant-java-library")
        self.assertFalse(propose(self.root)["supported_apk_route"])

    def test_rust_library_not_apk_automatically(self):
        self.write("Cargo.toml", '[package]\nname="example"\n')
        self.assertEqual(inspect_project(self.root)["project_type"], "rust-library")
        self.assertFalse(propose(self.root)["supported_apk_route"])

    def test_gradle_plugins_detected(self):
        self.write("settings.gradle.kts", 'rootProject.name = "Example"')
        self.write("app/build.gradle.kts", """plugins {
            id("com.android.application")
            id("com.google.devtools.ksp")
            id("org.jetbrains.kotlin.kapt")
            id("org.jetbrains.kotlin.plugin.compose")
        }
        android { externalNativeBuild { cmake { path = file("CMakeLists.txt") } } }
        """)
        self.write("app/src/main/aidl/ISession.aidl", "interface ISession {}")
        result = inspect_project(self.root)
        features = result["additional_gradle_plugins"]
        for expected in ("ksp-gradle-plugin", "kapt-gradle-plugin",
                         "compose-compiler-plugin", "ninja-build", "llvm-clang",
                         "android-aidl"):
            self.assertIn(expected, features)
        self.assertIn("ksp-gradle-plugin", propose(self.root)["recommended_extended_tool_ids"])

    def test_refuse_running_unsafe_zip_without_execute(self):
        self.npm({"react-native": "0.80.0"})
        self.has_android()
        with self.assertRaisesRegex(BuildError, "--execute"):
            inspect_or_build(SimpleNamespace(path=self.root, action="build",
                           execute=False, use_wrapper=False, output=self.root / "out"))

    def test_actual_apk_requires_android_manifest(self):
        build = self.root / "android/app/build/outputs/apk/debug"
        build.mkdir(parents=True)
        fake = build / "fake.apk"
        with zipfile.ZipFile(fake, "w") as z:
            z.writestr("other.txt", "not an APK")
        self.assertEqual(ext.actual_apks(self.root, "react-native"), [])

    def test_malformed_npm_packages_do_not_crash(self):
        self.write("package.json", json.dumps({"dependencies": ["nope"], "devDependencies": "bad"}))
        self.assertEqual(ext.detect_addon(self.root)["project_type"], "node-project")


class ProvisionTests(unittest.TestCase):
    def test_list_contains_expected_packages(self):
        for name in ("capacitor-cli", "cordova-cli", "eas-cli", "react-native-cli",
                     "expo-cli", "flet-cli", "beeware-briefcase"):
            self.assertIn(name, addons.PACKAGES)

    def test_disallows_unpinned_versions(self):
        for version in ("latest", "../evil", "1;rm -rf", "file://x", ""):
            self.assertIsNone(addons.VERSION.fullmatch(version))

    def test_no_install_without_consent(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError, "--approve-install"):
                addons.install(Path(td)/"app", "cordова-cli" if False else "cordova-cli", "12.0.0", False)

    def test_android_bionic_guard(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(addons, "ANDROID", return_value=True):
                with self.assertRaisesRegex(RuntimeError, "Android Bionic"):
                    addons.install(Path(td)/"app", "cordova-cli", "12.0.0", True)

    def test_unknown_installation_not_ready(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertFalse(addons.status(Path(td)/"app", "flet-cli", "0.28.0")["ready"])


if __name__ == "__main__":
    unittest.main()
