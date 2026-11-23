#!/usr/bin/env python3
"""Build the relocatable PRoot bundle used by Python Eye IDE's Linux (Ubuntu) runtime.

Source: the official Termux aarch64 packages `proot` and `libtalloc` (Android/Bionic
builds). Each .deb is checked against the SHA-256 published in the Termux package
index, unpacked, and the three runtime pieces are copied into a small tree:

    proot/bin/proot                  (Android/Bionic ARM64 PIE executable)
    proot/lib/libtalloc.so.2         (its only non-system dependency)
    proot/libexec/proot/loader[32]   (static ELF loaders, chosen with PROOT_LOADER)
    proot/LICENSES/*, proot/SOURCES.json

The IDE sets LD_LIBRARY_PATH, PROOT_LOADER and PROOT_TMP_DIR, so nothing depends on
Termux's /data/data/com.termux prefix. proot is GPL-2.0 and talloc LGPL-3.0; the
licence files and the exact upstream source locations are shipped in the bundle.
"""
import argparse
import gzip
import hashlib
import json
import lzma
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

MIRRORS = [
    "https://packages-cf.termux.dev/apt/termux-main",
    "https://packages.termux.dev/apt/termux-main",
    "https://grimler.se/termux/termux-main",
]
INDEXES = [
    "dists/stable/main/binary-aarch64/Packages.xz",
    "dists/stable/main/binary-aarch64/Packages.gz",
    "dists/stable/main/binary-aarch64/Packages",
]
PREFIX = Path("data/data/com.termux/files/usr")
SYSTEM_LIBS = {"libc.so", "libdl.so", "libm.so", "liblog.so"}
SOURCES = {
    "proot": {
        "upstream": "https://github.com/termux/proot",
        "build_recipe": "https://github.com/termux/termux-packages/tree/master/packages/proot",
        "license": "GPL-2.0-or-later",
    },
    "libtalloc": {
        "upstream": "https://www.samba.org/ftp/talloc/",
        "build_recipe": "https://github.com/termux/termux-packages/tree/master/packages/libtalloc",
        "license": "LGPL-3.0-or-later",
    },
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "python-eye-toolchain-ci"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def load_index():
    errors = []
    for mirror in MIRRORS:
        for index in INDEXES:
            try:
                data = fetch(f"{mirror}/{index}")
            except Exception as exc:  # noqa: BLE001 - try the next mirror
                errors.append(f"{mirror}/{index}: {exc}")
                continue
            if index.endswith(".xz"):
                data = lzma.decompress(data)
            elif index.endswith(".gz"):
                data = gzip.decompress(data)
            print(f"index: {mirror}/{index} ({len(data)} bytes)")
            return mirror, data.decode("utf-8")
    raise SystemExit("No Termux package index reachable:\n" + "\n".join(errors))


def parse_index(text: str) -> dict:
    packages = {}
    for block in text.split("\n\n"):
        fields, key = {}, None
        for line in block.splitlines():
            if line.startswith((" ", "\t")) and key:
                fields[key] += "\n" + line.strip()
            elif ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
        if "Package" in fields:
            packages[fields["Package"]] = fields
    return packages


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def needed(elf: Path) -> list:
    out = subprocess.run(["readelf", "-d", str(elf)], check=True, capture_output=True, text=True).stdout
    return re.findall(r"\(NEEDED\)\s+Shared library: \[([^\]]+)\]", out)


def elf_header(elf: Path) -> str:
    return subprocess.run(["readelf", "-h", str(elf)], check=True, capture_output=True, text=True).stdout


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    mirror, text = load_index()
    index = parse_index(text)
    work = Path(tempfile.mkdtemp(prefix="pyeye-proot-"))
    sources = []
    unpacked = {}
    for name in ("proot", "libtalloc"):
        meta = index.get(name)
        if not meta:
            raise SystemExit(f"{name} is not in the Termux aarch64 index")
        url = f"{mirror}/{meta['Filename']}"
        deb = work / Path(meta["Filename"]).name
        deb.write_bytes(fetch(url))
        digest = sha256(deb)
        if digest != meta["SHA256"].lower():
            raise SystemExit(f"{name}: SHA-256 mismatch {digest} != {meta['SHA256']}")
        root = work / f"x-{name}"
        subprocess.run(["dpkg-deb", "-x", str(deb), str(root)], check=True)
        unpacked[name] = root / PREFIX
        sources.append({
            "package": name,
            "version": meta["Version"],
            "deb": Path(meta["Filename"]).name,
            "deb_url": url,
            "deb_sha256": digest,
            "architecture": meta.get("Architecture"),
            **SOURCES[name],
        })
        print(f"{name} {meta['Version']} OK sha256={digest}")

    proot_version = next(s["version"] for s in sources if s["package"] == "proot")
    talloc_version = next(s["version"] for s in sources if s["package"] == "libtalloc")
    bundle = work / "bundle" / "proot"
    (bundle / "bin").mkdir(parents=True)
    (bundle / "lib").mkdir()
    (bundle / "libexec" / "proot").mkdir(parents=True)
    (bundle / "LICENSES").mkdir()

    src_proot = unpacked["proot"] / "bin" / "proot"
    shutil.copy2(src_proot, bundle / "bin" / "proot")
    loaders = []
    for loader in ("loader", "loader32"):
        src = unpacked["proot"] / "libexec" / "proot" / loader
        if src.is_file():
            shutil.copy2(src, bundle / "libexec" / "proot" / loader)
            loaders.append(loader)
    if "loader" not in loaders:
        raise SystemExit("proot package has no libexec/proot/loader")

    header = elf_header(bundle / "bin" / "proot")
    if "AArch64" not in header or "DYN" not in header:
        raise SystemExit("proot is not an ARM64 PIE executable:\n" + header)

    deps = needed(bundle / "bin" / "proot")
    print("proot NEEDED:", deps)
    for dep in deps:
        if dep in SYSTEM_LIBS:
            continue
        candidates = sorted((unpacked["libtalloc"] / "lib").glob(dep + "*")) + \
            sorted((unpacked["libtalloc"] / "lib").glob(dep.split(".so")[0] + ".so*"))
        real = next((c for c in candidates if c.is_file() and not c.is_symlink()), None)
        if real is None:
            real = next((c.resolve() for c in candidates if c.exists()), None)
        if real is None or "talloc" not in dep:
            raise SystemExit(f"Unexpected dependency {dep}; bundle refuses to guess")
        shutil.copy2(real, bundle / "lib" / dep)
        lib_deps = needed(bundle / "lib" / dep)
        unknown = [d for d in lib_deps if d not in SYSTEM_LIBS]
        if unknown:
            raise SystemExit(f"{dep} needs {unknown}")
    for name in ("proot", "libtalloc"):
        doc = unpacked[name] / "share" / "doc" / name / "copyright"
        if doc.is_file():
            shutil.copy2(doc, bundle / "LICENSES" / f"{name}.copyright")
        for lic in (unpacked[name] / "share" / "LICENSES").glob("*") if (unpacked[name] / "share" / "LICENSES").is_dir() else []:
            shutil.copy2(lic, bundle / "LICENSES" / f"{name}-{lic.name}")
    (bundle / "SOURCES.json").write_text(json.dumps({
        "built_by": "python-eye-toolchain .github/workflows/linux-runtime.yml",
        "termux_mirror": mirror,
        "packages": sources,
        "runtime_env": {
            "LD_LIBRARY_PATH": "<bundle>/lib",
            "PROOT_LOADER": "<bundle>/libexec/proot/loader",
            "PROOT_LOADER_32": "<bundle>/libexec/proot/loader32 (when present)",
            "PROOT_TMP_DIR": "<writable app directory>",
        },
    }, indent=2) + "\n")
    for f in (bundle / "bin" / "proot", *(bundle / "libexec" / "proot").iterdir()):
        f.chmod(0o755)

    safe_version = re.sub(r"[^0-9A-Za-z._-]", "_", proot_version)
    asset = f"proot-android-arm64-{safe_version}.tar.gz"
    archive = out / asset
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as tar:
        def clean(info):
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            return info
        tar.add(bundle, arcname="proot", filter=clean)
    info = {
        "asset_name": asset,
        "version": proot_version,
        "talloc_version": talloc_version,
        "sha256": sha256(archive),
        "file_size_bytes": archive.stat().st_size,
        "top_dir": "proot",
        "loaders": loaders,
        "needed": deps,
        "sources": sources,
    }
    (out / "proot-bundle.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    sys.exit(main())
