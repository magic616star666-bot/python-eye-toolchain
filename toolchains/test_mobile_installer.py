#!/usr/bin/env python3
"""Offline tests for Android Bionic asset catalog and consent/security rules."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import mobile_installer as mobile
from versions_manager import InstallError


class MobileTests(unittest.TestCase):
    def test_real_digest_entries_have_no_fake_ready_flag(self):
        data = mobile.load_index()
        self.assertEqual(len(data["assets"]), 26)
        self.assertTrue(any(x["id"] == "openjdk-21-bionic" for x in data["assets"]))
        self.assertTrue(any(x["id"] == "android-ndk-r30-bionic" for x in data["assets"]))
        self.assertTrue(any(x["id"] == "android-ninja-arm64" for x in data["assets"]))
        self.assertTrue(any(x["id"] == "android-build-tools-33-0-1-bionic" for x in data["assets"]))
        self.assertTrue(any(x["id"] == "android-platform-tools-34-0-3-bionic" for x in data["assets"]))
        self.assertTrue(all(not x["local_device_probe_passed"] for x in data["assets"]))
        self.assertTrue(all(not x["android_apk_build_verified"] for x in data["assets"]))

    def test_linux_host_cannot_run_phone_installer(self):
        with tempfile.TemporaryDirectory() as td:
            entry = mobile.load_index()["assets"][0]
            with patch.object(mobile, "device_host", return_value=False):
                with self.assertRaises(InstallError):
                    mobile.install(Path(td), entry, approve_third_party=False, execute_probe=False)

    def test_third_party_requires_second_consent(self):
        with tempfile.TemporaryDirectory() as td:
            entry = next(a for a in mobile.load_index()["assets"] if a["id"] == "openjdk-21-bionic")
            with patch.object(mobile, "device_host", return_value=True):
                with self.assertRaisesRegex(InstallError, "--approve-third-party"):
                    mobile.install(Path(td), entry, approve_third_party=False, execute_probe=False)

    def test_not_installed_never_ready(self):
        with tempfile.TemporaryDirectory() as td:
            entry = mobile.load_index()["assets"][0]
            observed = mobile.status(Path(td), entry, execute_probe=False)
            self.assertEqual(observed["status"], "not_installed")
            self.assertFalse(observed["local_device_probe_passed"])

    def test_fake_verified_state_cannot_come_from_catalog(self):
        data = mobile.load_index()
        data["assets"][0]["installed"] = True
        with tempfile.TemporaryDirectory() as td:
            spoof = Path(td) / "mobile-artifacts.json"
            spoof.write_text(json.dumps(data))
            with patch.object(mobile, "INDEX", spoof):
                with self.assertRaisesRegex(InstallError, "Untrusted ready"):
                    mobile.load_index()


if __name__ == "__main__":
    unittest.main()
