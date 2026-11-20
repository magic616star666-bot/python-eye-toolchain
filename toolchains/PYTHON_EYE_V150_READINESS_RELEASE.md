# Python Eye IDE v1.5.0 — consolidated Android builder readiness

This is a **source-code release**, not a fully tested phone APK and not a promise that every listed tool is installed. The GitHub distribution catalog remains the [single unified 53-route source](python-eye-unified-android-arm64.json), with 21 core, 19 native-optional, 13 unported/blocked workflows, 37 SHA-256-pinned native archive candidates, 67 Gradle releases and 14 SDK platform entries. None are marked working solely because they are listed.

## What's integrated into both Android IDE source variants

- **Full Android Readiness Matrix** in Extensions and the imported-project Build Doctor. Its read-only checks cover SDK package identity (including android-34-ext12 mistakenly unpacked under android-34), recorded SDK license consent, AGP 9.x minimum Build-Tools 36.0.0, explicitly pinned lower Build-Tools, compileSdk, missing installed platforms, and D8 memory risk.
- Old broken but **unused** build-tool versions generate warnings rather than blocking unrelated projects.
- Existing genuine Build-Tools 36 Google package download/checksum/rollback flow, Android/Bionic executable probes, 53-route inventory, terminal, tool Load/Test, SDK 34 correction, and RAM-aware Gradle launcher are retained.
- Distinct **Old Python Eye** and **Code On Go** source ZIPs preserve all baseline source entries.
- **13/13 JVM readiness tests passed for each variant.** This includes malformed package identity, AGP9, 36 blocker, missing license, low RAM and version-catalog uncertainty checks.

## Honest remaining device-only gates

1. Complete the user-approved Build-Tools 36 download and verify matching Android/Bionic aapt2/aidl/zipalign executables **on the Android handset**. Google official Linux 36 archive alone has Linux desktop-native binaries.
2. Verify actual APK compilation under AGP 9.3.1. Device D8 merging previously hit OutOfMemoryError at ~1.6 GiB available RAM even with a ~1 GiB child JVM heap; no static ZIP release can guarantee this workload fits.
3. Run on-device Load + Test for every tool that is actually installed, then verify install/run of an output APK. 13 unported routes are still blocked. Never call these 53 installed or verified without real device proof.

The existing GitHub toolchain repository hosts distributions and manifests, **not** the IDE application source ZIP; the complete source is shared separately in ChatGPT. Source/host tests do not equal a working APK.
