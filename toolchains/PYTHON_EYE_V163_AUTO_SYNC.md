# Python Eye IDE v1.6.3 — GitHub → app automatic tool catalog sync

The app now refreshes the trusted public **GitHub toolchain catalog when it opens or resumes**, with a 15-minute request cooldown to reduce unnecessary mobile traffic. Users can always tap **Extensions → Sync GitHub → new tools appear automatically** to force an immediate refresh.

## Publishing a new Android-native tool

1. Add a unique route to [the unified Android ARM64 toolchain manifest](python-eye-unified-android-arm64.json), preserving existing core/optional/blocked baseline categories.
2. Add its Bionic/AArch64 release archive under `native_archive_candidates` in the same manifest: GitHub Release HTTPS URL, matching provider, SHA-256, byte size, supported archive format (zip/tar.gz/tar.xz or constrained native Ninja binary), family and version. The manifest is **metadata only**.
3. GitHub Sync adds new routes beyond the baseline 53 and new pinned assets beyond the baseline 37. The first 53 routes remain in the bundled offline fallback; a cached synced catalog is used offline.
4. A new installable tool appears under Extensions, with **Load** and **Test** actions; the app must ask for third-party source permission, download the actual archive, verify checksum and Android/Bionic compatibility, and execute a real device CLI probe before saying Ready.
5. New tools **do not** automatically install. Google SDK license acceptance is always an explicit user action. Unsupported/blocked routes never display an install button.
6. Real APK build/install verification remains separate from metadata Sync or a successful CLI probe.

## Safety and limitations

- The app rejects malformed or non-Android/Bionic catalogs, duplicate routes, unsupported families, invalid digests, off-domain release URLs, and remote claims of installation/proof.
- The unified JSON is the primary source for both routes and new native archive candidates. The separate [mobile archives catalog](mobile-artifacts.json) remains a fallback for legacy entries; syncing either one will never silently replace existing installed binaries.
- The app checks on open/resume, **not continuously in the background**. Updates appear next time the app connects or by tapping Sync.
- Tool candidates are **not** evidence that the listed tools work on the user's phone. Build-Tools 36, python-for-Android local porting, memory constraints and unported tool categories remain separate issues.

The IDE source ZIP is distributed separately from this GitHub metadata-only repository; source compile tests are not an Android APK-build result.
