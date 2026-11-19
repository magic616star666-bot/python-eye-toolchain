#!/usr/bin/env python3
"""Plan resolver: never overwrite pinned project version or promise phone readiness."""
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from plan_project import propose


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, content):
        dest = self.root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        return dest

    def test_kotlin_java_profile(self):
        self.put("settings.gradle.kts", 'include(":app")')
        self.put("build.gradle.kts", 'plugins { id("com.android.application") version "8.11.0" apply false\n id("org.jetbrains.kotlin.android") version "2.1.20" apply false }')
        self.put("app/build.gradle.kts", 'plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }\nandroid { compileSdk = 36 }')
        self.put("app/src/main/kotlin/Main.kt", "class Main")
        plan = propose(self.root)
        self.assertEqual(plan["project_type"], "android-gradle")
        self.assertIn("kotlin-compiler", plan["recommended_legacy_tool_ids"])
        self.assertFalse(plan["android_phone_verified"])

    def test_pinned_gradle_is_respected(self):
        self.put("settings.gradle", 'include ":app"')
        self.put("build.gradle", "plugins { id 'com.android.application' version '8.11.0' apply false }")
        self.put("app/build.gradle", "plugins { id 'com.android.application' }")
        self.put("gradle/wrapper/gradle-wrapper.properties", "distributionUrl=https\\://services.gradle.org/distributions/gradle-8.13-bin.zip")
        plan = propose(self.root)
        self.assertEqual(plan["project_declarations"]["project_gradle_wrapper"], "8.13")
        self.assertTrue(any("respect project-pinned" in warning for warning in plan["warnings"]))

    def test_python_chapk(self):
        self.put("settings.gradle", 'include ":app"')
        self.put("app/build.gradle", "plugins { id 'com.android.application'; id 'com.chaquo.python' }")
        self.put("app/src/main/python/main.py", "print(1)")
        plan = propose(self.root)
        self.assertEqual(plan["project_type"], "android-gradle-python")
        self.assertIn("chaquopy-build", plan["recommended_legacy_tool_ids"])

    def test_plain_python_no_fake_apk(self):
        self.put("main.py", "print(1)")
        plan = propose(self.root)
        self.assertFalse(plan["supported_apk_route"])
        self.assertFalse(plan["android_phone_verified"])


if __name__ == "__main__":
    unittest.main()
