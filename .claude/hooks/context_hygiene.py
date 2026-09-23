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

R20 CHECKPOINT (added 2026-09-23). Compaction replaces the conversation with a
summary the model writes; only CLAUDE.md, memory, a few files and SessionStart
hook output come back from disk. Measured 09-16..09-23: 13 of 29 Reads after a
compaction re-read a file read before it [M]. R20 puts what must survive - the
verdicts verbatim, tagged figures, open questions - in CKPT_DIR/<session>.md.

  posttooluse   Context >= NUDGE_AT of autoCompactWindow AND the checkpoint is
                not newer than the moment the context crossed that line: add
                one line asking for it. Repeats after every tool call until
                written - the compaction is at most ~20% of the window away.
                Skipped inside subagents (agent_id is set only there).
  sessionstart  Matcher `compact` only. Re-inject the checkpoint verbatim, the
                session-start audit verdict (read from the transcript - no
                second copy), and a WARN (R8) when the checkpoint was missing
                or stale at the compaction. Appends one line to LOG.

NO PreCompact AND NO PostCompact HOOK, on purpose. A missing script makes
python exit 2, and exit 2 on PreCompact blocks the compaction - at the context
limit the request then fails (hooks.md, PreCompact). The checkpoint's age when
this SessionStart handler runs is its age at the compaction. The summary
PostCompact would save is already in the transcript (isCompactSummary record).
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
    os.path.dirname(os.path.abspath(__file__)), ".state"
)
STATE = os.path.join(STATE_DIR, "context_hygiene.json")
ARM = os.path.join(STATE_DIR, "arm_test")
PUSH = re.compile(r"\bgit\b[^\n|;&]*\bpush\b")
NUDGE_AT = 0.80
SMALL_TAIL = 256 << 10  # per-tool-call read; falls back to TAIL_BYTES
# additionalContext over 10,000 chars is replaced by a file path and a 2,000-char
# preview [S: code.claude.com/docs/en/hooks.md, "Add context for Claude"]. The
# rest of the budget is the WARN and audit lines around the checkpoint.
CKPT_MAX = 8000
_CLAUDE = os.path.join(os.path.expanduser("~"), ".claude")
CKPT_DIR = os.environ.get("CONTEXT_HYGIENE_CHECKPOINTS") or os.path.join(
    _CLAUDE, "checkpoints"
)
LOG = os.path.join(CKPT_DIR, "compactions.log")
SETTINGS = os.environ.get("CONTEXT_HYGIENE_SETTINGS") or os.path.join(
    _CLAUDE, "settings.json"
)


def tail_records(path, nbytes=TAIL_BYTES):
    """Transcript records from the last nbytes, oldest first."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - nbytes))
        lines = f.read().split(b"\n")
    if size > nbytes:
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


def is_boundary(r):
    return r.get("type") == "system" and r.get("subtype") == "compact_boundary"


def ctx_of(r):
    """Context tokens of a main-thread response record, else None."""
    m = r.get("message") or {}
    u = m.get("usage")
    if (
        r.get("type") == "assistant"
        and u
        and not r.get("isSidechain")
        and m.get("model") != "<synthetic>"
    ):
        return (
            u.get("input_tokens", 0)
            + u.get("cache_read_input_tokens", 0)
            + u.get("cache_creation_input_tokens", 0)
        )
    return None


def last_context(recs):
    """(tokens, epoch) of the newest main-thread response, or None.

    None also when a compaction follows it: the old size no longer applies.
    """
    resp = segment_responses(recs)
    return (resp[-1][1], resp[-1][0]) if resp else None


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
    return {
        "decision": "block",
        "reason": (
            "Paused once (context_hygiene): idle %s%d min, carrying %dK tokens. "
            "The prompt cache has expired, so this prompt would re-cache all %dK. "
            "New task? /clear, then send it - the work is in the commits, "
            "CHANGELOG and memory. Same task? Send it again to continue here."
            % ("%d h " % h if h else "", m, tokens // 1000, tokens // 1000)
        ),
    }


def pushed_this_turn(recs):
    """True if a git push succeeded after the newest real user prompt."""
    start = 0
    for i in range(len(recs) - 1, -1, -1):
        r = recs[i]
        c = (r.get("message") or {}).get("content")
        if (
            r.get("type") == "user"
            and not r.get("isMeta")
            and (
                isinstance(c, str)
                or any(b.get("type") == "text" for b in c or [] if isinstance(b, dict))
            )
        ):
            start = i
            break
    pushes, ok = set(), False
    for r in recs[start:]:
        for b in (r.get("message") or {}).get("content") or []:
            if not isinstance(b, dict):
                continue
            if (
                b.get("type") == "tool_use"
                and b.get("name") in ("Bash", "PowerShell")
                and PUSH.search(str((b.get("input") or {}).get("command", "")))
            ):
                pushes.add(b["id"])
            elif (
                b.get("type") == "tool_result"
                and b.get("tool_use_id") in pushes
                and not b.get("is_error")
            ):
                ok = True
    return ok


def on_stop(inp):
    if inp.get("stop_hook_active"):
        return None
    recs = tail_records(inp["transcript_path"])
    ctx = last_context(recs)
    if not ctx or ctx[0] < MIN_CONTEXT or not pushed_this_turn(recs):
        return None
    return {
        "systemMessage": (
            "Pushed, and this session carries %dK tokens. If the next request is "
            "a new task, /clear first - the work is in the commits. (context_hygiene)"
            % (ctx[0] // 1000)
        )
    }


def parse_tokens(v):
    """200000, "200000", "200k", "1m" -> int."""
    s = str(v).strip().lower()
    mult = {"k": 1000, "m": 1000000}.get(s[-1:], 1)
    return int(float(s[:-1] if mult > 1 else s) * mult)


def window():
    """The auto-compact window in tokens, or None when it cannot be read.

    The env var first, then settings.json, which `/autocompact` writes (Bill's
    `/autocompact 200K` landed there on 2026-09-23). Read, never copied, so a
    later /autocompact moves the nudge with it (R10).
    """
    try:
        v = os.environ.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW")
        if not v:
            with open(SETTINGS, encoding="utf-8") as f:
                v = json.load(f).get("autoCompactWindow")
        return parse_tokens(v) if v else None
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def checkpoint_path(sid):
    return os.path.join(CKPT_DIR, re.sub(r"[^\w.-]", "_", sid or "unknown") + ".md")


def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def hhmm(t):
    return datetime.fromtimestamp(t).strftime("%H:%M")


def stamp(t):
    return datetime.fromtimestamp(t).isoformat(timespec="seconds") if t else "-"


def segment_responses(recs):
    """[(epoch, tokens)] of main-thread responses after the newest compaction in recs.

    By timestamp, never by file order: at a /compact on 2026-09-23 Claude Code
    re-appended 117 earlier records (same uuids) after newer ones [M, n=1]. So
    the newest compaction is the latest-stamped one, and exact copies merge.
    """
    floor = max((epoch(r["timestamp"]) for r in recs if is_boundary(r)), default=0.0)
    out = set()
    for r in recs:
        n = ctx_of(r)
        if n is not None:
            t = epoch(r["timestamp"])
            if t > floor:
                out.add((t, n))
    return sorted(out)


def run_start(resp, thr):
    """Epoch of the first response in the newest unbroken run at >= thr, else None."""
    t = None
    for when, n in reversed(resp):
        if n < thr:
            break
        t = when
    return t


def on_tool(inp):
    if inp.get("agent_id"):
        return None  # a subagent: its context is not the one that compacts
    win = window()
    if not win:
        return None
    thr = int(NUDGE_AT * win)
    path = inp["transcript_path"]
    ctx = last_context(tail_records(path, SMALL_TAIL)) or last_context(
        tail_records(path)
    )
    if not ctx or ctx[0] < thr:
        return None
    since = run_start(segment_responses(tail_records(path)), thr)
    ck = checkpoint_path(inp.get("session_id"))
    written = mtime(ck)
    if written is not None and since is not None and written >= since:
        return None
    state = (
        "does not exist yet"
        if written is None
        else (
            "was last written %s, before the context crossed that line at %s"
            % (hhmm(written), hhmm(since) if since else "?")
        )
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "R20 CHECKPOINT DUE (context_hygiene): context %dK has passed %d%% of the "
                "%dK auto-compact window, and %s %s. Write it now, under %d chars: goal / "
                "verdicts verbatim / tagged figures / decisions + why / disproven theories / "
                "open questions to Bill / next step / files touched. This repeats after "
                "each tool call until the file is written."
                % (ctx[0] // 1000, NUDGE_AT * 100, win // 1000, ck, state, CKPT_MAX)
            ),
        }
    }


def scan(path):
    """Whole transcript -> (boundaries, responses, audits), sorted by time.

    boundaries [epoch], responses [(epoch, tokens)], audits [(epoch, text)] of
    the SessionStart audit context. Lines are pre-filtered by substring; records
    are then classified by their own fields, because a response that merely
    quotes those strings is still a response. Sorted and de-duplicated because
    file order is not time order (see segment_responses).
    """
    bnd, resp, aud = [], [], []
    with open(path, "rb") as f:
        for line in f:
            if (
                b"compact_boundary" not in line
                and b'"usage"' not in line
                and b"hook_additional_context" not in line
            ):
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            a = r.get("attachment") or {}
            if is_boundary(r):
                bnd.append(epoch(r["timestamp"]))
            elif (
                r.get("type") == "attachment"
                and a.get("type") == "hook_additional_context"
            ):
                c = a.get("content")
                for s in c if isinstance(c, list) else [c]:
                    if isinstance(s, str) and s.startswith("HA CONFIG AUDIT"):
                        aud.append((epoch(r["timestamp"]), s))
            else:
                n = ctx_of(r)
                if n is not None:
                    resp.append((epoch(r["timestamp"]), n))
    return sorted(set(bnd)), sorted(set(resp)), sorted(set(aud))


def log_line(*fields):
    try:
        os.makedirs(CKPT_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("\t".join(str(x) for x in fields) + "\n")
    except OSError:
        pass


def on_compact(inp):
    """LOG columns: now, session, window, ref, written, status, chars.

    The compaction's trigger and size are in its compact_boundary record, which
    scoring joins by session and time; they are not copied here (R10). The first
    line, 2026-09-23T10:22:48, predates that and has trigger "?" and preTokens
    None after the session column: that record was not on disk yet.
    """
    if inp.get("source") != "compact":
        return None
    now = time.time()
    sid = inp.get("session_id", "")
    bnd, resp, aud = scan(inp["transcript_path"])
    # Is this compaction's boundary on disk yet? On a /compact on 2026-09-23 it
    # was not: it is flushed in one batch with this hook's own output [M, n=1].
    # So the else branch is the usual one; the first stays for any compaction
    # that differs. The newest boundary is this one only if no response followed.
    if bnd and not any(t > bnd[-1] for t, _ in resp):
        this, start = bnd[-1], (bnd[-2] if len(bnd) > 1 else 0.0)
    else:
        this, start = now, (bnd[-1] if bnd else 0.0)
    seg = [(t, n) for t, n in resp if start < t <= this]
    win = window()
    since = run_start(seg, int(NUDGE_AT * win)) if win else None
    ref = since or (seg[0][0] if seg else start)
    ck = checkpoint_path(sid)
    written = mtime(ck)
    status = "missing" if written is None else "fresh" if written >= ref else "stale"
    body = ""
    if written is not None:
        with open(ck, encoding="utf-8", errors="replace") as f:
            body = f.read()
    parts = []
    if status == "missing":
        parts.append(
            "WARN (R8, context_hygiene): no R20 checkpoint existed at this compaction "
            "(%s). Everything before it survives only in the summary. Say so in your "
            "next message, and re-verify any verdict, figure or open question from "
            "before the compaction before relying on it." % ck
        )
    elif status == "stale":
        parts.append(
            "WARN (R8, context_hygiene): the R20 checkpoint was STALE at this "
            "compaction - written %s, before %s %s. Work after that survives only in "
            "the summary. Say so in your next message, and re-verify verdicts from "
            "that span before relying on them."
            % (
                hhmm(written),
                "the context crossed %d%% of the window at" % (NUDGE_AT * 100)
                if since
                else "this stretch of the session began at",
                hhmm(ref),
            )
        )
    if not win:
        parts.append(
            "WARN (R8, context_hygiene): autoCompactWindow could not be read "
            "from %s, so staleness was judged from the start of the stretch "
            "and the pre-compaction nudge cannot fire." % SETTINGS
        )
    if len(body) > CKPT_MAX:
        parts.append(
            "WARN (R8, context_hygiene): the checkpoint is %d chars; only the "
            "first %d follow, because hook context over 10,000 chars is replaced "
            "by a preview. Trim it." % (len(body), CKPT_MAX)
        )
    if body:
        parts.append(
            "R20 CHECKPOINT %s, re-injected verbatim after a compaction. Written %s. "
            "Its verdicts are quoted, not paraphrased - prefer them to the summary's "
            "wording. Update it at the next milestone.\n---\n%s\n---"
            % (ck, hhmm(written), body[:CKPT_MAX])
        )
    if aud:
        try:
            from ha_audit_gate import verdict_line  # one definition (R10)

            v = verdict_line(aud[-1][1])
        except Exception as e:
            v = "(could not parse it: %s)" % e
        parts.append(
            "Session-start audit verdict, %s - a baseline for 'WARN count must "
            "not increase', not a current result: %s" % (stamp(aud[-1][0]), v)
        )
    else:
        parts.append(
            "WARN (R8, context_hygiene): no session-start audit verdict in this "
            "transcript - run ha_audit.py before claiming a WARN count did not "
            "increase."
        )
    log_line(
        stamp(now),
        sid,
        win,
        stamp(ref),
        stamp(written),
        status,
        len(body),
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n\n".join(parts),
        }
    }


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        inp = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        out = {
            "userpromptsubmit": on_prompt,
            "stop": on_stop,
            "posttooluse": on_tool,
            "sessionstart": on_compact,
        }[mode](inp)
        if out:
            print(json.dumps(out))
    except Exception as e:
        if mode == "sessionstart":  # R8: a re-injection that did not happen must say so
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "SessionStart",
                            "additionalContext": (
                                "WARN (R8, context_hygiene): the compaction handler failed (%s: %s), "
                                "so no checkpoint was re-injected. Read it yourself from %s."
                                % (type(e).__name__, e, CKPT_DIR)
                            ),
                        }
                    }
                )
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
