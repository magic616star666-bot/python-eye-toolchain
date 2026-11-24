#!/usr/bin/env python3
"""Python Eye Android R8 release preflight (read-only; no network, build or key access)."""
import argparse
import json
import re
from pathlib import Path

def scan_project(root: Path):
    if not root.is_dir():
        raise ValueError("project must be an extracted Android Gradle project directory")
    results=[]
    for path in sorted(list(root.rglob("build.gradle")) + list(root.rglob("build.gradle.kts"))):
        if any(p in {".gradle", "build", ".git", "node_modules"} for p in path.relative_to(root).parts):
            continue
        if len(results) >= 30:
            break
        raw=path.read_text(encoding="utf-8",errors="replace")
        # Only the release build type is relevant. A whole-file search would misreport debug.
        m=re.search(r'\brelease\s*\{',raw)
        if not m:
            continue
        start=m.end(); depth=1; end=start
        while end<len(raw) and depth:
            if raw[end]=="{": depth+=1
            elif raw[end]=="}": depth-=1
            end+=1
        block=raw[start:end-1]
        no_comments=re.sub(r'(?m)^\s*//.*$|/\*[\s\S]*?\*/',"",block)
        minify=re.search(r'\b(?:isMinifyEnabled|minifyEnabled)\s*(?:=\s*)?true\b',no_comments)
        shrink=re.search(r'\b(?:isShrinkResources|shrinkResources)\s*(?:=\s*)?true\b',no_comments)
        modern=re.search(r'\boptimization\s*\{[^{}]*\benable\s*=\s*true',no_comments,re.S)
        debug=re.search(r'\b(?:isDebuggable|debuggable)\s*(?:=\s*)?true\b',no_comments)
        signing_debug=bool(re.search(r'\bsigningConfig\s*(?:=\s*)?(?:signingConfigs\.debug|getByName\(["\']debug["\']\))',no_comments))
        results.append({
          "gradle_file": str(path.relative_to(root)),
          "release_r8_enabled": bool(minify or modern),
          "release_resource_shrink_enabled": bool(shrink or modern),
          "release_debuggable_true": bool(debug),
          "release_uses_debug_signing": signing_debug,
          "proguard_rules_referenced": bool(re.search(r'\bproguardFiles\b',no_comments)),
          "result": "review" if not (minify or modern) or debug or signing_debug else "configuration_pass",
        })
    return {
      "tool":"python-eye-r8-release-check",
      "type":"static_preflight_not_a_build",
      "project":str(root),
      "gradle_release_blocks":results,
      "summary":"R8 is included in Android Gradle Plugin; release minification enables it. Signing is a separate requirement.",
      "verified_runtime":False,
      "next_action":"Build signed release, inspect mapping.txt and test APK on phone."
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project",required=True,help="Extracted Android Gradle project folder")
    args=parser.parse_args()
    try:
        result=scan_project(Path(args.project).resolve())
    except (OSError, ValueError) as e:
        parser.error(str(e))
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0 if result["gradle_release_blocks"] and all(x["result"]=="configuration_pass" for x in result["gradle_release_blocks"]) else 2

if __name__=="__main__":
    raise SystemExit(main())
