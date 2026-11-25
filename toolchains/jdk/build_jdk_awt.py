#!/usr/bin/env python3
"""Build a relocatable Android ARM64 (Bionic) JDK 17 WITH headless AWT for Python Eye IDE.

Why: the old JDK asset has no libawt*.so, so Android Lint (lintVitalAnalyzeRelease) dies with
"no awt in system library path" (IntelliJ core calls SwingUtilities -> java.awt.Toolkit).

Source: the official Termux aarch64 `openjdk-17` package + every package it depends on.
Each .deb is checked against the SHA-256 in the Termux index. The JDK tree is copied to
jdk/ (same layout as the current asset: jdk/bin/java, jdk/lib/server/libjvm.so, ...).
Every shared library any JDK ELF needs - transitively - is copied into jdk/lib, and the
build FAILS if one is neither inside the bundle nor an Android system library.
The archive is reproducible and content-addressed (sha256 prefix in the asset name).
"""
import argparse
import gzip
import hashlib
import json
import lzma
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

MIRRORS = [
    "https://packages-cf.termux.dev/apt/termux-main",
    "https://packages.termux.dev/apt/termux-main",
    "https://grimler.se/termux/termux-main",
]
INDEXES = ["dists/stable/main/binary-aarch64/Packages.xz", "dists/stable/main/binary-aarch64/Packages.gz"]
PREFIX = Path("data/data/com.termux/files/usr")
EPOCH = 1704067200
# Libraries every Android (API 26+) device provides in /system/lib64 (NDK stable APIs).
SYSTEM_LIBS = {"libc.so", "libdl.so", "libm.so", "liblog.so", "libz.so", "libandroid.so",
               "libjnigraphics.so", "libEGL.so", "libGLESv2.so", "libGLESv3.so", "libOpenSLES.so",
               "libvulkan.so", "libnativewindow.so", "libsync.so", "libmediandk.so", "libcamera2ndk.so"}
JDK_PACKAGE = "openjdk-17"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "python-eye-toolchain-ci"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def load_index():
    errors = []
    for mirror in MIRRORS:
        for index in INDEXES:
            try:
                data = fetch(f"{mirror}/{index}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{mirror}/{index}: {exc}")
                continue
            data = lzma.decompress(data) if index.endswith(".xz") else gzip.decompress(data)
            print(f"index: {mirror}/{index}")
            return mirror, data.decode("utf-8")
    raise SystemExit("No Termux index reachable:\n" + "\n".join(errors))


def parse_index(text: str) -> dict:
    out = {}
    for block in text.split("\n\n"):
        fields, key = {}, None
        for line in block.splitlines():
            if line.startswith((" ", "\t")) and key:
                fields[key] += "\n" + line.strip()
            elif ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
        if "Package" in fields:
            out[fields["Package"]] = fields
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_elf(p: Path) -> bool:
    try:
        with p.open("rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False


def needed(elf: Path) -> list:
    out = subprocess.run(["readelf", "-d", str(elf)], capture_output=True, text=True).stdout
    return re.findall(r"\(NEEDED\)\s+Shared library: \[([^\]]+)\]", out)


def deps_of(meta: dict) -> list:
    out = []
    for part in meta.get("Depends", "").split(","):
        alt = part.split("|")[0].strip()
        name = re.sub(r"\s*\(.*\)", "", alt).strip()
        if name:
            out.append(name)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    mirror, text = load_index()
    index = parse_index(text)
    work = Path(tempfile.mkdtemp(prefix="pyeye-jdk-"))
    extracted = {}
    sources = []

    def get(name: str) -> Path:
        if name in extracted:
            return extracted[name]
        meta = index.get(name)
        if not meta:
            raise SystemExit(f"{name} is not in the Termux aarch64 index")
        deb = work / Path(meta["Filename"]).name
        deb.write_bytes(fetch(f"{mirror}/{meta['Filename']}"))
        got = sha256(deb)
        if got != meta["SHA256"]:
            raise SystemExit(f"{name}: SHA-256 mismatch ({got} != {meta['SHA256']})")
        root = work / f"x-{name}"
        subprocess.run(["dpkg-deb", "-x", str(deb), str(root)], check=True)
        extracted[name] = root
        sources.append({"package": name, "version": meta["Version"], "sha256": got,
                        "deb_url": f"{MIRRORS[0]}/{meta['Filename']}"})
        print(f"  {name} {meta['Version']}")
        return root

    # 1) openjdk-17 and its whole Depends closure
    queue, seen = [JDK_PACKAGE], set()
    while queue:
        n = queue.pop(0)
        if n in seen:
            continue
        seen.add(n)
        get(n)
        queue += [d for d in deps_of(index[n]) if d in index and d not in seen]

    jdk_src = next((p.parent.parent for p in (extracted[JDK_PACKAGE] / PREFIX).rglob("bin/java")
                    if (p.parent.parent / "lib" / "server" / "libjvm.so").is_file()), None)
    if jdk_src is None:
        raise SystemExit("openjdk-17 package has no bin/java + lib/server/libjvm.so")
    jdk = out / "stage" / "jdk"
    if jdk.parent.exists():
        shutil.rmtree(jdk.parent)
    shutil.copytree(jdk_src, jdk, symlinks=True)
    awt = sorted(p.name for p in (jdk / "lib").glob("libawt*.so"))
    print("AWT libs:", awt)
    if "libawt.so" not in awt or "libawt_headless.so" not in awt:
        raise SystemExit("Termux openjdk-17 has no libawt.so + libawt_headless.so - cannot fix lint")

    # 2) soname -> file from every extracted package (regular files and symlinks)
    provided = {}
    for name, root in extracted.items():
        for f in (root / PREFIX / "lib").glob("*.so*") if (root / PREFIX / "lib").is_dir() else []:
            provided.setdefault(f.name, f)
    in_bundle = lambda so: any(p.name == so for p in jdk.rglob(so))  # noqa: E731

    # 3) transitive NEEDED closure into jdk/lib
    added, missing = [], set()
    pending = [p for p in jdk.rglob("*") if p.is_file() and not p.is_symlink() and is_elf(p)]
    while pending:
        elf = pending.pop()
        for so in needed(elf):
            if so in SYSTEM_LIBS or in_bundle(so):
                continue
            src = provided.get(so)
            if src is None:
                missing.add(f"{so} (needed by {elf.relative_to(jdk)})")
                continue
            dst = jdk / "lib" / so
            shutil.copy2(src.resolve(), dst)
            added.append(so)
            pending.append(dst)
    if missing:
        raise SystemExit("Unresolved native libraries:\n  " + "\n  ".join(sorted(missing)))
    print("bundled libs:", sorted(set(added)))

    (jdk / "PYTHON_EYE_SOURCES.json").write_text(json.dumps(
        {"built_from": sources, "bundled_libs": sorted(set(added)), "awt_libs": awt}, indent=2, sort_keys=True) + "\n")

    version = index[JDK_PACKAGE]["Version"]
    tar_path = out / "jdk.tar"
    with tarfile.open(tar_path, "w", format=tarfile.GNU_FORMAT) as tar:
        def clean(info):
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = EPOCH
            if info.isdir():
                info.mode = 0o755
            elif info.isfile():
                info.mode = 0o755 if info.mode & 0o111 else 0o644
            return info
        tar.add(jdk, arcname="jdk", filter=clean)
    packed = out / "jdk.tar.gz"
    with open(tar_path, "rb") as src, open(packed, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as gz:
            shutil.copyfileobj(src, gz)
    tar_path.unlink()
    digest = sha256(packed)
    safe = re.sub(r"[^0-9A-Za-z._-]", "_", version)
    asset = f"jdk17-android-bionic-awt-{safe}-{digest[:12]}.tar.gz"
    packed.replace(out / asset)
    info = {"asset_name": asset, "version": version, "sha256": digest,
            "file_size_bytes": (out / asset).stat().st_size, "awt_libs": awt,
            "bundled_libs": sorted(set(added)), "sources": sources}
    (out / "jdk-bundle.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps({k: info[k] for k in ("asset_name", "version", "sha256", "file_size_bytes")}, indent=2))


if __name__ == "__main__":
    main()
