"""Mutation check for read_guard.py: each break must make test_read_guard.py fail."""

import subprocess
import shutil
import sys

src = open("read_guard.py", encoding="utf-8").read()
M = [
    ("<= threshold", "if size <= THRESHOLD:", "if size < THRESHOLD:"),
    ("no repeat-allow", "if key in seen:", "if False:"),
    ("no normcase", "os.path.normcase(os.path.abspath(path))", "path"),
    ("ignore offset", '("offset", "limit", "pages")', '("limit", "pages")'),
    ("limit 0 = whole", "ti.get(k) is not None", "ti.get(k)"),
    ("no SKIP_EXT", "in SKIP_EXT:", "in ():"),
    (
        "one state for all sessions",
        r'read_guard_%s.json" % re.sub(r"[^\w.-]", "_", sid)',
        'read_guard_%s.json" % "all"',
    ),
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
    ("missing file denies", "return None  # missing", "size = 10**9  # missing"),
]
shutil.copy("read_guard.py", "read_guard.orig")
caught = 0
try:
    for name, a, b in M:
        if a not in src:
            print("NOT APPLIED:", name)
            continue
        open("read_guard.py", "w", encoding="utf-8").write(src.replace(a, b, 1))
        r = subprocess.run(
            [sys.executable, "test_read_guard.py"], capture_output=True, text=True
        )
        ok = r.returncode != 0
        caught += ok
        print(("CAUGHT  " if ok else "SURVIVED"), name)
finally:
    shutil.copy("read_guard.orig", "read_guard.py")
print(f"{caught}/{len(M)} caught")
