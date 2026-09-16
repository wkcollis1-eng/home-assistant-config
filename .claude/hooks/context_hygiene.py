#!/usr/bin/env python
"""Say /clear at the two moments it saves the most. Only Bill can run it.

WHY THIS EXISTS. Measured 2026-09-16 over 7,685 API calls (Aug 21 - Sep 16):
median context 330K tokens, 83% of calls over 150K. Re-reading the
conversation was ~72% of token cost; thinking was ~7%. Sessions ran 200-920
calls across days. The lever is session length, /clear is a user command, and
remembering to suggest it is exactly the kind of compliance that belongs to
the harness rather than the model.

  userpromptsubmit  Idle >= IDLE_MIN since the last response AND context >=
                    MIN_CONTEXT: block the prompt ONCE. The prompt cache has
                    expired (1 h on a subscription), so sending it re-caches
                    the whole context. Send it again to continue anyway.
  stop              The turn ran a successful `git push` AND context >=
                    MIN_CONTEXT: print a one-line /clear suggestion. Never
                    blocks - a push is where Bill's tasks end.

FAILS OPEN. Any error -> exit 0, no output. This is a cost nudge, not a safety
gate; it must never be the reason a prompt cannot be sent.

LIVE TEST. Create .state/arm_test next to this file: the next prompt is
treated as idle, blocks once, and the file is deleted. Send again -> allowed.
"""
import json
import os
import re
import sys
import time
from datetime import datetime

IDLE_MIN = 60
MIN_CONTEXT = 150_000
TAIL_BYTES = 4 << 20
STATE_DIR = os.environ.get("CONTEXT_HYGIENE_STATE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".state")
STATE = os.path.join(STATE_DIR, "context_hygiene.json")
ARM = os.path.join(STATE_DIR, "arm_test")
PUSH = re.compile(r"\bgit\b[^\n|;&]*\bpush\b")


def tail_records(path):
    """Transcript records from the last TAIL_BYTES, oldest first."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - TAIL_BYTES))
        lines = f.read().split(b"\n")
    if size > TAIL_BYTES:
        lines = lines[1:]  # first line is partial
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def epoch(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def last_context(recs):
    """(tokens, epoch) of the newest main-thread response, or None.

    None also when a compaction follows it: the old size no longer applies.
    """
    for r in reversed(recs):
        if r.get("type") == "system" and r.get("subtype") == "compact_boundary":
            return None
        m = r.get("message") or {}
        u = m.get("usage")
        if r.get("type") == "assistant" and u and not r.get("isSidechain") \
                and m.get("model") != "<synthetic>":
            n = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                 + u.get("cache_creation_input_tokens", 0))
            return n, epoch(r["timestamp"])
    return None


def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    week = time.time() - 7 * 86400
    state = {k: v for k, v in state.items() if v > week}
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def on_prompt(inp):
    ctx = last_context(tail_records(inp["transcript_path"]))
    if not ctx:
        return None
    tokens, last = ctx
    armed = os.path.exists(ARM)
    idle = time.time() - last
    if tokens < MIN_CONTEXT or (idle < IDLE_MIN * 60 and not armed):
        return None
    state = load_state()
    sid = inp.get("session_id", "")
    if state.get(sid, 0) > last:
        return None  # already paused once for this idle spell: the resend goes
    state[sid] = time.time()
    save_state(state)
    if armed:
        os.remove(ARM)
    h, m = divmod(int(idle // 60), 60)
    return {"decision": "block", "reason": (
        "Paused once (context_hygiene): idle %s%d min, carrying %dK tokens. "
        "The prompt cache has expired, so this prompt would re-cache all %dK. "
        "New task? /clear, then send it - the work is in the commits, "
        "CHANGELOG and memory. Same task? Send it again to continue here."
        % ("%d h " % h if h else "", m, tokens // 1000, tokens // 1000))}


def pushed_this_turn(recs):
    """True if a git push succeeded after the newest real user prompt."""
    start = 0
    for i in range(len(recs) - 1, -1, -1):
        r = recs[i]
        c = (r.get("message") or {}).get("content")
        if r.get("type") == "user" and not r.get("isMeta") and (
                isinstance(c, str) or any(
                    b.get("type") == "text" for b in c or [] if isinstance(b, dict))):
            start = i
            break
    pushes, ok = set(), False
    for r in recs[start:]:
        for b in (r.get("message") or {}).get("content") or []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and b.get("name") in ("Bash", "PowerShell") \
                    and PUSH.search(str((b.get("input") or {}).get("command", ""))):
                pushes.add(b["id"])
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in pushes \
                    and not b.get("is_error"):
                ok = True
    return ok


def on_stop(inp):
    if inp.get("stop_hook_active"):
        return None
    recs = tail_records(inp["transcript_path"])
    ctx = last_context(recs)
    if not ctx or ctx[0] < MIN_CONTEXT or not pushed_this_turn(recs):
        return None
    return {"systemMessage": (
        "Pushed, and this session carries %dK tokens. If the next request is "
        "a new task, /clear first - the work is in the commits. (context_hygiene)"
        % (ctx[0] // 1000))}


def main():
    try:
        inp = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        mode = sys.argv[1] if len(sys.argv) > 1 else ""
        out = {"userpromptsubmit": on_prompt, "stop": on_stop}[mode](inp)
        if out:
            print(json.dumps(out))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
