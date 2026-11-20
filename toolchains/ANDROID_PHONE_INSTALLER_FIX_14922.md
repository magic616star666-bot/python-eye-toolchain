# Python Eye IDE v1.4.9.22 — phone installer corrective patch

This document tracks fixes applied to the **Android IDE application's Kotlin source** and the GitHub toolchain catalog. It does **not** claim all catalog items are installed or device-tested.

## Observed phone failures (2026-11-20)

1. Google SDK Platform 23 and other platform ZIP installs fail: `ZIP has no android.jar`. Root cause: the installer hardcoded `android-23/`, but official Google archives can contain differently named root folders (e.g. `android-6.0/`). Fix in `SdkPlatformLayout.kt`: find a paired `android.jar` and `source.properties`, verify any declared `AndroidVersion.ApiLevel`, reject ambiguous/missing paths, and normalize to `platforms/android-API/`.
2. NDK r28c/r29, Android ADB, D8/APKSigner, Build Tools 33/34: `toybox: Unknown command xzcat` (exit 127). Root cause: IDE assumed every Android `toybox` contains `xzcat`. Fix in `XzArchiveExtractor.kt`: probe actual toybox applet availability with `toybox --list` **before reading** the verified archive; use native subprocess only if supported, otherwise safe Java XZ decoding with memory-budget check. App requests `android:largeHeap="true"` to accommodate 256 MiB dictionary on phones with enough app heap; phones whose heap is too small fail clearly, never claim Ready.
3. AGP shown as `Needs d8-apksigner`, followed by Chaquopy `Needs android-gradle-plugin`. Root cause: the legacy `tools.json` falsely required standalone D8/AAPT2/SDK to *resolve* the AGP Maven plugin. Fixed live `tools.json` to require only JDK 17 and Gradle for AGP **plugin resolution**. The IDE's `ToolStore.parseCatalog` also sanitizes cached legacy AGP dependencies, and the bundled asset catalog has the corrected prerequisites. Building a real APK still needs compatible SDK/Build Tools/AAPT2; resolving plugin coordinates does not prove an APK build.

## Reproduction and host checks

- `tests/SdkPlatformLayoutSmoke.kt`: PASS for API 23 nested `android-6.0/`, API 34 `android-34/`, API 35 multi-level folder, API 36 flat package; refuses wrong API, missing `android.jar` and ambiguous roots.
- `tests/XzNativeStreamingSmoke.kt`: PASS with actual host-compressed `.tar.xz` through a real `xz -dc` process, archive traversal rejection and cancellation. The Java fallback branch was exercised with an **identity decoder stub**; it has **not** been validated with a 256 MiB dictionary on Android.
- `tests/ToolDependencySmoke.kt`: PASS for stale AGP dependency correction, Gradle + JDK install ordering.
- Kotlin tool-engine host compilation: PASS; Android APK compilation and installed native executable probes still require a phone.

## Device testing requested before claiming stable

Install the new APK, open Extensions, tap `Load catalog` to pull the corrected GitHub index when possible, then:
- SDK API 23 / 34: Load → Test. Verify `platforms/android-API/android.jar`.
- Build Tools 33 and ADB 34: Load → Test; no `Unknown command xzcat`.
- NDK r28c: Load → Test; confirm Clang syntax probe. Heap limits or community binary compatibility can still fail, in which case copy the detailed report.
- AGP: Load → Test, then Chaquopy: Load → Test; no dependency on independently installed D8.
- Finally build a representative Android Gradle project and a Python APK.

Catalog URL: [tools.json](../tools.json). The [official on-demand SDK/Gradle index](official-on-demand.json) and [native Bionic artifacts](mobile-artifacts.json) remain independent, metadata-only or pinned upstream sources. No third-party Android executables are mirrored into GitHub without license review.
