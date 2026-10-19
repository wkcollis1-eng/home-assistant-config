"""Launcher probe: report what a hook script sees (argv, __name__, __file__, sys.path, stdin) and exit as asked.
argv[1]: exit code to return, or 'raise' to die with an uncaught exception."""

import json
import os
import sys

out = {
    "argv": sys.argv,
    "name": __name__,
    "file": os.path.normcase(os.path.abspath(__file__)),
    "path0": os.path.normcase(os.path.abspath(sys.path[0])),
    "cwd_on_path": any(
        x == "" or os.path.normcase(os.path.abspath(x)) == os.path.normcase(os.getcwd())
        for x in sys.path[1:]
    ),
    "path_tail": sys.path[1:],
    "stdin": sys.stdin.read(),
}
print(json.dumps(out))
if len(sys.argv) > 1 and sys.argv[1] == "raise":
    raise RuntimeError("probe")
if __name__ == "__main__":
    sys.exit(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
