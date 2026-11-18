# Upstream sources and verification

The listed archives already exist as real assets in [GitHub Releases: toolchain-v1](https://github.com/magic616star666-bot/python-eye-toolchain/releases/tag/toolchain-v1).

| File | Original upstream | Verification |
| --- | --- | --- |
| `jdk17-android-bionic-17.0.11.tar.gz` | https://github.com/MobileStudio-AndroidIDE/MobileStudio_AndroidIDE/releases/tag/MobileStudio-JDK17-Android-ARM64 | SHA-256 pinned to upstream GitHub Release asset digest; verified AArch64 Android Bionic ELF. Old `jdk17-arm64.tar.xz` remains only as a rollback archive. |
| `gradle-8.14.3-bin.zip` | https://services.gradle.org/distributions/gradle-8.14.3-bin.zip | Official published Gradle SHA-256 |
| `android-sdk-tools-static-aarch64.zip` | https://github.com/lzhiyong/android-sdk-tools/releases/tag/35.0.2 | Recorded archive SHA-256; contains ARM64 AAPT2 and Zipalign (audited) |
| `build-tools-34.0.4-aarch64.tar.xz` | https://github.com/AndroidIDEOfficial/androidide-tools/releases/tag/v34.0.4 | Recorded SHA-256; contains D8/APKSigner scripts and JARs, not a complete 35.x Build Tools |
| `kotlin-compiler-2.1.20.zip` | https://github.com/JetBrains/kotlin/releases/tag/v2.1.20 | Official JetBrains SHA-256 |

See `JDK17_BIONIC_AUDIT.json` for the new JDK archive SHA-256, size, root folder and ELF verification. The Release additionally includes a standalone `aapt2-arm64-v8a` and initial publication provenance files. The catalogue does not duplicate it as another AAPT2 tool. Verify all five **live Release digests** against `tools.json` with `python scripts/verify_release_assets.py`.

Neither package presence nor ELF AArch64 metadata proves a working Android IDE build. Users' Java/Gradle/SDK paths, library dependencies, Android Bionic execution and AAPT2 substitution still need device testing.

**Licenses:** Respect each upstream tool's respective license and preserve notices. The Google SDK Platform must be acquired and licensed through Google's SDK Manager; do not mirror proprietary SDK files unless redistribution is expressly permitted. No signing keys or secret credentials belong in this public repository.
