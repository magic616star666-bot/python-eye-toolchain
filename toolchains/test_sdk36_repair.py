#!/usr/bin/env python3
"""Offline tests: do not download anything or write into an Android SDK."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sdk36_repair", HERE / "sdk36_repair.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class TestSdk36Repair(unittest.TestCase):
    def test_official_google_pin(self):
        self.assertEqual(r.VERSION, "36.0.0")
        self.assertEqual(r.GOOGLE_BYTES, 63737259)
        self.assertEqual(r.GOOGLE_SHA1, "b0b6376977657e8ad9b969bacf4093601da2c6fb")
        self.assertEqual(r.GOOGLE_URL,
                         "https://dl.google.com/android/repository/build-tools_r36_linux.zip")

    def test_provider_ids_match_android_ide_store_names(self):
        self.assertGreaterEqual(len(r.PROVIDERS), 5)
        self.assertTrue(all(x.startswith("mobile-android-") for x in r.PROVIDERS))
        self.assertEqual(len(r.PROVIDERS), len(set(r.PROVIDERS)))

    def test_missing_license_is_not_auto_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(r.license_accepted(Path(tmp)))
            with self.assertRaisesRegex(RuntimeError, "Explicit|approve|accept"):
                r.repair(Path(tmp), Path(tmp), False, True, None)
            self.assertFalse((Path(tmp) / "licenses").exists())

    def test_invalid_elf_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "aapt2"
            f.write_bytes(b"x86 fake binary" * 10)
            self.assertFalse(r.is_bionic_arm64(f))

    def test_archive_zip_slip_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            z = Path(tmp) / "bad.zip"
            with zipfile.ZipFile(z, "w") as archive:
                archive.writestr("../escape.txt", "x")
            with self.assertRaisesRegex(RuntimeError, "Unsafe archive"):
                r.secure_unzip(z, Path(tmp) / "out")
            self.assertFalse((Path(tmp) / "escape.txt").exists())

    def test_mock_staged_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "source.properties").write_text("Pkg.Revision=36.0.0\n")
            (p / "lib").mkdir()
            for rel in r.REQUIRED_DATA:
                x = p / rel
                x.parent.mkdir(parents=True, exist_ok=True)
                x.write_bytes(b"fixture")
            self.assertEqual(r.sdk_status_at_stage(p),
                             ["Bad Bionic aapt2", "Bad Bionic aidl", "Bad Bionic zipalign"])

    def test_no_download_during_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(r.main(["status", "--tools-root", tmp]), 2)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
