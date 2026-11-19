# Python Eye IDE — Evidence ledger for real toolchain checks

**Verified on:** GitHub Actions Ubuntu Linux x86_64 host, 2026-11-20 (IST).  
**Passing workflow:** [Verify Real Python Eye Host Toolchains, run 44613219027](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44613219027).

| Tool family | Actual check | Result | Android ARM64 phone proof |
|---|---|---|---|
| Java JDK 8 | Temurin JDK install; `javac Smoke.java`; `java Smoke` | PASS | Not tested |
| Java JDK 11 | Same source compiled and run under JDK 11 | PASS | Not tested |
| Java JDK 21 | Same source compiled and run under JDK 21 | PASS | Not tested |
| JDK 17 / Gradle 8.14.3 / AGP 8.11 | Real Kotlin Android Gradle APK build | PASS | Not tested |
| Kotlin 2.1.20 | `org.jetbrains.kotlin.android` compilation of real `MainActivity.kt` into verified APK | PASS | Not tested |
| Android SDK Platform 36 | Google `sdkmanager` download + real `android.jar` probe | PASS | Not tested |
| Android Build Tools 35.0.0 | `aapt2 version`, D8 and ApkSigner execution | PASS | Android-native substitutes need separate validation |
| Android NDK 27.0.12077973 | Install official package and run actual `clang --version` | PASS | **Linux x86_64 host compiler cannot run unchanged under Android Bionic** |
| Android CMake 3.22.1 | Install package and run `cmake --version` | PASS | **Linux x86_64 host executable not an Android Bionic binary** |
| Android platform-tools / CLI | `adb version` and `sdkmanager --version` | PASS | Not tested |
| Flutter 3.47.9 / Dart | Install Flutter, `flutter create`, `flutter build apk --debug`, verify manifest and `classes.dex` | PASS | Not tested |
| Buildozer 1.6.0 | Real PyPI install and import / version command | PASS (CLI **only**) | Not tested |
| python-for-android 2026.5.9 | Real PyPI install and Python import | PASS (CLI **only**) | Not tested |
| Chaquopy 17.2.0 / Python 3.10 | Real Android Python debug APK build (existing CI) | PASS | Not tested |

**Earlier real Chaquopy APK:** [Build Python APK, run 44236880906](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44236880906). That workflow verifies Python packaged into an APK with ARM64 runtime, on Linux CI only.

### Unverified or not universally available

- Buildozer CLI installation does **not** prove a real Kivy APK build. Native Python modules may need platform-specific recipes.
- No Android Bionic phone-host NDK, CMake, Flutter, Gradle/Jansi or all-JDK installation has yet been confirmed. A Linux ARM64 package is **not** automatically compatible with Android ARM64/Bionic.
- Tools such as AGP, Kotlin plugin, Chaquopy, R8, Android Lint and bundletool are **versioned project dependencies / task integrations**, not independent ZIP archives to redistribute arbitrarily.
- The existing five public GitHub Release archives remain the only directly hosted toolchain binaries. They have cryptographic asset metadata, but actual on-phone success still needs device tests.
- There is no honest way to promise APK output from every Java, Python or other ZIP: the ZIP must be a supported Android app project, and custom native dependencies can fail.

### Added executable code

- [Read-only local tool doctor](probe_tools.py): reports 28 tool IDs with observed status; never treats a published catalog entry as device-ready.
- [Safe ZIP project analyzer](zip_builder.py): recognizes build families, refuses untrusted build execution without `--execute`.
- [Project-aware dependency planner](plan_project.py): detects Gradle wrapper, AGP and Kotlin declarations, requests NDK only when needed and never changes version silently.
- [Official SDK/NDK/CMake installer](sdk_installer.py): installs requested Google packages through sdkmanager on compatible desktop hosts with explicit SDK license acceptance.
- [Isolated Python package provisioner](provision_packagers.py): pinned Buildozer/p4a installs on supported Linux/macOS hosts.
- [Extended setup registry](extended-tools.json): 20 additional routes for future IDE integration without breaking old 8 IDs.

**Device readiness rule:** only after the real Android-native executable exits successfully and a representative APK compiles inside Python Eye IDE on the actual device. GitHub Linux results must be displayed separately from device results.
