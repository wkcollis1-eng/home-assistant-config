"""Mutation check for doc_guard.py: each break must make test_doc_guard.py fail.

Mutates a COPY in a temp dir, never the file beside it, so an interrupted run
cannot leave a broken hook where the launcher or a deploy will pick it up.
Run: python mutate_doc_guard.py -> "N/N caught".
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "doc_guard.py"), encoding="utf-8").read()
M = [
    (
        "read before compaction counts",
        'start, bid = i + 1, str(r.get("uuid") or i)',
        'start, bid = 0, str(r.get("uuid") or i)',
    ),
    (
        "boundary not confirmed",
        'if r.get("type") == "system" and r.get("subtype") == "compact_boundary":',
        "if True:",
    ),
    ("any tool counts as a read", 'if block.get("name") in READERS:', "if True:"),
    (
        "any record naming the doc counts",
        "if any(names_doc(b, needle) for b in content):",
        "if True:",
    ),
    # names_doc's tool_use type check is an equivalent mutant: a block that is
    # not a tool_use has no "name", so the READERS/SHELLS tests already reject it
    (
        "Grep pattern counts",
        'for k in ("file_path", "path")',
        'for k in ("file_path", "path", "pattern")',
    ),
    ("no backslash normalisation", r'hay.replace("\\", "/").lower()', "hay.lower()"),
    (
        "shell: no backslash normalisation",
        r'cmd = cmd.replace("\\", "/").lower()',
        "cmd = cmd.lower()",
    ),
    ("shell: heredoc body counts", '.split("<<", 1)[0]', ""),
    (
        "shell: no read verb needed",
        "return any(needle in m.group(0) for m in READ_VERB.finditer(cmd))",
        "return needle in cmd",
    ),
    ("shell: verb reaches past ;", r"\s[^;&|\n]*", r"\s[^&|\n]*"),
    ("shell: verb reaches past a newline", r"\s[^;&|\n]*", r"\s[^;&|]*"),
    ("PowerShell not a shell", 'SHELLS = {"Bash", "PowerShell"}', 'SHELLS = {"Bash"}'),
    (
        "bare doc name counts",
        '("docs/dashboards.md", "H:/docs/dashboards.md")',
        '("dashboards.md", "H:/docs/dashboards.md")',
    ),
    ("no deny-once", "if key in seen:", "if False:"),
    ("deny-once not re-armed by compaction", 'key = label + "@" + bid', "key = label"),
    (
        "one state for all sessions",
        r'doc_guard_%s.json" % re.sub(r"[^\w.-]", "_", sid)',
        'doc_guard_%s.json" % "all"',
    ),
    (
        "lovelace not left to ha_guard",
        '"dashboards/lovelace/"\n',
        '"never-matches/"\n',
    ),
    (
        "settings.local.json unguarded",
        r're.match(r"settings(\.local)?\.json$", rel)',
        'rel == "settings.json"',
    ),
    (
        "settings.json.bak guarded",
        r'r"settings(\.local)?\.json$"',
        r'r"settings(\.local)?\.json"',
    ),
    ("no git-bash /c/ form", "    if m:\n", "    if False:\n"),
    (
        "other projects' .claude guarded",
        "if p.startswith(h):",
        'if "/.claude/" in p:\n        h = p[:p.index("/.claude/") + 9]\n    if True:',
    ),
    (
        "missing transcript allows",
        'was_read, bid, how = False, "no-transcript"',
        'was_read, bid, how = True, "no-transcript"',
    ),
    ("Read tool policed", 'if inp.get("tool_name") not in EDITORS:', "if False:"),
    (
        "main not fail-open",
        "except Exception as exc:  # fail open",
        "except ValueError as exc:  # fail open",
    ),
    (
        "no error log",
        '_log(state_dir, sid, "error"',
        'None and _log(state_dir, sid, "error"',
    ),
    ("no prune", "_prune(state_dir, time.time())", "pass"),
    (
        "prune hits other hooks",
        'name.startswith("doc_guard_")',
        'name.endswith(".json")',
    ),
]
tmp = tempfile.mkdtemp(prefix="doc_guard_mut_")
shutil.copy(os.path.join(HERE, "test_doc_guard.py"), tmp)
caught = 0
for name, a, b in M:
    if src.count(a) != 1:
        print("NOT APPLIED (%d matches):" % src.count(a), name)
        continue
    with open(os.path.join(tmp, "doc_guard.py"), "w", encoding="utf-8") as fh:
        fh.write(src.replace(a, b, 1))
    # -B: no .pyc. Its check is source mtime (whole seconds) + size, so two mutants
    # of equal length written in one second ran the FIRST one's bytecode - seen
    # 2026-10-25 as the shell-backslash mutant "caught" by the Read check [M]
    r = subprocess.run(
        [sys.executable, "-B", os.path.join(tmp, "test_doc_guard.py")],
        capture_output=True,
        text=True,
    )
    ok = r.returncode != 0
    caught += ok
    # the first failing check, so a mutant "caught" only by a crash shows as one
    first = (r.stdout.splitlines() or r.stderr.splitlines()[-1:] or [""])[0]
    print(("CAUGHT  " if ok else "SURVIVED"), name, "|", first[:70])
shutil.rmtree(tmp, ignore_errors=True)
print("%d/%d caught" % (caught, len(M)))
sys.exit(0 if caught == len(M) else 1)
