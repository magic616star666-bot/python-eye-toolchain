# Real Android SDK 36 + AGP + Chaquopy managed installer

The three remaining Python Eye IDE tool types are **not standalone archives**. They are retrieved from the official repositories and configured by `installer/managed_installer.py`.

## What the installer actually does

| Tool ID | Action | Source | Proof of installation |
|---|---|---|---|
| `android-sdk-36` | `sdk` | Google's `sdkmanager`: `platforms;android-36` and `build-tools;35.0.0` | SDK `android.jar` and Build Tools `source.properties` found on disk |
| `android-gradle-plugin` | `plugins` | Gradle `com.android.application` **8.11.0**, Google Maven | Real Android APK build succeeds |
| `chaquopy-build` | `plugins` | Gradle `com.chaquo.python` **17.2.0**, Maven Central | Real Android APK build including Python succeeds |

The script pins JDK **17**, Gradle **8.14.3**, Android SDK API **36**, Android SDK Build Tools **35.0.0**, Chaquopy **17.2.0**, AGP **8.11.0** and Python **3.10**. It never calls a package "ready" simply because a JSON record or download exists.

## Invocation by the Android app

The host IDE will need a process runner exposing its Android-compatible JDK, a `GRADLE_BIN` executable, and an SDK Manager. Set `ANDROID_HOME` or pass an IDE-writable `--sdk-root`.

- `python3 installer/managed_installer.py status --sdk-root <IDE_SDK_ROOT>`: returns JSON readiness.
- `python3 installer/managed_installer.py sdk --sdk-root <IDE_SDK_ROOT> --accept-sdk-license`: official SDK download. **Only pass this flag after the user has read and explicitly accepted Google's SDK terms.**
- `python3 installer/managed_installer.py plugins --sdk-root <IDE_SDK_ROOT>`: resolves AGP and Chaquopy through Gradle, performs a real APK build, and stores a local success marker.
- `python3 installer/managed_installer.py all --sdk-root <IDE_SDK_ROOT> --accept-sdk-license`: complete process after user consent.

Required environment overrides: `JAVA_BIN`, `GRADLE_BIN`, and `SDKMANAGER_BIN` if these programs are not on PATH. The script returns a nonzero exit code and a JSON error if any step is unavailable or fails. It does **not** modify device settings or silently accept Android SDK terms.

## GitHub CI verification vs mobile integration

[GitHub build workflow](../.github/workflows/build-python-apk.yml) exercises the real SDK Manager and Gradle resolution against `apk-smoke-test`, and confirms all three ready flags from that **CI runner's** successful APK build. This does not prove the binaries will execute on Android.

**Not yet integrated:** The user's Python Eye IDE Kotlin source is not present in this repository. Its Extensions Manager must call the above installer through a working runtime, read JSON results, dedupe built-in and remote tool records by ID and toggle a green Ready flag only after the on-device installation succeeds. Until then, `tools.json` deliberately keeps `published: false` for these three, because they aren't Release ZIP assets and the app has not implemented this managed-install method.
