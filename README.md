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
