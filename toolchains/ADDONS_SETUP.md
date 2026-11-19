# Python Eye IDE — Additional Android APK Toolchains

Updated: 20 November 2026. This is a real code update to the public toolchain repository, not a change to the Android IDE APK.

## New optional tool families (25 unique IDs)

The new [addon registry](addons-catalog.json) includes Apache Maven, Apache Ant, Kotlin KSP/KAPT/Compose compiler plugins, Android AIDL, Ninja, LLVM/Clang, Rustup, Cargo, Node.js/npm, React Native, Expo, Expo EAS, Capacitor, Cordova, BeeWare Briefcase, Flet, Git, APK Analyzer, Logcat, release signing, Gradle compatibility and cloud-build fallback.

These 25 entries **describe support routes and prerequisites**; they are NOT 25 binaries uploaded to Releases. Existing eight-tool tools.json and twenty-tool extended-tools.json are preserved. The new combined [Setup Manifest](setup_extensions.py) reports exactly 53 unique IDs and always starts with Ready=false until the relevant CLI actually passes on the current host.

## Real GitHub Linux CI proof

[Additional toolchain CI run — five jobs PASS](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44622667164):

- Maven 3-compatible project produced a real Java JAR; Apache Ant compiled the same Java source into class files.
- Ninja and Clang compiled real C source; Cargo built and tested a Rust library; Git version ran.
- Node/npm actually installed and executed pinned Capacitor CLI 7.0.0 and Cordova CLI 12.0.0.
- Python virtual environments installed and executed Briefcase 0.3.26 and Flet 0.28.3.
- Framework detection, safety and no-fake-ready regression tests passed.

The CI above proves **tool execution on a GitHub Linux host**, NOT all possible APK builds or Android ARM64/Bionic phone execution. KSP/KAPT/Compose plugins are selected by matching the *project's* Kotlin/Gradle setup; they must resolve and compile for each project. React Native/Expo and other families have detection and build routes but require a correctly prepared Android project and compatible host toolchains.

## ZIP project auto detection

[Existing zip_builder.py](zip_builder.py) and [project planner](plan_project.py) now handle:

| ZIP type | Status |
| --- | --- |
| Android Java/Kotlin/Chaquopy Gradle app | Existing real build route |
| Flutter app | Existing real build route |
| Buildozer Python app | Existing Linux/macOS build route |
| React Native / Expo | Build route only if existing android/ Gradle project |
| Capacitor | Build route only if Android project is generated |
| Cordova | Build route only if cordova-android platform is installed |
| BeeWare Briefcase | Opt-in Android package route; dependencies required |
| Flet Python | Opt-in flet build apk route; Flutter required |
| Maven/Ant Java, standalone Rust, ordinary Node/Python | Detected, not falsely treated as an APK project |

All project ZIP extraction blocks traversal/symlinks. Build scripts are only executed after explicit --execute and only with required CLIs present. The produced APK must be a real ZIP containing AndroidManifest.xml.

## Commands

Read-only merged manifest: python3 toolchains/setup_extensions.py --compact

Probe installed local CLIs: python3 toolchains/setup_extensions.py --probe --compact

See per-project required tool IDs: python3 toolchains/setup_extensions.py --project my-project.zip --compact

Inspect a project ZIP: python3 toolchains/zip_builder.py inspect my-project.zip

Build a trusted compatible ZIP: python3 toolchains/zip_builder.py build trusted.zip --execute --output ./built-apks

List installable CLI packages: python3 toolchains/provision_addons.py list

Install pinned Capacitor in isolated directory with consent: python3 toolchains/provision_addons.py install --id capacitor-cli --version 7.0.0 --approve-install

Install pinned BeeWare with consent: python3 toolchains/provision_addons.py install --id beeware-briefcase --version 0.3.26 --approve-install

Read-only APK validation: python3 toolchains/apk_tooling.py inspect path/to/app.apk

Real APK signing uses apksigner, zipalign, a **user-owned keystore**, explicit --execute, and PYTHON_EYE_KS_PASS environment secret (never commit it). For AAB verification supply an official bundletool jar and use validate-aab --execute. Logcat requires --execute and Android Debug Bridge permissions.

## Device setup and boundaries

- The Android-native binaries in mobile-artifacts.json have upstream asset digests, but have **not all been executed inside Python Eye** on the user's phone.
- GitHub Actions workflows are examples of a cloud build fallback, not a live remote APK-building service integrated with the app.
- Android IDE Kotlin Extensions UI source is **not** this public toolchain repo. It must load addons-catalog.json separately instead of injecting 25 new IDs into the legacy 8-ID format.
- Don't present Kotlin plugin cache or Maven/npm/pip downloads as Ready without local execution and project compilation proof. Never claim ordinary Java/Python/backend ZIPs automatically become Android apps.

## Official vendor documentation

- [Kotlin compiler plugins and KSP](https://kotlinlang.org/docs/compiler-plugins-overview.html)
- [Jetpack Compose compiler](https://developer.android.com/develop/ui/compose/setup-compose-dependencies-and-compiler)
- [React Native Android](https://reactnative.dev/docs/running-on-device)
- [Expo local builds](https://docs.expo.dev/build-reference/local-builds/)
- [Capacitor Android](https://capacitorjs.com/docs/android)
- [Cordova CLI](https://cordova.apache.org/docs/en/latest/reference/cordova-cli/)
- [BeeWare Briefcase](https://briefcase.beeware.org/en/latest/)
- [Flet Android publishing](https://flet.dev/docs/publish/android/)
