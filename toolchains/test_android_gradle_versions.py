#!/usr/bin/env python3
"""Offline safety tests for Android-host pure JVM Gradle version installer."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import android_gradle_versions as av
from versions_manager import InstallError


class AndroidGradleTests(unittest.TestCase):
    def test_exact_version_only(self):
        for v in ("8.14.3", "9.1.0", "7.6.4", "8.13"):
            self.assertIsNotNone(av.VERSION.fullmatch(v))
        for v in ("", "latest", "9.1-rc1", "../8.14", "8.0;rm -rf", "v8.14.3"):
            self.assertIsNone(av.VERSION.fullmatch(v))

    def test_host_must_be_real_android_for_install(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(av, "device_host", return_value=False):
                with self.assertRaisesRegex(InstallError, "Android ARM64"):
                    av.install("8.14.3", Path(td), Path("/does-not-exist"),
                               approve=True, execute_probe=False)

    def test_requires_consent_before_download(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(av, "device_host", return_value=True):
                with self.assertRaisesRegex(InstallError, "approve-download"):
                    av.install("8.14.3", Path(td), Path("/fake-java"),
                               approve=False, execute_probe=False)

    def test_not_installed_is_not_ready(self):
        with tempfile.TemporaryDirectory() as td:
            result = av.status("8.14.3", Path(td))
            self.assertFalse(result["installed"])
            self.assertFalse(result["local_android_jvm_version_probe_passed"])
            self.assertFalse(result["android_apk_build_verified"])

    def test_jar_probe_requires_genuine_launcher(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(InstallError, "launcher JAR"):
                av.jar_for(Path(td), "8.14.3")

    def test_no_non_android_java_probe(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(av, "device_host", return_value=False):
                with self.assertRaisesRegex(InstallError, "Android"):
                    av.run_launcher(Path("/usr/bin/java"), Path(td), "8.14.3")


if __name__ == "__main__":
    unittest.main()
