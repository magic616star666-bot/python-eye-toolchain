# Python Eye IDE — Android Toolchain Distribution

Public catalog and real downloadable tool archives for **Python Eye IDE (Android ARM64)**. This repository is **not** the source code for the IDE itself.

### 📲 Load catalog URL

```text
https://raw.githubusercontent.com/magic616star666-bot/python-eye-toolchain/main/tools.json
```

The JSON root contains exactly **eight unique `tools` IDs**. The `published` field means *archive is uploaded*; it **does not** mean *installed* or *verified working on your Android phone*. The catalog keeps `schema_version: 1` for compatibility, but the Kotlin reader's exact schema remains unverified.

## Tool status — 18 November 2026

| ID | Version / platform | Delivery | Phone APK-build proof |
| --- | --- | --- | --- |
| `openjdk-17` | Java 17 / Android ARM64 (older 2022 upstream build) | Release .tar.xz ✓ | Not tested |
| `gradle` | 8.14.3 / JVM | Release .zip ✓ | Not tested |
| `aapt2-zipalign` | 35.0.2 / Android ARM64 | Release .zip ✓ | Not tested |
| `d8-apksigner` | 34.0.4 Java JARs and scripts / ARM64 bundle | Release .tar.xz ✓ | Not tested |
| `kotlin-compiler` | 2.1.20 / JVM | Release .zip ✓ | Not tested |
| `android-sdk-36` | Android SDK Platform 36 | Google `sdkmanager`; app installer not yet integrated | Not tested |
| `android-gradle-plugin` | 8.11.0 | Gradle plugin from Google Maven; app installer not yet integrated | Not tested |
| `chaquopy-build` | 17.2.0 | Gradle plugin via Maven; app installer not yet integrated | Not tested |

**Important:** D8/ApkSigner **34.0.4** is an auxiliary package and **does not** satisfy AGP 8.11's requirement for **Android SDK Build Tools 35.0.0 or later**. AAPT2/Zipalign 35.0.2 are present but are not a complete Build Tools 35 distribution. The IDE's Android-native installer must use official Build Tools resources and verified ARM64 host tools, and handle Gradle's AAPT2 selection.

## Actual published binaries

[Download real Toolchain assets](https://github.com/magic616star666-bot/python-eye-toolchain/releases/tag/toolchain-v1)

Catalog entries contain direct GitHub Release download links, exact file sizes, SHA-256 and extraction metadata. `scripts/validate_catalog.py` validates the catalog structure; `scripts/verify_release_assets.py` checks all SHA-256 values against **live** GitHub Release digests. The old JDK17 build deserves a separate production-security review.

## Real Python-to-APK test — PASSED on GitHub Linux CI

[Verified CI build](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44159445752) · [Download demonstration APK (17,459,980 bytes)](https://github.com/magic616star666-bot/python-eye-toolchain/releases/download/python-eye-apk-smoke-test/app-debug.apk)

An **ARM64-targeted Android APK** was compiled successfully using the official SDK 36, Build Tools 35.0.0, JDK 17, Gradle 8.14.3, AGP 8.11.0, Chaquopy 17.2.0 and Python 3.10. Build output SHA-256: `df7a59cdea7193f70415c5381eafbc3fba302e1f0c8045764f71d5dfa956bfc4`.

**This proves only the GitHub Linux x86-64 runner build. It does NOT prove that Python Eye IDE itself can compile APKs on Android.** The source for that IDE's actual Kotlin catalog parser/installer has not been provided, so the phone's switches, extraction and external plugin resolution cannot be verified from this repo. Local duplicate cards from bundled + remote extensions must be de-duplicated by ID **inside the IDE**, not by publishing duplicate catalog entries.

## Android IDE integration guide

For the exact contents of the five archives, safe extraction rules, de-duplication of built-in vs remote tools, and the six probes needed before an on-phone APK builder may be called Ready, see [KOTLIN_IDE_INTEGRATION.md](KOTLIN_IDE_INTEGRATION.md).

## Maintenance and safety

- `tools.json` — **single authoritative catalog**; stable `id` keys and explicit `install.method`. Five archives and three managed dependencies.
- `managed-tools.json` — details for Google SDK Manager and Gradle plugin resolution (not ZIP downloads).
- `archive_audit.json` — recorded archive inventory; confirms AAPT2/Zipalign ARM64 and D8/APKSigner Java JARs are present in their respective archives.
- `scripts/validate_catalog.py` — offline metadata/version/dependency validation.
- `scripts/verify_release_assets.py` — live GitHub SHA-256 and size check.
- `apk-smoke-test/` — real minimal Python→Android APK project for CI.
- `.github/workflows/build-python-apk.yml` — genuine APK CI; artifact/Release on success.

No private signing keys or API secrets should go in this public repository. Review each upstream license before redistributing. The SDK's own license acceptance cannot be silently bypassed.

**Next required device proof:** The IDE must parse this JSON, unpack each archive safely, resolve managed packages, point Gradle at valid SDK/JDK host tools, build a debug APK and then install/run it on the phone. These steps remain unverified and should never be shown as Ready based only on a catalog download.
