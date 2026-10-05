"""PreToolUse hook: deny a whole-file Read of a large text file, once per file.

WHY THIS EXISTS. 14 days of transcripts (2026-09-20 to 10-04) [M]: 64 whole-file
Reads brought 698,007 chars into context, and the 9 over 20,000 chars were
363,464 of them - mostly design docs re-read in full. Every char that enters is
re-sent on every later call until the next compaction. Anthropic's cost guide
(code.claude.com/docs/en/costs, "Offload processing to hooks and skills") puts
the filter in a hook so it does not depend on remembering a rule. The nudge is:
Grep for the part you need, then Read with offset/limit.

DESIGNED FOR NO HELP COMING - the unattended moment is a long task that really
does need the whole file, with nobody there to approve anything:
- Deny ONCE per (session, file). The same Read repeated runs, so no task is
  ever stuck behind this guard.
- Fail open. Any error -> no output, exit 0 -> the Read runs. A cost guard must
  never block work. The settings entry uses the runpy launcher, so a missing
  script also exits 0.
- R8: an error is never silent. It is logged as "error" in LOG_FILE, beside
  every deny and every repeat-allow, so the threshold is scored, not guessed.
"""

import json
import os
import re
import sys
import time

# Bytes on disk. [D] from the 14-day distribution above: 9 whole reads over
# 20,000 chars. Tune from read_guard.log, not by feel.
THRESHOLD = 20000

# Read renders these as images or pages, not as text; size says nothing about
# the context they cost, and PDFs over 10 pages already need `pages`.
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".pdf", ".ipynb"}

STATE_DIR = os.environ.get("READ_GUARD_STATE") or os.path.join(
    os.path.expanduser("~"), ".claude", "hooks", ".state"
)
LOG_FILE = "read_guard.log"
STATE_MAX_AGE = 7 * 86400  # per-session state files older than this are pruned


def _key(path):
    return os.path.normcase(os.path.abspath(path))


def _state_path(state_dir, sid):
    return os.path.join(state_dir, "read_guard_%s.json" % re.sub(r"[^\w.-]", "_", sid))


def _log(state_dir, sid, decision, size, path):
    line = "%s\t%s\t%s\t%s\t%s\n" % (
        time.strftime("%Y-%m-%dT%H:%M:%S"),
        sid[:8],
        decision,
        size,
        path,
    )
    with open(os.path.join(state_dir, LOG_FILE), "a", encoding="utf-8") as fh:
        fh.write(line)


def _prune(state_dir, now):
    for name in os.listdir(state_dir):
        if name.startswith("read_guard_") and name.endswith(".json"):
            p = os.path.join(state_dir, name)
            if now - os.path.getmtime(p) > STATE_MAX_AGE:
                os.remove(p)


def decide(inp, state_dir=STATE_DIR):
    """Return the hook output dict for a deny, or None to let the Read run."""
    if inp.get("tool_name") != "Read":
        return None
    ti = inp.get("tool_input") or {}
    path = ti.get("file_path")
    if not path:
        return None
    if any(ti.get(k) is not None for k in ("offset", "limit", "pages")):
        return None
    if os.path.splitext(path)[1].lower() in SKIP_EXT:
        return None
    try:
        size = os.path.getsize(path)
    except OSError:
        return None  # missing or unreadable: let Read report it
    if size <= THRESHOLD:
        return None

    sid = str(inp.get("session_id") or "unknown")
    os.makedirs(state_dir, exist_ok=True)
    sp = _state_path(state_dir, sid)
    try:
        with open(sp, encoding="utf-8") as fh:
            seen = json.load(fh)
    except (OSError, ValueError):
        seen = []
    key = _key(path)
    if key in seen:
        _log(state_dir, sid, "allow-repeat", size, path)
        return None

    seen.append(key)
    tmp = sp + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(seen, fh)
    os.replace(tmp, sp)
    _prune(state_dir, time.time())
    _log(state_dir, sid, "deny", size, path)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "READ GUARD: %s is %d KB and this Read has no offset/limit. Grep -n "
                "for the part you need (yq for one YAML key), then Read with "
                "offset/limit. If you need the whole file, repeat this exact Read "
                "once and it will run." % (path, size // 1000)
            ),
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
