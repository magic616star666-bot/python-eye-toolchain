#!/usr/bin/env python3
"""Safety self-test for the IDE's Kotlin RootfsExtractor (run through Harness.kt).

Builds small hostile/edge-case tar files and checks that nothing is ever written
outside the extraction directory, that absolute symlinks are treated as GUEST paths,
that hard links become guest symlinks and that device nodes are skipped.

usage: selftest_extractor.py <harness.jar>
"""
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def add_dir(tar, name):
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    info.mode = 0o755
    tar.addfile(info)


def add_file(tar, name, data=b"x", mode=0o644):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    tar.addfile(info, io.BytesIO(data))


def add_link(tar, name, target, kind=tarfile.SYMTYPE):
    info = tarfile.TarInfo(name)
    info.type = kind
    info.linkname = target
    tar.addfile(info)


def run(jar, tar_path, out):
    return subprocess.run(["java", "-jar", jar, "extract", str(tar_path), str(out), "1"],
                          capture_output=True, text=True)


def main():
    jar = sys.argv[1]
    work = Path(tempfile.mkdtemp(prefix="pyeye-selftest-"))
    host_probe = Path("/tmp/pyeye-selftest-pwned")
    host_probe.unlink(missing_ok=True)

    good = work / "good.tar"
    with tarfile.open(good, "w", format=tarfile.GNU_FORMAT) as tar:
        add_dir(tar, "root/")
        add_dir(tar, "root/usr/")
        add_dir(tar, "root/usr/bin/")
        add_dir(tar, "root/usr/share/")
        add_dir(tar, "root/etc/")
        add_dir(tar, "root/tmp/")
        add_file(tar, "root/etc/os-release", b"NAME=Test\n")
        add_link(tar, "root/bin", "usr/bin")
        add_file(tar, "root/bin/hello", b"#!/bin/sh\necho hi\n", 0o755)          # written THROUGH bin -> usr/bin
        add_link(tar, "root/etc/alt", "/usr/share")                            # absolute = guest path
        add_file(tar, "root/etc/alt/x.txt", b"guest\n")
        add_link(tar, "root/evil", "/../../../../../../tmp")                   # tries to reach host /tmp
        add_file(tar, "root/evil/pyeye-selftest-pwned", b"no\n")
        add_link(tar, "root/usr/bin/hello2", "root/usr/bin/hello", tarfile.LNKTYPE)
        dev = tarfile.TarInfo("root/dev-null-node")
        dev.type = tarfile.CHRTYPE
        dev.devmajor, dev.devminor = 1, 3
        tar.addfile(dev)
        long_name = "root/usr/share/" + "d" * 120 + "/" + "f" * 120 + ".txt"   # GNU long name
        add_file(tar, long_name, b"long\n")

    out = work / "out"
    r = run(jar, good, out)
    print(r.stdout, r.stderr)
    assert r.returncode == 0, "extract failed"
    assert (out / "usr/bin/hello").is_file() and os.access(out / "usr/bin/hello", os.X_OK), "file via relative symlink / exec bit"
    assert (out / "bin").is_symlink() and os.readlink(out / "bin") == "usr/bin"
    assert (out / "usr/share/x.txt").read_text() == "guest\n", "absolute symlink must resolve inside rootfs"
    assert (out / "etc/alt").is_symlink() and os.readlink(out / "etc/alt") == "/usr/share"
    assert (out / "tmp/pyeye-selftest-pwned").is_file(), "escape attempt must land in rootfs/tmp"
    assert not host_probe.exists(), "HOST /tmp WAS WRITTEN — extractor is unsafe"
    assert (out / "usr/bin/hello2").is_symlink() and os.readlink(out / "usr/bin/hello2") == "/usr/bin/hello"
    assert not (out / "dev-null-node").exists(), "device node must be skipped"
    assert (out / long_name[len("root/"):]).read_text() == "long\n", "GNU long names"

    bad = work / "bad.tar"
    with tarfile.open(bad, "w", format=tarfile.GNU_FORMAT) as tar:
        add_dir(tar, "root/")
        add_file(tar, "root/../outside.txt", b"bad\n")
    r = run(jar, bad, work / "out2")
    print(r.stdout, r.stderr)
    assert r.returncode != 0 and "leaves the rootfs" in r.stderr, "'..' entries must be refused"
    assert not (work / "outside.txt").exists()

    shutil.rmtree(work)
    print("SELFTEST_OK: no writes outside rootfs; guest symlinks, hard links, devices, long names handled")


if __name__ == "__main__":
    main()
