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
Gradle, Buildozer, Flutter, NDK native host port, or command-line tools.
Those components must already be present on the host or installed through
their official vendor-specific mechanisms. The registry is not a 20-binary
download catalog. Source-only support does not equal installed and tested.

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
