"""Two-direction tests for context_hygiene.py: every case that should fire, and
every near miss that must stay silent."""
import json, os, subprocess, sys, tempfile, time, glob
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "context_hygiene.py")
TMP = tempfile.mkdtemp(prefix="hyg_")
STATE = os.path.join(TMP, "state")
fails = 0


def iso(ago_s):
    return datetime.fromtimestamp(time.time() - ago_s, timezone.utc).isoformat().replace("+00:00", "Z")


def asst(ago, ctx, content=None, side=False):
    return {"type": "assistant", "timestamp": iso(ago), "isSidechain": side, "message": {
        "model": "claude-opus-5", "content": content or [{"type": "text", "text": "ok"}],
        "usage": {"input_tokens": 2, "cache_read_input_tokens": ctx - 1002, "cache_creation_input_tokens": 1000}}}


def user(text, ago=0):
    return {"type": "user", "timestamp": iso(ago), "message": {"content": text}}


def result(tid, err=False, ago=0):
    return {"type": "user", "timestamp": iso(ago), "message": {"content": [
        {"type": "tool_result", "tool_use_id": tid, "is_error": err, "content": "done"}]}}


def push_call(tid, cmd="cd /h && git add a && git commit -m x && git push", name="Bash", ago=0, ctx=480_000):
    return asst(ago, ctx, [{"type": "tool_use", "id": tid, "name": name, "input": {"command": cmd}}])


def run(mode, recs, sid="s1", raw=None):
    p = os.path.join(TMP, "t.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r) for r in recs) + "\n")
    stdin = raw if raw is not None else json.dumps({"session_id": sid, "transcript_path": p, "stop_hook_active": False})
    env = dict(os.environ, CONTEXT_HYGIENE_STATE=STATE)
    cp = subprocess.run([sys.executable, HOOK, mode], input=stdin.encode(), capture_output=True, env=env, timeout=30)
    assert cp.returncode == 0, cp
    return json.loads(cp.stdout) if cp.stdout.strip() else None


def check(name, got, want):
    global fails
    kind = None if got is None else ("block" if got.get("decision") == "block" else "message" if "systemMessage" in got else "other")
    ok = kind == want
    fails += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: want {want}, got {kind}" + ("" if ok else f"  {got}"))


H = 3600
print("userpromptsubmit")
stale = [user("hi", 2 * H + 60), asst(2 * H, 480_000)]
check("idle 2h, 480K -> block", run("userpromptsubmit", stale), "block")
check("same idle spell, resend -> allow", run("userpromptsubmit", stale), None)
check("other session, same shape -> block", run("userpromptsubmit", stale, sid="s2"), "block")
check("idle 2h, 149K -> allow", run("userpromptsubmit", [asst(2 * H, 149_000)], sid="s3"), None)
check("idle 2h, exactly 150K -> block", run("userpromptsubmit", [asst(2 * H, 150_000)], sid="s3b"), "block")
check("idle 59 min, 480K -> allow", run("userpromptsubmit", [asst(59 * 60, 480_000)], sid="s4"), None)
check("idle 61 min, 480K -> block", run("userpromptsubmit", [asst(61 * 60, 480_000)], sid="s4b"), "block")
check("compaction after last response -> allow", run("userpromptsubmit", stale + [{"type": "system", "subtype": "compact_boundary", "timestamp": iso(60)}], sid="s5"), None)
check("fresh session (no responses) -> allow", run("userpromptsubmit", [user("hi")], sid="s6"), None)
check("only a sidechain response is stale+big -> allow", run("userpromptsubmit", [asst(10, 60_000), asst(2 * H, 480_000, side=True)], sid="s7"), None)
# new idle spell: paused 5 h ago, work resumed (response 4 h ago is newer than the pause), idle again
with open(os.path.join(STATE, "context_hygiene.json"), encoding="utf-8") as f:
    st = json.load(f)
st["s8"] = st["s8b"] = time.time() - 5 * H
with open(os.path.join(STATE, "context_hygiene.json"), "w", encoding="utf-8") as f:
    json.dump(st, f)
check("paused 5h ago, responses since, idle again -> block again", run("userpromptsubmit", [asst(6 * H, 480_000), asst(4 * H, 490_000)], sid="s8"), "block")
check("paused 5h ago, NO response since -> allow", run("userpromptsubmit", [asst(6 * H, 480_000)], sid="s8b"), None)
os.makedirs(STATE, exist_ok=True); open(os.path.join(STATE, "arm_test"), "w").close()
check("armed, idle 5 min, 480K -> block", run("userpromptsubmit", [asst(300, 480_000)], sid="s9"), "block")
check("arm file consumed", None if not os.path.exists(os.path.join(STATE, "arm_test")) else {"x": 1}, None)
check("armed test resend -> allow", run("userpromptsubmit", [asst(300, 480_000)], sid="s9"), None)
check("malformed stdin -> silent", run("userpromptsubmit", [], raw="{not json"), None)
check("missing transcript -> silent", run("userpromptsubmit", [], raw=json.dumps({"session_id": "x", "transcript_path": "Z:/nope.jsonl"})), None)
check("unknown mode -> silent", run("bogus", stale), None)

print("stop")
turn = [asst(600, 470_000), user("commit and push"), push_call("t1"), result("t1"), asst(0, 482_000)]
check("pushed OK this turn, 482K -> message", run("stop", turn), "message")
check("PowerShell git -C push -> message", run("stop", [user("go"), push_call("t2", "git -C H:/ push origin main", "PowerShell"), result("t2"), asst(0, 482_000)]), "message")
check("push failed (is_error) -> silent", run("stop", [user("go"), push_call("t3"), result("t3", err=True), asst(0, 482_000)]), None)
check("push result not written yet -> silent", run("stop", [user("go"), push_call("t4")]), None)
check("no push this turn -> silent", run("stop", [user("go"), push_call("t5", "git status"), result("t5"), asst(0, 482_000)]), None)
check("push in an EARLIER turn -> silent", run("stop", [user("a"), push_call("t6"), result("t6"), asst(60, 470_000), user("b"), asst(0, 482_000)]), None)
check("pushed, 100K -> silent", run("stop", [user("go"), push_call("t7", ctx=100_000), result("t7"), asst(0, 100_000)]), None)
check("stop_hook_active -> silent", run("stop", [], raw=json.dumps({"transcript_path": "x", "stop_hook_active": True})), None)
check("'git pushd' not a push -> silent", run("stop", [user("go"), push_call("t8", "echo git-pushd"), result("t8"), asst(0, 482_000)]), None)

print("real transcripts (read-only parse)")
sys.path.insert(0, HERE); import context_hygiene as ch
files = sorted(glob.glob(os.path.expanduser("~/.claude/projects/**/*.jsonl"), recursive=True), key=os.path.getsize)
for p in (files[-1], max(files, key=os.path.getmtime)):
    t0 = time.time(); recs = ch.tail_records(p); ctx = ch.last_context(recs); pushed = ch.pushed_this_turn(recs)
    print(f"  {os.path.getsize(p)/1e6:5.1f} MB  {os.path.basename(p)[:8]}  ctx={ctx and ctx[0]//1000}K  idle={ctx and int((time.time()-ctx[1])//60)} min  pushed_this_turn={pushed}  parse {1000*(time.time()-t0):.0f} ms")
print("FAILS:", fails)
sys.exit(1 if fails else 0)
