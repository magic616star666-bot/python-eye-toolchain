# Python Eye IDE Toolchain

This public repository holds the **tool catalog** for Python Eye IDE on Android ARM64. The user-facing IDE project is separate.

## Public catalog URL

https://raw.githubusercontent.com/magic616star666-bot/python-eye-toolchain/main/tools.json

The JSON root contains a `tools` array. **All entries are currently `not_published`**: the app must not try to install them yet.

## Tools represented

- OpenJDK 17
- Gradle (provisional 9.6.1; final version must be tested against AGP/Chaquopy)
- Android SDK Platform 36 (not the entire SDK)
- AAPT2 + Zipalign (Android ARM64 versions required)
- D8 + APK Signer
- Kotlin Compiler (provisional 2.3.21)
- Android Gradle Plugin
- Chaquopy Build Plugin

## Publishing a tool, safely

1. Select a real **Android ARM64-compatible** archive from its original project or a trusted vendor, and verify redistribution rights.
2. Test the binary **on an Android ARM64 device**. In particular, ordinary Android SDK host executables for Linux x86_64 will not run natively on the phone.
3. Upload the archive as an asset under **GitHub Releases** in this repository.
4. Compute its real SHA-256 using `sha256sum filename.zip`.
5. Change the matching entry in `tools.json`: give it a tested version, direct HTTPS asset URL, SHA-256, and set `published: true`, `status: "published"`.
6. Run `python scripts/validate_catalog.py`.
7. Test automatic download, checksum validation, installation, removal, rollback, disk use, and APK compilation in Python Eye IDE.

For actual Android APK builds, versions of Gradle, Android Gradle Plugin and Chaquopy must be mutually compatible. The SDK Platform package alone does not supply a complete build system. Do not publish signing keys, private tokens or licenses with restrictions on redistribution.

## App compatibility note

The IDE's Kotlin catalog parser has **not** been supplied or verified. This is a starter catalog and conforms to a root `tools` list, but exact field names and installer behavior must be aligned with the app before the **Load catalog** button can be marked working.

## Validation

```sh
python scripts/validate_catalog.py
```

## Upload a verified binary without terminal commands

When a legal-to-redistribute, Android-tested ZIP/JAR is available, go to **Actions → Publish Verified Tool Asset → Run workflow** and fill in:
- `tool_id` (from `tools.json`), `version`, **direct public HTTPS** source URL, SHA-256 checksum, and filename.
- Confirm **tested_on_android_arm64 = yes** only after the archive has really been tested on a physical Android ARM64 device.

The workflow downloads the asset, checks SHA-256, adds it to the `toolchain-v1` GitHub Release, and updates `tools.json` with a real Release download URL. A mismatch causes publication to stop. This pipeline has been added but has **not yet published any binary assets**.

**Important:** This repo does not currently host the Android build tools. The IDE's Kotlin parser and installer logic still need to be checked against this catalog before the in-app **Load catalog** flow can be declared working.


## ✅ Real Python APK build proof (2026-11-18)

The following **real build passed on GitHub Actions Linux CI**:

- Official Android SDK Platform 36 was installed from Google.
- Android Gradle Plugin 8.11.0 and Chaquopy Gradle Plugin 17.2.0 were downloaded/resolved by Gradle 8.14.3.
- Python 3.10 code was packaged into an ARM64-only Android debug APK (`app-debug.apk`).
- Verified APK size: **17,459,980 bytes**; SHA-256: `df7a59cdea7193f70415c5381eafbc3fba302e1f0c8045764f71d5dfa956bfc4`.

[Download APK from Releases](https://github.com/magic616star666-bot/python-eye-toolchain/releases/download/python-eye-apk-smoke-test/app-debug.apk) · [Successful Actions run](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44159445752)

⚠️ This validates a cloud-runner APK compilation, **not** running Gradle on an Android ARM64 handset. SDK36, AGP and Chaquopy are **managed installers** (official SDK Manager and Maven/Gradle dependency resolution), not three self-contained Release ZIPs. Their app-side on-device installers are not implemented without the Python Eye IDE Kotlin project. See `managed-tools.json` and `MANAGED_TOOL_INSTALL.md`.

⚠️ **Build Tools version gap:** AGP 8.11 requires Build Tools 35.0.0 or newer. The existing mirror of Android ARM64 34.0.4 tools alone is insufficient; ARM64 replacements / override for the newer host tools must be validated on the phone.

