# Python Eye IDE · Unified Android ARM64/Bionic Toolchain (complete audit)

**This is one catalog covering all 53 existing workflows, not a claim that 53 programs are installed.** The audit is generated from the existing Android-only profile and pinned native archive catalog. Every candidate remains unverified on the owner's device until tested there.

| Class | Count | Current integration policy |
|---|---:|---|
| Core Android/Gradle/JVM routes | 21 | Inspect installed runtime or resolve a known Maven/Gradle coordinate |
| Android-native optional routes | 19 | Offer explicit Download/Load only for pinned Android/Bionic binaries; test each executable |
| Not ported or blocked routes | 13 | Never offer Linux desktop binaries as a mobile installer |
| Pinned Android/Bionic archive candidates | 37 | Upstream URL, expected size, SHA-256 recorded; **device-ready false** |
| Known Gradle releases | 67 | Version/ZIP resolver only; no offline claim |
| SDK platform package entries | 14 | Official package metadata; user license consent required |

**Single source of truth:** [python-eye-unified-android-arm64.json](python-eye-unified-android-arm64.json). CI validator [verify_unified_android_catalog.py](verify_unified_android_catalog.py) checks catalog integrity.

## Required pipeline for every imported Android project

1. Inspect `settings.gradle[.kts]`, `libs.versions.toml`, `build.gradle[.kts]`, wrapper properties; resolve AGP, Gradle, Java, platform API, Build-Tools and optional NDK.
2. Compare those requirements with the **active** SDK package identity, binaries, licenses, and tested app-private installations.
3. Explain every missing dependency before Gradle starts. No silent version substitutions that violate AGP's minimums.
4. Ask user approval for each required license/download; validate SHA-256 of every pinned native archive.
5. Install into staging, enforce path traversal protection, promote only after successful extraction and metadata checks.
6. Execute an actual Android Bionic CLI probe for each binary and persist a dated report. Never mark a route Ready from the catalog alone.
7. Run the APK task with memory-safe workers. Verify output and optional on-device installation separately.

## AGP 9.3.1 blocker (Build-Tools 36.0.0)

Google's AGP 9.3.x requires **SDK Build-Tools 36.0.0 or newer**; 35.0.0 cannot override this minimum. A complete 36.0.0 directory must contain official version-matching SDK package files and real Android/Bionic aapt2/aidl/zipalign executables (not Linux glibc ARM64 files); license agreement must be explicitly accepted. The 37 pinned native candidate archives do **not** currently contain a verified and tested Bionic 36.0.0 full package. [Termux Android build-tools](https://github.com/termux/android-build-tools) is a potential source to evaluate. [Commit451 ARM tools](https://github.com/Commit451/android-arm-build-tools) targets **glibc Linux** and is **not** directly executable inside this Android application.

**Never fabricate a 36.0.0 directory, modify source.properties to lie about a revision, auto-accept Google licenses, or label an untested binary Ready.**

App integration: Python Eye Extensions > unified route inventory and per-tool Test/Load, plus active SDK audit and pre-build compatibility diagnostics. Android APK compilation and all tool executions require real testing on the user's handset. CI only validates metadata.


## Python Eye v1.4.9.33 — consent-based Google Build-Tools 36 installer

The IDE now includes an **explicitly approved** Google Build-Tools 36.0.0 download/staging flow. The official source is `https://dl.google.com/android/repository/build-tools_r36_linux.zip`, size **63,737,259 bytes**, Google SDK repository SHA-1 **b0b6376977657e8ad9b969bacf4093601da2c6fb**. These properties authenticate the official package bytes but do **not** imply its bundled x86/Linux binaries run on Android.

Installation checks: Google license consent, separately approved 64 MB download, SHA-1 and exact size, safe archive extraction, genuine Google source.properties, pretested Android/Bionic `aapt2`, `aidl`, `zipalign`, native executable subprocess tests, and atomic promotion/rollback of the active SDK folder.

Do not mark this path as device verified until an actual APK compilation and installation completes with AGP 9.3.x. Third-party native binaries require independent download approval, checksum and executable tests. No automatic license acceptance. Devices with ~1.6 GiB available RAM may still encounter D8 Java heap exhaustion.

This is a documented Android app source integration, **not a published prebuilt Bionic 36.0.0 binary**.
