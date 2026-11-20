#!/usr/bin/env python3
"""Read-only CI validator for Python Eye Android/Bionic unified catalog."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / "python-eye-unified-android-arm64.json").read_text(encoding="utf-8"))
assert data["schema_version"] == 1
assert data["platform"] == {"os":"android","abi":"arm64-v8a","libc":"bionic"}
routes = data["routes"]
assets = data["native_archive_candidates"]
assert len(routes) == 53
assert len({r["id"] for r in routes}) == 53
assert {g: sum(r["group"] == g for r in routes) for g in ("core","optional_native","blocked")} == {
    "core":21,"optional_native":19,"blocked":13}
assert len(assets) == 37
assert len({a["id"] for a in assets}) == 37
assert len(data["gradle_versions_catalog_only"]) == 67
assert len(data["sdk_platforms_catalog_only"]) == 14
known = {a["id"] for a in assets}
for asset in assets:
    assert asset["host"] == "android-bionic-aarch64"
    assert re.fullmatch(r"[0-9a-f]{64}", asset["sha256"]), asset["id"]
    assert asset["url"].startswith("https://github.com/"), asset["id"]
    assert asset["bytes"] > 1024 and not asset["installed"]
    assert not asset["device_probe_passed"] and not asset["android_apk_build_verified"]
for route in routes:
    assert route["id"] and route["name"]
    assert set(route["asset_ids"]).issubset(known), route["id"]
    assert not route["device_installed"] and not route["device_probe_passed"]
    assert not route["android_apk_build_verified"]
    if route["group"] == "blocked":
        assert route["installer_kind"] == "blocked-unported"
        assert not route["asset_ids"]
assert not data["missing_blocker"]["native_bionic_verified"]
assert not data["missing_blocker"]["sha256_pinned_binary"]
assert not any(a["family"] == "build-tools" and a["version"] == "36.0.0" for a in assets), "Update blocker before publishing a real 36.0.0"
print("PASS: 53 Android routes, 37 checksum-pinned candidate assets, 67 Gradle versions, 14 SDK platforms; all untested status preserved")
