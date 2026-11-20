# Python Eye IDE v1.5.1 — Consolidated Android/Bionic Tool Integration

**ONE SOURCE RELEASE.** The code ZIP for **Old Python Eye** and **Code On Go** contains the full Android-native tool inventory and integrated installer UI. This GitHub repository continues to host distribution manifests and pinned archives, not a compiled working IDE APK.

## Tool support ledger
- **53** classified workflow routes (21 Android core / 19 optional native / 13 blocked or unported).
- **37** GitHub SHA-256-pinned native Android/Bionic archive candidates, now also bundled in app assets for an offline first-run; they are NOT installed binaries.
- **67** Gradle versions and **14** SDK-platform entries in the online version resolver.
- All version candidates are accessible in Extensions; the old list limit showing only four candidates per route has been removed.
- Native test source consent and per-tool direct CLI probes remain required.

## SDK Build-Tools 36 guidance
1. **Prepare native prerequisites** button starts explicit user-approved Load/Test of AndroidIDE Bionic Build-Tools 34.0.3. This is a source of Android-host binaries; it does NOT relabel the 34.0.3 native archive as an official Google 36 package.
2. **Install genuine Google SDK Build-Tools 36.0.0** downloads original Google package only after license/download approval, validates its recorded size and SHA-1, stages it, overlays tested Bionic aapt2/aidl/zipalign, individually invokes CLI tests, then activates with rollback.
3. Installer now probes AAPT2/AIDL/zipalign versions AND valid usage dialects, drains process stdout concurrently to avoid false hangs, and rejects loader errors. It re-probes an already-installed package rather than trusting files-only checks.
4. Catalog cache updates replace the old cache only after successfully writing a complete validated download. Offline app assets provide fallback when GitHub is unreachable.

## Verified host tests
- Kotlin JVM tools/build/util backend (26 non-Android source files): compile PASS on Old variant.
- Byte-for-byte compare 29 backend source files: Old and Code On Go identical.
- Offline assets: 37 distinct native sources, 53 distinct routes, SHA/URL/readiness flags validated in both.
- Host-script simulations: AAPT2, AIDL, zipalign usage variants PASS; fake dynamic-loader failure rejected.
- Existing unified manifest tampering, SDK AGP9 detection, license-consent smoke tests: PASS.
- Original v1.5.0 source files retained; ZIP integrity audited.

## Unverified device-only requirements
Actual Android handset downloads and binary execution are **not performed by this GitHub CI or JVM tests**. All 53 are not installed or ready. 13 workflows are still unported. SDK36 Bionic compatibility and the imported AVIRA Algo AGP9 APK must be proved on the device. D8 previously exhausted heap at ~1.6 GiB available RAM. A source release cannot guarantee that memory fits or that an APK builds.

**Sources:** [unified manifest](python-eye-unified-android-arm64.json), [native archive list](mobile-artifacts.json), [official SDK/Gradle catalog](official-on-demand.json), [existing build guide](PYTHON_EYE_UNIFIED_BUILD_GUIDE.md).
