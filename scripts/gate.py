#!/usr/bin/env python3
"""The DEFINITION OF DONE gate, as one command.

WHY THIS EXISTS. The gate sequence lived in three places in CLAUDE.md - the
SESSION PROTOCOL end-of-session block (4 steps), DEFINITION OF DONE's "The
gate" (6 steps), and the PRE-COMMIT CHECKLIST (bullets) - which is R10 in the
file that declares R10. They had already drifted: the DoD block carried
py_compile and the ESPHome step, the session-protocol block did not.

Three things this buys, in order of importance:

  1. The verdict string is GENERATED. That is the only reliable defence
     against the assurance-upgrade failure the verdict table exists to
     prevent - nobody can type "PASS (HA-certified)" when what ran was a
     parse check.
  2. Skipping a step becomes impossible rather than discouraged.
  3. Four invocations become one.

STEPS 3-5 ARE NOT HERE ON PURPOSE. check_config, reload and observe all touch
the live instance, and R12 says confirm before acting outward. This script is
safe to run at any time against any tree; it never writes to Home Assistant.

  python3 scripts/gate.py configuration.yaml packages/spc.yaml
  python3 scripts/gate.py --baseline .audit_baseline.json <files>

Exit 0 only if every step that applies passed.
"""
import argparse
import os
import subprocess
import sys

CONFIG = os.environ.get("HA_CONFIG", "/config").rstrip("/")
P = lambda *a: os.path.join(CONFIG, *a)
YAML_EXT = (".yaml", ".yml")


def run(argv, label):
    print("\n--- %s" % label)
    print("    $ " + " ".join(os.path.basename(a) if a.endswith(".py") else a
                              for a in argv[1:]))
    try:
        r = subprocess.run(argv, env=dict(os.environ, HA_CONFIG=CONFIG),
                           capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.SubprocessError) as exc:
        print("    COULD NOT RUN: %s" % exc)
        return None, ""
    out = (r.stdout or "") + (r.stderr or "")
    for line in out.strip().splitlines()[-25:]:
        print("    " + line)
    return r.returncode, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="the files you edited")
    ap.add_argument("--baseline", metavar="FILE", default=P(".audit_baseline.json"))
    a = ap.parse_args()

    files = [f for f in a.files if os.path.exists(f) or os.path.exists(P(f))]
    yamls = [f for f in files if f.endswith(YAML_EXT)]
    pys = [f for f in files if f.endswith(".py")]
    # test_ha_audit.py added 2026-08-25, found by this gate reporting
    # "2b. RULES  n/a" on a commit that changed nothing BUT the harness.
    # Editing the harness is strictly more dangerous than editing the audit: a
    # broken audit reports the wrong findings, a broken harness reports SUCCESS
    # for every rule at once. That is the one file whose change must never skip
    # step 2b.
    GATE_2B_TRIGGERS = ("ha_audit.py", "gen_reference.py", "test_ha_audit.py")
    touched_audit = any(os.path.basename(f) in GATE_2B_TRIGGERS for f in files)

    verdicts, failed = [], False

    # ---- 1. SYNTAX ------------------------------------------------------
    if yamls:
        rc, _ = run([sys.executable, P("scripts", "validate_ha.py"), "--strict"] + yamls,
                    "1. SYNTAX   validate_ha.py --strict")
        ok = rc == 0
        failed |= not ok
        verdicts.append("PASS (parse-clean)" if ok else "FAIL (validate_ha --strict)")
    else:
        verdicts.append("n/a - no YAML edited")

    if pys:
        rc, _ = run([sys.executable, "-m", "py_compile"] + pys, "1b. SYNTAX  py_compile")
        failed |= rc != 0

    # ---- 2. SEMANTIC ----------------------------------------------------
    rc, out = run([sys.executable, P("scripts", "ha_audit.py"),
                   "--baseline", a.baseline], "2. SEMANTIC ha_audit.py --baseline")
    summary = next((l for l in out.splitlines() if " FAIL, " in l and " WARN," in l), "")
    ok = rc == 0
    failed |= not ok
    verdicts.append(summary.strip() or ("audit ok" if ok else "audit FAILED"))

    # ---- 2b. RULES ------------------------------------------------------
    if touched_audit:
        rc, out = run([sys.executable, P("scripts", "test_ha_audit.py")],
                      "2b. RULES   test_ha_audit.py (the audit itself moved)")
        ok = rc == 0
        failed |= not ok
        verdicts.append(next((l.strip() for l in out.splitlines()
                              if l.startswith("SUITE")), "SUITE result unreadable"))
    else:
        verdicts.append("n/a - none of %s edited" % ", ".join(GATE_2B_TRIGGERS))

    # ---- the block, generated -------------------------------------------
    print("\n" + "=" * 66)
    print("Gate:")
    print("  1. SYNTAX    %s" % verdicts[0])
    print("  2. SEMANTIC  %s" % verdicts[-2])
    print("  2b. RULES    %s" % verdicts[-1])
    print("  3. DEPLOYED  NOT RUN - POST /api/config/core/check_config yourself")
    print("  4. RELOAD    NOT RUN")
    print("  5. OBSERVE   NOT RUN")
    print()
    if failed:
        print("NOT READY. A step above failed; nothing here certifies HA will load it.")
    else:
        print("PASS (parse-clean) + audit delta clean.")
        print("This is NOT 'ready to restart'. Only step 3 returning \"valid\"")
        print("makes it PASS (HA-certified) - see CLAUDE.md's verdict table.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
