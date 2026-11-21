# Python Eye IDE v1.6.1 — Android native Load / Test consolidation

Source-level Android ARM64/Bionic integration. A route in a catalog is not a working installation.

## GitHub to Android IDE
- 53 workflow routes (21 core, 19 optional, 13 not ported).
- All 37 checksum-pinned Android ARM64 native archive candidates are bundled in app assets as offline metadata and connected to individual Load / Test actions.
- New batch selector: six recommended APK-related packages, or all 37 candidates (~4023 MiB compressed; much more disk can be needed after extraction). Explicit action required.
- Fixed lost queue bug: previous third-party approval resumed only one selected tool; now the entire selected installation queue survives. Consent is scoped per provider to selected archives only.
- Explicit checksum and size validation, staged extraction, runtime CLI test, no automatic Google SDK license acceptance.
- SDK36 native prerequisites and genuine Google SDK36 installer are connected, with Android ARM64 shared-library discovery and linker runtime paths for Gradle child processes.
- Full 53-route version search, expand all versions, and no 35-entry UI cap.

## Verification and limits
- Host Kotlin tools/build compile passed for both source variants; host catalog, checksum metadata, SDK detection and probe smoke tests passed.
- No Android APK or native CLI was executed on the user's handset; such device tests remain required.
- 13 blocked routes (including local python-for-Android and Flutter) are not working Android/Bionic ports.
- Python 3.10 to 3.15 are Chaquopy APK build-time options, not six installed on-device interpreters.
- Build-Tools 36 final phone installation and D8 memory behavior remain unverified.

The IDE application sources are distributed as separate ZIPs in ChatGPT, not inside this toolchain metadata repository.
