# Python Eye IDE v1.6.4 — SDK36 AIDL error=13 (Permission denied) recovery

## Confirmed failing device step

Android phone log from Extensions:

`Cannot run program "/data/user/0/com.pythoneye.idestudio/files/tools/aapt2-zipalign/aidl": error=13, Permission denied`

This happens BEFORE the genuine Google SDK Build-Tools 36.0.0 package is installed. It is not a missing SDK license error and cannot be fixed by pressing Repair 10 times.

## Root-cause candidates

- Extracted `aidl` is missing execute permission despite `aapt2` being runnable.
- Android SELinux/W^X policy prevents execution from app-writable data. Google documents that apps targeting Android API 29+ cannot exec files in app home; the historical IDE source targets API 28, so this is a **possible**, not proven, cause.
- Wrong native library/runtime for this Android/Bionic binary; binary present is not equal to CLI Ready.

## Changed in BOTH IDE v1.6.4 source variants

- SDK36 installer probes all three native requirements separately: `aapt2`, `aidl`, `zipalign`, rather than trusting an AAPT2-only ready marker.
- Attempts the real execute mode correction via `File.setExecutable` if `canExecute` is false.
- When a provider's AIDL process throws EACCES, the failed command is marked `.sdk36-unusable-aidl` **without deleting or degrading the working AAPT2 test**.
- Tries the next already-loaded, checksum-pinned Android/Bionic native provider; if none works, the Build APK repair wizard offers the next eligible approved source.
- Retains Google-license consent, official Build-Tools 36 archive checksum, staging and rollback. No download or device execution is silently triggered by GitHub Sync.
- Runs device-level executable probes before downloading the ~64 MB Google ZIP.

## Limits

Source Kotlin backend compilation and simulated AIDL error=13 / fallback smoke test passed. **No AIDL execution or SDK36 installation was completed remotely on the user's handset.** If Android app-data execution restrictions are the cause for ALL providers, an APK-bundled native executable in `nativeLibraryDir` may be required; metadata sync or chmod alone cannot bypass OS enforcement. Android policy: https://developer.android.com/about/versions/10/behavior-changes-10#execute-permission

The IDE source ZIP is distributed separately, NOT delivered by this metadata-only GitHub catalog. **Install the updated IDE APK once before retrying Repair.**
