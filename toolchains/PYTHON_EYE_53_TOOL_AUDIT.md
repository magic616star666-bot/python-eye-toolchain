# Python Eye IDE · Android ARM64 Tool Inventory (v1.4.9.31)

**53 workflow routes ≠ 53 working binaries.** This inventory must never mark a tool Ready without an actual device CLI test, and an APK-builder Ready label needs a real APK build and install test.

## Critical missing dependency — Build-Tools 36.0.0

AGP 9.3.1 requires Android SDK Build-Tools 36.0.0. The current 37-candidate ARM64/Bionic native tool archive list contains no pinned tested Build-Tools 36.0.0 archive. Do not force 35.0.0 or use Google x86_64 binaries as Android/Bionic executables. SDK license acceptance requires explicit user consent.

## Android core / JVM routes (21)

| ID | Name | In-app state |
|---|---|---|
| `openjdk-17` | OpenJDK 17 | Route only; check Load + Test on phone |
| `gradle` | Gradle | Route only; check Load + Test on phone |
| `android-sdk-36` | Android SDK Platform 36 | Route only; check Load + Test on phone |
| `aapt2-zipalign` | AAPT2 + Zipalign | Route only; check Load + Test on phone |
| `d8-apksigner` | D8 + APK Signer | Route only; check Load + Test on phone |
| `kotlin-compiler` | Kotlin Compiler | Route only; check Load + Test on phone |
| `android-gradle-plugin` | Android Gradle Plugin | Route only; check Load + Test on phone |
| `chaquopy-build` | Chaquopy Build Plugin | Route only; check Load + Test on phone |
| `gradle-wrapper` | Per-project Gradle Wrapper | Route only; check Load + Test on phone |
| `android-sdk-platforms` | Android SDK API platforms | Route only; check Load + Test on phone |
| `android-gradle-plugin-resolver` | Per-project Android Gradle Plugin | Route only; check Load + Test on phone |
| `kotlin-gradle-plugin-resolver` | Kotlin Gradle Plugin | Route only; check Load + Test on phone |
| `r8-d8` | D8 / R8 | Route only; check Load + Test on phone |
| `apk-signing` | ApkSigner and Zipalign | Route only; check Load + Test on phone |
| `android-lint` | Android Lint | Route only; check Load + Test on phone |
| `bundletool` | Android App Bundle Tool | Route only; check Load + Test on phone |
| `chaquopy-python` | Chaquopy Python packaging | Route only; check Load + Test on phone |
| `ksp-gradle-plugin` | Kotlin Symbol Processing | Route only; check Load + Test on phone |
| `kapt-gradle-plugin` | Kotlin KAPT | Route only; check Load + Test on phone |
| `compose-compiler-plugin` | Jetpack Compose Compiler | Route only; check Load + Test on phone |
| `gradle-compatibility` | Gradle/JDK/AGP compatibility planner | Route only; check Load + Test on phone |

## Optional native Android routes (19)

| ID | Name | In-app state |
|---|---|---|
| `jdk-11` | JDK 11 | Route only; check Load + Test on phone |
| `jdk-21` | JDK 21 | Route only; check Load + Test on phone |
| `android-build-tools` | Android SDK Build Tools | Route only; check Load + Test on phone |
| `android-platform-tools` | ADB and Platform Tools | Route only; check Load + Test on phone |
| `android-ndk` | Android NDK | Route only; check Load + Test on phone |
| `android-cmake` | Android SDK CMake | Route only; check Load + Test on phone |
| `apache-maven` | Apache Maven | Route only; check Load + Test on phone |
| `apache-ant` | Apache Ant | Route only; check Load + Test on phone |
| `android-aidl` | Android AIDL compiler | Route only; check Load + Test on phone |
| `ninja-build` | Ninja | Route only; check Load + Test on phone |
| `llvm-clang` | LLVM/Clang toolchain | Route only; check Load + Test on phone |
| `rustup` | Rust toolchain manager | Route only; check Load + Test on phone |
| `rust-cargo` | Rust/Cargo | Route only; check Load + Test on phone |
| `nodejs` | Node.js | Route only; check Load + Test on phone |
| `npm` | npm | Route only; check Load + Test on phone |
| `git-cli` | Git | Route only; check Load + Test on phone |
| `apk-analyzer` | APK Analyzer | Route only; check Load + Test on phone |
| `logcat-debug` | Logcat / ADB debugging | Route only; check Load + Test on phone |
| `release-signing` | APK release signing | Route only; check Load + Test on phone |

## Not verified / unported in-app (13)

| ID | Name | In-app state |
|---|---|---|
| `jdk-8` | JDK 8 | Blocked / unverified |
| `android-cmdline-tools` | SDK Manager command-line tools | Blocked / unverified |
| `buildozer` | Buildozer | Blocked / unverified |
| `python-for-android` | python-for-android | Blocked / unverified |
| `flutter-dart` | Flutter SDK and Dart | Blocked / unverified |
| `react-native-cli` | React Native CLI | Blocked / unverified |
| `expo-cli` | Expo CLI | Blocked / unverified |
| `eas-cli` | Expo EAS CLI | Blocked / unverified |
| `capacitor-cli` | Capacitor CLI | Blocked / unverified |
| `cordova-cli` | Apache Cordova CLI | Blocked / unverified |
| `beeware-briefcase` | BeeWare Briefcase | Blocked / unverified |
| `flet-cli` | Flet CLI | Blocked / unverified |
| `cloud-build-fallback` | GitHub Actions cloud build option | Blocked / unverified |

## Integration

- App: **Extensions → Full Android tool inventory** plus **Audit installed SDK packages & license records**.
- GitHub toolchain metadata: [53 route JSON](python-eye-v14931-tool-audit.json), [37 archive candidates](mobile-artifacts.json), [on-demand Gradle and platform versions](official-on-demand.json).
- The IDE source ZIP is separate from this toolchain-distribution repository. The GitHub metadata does not contain a compiled or runnable APK.
