"""Tests for read_guard.py. Run: python test_read_guard.py -> "ALL PASSED".

Mutations: python mutate_read_guard.py -> "11/11 caught"."""

import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import read_guard as rg  # noqa: E402

T = rg.THRESHOLD
FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print("FAIL", name)


def mk(d, name, size):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("x" * size)
    return p


def read(path, sid="s1", **kw):
    ti = {"file_path": path}
    ti.update(kw)
    return {"tool_name": "Read", "session_id": sid, "tool_input": ti}


def denied(out):
    return bool(out) and out["hookSpecificOutput"]["permissionDecision"] == "deny"


def run():
    root = tempfile.mkdtemp()
    st = os.path.join(root, "state")
    try:
        small = mk(root, "small.md", 100)
        edge = mk(root, "edge.md", T)
        over = mk(root, "over.md", T + 1)
        big = mk(root, "Big.md", 3 * T)
        png = mk(root, "pic.png", 3 * T)

        check("small allowed", rg.decide(read(small), st) is None)
        check("size == threshold allowed", rg.decide(read(edge), st) is None)
        check("threshold+1 denied", denied(rg.decide(read(over), st)))

        out = rg.decide(read(big), st)
        check("big denied", denied(out))
        check(
            "reason names size",
            "60 KB" in out["hookSpecificOutput"]["permissionDecisionReason"],
        )
        check("repeat allowed", rg.decide(read(big), st) is None)
        check("other session denied", denied(rg.decide(read(big, sid="s2"), st)))

        big2 = mk(root, "Big2.md", 3 * T)
        check("first big2 denied", denied(rg.decide(read(big2, sid="s3"), st)))
        flipped = big2.replace("\\", "/").upper() if os.name == "nt" else big2
        check(
            "same file other spelling = repeat",
            rg.decide(read(flipped, sid="s3"), st) is None,
        )

        for k, v in (("limit", 50), ("offset", 10), ("pages", "1-2"), ("limit", 0)):
            check(
                "partial %s=%r allowed" % (k, v),
                rg.decide(read(big, sid="s4", **{k: v}), st) is None,
            )
        check(
            "partial did not consume the deny",
            denied(rg.decide(read(big, sid="s4"), st)),
        )

        check("png allowed", rg.decide(read(png, sid="s5"), st) is None)
        check(
            "missing allowed",
            rg.decide(read(os.path.join(root, "nope.md"), sid="s5"), st) is None,
        )
        check(
            "no path allowed",
            rg.decide({"tool_name": "Read", "tool_input": {}}, st) is None,
        )
        check(
            "other tool allowed",
            rg.decide(
                {
                    "tool_name": "Grep",
                    "session_id": "s5",
                    "tool_input": {"file_path": big},
                },
                st,
            )
            is None,
        )

        log = open(os.path.join(st, rg.LOG_FILE), encoding="utf-8").read()
        check("deny logged", "\tdeny\t" in log)
        check("repeat logged", "\tallow-repeat\t" in log)

        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = rg.main(io.StringIO(json.dumps(read(big, sid="s6"))), st)
        finally:
            sys.stdout = old
        check("main deny rc 0", rc == 0)
        check("main prints deny json", denied(json.loads(buf.getvalue())))

        buf = io.StringIO()
        sys.stdout = buf
        try:
            rc = rg.main(io.StringIO("not json"), st)
        finally:
            sys.stdout = old
        check("garbage stdin rc 0", rc == 0)
        check("garbage stdin no output", buf.getvalue() == "")
        check(
            "garbage stdin logged as error",
            "\terror\t" in open(os.path.join(st, rg.LOG_FILE), encoding="utf-8").read(),
        )

        # Unwritable state dir: fail open (no output, rc 0).
        blocker = mk(root, "blocker", 1)  # a FILE where the state dir should be
        buf = io.StringIO()
        sys.stdout = buf
        try:
            rc = rg.main(
                io.StringIO(json.dumps(read(big, sid="s7"))),
                os.path.join(blocker, "state"),
            )
        finally:
            sys.stdout = old
        check("bad state dir rc 0", rc == 0)
        check("bad state dir no deny", buf.getvalue() == "")

        # Pruning: an old state file goes, a fresh one stays.
        oldf = os.path.join(st, "read_guard_old.json")
        with open(oldf, "w") as fh:
            fh.write("[]")
        os.utime(oldf, (0, 0))
        rg.decide(read(big, sid="s8"), st)
        check("old state pruned", not os.path.exists(oldf))
        check("fresh state kept", os.path.exists(rg._state_path(st, "s8")))
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    run()
    print("ALL PASSED" if not FAILS else "%d FAILED" % len(FAILS))
    sys.exit(1 if FAILS else 0)
