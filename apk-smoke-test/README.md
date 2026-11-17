# Python Eye IDE: real Python-to-APK smoke test

This is a real minimal **Android + Chaquopy** project, not a webview-only sample. It uses the following pinned versions:

- JDK 17
- Gradle 8.14.3
- Android Gradle Plugin 8.11.0
- Android SDK Platform 36 / Build Tools 35.0.0
- Chaquopy 17.2.0
- Embedded Python 3.10, ARM64 ABI only

Source code in `app/src/main/python/hello.py` executes in the APK. The app's Java Activity calls it and prints the result.

## CI build

See GitHub Actions → **Build Real Python APK**. The action downloads SDK Platform 36 using Google's SDK Manager after accepting CI licenses, resolves AGP/Chaquopy from Maven/Google via Gradle, and builds a debug APK.

Success in GitHub Actions proves **Linux x86-64 CI** compilation, not the on-phone ARM64 build toolchain. Reproduce the build on Python Eye IDE separately.

The test does not include an ONNX model.
