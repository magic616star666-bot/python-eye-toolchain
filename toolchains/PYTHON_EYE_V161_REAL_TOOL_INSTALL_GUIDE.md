# Python Eye IDE v1.6.1 — direct native tool installation integration

Source integration delivered as Old Python Eye and Code On Go ZIPs outside this metadata repository.

## What is connected

- Full offline inventory of **53** workflow routes (21 core, 19 native-optional, 13 blocked/unported).
- **37** checksum-pinned Android/Bionic tool archive candidates; displayed offline and verified against GitHub manifests when online.
- **Install 6 recommended** or **Install all 37 candidates** via explicit opt-in. Not all are required for a given project. 37 candidates include alternative NDK/Build-Tools versions and use several GB compressed plus much larger unpacked storage.
- Per-provider user permission, SHA-256 + archive-size verification, secure extraction, native CLI probe and status distinct from APK success. Cancel stops queued downloads, and the existing SDK remains protected on unsuccessful install.
- SDK 36 guided flow: an Android/Bionic Build-Tools candidate is loaded and probed before the official Google Build-Tools 36 package is downloaded with separate license consent. Genuine SDK36 files are staged, ARM64/Bionic native binaries overlayed only after verification, CLI probed, and failure rollback attempted.
- App's Gradle process inherits explicitly probed ARM64 native library paths.
- Python 3.10–3.15 APK build profiles are preserved; this does not install six independent Python interpreters.

## Source-side verification

Host Kotlin backend compiles for both source variants; smoke tests cover 37 native archives, provider-specific approval groups, 6 recommended tools, AAPT2/aidl/zipalign version/help dialects, native-linker-failure rejection, and bundle ZIP integrity. Baseline v1.6.0 source files retained.

## Hard limitations — not claimed complete

The archive catalog does **not** mean any of 37 binaries are already installed on the owner's phone. All downloads and first-run tests require internet, user permissions, disk, and device execution. 13 unported categories still have no functioning local Android CLI port. SDK36 and AGP9 APK-build success on the owner's phone is unverified, as is D8 memory sufficiency. No binary or package identities have been fabricated. This document is a source integration report, not a certified Android APK or a guarantee of 100% tool readiness.

Use: **Extensions → Load Android GitHub tools → Load 6 recommended → Run installed tools doctor → Prepare/Install Build-Tools 36 → APK Build**.

Sources: [Unified 53 routes](python-eye-unified-android-arm64.json), [37 archive candidates](mobile-artifacts.json), [Build-Tools 36 details](PYTHON_EYE_UNIFIED_BUILD_GUIDE.md).
