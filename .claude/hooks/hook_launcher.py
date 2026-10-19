"""The one hook launcher (2026-10-18). Builds the `python -c` argv for a hook script and rewrites settings.json.

Behaviour of the launched code:
  script present -> run it as __main__ with sys.argv[0] = the script and sys.path[0] = its directory, the same as
                    `python <script>`; the '' (cwd) entry that `-c` adds is dropped, so a stray json.py in the cwd
                    cannot shadow an import. Exit code, stdout and stderr are the script's own.
  script missing -> exit 0 and print a JSON systemMessage naming the file and the fix (R8: announce the skip),
                    instead of python's exit 2, which blocks every prompt on UserPromptSubmit and every stop on Stop.

Usage: python hook_launcher.py <settings.json in> <settings.json out>   (prints a per-entry report; writes only `out`)
"""

import json
import re
import sys

# sys.path is cleaned BEFORE the other imports: the first version imported json first, and test_hook_launcher.py's cwd
# json.py shadowed it (2026-10-18, caught by the probe before deploy).
CODE = (
    # no sys.argv[0]=p (the old launcher had it): runpy.run_path sets argv[0] itself via _ModifiedArgv0
    # [S: C:\Python314\Lib\runpy.py:288,302]; the test's mutant without it was equivalent, 2026-10-18.
    "import sys;sys.path[:]=[x for x in sys.path if x];import json,os,runpy;p='{p}';"
    "sys.path.insert(0,os.path.dirname(p));"
    "runpy.run_path(p,run_name='__main__') if os.path.exists(p) else "
    "print(json.dumps({{'systemMessage':'HOOK MISSING: '+p+' - copy it back from H:/.claude/hooks, or remove "
    "its entries from ~/.claude/settings.json (H:/docs/claude-code-enforcement.md)'}}))"
)


def launch_args(script, modes):
    assert "'" not in script and "\\" not in script, script
    return ["-c", CODE.format(p=script)] + list(modes)


def script_of(args):
    """(script path, mode args) from either the bare form or the old launcher form."""
    if args and args[0] == "-c":
        return re.search(r"p='([^']+)'", args[1]).group(1), args[2:]
    return args[0], args[1:]


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    text = open(src, encoding="utf-8", newline="").read()
    d = json.loads(text)
    assert json.dumps(d, indent=2, ensure_ascii=False) + "\n" == text, (
        "settings.json does not round-trip"
    )
    n = 0
    for ev, groups in d["hooks"].items():
        for g in groups:
            for h in g["hooks"]:
                if h.get("command") != "python":
                    continue
                script, modes = script_of(h["args"])
                new = launch_args(script, modes)
                print(
                    f"{ev:17s} [{g.get('matcher', '*')}] {script.rsplit('/', 1)[-1]} {modes} "
                    f"{'(old launcher)' if h['args'][0] == '-c' else '(bare)'} -> launcher"
                )
                h["args"] = new
                n += 1
    out = json.dumps(d, indent=2, ensure_ascii=False) + "\n"
    open(dst, "w", encoding="utf-8", newline="").write(out)
    print(f"{n} entries rewritten -> {dst}")
