# Python Eye IDE — 51 Android ARM64 Extensions

The consolidated [51-entry catalog](python-eye-extensions-51.json) has **37 Android ARM64/Bionic upstream archives**, **8 pinned legacy tools**, **5 additional official SDK/Gradle versions**, and **1 local demo**.

## What GitHub has (and does not have)

- Every catalog entry identifies its source, version and download route. SHA-256 is pinned where the asset is downloadable.
- Existing third-party archives remain at original upstream GitHub Release URLs. No unauthorized binary mirroring or false claim that all 51 binaries were uploaded to this repository.
- These are **51 catalog entries**, not 51 guaranteed working binaries. Their device status depends on actual Load → verified bytes → safe unpack → Test on the Android phone.
- Official SDK packages require explicit license acceptance. Loading SDK 36 does **not** automatically install SDK 34 or Build Tools 34.0.0.

## Android NDK .tar.xz crash (r28c/r29/r30)

Android NDK archives can use an LZMA2 dictionary requiring around **262248 KiB**. The prior Python Eye IDE Java installer enforced **65536 KiB**, producing a misleading “invalid .tar.xz” error. The fix in IDE **v1.4.9.19** streams verified compressed data through Android’s system `xzcat` (or `toybox xzcat`) in a separate native process and retains safe TAR path and size checks. A guarded Java fallback is available only with sufficient heap. **Real device extraction still needs verification.**

## Imported Gradle projects requesting Android 34

The IDE’s default active SDK is SDK 36. For an imported project that needs SDK Platform 34 or Build Tools 34.0.0, first Load and Test the matching versions in Extensions. The v1.4.9.19 builder stages **already installed and tested** components into its active SDK root; it does not auto-accept licenses or silently download a missing component. If the requested version is absent, the builder prints a precise diagnostic before attempting Gradle.

## Readiness labels

- Downloaded + SHA-256 verified ≠ CLI passed.
- CLI passed ≠ Android APK compiled.
- A device build cannot be certified from GitHub metadata alone.

The Android project ZIP contains `XzArchiveExtractor.kt` and patches in `ToolStore.kt`, `GradleApkBuilder.kt`, and `ExtensionsScreen.kt`.
