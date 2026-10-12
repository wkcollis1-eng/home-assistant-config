"""Tests for bash_guard.py, both directions (R7). Run: python test_bash_guard.py
-> "ALL PASSED (N checks)". BASH_GUARD_MODULE=<path> tests another copy (mutation runs)."""

import importlib.util
import io
import json
import os
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "bash_guard",
    os.environ.get("BASH_GUARD_MODULE") or os.path.join(here, "bash_guard.py"),
)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

BS = "\\"
checks = 0


def check(name, cond):
    global checks
    checks += 1
    if not cond:
        print("FAIL:", name)
        sys.exit(1)


def bash(cmd):
    return {
        "session_id": "test-sid-0001",
        "tool_name": "Bash",
        "tool_input": {"command": cmd},
    }


with tempfile.TemporaryDirectory() as d:
    fire = [
        "printf '%s' 'a" + BS * 2 + "b'",  # single quotes
        "python - <<'EOF'\nx = 'a"
        + BS * 2
        + "n'\nEOF",  # quoted heredoc (the 2026-10-11 slip)
        "echo " + BS * 4,  # four in a row
        'grep "' + BS * 2 + '." f',  # double quotes
    ]
    for cmd in fire:
        out = g.decide(bash(cmd), d)
        check(
            "deny %r" % cmd,
            bool(out) and out["hookSpecificOutput"]["permissionDecision"] == "deny",
        )
        check(
            "reason names Write %r" % cmd,
            "Write" in out["hookSpecificOutput"]["permissionDecisionReason"],
        )
    silent = [
        "ls -la",
        "python -c \"print(b'"
        + BS
        + "r"
        + BS
        + "n')\"",  # lone backslashes: safe [M p=0.65]
        "echo a" + BS + " b",
        "sed -n '1,5p' f",
        "",
    ]
    for cmd in silent:
        check("allow %r" % cmd, g.decide(bash(cmd), d) is None)
    check(
        "non-Bash tool ignored",
        g.decide({"tool_name": "Read", "tool_input": {"command": "a" + BS * 2}}, d)
        is None,
    )
    check("missing tool_input", g.decide({"tool_name": "Bash"}, d) is None)
    check(
        "null command",
        g.decide({"tool_name": "Bash", "tool_input": {"command": None}}, d) is None,
    )

    for stdin, want in [
        (json.dumps(bash("echo " + BS * 2)), "deny"),
        (json.dumps(bash("ls")), None),
        ("not json", None),
    ]:
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            rc = g.main(io.StringIO(stdin), d)
        finally:
            sys.stdout = old
        check("main exit 0 %r" % stdin[:20], rc == 0)
        o = buf.getvalue().strip()
        if want:
            check(
                "main prints deny JSON",
                json.loads(o)["hookSpecificOutput"]["permissionDecision"] == "deny",
            )
        else:
            check("main prints nothing %r" % stdin[:20], o == "")

    log = open(os.path.join(d, g.LOG_FILE), encoding="utf-8").read().splitlines()
    check(
        "5 denies logged",
        sum(1 for x in log if x.split("\t")[2] == "deny") == len(fire) + 1,
    )
    check(
        "1 error logged (fail-open is not silent, R8)",
        sum(1 for x in log if x.split("\t")[2] == "error") == 1,
    )
    check("one line per event, 5 fields", all(x.count("\t") == 4 for x in log))
    check(
        "multi-line command logged on one line",
        any("python - <<'EOF' x =" in x for x in log),
    )

print("ALL PASSED (%d checks)" % checks)
