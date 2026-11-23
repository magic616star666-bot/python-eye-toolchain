#!/usr/bin/env python3
"""Write toolchains/linux-runtime.json and toolchains/linux-ci-results.json from a CI run.

linux-runtime.json pins what the IDE downloads (proot bundle from this repo's
Release, Ubuntu rootfs from its upstream release) and records the CI proof.
linux-ci-results.json records, per package, what really happened when the package
was installed and probed inside the Android-Bionic ARM64 test container.
"""
import argparse
import base64
import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = "magic616star666-bot/python-eye-toolchain"
TAG = "linux-runtime-v1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--run-url", required=True)
    ap.add_argument("--uploaded-digest", default="")
    args = ap.parse_args()
    dist, res = Path(args.dist), Path(args.results)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    bundle = json.loads((dist / "proot-bundle.json").read_text())
    rootfs = json.loads((dist / "rootfs.json").read_text())
    if args.uploaded_digest.lower().startswith("sha256:") and args.uploaded_digest.lower() != f"sha256:{bundle['sha256']}":
        raise SystemExit(f"uploaded asset digest {args.uploaded_digest} != local {bundle['sha256']}")

    boot = (res / "boot.txt").read_text(errors="replace") if (res / "boot.txt").exists() else ""
    pretty = (re.search(r'^PRETTY_NAME="?([^"\n]+)"?', boot, re.M) or [None, rootfs["name"]])[1]
    arch = (re.search(r"^arch=(\S+)", boot, re.M) or [None, "?"])[1]
    bind = (res / "bind-status.txt").read_text().strip() if (res / "bind-status.txt").exists() else "unknown"

    catalog = json.loads((ROOT / "toolchains" / "linux-packages.json").read_text())
    expects = {p["id"]: p["expect"] for p in catalog["packages"]}
    results = {}
    for line in (res / "results.tsv").read_text().splitlines() if (res / "results.tsv").exists() else []:
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        pid, status, secs, b64 = parts
        detail = base64.b64decode(b64).decode("utf-8", "replace")
        # Double-check the shell's ERE verdict with the regex the IDE uses.
        if status == "ok" and not re.search(expects.get(pid, "$^"), detail, re.M):
            status = "probe_failed"
        results[pid] = {"status": status, "seconds": int(secs), "output": detail[-900:]}
    ok = sum(1 for r in results.values() if r["status"] == "ok")

    runtime = {
        "schema_version": 1,
        "catalog_id": "python-eye-linux-runtime",
        "host_abi": "arm64-v8a",
        "updated": now,
        "purpose": "Ubuntu userland for Python Eye IDE via PRoot (no root). The IDE downloads both files, checks SHA-256 and size, unpacks them in app-private storage and boots Ubuntu with PRoot.",
        "proot": {
            "version": bundle["version"],
            "talloc_version": bundle["talloc_version"],
            "provider": REPO,
            "asset_name": bundle["asset_name"],
            "url": f"https://github.com/{REPO}/releases/download/{TAG}/{bundle['asset_name']}",
            "sha256": bundle["sha256"],
            "file_size_bytes": bundle["file_size_bytes"],
            "top_dir": bundle["top_dir"],
            "loaders": bundle["loaders"],
            "sources": bundle["sources"],
        },
        "rootfs": [{
            "id": rootfs["id"],
            "name": rootfs["name"],
            "pretty_name": pretty,
            "provider": rootfs["provider"],
            "release_tag": rootfs["release_tag"],
            "asset_name": rootfs["asset_name"],
            "url": rootfs["url"],
            "sha256": rootfs["sha256"],
            "file_size_bytes": rootfs["file_size_bytes"],
            "format": rootfs["format"],
            "strip_components": rootfs["strip_components"],
            "upstream_digest_checked": rootfs["upstream_digest_checked"],
        }],
        "ci_proof": {
            "run_url": args.run_url,
            "tested_at": now,
            "environment": "GitHub ubuntu-24.04-arm runner + termux/termux-docker:aarch64 (Android Bionic userland, privileged); bundle installed outside the Termux prefix",
            "extracted_by": "IDE RootfsExtractor (LinuxCore.kt) via Harness.kt",
            "boot": "ok" if "pyeye-boot-ok" in boot else "failed",
            "guest_arch": arch,
            "project_bind": bind,
            "packages_ok": ok,
            "packages_total": len(results),
            "not_proven": "A real phone adds SELinux and app-sandbox limits that Docker does not have. The IDE marks a tool Ready only after the same probe passes on the phone.",
        },
    }
    (ROOT / "toolchains" / "linux-runtime.json").write_text(json.dumps(runtime, indent=2) + "\n")
    (ROOT / "toolchains" / "linux-ci-results.json").write_text(json.dumps({
        "schema_version": 1,
        "run_url": args.run_url,
        "tested_at": now,
        "environment": runtime["ci_proof"]["environment"],
        "rootfs": pretty,
        "results": results,
    }, indent=2) + "\n")
    print(f"catalog written: proot {bundle['version']}, {pretty}, {ok}/{len(results)} packages ok")


if __name__ == "__main__":
    main()
