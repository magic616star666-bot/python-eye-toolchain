# Python Eye IDE — Android Installer Integration Contract

This is an implementation guide for the **real Python Eye IDE Android app**. The IDE's Kotlin source is not stored in this tool-distribution repository, so this file does **not** mean the app itself is already fixed.

## API: keep existing catalog URL

```
https://raw.githubusercontent.com/magic616star666-bot/python-eye-toolchain/main/tools.json
```

Expect a top-level JSON object with `schema_version: 1`, `tools: [ ... ]` and exactly eight stable `id` values. New metadata fields may be ignored by older parsers, but don't let an unknown field crash catalog import.

## De-duplication

The previous screenshots showed both **built-in** and **remote** entries (old Kotlin 2.3.21 and remote Kotlin 2.1.20, for example). The app must merge by stable `id`, not by display name/version. Importing a remote tool **replaces metadata for that ID**; it must not append another card.

Kotlin design outline (adapt to your actual `Tool` model):

```kotlin
val byId = LinkedHashMap<String, Tool>()
for (item in builtInTools) byId[item.id] = item
for (item in remoteTools) byId[item.id] = item
val visible = byId.values.toList()
```

Never count a remote **published** archive as an **installed** tool. The app's installed state must be determined by the verified contents of its own private tool directory and a command/process probe.

## Five direct release archives

| id | archive | top-level structure / required files |
|---|---|---|
| openjdk-17 | `jdk17-arm64.tar.xz` | `./bin/java`, `./bin/javac`; AArch64 ELF |
| gradle | `gradle-8.14.3-bin.zip` | `gradle-8.14.3/bin/gradle` |
| aapt2-zipalign | `android-sdk-tools-static-aarch64.zip` | `build-tools/aapt2`, `build-tools/zipalign`; AArch64 ELF |
| d8-apksigner | `build-tools-34.0.4-aarch64.tar.xz` | `build-tools/34.0.4/d8`, `lib/d8.jar`, `apksigner`, `lib/apksigner.jar` |
| kotlin-compiler | `kotlin-compiler-2.1.20.zip` | `kotlinc/bin/kotlinc` |

**Installation design:** download the `url` once per unique URL, stream and verify SHA-256 **before extraction**, verify exact `file_size_bytes`, refuse path traversal / symlinks outside installation root, extract under app-private storage, set executable permissions on binaries where appropriate, then probe each installed command. Both `.zip` and `.tar.xz` must be supported. Use a shared cache by asset SHA-256 to avoid duplicate downloads.

Do not automatically share these installed binaries with a different Android application's sandbox. Do not extract into public Downloads or executable-disallowed public storage.

Commands to probe after installation (adapt environment/PATH; exit code and actual output must be checked): `java -version`, `gradle --version`, `aapt2 version`, `zipalign -h`, `d8 --version`, `apksigner version`, `kotlinc -version`.

D8+APKSigner **34.0.4** is only a supplementary, legacy archive. AGP 8.11 requires Android **Build Tools >=35.0.0**. AAPT2 35.0.2 and Zipalign 35.0.2 alone do not provide all required Build Tools classes or file layout. Do not trick AGP by renaming a partial directory to 35.0.0.

## Three managed dependencies (not direct ZIPs)

- `android-sdk-36`: `sdkmanager "platforms;android-36" "build-tools;35.0.0"`, with proper Google license display and user acceptance; ensure `android.jar` exists. Official Linux host binaries may be x86_64 and **will not execute on the Android ARM64 phone without appropriate replacements**.
- `android-gradle-plugin`: pin `com.android.application` version `8.11.0` via `google()` and resolve transitive dependencies in Gradle. Do not pretend a single `.jar` is the plugin.
- `chaquopy-build`: pin `com.chaquo.python` version `17.2.0` via Gradle + Maven Central; requires a compatible Python build toolchain, and for this sample Python 3.10, `minSdk=24`.

The `managed-tools.json` file gives machine-readable resolved profiles. On-device support requires Kotlin installer code and error-handling not present in this repo.

## Probes required before saying APK Builder READY

1. All five archives download, SHA-256 verify and install in app-private storage.
2. ARM64 `java`, `aapt2`, `zipalign` actually execute on the user's Android phone.
3. Official SDK Platform 36 and Android Build Tools 35 needed for AGP are installed and appropriately integrated for ARM64.
4. Gradle resolves AGP 8.11 and Chaquopy 17.2 on the phone, including Python packaging prerequisites.
5. The IDE builds a **new** debug APK on-device, checks APK and signs/installs it.
6. The user launches it and sees Python `3 * 2 + 1 = 7`.

Without all six, the mobile APK builder is **not verified ready** even if GitHub Actions built the example APK on Linux.
