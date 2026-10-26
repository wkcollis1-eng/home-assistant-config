"""Each mutant of ha_audit_gate.py must make test_memory_index_size.py FAIL (R7)."""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "ha_audit_gate.py"), encoding="utf-8").read()
MUTANTS = [
    ("line cap > -> >=", "> MEM_LINE_MAX\n", ">= MEM_LINE_MAX\n"),
    ("total cap > -> >=", "or size > MEM_TOTAL_MAX):", "or size >= MEM_TOTAL_MAX):"),
    ("hard lines >= -> >", "n >= MEM_HARD_LINES", "n > MEM_HARD_LINES"),
    ("hard bytes >= -> >", "size >= MEM_HARD_BYTES", "size > MEM_HARD_BYTES"),
    ("total cap off by one", "MEM_TOTAL_MAX = 6500", "MEM_TOTAL_MAX = 6501"),
    (
        "CR counted as a char",
        'if len(r.rstrip("\\r")) > MEM_LINE_MAX',
        "if len(r) > MEM_LINE_MAX",
    ),
    (
        "bytes counted, not chars",
        'raw.decode("utf-8-sig", errors="replace")',
        'raw.decode("latin-1")',
    ),
    ("final newline counted as a line", "rows.pop()  # the final", "pass  # the final"),
    ("transcript_path ignored", "    if tp:\n", "    if False:\n"),
    ("stdin re-read, not kept", "if _INPUT is None:", "if True:"),
    (
        "failure silent",
        "    except Exception as e:  # fail open, never silently (R8)\n        return (",
        '    except Exception as e:  # fail open, never silently (R8)\n        return "" and (',
    ),
    ("never appended", " + memory_index_size(),", ","),
    ("list not capped", "long[:15]", "long"),
]
bad = 0
for i, (name, old, new) in enumerate(MUTANTS):
    assert SRC.count(old) == 1, (name, SRC.count(old))
    # One file per mutant: see load() in the test for the stale-.pyc trap.
    p = os.path.join(HERE, "mutant_memidx_%d.py" % i)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(SRC.replace(old, new))
    out = subprocess.run(
        [sys.executable, os.path.join(HERE, "test_memory_index_size.py"), p],
        stdin=subprocess.DEVNULL,  # a mutant that re-reads stdin must not hang the run
        capture_output=True,
        text=True,
        timeout=600,
    ).stdout
    os.remove(p)
    caught = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("FAIL ")]
    bad += not caught
    print(
        "%s  %s: %d failing%s"
        % (
            "CAUGHT" if caught else "MISSED",
            name,
            len(caught),
            "  e.g. " + caught[0][:80] if caught else "",
        )
    )
print("MUTATIONS MISSED:", bad)
