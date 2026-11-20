# Python Eye IDE — ANDROID ARM64 ONLY 🚀

**Target:** Real Android device / arm64-v8a / Bionic libc. No Windows/macOS/Linux x86_64 installers in the Python Eye Android Auto Setup.

### Official Android selection

[android-only-profile.json](android-only-profile.json) is the **only** default IDE selection source. It classifies the existing 53 legacy/extended/addon entries without deleting their source catalogs:

- **21 Android core/JVM-managed workflows:** Bionic JDK 17, JVM Gradle, Android SDK platform data, Bionic AAPT2/zipalign, Kotlin and project Gradle plugins, signing, Java bytecode tooling. These are *routes*—all require appropriate device and project checks.
- **19 optional Android-native-dependent routes:** Android/Bionic JDK 11/21, NDK, CMake, ADB, AIDL, Ninja, Clang, Rust/Cargo, Node/npm, Git, etc. Some have native upstream assets; others are hidden from installation until a functioning Bionic executable is independently proven.
- **13 desktop-only or unported routes excluded from the mobile Auto Setup:** desktop sdkmanager, desktop Buildozer/p4a, Flutter/Flet/BeeWare and React Native/Expo/Capacitor/Cordova CLI tool installers that are not validated **inside the IDE app sandbox**, and cloud build.

**26 actual upstream Android/Bionic archives** are in [mobile-artifacts.json](mobile-artifacts.json), each with a real SHA-256, source link and recorded size. Release assets are hosted by the original upstream projects; not all are mirrored or executable-tested on the user's handset. A downloaded archive is NOT a working tool. A device CLI probe is NOT a successful APK build.

### Android-only Auto Setup CLI (the eventual app Extensions Manager can call this)

From inside Python Eye IDE's Android-arm64 Python runtime:

```bash
# Read-only Android-native candidates and recorded local installation states
python3 toolchains/android_setup.py catalog

# Which Android-local requirements does this project actually need?
python3 toolchains/android_setup.py plan --project /path/to/my-android-project.zip

# Check one native installed package without executing anything
python3 toolchains/android_setup.py status --asset openjdk-17-bionic

# Explicitly consent to downloading the existing upstream Bionic archive
# Third-party native code needs --approve-third-party.
python3 toolchains/android_setup.py install --asset android-cmake-3-22-1 --approve-download --approve-third-party

# Only after installation, explicitly run an actual executable probe ON THE PHONE
python3 toolchains/android_setup.py probe --asset android-cmake-3-22-1

# Advanced combined inventory is Android-filtered BY DEFAULT
python3 toolchains/setup_extensions.py --target android --project /path/to/my-android-project.zip
```

All commands refuse unapproved downloads/executable installation, and the mobile installer blocks non-Android/non-ARM64 environments. The target folder must be a compatible IDE-controlled executable location. Android OS application execution restrictions can prevent running unpacked binaries even after SHA-256 succeeds; report that error and do not mark Ready. Executable probe failure **must not be hidden** by ZIP metadata.

### Android build selection rules

1. A Java/Kotlin Android Gradle APK needs Bionic JDK, usable JVM Gradle, Android SDK platform data, Android-ready AAPT2, D8/signing, and compatible AGP/Kotlin artifacts. Verify the *same* project inside the phone IDE.
2. An Android NDK/CMake project additionally needs Bionic-host Clang/CMake/Ninja plus a compatible Android sysroot. Standard Google Linux x86_64/ARM64-host binaries are **not Android/Bionic executables**.
3. A Chaquopy-Python APK needs verified AGP/Chaquopy versions and native Python Android runtimes. A plain *.py file doesn't automatically become an Android app.
4. For Flutter, Flet, React Native, Expo, Capacitor, Cordova, BeeWare, Rust, etc., only show an install option **after** the relevant Android-host runtime is actually supported and phone-probed; never download Linux desktop distributions silently.
5. Keep Gradle, JDK, Kotlin, AGP and SDK versions matching the project. Arbitrary version upgrades can break APK builds.

### Status truth

- *Indexed*: a route exists. **Not installed.**
- *Downloaded*: archive checksum/size matches. **Not executable-verified.**
- *CLI probed*: tool was actually invoked in Android app runtime. **Not APK-build-verified.**
- *Build verified*: a real generated APK from the project is validated. Only after same-phone build can this become green for that project/host.

**CI proof is about metadata tests on GitHub Linux, not actual on-device installation.** The current public toolchain repo has *no Kotlin Android app source*; final integration into the IDE Extensions UI requires editing the separate IDE project. The existing 8-ID manifest stays unchanged for backward compatibility.
