# Python Eye IDE 1.4.9.23 — remaining phone tool fixes

## Problems reproduced from screenshots (20 Nov 2026)

| Version | Original observed error | Change |
|---|---|---|
| JDK 21.0.4 | `Download failed (HTTP 404)` | Replaced catalog URL with publisher's real `jdk21-android-21.0.14` release, SHA-256 `b6575760724183350c98206082da7829808b62b766e2d30fc253101b1e8cda0e` and 201284627 bytes. |
| Android CMake 3.22.1 | `libc++_shared.so not found` | Android IDE project now bundles ARM64 `libc++_shared.so` through Maven dependency `dev.atsushieno:libcxx-provider:29.0.14206865`, explicitly extracts JNI libs, and forwards its native-library directory to child processes. |
| Android Ninja_arm64 | `libc++_shared.so not found` | Uses the same verified ELF64 ARM64 JNI runtime; no separate NDK installation needed if the library is correctly packaged in the APK. |

The source fix is in Python Eye IDE `AndroidNativeTools.kt`, `IdeState.kt`, and `app/build.gradle.kts` of the **1.4.9.23** ZIP (old IDE and Code On the Go variants). The toolchain GitHub repo is the distribution **catalog**, not a substitute for the application's source ZIP.

## Verification

- JDK21 upstream source pin verified against the actual GitHub Release assets metadata; downloading and executing the 201MB archive on the target phone remains necessary.
- GitHub CI [**Verify Android ARM64 libc++ Maven provider**](https://github.com/magic616star666-bot/python-eye-toolchain/actions/runs/44752174113) **PASS**: Maven AAR is 1833646 bytes, `jni/arm64-v8a/libc++_shared.so` exists (1374336 bytes), verified ELF64 little-endian EM_AARCH64 183, SHA-256 `c4c2fe5cbcb1fba0003a31fc7ab29a9bb12df6cc187ec45a806462540e83d93b`.
- Local Kotlin/JVM tests **PASS** for cached JDK21 old URL migration, ARM64 ELF verification, injecting JNI runtime paths for real Ninja and CMake mock executables, rejecting wrong-ABI libraries and clearing runtime context after a probe. **These are host tests, not Android device execution.**
- The native runner skips C++ injection for java/javac and does not claim an APK build merely because a CLI returned success.

## Next phone tests

Install the new v1.4.9.23 APK. In Extensions tap **Update all available versions** to refresh the GitHub catalog, then:
1. **JDK 21.0.14** → Load → Test. It must not attempt the old 21.0.4 URL.
2. Already-installed **CMake 3.22.1** → Test again (no need to re-download if files exist).
3. Already-installed **Ninja ARM64** → Test again.
4. If CMake/Ninja still fail, use **Copy complete crash report** and verify the APK actually shipped `lib/arm64-v8a/libc++_shared.so`. A successful Maven AAR download is not proof that AGP packed it into the installed APK.

Third-party Maven provider's license is Apache-2.0; the repo does not republish its binary. Keep other Java/Gradle/SDK tools installed unless they fail their own tests. Device runtime behavior remains unverified.
