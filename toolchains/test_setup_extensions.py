#!/usr/bin/env python3
"""Security and compatibility regression for combined Python Eye setup UI."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).parent))
import setup_extensions as setup
import apk_tooling as apk


class SetupTests(unittest.TestCase):
    def test_catalogs_merge_to_54_without_duplicates(self):
        m = setup.manifest()
        self.assertEqual(m["count"], 54)
        self.assertEqual(len({x["id"] for x in m["tools"]}), 54)
        self.assertFalse(m["android_phone_apk_build_verified"])
        self.assertTrue(all(not x["ready"] for x in m["tools"]))

    def test_kotlin_plugins_present(self):
        ids = {tool["id"] for tool in setup.load_all()["tools"]}
        for item in ("ksp-gradle-plugin", "compose-compiler-plugin",
                     "kapt-gradle-plugin", "beeware-briefcase", "rust-cargo",
                     "react-native-cli", "bundletool", "android-ndk"):
            self.assertIn(item, ids)

    def test_project_only_requires_relevant_tools(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "package.json").write_text(json.dumps({
                "name": "test", "version": "1.0.0",
                "dependencies": {"@capacitor/core": "7.0.0"}}))
            (root / "android").mkdir()
            (root / "android/settings.gradle").write_text("include ':app'")
            state = setup.manifest(project=root)
            self.assertEqual(state["project"]["project_type"], "capacitor")
            self.assertTrue(state["project_supported_apk_route"])
            self.assertIn("capacitor-cli", state["project_required_ids"])
            self.assertEqual(state["project_unmapped_requirements"], [])

    def test_read_only_cli_probe_requires_local_executable(self):
        with patch.object(setup.shutil, "which", return_value=None):
            self.assertFalse(setup.cli_probe({"id": "apache-maven"})["ready"])

    def test_managed_plugin_not_global_ready(self):
        with patch.object(setup.shutil, "which", return_value="/usr/bin/mvn"):
            result = setup.cli_probe({"id": "ksp-gradle-plugin"})
            self.assertFalse(result["ready"])
            self.assertEqual(result["probe"], "per-project-package-or-unsupported-global-probe")


class SigningTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root = Path(self.dir.name)

    def create_apk(self, name="demo.apk", manifest=True):
        path = self.root / name
        with zipfile.ZipFile(path, "w") as zf:
            if manifest:
                zf.writestr("AndroidManifest.xml", "binary")
            zf.writestr("classes.dex", "binary")
            zf.writestr("lib/arm64-v8a/libdemo.so", "binary")
        return path

    def test_zip_manifest_and_abis_are_read_only(self):
        result = apk.apk_details(self.create_apk())
        self.assertTrue(result["manifest_present"])
        self.assertEqual(result["native_abis"], ["arm64-v8a"])
        self.assertFalse(result["v2_v3_signature_checked"])

    def test_fake_zip_not_falsely_apk(self):
        with self.assertRaises(ValueError):
            apk.apk_details(self.create_apk(manifest=False))

    def test_refuse_signing_without_execute_or_password(self):
        path = self.create_apk()
        ks = self.root / "owner.jks"
        ks.write_bytes(b"private test stub")
        with self.assertRaisesRegex(RuntimeError, "--execute"):
            apk.sign(path, self.root / "signed.apk", ks, "owner", False)
        with patch.dict(apk.os.environ, {"PYTHON_EYE_KS_PASS": ""}):
            with self.assertRaisesRegex(RuntimeError, "PYTHON_EYE_KS_PASS"):
                apk.sign(path, self.root / "signed.apk", ks, "owner", True)

    def test_refuse_existing_output(self):
        path = self.create_apk()
        ks = self.root / "owner.jks"
        ks.write_bytes(b"private test stub")
        with patch.dict(apk.os.environ, {"PYTHON_EYE_KS_PASS": "dummy"}):
            with self.assertRaisesRegex(RuntimeError, "overwrite"):
                apk.sign(path, path, ks, "owner", True)

    def test_logcat_requires_approval(self):
        with self.assertRaisesRegex(RuntimeError, "--execute"):
            apk.logcat(100, False)


if __name__ == "__main__":
    unittest.main()
