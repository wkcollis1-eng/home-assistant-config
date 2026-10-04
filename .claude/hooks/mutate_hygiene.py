"""R7 for the tests themselves: each mutation must make test_hygiene.py report FAILS > 0."""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "context_hygiene.py"), encoding="utf-8").read()
MUT = [
    ("due line 1K late", "DUE_BEFORE = 40_000", "DUE_BEFORE = 39_000"),
    ("due line 1K early", "DUE_BEFORE = 40_000", "DUE_BEFORE = 41_000"),
    ("gate line 1K late", "GATE_BEFORE = 20_000", "GATE_BEFORE = 19_000"),
    ("gate line 1K early", "GATE_BEFORE = 20_000", "GATE_BEFORE = 21_000"),
    ("trigger gap 1K short", "TRIGGER_GAP = 34_000", "TRIGGER_GAP = 33_000"),
    ("ceiling 1K late", "CEILING_AFTER = 90_000", "CEILING_AFTER = 91_000"),
    (
        "gate lets any file through",
        "tool in CKPT_TOOLS and same_file(",
        "tool in CKPT_TOOLS or same_file(",
    ),
    (
        "path compared without normcase",
        "os.path.normcase(os.path.abspath(a))",
        "os.path.abspath(a)",
    ),
    ("gate never denies", 'if not d or d["ctx"] < d["gate"]:', "if True:"),
    ("deny not logged", 'gate_log(inp, "pretooluse-deny", d)', "pass"),
    (
        "stop ignores stop_hook_active",
        'def on_stop(inp):\n    if inp.get("stop_hook_active"):',
        "def on_stop(inp):\n    if False:",
    ),
    (
        "stop never blocks",
        '    d = checkpoint_due(inp)\n    if d:\n        gate_log(inp, "stop-block", d)',
        '    d = None\n    if d:\n        gate_log(inp, "stop-block", d)',
    ),
    ("manual /compact blocked", 'if inp.get("trigger") != "auto":', "if False:"),
    ("no ceiling", 'if d["ctx"] >= d["ceiling"]:', "if False:"),
    (
        "gave-way WARN dropped",
        'if status != "fresh" and win and seg and seg[-1][1] >= lines(win)[2]:',
        "if False:",
    ),
    ("no subagent skip", 'if inp.get("agent_id"):', "if False:"),
    (
        "boundary-written branch never taken",
        "if bnd and not any(t > bnd[-1] for t, _ in resp):",
        "if False:",
    ),
    (
        "dip does not restart the run",
        "        if n < thr:\n            break",
        "        if n < thr:\n            continue",
    ),
    (
        "audit found by substring",
        's.startswith("HA CONFIG AUDIT")',
        '"HA CONFIG AUDIT" in s',
    ),
    (
        "env var ignored",
        'v = os.environ.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW")',
        "v = None",
    ),
    ("no truncation", "body[:CKPT_MAX]", "body"),
    (
        "boundary found by substring",
        "            if is_boundary(r):\n                bnd.append",
        '            if b"compact_boundary" in line:\n                bnd.append',
    ),
    ("responses before the newest compaction kept", "if t > floor:", "if True:"),
    (
        "segment in file order",
        "out = set()\n    for r in recs:\n        n = ctx_of(r)\n        if n is not None:\n"
        '            t = epoch(r["timestamp"])\n            if t > floor:\n'
        "                out.add((t, n))\n    return sorted(out)",
        "out = []\n    for r in recs:\n        n = ctx_of(r)\n        if n is not None:\n"
        '            t = epoch(r["timestamp"])\n            if t > floor:\n'
        "                out.append((t, n))\n    return out",
    ),
    (
        "newest compaction by file order",
        'floor = max((epoch(r["timestamp"]) for r in recs if is_boundary(r)), default=0.0)',
        'floor = ([epoch(r["timestamp"]) for r in recs if is_boundary(r)] or [0.0])[-1]',
    ),
    (
        "scan not sorted",
        "return sorted(set(bnd)), sorted(set(resp)), sorted(set(aud))",
        "return bnd, resp, aud",
    ),
    (
        "no 4 MB fallback",
        " or last_context(\n        tail_records(path)\n    )",
        "",
    ),
    ("handler failure silent", 'if mode == "sessionstart":  # R8', "if False:  # R8"),
]
bad = 0
for name, old, new in MUT:
    assert SRC.count(old) == 1, (name, SRC.count(old))
    p = os.path.join(HERE, "mutant.py")
    open(p, "w", encoding="utf-8").write(SRC.replace(old, new))
    out = subprocess.run(
        [sys.executable, os.path.join(HERE, "test_hygiene.py")],
        capture_output=True,
        text=True,
        env=dict(os.environ, HYGIENE_HOOK=p),
        timeout=600,
    ).stdout
    caught = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("FAIL ")]
    bad += not caught
    print(
        f"{'CAUGHT' if caught else 'MISSED'}  {name}: {len(caught)} failing"
        + (f"  e.g. {caught[0][:90]}" if caught else "")
    )
os.remove(os.path.join(HERE, "mutant.py"))
print("MUTATIONS MISSED:", bad)
