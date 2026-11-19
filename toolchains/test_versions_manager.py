#!/usr/bin/env python3
"""Offline security and version-manager tests (no third-party deps/network)."""
import hashlib
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import versions_manager as vm


class VersionManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_only_numbered_gradle_releases(self):
        for v in ("8.14.3", "9.9.1", "7.6.4", "8.14"):
            self.assertEqual(vm.version_id(v), v)
        for invalid in ("../../bad", "9.9-rc1", "8", "9.1.0;rm", ""):
            with self.assertRaises(vm.InstallError):
                vm.version_id(invalid)

    def test_android_bionic_host_blocked(self):
        with patch.dict(vm.os.environ, {"ANDROID_ROOT": "/system"}, clear=False):
            with self.assertRaisesRegex(vm.InstallError, "Bionic"):
                vm.host()

    def test_gradle_sha256_from_official_metadata(self):
        with patch.object(vm, "https_get", return_value=(b"a"*64)+b"\n"):
            with patch.object(vm, "host", return_value=("linux", "x64")):
                m = vm.gradle_release("8.14.3")
                self.assertEqual(m["sha256"], "a"*64)
                self.assertEqual(m["download_url"],
                                 "https://services.gradle.org/distributions/gradle-8.14.3-bin.zip")

    def test_bad_sha256_metadata_blocked(self):
        with patch.object(vm, "https_get", return_value=b"garbage"):
            with patch.object(vm, "host", return_value=("linux", "x64")):
                with self.assertRaises(vm.InstallError):
                    vm.gradle_release("8.14.3")

    def test_official_jdk_metadata_selection(self):
        item = [{
            "release_name": "jdk-21.0.1+1",
            "binaries": [{"os": "linux", "architecture": "x64", "image_type": "jdk",
                          "package": {"name": "jdk21.tar.gz",
                                      "link": "https://github.com/adoptium/safe-release",
                                      "checksum": "f"*64}}]
        }]
        with patch.object(vm, "https_get", return_value=__import__("json").dumps(item).encode()):
            with patch.object(vm, "host", return_value=("linux", "x64")):
                m = vm.jdk_release(21)
                self.assertEqual(m["sha256"], "f"*64)
                self.assertEqual(m["version"], "21")

    def test_zip_safe_extract_and_preserve_binary(self):
        arc = self.root / "test.zip"
        with zipfile.ZipFile(arc, "w") as out:
            item = zipfile.ZipInfo("gradle-1.0/bin/gradle")
            item.external_attr = (0o100755 << 16)
            out.writestr(item, "#!/bin/sh\necho Gradle 1.0\n")
        folder = self.root / "extract"
        vm.safe_unpack(arc, folder, limit=50000)
        self.assertTrue((folder / "gradle-1.0/bin/gradle").is_file())

    def test_zip_traversal_blocked(self):
        arc = self.root / "bad.zip"
        with zipfile.ZipFile(arc, "w") as out:
            out.writestr("../evil", "x")
        with self.assertRaises(vm.InstallError):
            vm.safe_unpack(arc, self.root / "extract", limit=10000)

    def test_zip_symlink_blocked(self):
        arc = self.root / "badlink.zip"
        with zipfile.ZipFile(arc, "w") as out:
            item = zipfile.ZipInfo("sym")
            item.create_system = 3
            item.external_attr = 0o120777 << 16
            out.writestr(item, "../../outside")
        with self.assertRaises(vm.InstallError):
            vm.safe_unpack(arc, self.root / "extract", limit=10000)

    def test_tar_absolute_link_blocked(self):
        arc = self.root / "bad.tar.gz"
        with tarfile.open(arc, "w:gz") as tar:
            sym = tarfile.TarInfo(name="jdk/lib/escape")
            sym.type = tarfile.SYMTYPE
            sym.linkname = "/etc/passwd"
            tar.addfile(sym)
        with self.assertRaises(vm.InstallError):
            vm.safe_unpack(arc, self.root / "extract", limit=10000)

    def test_tar_relative_link_inside_root_ok(self):
        arc = self.root / "good.tar.gz"
        with tarfile.open(arc, "w:gz") as tar:
            info = tarfile.TarInfo("jdk/bin/java")
            data = b"#!/bin/sh\n"
            info.size = len(data)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(data))
            sym = tarfile.TarInfo("jdk/bin/java-alias")
            sym.type = tarfile.SYMTYPE
            sym.linkname = "java"
            tar.addfile(sym)
        folder = self.root / "extract"
        vm.safe_unpack(arc, folder, limit=10000)
        self.assertEqual((folder / "jdk/bin/java-alias").read_bytes(), b"#!/bin/sh\n")

    def test_wrong_checksum_download_blocks(self):
        class Response:
            def __init__(self): self.data = io.BytesIO(b"test zip bytes")
            def __enter__(self): return self
            def __exit__(self, exc_type, exc, tb): pass
            def read(self, n): return self.data.read(n)
            def geturl(self): return "https://example.org/file.zip"
        with patch.object(vm, "urlopen", return_value=Response()):
            out = self.root / "download.zip"
            with self.assertRaisesRegex(vm.InstallError, "SHA-256 mismatch"):
                vm.download_verified({"download_url": "https://example.org/file.zip",
                                      "sha256": "0"*64}, out, 1000)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
