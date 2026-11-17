# Remaining three Android build components — managed install routes

The **actual installers/configuration** for SDK Platform 36, Android Gradle Plugin 8.11.0 and Chaquopy 17.2.0 are described in `managed-tools.json`. These aren't three standalone binary ZIP files.

- **SDK 36**: Google's `sdkmanager` installs `platforms;android-36`, subject to user agreement to the Android SDK license. **Do not mirror Google's SDK platform as a GitHub Release asset without appropriate redistribution rights.**
- **AGP 8.11.0**: Gradle plugin `com.android.application` resolved from `google()`, requires JDK 17 and Gradle 8.13+.
- **Chaquopy 17.2.0**: `com.chaquo.python` resolved via Maven Central, compatible with AGP 8.11 and Python 3.10, Android minSdk 24.
- **Google SDK Build Tools 35.0.0 or later**: required for AGP 8.11. Our old ARM64 Build Tools 34.0.4 is insufficient. On Android phones Google-provided x86_64 executables must be replaced or overridden with tested Android ARM64 builds.

A real sample Android application lives in `apk-smoke-test/`. The GitHub Actions workflow `Build Real Python APK` downloads the official Android platform and Gradle plugins and compiles Python into a debug APK. Its success or failure is recorded in the Actions tab.

## Next Android app integration work

The Python Eye IDE app's extension installer needs to support 2 types beyond the current archive downloader:

1. `android_sdk_manager`: show Google's license, get user approval, download from official SDK Manager, validate `android.jar`.
2. `gradle_plugin_resolution`: create/use a Gradle Android project, resolve plugin and all transitive Maven artifacts, report success only after an actual build.

**The IDE Kotlin source was not supplied**, so the two installer types cannot be wired into its switches directly here. Do not set `Ready` based on a JSON entry alone. Existing uploaded binaries may report Ready, but that is not end-to-end APK build proof.
