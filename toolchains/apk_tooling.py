#!/usr/bin/env python3
"""Read-only APK audit, optional AAB validation and explicit release signing.

Never embeds an upload keystore or password in a repository or argument list.
Release signing requires --execute, a user-owned keystore and the user's own
PYTHON_EYE_KS_PASS environment variable. Output is verified with apksigner.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


def apk_details(apk: Path) -> dict:
    if not apk.is_file() or not zipfile.is_zipfile(apk):
        raise ValueError("Input must be a real APK ZIP")
    with zipfile.ZipFile(apk) as zf:
        names = zf.namelist()
        if "AndroidManifest.xml" not in names:
            raise ValueError("AndroidManifest.xml missing from APK")
        if zf.testzip() is not None:
            raise ValueError("APK ZIP has corrupt members")
        native = sorted({name.split("/")[1] for name in names
                         if name.startswith("lib/") and len(name.split("/")) >= 3})
        return {
            "apk": str(apk), "size_bytes": apk.stat().st_size,
            "manifest_present": True,
            "dex_count": sum(name.endswith(".dex") and name.startswith("classes") for name in names),
            "native_abis": native,
            "v1_signature_files": any(name.startswith("META-INF/") and name.endswith(".RSA") for name in names),
            "v2_v3_signature_checked": False,
            "apk_is_installable": "not_proven_until_sign_and_install_probe",
        }


def executable(name: str, env_name: str = "") -> str:
    result = os.environ.get(env_name) if env_name else None
    result = result or shutil.which(name)
    if not result or not Path(result).is_file():
        raise RuntimeError(f"{name} missing on this build host")
    return result


def run(argv: list[str], env: dict | None = None) -> str:
    result = subprocess.run(argv, capture_output=True, text=True, check=False,
                            timeout=120, env=env, errors="replace")
    if result.returncode:
        # Avoid printing any sensitive keystore credentials (passed via env, not argv)
        raise RuntimeError(f"{Path(argv[0]).name} failed with exit {result.returncode}: {(result.stdout + result.stderr)[-600:]}")
    return (result.stdout + result.stderr)[-1000:].strip()


def sign(apk: Path, output: Path, ks: Path, alias: str, execute: bool) -> dict:
    if not execute:
        raise RuntimeError("Signing requires explicit --execute and keystore ownership")
    if not ks.is_file():
        raise RuntimeError("Keystore not found")
    if not os.environ.get("PYTHON_EYE_KS_PASS"):
        raise RuntimeError("Set PYTHON_EYE_KS_PASS privately; password is NEVER a command-line argument")
    if not alias or len(alias) > 100:
        raise RuntimeError("Provide a valid keystore alias")
    source = apk.resolve()
    target = output.resolve()
    if source == target or target.exists():
        raise RuntimeError("Refusing to overwrite source or existing output APK")
    apk_details(source)
    zipalign = executable("zipalign", "ZIPALIGN_BIN")
    signer = executable("apksigner", "APKSIGNER_BIN")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pyeye-sign-", dir=target.parent) as td:
        aligned = Path(td) / "aligned.apk"
        run([zipalign, "-f", "-p", "4", str(source), str(aligned)])
        args = [signer, "sign", "--ks", str(ks.resolve()),
                "--ks-key-alias", alias, "--ks-pass", "env:PYTHON_EYE_KS_PASS"]
        if os.environ.get("PYTHON_EYE_KEY_PASS"):
            args.extend(["--key-pass", "env:PYTHON_EYE_KEY_PASS"])
        args.extend(["--out", str(target), str(aligned)])
        try:
            run(args, env=dict(os.environ))
            verified = run([signer, "verify", "--verbose", str(target)])
            info = apk_details(target)
            info.update({"verified_signer": True, "signer_output": verified[-400:],
                         "signed_with_user_owned_keystore": True})
            return info
        except Exception:
            target.unlink(missing_ok=True)
            raise


def bundle_validate(bundle: Path, tool: Path, execute: bool) -> dict:
    if not execute:
        raise RuntimeError("Bundletool invocation requires --execute")
    if not bundle.is_file() or not zipfile.is_zipfile(bundle):
        raise RuntimeError("AAB file missing or corrupt")
    with zipfile.ZipFile(bundle) as zf:
        if not any(name.endswith("/manifest/AndroidManifest.xml") for name in zf.namelist()):
            raise RuntimeError("Android App Bundle manifest not found")
    if not tool.is_file():
        raise RuntimeError("Provide trusted official bundletool JAR path")
    java = executable("java", "JAVA_BIN")
    output = run([java, "-jar", str(tool), "validate", "--bundle=" + str(bundle)])
    return {"bundle": str(bundle), "validated_by_real_bundletool": True, "output": output}


def logcat(lines: int, execute: bool) -> dict:
    if not execute:
        raise RuntimeError("Device log reading requires explicit --execute")
    if not 1 <= lines <= 500:
        raise ValueError("Only 1..500 device log lines allowed")
    adb = executable("adb", "ADB_BIN")
    # Output may include personal app logs. It is not uploaded anywhere.
    content = run([adb, "logcat", "-d", "-t", str(lines)])
    return {"read_only": True, "lines_requested": lines, "log_output": content}


def main() -> None:
    p = argparse.ArgumentParser(description="APK auditor / opt-in release signer / bundletool validator")
    sub = p.add_subparsers(dest="action", required=True)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("apk", type=Path)
    signed = sub.add_parser("sign")
    signed.add_argument("apk", type=Path)
    signed.add_argument("--output", type=Path, required=True)
    signed.add_argument("--keystore", type=Path, required=True)
    signed.add_argument("--alias", required=True)
    signed.add_argument("--execute", action="store_true")
    bundle = sub.add_parser("validate-aab")
    bundle.add_argument("bundle", type=Path)
    bundle.add_argument("--bundletool-jar", type=Path, required=True)
    bundle.add_argument("--execute", action="store_true")
    logs = sub.add_parser("logcat")
    logs.add_argument("--lines", type=int, default=100)
    logs.add_argument("--execute", action="store_true")
    args = p.parse_args()
    try:
        if args.action == "inspect":
            result = apk_details(args.apk)
        elif args.action == "sign":
            result = sign(args.apk, args.output, args.keystore, args.alias, args.execute)
        elif args.action == "validate-aab":
            result = bundle_validate(args.bundle, args.bundletool_jar, args.execute)
        else:
            result = logcat(args.lines, args.execute)
        print(json.dumps(result, indent=2))
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
