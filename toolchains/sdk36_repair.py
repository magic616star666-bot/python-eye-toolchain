#!/usr/bin/env python3
"""Python Eye IDE: explicit, rollback-safe Build-Tools 36.0.0 Android/Bionic repair.

This is an optional *manual recovery tool*, not code executed by GitHub catalog
Sync. The normal app UI has Extensions > Prepare Android-native tools for SDK 36
and Install genuine SDK Build-Tools 36.0.0. No license is accepted automatically.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
from urllib.request import urlopen
import zipfile

VERSION = "36.0.0"
GOOGLE_URL = "https://dl.google.com/android/repository/build-tools_r36_linux.zip"
GOOGLE_SHA1 = "b0b6376977657e8ad9b969bacf4093601da2c6fb"
GOOGLE_BYTES = 63737259
NATIVE_TOOLS = ("aapt2", "aidl", "zipalign")
OPTIONAL_TOOLS = ("aapt", "dexdump", "split-select")
PROVIDERS = (
    "mobile-android-build-tools-34-0-3-bionic",
    "mobile-android-build-tools-34-0-1-bionic",
    "mobile-android-build-tools-34-0-0-bionic",
    "mobile-android-build-tools-33-0-3-bionic",
    "mobile-android-build-tools-33-0-1-bionic",
    "mobile-android-aapt2-zipalign-35",
)
LICENSE_HASHES = {"8933bad161af4178b1185d1a37fbf41ea5269c55",
                  "d56f5187479451eabf01fb78af6dfcb131a6481e"}
REQUIRED_DATA = ("lib/d8.jar", "lib/apksigner.jar", "core-lambda-stubs.jar")


def is_bionic_arm64(file: Path) -> bool:
    """Android ARM64 ELF with Android linker, or static ELF; not glibc."""
    try:
        with file.open("rb") as stream:
            head = stream.read(64)
            if len(head) != 64 or head[:4] != b"\x7fELF" or head[4:6] != b"\x02\x01":
                return False
            if struct.unpack_from("<H", head, 18)[0] != 183:
                return False
            phoff = struct.unpack_from("<Q", head, 32)[0]
            phsize = struct.unpack_from("<H", head, 54)[0]
            count = struct.unpack_from("<H", head, 56)[0]
            if phsize < 56 or count > 128 or phoff + phsize * count > file.stat().st_size:
                return False
            for i in range(count):
                stream.seek(phoff + i * phsize)
                hdr = stream.read(56)
                if len(hdr) < 56:
                    return False
                if struct.unpack_from("<I", hdr)[0] != 3:
                    continue
                offset = struct.unpack_from("<Q", hdr, 8)[0]
                size = struct.unpack_from("<Q", hdr, 32)[0]
                if not 1 <= size <= 512 or offset + size > file.stat().st_size:
                    return False
                stream.seek(offset)
                linker = stream.read(size).rstrip(b"\x00")
                return linker in (b"/system/bin/linker64",
                                  b"/apex/com.android.runtime/bin/linker64")
            return True
    except (OSError, ValueError, struct.error):
        return False


def license_accepted(sdk: Path) -> bool:
    try:
        return bool(LICENSE_HASHES.intersection(
            set((sdk / "licenses" / "android-sdk-license").read_text().split())))
    except OSError:
        return False


def package_identity(path: Path) -> bool:
    try:
        return any(line.strip() == "Pkg.Revision=36.0.0"
                   for line in (path / "source.properties").read_text().splitlines())
    except OSError:
        return False


def sdk_status(sdk: Path) -> list[str]:
    directory = sdk / "build-tools" / VERSION
    issues = []
    if not directory.is_dir():
        return ["Missing build-tools/36.0.0 directory"]
    if not package_identity(directory):
        issues.append("Genuine Google 36.0.0 source.properties absent or mismatched")
    for rel in REQUIRED_DATA:
        f = directory / rel
        if not f.is_file() or not f.stat().st_size:
            issues.append("Missing Google package data: " + rel)
    for name in NATIVE_TOOLS:
        f = directory / name
        if not is_bionic_arm64(f):
            issues.append("Missing Android/Bionic ARM64 executable: " + name)
    return issues


def native_library_dirs(provider: Path, extra: str | None = None) -> list[str]:
    dirs = [provider / "lib", provider / "lib64",
            provider / "lib" / "native", provider / "lib" / "aarch64"]
    if extra:
        dirs.insert(0, Path(extra))
    return [str(x) for x in dirs if x.is_dir()]


def probe(exe: Path, name: str, roots: list[str]) -> bool:
    commands = {
        "aapt2": (("version",), ()),
        "aidl": (("--version",), ("--help",)),
        "zipalign": (("-h",), ()),
    }
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = ":".join(roots + ([env["LD_LIBRARY_PATH"]]
                                                if env.get("LD_LIBRARY_PATH") else []))
    for arguments in commands[name]:
        try:
            p = subprocess.run([str(exe), *arguments], capture_output=True, text=True,
                               timeout=15, env=env, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        txt = (p.stdout + p.stderr).lower()
        if any(bad in txt for bad in ("cannot link executable", "exec format error",
                                      "permission denied", "not found: library")):
            continue
        if name == "aapt2" and (("aapt2" in txt or
                                ("compile" in txt and "link" in txt))):
            return True
        if name == "aidl" and ("aidl" in txt or "interface definition" in txt):
            return True
        if name == "zipalign" and ("zipalign" in txt or "alignment" in txt):
            return True
    return False


def find_native_sources(tools: Path, sdk: Path, extra_lib: str | None) -> tuple[dict, list[str]]:
    found: dict[str, tuple[Path, str, Path]] = {}
    logs = []
    candidates = [tools / id for id in PROVIDERS]
    sdk35 = sdk / "build-tools" / "35.0.0"
    if (sdk35 / "source.properties").is_file() and (
        "Pkg.Revision=35.0.0" in (sdk35 / "source.properties").read_text()):
        candidates.append(sdk35)
    for root in candidates:
        if root != sdk35 and not ((root / ".test-ok").is_file() and
                                  (root / "tool.properties").exists() or
                                  (root / ".tool-installed").exists() and
                                  (root / ".test-ok").exists()):
            # Different IDE versions have different metadata names, but
            # a previous .test-ok is always mandatory.
            if not (root / ".test-ok").is_file():
                continue
        if not root.is_dir():
            continue
        for name in NATIVE_TOOLS:
            if name in found:
                continue
            candidates_for_name = (x for x in root.rglob(name)
                                   if x.is_file() and len(x.relative_to(root).parts) <= 8)
            for binary in candidates_for_name:
                if not is_bionic_arm64(binary):
                    continue
                if not os.access(binary, os.X_OK):
                    continue
                paths = native_library_dirs(binary.parent.parent, extra_lib)
                paths += native_library_dirs(root, extra_lib)
                if probe(binary, name, paths):
                    found[name] = (binary, root.name, root)
                    logs.append(f"PASS {name} from {root.name}")
                    break
    return found, logs


def secure_unzip(archive: Path, output: Path):
    with zipfile.ZipFile(archive) as zipf:
        members = zipf.infolist()
        if len(members) > 10000:
            raise RuntimeError("Unexpected Google archive member count")
        size = 0
        for item in members:
            rel = Path(item.filename)
            if rel.is_absolute() or ".." in rel.parts or "\x00" in item.filename:
                raise RuntimeError("Unsafe archive path")
            if (item.external_attr >> 16) & 0o170000 == stat.S_IFLNK:
                raise RuntimeError("Archive symlinks unsupported")
            size += item.file_size
            if size > 700 * 1024 * 1024:
                raise RuntimeError("Google SDK archive expanded size limit exceeded")
        zipf.extractall(output)


def official_download(destination: Path):
    digest = hashlib.sha1()
    count = 0
    with urlopen(GOOGLE_URL, timeout=60) as src, destination.open("wb") as dst:
        while True:
            chunk = src.read(128 * 1024)
            if not chunk:
                break
            count += len(chunk)
            if count > GOOGLE_BYTES:
                raise RuntimeError("Google SDK archive is larger than expected")
            digest.update(chunk)
            dst.write(chunk)
    if count != GOOGLE_BYTES or digest.hexdigest() != GOOGLE_SHA1:
        raise RuntimeError("Google SDK archive size/SHA-1 mismatch")


def repair(sdk: Path, tools: Path, approved: bool, download: bool,
           native_lib: str | None):
    if not approved or not download:
        raise RuntimeError("Use --accept-google-license AND --approve-download after reviewing terms")
    if not license_accepted(sdk):
        raise RuntimeError("SDK license record missing: approve via Python Eye Extensions first")
    found, logs = find_native_sources(tools, sdk, native_lib)
    for line in logs:
        print(line)
    missing = [x for x in NATIVE_TOOLS if x not in found]
    if missing:
        raise RuntimeError("Load + Test an Android/Bionic Build-Tools provider in Extensions "
                           "before repairing SDK36. Missing: " + ", ".join(missing))
    base = sdk / "build-tools"
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".sdk36-work-", dir=base) as work:
        temp = Path(work)
        archive = temp / "official.zip"
        print("Downloading and verifying official Google Build-Tools 36.0.0…")
        official_download(archive)
        unpacked = temp / "unpacked"
        secure_unzip(archive, unpacked)
        roots = [x for x in unpacked.rglob("source.properties")
                 if package_identity(x.parent) and
                 all((x.parent / r).is_file() for r in REQUIRED_DATA)]
        if len(roots) != 1:
            raise RuntimeError("Official Build-Tools 36 identity or archive layout not recognized")
        staged = temp / "36.0.0"
        shutil.copytree(roots[0].parent, staged)
        for name, (src, provider, root) in found.items():
            dest = staged / name
            if dest.is_file():
                backups = staged / ".google-linux-originals"
                backups.mkdir(exist_ok=True)
                dest.replace(backups / name)
            shutil.copy2(src, dest)
            dest.chmod(dest.stat().st_mode | stat.S_IXUSR)
        libs = staged / "lib" / "native"
        for _name, (_exe, _provider, root) in found.items():
            for dll in root.rglob("*.so"):
                if not dll.is_file() or dll.stat().st_size > 40_000_000:
                    continue
                if len(dll.relative_to(root).parts) > 8 or not is_bionic_arm64(dll):
                    continue
                libs.mkdir(parents=True, exist_ok=True)
                dst = libs / dll.name
                if not dst.exists():
                    shutil.copy2(dll, dst)
        envlibs = native_library_dirs(staged, native_lib) + ([str(libs)] if libs.is_dir() else [])
        if not all(probe(staged / name, name, envlibs) for name in NATIVE_TOOLS):
            raise RuntimeError("Android/Bionic executable CLI probe failed after SDK 36 staging")
        if sdk_status_at_stage(staged):
            raise RuntimeError("SDK 36 staged package did not pass identity/data audit")
        dest = base / VERSION
        backup = base / ".sdk36-python-eye-backup"
        if backup.exists():
            raise RuntimeError("Existing SDK36 backup found: investigate before repair")
        had_old = dest.exists()
        if had_old:
            dest.rename(backup)
        try:
            staged.rename(dest)
        except Exception:
            if had_old:
                backup.rename(dest)
            raise
        if sdk_status(sdk):
            if dest.exists():
                shutil.rmtree(dest)
            if had_old:
                backup.rename(dest)
            raise RuntimeError("Post-install SDK36 validation failed; previous SDK restored")
        if backup.exists():
            shutil.rmtree(backup)
    print("SDK 36 PACKAGE + ARM64 CLI CHECK PASS. Android APK build is still UNVERIFIED.")


def sdk_status_at_stage(stage: Path) -> list[str]:
    errors = [] if package_identity(stage) else ["Pkg.Revision mismatch"]
    errors += [f"Missing {part}" for part in REQUIRED_DATA if not (stage / part).is_file()]
    errors += [f"Bad Bionic {name}" for name in NATIVE_TOOLS
               if not is_bionic_arm64(stage / name)]
    return errors


def main(argv=None):
    p = argparse.ArgumentParser(description="Python Eye SDK36 read-only check or consented repair")
    p.add_argument("action", choices=("status", "repair"))
    p.add_argument("--tools-root", default="/data/user/0/com.pythoneye.idestudio/files/tools")
    p.add_argument("--accept-google-license", action="store_true")
    p.add_argument("--approve-download", action="store_true")
    p.add_argument("--native-lib-dir", default=None)
    a = p.parse_args(argv)
    tools = Path(a.tools_root).expanduser().resolve()
    sdk = tools / "android-sdk-36"
    issues = sdk_status(sdk)
    print("Active SDK:", sdk)
    print("SDK Build-Tools 36:", "PACKAGE FILES OK; native CLI needs testing" if not issues
          else "; ".join(issues))
    if a.action == "status":
        found, logs = find_native_sources(tools, sdk, a.native_lib_dir)
        for line in logs:
            print(line)
        print("Native prerequisites:", ", ".join(x for x in NATIVE_TOOLS if x not in found) or "present")
        return 0 if not issues else 2
    repair(sdk, tools, a.accept_google_license, a.approve_download, a.native_lib_dir)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError, zipfile.BadZipFile) as exc:
        print("SDK36 REPAIR NOT COMPLETED:", exc, file=sys.stderr)
        sys.exit(1)
