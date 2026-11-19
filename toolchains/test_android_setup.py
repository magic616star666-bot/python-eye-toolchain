#!/usr/bin/env python3
"""Android-only profile regression tests; NO Android host claims from GitHub CI."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import android_setup as android


class AndroidProfileTests(unittest.TestCase):
    def test_every_legacy_and_addon_id_classified_once(self):
        p = android.android_profile()
        groups = [p["core_android_workflow"], p["optional_android_native"],
                  p["blocked_on_android_until_ported"]]
        ids = [row["id"] for group in groups for row in group]
        self.assertEqual(len(ids), 53)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(groups[0]), 21)
        self.assertEqual(len(groups[1]), 19)
        self.assertEqual(len(groups[2]), 13)

    def test_mobile_only_candidates_count(self):
        with tempfile.TemporaryDirectory() as td:
            result = android.android_catalog(Path(td))
            self.assertEqual(result["target"], "android-arm64-v8a-bionic")
            self.assertEqual(result["available_upstream_native_archives"], 11)
            self.assertFalse(result["apk_build_tested_on_this_phone"])
            self.assertTrue(all(not x["device_ready"] for x in result["native_sources"]))

    def test_actual_android_sources_not_generic_linux_downloads(self):
        catalog = android.load_index()
        for entry in catalog["assets"]:
            self.assertEqual(entry["host"], "android-bionic-aarch64")
            self.assertEqual(entry["local_device_probe_passed"], False)
            self.assertEqual(entry["android_apk_build_verified"], False)

    def test_desktop_packages_are_hidden(self):
        p = android.android_profile()
        hidden = {row["id"] for row in p["blocked_on_android_until_ported"]}
        for name in ("buildozer", "python-for-android", "cloud-build-fallback",
                     "flutter-dart", "beeware-briefcase", "flet-cli"):
            self.assertIn(name, hidden)
        native = {row["id"] for row in p["optional_android_native"]}
        self.assertIn("android-ndk", native)

    def test_installer_cannot_run_on_linux_ci(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(android, "device_host", return_value=False):
                with self.assertRaisesRegex(Exception, "Android"):
                    android.do_install("openjdk-17-bionic", Path(td), True, False, False)
                with self.assertRaisesRegex(Exception, "Android"):
                    android.do_probe("openjdk-17-bionic", Path(td))

    def test_project_flutter_hidden_from_android_auto_setup(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            (project / "pubspec.yaml").write_text("name: example\ndependencies:\n  flutter:\n    sdk: flutter\n")
            result = android.android_plan(project)
            self.assertEqual(result["project_type"], "flutter")
            self.assertIn("flutter-dart", result["blocked_desktop_unported_requirements"])
            self.assertFalse(result["can_start_build_without_checks"])

    def test_java_gradle_is_mapped_to_on_device_workflow(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            (project / "settings.gradle").write_text("include ':app'")
            app = project / "app"
            app.mkdir()
            (app / "build.gradle").write_text("plugins { id 'com.android.application' }")
            plan = android.android_plan(project)
            self.assertTrue(plan["recognized_android_packaging_project"])
            self.assertIn("openjdk-17", plan["android_core_requirements"])
            self.assertFalse(plan["can_start_build_without_checks"])

    def test_raw_python_zip_not_falsely_android_app(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            (project / "main.py").write_text("print(1)")
            plan = android.android_plan(project)
            self.assertFalse(plan["recognized_android_packaging_project"])
            self.assertFalse(plan["can_start_build_without_checks"])


if __name__ == "__main__":
    unittest.main()
