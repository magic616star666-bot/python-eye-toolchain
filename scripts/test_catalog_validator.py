#!/usr/bin/env python3
"""Regression tests for the catalog validator; stdlib only."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from validate_catalog import check

ORIGINAL=json.loads(Path("tools.json").read_text(encoding="utf-8"))

def assert_rejected(label,change):
    data=copy.deepcopy(ORIGINAL)
    change(data)
    with TemporaryDirectory() as td:
        file=Path(td)/"tools.json"
        file.write_text(json.dumps(data),encoding="utf-8")
        try:
            check(file)
        except (ValueError, KeyError, TypeError, AssertionError) as exc:
            print(f"PASS rejects {label}: {exc}")
            return
    raise AssertionError(f"Validator incorrectly accepted {label}")

check(Path("tools.json"))
assert_rejected("missing list",lambda d:d.pop("tools"))
assert_rejected("duplicate IDs",lambda d:d["tools"][1].update(id=d["tools"][0]["id"]))
assert_rejected("fake managed archive",lambda d:d["tools"][2].update(published=True))
assert_rejected("bad archive SHA",lambda d:d["tools"][0].update(sha256="0"))
assert_rejected("insecure URL",lambda d:d["tools"][0].update(url="http://bad.example/tool.zip"))
assert_rejected("archive type mismatch",lambda d:d["tools"][0].update(archive_format="zip"))
assert_rejected("unknown dependency",lambda d:d["tools"][1].update(requires=["does-not-exist"]))
assert_rejected("dependency cycle",lambda d:d["tools"][0].update(requires=["gradle"]))
assert_rejected("false phone verified",lambda d:d["tools"][0]["install"].update(device_verified=True))
assert_rejected("incorrect AGP version",lambda d:d["tools"][6].update(version="9.5.0"))
assert_rejected("missing real release size",lambda d:d["tools"][0].pop("file_size_bytes"))
print("PASS: positive catalog and 11 negative regression tests.")
