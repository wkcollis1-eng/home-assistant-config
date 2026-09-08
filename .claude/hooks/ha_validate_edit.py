#!/usr/bin/env python
"""PostToolUse: validate the file that was just edited, next to the edit.

WHY. Until now the first thing that looked at a YAML error was the Stop gate,
at the end of the turn - by which point several more edits are stacked on top
of it and the fix means unpicking them. Cost measured 2026-08-25: the audit was
18.0s (n=5) because config_files() is consulted at 13 sites with no parse
caching, which is why a per-edit gate was never affordable. Memoizing load()
and text() took it to 3.85s, and validate_ha.py on a single file is faster
still - so the error can now land beside the edit that caused it.

PostToolUse runs AFTER the tool, so this cannot prevent the write. Exit 2 puts
stderr in front of Claude anyway, which is the point: the feedback arrives one
step later instead of ten.

Deliberately narrow. It validates ONE file, the one just written, and only
under the HA config root - never the whole tree, or this stops being cheap and
starts being skipped.
"""
import json
import os
import subprocess
import sys

CONFIG = os.environ.get("HA_GATE_CONFIG", "H:/").rstrip("/")
VALIDATOR = CONFIG + "/scripts/validate_ha.py"


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0

    path = ((payload.get("tool_input") or {}).get("file_path") or "").replace("\\", "/")
    if not path:
        return 0

    root = CONFIG.rstrip("/").lower()
    if not path.lower().startswith(root):
        return 0                      # not the HA config; not our business

    if path.lower().endswith((".yaml", ".yml")):
        if not os.path.exists(VALIDATOR):
            return 0
        argv = [sys.executable, VALIDATOR, "--strict", path]
    elif path.lower().endswith(".py"):
        argv = [sys.executable, "-m", "py_compile", path]
    else:
        return 0

    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=120,
                           env=dict(os.environ, HA_CONFIG=CONFIG))
    except (OSError, subprocess.SubprocessError) as exc:
        return 0                      # a broken validator must not block work

    if r.returncode == 0:
        return 0

    out = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    sys.stderr.write(
        "validate_ha --strict FAILED on the file just edited: %s\n%s\n"
        "Fix it now, while this is the only change in flight.\n"
        % (os.path.basename(path), "\n".join(out[-20:])))
    return 2                          # exit 2 = show stderr to Claude


if __name__ == "__main__":
    sys.exit(main())
