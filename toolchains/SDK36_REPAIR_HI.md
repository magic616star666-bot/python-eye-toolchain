# Python Eye IDE — SDK Build-Tools 36.0.0 GitHub Repair

**Status: GitHub repair sources and version/pin mapping published. Phone installation NOT performed.**

## For Python Eye IDE v1.6.3 on Android

1. Open **Extensions → Sync GitHub**. The unified [GitHub catalog](python-eye-unified-android-arm64.json) now points the SDK36 repair to **six existing Android/Bionic native providers** with the exact matching inventory IDs. GitHub Sync changes metadata and available Load options; **it cannot install a package or execute a script by itself**.
2. In Extensions choose **Prepare Android-native tools for SDK 36 (Load + Test)**. Approve the provider source and download. ToolStore verifies the pinned archive SHA-256, installs locally and runs the real native CLI test.
3. Choose **Install genuine SDK Build-Tools 36.0.0**, review and explicitly accept the Google Android SDK license and ~64 MB download. The built-in installer checks the actual Google archive and requires Android/Bionic `aapt2`, `aidl`, `zipalign` to run successfully before activating the SDK.
4. Then **Full Build Doctor → Build APK** on AVIRA. A successful file/CLI check does **not** guarantee an APK build, particularly when D8 has only ~1–2 GiB available RAM.

## Official Google package pin, confirmed in SDK repository2-3.xml

- Package: `build-tools;36.0.0`
- Google URL: `https://dl.google.com/android/repository/build-tools_r36_linux.zip`
- Size: `63737259` bytes
- Official SHA-1: `b0b6376977657e8ad9b969bacf4093601da2c6fb`
- License: `android-sdk-license`
- Native executables in Google's **Linux/x86_64** package are *not* directly runnable in Python Eye on Android. Only independently tested Bionic/ARM64 replacements may be used.

## Source providers (from existing SHA-256 catalog)

| First attempt order | GitHub native asset ID | Installed ToolStore ID |
|---:|---|---|
| 1 | `android-build-tools-34-0-3-bionic` | `mobile-android-build-tools-34-0-3-bionic` |
| 2 | `android-build-tools-34-0-1-bionic` | `mobile-android-build-tools-34-0-1-bionic` |
| 3 | `android-build-tools-34-0-0-bionic` | `mobile-android-build-tools-34-0-0-bionic` |
| 4 | `android-build-tools-33-0-3-bionic` | `mobile-android-build-tools-33-0-3-bionic` |
| 5 | `android-build-tools-33-0-1-bionic` | `mobile-android-build-tools-33-0-1-bionic` |
| 6 | `android-aapt2-zipalign-35` | `mobile-android-aapt2-zipalign-35` |

These provide **candidate native binaries**, not a complete verified Build-Tools 36.0.0 Android native release. Version/CLI compatibility must be checked on the actual phone. Never force Build-Tools 35 in an AGP 9.3.1 project.

## Manual recovery if the built-in UI cannot complete

[SDK36 repair Python 3.10 CLI](sdk36_repair.py) is an **optional manual recovery script** for Python Eye's own Python terminal. It checks local prerequisites and, **only with explicit flags and an already-accepted license record**, downloads the pinned Google 36 archive, stages Android/Bionic native binaries, verifies them and rolls back an unsuccessful installation. It **does not execute on GitHub Sync**. [Offline safety tests](test_sdk36_repair.py) and [CI workflow](../.github/workflows/sdk36-repair-verify.yml) are included; no phone-level success is asserted.

**Diagnosis from user log:** `Missing SDK Build-Tools 36.0.0 directory`. GitHub upload cannot change `/data/user/0/com.pythoneye.idestudio/files/tools/android-sdk-36` remotely.

**Ready status:** catalog repair prepared; actual device Load+Test, Google license consent, native overlay and AGP9 APK compilation still required.
