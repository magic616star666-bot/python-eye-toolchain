# Python Eye — all official SDK and Gradle versions on demand

Sources: [Gradle releases JSON](https://services.gradle.org/versions/all), [Google SDK repository XML](https://dl.google.com/android/repository/repository2-1.xml).

The [generated version list](official-on-demand.json) is refreshed by `scripts/generate_official_version_index.py` on a weekly schedule and when invoked manually. It is **metadata only**. No binaries are pushed to GitHub, and versions not verified on an Android phone are not labeled Ready.

The Android IDE reads these same official sources when you tap **Update all available SDK / Gradle / Android versions**. Installed versions are private per-tool, with separately selectable **Load / Unload / Test**; older default Python → APK Gradle/SDK versions remain pinned. Google's SDK license must be accepted explicitly. No official desktop/x86 Android Build Tools binaries should be represented as compatible Android/Bionic native binaries.

Google's Android SDK repository may publish SHA-1 only; Gradle's stable releases provide SHA-256. SHA-1 is weaker than SHA-256, so this is shown distinctly and accepted only for HTTPS Google SDK platform packages. The bundled pinned SDK 33–35 packages retain their independent SHA-256.

Native NDK ports remain under [mobile-artifacts.json](mobile-artifacts.json), with real device testing required.
