# Naya tool kaise jodein — bina naya APK banaye

Python Eye IDE (v1.6.3+) mein **Maven JAR tools** ab poori tarah catalog se chalte hain. Naya tool = `tools.json` mein ek entry + push. Phone par: Extensions → **Sync** → **Load** → **Test**.

## Entry ka namuna
```json
{
  "id": "mera-tool",
  "name": "Mera Tool",
  "version": "1.2.3",
  "requires": ["openjdk-17", "gradle"],
  "description": "Kya karta hai",
  "published": false, "url": "", "sha256": "",
  "archive_format": "jar",
  "required_probes": ["com.example.tool.Main --version"],
  "expect": "1.2.3",
  "install": {
    "method": "maven_artifact_resolution",
    "plugin_id": "com.example:tool",
    "required_paths": [],
    "device_verified": false
  },
  "catalog_state": "maven_resolution_not_device_verified",
  "device_build_verified": false
}
```

## Niyam (IDE aur CI dono yahi check karte hain)
- `plugin_id` = `group:artifact` (google() ya mavenCentral() par hona chahiye).
- `required_probes` = 1–6 Java commands: `java.main.Class [args]`. Shell command allowed nahi.
- `expect` = Test output mein yeh text aana chahiye (khali ho to `version`).
- `required_paths` (optional) = `lib/<naam>.jar` — ek ho to main JAR is naam se bhi save hota hai (R8: `lib/r8.jar`).

## Push karte hi CI
`Validate Tool Catalog` workflow:
1. Niyam check (`scripts/validate_catalog.py`).
2. Asli Load + Test (`scripts/verify_maven_tools.py`): wahi `build.gradle` jo phone banata hai, wahi probes.

CI laal = phone tak galat entry mat bhejo; log mein exact wajah hai.

## Kya abhi bhi APK update maangta hai
- Gradle **plugins** (AGP, Chaquopy, Kotlin plugin) — inke liye plugin-specific probe project chahiye.
- Native archives (`archive` method) pehle se catalog-driven hain: URL + SHA-256 + `test` command.
