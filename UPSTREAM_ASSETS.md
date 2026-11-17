# Actual upstream binary package sources

These are **prebuilt binaries from their respective upstreams**, mirrored for Python Eye IDE's optional tool downloader. They are not original Python Eye builds and have **not been tested inside Python Eye IDE**.

| File | Source | Verification |
| --- | --- | --- |
| gradle-8.14.3-bin.zip | https://services.gradle.org/distributions/gradle-8.14.3-bin.zip | Official Gradle 8.14.3 SHA-256 pinned |
| jdk17-arm64.tar.xz | https://github.com/itsaky/openjdk-17-android/releases/tag/01-01-2022 | SHA-256 computed after download; upstream digest unavailable |
| build-tools-34.0.4-aarch64.tar.xz | https://github.com/AndroidIDEOfficial/androidide-tools/releases/tag/v34.0.4 | SHA-256 computed after download; upstream digest unavailable |
| aapt2-arm64-v8a | https://github.com/AndroidIDE-Dev/platform-tools/releases/tag/v35.0.2 | Upstream GitHub Release SHA-256 pinned |

The GitHub Release also includes `SOURCE_SHA256SUMS.txt` and `PROVENANCE.json`.

**License/redistribution:** Gradle uses Apache 2.0; OpenJDK 17 generally uses GPLv2 with Classpath Exception; Android Build Tools may include components under differing licenses. Preserve upstream legal notices; review the licenses of individual tools before distribution in a commercial product. These assets do not grant permission to distribute third-party intellectual property beyond its license.

**Compatibility warning:** A binary built for Linux ARM64 (glibc) is NOT necessarily usable on Android ARM64 (Bionic). These packages were chosen for Android ARM64 origin (except Gradle, which is Java). Python Eye IDE has a separate installer and has not yet validated these paths, library dependencies or Gradle invocation.

The remaining catalog items Android SDK Platform 36, Kotlin, AGP and Chaquopy are still absent from this Release; SDK/AGP/Kotlin/Chaquopy must be version-matched and obtained via suitable upstream repositories/installers. 
