# Python Eye IDE v1.6.0 · Java/Kotlin/Python/HTML real device coverage

This is a consolidated **source-code update**, not proof that every tool or runtime is installed on the phone.

## Complete source integration carried into both Old Python Eye and Code On Go variants

| Domain | Catalog / source integration | What remains a real Android test |
| --- | --- | --- |
| Java | JDK 11/17/21 native candidate catalog, JDK 17 core requirement, Java/Gradle APK builder | Install+execute relevant JDK version(s) and successfully build Java APK |
| Kotlin | Kotlin compiler / KGP official Maven index, AGP/Gradle and D8/R8 | Actual KGP Gradle resolve and Kotlin APK compile/dex |
| Python | Chaquopy 17.2.0 APK selector for 3.10, 3.11, 3.12, 3.13, 3.14, 3.15; Python Run; pip/PyPI; optional GitHub Actions Kivy p4a/Buildozer workflow | One build host/runtime per APK, validate each chosen version, cloud workflow requires credentials and external runner |
| HTML/CSS/JS | Editor, WebView runner, standalone Android APK wrapper, now JS console and main-frame load diagnostics | Render JS/CSS on actual System WebView and build/install HTML APK |

New **Extensions → Check Java / Kotlin / Python / HTML — installed vs missing** button creates a device-local read-only status report and merges existing SDK/AGP/Build-Tools 36 compatibility blockers. Each status distinguishes *listed*, *installed*, *CLI test passed*, and *APK built*. The code never turns an untested entry Ready.

## Remaining limitations

- Genuine Google SDK Build-Tools 36.0.0 + correctly functioning Android/Bionic ARM64 native AAPT2/AIDL/zipalign have not been fully verified in the user's IDE sandbox.
- Python-for-Android standalone **local Android/Bionic port** is unported, although a Linux GitHub Actions Kivy cloud workflow is available.
- 13 historically blocked routes do not automatically become functional from adding a menu entry or version list.
- D8 dex merging may still exhaust memory on a phone with ~1.6 GiB RAM free.
- Kotlin/JVM tests passed in the source environment but **no APK or device-level run** is claimed by this document.

Previous manifests remain authoritative for catalog candidates and version lists:
- [Unified ARM64 toolchain](python-eye-unified-android-arm64.json)
- [Python 3.10–3.15 build profiles](python-eye-python-310-to-315.json)
- [Native toolchain source audit](PYTHON_EYE_V151_NATIVE_TOOLCHAIN_RELEASE.md)

The IDE project source is delivered separately as ZIPs; this repository stores toolchain distribution metadata and build guidance.
