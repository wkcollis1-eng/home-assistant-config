#!/usr/bin/env python
"""Fire/silent tests for ha_audit_gate.memory_index_size() (CLAUDE.md R2/R7).

Every cap is tested on both sides of its line, then the gate runs end to end as
Claude Code runs it (sessionstart argv, JSON on stdin) against a fake ha_audit.py.
Touches nothing outside a temp dir; the live MEMORY.md is only read (argv[2] or
the default path) and copied. Optional argv[1]: the gate file to test.

    python test_memory_index_size.py [path/to/ha_audit_gate.py] [path/to/MEMORY.md]
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = (
    os.path.abspath(sys.argv[1])
    if len(sys.argv) > 1
    else os.path.join(HERE, "ha_audit_gate.py")
)
LIVE = (
    sys.argv[2]
    if len(sys.argv) > 2
    else os.path.join(
        os.path.expanduser("~"),
        ".claude",
        "projects",
        "C--Users-wkcol",
        "memory",
        "MEMORY.md",
    )
)
TMP = tempfile.mkdtemp(prefix="memidx_")
FAILS = 0

FAKE = r"""
import io, json, os, sys
a = sys.argv[1:]
opt = lambda k: a[a.index(k) + 1] if k in a else None
s = "0 FAIL, 1 WARN, 0 INFO across 3 pipelines"
w = "WARN  open-question            fake standing WARN"
if opt("--log"):
    with io.open(opt("--log"), "a", encoding="utf-8") as fh:
        fh.write("\n===== 2026-10-26T12:00:00 =====\n" + w + "\n\n" + s + "\n")
b = opt("--baseline")
if b:
    json.dump({"findings": [w]}, open(b, "w"))
    print("BASELINE WRITTEN  %s  (1 finding(s) recorded)" % b)
print(s)
"""


def check(name, got, has=(), lacks=(), silent=False):
    global FAILS
    ok = (
        (got == "")
        if silent
        else (
            got != ""
            and all(w in got for w in has)
            and not any(w in got for w in lacks)
        )
    )
    FAILS += not ok
    print(
        "  %s  %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else ": got %r" % got)
    )


def load(memory_env=None):
    """The gate as a fresh module, compiled from source on every call.

    Not importlib's spec_from_file_location (R13, 2026-10-26): its .pyc cache is
    keyed on source mtime + size, and mutate_memory_index.py rewrites one mutant
    file within the same second at the same size, so mutant 2 ran mutant 1's
    bytecode and its "CAUGHT" was mutant 1's result [M, n=1].
    """
    if memory_env:
        os.environ["HA_GATE_MEMORY"] = memory_env
    mod = types.ModuleType("gate_under_test")
    mod.__file__ = GATE
    with open(GATE, encoding="utf-8") as fh:
        exec(compile(fh.read(), GATE, "exec"), mod.__dict__)
    os.environ.pop("HA_GATE_MEMORY", None)
    return mod


def mem(name, rows=None, raw=None):
    """A MEMORY.md from rows (joined with LF, final newline) or exact bytes."""
    p = os.path.join(TMP, name)
    with open(p, "wb") as fh:
        fh.write(raw if raw is not None else ("\n".join(rows) + "\n").encode("utf-8"))
    return p


def sized(name, total, width=60):
    """Short lines, exactly `total` bytes, under 180 lines while total < 10,800."""
    rows, left = [], total
    while left > width + 1:
        rows.append("x" * width)
        left -= width + 1
    rows.append("y" * (left - 1))  # its own "\n" makes up the rest
    p = mem(name, rows)
    assert os.path.getsize(p) == total, (name, os.path.getsize(p))
    return p


g = load()
f = g.memory_index_size
print("memory_index_size() against %s" % GATE)
print("fires")
check(
    "171-char line -> named with its length",
    f(mem("l171.md", ["# idx", "a" * 171, "b" * 20])),
    has=("OVER BUDGET", "L2 (171)", "memtrim"),
    lacks=("L1 ", "L3 ", "LOADER LIMIT", "merge or delete"),
)
check(
    "6,501 B of short lines -> over the total budget",
    f(sized("b6501.md", 6501)),
    has=("6,501 B (budget 6,500)", "chars: none", "merge or delete"),
    lacks=("LOADER LIMIT", "memtrim"),
)
check(
    "180 short lines (well under 6,500 B) -> loader-limit wording",
    f(mem("n180.md", ["- x"] * 180)),
    has=("LOADER LIMIT", "180 lines", "silently stop loading", "merge or delete"),
)
rows = ["z" * 169] * 132 + ["q" * 59]  # 132 x 170 B + 60 B = 22,500 B, 133 lines
check(
    "22,500 B in 133 lines -> loader-limit wording",
    f(mem("b22500.md", rows)),
    has=("LOADER LIMIT", "22,500 B"),
)
check(
    "171 chars + CRLF -> fires (the CR is not a char of the line)",
    f(mem("crlf171.md", raw=b"# idx\r\n" + b"c" * 171 + b"\r\n")),
    has=("L2 (171)",),
)
check(
    "17 long lines -> 15 named, the rest counted",
    f(mem("many.md", ["d" * 175] * 17)),
    has=("L15 (175)", "(+2 more)"),
    lacks=("L16 ",),
)
print("fires but not the hard line")
check(
    "22,499 B in 133 lines -> over budget, NOT loader-limit",
    f(mem("b22499.md", ["z" * 169] * 132 + ["q" * 58])),
    has=("22,499 B",),
    lacks=("LOADER LIMIT",),
)
print("silent")
check("170-char line", f(mem("l170.md", ["# idx", "a" * 170])), silent=True)
check("exactly 6,500 B", f(sized("b6500.md", 6500)), silent=True)
check("179 short lines", f(mem("n179.md", ["- x"] * 179)), silent=True)
check(
    "170 chars + CRLF",
    f(mem("crlf170.md", raw=b"# idx\r\n" + b"c" * 170 + b"\r\n")),
    silent=True,
)
check(
    "170 x 3-byte char (510 B) -> chars counted, not bytes",
    f(mem("utf8.md", ["—" * 170])),
    silent=True,
)
check("no final newline, 170 chars", f(mem("nofinal.md", raw=b"a" * 170)), silent=True)
live = os.path.join(TMP, "live_copy.md")
shutil.copy(LIVE, live)
check("copy of the live MEMORY.md (%d B)" % os.path.getsize(live), f(live), silent=True)
print("did not run (R8)")
check(
    "missing file -> DID NOT RUN, names the path",
    f(os.path.join(TMP, "nope", "MEMORY.md")),
    has=("MEMORY INDEX CHECK DID NOT RUN", "nope"),
)
check(
    "a directory, not a file -> DID NOT RUN",
    f(TMP),
    has=("MEMORY INDEX CHECK DID NOT RUN",),
)

print("path")
g = load(memory_env=os.path.join(TMP, "fallback.md"))
g._INPUT = {"transcript_path": os.path.join(TMP, "proj", "abc.jsonl")}
got = g.memory_index_path()
check(
    "transcript_path -> <its dir>/memory/MEMORY.md",
    "" if got == os.path.join(TMP, "proj", "memory", "MEMORY.md") else got,
    silent=True,
)
g._INPUT = {"session_id": "x"}
got = g.memory_index_path()
check(
    "no transcript_path -> the fallback path",
    "" if got == os.path.join(TMP, "fallback.md") else got,
    silent=True,
)

print("end to end (sessionstart subprocess, fake audit)")
fake = os.path.join(TMP, "fake_audit.py")
with open(fake, "w") as fh:
    fh.write(FAKE)
over = ["- [m](m.md) - " + "w" * 180]
clean = mem("clean_fallback.md", ["- [m](m.md) - fine"])


def e2e(sid, memory_rows=None, transcript=True, fallback=clean):
    proj = os.path.join(TMP, "e2e_" + sid)
    os.makedirs(proj)
    if memory_rows is not None:
        os.makedirs(os.path.join(proj, "memory"))
        mem(os.path.join(proj, "memory", "MEMORY.md"), memory_rows)
    stdin = {"session_id": sid, "hook_event_name": "SessionStart", "source": "startup"}
    if transcript:
        stdin["transcript_path"] = os.path.join(proj, sid + ".jsonl")
    state = os.path.join(TMP, "state_" + sid)
    env = dict(
        os.environ,
        HA_GATE_AUDIT=fake,
        HA_GATE_CONFIG=os.path.join(TMP, "cfg").replace("\\", "/") + "/",
        HA_GATE_STATE=state,
        HA_GATE_STAMP=os.path.join(TMP, "stamp_" + sid),
        HA_GATE_MEMORY=fallback,
    )
    cp = subprocess.run(
        [sys.executable, GATE, "sessionstart"],
        input=json.dumps(stdin),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    base = os.path.exists(os.path.join(state, "audit_baseline_%s.json" % sid))
    try:
        ctx = json.loads(cp.stdout)["hookSpecificOutput"]["additionalContext"]
    except (ValueError, KeyError, TypeError):
        ctx = "UNPARSEABLE rc=%s out=%r err=%r" % (
            cp.returncode,
            cp.stdout,
            cp.stderr[-300:],
        )
    return ctx, base, cp.returncode


ctx, base, rc = e2e("e1", over)
check(
    "over budget -> audit verdict AND the memory line, exit 0",
    ctx if rc == 0 else "rc=%d" % rc,
    has=("HA CONFIG AUDIT", "0 FAIL, 1 WARN", "MEMORY INDEX OVER BUDGET", "L1 ("),
    lacks=("NO STOP-GATE BASELINE", "DID NOT RUN"),
)
check(
    "session_id still read from stdin -> this session's baseline written",
    "" if base else "no audit_baseline_e1.json",
    silent=True,
)
ctx, base, rc = e2e("e2", ["- [m](m.md) - fine"])
check(
    "within budget -> audit verdict, no memory line",
    ctx,
    has=("HA CONFIG AUDIT", "0 FAIL, 1 WARN"),
    lacks=("MEMORY INDEX",),
)
ctx, base, rc = e2e("e3", None)
check(
    "no memory dir beside the transcript -> DID NOT RUN line",
    ctx,
    has=("HA CONFIG AUDIT", "MEMORY INDEX CHECK DID NOT RUN"),
)
ctx, base, rc = e2e(
    "e4", None, transcript=False, fallback=mem("over_fallback.md", over)
)
check(
    "no transcript_path -> the fallback file is checked",
    ctx,
    has=("MEMORY INDEX OVER BUDGET",),
)

shutil.rmtree(TMP, ignore_errors=True)
print("FAILS: %d" % FAILS)
sys.exit(1 if FAILS else 0)
