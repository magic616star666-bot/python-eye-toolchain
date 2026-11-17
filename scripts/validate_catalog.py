#!/usr/bin/env python3
"""Validate the Python Eye tool catalog (stdlib only)."""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

def check(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("tools"), list):
        raise ValueError('Root JSON needs a "tools" list')
    tools = data["tools"]
    if not tools:
        raise ValueError("Tools list is empty")
    ids = set()
    for item in tools:
        if not isinstance(item, dict):
            raise ValueError("Each entry must be a JSON object")
        key = item.get("id")
        if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9-]+", key):
            raise ValueError(f"Invalid tool id: {key!r}")
        if key in ids:
            raise ValueError(f"Duplicate tool id: {key}")
        ids.add(key)
        if not item.get("name"):
            raise ValueError(f"{key}: missing name")
        if not isinstance(item.get("requires"), list):
            raise ValueError(f"{key}: requires must be a list")
        if item.get("published") is True:
            url = item.get("url")
            digest = item.get("sha256", "")
            if not isinstance(url, str) or urlparse(url).scheme != "https":
                raise ValueError(f"{key}: a published tool needs an HTTPS download URL")
            if not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
                raise ValueError(f"{key}: a published tool needs its real SHA-256 checksum")
        elif item.get("url") or item.get("sha256"):
            raise ValueError(f"{key}: unpublished tool must not advertise download URLs/checksums")
    by_id = {item["id"]: item for item in tools}
    def visit(key, active, complete):
        if key in complete:
            return
        if key in active:
            raise ValueError(f"Dependency cycle at {key}")
        active.add(key)
        for dep in by_id[key]["requires"]:
            if dep not in by_id:
                raise ValueError(f"{key}: unknown dependency {dep}")
            visit(dep, active, complete)
        active.remove(key)
        complete.add(key)
    complete = set()
    for key in ids:
        visit(key, set(), complete)
    print(f"PASS: {len(tools)} catalog entries; {sum(bool(t['published']) for t in tools)} published; {len(tools) - sum(bool(t['published']) for t in tools)} awaiting binaries.")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(check(Path(sys.argv[1] if len(sys.argv) > 1 else "tools.json")))
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
