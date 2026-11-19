#!/usr/bin/env python3
"""Verified on-demand desktop JDK and Gradle version manager for Python Eye.

Official Temurin JDK and Gradle release providers, SHA-256 verified before
safe extraction. Each version coexists; no silent system JAVA_HOME changes.
Android Bionic phone installation is intentionally blocked: desktop archives
are NOT Android-compatible native binaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
import zipfile

DEFAULT_LIMIT = 2_000_000_000
MAX_FILES = 30000
ALLOWED_JDK_MAJOR = (8, 11, 17, 21, 25)
API = "https://api.adoptium.net/v3/assets/feature_releases"
GRADLE = "https://services.gradle.org/distributions"


class InstallError(RuntimeError):
    pass


def is_android() -> bool:
    return bool(os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA")
                or sys.platform == "android" or hasattr(sys, "getandroidapilevel"))


def host() -> tuple[str, str]:
    if is_android():
        raise InstallError("Desktop Temurin and Gradle archives cannot be marked Android Bionic ready; use separately verified Android-native tools")
    os_name = {"linux": "linux", "darwin": "mac", "win32": "windows"}.get(sys.platform)
    machine = platform.machine().lower()
    arch = {"x86_64": "x64", "amd64": "x64", "aarch64": "aarch64", "arm64": "aarch64"}.get(machine)
    if not os_name or not arch:
        raise InstallError(f"Unsupported desktop host {sys.platform}/{machine}")
    if os_name == "windows" and arch != "x64":
        raise InstallError("Windows ARM64 JDK archive not verified by this installer")
    if os_name == "linux" and arch == "aarch64":
        # glibc Linux ARM64 JDK isn't Bionic but works on many glibc hosts.
        pass
    return os_name, arch


def https_get(url: str, *, max_size: int = 8_000_000) -> bytes:
    if urlsplit(url).scheme != "https":
        raise InstallError("Only HTTPS metadata sources permitted")
    request = Request(url, headers={"User-Agent": "Python-Eye-Version-Manager/1.0"})
    with urlopen(request, timeout=50) as response:
        if urlsplit(response.geturl()).scheme != "https":
            raise InstallError("Refusing non-HTTPS redirect")
        content = response.read(max_size + 1)
    if len(content) > max_size:
        raise InstallError("Response exceeded size limit")
    return content


def version_id(s: str) -> str:
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", s):
        raise InstallError("Use a released numeric Gradle version, e.g. 8.14.3")
    return s


def jdk_release(major: int) -> dict:
    if major not in ALLOWED_JDK_MAJOR:
        raise InstallError(f"Available vetted JDK release families: {list(ALLOWED_JDK_MAJOR)}")
    os_name, arch = host()
    url = (f"{API}/{major}/ga?architecture={arch}&heap_size=normal&image_type=jdk"
           f"&jvm_impl=hotspot&os={os_name}&page_size=5&project=jdk"
           f"&sort_method=DATE&sort_order=DESC&vendor=eclipse")
    try:
        releases = json.loads(https_get(url))
    except (ValueError, OSError) as exc:
        raise InstallError(f"Temurin release API failed: {exc}") from exc
    for release in releases:
        for binary in release.get("binaries", []):
            if (binary.get("os") == os_name and binary.get("architecture") == arch
                    and binary.get("image_type") == "jdk"):
                package = binary.get("package") or {}
                link = package.get("link", "")
                checksum = package.get("checksum", "").lower()
                if not link.startswith("https://") or not re.fullmatch(r"[0-9a-f]{64}", checksum):
                    continue
                name = package.get("name", "")
                if not re.fullmatch(r"[a-zA-Z0-9+_.-]+\.(?:zip|tar\.gz)", name):
                    continue
                return {"kind": "jdk", "version": str(major),
                        "release_name": release.get("release_name", ""),
                        "archive_name": name, "download_url": link,
                        "sha256": checksum, "source": url, "host": f"{os_name}-{arch}"}
    raise InstallError(f"No official Temurin JDK {major} archive found for {os_name}-{arch}")


def gradle_release(version: str) -> dict:
    version = version_id(version)
    name = f"gradle-{version}-bin.zip"
    checksum = https_get(f"{GRADLE}/{name}.sha256", max_size=512).decode("ascii").strip().split()[0].lower()
    if not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise InstallError("Official Gradle SHA-256 metadata invalid")
    os_name, arch = host()
    return {"kind": "gradle", "version": version,
            "release_name": f"gradle-{version}", "archive_name": name,
            "download_url": f"{GRADLE}/{name}",
            "sha256": checksum, "source": f"{GRADLE}/{name}.sha256",
            "host": f"{os_name}-{arch}"}


def download_verified(metadata: dict, dest: Path, limit: int) -> None:
    source = metadata["download_url"]
    if urlsplit(source).scheme != "https":
        raise InstallError("Download URL must be HTTPS")
    sha = hashlib.sha256()
    total = 0
    request = Request(source, headers={"User-Agent": "Python-Eye-Version-Manager/1.0"})
    try:
        with urlopen(request, timeout=120) as response, dest.open("xb") as file:
            if urlsplit(response.geturl()).scheme != "https":
                raise InstallError("Refusing non-HTTPS download redirect")
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > limit:
                    raise InstallError("Archive exceeds configured byte limit")
                sha.update(block)
                file.write(block)
        if sha.hexdigest() != metadata["sha256"]:
            raise InstallError("SHA-256 mismatch: archive was not installed")
        if not total:
            raise InstallError("Empty archive")
    except Exception:
        dest.unlink(missing_ok=True)
        raise


def path_parts(name: str) -> tuple[str, ...]:
    if (not name or "\\" in name or name.startswith("/") or
            re.match(r"^[A-Za-z]:", name)):
        raise InstallError(f"Unsafe archive filename: {name!r}")
    path = PurePosixPath(name)
    if any(p in ("..", "") for p in path.parts):
        raise InstallError(f"Unsafe archive traversal: {name!r}")
    return path.parts


def safe_unpack(archive: Path, dest: Path, *, limit: int) -> None:
    """Extract verified archives safely, allowing only contained relative tar links."""
    seen: set[str] = set()
    total = 0
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            infos = zf.infolist()
            if len(infos) > MAX_FILES:
                raise InstallError("Too many ZIP entries")
            for item in infos:
                parts = path_parts(item.filename)
                p = "/".join(parts).rstrip("/")
                if p in seen:
                    raise InstallError("Duplicate ZIP path")
                seen.add(p)
                kind = stat.S_IFMT(item.external_attr >> 16)
                if kind not in (0, stat.S_IFDIR, stat.S_IFREG):
                    raise InstallError("ZIP symlinks/special entries are forbidden")
                total += item.file_size
                if total > limit:
                    raise InstallError("ZIP extraction limit exceeded")
            for item in infos:
                target = dest.joinpath(*path_parts(item.filename))
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(item) as src, target.open("xb") as out:
                        remaining = item.file_size
                        while True:
                            data = src.read(min(1024 * 1024, remaining + 1))
                            if not data:
                                break
                            if len(data) > remaining:
                                raise InstallError("ZIP expanded past declared size")
                            out.write(data)
                            remaining -= len(data)
                        if remaining:
                            raise InstallError("Incomplete ZIP member")
                    mode = (item.external_attr >> 16) & 0o777
                    if mode and os.name != "nt":
                        target.chmod(mode & 0o755)
    elif archive.name.endswith((".tar.gz", ".tar.xz")):
        links = []
        with tarfile.open(archive, "r:*") as tf:
            members = tf.getmembers()
            if len(members) > MAX_FILES:
                raise InstallError("Too many TAR entries")
            for item in members:
                parts = path_parts(item.name)
                normalized = "/".join(parts).rstrip("/")
                if normalized in seen:
                    raise InstallError("Duplicate TAR path")
                seen.add(normalized)
                if not (item.isfile() or item.isdir() or item.issym() or item.islnk()):
                    raise InstallError(f"Unsupported TAR member: {item.name}")
                if item.isfile():
                    total += item.size
                    if total > limit:
                        raise InstallError("TAR extraction limit exceeded")
                if item.issym() or item.islnk():
                    links.append(item)
                    # Resolve using posix lexical path to prevent link escaping root
                    import posixpath
                    candidate = (posixpath.join(posixpath.dirname(normalized), item.linkname)
                                 if item.issym() else item.linkname)
                    result = posixpath.normpath(candidate)
                    if (not item.linkname or item.linkname.startswith("/")
                            or result == ".." or result.startswith("../")
                            or "\\" in item.linkname):
                        raise InstallError(f"TAR link escapes extraction root: {item.name}")
            # Prevent a crafted source archive from placing a file under an earlier link.
            link_paths = {x.name.rstrip("/") for x in links}
            for name in seen:
                if any(name.startswith(p + "/") for p in link_paths):
                    raise InstallError("TAR member beneath a link")
            for item in members:
                target = dest.joinpath(*path_parts(item.name))
                if item.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif item.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    member = tf.extractfile(item)
                    if member is None:
                        raise InstallError("Missing TAR member data")
                    with member, target.open("xb") as out:
                        shutil.copyfileobj(member, out, 1024 * 1024)
                    target.chmod(item.mode & 0o755)
            # Only symlinks, not hardlinks, are necessary for Temurin.
            for item in links:
                if item.islnk():
                    raise InstallError("TAR hardlinks not supported")
                target = dest.joinpath(*path_parts(item.name))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(item.linkname)
    else:
        raise InstallError("Unexpected archive format")


def executable_path(folder: Path, meta: dict) -> Path:
    bin_name = ("java.exe" if sys.platform == "win32" else "java") if meta["kind"] == "jdk" else ("gradle.bat" if sys.platform == "win32" else "gradle")
    candidates = list(folder.glob(f"*/bin/{bin_name}"))
    if len(candidates) != 1:
        raise InstallError(f"Expected one extracted {bin_name}, found {len(candidates)}")
    return candidates[0]


def check_executable(path: Path, meta: dict) -> dict:
    cmd = ([str(path), "-version"] if meta["kind"] == "jdk" else [str(path), "--version"])
    try:
        p = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=90, errors="replace")
    except (OSError, subprocess.TimeoutExpired) as e:
        raise InstallError(f"Native host executable check failed: {e}") from e
    if p.returncode:
        raise InstallError(f"{path.name} exited {p.returncode}: {p.stdout[-600:]}")
    if meta["kind"] == "gradle":
        expected = f"Gradle {meta['version']}"
        if expected not in p.stdout:
            raise InstallError(f"Expected {expected} in version output")
    else:
        version_pattern = re.search(r'(?i)(?:openjdk|java) version\s+"?(1\.)?(\d+)', p.stdout)
        if not version_pattern:
            version_pattern = re.search(r"(?i)openjdk\s+(\d+)\.", p.stdout)
            major = int(version_pattern.group(1)) if version_pattern else -1
        else:
            major = int(version_pattern.group(2))
        if major != int(meta["version"]):
            raise InstallError(f"JDK mismatch: expected {meta['version']}, detected {major}")
    return {"ready": True, "verified_executable": str(path), "output": p.stdout.strip()[-750:]}


def install(meta: dict, root: Path, max_bytes: int) -> dict:
    host()  # refuses Android Bionic native-host mismatch
    root = root.expanduser().resolve()
    target = root / meta["kind"] / meta["version"]
    manifest = target / ".python-eye-install.json"
    if manifest.is_file():
        old = json.loads(manifest.read_text("utf-8"))
        if old.get("sha256") == meta["sha256"]:
            binary = executable_path(target, meta)
            return {"state": "already_installed_probe_passed", **check_executable(binary, meta), "destination": str(target)}
        raise InstallError("Existing version differs from official current digest. Do not overwrite automatically; use a new root.")
    if target.exists():
        raise InstallError(f"Refusing to overwrite existing folder: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pyeye-version-", dir=target.parent) as td:
        workspace = Path(td)
        archive = workspace / meta["archive_name"]
        download_verified(meta, archive, max_bytes)
        extracted = workspace / "unpacked"
        extracted.mkdir()
        safe_unpack(archive, extracted, limit=max_bytes * 2)
        binary = executable_path(extracted, meta)
        check_executable(binary, meta)
        # Install only after a complete successful executable check.
        extracted.rename(target)
    checked = check_executable(executable_path(target, meta), meta)
    manifest.write_text(json.dumps({**meta, "locally_verified": True,
                                    "android_bionic_verified": False,
                                    "executable": checked["verified_executable"]}, indent=2) + "\n", "utf-8")
    return {"state": "installed_probe_passed", "destination": str(target), **checked}


def main() -> None:
    parser = argparse.ArgumentParser(description="Download/check official JDK and Gradle versions for supported desktop build hosts")
    parser.add_argument("action", choices=("list", "resolve", "install", "status"))
    parser.add_argument("--kind", choices=("jdk", "gradle"))
    parser.add_argument("--version", help="JDK major (8/11/17/21/25) or exact Gradle release (e.g. 8.14.3)")
    parser.add_argument("--root", type=Path, default=Path.home() / ".python-eye" / "toolchains")
    parser.add_argument("--approve-download", action="store_true", help="Required before network download/install")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_LIMIT)
    args = parser.parse_args()
    try:
        if args.action == "list":
            print(json.dumps({"jdk_major_families": ALLOWED_JDK_MAJOR,
                              "gradle": "Any existing numbered official release with SHA-256 at services.gradle.org",
                              "sdk_platforms_ndk_cmake": "Use toolchains/sdk_installer.py with official sdkmanager",
                              "android_phone_ready": False,
                              "strategy": "Install versions on demand, do not upload every version into GitHub Releases"}, indent=2))
            return
        if not args.kind or not args.version:
            raise InstallError("--kind and --version required")
        if args.kind == "jdk":
            if not args.version.isdecimal():
                raise InstallError("JDK --version must be one major (8/11/17/21/25)")
            major = int(args.version)
            if args.action in ("resolve", "install"):
                meta = jdk_release(major)
        else:
            version = version_id(args.version)
            if args.action in ("resolve", "install"):
                meta = gradle_release(version)
        target = args.root.expanduser().resolve() / args.kind / args.version
        if args.action == "status":
            path = target / ".python-eye-install.json"
            if not path.is_file():
                print(json.dumps({"ready": False, "reason": "version is not installed", "path": str(target)}))
                return
            meta = json.loads(path.read_text("utf-8"))
            if meta.get("kind") != args.kind or meta.get("version") != args.version:
                raise InstallError("Stored installation manifest does not match selected version")
            print(json.dumps({**check_executable(executable_path(target, meta), meta),
                              "android_bionic_verified": False}, indent=2))
            return
        if args.action == "resolve":
            print(json.dumps({**meta, "downloaded": False, "android_bionic_verified": False}, indent=2))
            return
        if args.max_bytes < 100_000 or args.max_bytes > 3_000_000_000:
            raise InstallError("--max-bytes outside allowed range")
        if not args.approve_download:
            raise InstallError("Network download requires explicit --approve-download")
        print(json.dumps({**install(meta, args.root, args.max_bytes),
                          "android_bionic_verified": False}, indent=2))
    except (InstallError, OSError, ValueError, zipfile.BadZipFile, tarfile.TarError) as err:
        print(json.dumps({"ok": False, "error": str(err)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
