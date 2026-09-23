"""Two-direction tests for context_hygiene.py: every case that should fire, and
every near miss that must stay silent."""

import json
import os
import subprocess
import sys
import tempfile
import time
import glob
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.environ.get("HYGIENE_HOOK") or os.path.join(
    HERE, "context_hygiene.py"
)  # mutation runs
TMP = tempfile.mkdtemp(prefix="hyg_")
STATE = os.path.join(TMP, "state")
CK = os.path.join(TMP, "ck")
SET = os.path.join(TMP, "settings.json")
with open(SET, "w", encoding="utf-8") as f:
    json.dump({"autoCompactWindow": 200000}, f)
fails = 0


def iso(ago_s):
    return (
        datetime.fromtimestamp(time.time() - ago_s, timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def asst(ago, ctx, content=None, side=False):
    return {
        "type": "assistant",
        "timestamp": iso(ago),
        "isSidechain": side,
        "message": {
            "model": "claude-opus-5",
            "content": content or [{"type": "text", "text": "ok"}],
            "usage": {
                "input_tokens": 2,
                "cache_read_input_tokens": ctx - 1002,
                "cache_creation_input_tokens": 1000,
            },
        },
    }


def user(text, ago=0):
    return {"type": "user", "timestamp": iso(ago), "message": {"content": text}}


def result(tid, err=False, ago=0):
    return {
        "type": "user",
        "timestamp": iso(ago),
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tid,
                    "is_error": err,
                    "content": "done",
                }
            ]
        },
    }


def push_call(
    tid,
    cmd="cd /h && git add a && git commit -m x && git push",
    name="Bash",
    ago=0,
    ctx=480_000,
):
    return asst(
        ago,
        ctx,
        [{"type": "tool_use", "id": tid, "name": name, "input": {"command": cmd}}],
    )


def run(mode, recs, sid="s1", raw=None, extra=None, env_extra=None):
    p = os.path.join(TMP, "t.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r) for r in recs) + "\n")
    stdin = (
        raw
        if raw is not None
        else json.dumps(
            dict(
                {"session_id": sid, "transcript_path": p, "stop_hook_active": False},
                **(extra or {}),
            )
        )
    )
    env = dict(
        os.environ,
        CONTEXT_HYGIENE_STATE=STATE,
        CONTEXT_HYGIENE_CHECKPOINTS=CK,
        CONTEXT_HYGIENE_SETTINGS=SET,
    )
    env.pop("CLAUDE_CODE_AUTO_COMPACT_WINDOW", None)
    env.update(env_extra or {})
    cp = subprocess.run(
        [sys.executable, HOOK, mode],
        input=stdin.encode(),
        capture_output=True,
        env=env,
        timeout=30,
    )
    assert cp.returncode == 0, cp
    return json.loads(cp.stdout) if cp.stdout.strip() else None


def text(got):
    return ((got or {}).get("hookSpecificOutput") or {}).get("additionalContext", "")


def check(name, got, want, has=(), lacks=()):
    """want: None/block/message/context; has/lacks: substrings of the injected context."""
    global fails
    kind = (
        None
        if got is None
        else (
            "block"
            if got.get("decision") == "block"
            else "message"
            if "systemMessage" in got
            else "context"
            if "hookSpecificOutput" in got
            else "other"
        )
    )
    t = text(got)
    ok = kind == want and all(s in t for s in has) and not any(s in t for s in lacks)
    fails += not ok
    print(
        f"  {'PASS' if ok else 'FAIL'}  {name}: want {want}, got {kind}"
        + ("" if ok else f"  {got}")
    )


H = 3600
print("userpromptsubmit")
stale = [user("hi", 2 * H + 60), asst(2 * H, 480_000)]
check("idle 2h, 480K -> block", run("userpromptsubmit", stale), "block")
check("same idle spell, resend -> allow", run("userpromptsubmit", stale), None)
check(
    "other session, same shape -> block",
    run("userpromptsubmit", stale, sid="s2"),
    "block",
)
check(
    "idle 2h, 149K -> allow",
    run("userpromptsubmit", [asst(2 * H, 149_000)], sid="s3"),
    None,
)
check(
    "idle 2h, exactly 150K -> block",
    run("userpromptsubmit", [asst(2 * H, 150_000)], sid="s3b"),
    "block",
)
check(
    "idle 59 min, 480K -> allow",
    run("userpromptsubmit", [asst(59 * 60, 480_000)], sid="s4"),
    None,
)
check(
    "idle 61 min, 480K -> block",
    run("userpromptsubmit", [asst(61 * 60, 480_000)], sid="s4b"),
    "block",
)
check(
    "compaction after last response -> allow",
    run(
        "userpromptsubmit",
        stale
        + [{"type": "system", "subtype": "compact_boundary", "timestamp": iso(60)}],
        sid="s5",
    ),
    None,
)
check(
    "fresh session (no responses) -> allow",
    run("userpromptsubmit", [user("hi")], sid="s6"),
    None,
)
check(
    "only a sidechain response is stale+big -> allow",
    run(
        "userpromptsubmit",
        [asst(10, 60_000), asst(2 * H, 480_000, side=True)],
        sid="s7",
    ),
    None,
)
# new idle spell: paused 5 h ago, work resumed (response 4 h ago is newer than the pause), idle again
with open(os.path.join(STATE, "context_hygiene.json"), encoding="utf-8") as f:
    st = json.load(f)
st["s8"] = st["s8b"] = time.time() - 5 * H
with open(os.path.join(STATE, "context_hygiene.json"), "w", encoding="utf-8") as f:
    json.dump(st, f)
check(
    "paused 5h ago, responses since, idle again -> block again",
    run("userpromptsubmit", [asst(6 * H, 480_000), asst(4 * H, 490_000)], sid="s8"),
    "block",
)
check(
    "paused 5h ago, NO response since -> allow",
    run("userpromptsubmit", [asst(6 * H, 480_000)], sid="s8b"),
    None,
)
os.makedirs(STATE, exist_ok=True)
open(os.path.join(STATE, "arm_test"), "w").close()
check(
    "armed, idle 5 min, 480K -> block",
    run("userpromptsubmit", [asst(300, 480_000)], sid="s9"),
    "block",
)
check(
    "arm file consumed",
    None if not os.path.exists(os.path.join(STATE, "arm_test")) else {"x": 1},
    None,
)
check(
    "armed test resend -> allow",
    run("userpromptsubmit", [asst(300, 480_000)], sid="s9"),
    None,
)
check("malformed stdin -> silent", run("userpromptsubmit", [], raw="{not json"), None)
check(
    "missing transcript -> silent",
    run(
        "userpromptsubmit",
        [],
        raw=json.dumps({"session_id": "x", "transcript_path": "Z:/nope.jsonl"}),
    ),
    None,
)
check("unknown mode -> silent", run("bogus", stale), None)

print("stop")
turn = [
    asst(600, 470_000),
    user("commit and push"),
    push_call("t1"),
    result("t1"),
    asst(0, 482_000),
]
check("pushed OK this turn, 482K -> message", run("stop", turn), "message")
check(
    "PowerShell git -C push -> message",
    run(
        "stop",
        [
            user("go"),
            push_call("t2", "git -C H:/ push origin main", "PowerShell"),
            result("t2"),
            asst(0, 482_000),
        ],
    ),
    "message",
)
check(
    "push failed (is_error) -> silent",
    run(
        "stop", [user("go"), push_call("t3"), result("t3", err=True), asst(0, 482_000)]
    ),
    None,
)
check(
    "push result not written yet -> silent",
    run("stop", [user("go"), push_call("t4")]),
    None,
)
check(
    "no push this turn -> silent",
    run(
        "stop",
        [user("go"), push_call("t5", "git status"), result("t5"), asst(0, 482_000)],
    ),
    None,
)
check(
    "push in an EARLIER turn -> silent",
    run(
        "stop",
        [
            user("a"),
            push_call("t6"),
            result("t6"),
            asst(60, 470_000),
            user("b"),
            asst(0, 482_000),
        ],
    ),
    None,
)
check(
    "pushed, 100K -> silent",
    run(
        "stop",
        [user("go"), push_call("t7", ctx=100_000), result("t7"), asst(0, 100_000)],
    ),
    None,
)
check(
    "stop_hook_active -> silent",
    run("stop", [], raw=json.dumps({"transcript_path": "x", "stop_hook_active": True})),
    None,
)
check(
    "'git pushd' not a push -> silent",
    run(
        "stop",
        [user("go"), push_call("t8", "echo git-pushd"), result("t8"), asst(0, 482_000)],
    ),
    None,
)


def ckpt(
    sid,
    ago=None,
    body="GOAL: x\nVERDICT: PASS (parse-clean) - validate_ha.py --strict\n",
):
    """Write the session's checkpoint with mtime `ago` seconds back; ago=None removes it."""
    os.makedirs(CK, exist_ok=True)
    p = os.path.join(CK, sid + ".md")
    if ago is None:
        if os.path.exists(p):
            os.remove(p)
        return p
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    t = time.time() - ago
    os.utime(p, (t, t))
    return p


def bnd(ago, trigger="auto", pre=185_000):
    return {
        "type": "system",
        "subtype": "compact_boundary",
        "timestamp": iso(ago),
        "compactMetadata": {"trigger": trigger, "preTokens": pre},
    }


def audit(ago, verdict="0 FAIL, 0 WARN, 2 INFO", first=None):
    body = (
        "HA CONFIG AUDIT (ran automatically per CLAUDE.md SESSION PROTOCOL).\n\nINFO  x  y\n"
        + verdict
    )
    return {
        "type": "attachment",
        "timestamp": iso(ago),
        "attachment": {
            "type": "hook_additional_context",
            "hookEvent": "SessionStart",
            "content": ([first] if first else []) + [body],
        },
    }


PT = "posttooluse"
up = [
    asst(900, 150_000),
    asst(600, 165_000),
    asst(0, 170_000),
]  # crosses 160K (80% of 200K) 600 s ago
print("posttooluse (window 200K from settings, line at 160K)")
ckpt("p1")
check(
    "170K, no checkpoint -> nudge",
    run(PT, up, sid="p1"),
    "context",
    has=("does not exist", "p1.md"),
)
ckpt("p2", 300)
check("checkpoint written after the crossing -> silent", run(PT, up, sid="p2"), None)
ckpt("p3", 1200)
check(
    "checkpoint written before the crossing -> nudge",
    run(PT, up, sid="p3"),
    "context",
    has=("before the context crossed",),
)
check(
    "159,999 -> silent", run(PT, [asst(600, 150_000), asst(0, 159_999)], sid="p4"), None
)
check(
    "exactly 160,000 -> nudge",
    run(PT, [asst(600, 150_000), asst(0, 160_000)], sid="p5"),
    "context",
)
check(
    "inside a subagent (agent_id) -> silent",
    run(PT, up, sid="p1", extra={"agent_id": "a1"}),
    None,
)
check(
    "settings unreadable, no env -> silent",
    run(
        PT,
        up,
        sid="p1",
        env_extra={"CONTEXT_HYGIENE_SETTINGS": os.path.join(TMP, "none.json")},
    ),
    None,
)
check(
    "env 250k beats settings (line 200K) -> silent",
    run(PT, up, sid="p1", env_extra={"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "250k"}),
    None,
)
check(
    "env 150k beats settings (line 120K) -> nudge",
    run(PT, up, sid="p1", env_extra={"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "150k"}),
    "context",
)
check(
    "compaction after the last response -> silent",
    run(PT, up + [bnd(10)], sid="p1"),
    None,
)
two = [
    asst(3000, 190_000),
    bnd(2500),
    asst(2400, 60_000),
    asst(300, 165_000),
    asst(0, 170_000),
]
ckpt("p10", 600)
check(
    "written after the OLD crossing, before the new one -> nudge",
    run(PT, two, sid="p10"),
    "context",
)
ckpt("p10", 100)
check("written after the new crossing -> silent", run(PT, two, sid="p10"), None)
dip = [asst(1200, 170_000), asst(900, 150_000), asst(300, 165_000), asst(0, 170_000)]
ckpt("p12", 600)
check(
    "dip below the line restarts the run -> nudge", run(PT, dip, sid="p12"), "context"
)
big = up + [
    {
        "type": "user",
        "timestamp": iso(0),
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "x",
                    "content": "z" * (300 << 10),
                }
            ]
        },
    }
]
check(
    "last response hidden behind a 300 KB result -> nudge",
    run(PT, big, sid="p1"),
    "context",
)
check("malformed stdin -> silent", run(PT, [], raw="{not json"), None)

SS = "sessionstart"
C = {"source": "compact"}
pre = [
    audit(5000),
    asst(4000, 60_000),
    asst(1200, 150_000),
    asst(600, 165_000),
    asst(120, 185_000),
]
done = pre + [bnd(60, "auto", 185_000)]
print("sessionstart (matcher compact)")
body = "GOAL: x\nVERDICT: PASS (parse-clean) - validate_ha.py --strict\n"
ckpt("c1", 300)
check(
    "fresh checkpoint -> re-injected verbatim, no WARN",
    run(SS, done, sid="c1", extra=C),
    "context",
    has=(body, "auto compaction at 185K", "0 FAIL, 0 WARN, 2 INFO"),
    lacks=("WARN (R8",),
)
ckpt("c2", 900)
check(
    "written before the crossing -> STALE WARN + text",
    run(SS, done, sid="c2", extra=C),
    "context",
    has=("STALE", "crossed 80%", body),
)
ckpt("c3")
check(
    "no checkpoint -> missing WARN",
    run(SS, done, sid="c3", extra=C),
    "context",
    has=("no R20 checkpoint existed",),
)
nobnd = [
    audit(5000),
    asst(4500, 190_000),
    bnd(4000),
    asst(3000, 60_000),
    asst(600, 165_000),
    asst(60, 185_000),
]
ckpt("c4", 300)
check(
    "boundary not written yet, fresh -> no WARN",
    run(SS, nobnd, sid="c4", extra=C),
    "context",
    has=(body,),
    lacks=("WARN (R8",),
)
ckpt("c4", 900)
check(
    "boundary not written yet, stale -> STALE",
    run(SS, nobnd, sid="c4", extra=C),
    "context",
    has=("STALE",),
)
early = [
    audit(5000),
    asst(3000, 60_000),
    asst(600, 100_000),
    bnd(30, "manual", 100_000),
]
ckpt("c5", 2000)
check(
    "manual compact below the line, written this stretch -> no WARN",
    run(SS, early, sid="c5", extra=C),
    "context",
    has=("manual compaction at 100K",),
    lacks=("WARN (R8",),
)
ckpt("c5", 4000)
check(
    "manual compact, written before this stretch -> STALE",
    run(SS, early, sid="c5", extra=C),
    "context",
    has=("STALE", "began at"),
)
check(
    "source startup -> silent",
    run(SS, done, sid="c1", extra={"source": "startup"}),
    None,
)
check(
    "no audit in transcript -> audit WARN",
    run(SS, done[1:], sid="c1", extra=C),
    "context",
    has=("no session-start audit verdict",),
)
quote = [
    asst(
        600,
        165_000,
        [
            {
                "type": "text",
                "text": "hook_additional_context HA CONFIG AUDIT 1 FAIL, 9 WARN, compact_boundary",
            }
        ],
    )
]
check(
    "a response quoting the markers is not an audit or a boundary",
    run(SS, quote + [bnd(60)], sid="c1", extra=C),
    "context",
    has=("no session-start audit verdict",),
    lacks=("9 WARN",),
)
qb = [
    audit(5000),
    asst(1200, 150_000),
    asst(600, 165_000),
    asst(300, 170_000, [{"type": "text", "text": "the compact_boundary record says"}]),
    asst(120, 185_000),
    bnd(60),
]
ckpt("c9", 200)
check(
    "a response quoting compact_boundary does not move the stretch start",
    run(SS, qb, sid="c9", extra=C),
    "context",
    lacks=("WARN (R8",),
)
reinj = done + [audit(30, verdict="x", first="R20 CHECKPOINT ... 7 FAIL, 7 WARN,")]
reinj[-1]["attachment"]["content"] = [
    "R20 CHECKPOINT ... quoting HA CONFIG AUDIT from an old run\n7 FAIL, 7 WARN,"
]
check(
    "an earlier re-injection is not mistaken for the audit",
    run(SS, reinj, sid="c1", extra=C),
    "context",
    has=("0 FAIL, 0 WARN, 2 INFO",),
    lacks=("7 FAIL",),
)
ckpt("c8", 300, "Y" * 9800)  # over 10,000 with the wrapper unless truncated
got = run(SS, done, sid="c8", extra=C)
check(
    "9,800-char checkpoint -> trim WARN, context under 10,000",
    got,
    "context",
    has=("is 9800 chars", "Trim it"),
)
check(
    "  ...and the injected context really is under 10,000",
    None if len(text(got)) < 10_000 else {"len": len(text(got))},
    None,
)
check(
    "malformed stdin -> handler-failed WARN",
    run(SS, [], raw="{not json"),
    "context",
    has=("handler failed",),
)
with open(os.path.join(CK, "compactions.log"), encoding="utf-8") as f:
    st8 = [ln.split("\t")[7] for ln in f.read().splitlines()]
check(
    "log: one line per compaction, statuses in order",
    None
    if st8[:3] == ["fresh", "stale", "missing"] and len(st8) == 12
    else {"log": st8},
    None,
)

print("real transcripts (read-only parse)")
sys.path.insert(0, HERE)
import context_hygiene as ch  # noqa: E402
from ha_audit_gate import verdict_line  # noqa: E402

files = sorted(
    glob.glob(os.path.expanduser("~/.claude/projects/**/*.jsonl"), recursive=True),
    key=os.path.getsize,
)
for p in (files[-1], max(files, key=os.path.getmtime)):
    t0 = time.time()
    recs = ch.tail_records(p)
    ctx = ch.last_context(recs)
    pushed = ch.pushed_this_turn(recs)
    print(
        f"  {os.path.getsize(p) / 1e6:5.1f} MB  {os.path.basename(p)[:8]}  ctx={ctx and ctx[0] // 1000}K  idle={ctx and int((time.time() - ctx[1]) // 60)} min  pushed_this_turn={pushed}  parse {1000 * (time.time() - t0):.0f} ms"
    )
    t0 = time.time()
    b, rsp, au = ch.scan(p)
    print(
        f"      scan: boundaries={[(x[1], x[2]) for x in b][-3:]} responses={len(rsp)} audit={verdict_line(au[-1][1]) if au else None!r}  {1000 * (time.time() - t0):.0f} ms"
    )
    t0 = time.time()
    out = run(PT, [], raw=json.dumps({"session_id": "timing", "transcript_path": p}))
    print(
        f"      posttooluse end to end: {'nudge' if out else 'silent'}  {1000 * (time.time() - t0):.0f} ms"
    )
print("FAILS:", fails)
sys.exit(1 if fails else 0)
