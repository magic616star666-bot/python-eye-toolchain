# Actual Toolchain Release Status — 2026-11-18

This document is for operational inspection; the authoritative machine-readable source is `tools.json`.

## Published downloadable assets

| Entry | Release file | Verified source |
|---|---|---|
| JDK 17 | `jdk17-arm64.tar.xz` | itsaky/android OpenJDK; mirrored digest recorded |
| Gradle 8.14.3 | `gradle-8.14.3-bin.zip` | Official Gradle SHA-256 |
| AAPT2 + Zipalign 35.0.2 | `android-sdk-tools-static-aarch64.zip` | lzhiyong Android ARM64 SDK tools; SHA-256 recorded |
| D8 + APK Signer 34.0.4 (auxiliary) | `build-tools-34.0.4-aarch64.tar.xz` | AndroidIDEOfficial Android ARM64 build tools; SHA-256 recorded |
| Kotlin 2.1.20 | `kotlin-compiler-2.1.20.zip` | Official JetBrains SHA-256 |

All five archives are present on [toolchain-v1 Releases](https://github.com/magic616star666-bot/python-eye-toolchain/releases/tag/toolchain-v1). A separate standalone AAPT2 binary also exists as a supplemental Release asset, not an additional catalog entry.

## Three managed components, not mirrored ZIPs

- Android SDK 36: Google SDK Manager `platforms;android-36`, license acceptance required.
- Android Gradle Plugin 8.11.0: `com.android.application` from Google Maven.
- Chaquopy 17.2.0: `com.chaquo.python` via Gradle/Maven Central.

They are version-selected and used successfully in [a real GitHub Linux CI APK build](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44159445752), but **remain not installed in the Android IDE** and therefore `published: false` in the old archive-style catalog.

## Known on-device gaps

- Source of Python Eye IDE's catalog reader and installer not present in this repository. Duplicate app UI cards cannot be removed here.
- The 34.x D8+ApkSigner archive is **not** a complete 35.x SDK Build Tools installation required by AGP 8.11.
- ARM64 AAPT2/Zipalign were checked for ELF architecture, not executed in the user's Android environment.
- The mirrored JDK17 upstream release is from 2022; security maintenance must be reassessed before production deployment.
- No signing keys or user secrets are stored.
