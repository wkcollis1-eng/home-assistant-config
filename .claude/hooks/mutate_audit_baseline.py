"""Each mutant of the new ha_audit_gate.py must make test_audit_baseline.py FAIL (R7)."""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "ha_audit_gate.py"), encoding="utf-8").read()
MUTANTS = [
    (
        "stop ignores the baseline",
        "have_base = bool(base) and os.path.exists(base)",
        "have_base = False",
    ),
    (
        "inherited FAIL baselined",
        'clean = bool(m) and m.group(1) == "0" and v.startswith("0 FAIL")',
        'clean = bool(m) and m.group(1) == "0"',
    ),
    (
        "fallback ignores WARN",
        'clean = v.startswith("0 FAIL") and " 0 WARN," in v',
        'clean = v.startswith("0 FAIL")',
    ),
    (
        "one shared baseline",
        '"audit_baseline_%s.json" % sid',
        '"audit_baseline_%s.json" % "x"',
    ),
    (
        "missing delta line = clean",
        'clean = bool(m) and m.group(1) == "0" and',
        'clean = (not m or m.group(1) == "0") and',
    ),
    (
        "vanished baseline re-trusted",
        'if not m and "BASELINE WRITTEN" in out:',
        "if False:",
    ),
    (
        "start keeps an old baseline",
        "            if os.path.exists(p):\n                os.remove(p)",
        "            if False:\n                os.remove(p)",
    ),
    (
        "prune keeps old files",
        "if os.path.getmtime(p) < cutoff:",
        "if os.path.getmtime(p) > cutoff:",
    ),
    ("start drops the note", "out + note + deploy_drift()", "out + deploy_drift()"),
]
bad = 0
for name, old, new in MUTANTS:
    if SRC.count(old) != 1:
        print("  SETUP  %s: anchor found %d times" % (name, SRC.count(old)))
        bad += 1
        continue
    p = os.path.join(HERE, "mutant_tmp.py")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(SRC.replace(old, new))
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "test_audit_baseline.py"), p],
        capture_output=True,
        text=True,
        timeout=600,
    )
    caught = r.returncode != 0
    bad += not caught
    print("  %s  %s" % ("CAUGHT " if caught else "MISSED ", name))
os.remove(os.path.join(HERE, "mutant_tmp.py"))
print("%d/%d mutants caught" % (len(MUTANTS) - bad, len(MUTANTS)))
sys.exit(1 if bad else 0)
