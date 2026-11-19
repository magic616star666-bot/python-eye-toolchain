# Python Eye IDE — Android Toolchain Distribution

Public catalog and real downloadable tool archives for **Python Eye IDE (Android ARM64)**. This repository is **not** the source code for the IDE itself.

### 📲 Load catalog URL

```text
https://raw.githubusercontent.com/magic616star666-bot/python-eye-toolchain/main/tools.json
```

The JSON root contains exactly **eight unique `tools` IDs**. The `published` field means *archive is uploaded*; it **does not** mean *installed* or *verified working on your Android phone*. The catalog keeps `schema_version: 1` for compatibility, but the Kotlin parser has been inspected and its eight-tool catalog schema is supported in the patched app source; Android phone runtime testing is still required.

## Tool status — 18 November 2026

| ID | Version / platform | Delivery | Phone APK-build proof |
| --- | --- | --- | --- |
| `openjdk-17` | Java 17.0.11 / Android ARM64 Bionic | Release .tar.gz ✓ | Not tested |
| `gradle` | 8.14.3 / JVM | Release .zip ✓ | Not tested |
| `aapt2-zipalign` | 35.0.2 / Android ARM64 | Release .zip ✓ | Not tested |
| `d8-apksigner` | 34.0.4 Java JARs and scripts / ARM64 bundle | Release .tar.xz ✓ | Not tested |
| `kotlin-compiler` | 2.1.20 / JVM | Release .zip ✓ | Not tested |
| `android-sdk-36` | Android SDK Platform 36 | Official Google direct ZIP + user license confirmation; Kotlin source patch included, phone test pending | Not tested |
| `android-gradle-plugin` | 8.11.0 | Gradle plugin from Google Maven; Kotlin resolver in patched source, device test pending | Not tested |
| `chaquopy-build` | 17.2.0 | Gradle plugin via Maven; Kotlin resolver in patched source, device test pending | Not tested |

**Important:** D8/ApkSigner **34.0.4** is an auxiliary package and **does not** satisfy AGP 8.11's requirement for **Android SDK Build Tools 35.0.0 or later**. AAPT2/Zipalign 35.0.2 are present but are not a complete Build Tools 35 distribution. The IDE's Android-native installer must use official Build Tools resources and verified ARM64 host tools, and handle Gradle's AAPT2 selection.

## Actual published binaries

[Download real Toolchain assets](https://github.com/magic616star666-bot/python-eye-toolchain/releases/tag/toolchain-v1)

Catalog entries contain direct GitHub Release download links, exact file sizes, SHA-256 and extraction metadata. `scripts/validate_catalog.py` validates the catalog structure; `scripts/verify_release_assets.py` checks all SHA-256 values against **live** GitHub Release digests. New JDK17.0.11 uses an SHA-256 verified Android Bionic ARM64 build; still not device-tested and does not repair incompatible Gradle/Jansi Linux JNI automatically.

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


## Official managed installer — three remaining components

The repo now includes [`installer/managed_installer.py`](installer/managed_installer.py), which can invoke the real SDK Manager for Android SDK Platform 36 and Build Tools 35.0.0, then use **Gradle 8.14.3** to fetch AGP **8.11.0** and Chaquopy **17.2.0** and compile an actual Python APK.

**[All three managed installation methods passed a real GitHub CI build on 18 November 2026](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44236880906).** The script checks installed files and build results instead of marking tools ready from their metadata. It also requires explicit acceptance of the Google Android SDK license before a fresh SDK install.

Android phone caveat: this pass was on a GitHub **Linux runner**, not inside Python Eye IDE. The three managed entries deliberately remain `published: false` in the legacy archive-style `tools.json` because they are not standalone downloadable archives and the Android Kotlin app has a separate managed-install implementation in the delivered patched source ZIP. On-device functionality is still pending testing. See [`installer/README.md`](installer/README.md).

## 📱 Python Eye IDE Kotlin integration (source ZIP patch)

The user-supplied Android IDE project **v1.4.8** now has a local updated source ZIP that:

- bundles all eight catalog entries in `app/src/main/assets/tools/catalog.json` as a fallback to GitHub `tools.json`;
- renders one Extensions card per unique ID using the same dark/coral switch design;
- uses a Google SDK license confirmation, official direct Android SDK Platform 36 download and pinned SHA-256 `37607369a28c5b640b3a7998868d45898ebcb777565a0e85f9acf36f29631d2e` (no SDK ZIP mirror);
- includes native Kotlin Gradle plugin resolution for AGP **8.11.0** and Chaquopy **17.2.0**;
- displays Ready only after the particular tool's real installation/test succeeds.

The GitHub Python CLI installer is **for CI/compatible hosts**; the Android app has separate **native Kotlin integration**. The patched Kotlin ToolStore/ManagedToolResolver compiled in a standalone JVM check, and SDK ZIP layout plus catalog merge/dependency tests passed. **Android project APK compilation and execution on the user's actual phone remain unverified**. The revised app ZIP was delivered in the conversation, not published as a source repository commit.

An important distinction: the IDE's own Code on the Go Gradle build uses AGP 9.3.1 / Kotlin 2.3.21 / Gradle 9.6.1; these pre-existing IDE build dependencies were deliberately preserved. The optional downloaded toolchain is separate (AGP 8.11 / Kotlin 2.1.20 / Gradle 8.14.3). Do not mix the two build profiles.



## Extended toolchains for broader Android ZIP builds (20 November 2026)

See **[Extended Toolchains + Safe ZIP Builder](toolchains/README.md)** for 20 optional
provisioning routes across Java/JDK, Android SDK/NDK/CMake, Gradle, Flutter,
Buildozer, python-for-android, Chaquopy, APK signing, debugging and linting.

- [Extended route registry](toolchains/extended-tools.json) — **not** a downloadable binary list.
- [Project ZIP detector and APK builder](toolchains/zip_builder.py) — inspect without execution; `build --execute` for reviewed projects.
- [Google SDK/NDK/CMake installer](toolchains/sdk_installer.py) — supported desktop hosts, official sdkmanager and explicit SDK license consent.
- [Passing ZIP safety CI](https://github.com/magic616star666-bot/python-eye-toolchain/actions/workflows/verify-extended-toolchains.yml) — tested on GitHub Linux runners, **not** on the user's Android phone.

The existing eight-tool `tools.json` remains unchanged for compatibility with
the delivered Kotlin Extensions parser. Extended routes must be integrated as
a separate catalog until the app's parser and real Android-native runtime
are updated. Generic Python/Java ZIPs without Android packaging cannot
be automatically converted into APKs.


### Real host toolchain verification (20 November 2026)

[**7-job passing GitHub Actions run**](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44613219027):
JDK 8/11/21 Java compile-and-run; Kotlin 2.1.20 / AGP 8.11 real APK;
SDK 36 / Build Tools 35 / NDK 27 / CMake 3.22 executable checks;
Flutter 3.47.9 real Android APK; Buildozer + python-for-android import and CLI checks.

See [CI evidence and limitations](toolchains/CI_PROOF.md), the
[automatic ZIP dependency planner](toolchains/plan_project.py), and
[real local-executable tool doctor](toolchains/probe_tools.py).
**All proof above is from GitHub Linux x86_64 CI, not actual Android phone
compilation.** The five pre-existing hosted Android tool ZIP/JDK archives
are unchanged and do not establish 28 on-device working binaries.


### Multi-version download and Android Bionic native archive routes

New: [JDK and Gradle multi-version installer](toolchains/versions_manager.py),
[Android SDK versions discovery](toolchains/sdk_versions.py),
[11 checksum-pinned Android/Bionic upstream archives](toolchains/mobile-artifacts.json),
[Android native installer/probes](toolchains/mobile_installer.py),
and [full setup instructions](toolchains/README.md).

[Live asset identity, size and SHA-256 checks PASS](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44617197516).
GitHub Linux executable checks and Android ARM64 on-device APK-build proof are separate; the native assets are NOT all phone-tested.
