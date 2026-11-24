#!/usr/bin/env python3
"""Load + Test every maven_artifact_resolution tool in tools.json exactly like the IDE.

Load: the same build.gradle the IDE writes (ManagedToolResolver.mavenScript) -> `gradle verifyTool`.
Test: the same java -cp <lib/*.jar> <probe> runs as ToolStore.test, output must contain `expect`.
Needs `gradle` and `java` (17) on PATH. Exit 1 if any tool fails.
"""
import json, re, subprocess, sys, tempfile
from pathlib import Path

def build_gradle(coord, version, required_paths):
    artifact = coord.split(":", 1)[1]
    main = f"{artifact}-{version}.jar"
    alias = next((p[4:] for p in required_paths if re.fullmatch(r"lib/[A-Za-z0-9_.-]+\.jar", p)), None) \
        if len(required_paths) == 1 else None
    copy_alias = f"project.copy {{ from main; into 'lib'; rename {{ '{alias}' }} }}" if alias and alias != main else ""
    return f"""repositories {{ google(); mavenCentral() }}
configurations {{ toolJars }}
dependencies {{ toolJars '{coord}:{version}' }}
tasks.register('verifyTool') {{
    doLast {{
        def files = configurations.toolJars.resolve().findAll {{ it.name.endsWith('.jar') }}
        def main = files.find {{ it.name == '{main}' }}
        if (main == null || !main.isFile()) throw new GradleException('Artifact {main} missing')
        project.copy {{ from files; into 'lib' }}
        {copy_alias}
        println 'MAVEN_ARTIFACT_RESOLVED:{coord}:{version} jars=' + files.size()
    }}
}}
"""

failed = []
tools = [t for t in json.loads(Path("tools.json").read_text())["tools"]
         if t["install"]["method"] == "maven_artifact_resolution"]
for t in tools:
    tid, version, coord = t["id"], t["version"], t["install"]["plugin_id"]
    expect = t.get("expect") or version
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "settings.gradle").write_text("rootProject.name = 'PythonEyeManagedToolCheck'\n")
        (d / "build.gradle").write_text(build_gradle(coord, version, t["install"].get("required_paths", [])))
        load = subprocess.run(["gradle", "--no-daemon", "--console=plain", "-q", "verifyTool"], cwd=d,
                              capture_output=True, text=True)
        print(f"== {tid}: Load ({coord}:{version}) exit={load.returncode}\n{(load.stdout + load.stderr).strip()[-1500:]}")
        missing = [p for p in t["install"].get("required_paths", []) if not (d / p).is_file()]
        jars = sorted(str(j) for j in (d / "lib").glob("*.jar")) if (d / "lib").is_dir() else []
        if load.returncode != 0 or missing or not jars:
            failed.append(f"{tid}: Load failed (missing={missing}, jars={len(jars)})")
            continue
        for probe in t["required_probes"]:
            r = subprocess.run(["java", "-cp", ":".join(jars)] + probe.split(" "), cwd=d,
                               capture_output=True, text=True, timeout=180)
            out = (r.stdout + r.stderr).strip()
            ok = r.returncode == 0 and expect in out
            print(f"   Test {probe}: exit={r.returncode} {'OK' if ok else 'FAIL'} | {out[-300:]}")
            if not ok:
                failed.append(f"{tid}: {probe} (expected '{expect}')")
print(f"\nMaven JAR tools: {len(tools) - len({f.split(':')[0] for f in failed})}/{len(tools)} passed Load + Test")
if failed:
    print("FAILED:\n  " + "\n  ".join(failed))
    sys.exit(1)
