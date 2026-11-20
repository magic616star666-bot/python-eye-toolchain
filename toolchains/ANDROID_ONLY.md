# Python Eye IDE — ANDROID ARM64 ONLY 🚀

**Target:** Real Android device / arm64-v8a / Bionic libc. No Windows/macOS/Linux x86_64 installers in the Python Eye Android Auto Setup.

### Official Android selection

[android-only-profile.json](android-only-profile.json) is the **only** default IDE selection source. It classifies the existing 53 legacy/extended/addon entries without deleting their source catalogs:

- **21 Android core/JVM-managed workflows:** Bionic JDK 17, JVM Gradle, Android SDK platform data, Bionic AAPT2/zipalign, Kotlin and project Gradle plugins, signing, Java bytecode tooling. These are *routes*—all require appropriate device and project checks.
- **19 optional Android-native-dependent routes:** Android/Bionic JDK 11/21, NDK, CMake, ADB, AIDL, Ninja, Clang, Rust/Cargo, Node/npm, Git, etc. Some have native upstream assets; others are hidden from installation until a functioning Bionic executable is independently proven.
- **13 desktop-only or unported routes excluded from the mobile Auto Setup:** desktop sdkmanager, desktop Buildozer/p4a, Flutter/Flet/BeeWare and React Native/Expo/Capacitor/Cordova CLI tool installers that are not validated **inside the IDE app sandbox**, and cloud build.

**37 actual upstream Android/Bionic archives** are in [mobile-artifacts.json](mobile-artifacts.json), each with a real SHA-256, source link and recorded size. Release assets are hosted by the original upstream projects; not all are mirrored or executable-tested on the user's handset. A downloaded archive is NOT a working tool. A device CLI probe is NOT a successful APK build.

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


## Real Android-native version coverage and device APK check

**Native download catalog now contains 37 distinct source archives/binaries** with SHA-256 and exact size.
Build Tools and ADB ports cover 33.0.1, 33.0.3, 34.0.0, 34.0.1, 34.0.3 and (previously) 34.0.4.
NDK Android/Bionic community ports cover r26/r26b/r26c/r26d, r27/r27b/r27c/r27d, r28/r28b/r28c, r29 and r30.
JDK ports cover major 11, 17 and 21. Optional Ninja, Clang, LLD, clangd, clang-tidy, LLVM and CMake versions are also indexed.

**[Live 37-source SHA-256 verifier](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44678173834) passed.** GitHub verifies original upstream asset links, size and hashes; it does not execute Android/Bionic binaries on a phone.

### Gradle versions are Java, not PC/Linux native binaries

Official, version-selectable Gradle releases can now be installed *from Android itself* using [android_gradle_versions.py](android_gradle_versions.py) through the Android-only setup CLI. They use a working Bionic JDK and the Java Gradle launcher directly, not the Linux Gradle executable.

```bash
python3 toolchains/android_setup.py gradle-list
python3 toolchains/android_setup.py gradle-resolve --version 8.14.3
python3 toolchains/android_setup.py gradle-install --version 8.14.3 --approve-download --execute-probe --java "$JAVA_HOME/bin/java"
python3 toolchains/android_setup.py gradle-status --version 8.14.3
python3 toolchains/android_setup.py gradle-probe --version 8.14.3 --java "$JAVA_HOME/bin/java"
```

SHA-256 is fetched from official Gradle distributions for the exact version requested; no fixed list can promise every past/future Gradle version. [Real Java launcher CLI checks passed for Gradle 8.13 and 8.14.3 on Linux](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44677658233), but the Bionic Java invocation requires an on-device test.

### Real same-phone Kotlin/Java Android APK smoke (only with your explicit approval)

[android_apk_smoke.py](android_apk_smoke.py) uses the installed Bionic JDK + selected Gradle Java launcher + installed Android SDK `android.jar` + native AAPT2. It builds only a recognized Android Gradle project and confirms a **new nonempty APK ZIP containing `AndroidManifest.xml` and `classes.dex`**. No fake output, no desktop fallback, no automatic project wrapper.

```bash
python3 toolchains/android_apk_smoke.py \
  --project kotlin-smoke-test \
  --gradle-version 8.14.3 \
  --sdk-root "$ANDROID_HOME" \
  --java "$JAVA_HOME/bin/java" \
  --aapt2 "$ANDROID_HOME/build-tools/35.0.0/aapt2" \
  --output ./phone-apk-results \
  --approve-build
```

Set the real device paths from your IDE; the example AAPT2 path must **actually exist and execute on Android/Bionic**. If compilation, AAPT2 execution, APK output or checksum checks fail, the script outputs a real error instead of announcing success. It does not automatically install or launch APKs.

**Still required to finish the Android app itself:** actual Python Eye IDE Kotlin source integration, Android private-executable storage compatibility, installed SDK platform versions, and genuine APK build+install+launch smoke on the user's phone. There is no direct connection to the user's device in this chat, so these device claims remain unverified.
