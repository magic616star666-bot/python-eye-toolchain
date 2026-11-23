# Python Eye Linux runtime — Ubuntu via PRoot (Android ARM64)

Python Eye IDE can run a full **Ubuntu ARM64 userland** inside the app, without root,
the same way Quantum IDE / proot-distro do it. Inside it, real Linux tools are installed
with `apt`, `npm` and `pip`: Git, GitHub CLI, Node.js, Python + pip/venv/uv, GCC/Clang,
CMake/Ninja, Go, Rust, PHP, Java 21, Ruby, SQLite/OpenSSL dev libraries, protoc,
SSH/SFTP, QEMU user-mode, language servers (Pyright, TypeScript, HTML/CSS/JSON, YAML,
Bash, clangd, gopls), AI CLIs (Claude Code, Gemini CLI, Codex) and Flutter.

## What the IDE downloads

| File | From | Check |
|---|---|---|
| `proot-android-arm64-<version>.tar.gz` | this repo, Release [`linux-runtime-v1`](https://github.com/magic616star666-bot/python-eye-toolchain/releases/tag/linux-runtime-v1) | SHA-256 + size from [`linux-runtime.json`](../linux-runtime.json) |
| Ubuntu ARM64 rootfs `.tar.xz` | original [termux/proot-distro](https://github.com/termux/proot-distro/releases) release (not re-hosted) | SHA-256 + size from [`linux-runtime.json`](../linux-runtime.json) |

The PRoot bundle is built by CI from the official Termux `proot` and `libtalloc`
aarch64 packages (their SHA-256 is checked against the Termux package index). It
contains `bin/proot`, `lib/libtalloc.so.2`, `libexec/proot/loader[32]`, the licence
files and `SOURCES.json`. The IDE sets `LD_LIBRARY_PATH`, `PROOT_LOADER` and
`PROOT_TMP_DIR`, so nothing depends on Termux being installed.

## Catalogs

- [`linux-runtime.json`](../linux-runtime.json) — written by CI: pinned PRoot bundle + rootfs, and the CI proof.
- [`linux-packages.json`](../linux-packages.json) — install recipe + probe for every tool (hand-written, validated by `recipes.py`).
- [`linux-ci-results.json`](../linux-ci-results.json) — written by CI: what happened to every package.

These are **new files**. The existing `tools.json` and `mobile-artifacts.json` are
unchanged, because older IDE versions reject a whole catalog that contains an unknown
tool family.

## How CI proves it ([`linux-runtime.yml`](../../.github/workflows/linux-runtime.yml))

1. **bundle** (x86_64): builds the PRoot bundle, pins the rootfs, compiles the IDE's own
   [`LinuxCore.kt`](kotlin/LinuxCore.kt) (identical to the IDE source) with
   [`Harness.kt`](kotlin/Harness.kt), runs the extractor safety self-test, then unpacks
   and configures Ubuntu **with the IDE's code** and generates the IDE's exact PRoot
   command line.
2. **verify** (GitHub `ubuntu-24.04-arm`): starts `termux/termux-docker:aarch64` — a real
   Android **Bionic** userland on ARM64 — installs the bundle outside the Termux prefix,
   boots Ubuntu, checks the project-folder bind, runs `apt-get update`, then installs and
   probes every package (compile-and-run tests for C and Go).
3. **publish**: uploads the bundle to the `linux-runtime-v1` Release, checks GitHub's
   asset digest, writes the two JSON files and commits them.

## Status truth

- *CI ok* = installed and probed inside the Android-Bionic ARM64 container.
- *Ready on phone* = the IDE ran the same probe on your phone. A phone adds SELinux and
  app-sandbox limits that Docker does not have, so the IDE never copies CI status.
- Python Eye targets Android API 28, so files it unpacks may be executed (Android blocks
  this for apps targeting API 29+).

## Hindi / Hinglish

Python Eye ab app ke andar hi **Ubuntu (PRoot)** chala sakta hai — bina root. Setup
screen se ek baar install karo; phir Extensions → Linux se Git, Node.js, GitHub CLI,
Rust, Go, C/C++, PHP, Java 21, language servers, Claude Code / Gemini / Codex CLI
waghera ek tap mein install aur test hote hain. Har tool tabhi "Ready" dikhega jab
uska test aapke phone par pass ho.
