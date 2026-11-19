#!/usr/bin/env python3
"""Regression tests: ZIP safety, Android project routing and SDK allowlist."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))
from zip_builder import BuildError, inspect_or_build, safe_unpack
from sdk_installer import ToolError, parse_package


class ZipProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_zip(self, name, entries):
        path = self.root / name
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as out:
            for filename, content in entries.items():
                out.writestr(filename, content)
        return path

    def inspect(self, path):
        return inspect_or_build(SimpleNamespace(action="inspect", path=path))

    def test_android_java_zip(self):
        src = self.make_zip("java.zip", {
            "project/settings.gradle.kts": 'rootProject.name = "Test"',
            "project/app/build.gradle.kts": 'plugins { id("com.android.application") }',
            "project/app/src/main/java/Test.java": "class Test {}",
        })
        result = self.inspect(src)
        self.assertEqual(result["project_type"], "android-gradle")
        self.assertTrue(result["apk_build_supported"])

    def test_android_chaquopy_zip(self):
        src = self.make_zip("python.zip", {
            "project/settings.gradle": "include ':app'",
            "project/app/build.gradle": "plugins { id 'com.android.application'; id 'com.chaquo.python' }",
            "project/app/src/main/python/hello.py": "print('hi')",
        })
        self.assertEqual(self.inspect(src)["project_type"], "android-gradle-python")

    def test_flutter_zip(self):
        src = self.make_zip("flutter.zip", {
            "pubspec.yaml": "name: hello\nflutter:\n  uses-material-design: true\n",
            "lib/main.dart": "void main() {}"
        })
        self.assertEqual(self.inspect(src)["project_type"], "flutter")

    def test_buildozer_zip(self):
        src = self.make_zip("kivy.zip", {
            "main.py": "print(1)",
            "buildozer.spec": "[app]\ntitle=Hello\n"
        })
        self.assertEqual(self.inspect(src)["project_type"], "buildozer-python")

    def test_plain_python_is_not_falsely_apk_ready(self):
        src = self.make_zip("plain.zip", {"main.py": "print(1)"})
        result = self.inspect(src)
        self.assertEqual(result["project_type"], "plain-python")
        self.assertFalse(result["apk_build_supported"])

    def test_java_library_not_falsely_android_app(self):
        src = self.make_zip("plain-java.zip", {
            "build.gradle": "plugins { id 'java-library' }",
            "settings.gradle": "rootProject.name = 'lib'"
        })
        result = self.inspect(src)
        self.assertEqual(result["project_type"], "non-android-gradle")
        self.assertFalse(result["apk_build_supported"])

    def test_untrusted_build_requires_explicit_execute(self):
        src = self.make_zip("blocked.zip", {
            "settings.gradle": "include ':app'",
            "app/build.gradle": "apply plugin: 'com.android.application'",
        })
        with self.assertRaisesRegex(BuildError, "--execute"):
            inspect_or_build(SimpleNamespace(action="build", path=src,
                             execute=False, output=self.root / "out", use_wrapper=False))

    def test_zip_traversal_rejected(self):
        src = self.make_zip("evil.zip", {"../outside.txt": "oops"})
        with self.assertRaises(BuildError):
            safe_unpack(src, self.root / "extract")
        self.assertFalse((self.root.parent / "outside.txt").exists())

    def test_zip_absolute_path_rejected(self):
        src = self.make_zip("absolute.zip", {"/tmp/file": "oops"})
        with self.assertRaises(BuildError):
            safe_unpack(src, self.root / "extract")

    def test_zip_symlink_rejected(self):
        src = self.root / "symlink.zip"
        with zipfile.ZipFile(src, "w") as z:
            item = zipfile.ZipInfo("symlink")
            item.create_system = 3
            item.external_attr = (0o120777 << 16)
            z.writestr(item, "../outside")
        with self.assertRaises(BuildError):
            safe_unpack(src, self.root / "extract")

    def test_duplicate_entries_rejected(self):
        src = self.root / "duplicate.zip"
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(src, "w") as z:
                z.writestr("x.txt", "1")
                z.writestr("x.txt", "2")
        with self.assertRaises(BuildError):
            safe_unpack(src, self.root / "extract")


class SdkInstallerTests(unittest.TestCase):
    def test_sdk_package_allowlist(self):
        for name in ["platforms;android-36", "platforms;android-21",
                     "build-tools;35.0.0", "ndk;27.0.12077973",
                     "cmake;3.22.1", "platform-tools", "cmdline-tools;latest",
                     "platforms;android-37", "cmdline-tools;22.0", "emulator"]:
            self.assertEqual(parse_package(name), name)

    def test_injection_and_unknown_sdk_rejected(self):
        for name in ["--help", ";rm -rf /", "extras;some-vendor",
                     "platforms;android-9999", "ndk;../bad", "build-tools;35.0.0;rm"]:
            with self.assertRaises(ToolError):
                parse_package(name)


if __name__ == "__main__":
    unittest.main()
