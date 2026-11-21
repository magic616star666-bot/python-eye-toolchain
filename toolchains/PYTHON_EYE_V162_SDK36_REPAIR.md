# Python Eye IDE v1.6.2 — Direct SDK Build-Tools 36 Repair (Android ARM64)

This release integrates a repair action into **Build APK** for imported Android Gradle Plugin 9.x projects. It is a **source release**; no installation has been remotely performed on the owner's phone.

## Exact previous failure

Imported AGP 9.3.1 needs SDK Build-Tools 36.0.0. With Build-Tools 36 missing, Python Eye v1.6.1 blocked the APK before launching Gradle. That was correct validation, but the build screen did not offer a working direct route to the existing consent-based installer and misleadingly reported **Static problems: 0**.

## Implemented in BOTH Old Python Eye and Code On Go source

- **Build APK → Repair SDK 36:** when a project is AGP 9.x and the true Build-Tools 36 directory fails identity/binary checks, the build action offers a direct repair step. The route opens Extensions and the Android-native source approval / test flow.
- Android/Bionic native prerequisite discovery now tries available SHA-256-pinned candidates in priority order, instead of stopping permanently after the first Build-Tools 34.0.3 provider. A failing provider is not considered Ready, and each third-party download requires explicit approval.
- When a tested provider supplies genuine native `aapt2`, `aidl`, `zipalign`, the existing **official Google Build-Tools 36.0.0** download requires separate Google SDK license/download approval, verifies the official checksum and size, and performs staged native ELF + CLI probes before activation with rollback.
- **Full Build Doctor** now includes missing AGP9 Build-Tools 36 in the *initial static problems count*, rather than reporting zero static problems and failing later.
- Original source files, Python 3.10–3.15 APK profiles, all 53 workflow routes, 37 checksum-pinned native candidate records and original tools remain present.

## Verification and limitations

- Kotlin JVM backend (tools, builder, utilities) compiles on host (Android-specific UI requires Android device/AGP toolchain).
- Host tests: native candidate fallback, imported AGP9 initial doctor blocker, UI action/source wiring and ZIP file integrity passed.
- **No on-device download, SDK license approval, native binary execution, or AGP 9.3.1 APK build was performed or claimed in this source environment.**
- Build-Tools 36 is not bundled in the app ZIP. Google's 64 MB official package and the Android/Bionic native providers must be downloaded and tested **on the phone** with permission.
- Low available memory (~1.8 GiB in latest phone log) may still cause D8 Java heap failures even after SDK 36 is repaired.
- Other 13 unported framework routes remain unsupported; a catalog is not a runtime installation.

Run **Build APK → Repair SDK 36 → approve the third-party native source → approve Google SDK terms/download → verify SDK 36 → Build APK**.

See [unified toolchain](python-eye-unified-android-arm64.json) and [native asset list](mobile-artifacts.json). The full app source ZIP is shared separately; this GitHub repository is a toolchain distribution catalog.
