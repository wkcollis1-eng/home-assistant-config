"""R7 for the tests themselves: each mutation must make test_hygiene.py report FAILS > 0."""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "context_hygiene.py"), encoding="utf-8").read()
MUT = [
    ("line at 79%", "NUDGE_AT = 0.80", "NUDGE_AT = 0.79"),
    ("no subagent skip", 'if inp.get("agent_id"):', "if False:"),
    (
        "boundary-written branch never taken",
        "if bnd and not any(t > bnd[-1][0] for t, _ in resp):",
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
        "            if is_boundary(r):\n                md",
        '            if b"compact_boundary" in line:\n                md',
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
