"""PreToolUse hook: deny a Bash command that contains a doubled backslash.

WHY THIS EXISTS. The Bash tool turns every doubled backslash into a single one
before bash runs, in any quoting [M, 2026-10-11: two backslashes between a and b
reached bash as one, in single quotes, double quotes, a quoted heredoc body and
a python -c argument; bash itself keeps both in single quotes and heredocs]. The
transcript, and so this hook, still sees both, so the check can run here. All
main-thread transcripts to 2026-10-11 [M, C:/sandbox/token_replay/heredoc_cost.py]:
155 commands held a doubled backslash and 29 of them had a Python/shell error in
the result, against 107 of 5,319 with no backslash (Fisher p=2.5e-18). Commands
with lone backslashes only: 82 errors in 3,798 (p=0.65 against none), so a lone
backslash is safe. The worse failure is silent: on 2026-10-10 two stray CRs went
into a checkpoint with no error raised. A memory note did not stop it (two slips
on 2026-10-11 with the note loaded), so it is a hook.

DESIGNED FOR NO HELP COMING - the unattended moment is a session writing a
doubled backslash with nobody watching:
- Deny before bash runs, and name the way through: put the code in a file with
  the Write tool and run the file. No repeat-allow: the collapsed command is
  never the one that was typed, and a file always works, so no task is stuck.
- Lone backslashes pass untouched.
- Fail open. Any error -> no output, exit 0 -> the command runs. The settings
  entry uses the runpy launcher, so a missing script also exits 0.
- R8: every deny and every error is logged in LOG_FILE, so the guard is scored
  against the CHANGELOG prediction-ledger row, not assumed to work.
"""

import json
import os
import re
import sys
import time

DOUBLE = "\\" * 2  # two backslash characters

STATE_DIR = os.environ.get("BASH_GUARD_STATE") or os.path.join(
    os.path.expanduser("~"), ".claude", "hooks", ".state"
)
LOG_FILE = "bash_guard.log"

REASON = (
    "BASH GUARD: this command contains a doubled backslash. The Bash tool turns "
    "every doubled backslash into one before bash runs, in any quoting, so bash "
    "would not get what you typed. Put the code in a file with the Write tool and "
    "run the file (python file.py). A lone backslash is fine. Memory: "
    "bash-heredoc-body-with-redirect-operator."
)


def _log(state_dir, sid, decision, size, text):
    line = "%s\t%s\t%s\t%s\t%s\n" % (
        time.strftime("%Y-%m-%dT%H:%M:%S"),
        sid[:8],
        decision,
        size,
        re.sub(r"\s+", " ", text)[:100],
    )
    with open(os.path.join(state_dir, LOG_FILE), "a", encoding="utf-8") as fh:
        fh.write(line)


def decide(inp, state_dir=STATE_DIR):
    """Return the hook output dict for a deny, or None to let the command run."""
    if inp.get("tool_name") != "Bash":
        return None
    cmd = (inp.get("tool_input") or {}).get("command") or ""
    if DOUBLE not in cmd:
        return None
    sid = str(inp.get("session_id") or "unknown")
    os.makedirs(state_dir, exist_ok=True)
    _log(state_dir, sid, "deny", len(cmd), cmd)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": REASON,
        }
    }


def main(stdin=None, state_dir=None):
    state_dir = state_dir or STATE_DIR
    sid = "unknown"
    try:
        inp = json.load(stdin or sys.stdin)
        sid = str(inp.get("session_id") or "unknown")
        out = decide(inp, state_dir)
        if out:
            print(json.dumps(out))
    except Exception as exc:  # fail open, but never silently (R8)
        try:
            os.makedirs(state_dir, exist_ok=True)
            _log(state_dir, sid, "error", type(exc).__name__, str(exc)[:200])
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
