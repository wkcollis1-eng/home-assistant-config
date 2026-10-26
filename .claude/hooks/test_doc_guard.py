"""Tests for doc_guard.py. Run: python test_doc_guard.py -> "ALL PASSED".

Fake transcripts are written as Claude Code writes them: one compact JSON
record per line (separators without spaces), so the raw compact_boundary
marker is matched exactly as it is in a real transcript.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import doc_guard as g  # noqa: E402

FAILS = []
HOME = "C:/fakehome"


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print("FAIL", name)


def rec(obj):
    return json.dumps(obj, separators=(",", ":"))


def use(name, **inp):
    return rec(
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "t", "name": name, "input": inp}
                ],
            },
        }
    )


def result(text):
    return rec(
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "t", "content": text}
                ],
            },
        }
    )


def boundary(uid):
    return rec(
        {
            "type": "system",
            "subtype": "compact_boundary",
            "uuid": uid,
            "content": "Conversation compacted",
        }
    )


class T:
    def __init__(self):
        self.d = tempfile.mkdtemp(prefix="doc_guard_t_")
        self.state = os.path.join(self.d, "state")
        self.n = 0

    def transcript(self, *lines):
        self.n += 1
        p = os.path.join(self.d, "t%d.jsonl" % self.n)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write("".join(ln + "\n" for ln in lines))
        return p

    def edit(self, path, tp, sid="s1", tool="Write"):
        key = "notebook_path" if tool == "NotebookEdit" else "file_path"
        inp = {
            "session_id": sid,
            "transcript_path": tp,
            "tool_name": tool,
            "tool_input": {key: path},
        }
        return g.decide(inp, self.state, HOME)

    def log(self):
        try:
            with open(os.path.join(self.state, g.LOG_FILE), encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return ""


def denied(out):
    return bool(out) and out["hookSpecificOutput"]["permissionDecision"] == "deny"


DASH = "H:/dashboards/views/energy.yaml"
DOC = "H:/docs/dashboards.md"
HOOK = HOME + "/.claude/hooks/x.py"


def run():
    # ---- area(): which paths are guarded ----
    A = {
        "H:/dashboards/views/a.yaml": "dashboards",
        "H:\\dashboards\\views\\a.yaml": "dashboards",
        "/h/dashboards/cards/x.yaml": "dashboards",
        "//10.0.0.210/config/dashboards/views/a.yaml": "dashboards",
        "\\\\10.0.0.210\\config\\dashboards\\x.yaml": "dashboards",
        "H:/dashboards/lovelace/x.yaml": None,  # ha_guard.py walls it
        "H:/packages/x.yaml": None,
        "H:/docs/dashboards.md": None,  # the doc itself is not guarded
        "C:/sandbox/doc_guard/doc_guard.py": None,
        HOME + "/.claude/hooks/x.py": "hooks",
        "C:\\fakehome\\.claude\\settings.json": "hooks",
        "/c/fakehome/.claude/settings.local.json": "hooks",
        HOME + "/.claude/settings.json.bak": None,
        HOME + "/.claude/agents/x.md": None,
        "C:/repos/x/.claude/settings.json": None,
        "C:/repos/x/.claude/hooks/y.py": None,
        "H:/.claude/hooks/x.py": "hooks",
        "H:/.claude/settings.json": "hooks",
    }
    for p, want in A.items():
        check("area %s -> %s" % (p, want), g.area(p, HOME) == want)

    t = T()
    # 1. not read -> deny once, naming the doc; the repeat runs
    tp = t.transcript(use("Read", file_path="H:/packages/x.yaml"))
    out = t.edit(DASH, tp)
    check("1 deny when doc unread", denied(out))
    check(
        "1 reason names the doc",
        denied(out) and DOC in out["hookSpecificOutput"]["permissionDecisionReason"],
    )
    check("1 repeat runs", t.edit(DASH, tp) is None)
    check(
        "1 log deny + allow-repeat",
        "\tdeny\tdashboards\t" in t.log() and "\tallow-repeat\tdashboards\t" in t.log(),
    )

    # 2-3. Read (backslash path), Bash, Grep, PowerShell all count as reading
    for i, ln in enumerate(
        [
            use("Read", file_path="H:\\docs\\dashboards.md"),
            use("Bash", command="cat /h/docs/dashboards.md | head"),
            use("Grep", pattern="lovelace", path=DOC),
            use("Bash", command="cd /h && sed -n '1,40p' docs/dashboards.md"),
            use("PowerShell", command="Get-Content H:\\docs\\dashboards.md -Total 40"),
        ]
    ):
        check(
            "2 reader %d counts" % i,
            t.edit(DASH, t.transcript(ln), sid="r%d" % i) is None,
        )
    check("2 log allow-read", "\tallow-read\tdashboards\t" in t.log())

    # 4-5. a read before the last compaction does not count; one after does
    check(
        "4 read before compaction -> deny",
        denied(
            t.edit(
                DASH, t.transcript(use("Read", file_path=DOC), boundary("b1")), sid="c4"
            )
        ),
    )
    check(
        "5 read after compaction -> run",
        t.edit(DASH, t.transcript(boundary("b1"), use("Read", file_path=DOC)), sid="c5")
        is None,
    )

    # 6-8. what does NOT count as reading the doc
    check(
        "6 doc named only in a tool_result -> deny",
        denied(
            t.edit(DASH, t.transcript(result("see H:/docs/dashboards.md")), sid="c6")
        ),
    )
    check(
        "7 Write of the doc is not a read -> deny",
        denied(
            t.edit(
                DASH, t.transcript(use("Write", file_path=DOC, content="x")), sid="c7"
            )
        ),
    )
    check(
        "8 Read of a dashboards file is not the doc -> deny",
        denied(t.edit(DASH, t.transcript(use("Read", file_path=DASH)), sid="c8")),
    )
    check(
        "8b doc name as a Grep pattern is not a read -> deny",
        denied(
            t.edit(
                DASH,
                t.transcript(
                    use("Grep", pattern="docs/dashboards.md", path="H:/CLAUDE.md")
                ),
                sid="c8b",
            )
        ),
    )
    # 8c: the first live run's false accept - a one-liner quoting the bare name
    check(
        "8c bare doc name in a Bash command is not a read -> deny",
        denied(
            t.edit(
                DASH,
                t.transcript(use("Bash", command="python -c \"f('dashboards.md')\"")),
                sid="c8c",
            )
        ),
    )
    check(
        "8c2 another file named *dashboards.md is not the doc -> deny",
        denied(
            t.edit(
                DASH,
                t.transcript(use("Read", file_path="H:/dashboards/old_dashboards.md")),
                sid="c8c2",
            )
        ),
    )
    # 8d-8h: the second live run's false accept - shell text that only QUOTES the
    # doc. A heredoc body is data, and the doc must follow a read verb in the same
    # pipeline segment
    for tag, cmd in [
        (
            "8d heredoc body",
            "cat > x.md <<'EOF'\nnext: grep -n x docs/dashboards.md\nEOF",
        ),
        ("8e echo", 'echo "see docs/dashboards.md" >> x.md'),
        ("8f python heredoc", "python - <<'EOF'\nopen('H:/docs/dashboards.md')\nEOF"),
        ("8g verb in another ; segment", "cat a.txt; echo docs/dashboards.md"),
        ("8h verb on another line", "cat a.txt\necho docs/dashboards.md"),
    ]:
        check(
            tag + " is not a read -> deny",
            denied(
                t.edit(DASH, t.transcript(use("Bash", command=cmd)), sid="c" + tag[:2])
            ),
        )

    # 9-10. things that look like a boundary but are not one
    quoted = result('{"type":"system","subtype":"compact_boundary"}')
    check(
        "9 quoted boundary is not a boundary",
        t.edit(DASH, t.transcript(use("Read", file_path=DOC), quoted), sid="c9")
        is None,
    )
    rawkey = use("Bash", command="echo", subtype="compact_boundary")
    check(
        "10 raw-key lookalike is not a boundary",
        t.edit(DASH, t.transcript(use("Read", file_path=DOC), rawkey), sid="c10")
        is None,
    )

    # 11. deny once per compaction: a new boundary re-arms it
    lines = [use("Read", file_path="H:/x")]
    tp = t.transcript(*lines)
    check("11 first -> deny", denied(t.edit(DASH, tp, sid="c11")))
    check("11 repeat -> run", t.edit(DASH, tp, sid="c11") is None)
    tp2 = t.transcript(*(lines + [boundary("b2")]))
    check("11 after a compaction -> deny again", denied(t.edit(DASH, tp2, sid="c11")))
    check("11 and its repeat runs", t.edit(DASH, tp2, sid="c11") is None)

    # 12-13. state is per area and per session
    tp = t.transcript(use("Read", file_path="H:/x"))
    t.edit(DASH, tp, sid="c12")
    check("12 other area still denied", denied(t.edit(HOOK, tp, sid="c12")))
    check("13 other session still denied", denied(t.edit(DASH, tp, sid="c13")))

    # 14. no transcript -> deny once (logged), then run
    missing = os.path.join(t.d, "nope.jsonl")
    check("14 missing transcript -> deny", denied(t.edit(DASH, missing, sid="c14")))
    check("14 repeat runs", t.edit(DASH, missing, sid="c14") is None)
    check("14 logged", "\tdeny-no-transcript\tdashboards\t" in t.log())
    check("14 None transcript -> deny", denied(t.edit(DASH, None, sid="c14b")))

    # 15-16. tool scope
    tp = t.transcript()
    check(
        "15 Read of a guarded path is not policed",
        t.edit(DASH, tp, sid="c15", tool="Read") is None,
    )
    check(
        "15 NotebookEdit is policed",
        denied(t.edit("H:/dashboards/x.ipynb", tp, sid="c15n", tool="NotebookEdit")),
    )
    check(
        "16 lovelace left to ha_guard",
        t.edit("H:/dashboards/lovelace/a.yaml", tp, sid="c16") is None,
    )

    # 17. hooks area: a partial Read of the enforcement doc counts
    tp = t.transcript(
        use(
            "Read", file_path="H:/docs/claude-code-enforcement.md", offset=300, limit=40
        )
    )
    check(
        "17 enforcement doc read -> hook edit runs", t.edit(HOOK, tp, sid="c17") is None
    )
    check(
        "17 settings edit runs",
        t.edit(HOME + "/.claude/settings.json", tp, sid="c17") is None,
    )
    check(
        "17 unread -> settings edit denied",
        denied(t.edit(HOME + "/.claude/settings.json", t.transcript(), sid="c17b")),
    )

    # 18. prune: old doc_guard state goes, fresh state and other hooks' state stay
    old = os.path.join(t.state, "doc_guard_old.json")
    other = os.path.join(t.state, "read_guard_old.json")
    for p in (old, other):
        with open(p, "w") as fh:
            fh.write("[]")
        os.utime(p, (time.time() - 8 * 86400,) * 2)
    t.edit(DASH, t.transcript(), sid="c18")
    check("18 old state pruned", not os.path.exists(old))
    check("18 other hook state kept", os.path.exists(other))
    check("18 fresh state kept", os.path.exists(g._state_path(t.state, "c18")))

    # 19-21. main(): output, fail-open, error log
    payload = json.dumps(
        {
            "session_id": "m19",
            "transcript_path": t.transcript(),
            "tool_name": "Edit",
            "tool_input": {"file_path": DASH},
        }
    )
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = g.main(io.StringIO(payload), t.state)
    check("19 main prints a deny", rc == 0 and denied(json.loads(buf.getvalue())))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = g.main(io.StringIO("{not json"), t.state)
    check("20 bad stdin -> exit 0, silent", rc == 0 and buf.getvalue() == "")
    check("20 error logged", "\terror\t" in t.log())
    blocker = os.path.join(t.d, "afile")
    with open(blocker, "w") as fh:
        fh.write("x")
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = g.main(io.StringIO(payload), blocker)
        check(
            "21 unusable state dir -> exit 0, silent", rc == 0 and buf.getvalue() == ""
        )
    except Exception as exc:
        check("21 unusable state dir raised %s" % type(exc).__name__, False)

    # 22. as a script, the way the launcher runs it
    env = dict(os.environ, DOC_GUARD_STATE=os.path.join(t.d, "sub"))
    payload = json.dumps(
        {
            "session_id": "s22",
            "transcript_path": t.transcript(),
            "tool_name": "Edit",
            "tool_input": {"file_path": DASH},
        }
    )
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "doc_guard.py")],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
    )
    check("22 script exit 0", r.returncode == 0)
    check("22 script prints a deny", r.stdout.strip() and denied(json.loads(r.stdout)))


if __name__ == "__main__":
    run()
    print("ALL PASSED" if not FAILS else "%d FAILED" % len(FAILS))
    sys.exit(1 if FAILS else 0)
