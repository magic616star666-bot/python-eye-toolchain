#!/usr/bin/env python3
"""Same rules as the IDE's BuildRules.parse(): an invalid file is ignored by phones, so fail CI instead."""
import json, re, sys
VERSION = re.compile(r"[0-9]{2}\.[0-9]{1,2}\.[0-9]{1,2}")
d = json.load(open("toolchains/build-rules.json"))
assert d["schema_version"] == 1, "schema_version must be 1"
rows = d["agp_build_tools"]
assert 1 <= len(rows) <= 12, "agp_build_tools: 1..12 rows"
for i, r in enumerate(rows):
    assert isinstance(r["min_agp_major"], int) and 0 <= r["min_agp_major"] <= 40, f"row {i}: min_agp_major"
    assert VERSION.fullmatch(r["build_tools"]), f"row {i}: build_tools"
rows = sorted(rows, key=lambda r: -r["min_agp_major"])
assert rows[-1]["min_agp_major"] == 0, "needs a min_agp_major 0 fallback row"
aliases = d.get("arm64_aliases", [])
assert len(aliases) <= 4 and all(VERSION.fullmatch(a) and a != "35.0.0" for a in aliases), "arm64_aliases"
missing = [r["build_tools"] for r in rows if r["build_tools"] != "35.0.0" and r["build_tools"] not in aliases]
assert not missing, f"table selects versions that are not staged on the phone: {missing}"
assert len(json.dumps(d)) < 64000
print("PASS build-rules.json: " + ", ".join(f"AGP {r['min_agp_major']}+ -> {r['build_tools']}" for r in rows)
      + f"; ARM64 aliases {aliases}")
