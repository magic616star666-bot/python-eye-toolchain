#!/usr/bin/env python3
"""Regression coverage for real on-phone APK build doctor, no fake phone proof."""
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent))
import android_apk_smoke as smoke
from versions_manager import InstallError


class AndroidApkSmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def test_no_android_host_blocks_actual_build(self):
        with patch.object(smoke, "device_host", return_value=False):
            with self.assertRaisesRegex(InstallError, "actual Android ARM64"):
                smoke.run_smoke(self.base, self.base, "8.14.3", self.base,
                                self.base / "java", self.base / "aapt2",
                                self.base / "output", approve_build=True)

    def test_explicit_build_approval_required(self):
        with patch.object(smoke, "device_host", return_value=True):
            with self.assertRaisesRegex(InstallError, "--approve-build"):
                smoke.run_smoke(self.base, self.base, "8.14.3", self.base,
                                self.base / "java", self.base / "aapt2",
                                self.base / "output", approve_build=False)

    def test_valid_apk_needs_manifest_and_dex(self):
        root = self.base / "app/build/outputs/apk/debug"
        root.mkdir(parents=True)
        file = root / "test.apk"
        with zipfile.ZipFile(file, "w") as out:
            out.writestr("AndroidManifest.xml", "android manifest")
            out.writestr("classes.dex", b"\x00" * 3000)
            out.writestr("resources.arsc", "resource")
        self.assertEqual(smoke.actual_apks(self.base), [file])

    def test_manifest_without_dex_is_not_real_app_output(self):
        root = self.base / "app/build/outputs/apk/debug"
        root.mkdir(parents=True)
        file = root / "bad.apk"
        with zipfile.ZipFile(file, "w") as out:
            out.writestr("AndroidManifest.xml", "android manifest")
            out.writestr("unrelated.txt", b"\x00" * 3000)
        self.assertEqual(smoke.actual_apks(self.base), [])

    def test_zipfile_named_apk_without_manifest_is_not_output(self):
        root = self.base / "app/build/outputs/apk/debug"
        root.mkdir(parents=True)
        file = root / "bad.apk"
        with zipfile.ZipFile(file, "w") as out:
            out.writestr("classes.dex", b"\x00" * 3000)
        self.assertEqual(smoke.actual_apks(self.base), [])

    def test_jdk_check_refuses_desktop_host(self):
        with patch.object(smoke, "device_host", return_value=False):
            with self.assertRaisesRegex(InstallError, "real Android"):
                smoke.require_android_jdk(Path("/usr/bin/java"))


if __name__ == "__main__":
    unittest.main()
