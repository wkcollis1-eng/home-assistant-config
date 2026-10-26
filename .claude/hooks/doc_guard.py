"""PreToolUse hook: deny the first edit in an area whose rules live in a doc the
session has not read since its last compaction - once.

WHY THIS EXISTS. On 2026-10-25 three blocks moved out of CLAUDE.md into docs
that are read on a trigger (CHANGELOG 2026-10-25, "CLAUDE.md re-cut"). Two of the
triggers are paths, so a hook can check them instead of a session remembering:
  H:/dashboards/ (not lovelace/, which ha_guard.py walls)  -> docs/dashboards.md
  .claude/hooks/ and .claude/settings[.local].json, under ~ or H:
                                                 -> docs/claude-code-enforcement.md
"Read" means a Read or Grep whose path is the doc, or a Bash/PowerShell command
that runs a read verb on it (names_doc), AFTER the last compact_boundary record
in the transcript: a read before a compaction is no longer in context.

DESIGNED FOR NO HELP COMING - the unattended moment is a long task editing a
dashboard view or a hook with nobody there to approve anything:
- Deny ONCE per (session, area, compaction). The next edit in that area runs,
  so no task is ever stuck behind this guard.
- Fail open. Any error -> no output, exit 0 -> the edit runs. The settings entry
  uses hook_launcher, so a missing script also exits 0 (with a HOOK MISSING line).
- R8: never silent. deny / allow-read / allow-repeat / error all go to LOG_FILE,
  so whether it earns its place is scored from the log, not guessed.
"""

import json
import os
import re
import sys
import time

STATE_DIR = os.environ.get("DOC_GUARD_STATE") or os.path.join(
    os.path.expanduser("~"), ".claude", "hooks", ".state"
)
LOG_FILE = "doc_guard.log"
STATE_MAX_AGE = 7 * 86400  # per-session state files older than this are pruned

EDITORS = {"Edit", "Write", "NotebookEdit"}
READERS = {"Read", "Grep"}  # the doc is in a path field
SHELLS = {"Bash", "PowerShell"}  # the doc follows a read verb in the command
# A shell command is free text. On the second live run (2026-10-25) a heredoc that
# only QUOTED "docs/dashboards.md", in a checkpoint note, counted as a read and let
# the fire test through [M]. So: heredoc bodies are cut, and the doc must follow a
# read verb in the same pipeline segment.
READ_VERB = re.compile(
    r"(?:^|[\s;&|(])(?:cat|head|tail|sed|less|more|e?grep|rg|awk|cut|nl|"
    r"get-content|gc|type|select-string|sls)\s[^;&|\n]*"
)
# Claude Code writes the transcript as compact JSON; inside a string the quotes
# are escaped, so a transcript that merely quotes this marker cannot match it.
BOUNDARY = b'"subtype":"compact_boundary"'
HA_ROOTS = ("h:/", "//10.0.0.210/config/")

# area -> (needle searched for in reader inputs, doc named in the message).
# "docs/<name>", not the bare name: a Bash command is free text, and on the first
# live run the bare "dashboards.md" in a python one-liner counted as a read [M].
DOCS = {
    "dashboards": ("docs/dashboards.md", "H:/docs/dashboards.md"),
    "hooks": ("docs/claude-code-enforcement.md", "H:/docs/claude-code-enforcement.md"),
}


def norm(p):
    """Lower case, forward slashes, and git-bash /c/... -> c:/..."""
    p = str(p).replace("\\", "/").lower()
    m = re.match(r"^/([a-z])/", p)
    if m:
        p = m.group(1) + ":/" + p[3:]
    return p


def _claude_area(rel):
    if rel.startswith("hooks/") or re.match(r"settings(\.local)?\.json$", rel):
        return "hooks"
    return None


def area(path, home):
    """The guarded area a path is in, or None."""
    p = norm(path)
    for root in HA_ROOTS:
        if p.startswith(root):
            rel = p[len(root) :]
            if rel.startswith("dashboards/") and not rel.startswith(
                "dashboards/lovelace/"
            ):
                return "dashboards"
            if rel.startswith(".claude/"):
                return _claude_area(rel[len(".claude/") :])
            return None
    h = norm(home).rstrip("/") + "/.claude/"
    if p.startswith(h):
        return _claude_area(p[len(h) :])
    return None


def names_doc(block, needle):
    """True when a transcript content block is a tool call that reads `needle`."""
    if not (isinstance(block, dict) and block.get("type") == "tool_use"):
        return False
    ti = block.get("input") or {}
    if block.get("name") in READERS:
        hay = " ".join(str(ti.get(k) or "") for k in ("file_path", "path"))
        return needle in hay.replace("\\", "/").lower()
    if block.get("name") in SHELLS:
        cmd = str(ti.get("command") or "").split("<<", 1)[0]
        cmd = cmd.replace("\\", "/").lower()
        return any(needle in m.group(0) for m in READ_VERB.finditer(cmd))
    return False


def doc_read(transcript, needle):
    """(was_read, boundary_id). was_read: names_doc is true for some tool call
    after the last compact_boundary. boundary_id keys the deny-once state."""
    with open(transcript, "rb") as fh:
        lines = fh.read().split(b"\n")
    start, bid = 0, "start"
    for i in range(len(lines) - 1, -1, -1):
        if BOUNDARY in lines[i]:
            try:
                r = json.loads(lines[i])
            except ValueError:
                continue
            if r.get("type") == "system" and r.get("subtype") == "compact_boundary":
                start, bid = i + 1, str(r.get("uuid") or i)
                break
    # raw JSON escapes \ as \\, so the cheap prefilter looks for the name alone
    key = needle.rsplit("/", 1)[-1].encode()
    for line in lines[start:]:
        if key not in line.lower():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        content = (r.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        if any(names_doc(b, needle) for b in content):
            return True, bid
    return False, bid


def _state_path(state_dir, sid):
    return os.path.join(state_dir, "doc_guard_%s.json" % re.sub(r"[^\w.-]", "_", sid))


def _log(state_dir, sid, decision, label, path):
    line = "%s\t%s\t%s\t%s\t%s\n" % (
        time.strftime("%Y-%m-%dT%H:%M:%S"),
        sid[:8],
        decision,
        label,
        path,
    )
    with open(os.path.join(state_dir, LOG_FILE), "a", encoding="utf-8") as fh:
        fh.write(line)


def _prune(state_dir, now):
    for name in os.listdir(state_dir):
        if name.startswith("doc_guard_") and name.endswith(".json"):
            p = os.path.join(state_dir, name)
            if now - os.path.getmtime(p) > STATE_MAX_AGE:
                os.remove(p)


def decide(inp, state_dir=STATE_DIR, home=None):
    """Return the hook output dict for a deny, or None to let the edit run."""
    if inp.get("tool_name") not in EDITORS:
        return None
    ti = inp.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path")
    if not path:
        return None
    label = area(path, home or os.path.expanduser("~"))
    if not label:
        return None
    needle, doc = DOCS[label]

    sid = str(inp.get("session_id") or "unknown")
    os.makedirs(state_dir, exist_ok=True)
    try:
        was_read, bid = doc_read(inp.get("transcript_path"), needle)
        how = "deny"
    except (OSError, TypeError):  # no transcript: cannot tell, so ask once
        was_read, bid, how = False, "no-transcript", "deny-no-transcript"
    if was_read:
        _log(state_dir, sid, "allow-read", label, path)
        return None

    sp = _state_path(state_dir, sid)
    try:
        with open(sp, encoding="utf-8") as fh:
            seen = json.load(fh)
    except (OSError, ValueError):
        seen = []
    key = label + "@" + bid
    if key in seen:
        _log(state_dir, sid, "allow-repeat", label, path)
        return None

    seen.append(key)
    tmp = sp + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(seen, fh)
    os.replace(tmp, sp)
    _prune(state_dir, time.time())
    _log(state_dir, sid, how, label, path)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "DOC GUARD: %s is in the %s area, whose rules are in %s, and "
                "there has been no Read, Grep or shell read (cat, sed, grep...) of "
                "that doc since this session's last compaction. Grep -n it for the "
                "section you need and Read that part, then edit. If it is already "
                "in context, repeat the edit once and it will run." % (path, label, doc)
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
