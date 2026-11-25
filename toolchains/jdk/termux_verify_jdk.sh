#!/bin/bash
# Runs INSIDE termux-docker (Android Bionic aarch64). Unpacks the JDK OUTSIDE the Termux
# prefix and runs it with the same kind of environment Python Eye gives Java children.
set -uo pipefail
DIST="$1"; RESULTS="$2"; mkdir -p "$RESULTS"
T=/data/local/tmp/pyeye-jdk-test
mkdir -p "$T" 2>/dev/null || T="$HOME/pyeye-jdk-test"
rm -rf "$T"; mkdir -p "$T/tmp" "$T/out"
tar -xzf "$DIST"/jdk17-android-bionic-awt-*.tar.gz -C "$T"
J="$T/jdk"
run() { # env like the IDE: JDK native dirs first, writable HOME/TMPDIR, no Termux paths
  env -i PATH="$J/bin:/system/bin" HOME="$T" TMPDIR="$T/tmp" ANDROID_ROOT=/system ANDROID_DATA=/data \
    LD_LIBRARY_PATH="$J/lib/server:$J/lib/jli:$J/lib" "$@"
}
fail=0
step() { local name="$1"; shift; echo "== $name"; if run "$@" > "$RESULTS/$name.txt" 2>&1; then echo "PASS $name"; else echo "FAIL $name"; fail=1; fi; tail -n 25 "$RESULTS/$name.txt"; }
step java-version "$J/bin/java" -version
step awt-lint-probe "$J/bin/java" -Djava.awt.headless=true -Djava.io.tmpdir="$T/tmp" -Xmx256m /work/toolchains/jdk/AwtLintProbe.java "$T/out"
step javac "$J/bin/javac" -version
step keytool env SP=pyeye-test-pass "$J/bin/keytool" -genkeypair -keystore "$T/out/k.p12" -storetype PKCS12 -alias a -keyalg RSA -keysize 2048 -validity 1 -dname CN=t -storepass:env SP -keypass:env SP
step jarsigner "$J/bin/jarsigner" -help
grep -q AWT_LINT_PROBE_PASS "$RESULTS/awt-lint-probe.txt" || fail=1
echo "RESULT: $([ $fail = 0 ] && echo PASS || echo FAIL)" | tee "$RESULTS/summary.txt"
exit $fail
