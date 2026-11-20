# Python Eye IDE — Extended Android Build Toolchains

**Date:** 2026-11-20 · **Purpose:** additional build routes for Java, Kotlin,
Flutter and Python Android projects, without breaking the existing eight
`tools.json` IDs which the currently delivered Kotlin IDE source expects.

## What was actually added

- `extended-tools.json`: 20 distinct **provisioning routes** (JDK 8/11/21,
  per-project Gradle Wrapper, Android SDK platforms, Build Tools, platform
  tools, Command-line Tools, NDK, CMake, AGP/Kotlin Gradle resolution, D8/R8,
  APK signing, Android Lint, bundletool, Chaquopy, Buildozer,
  python-for-android and Flutter/Dart).
- `sdk_installer.py`: **runnable installer**, using an already-installed
  official Google `sdkmanager` on compatible Linux x86_64 or macOS hosts.
  It installs only explicitly requested SDK packages, with Google SDK
  license acceptance required.
- `zip_builder.py`: **runnable project detector** for Android Gradle Java /
  Kotlin, Chaquopy-Python Gradle, Flutter, and Buildozer Python projects.
  Project inspection does not run build scripts. The optional `build` mode
  executes actual external build tools and verifies a nonempty APK ZIP
  containing `AndroidManifest.xml`; no dummy APKs are generated.
- `test_toolchains.py` and GitHub Actions workflow: ZIP traversal/links,
  project-type detection, allowlist and no-execution-without-approval checks.

## Run with an external build host

```bash
python3 toolchains/zip_builder.py inspect /path/to/project.zip

# WARNING: --execute runs project-controlled Gradle, Flutter or Buildozer code.
# Run this only with a ZIP whose origin and build scripts you trust.
python3 toolchains/zip_builder.py build /path/to/trusted-android-project.zip --execute --output ./real-apks

# Gradle wrapper is optional and never silently executed:
python3 toolchains/zip_builder.py build /path/to/trusted-android-project.zip --execute --use-wrapper --output ./real-apks

# License must be personally reviewed/accepted before using this flag:
python3 toolchains/sdk_installer.py install --sdk-root "$ANDROID_HOME" \
  --package 'platforms;android-36' \
  --package 'build-tools;35.0.0' \
  --accept-sdk-license

# Optional SDK/NDK/CMake packages are resolved individually:
python3 toolchains/sdk_installer.py install --sdk-root "$ANDROID_HOME" \
  --package 'ndk;27.0.12077973' \
  --package 'cmake;3.22.1' \
  --accept-sdk-license

python3 -m unittest discover -s toolchains -p 'test_*.py' -v
```

The SDK installer **does not bootstrap** a missing `sdkmanager`, Java,
Gradle, Flutter, Android-native NDK host port, or command-line tools.
Buildozer and python-for-android now have an independent, real venv installer
(`provision_packagers.py`) for supported desktop hosts. Other components must
be supplied through their official vendor-specific mechanisms. The registry is
not a 20-binary download catalog. Source-only support does not equal installed.

## Supported and unsupported ZIP families

| ZIP type | Detection | Build command | Requirements |
| --- | --- | --- | --- |
| Android Java/Kotlin Gradle app | Yes | Gradle `assembleDebug` | Android SDK, AGP, JDK, Gradle version matching the project |
| Android Gradle + Chaquopy Python | Yes | Gradle `assembleDebug` | Compatible Chaquopy plugin, Python version and dependencies |
| Flutter/Dart app | Yes | `flutter build apk --debug` | Installed Flutter/Android toolchain |
| Buildozer/Kivy Python app | Yes | `buildozer android debug` | Supported Linux/macOS build host, SDK/NDK and recipes |
| Plain Java library / Maven Java | Yes, unsupported APK | None | Needs Android app module or supported conversion |
| Plain Python file | Yes, unsupported APK | None | Needs a valid Android packaging project |
| Unrelated ZIP (photos, backend, etc.) | Unknown | None | Not an Android app |

**Host/platform restriction:** Official Android SDK Command-line Tools,
Build Tools and NDK downloads for Linux are typically built for Linux
desktop hosts; unpacking them on an Android ARM64/Bionic phone does **not**
make their `aapt2`, `clang`, `cmake`, etc. executable. The legacy repo
already includes some ARM64-specific archives whose functionality on the
user's actual phone remains unverified. This extension catalog deliberately
reports `device_build_verified: false` everywhere until on-device
compilation and installation succeed.

## Planned Python Eye extension wiring

When the IDE Kotlin source is available for an integration patch:

1. Keep loading the eight stable `tools.json` IDs as before.
2. Show the 20 **optional** routes on a separate advanced screen or route
   registry — do **not** feed them into the old eight-ID archive installer.
3. Before installing any tool, detect the ZIP and select only the compatible
   JDK, AGP, Gradle, SDK API and native dependencies.
4. Resolve these through official vendors / verified Bionic ports, enforcing
   license review, checksum validation and per-tool runtime probes.
5. Mark APK build successful only after inspecting the real generated APK
   and running an install/launch smoke test where applicable.

No claim that every Python or Java ZIP becomes an APK is possible:
incompatible Android libraries, unsupported architectures, obsolete
Gradle/AGP combinations and non-Android programs need project-specific work.
For difficult native dependencies, a Linux CI cloud builder is a supported
fallback; the public repo already demonstrates a real Chaquopy APK build
on GitHub Actions.

**Sources:** [AGP 8.11 compatibility](https://developer.android.com/build/releases/agp-8-11-0-release-notes),
[Chaquopy 17.2 compatibility](https://chaquo.com/chaquopy/doc/current/versions.html),
[Buildozer installation](https://buildozer.readthedocs.io/en/latest/installation/).

## Real host CI: verified Java, Kotlin, Flutter, SDK, NDK, CMake and Python CLIs

The new [**real toolchain CI run (7 successful jobs)**](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44613219027)
actually compiled Java using JDK 8/11/21, compiled a **Kotlin 2.1.20 APK**
with AGP 8.11.0, ran Android Build Tools 35, NDK 27.0.12077973 and
CMake 3.22.1, **built a real Flutter 3.47.9 APK**, and installed the
Buildozer 1.6.0 / python-for-android 2026.5.9 packages (CLI checks only).

The existing real Chaquopy Python APK test also passed on GitHub Linux.
Read [CI_PROOF.md](CI_PROOF.md) for exact verified scope and
**why this does not prove Android-on-phone toolchain readiness.**

### Setup, diagnose and plan (no app integration required yet)

```bash
# Read-only. Shows actual locally runnable tools; no network or downloads.
python3 toolchains/probe_tools.py --sdk-root "$ANDROID_HOME"

# Inspect ZIP safely and select only necessary tool families.
python3 toolchains/plan_project.py path/to/android-project.zip

# Install real Buildozer + python-for-android into an isolated host venv.
# Only on supported Linux/macOS; requires explicit approval.
python3 toolchains/provision_packagers.py install \
  --prefix "$HOME/python-eye-packagers" --approve-install

# Verify installed Python packager versions, without downloading anything.
python3 toolchains/provision_packagers.py status --prefix "$HOME/python-eye-packagers"
```

**The Kotlin IDE source and the Android phone's complete build environment
are not included in this public toolchain repo.** The app must use this
registry as setup *instructions*, not a green Ready indication, until real
device probes and APK build tests pass.


## Multi-version setup and Android Bionic archive sources (20 November 2026)

These CLI installers exist now. The Android Kotlin Extensions UI has NOT been wired to them.

- [versions_manager.py](versions_manager.py): official Temurin JDK families 8, 11, 17, 21 and 25; any existing numbered official Gradle release with official SHA-256. Installs chosen versions side by side, safely extracts and executes for verification on supported desktop hosts, NOT Android Bionic.
- [sdk_versions.py](sdk_versions.py): local SDK version inventory and live official Google sdkmanager package discovery.
- [sdk_installer.py](sdk_installer.py): chosen official SDK Platforms, Build Tools, NDK and CMake for compatible desktop hosts after explicit SDK license acceptance.
- [mobile-artifacts.json](mobile-artifacts.json): 37 original upstream Android/Bionic ARM64 release archives: JDK 11/17/21; CMake 3.22.1/3.31.5; community NDK r28c/r29/r30; AAPT2+Zipalign, D8+APKSigner, and ADB. Each includes a recorded file size and SHA-256. SHA-256 of older JDK11 and ADB archives was measured from complete downloaded bytes in [audit run 44616843832](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44616843832).
- [mobile_installer.py](mobile_installer.py): explicit consent and checksum-verified Android-only install, with opt-in real executable probes; separates archive installation from device readiness.
- [verify_mobile_sources.py](verify_mobile_sources.py): checks the original GitHub release asset identities, SHA-256 provenance, file size and URLs. [Passing upstream verification CI](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44617197516).

### Example commands

Desktop: python3 toolchains/versions_manager.py list
Desktop: python3 toolchains/versions_manager.py install --kind jdk --version 21 --approve-download
Desktop: python3 toolchains/versions_manager.py install --kind gradle --version 8.14.3 --approve-download
Desktop: python3 toolchains/sdk_versions.py available --sdk-root /path/to/android-sdk

Android ARM64 only, after reviewing the source: python3 toolchains/mobile_installer.py list
Android ARM64 only, with explicit user approval: python3 toolchains/mobile_installer.py install --id android-cmake-3-22-1 --approve-download --approve-third-party --execute-probe
Android ARM64 status: python3 toolchains/mobile_installer.py status --id android-cmake-3-22-1

### Verification boundaries

- The 11 asset entries point to REAL upstream downloadable releases, not rehosted binaries in this repository; redistribution rights were not assumed.
- Upstream checksums do not demonstrate binaries run on the user's Android Bionic handset. Actual on-device test is still required.
- A successful local executable probe does not prove a real Gradle/Flutter/Python APK compile, install and launch.
- There is no guarantee for every ZIP or every historical JDK/NDK/Gradle version. Project compatibility and license constraints apply.
- Real JDK and Gradle download jobs have passed on GitHub Linux. [Five JDK/four Gradle downloads](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44616479513) succeeded; that run had a separate regression-test fixture failure which was subsequently fixed and verified [here](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44617197439).
