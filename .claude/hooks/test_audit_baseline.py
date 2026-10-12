#!/usr/bin/env python
"""Fire/silent tests for ha_audit_gate.py's session baseline (CLAUDE.md R7).

Runs the gate as a subprocess, as Claude Code does (mode argv, JSON on stdin),
against a fake ha_audit.py that follows the real CLI contract: --log appends
the human report, --baseline FILE writes FILE when absent and otherwise prints
NEW/FIXED lines and "N NEW, N FIXED, N UNCHANGED". The fake is not the real
comparison - the live end-to-end run against a sandbox config copy is recorded
in CHANGELOG.md 2026-10-11. Touches nothing outside a temp dir.

    python test_audit_baseline.py [path/to/ha_audit_gate.py]
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = (
    os.path.abspath(sys.argv[1])
    if len(sys.argv) > 1
    else os.path.join(HERE, "ha_audit_gate.py")
)
FAILS = 0

FAKE = r"""
import io, json, os, sys
f = json.loads(os.environ.get("FAKE_FINDINGS", "[]"))
a = sys.argv[1:]
opt = lambda k: a[a.index(k) + 1] if k in a else None
n = {s: sum(1 for x in f if x[0] == s) for s in ("FAIL", "WARN", "INFO")}
summary = "%d FAIL, %d WARN, %d INFO across 3 pipelines" % (n["FAIL"], n["WARN"], n["INFO"])
lines = ["%-5s %-24s %s" % tuple(x) for x in f]
if opt("--log"):
    with io.open(opt("--log"), "a", encoding="utf-8") as fh:
        fh.write("\n===== 2026-10-11T12:00:00 =====\n" + "\n".join(lines + [summary]) + "\n")
base = opt("--baseline")
if base and os.environ.get("FAKE_DROP_BASELINE") and os.path.exists(base):
    os.remove(base)  # simulates the file vanishing after the gate checked it
if not base:
    print("\n".join(lines) + "\n\n" + summary)
    sys.exit(1 if n["FAIL"] else 0)
cur = sorted("%s|%s|%s" % tuple(x) for x in f if x[0] != "INFO")
if not os.path.exists(base):
    json.dump({"findings": cur}, open(base, "w"))
    print("BASELINE WRITTEN  %s  (%d finding(s) recorded)" % (base, len(cur)))
    print(summary)
    sys.exit(1 if n["FAIL"] else 0)
try:
    prev = json.load(open(base)).get("findings") or []
except ValueError as e:
    print("FAIL  baseline-unreadable       %s: %s" % (base, e))
    sys.exit(1)
new, fixed = sorted(set(cur) - set(prev)), sorted(set(prev) - set(cur))
for k in new:
    print("NEW    %s" % k.replace("|", "  ", 2))
for k in fixed:
    print("FIXED  %s" % k.replace("|", "  ", 2))
print("\n%d NEW, %d FIXED, %d UNCHANGED   (baseline %s)" % (len(new), len(fixed), len(set(cur) & set(prev)), base))
print(summary)
sys.exit(1 if (new or n["FAIL"]) else 0)
"""

W = [
    "WARN",
    "open-question",
    "UNANSWERED since 2026-09-30 - 11 days outstanding: clamp reading",
]
W2 = ["WARN", "entity-ref-unresolved", "automations.yaml: sensor.zz_gate_fault"]
W3 = ["WARN", "open-question", "UNANSWERED since 2026-10-11: a second question"]
F = ["FAIL", "fetch-health", "sensor.x is unavailable since 2026-10-11"]
INF = ["INFO", "eod-concurrent", "3 same-second groups checked"]


class Box:
    """A fresh config dir, stamp, state dir and fake audit."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="gatebase_")
        self.cfg = os.path.join(self.root, "cfg")
        self.state = os.path.join(self.root, "state")
        os.makedirs(self.cfg)
        self.yaml = os.path.join(self.cfg, "x.yaml")
        open(self.yaml, "w").close()
        self.fake = os.path.join(self.root, "fake_audit.py")
        with open(self.fake, "w") as fh:
            fh.write(FAKE)
        self.tick = time.time()

    def run(self, mode, sid, findings, touch=False, **extra_env):
        if touch:
            self.tick += 10
            os.utime(self.yaml, (self.tick, self.tick))
        env = dict(
            os.environ,
            HA_GATE_CONFIG=self.cfg + "/",
            HA_GATE_AUDIT=self.fake,
            HA_GATE_STAMP=os.path.join(self.root, "stamp"),
            HA_GATE_STATE=self.state,
            FAKE_FINDINGS=json.dumps(findings),
            **extra_env,
        )
        stdin = json.dumps({"session_id": sid, "hook_event_name": mode}) if sid else ""
        r = subprocess.run(
            [sys.executable, GATE, mode],
            input=stdin,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        try:
            return json.loads(r.stdout) if r.stdout.strip() else {}
        except ValueError:
            return {"_raw": r.stdout + r.stderr}

    def base(self, sid):
        return os.path.join(self.state, "audit_baseline_%s.json" % sid)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


def ctx(o):
    return (o.get("hookSpecificOutput") or {}).get("additionalContext") or ""


def blocked(o):
    return o.get("decision") == "block"


def check(name, ok, got=None):
    global FAILS
    FAILS += not ok
    print(
        "  %s  %s%s"
        % ("PASS" if ok else "FAIL", name, "" if ok else ": got %r" % (got,))
    )


def case(name, fn):
    b = Box()
    try:
        fn(b, name)
    except Exception as e:  # a crash is a failed case, not a crashed suite
        check(name, False, "exception %r" % e)
    finally:
        b.close()


def t_start(b, n):
    o = b.run("sessionstart", "s1", [W, INF])
    c = ctx(o)
    check(
        n,
        "WARN  open-question" in c
        and "0 FAIL, 1 WARN, 1 INFO" in c
        and "INFO  eod" in c
        and os.path.exists(b.base("s1"))
        and "BASELINE WRITTEN" not in c
        and "NO STOP-GATE BASELINE" not in c
        and "=====" not in c,
        c,
    )


def t_inherited_silent(b, n):
    b.run("sessionstart", "s1", [W, INF])
    o = b.run("stop", "s1", [W, INF], touch=True)
    check(n, o == {}, o)


def t_new_warn_fires(b, n):
    b.run("sessionstart", "s1", [W])
    r = b.run("stop", "s1", [W, W2], touch=True).get("reason", "")
    check(
        n,
        "entity-ref-unresolved" in r
        and "NEW" in r
        and "open-question" not in r
        and "--baseline" in r,
        r,
    )


def t_new_question_fires(b, n):
    b.run("sessionstart", "s1", [W])
    r = b.run("stop", "s1", [W, W3], touch=True).get("reason", "")
    check(n, "a second question" in r and "11 days outstanding" not in r, r)


def t_inherited_fail_fires(b, n):
    b.run("sessionstart", "s1", [F, W])
    o = b.run("stop", "s1", [F, W], touch=True)
    check(n, blocked(o) and "never baselined" in o.get("reason", ""), o)


def t_no_baseline_fires(b, n):
    b.run("sessionstart", "s1", [W])
    o = b.run("stop", "s2", [W], touch=True)
    check(
        n,
        blocked(o)
        and "No session-start baseline" in o.get("reason", "")
        and "open-question" in o.get("reason", "")
        and not os.path.exists(b.base("s2")),
        o,
    )


def t_no_sid_fires(b, n):
    b.run("sessionstart", "s1", [W])
    o = b.run("stop", None, [W], touch=True)
    check(n, blocked(o) and "No session-start baseline" in o.get("reason", ""), o)


def t_corrupt_fires(b, n):
    b.run("sessionstart", "s1", [W])
    with open(b.base("s1"), "w") as fh:
        fh.write("{")
    o = b.run("stop", "s1", [W], touch=True)
    check(n, blocked(o) and "baseline-unreadable" in o.get("reason", ""), o)


def t_vanished_fires(b, n):
    b.run("sessionstart", "s1", [W])
    o = b.run("stop", "s1", [W, W2], touch=True, FAKE_DROP_BASELINE="1")
    o2 = b.run(
        "stop", "s1", [W, W2], touch=True
    )  # must not compare against a blessed file
    check(
        n,
        blocked(o)
        and "vanished" in o.get("reason", "")
        and not os.path.exists(b.base("s1"))
        and blocked(o2)
        and "No session-start baseline" in o2.get("reason", ""),
        (o, o2),
    )


def t_start_no_sid(b, n):
    c = ctx(b.run("sessionstart", None, [W]))
    check(n, "WARN  open-question" in c and "NO STOP-GATE BASELINE" in c, c)


def t_untouched_silent(b, n):
    b.run("sessionstart", "s1", [W])
    o = b.run("stop", "s1", [W, W2])
    check(n, o == {}, o)


def t_fixed_silent(b, n):
    b.run("sessionstart", "s1", [W, W2])
    o = b.run("stop", "s1", [W], touch=True)
    check(n, o == {}, o)


def t_sessions_separate(b, n):
    b.run("sessionstart", "s1", [W])
    b.run("sessionstart", "s2", [W, W2])
    o = b.run("stop", "s1", [W, W2], touch=True)
    check(n, blocked(o) and "entity-ref-unresolved" in o.get("reason", ""), o)


def t_gives_way(b, n):
    b.run("sessionstart", "s1", [W])
    got = [b.run("stop", "s1", [W, W2], touch=True) for _ in range(3)]
    check(
        n,
        blocked(got[0])
        and blocked(got[1])
        and not blocked(got[2])
        and "letting the turn end" in got[2].get("systemMessage", ""),
        got,
    )


def t_resume_rebaselines(b, n):
    b.run("sessionstart", "s1", [W])
    c = ctx(b.run("sessionstart", "s1", [W, W2]))  # resume: W2 is now read aloud
    o = b.run("stop", "s1", [W, W2], touch=True)
    check(n, "entity-ref-unresolved" in c and o == {}, (c, o))


def t_prune(b, n):
    os.makedirs(b.state)
    old, keep = b.base("old"), b.base("recent")
    for p in (old, keep):
        open(p, "w").close()
    t = time.time() - 40 * 86400
    os.utime(old, (t, t))
    b.run("sessionstart", "s1", [W])
    check(n, not os.path.exists(old) and os.path.exists(keep), os.listdir(b.state))


CASES = [
    ("start: full report injected, baseline written", t_start),
    ("SILENT: inherited WARN only, H: touched", t_inherited_silent),
    ("FIRES: new WARN, names only the new one", t_new_warn_fires),
    ("FIRES: new open-question, same rule name", t_new_question_fires),
    ("FIRES: inherited FAIL is never baselined", t_inherited_fail_fires),
    (
        "FIRES: no baseline for this session (fails closed, writes none)",
        t_no_baseline_fires,
    ),
    ("FIRES: no session id at stop (fails closed)", t_no_sid_fires),
    ("FIRES: unreadable baseline", t_corrupt_fires),
    (
        "FIRES: baseline vanished mid-run; the re-written one is not trusted",
        t_vanished_fires,
    ),
    ("start with no session id says the gate falls back", t_start_no_sid),
    (
        "SILENT: new WARN but H: untouched (mtime short-circuit kept)",
        t_untouched_silent,
    ),
    ("SILENT: a WARN fixed, nothing new", t_fixed_silent),
    ("FIRES: sessions do not share a baseline", t_sessions_separate),
    ("gives way after MAX_BLOCKS (no wedge)", t_gives_way),
    ("resume re-baselines (its report was read aloud)", t_resume_rebaselines),
    ("start prunes baselines older than 30 d", t_prune),
]

if __name__ == "__main__":
    print("gate: %s" % GATE)
    for name, fn in CASES:
        case(name, fn)
    print("SUITE %s (%d case(s) failed)" % ("FAILED" if FAILS else "PASSED", FAILS))
    sys.exit(1 if FAILS else 0)
