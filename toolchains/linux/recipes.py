#!/usr/bin/env python3
"""Validate toolchains/linux-packages.json and turn it into CI recipe lines.

The install/probe command text built here is the SAME rule the IDE uses
(LinuxPackages.kt in Python Eye IDE): apt -> script -> pip -> npm, under `set -e`.

    recipes.py validate
    recipes.py tsv <out.tsv>     # id, needs, timeout_s, b64(install), b64(probe), b64(expect)
"""
import base64
import json
import re
import sys
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "linux-packages.json"
ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,48}$")
APT = re.compile(r"^[a-z0-9][a-z0-9+.-]{1,80}$")
NPM = re.compile(r"^(@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*(@[0-9A-Za-z.^~<>=*-]+)?$")
PIP = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*([<>=!~]=?[0-9A-Za-z.*]+)?$")
CATEGORIES = {"languages", "ai", "tools", "lsp", "build"}


def load():
    doc = json.loads(CATALOG.read_text())
    if doc.get("schema_version") != 1:
        raise SystemExit("schema_version must be 1")
    seen = []
    for p in doc["packages"]:
        pid = p["id"]
        if not ID.match(pid) or pid in seen:
            raise SystemExit(f"bad or duplicate id {pid}")
        if p.get("category") not in CATEGORIES:
            raise SystemExit(f"{pid}: bad category")
        for need in p.get("needs", []):
            if need not in seen:
                raise SystemExit(f"{pid}: dependency {need} must be listed earlier")
        for a in p.get("apt", []):
            if not APT.match(a):
                raise SystemExit(f"{pid}: bad apt name {a}")
        for a in p.get("npm", []):
            if not NPM.match(a):
                raise SystemExit(f"{pid}: bad npm name {a}")
        for a in p.get("pip", []):
            if not PIP.match(a):
                raise SystemExit(f"{pid}: bad pip name {a}")
        if not (p.get("apt") or p.get("npm") or p.get("pip") or p.get("script")):
            raise SystemExit(f"{pid}: nothing to install")
        if not p.get("probe") or not p.get("expect"):
            raise SystemExit(f"{pid}: probe and expect are required")
        re.compile(p["expect"])
        seen.append(pid)
    return doc


def install_command(p: dict) -> str:
    lines = ["set -e"]
    if p.get("apt"):
        lines.append("apt-get install -y --no-install-recommends " + " ".join(p["apt"]))
    if p.get("script"):
        lines.append(p["script"])
    if p.get("pip"):
        lines.append("python3 -m pip install --break-system-packages --no-cache-dir " + " ".join(p["pip"]))
    if p.get("npm"):
        lines.append("npm install -g --no-fund --no-audit " + " ".join(p["npm"]))
    return "\n".join(lines)


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def main(argv):
    doc = load()
    if len(argv) >= 2 and argv[1] == "tsv":
        rows = []
        for p in doc["packages"]:
            rows.append("\t".join([
                p["id"], ",".join(p.get("needs", [])) or "-", str(int(p.get("timeout_minutes", 20)) * 60),
                b64(install_command(p)), b64(p["probe"]), b64(p["expect"]),
            ]))
        Path(argv[2]).write_text("\n".join(rows) + "\n")
        print(f"{len(rows)} recipes written")
    else:
        print(f"OK: {len(doc['packages'])} Linux packages")


if __name__ == "__main__":
    main(sys.argv)
