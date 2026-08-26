#!/usr/bin/env python3
"""Which audit rules have never fired, and which of those nobody has tested.

WHY THIS EXISTS. On its own, "this rule has never fired" is a weak signal - a
healthy config produces silence too. Crossed with the harness coverage list it
stops being weak: a rule that is BOTH uncovered by test_ha_audit.py AND has
never fired in N nightly runs is a rule whose silence proves nothing at all.
That is exactly the population both 2026-08-24 "structurally incapable of
firing" bugs came out of, and it is the population-level form of R7.

Measured 2026-08-25 on 38 logged runs: 34 rule ids emitted, 16 had ever fired,
9 had injectors - and 14 rules were in neither set.

  python3 scripts/audit_log_stats.py
  python3 scripts/audit_log_stats.py --log /config/www/spc/ha_audit.log

Exit 0 always. This reports; it does not gate.
"""
import argparse
import io
import os
import re
import subprocess
import sys

CONFIG = os.environ.get("HA_CONFIG", "/config").rstrip("/")
P = lambda *a: os.path.join(CONFIG, *a)
DEFAULT_LOG = P("www", "spc", "ha_audit.log")


def emitted_ids():
    """Every rule id ha_audit.py can emit, scraped from the source (R10)."""
    src = io.open(P("scripts", "ha_audit.py"), encoding="utf-8").read()
    out = {}
    for sev, rid in re.findall(r'\b(fail|warn|info)\(\s*"([a-z0-9-]+)"', src):
        out.setdefault(rid, set()).add(sev)
    return out


def covered_ids():
    """Rule ids the harness has an injector for - asked, never duplicated."""
    try:
        r = subprocess.run([sys.executable, P("scripts", "test_ha_audit.py"), "--list"],
                           capture_output=True, text=True, timeout=120,
                           env=dict(os.environ, HA_CONFIG=CONFIG))
    except (OSError, subprocess.SubprocessError):
        return None
    covered, section = set(), None
    for line in (r.stdout or "").splitlines():
        if line.startswith("COVERED"):
            section = "c"
        elif line and not line.startswith(" "):
            section = None
        elif section == "c" and line.strip():
            covered.add(line.strip())
    return covered or None


def parse_log(path):
    """(runs, {rule_id: times_fired})."""
    if not os.path.exists(path):
        return 0, {}
    runs, counts = 0, {}
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if re.match(r"^\d+ FAIL, \d+ WARN, \d+ INFO", line):
                runs += 1
                continue
            m = re.match(r"^(FAIL|WARN|INFO)\s+([a-z0-9-]+)\s", line)
            if m:
                counts[m.group(2)] = counts.get(m.group(2), 0) + 1
    return runs, counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=DEFAULT_LOG)
    a = ap.parse_args()

    em = emitted_ids()
    runs, counts = parse_log(a.log)
    covered = covered_ids()

    if not runs:
        print("no runs found in %s" % a.log)
        print("Is nightly_ha_audit passing --log? Without it this cannot "
              "distinguish a quiet rule from a broken one.")
        return 0

    print("%d logged runs   %d rule ids emitted by ha_audit.py" % (runs, len(em)))
    print()
    fired = set(counts)
    print("FIRED (%d):" % len(fired))
    for rid, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print("   %6d  %s" % (n, rid))

    never = sorted(set(em) - fired)
    print("\nNEVER FIRED in %d runs (%d):" % (runs, len(never)))
    for rid in never:
        print("   %s%s" % (rid, "" if covered is None or rid in covered
                           else "   <- and no injector"))

    if covered is None:
        print("\n(could not read harness coverage - the cross-reference below "
              "is the whole point of this script, so fix that first)")
        return 0

    danger = sorted(set(em) - fired - covered - {r for r, s in em.items() if s == {"info"}})
    print("\n" + "=" * 62)
    print("UNPROVEN IN BOTH DIRECTIONS (%d) - never fired, no injector." % len(danger))
    print("Silence here is not evidence. Write an injector before trusting one.")
    for rid in danger:
        print("   %s" % rid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
