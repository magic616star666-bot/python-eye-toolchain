# Real upstream tooling added

[GitHub Releases: toolchain-v1](https://github.com/magic616star666-bot/python-eye-toolchain/releases/tag/toolchain-v1)

## Published in this repository

Five **real upstream files** are uploaded and have recorded SHA-256 values:

1. `jdk17-arm64.tar.xz` (Android ARM64 JDK 17, upstream from itsaky).
2. `gradle-8.14.3-bin.zip` (official Gradle, verified against official published digest).
3. `build-tools-34.0.4-aarch64.tar.xz` (AndroidIDE Android ARM64 build tools; supplies components corresponding to two catalog entries).
4. `aapt2-arm64-v8a` (additional Android ARM64 AAPT2, verified against upstream GitHub SHA-256).
5. `kotlin-compiler-2.1.20.zip` (official JetBrains Kotlin distribution, validated against JetBrains SHA-256 file).

The catalog lists five published entries, but the Android Build Tools archive is shared by two entries, and the newer standalone AAPT2 is an extra Release asset.

## Other three tool entries

- **SDK Platform 36:** fetch through Google's official Android SDK Manager package `platforms;android-36`, and accept applicable SDK licenses.
- **Android Gradle Plugin:** Gradle plugin `com.android.application` version `8.11.0` from `google()`.
- **Chaquopy:** Gradle plugin `com.chaquo.python` version `17.2.0`, using Maven/Gradle repositories.

Configuration details are in `official_install_routes.json`. These are official dependency installation routes rather than individual rehosted ZIP files. **They are not yet wired to Python Eye's mobile installer and remain unpublished in the catalog.**

## Important

All Release downloads are physically uploaded and verified as downloadable GitHub Release assets, but are **not yet verified by running them on the user's Python Eye IDE**, and are **not proof that APK building works**. Use the repository's `tools.json` in your IDE only after matching the Kotlin catalog schema and unpack/install routines.

The JDK17 Android archive is an older upstream build. A security-supported modern build is preferred for production use; do not treat this as a current security update.
