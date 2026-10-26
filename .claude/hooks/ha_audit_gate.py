#!/usr/bin/env python
"""Run ha_audit.py at session start, and again after any turn that touched H:.

WHY THIS EXISTS. CLAUDE.md's SESSION PROTOCOL says to run the audit at the
start of every session and again before saying you are done, and that "an audit
you did not read is an audit that did not run for you." That made compliance a
matter of the model remembering. This makes it the harness's job.

  sessionstart  always runs, injects the verdict into context, and writes
                this session's finding baseline (ha_audit.py --baseline).
  stop          runs ONLY if something under H: changed since the last run,
                and BLOCKS on any FAIL, or on a WARN that was not there at
                session start. With no baseline, on any WARN (fails closed).

WHAT CHANGED 2026-08-25, and why it mattered
--------------------------------------------
1. STOP CAN NOW ACTUALLY STOP. It only ever emitted `systemMessage`, which
   prints and lets the turn end. CLAUDE.md's enforcement table calls this "the
   backstop, because it catches the consequence however the edit was made" -
   and a write through Bash bypasses the PreToolUse guard, so this was the only
   thing standing behind it. It could not stop anything. Blocking on Stop needs
   top-level {"decision": "block", "reason": ...}.

2. IT NO LONGER FAILS OPEN IN SILENCE. `if not os.path.exists(AUDIT): return`
   meant a missing H: produced no message at all, directly contradicting
   CLAUDE.md: "If ha_audit.py cannot run at all, say so and stop. Working blind
   on a live house is not a thing to do quietly."

   WHERE THIS FILE MUST LIVE, and it is not obvious. It was briefly moved to
   H:/.claude/hooks/ so it would be version-controlled with the config it
   guards. That made the message above UNREACHABLE: if H: is unmounted, python
   cannot open this script at all, exits before a line of it runs, and Claude
   Code treats that as a non-blocking error - so the session starts in silence,
   which is the exact failure the message exists to prevent. A guard that lives
   on the drive it is guarding cannot report that drive missing. It therefore
   runs from C:/Users/wkcol/.claude/hooks/ (local, always startable), with
   H:/.claude/hooks/ as the tracked source. deploy_drift() below compares
   every deployed hook with its tracked copy at every session start, so the
   pair cannot silently diverge.

3. THE WATCH LIST INCLUDES dashboards/. It was root *.yaml, packages/*.yaml,
   scripts/*.py and *.md - so editing dashboards/views/*.yaml never moved
   newest() and the gate silently skipped, on the one surface CLAUDE.md calls
   "the one place a broken entity is completely silent". P12 was that class.

WHAT CHANGED 2026-10-11, and why
--------------------------------
4. STOP BLOCKS ON WHAT THE SESSION ADDED, NOT ON WHAT IT INHERITED. It blocked
   on any WARN, while DEFINITION OF DONE step 2 says "WARN count must not
   rise". Over 30 d it blocked 105 times in 44 sessions and 85 of those named
   only the standing open-question WARN [M, transcripts, stop_blocks.py in
   C:/sandbox/token_replay] - a WARN that waits on Bill and that no session can
   fix, so each was a forced extra turn that taught waving blocks through
   (R7). Session start now runs ha_audit.py --baseline (one run: --log keeps
   the human report), and Stop compares against that file, so the comparison
   lives in ha_audit.py once (R10), day-count churn included. Any FAIL still
   blocks, baselined or not. A missing or unreadable baseline blocks as before.

WHAT CHANGED 2026-10-26, and why
--------------------------------
5. SESSION START ALSO SIZES MEMORY.md (memory_index_size). The index loads
   into every session. It was trimmed 7,275 -> 4,783 B on 10-11, crept back to
   6,846 B by 10-26 with 18 of 39 lines over 170 chars, and was re-trimmed to
   5,803 B / longest line 167 that day [M]. Nothing watched the creep. Here,
   not in ha_audit.py: the nightly host run has no memory dir. Spec and proof:
   C:/sandbox/memory_check (DESIGN.md, test_memory_index_size.py).

LOOP SAFETY. A blocking Stop hook that keeps blocking would wedge the session,
and the original docstring's "a broken gate must never wedge a session" still
holds. After MAX_BLOCKS consecutive blocks the gate downgrades itself to a
message and lets the turn end, saying so.
"""

import glob
import json
import os
import re
import subprocess
import sys
import time

CONFIG = os.environ.get("HA_GATE_CONFIG", "H:/")
URL = os.environ.get("HA_GATE_URL", "http://10.0.0.210:8123")
AUDIT = os.environ.get("HA_GATE_AUDIT", CONFIG.rstrip("/") + "/scripts/ha_audit.py")
STAMP = os.environ.get(
    "HA_GATE_STAMP",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ha_audit_stamp"),
)
STATE = os.environ.get(
    "HA_GATE_STATE", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".state")
)
MAX_BLOCKS = 2
BASELINE_DAYS = 30
# MEMORY.md caps. 170 chars/line: the 10-26 trim brought every line to <= 167, and
# the lines above 170 were the ones carrying facts [M]. 6,500 B is a budget, not a
# measurement (~5 lines over 5,803 B): when it fires, merge or delete memories,
# do not raise it silently. The hard line is under the loader's limit, "the first
# 200 lines or 25KB" [S: code.claude.com/docs/en/memory.md:547]; past that,
# memories silently stop loading.
MEM_LINE_MAX = 170
MEM_TOTAL_MAX = 6500
MEM_HARD_LINES = 180
MEM_HARD_BYTES = 22500
# Used only when the hook input has no transcript_path.
MEM_FALLBACK = os.environ.get(
    "HA_GATE_MEMORY",
    os.path.join(
        os.path.expanduser("~"),
        ".claude",
        "projects",
        "C--Users-wkcol",
        "memory",
        "MEMORY.md",
    ),
)
_root = CONFIG.rstrip("/")
WATCH = [
    _root + "/*.yaml",
    _root + "/*.md",
    _root + "/packages/*.yaml",
    _root + "/scripts/*.py",
    _root + "/dashboards/*.yaml",
    _root + "/dashboards/*/*.yaml",
    _root + "/dashboards/*/*/*.yaml",
    _root + "/esphome/*.yaml",
]


def newest():
    t = 0.0
    for pat in WATCH:
        for p in glob.glob(pat):
            try:
                t = max(t, os.path.getmtime(p))
            except OSError:
                pass
    return t


def read_stamp():
    """(mtime, consecutive_blocks)."""
    try:
        with open(STAMP) as fh:
            parts = fh.read().strip().split("|")
        return float(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except (IOError, OSError, ValueError, IndexError):
        return 0.0, 0


def write_stamp(mtime, blocks=0):
    """True if the stamp was persisted.

    THE WEDGE (found 2026-08-25, before this ever ran). This used to swallow
    the failure. The block counter lives in that file, so if it could not be
    written - read-only dir, H: dropped, antivirus lock - `blocks` would reset
    to 0 on every read, MAX_BLOCKS would never be reached, and the Stop gate
    would block the session forever. That is precisely the outcome this
    script's own docstring promises never to cause. The caller now refuses to
    block when it cannot remember that it did.
    """
    try:
        with open(STAMP, "w") as fh:
            fh.write("%s|%d" % (mtime, blocks))
        return True
    except (IOError, OSError):
        return False


def run_audit(*extra):
    env = dict(os.environ, HA_CONFIG=CONFIG, HA_URL=URL)
    try:
        r = subprocess.run(
            [sys.executable, AUDIT] + list(extra),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return None, "ha_audit could not run: %s" % e
    return ((r.stdout or "") + (r.stderr or "")).strip(), None


def verdict_line(out):
    for line in reversed(out.splitlines()):
        if "FAIL," in line and "WARN," in line:
            return line.strip()
    return out.splitlines()[-1].strip() if out.splitlines() else "(no output)"


def emit(obj):
    json.dump(obj, sys.stdout)


_INPUT = None


def hook_input():
    """The hook's stdin JSON as a dict, {} if none. Read once and kept: stdin can
    be read only once, and session_id() and memory_index_path() both need it."""
    global _INPUT
    if _INPUT is None:
        _INPUT = {}
        try:
            if sys.stdin is not None and not sys.stdin.isatty():
                data = json.load(sys.stdin)
                if isinstance(data, dict):
                    _INPUT = data
        except (ValueError, OSError):
            pass
    return _INPUT


def session_id():
    """This session's id from the hook's stdin JSON, filename-safe; '' if none."""
    sid = hook_input().get("session_id")
    return re.sub(r"[^A-Za-z0-9_-]", "", str(sid or ""))[:80]


def baseline_path(sid):
    """Per session, so two concurrent sessions never compare against each other."""
    return os.path.join(STATE, "audit_baseline_%s.json" % sid) if sid else ""


def prune_baselines():
    cutoff = time.time() - BASELINE_DAYS * 86400
    for p in glob.glob(os.path.join(STATE, "audit_baseline_*")):
        try:
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
        except OSError:
            pass


NO_BASELINE = (
    "\n\nNO STOP-GATE BASELINE for this session (%s): the Stop gate "
    "will block on EVERY WARN, inherited ones included, as it did "
    "before 2026-10-11."
)


def start_audit(base):
    """(report, err, note): one audit run that also writes this session's baseline.

    One run, not two: in --baseline mode ha_audit.py prints only the delta, so
    --log captures the human report from the same run. A second run would add
    7.4 s to every session start [M, n=1, live, 2026-10-11].
    """
    if not base:
        out, err = run_audit()
        return out, err, NO_BASELINE % "the hook got no session id"
    log = base + ".log"
    try:
        os.makedirs(STATE, exist_ok=True)
        for p in (base, log):
            if os.path.exists(p):
                os.remove(p)
    except OSError as e:
        out, err = run_audit()
        return out, err, NO_BASELINE % ("state dir not writable: %s" % e)
    out, err = run_audit("--baseline", base, "--log", log)
    if err:
        return out, err, ""
    report = ""
    try:
        with open(log, encoding="utf-8") as fh:
            report = re.sub(r"\A\s*=+ .* =+\n", "", fh.read()).strip()
        os.remove(log)
    except OSError:
        pass
    note = "" if os.path.exists(base) else NO_BASELINE % "ha_audit.py did not write it"
    if not report:
        # It stopped before reporting (e.g. pipelines.yaml not found): its own
        # words are the report.
        return out, None, note
    extra = [
        ln
        for ln in out.splitlines()
        if ln.strip()
        and not ln.startswith("BASELINE WRITTEN")
        and ln.strip() not in report
    ]
    return "\n".join([report] + extra), None, note


def deploy_drift():
    """A one-line warning naming every drifted deployed hook, else ''.

    The deployed hooks on C: and the tracked hooks under H:/.claude/hooks/ are
    meant to be byte-identical. Nothing else checks that, and a stale deployed
    hook is a guard that silently enforces last month's rules. Checks every
    *.py beside this file. Until 2026-09-16 it compared only itself, so drift
    in ha_guard.py, ha_validate_edit.py or context_hygiene.py was invisible and
    a hook with no tracked copy at all passed; test_deploy_drift.py reproduces
    that against the old version. Silent when all match, silent when the repo
    hooks dir is unreachable (that case is already reported far more loudly by
    the audit itself).
    """
    here = os.path.dirname(os.path.abspath(__file__))
    # Not os.path.join(CONFIG.rstrip("/"), ...): for "H:/" that gives "H:.claude",
    # which is relative to H:'s current directory, not its root (found and
    # fixed 2026-09-16, present since the check was written). Same idiom as AUDIT.
    repo = CONFIG.rstrip("/") + "/.claude/hooks"
    try:
        if not os.path.isdir(repo) or os.path.normcase(
            os.path.abspath(repo)
        ) == os.path.normcase(here):
            return ""
        drift = []
        for path in sorted(glob.glob(os.path.join(here, "*.py"))):
            name = os.path.basename(path)
            tracked = os.path.join(repo, name)
            if not os.path.exists(tracked):
                drift.append("%s (no tracked copy)" % name)
                continue
            with open(path, "rb") as a, open(tracked, "rb") as b:
                if a.read() != b.read():
                    drift.append("%s (differs)" % name)
    except OSError:
        return ""
    if not drift:
        return ""
    return (
        "\n\nHOOK DEPLOY DRIFT: %s - running hooks in %s against the tracked "
        "copies in %s. One side is stale - re-copy before trusting what the "
        "hooks enforce." % (", ".join(drift), here, repo)
    )


def memory_index_path():
    """This project's MEMORY.md: <transcript dir>/memory/MEMORY.md, as Claude Code
    lays it out, so a session started from another project checks its own index."""
    tp = hook_input().get("transcript_path")
    if tp:
        return os.path.join(os.path.dirname(str(tp)), "memory", "MEMORY.md")
    return MEM_FALLBACK


def memory_index_size(path=None):
    """A warning naming what is over the MEMORY.md caps, else ''.

    Never raises (R8): any failure is one DID NOT RUN line, because a check that
    could not look must not read like one that found nothing.
    """
    try:
        path = path or memory_index_path()
        with open(path, "rb") as fh:
            raw = fh.read()
        rows = raw.decode("utf-8-sig", errors="replace").split("\n")
        if rows and rows[-1] == "":
            rows.pop()  # the final newline ends a line, it does not start one
        size, n = len(raw), len(rows)
        long = [
            (i, len(r.rstrip("\r")))
            for i, r in enumerate(rows, 1)
            if len(r.rstrip("\r")) > MEM_LINE_MAX
        ]
        hard = n >= MEM_HARD_LINES or size >= MEM_HARD_BYTES
        if not (hard or long or size > MEM_TOTAL_MAX):
            return ""
        named = ", ".join("L%d (%d)" % x for x in long[:15]) or "none"
        if len(long) > 15:
            named += " (+%d more)" % (len(long) - 15)
        fix = []
        if size > MEM_TOTAL_MAX or hard:
            fix.append(
                "merge or delete memories, stale project memories first - do not "
                "raise the budget silently"
            )
        if long:
            fix.append(
                "move the fact into the topic file, keep a pointer + trigger "
                "(memtrim pattern)"
            )
        msg = "MEMORY INDEX OVER BUDGET: {:,} B (budget {:,}), {} lines; lines > {} chars: {} - {}.".format(
            size, MEM_TOTAL_MAX, n, MEM_LINE_MAX, named, "; ".join(fix)
        )
        if hard:
            msg = (
                "MEMORY INDEX NEAR THE LOADER LIMIT: {} lines / {:,} B. Claude Code "
                "loads only the first 200 lines or 25 KB of MEMORY.md; past that, "
                "memories silently stop loading. Cut it in this session. ".format(
                    n, size
                )
                + msg
            )
        return "\n\n" + msg
    except Exception as e:  # fail open, never silently (R8)
        return (
            "\n\nMEMORY INDEX CHECK DID NOT RUN: %s: %s - fix memory_index_size() in "
            "ha_audit_gate.py, or the path it was given." % (type(e).__name__, e)
        )


def missing_audit_message():
    return (
        'HA CONFIG AUDIT DID NOT RUN: %s does not exist. CLAUDE.md: "If '
        "ha_audit.py cannot run at all, say so and stop. Working blind on a "
        'live house is not a thing to do quietly." Check that H: is mounted.' % AUDIT
    )


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "sessionstart").lower()

    if mode == "stop":
        if not os.path.exists(AUDIT):
            emit({"systemMessage": missing_audit_message()})
            return
        mtime, blocks = read_stamp()
        if newest() <= mtime:
            return
        base = baseline_path(session_id())
        have_base = bool(base) and os.path.exists(base)
        out, err = run_audit("--baseline", base) if have_base else run_audit()
        if err:
            write_stamp(newest(), 0)
            emit({"systemMessage": "HA audit gate: %s" % err})
            return
        v = verdict_line(out)
        if have_base:
            # ha_audit.py prints only the delta here: NEW/FIXED lines and
            # "N NEW, N FIXED, N UNCHANGED". No such line = the comparison did
            # not run (unreadable baseline, crash) - not clean, block.
            m = re.search(r"^(\d+) NEW, \d+ FIXED", out, re.M)
            # Finding lines only: ha_audit.py's closing "NEW findings block ...
            # re-baseline DELIBERATELY" advice would invite silencing this gate.
            new = [
                ln for ln in out.splitlines() if re.match(r"NEW\s+(FAIL|WARN)\s", ln)
            ]
            clean = bool(m) and m.group(1) == "0" and v.startswith("0 FAIL")
            bad = new or [
                ln for ln in out.splitlines() if ln.startswith(("FAIL", "WARN"))
            ]
            if not m and "BASELINE WRITTEN" in out:
                # The file vanished between exists() and the run, so ha_audit.py
                # wrote a new one from the CURRENT tree - which would bless
                # whatever this session added. Remove it, so the later stops
                # fall back to blocking on every WARN.
                try:
                    os.remove(base)
                except OSError:
                    pass
                bad = [
                    "(the session baseline vanished before the comparison; "
                    "the one ha_audit.py just wrote from the current tree was "
                    "removed, so this session now blocks on every WARN)"
                ]
            if not bad and m and not v.startswith("0 FAIL"):
                bad = [
                    "(no NEW finding, but a FAIL already there at session "
                    "start still blocks - FAIL is never baselined. The "
                    "session-start report names it.)"
                ]
            how = (
                "Compared with this session's start (ha_audit.py "
                "--baseline %s):\n" % base
            )
        else:
            clean = v.startswith("0 FAIL") and " 0 WARN," in v
            bad = [ln for ln in out.splitlines() if ln.startswith(("FAIL", "WARN"))]
            how = (
                "No session-start baseline for this session, so every WARN "
                "blocks, inherited ones included:\n"
            )
        if clean:
            write_stamp(newest(), 0)
            return
        if blocks >= MAX_BLOCKS:
            write_stamp(newest(), 0)
            emit(
                {
                    "systemMessage": "HA CONFIG GATE: still not clean after %d blocked stops - "
                    "letting the turn end so the session is not wedged. UNRESOLVED:\n%s\n%s"
                    % (MAX_BLOCKS, "\n".join(bad[:12]), v)
                }
            )
            return
        if not write_stamp(newest(), blocks + 1):
            # Cannot persist the block count, so cannot guarantee this ever
            # stops. Speak instead of blocking - a gate that cannot count its
            # own retries has no business holding the session open.
            emit(
                {
                    "systemMessage": "HA CONFIG GATE: audit is not clean, but the gate stamp (%s) "
                    "could not be written, so the retry count cannot be tracked. "
                    "NOT blocking, to avoid wedging the session. UNRESOLVED:\n%s\n%s"
                    % (STAMP, "\n".join(bad[:12]), v)
                }
            )
            return
        emit(
            {
                "decision": "block",
                "reason": "H: changed this turn and ha_audit.py is not clean. Fix "
                "these before finishing, or say explicitly what you are "
                "leaving open and why (CLAUDE.md OUTPUT FORMAT):\n"
                + how
                + "\n".join(bad[:12])
                + "\n"
                + v,
            }
        )
        return

    # ---- session start --------------------------------------------------
    if not os.path.exists(AUDIT):
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": missing_audit_message(),
                }
            }
        )
        return
    prune_baselines()
    out, err, note = start_audit(baseline_path(session_id()))
    write_stamp(newest(), 0)
    if err:
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": "HA CONFIG AUDIT could not run: %s\nCLAUDE.md: if ha_audit.py "
                    "cannot run at all, say so and stop. Working blind on a live "
                    "house is not a thing to do quietly." % err,
                }
            }
        )
        return
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "HA CONFIG AUDIT (ran automatically per CLAUDE.md SESSION PROTOCOL).\n"
                "Read this verdict aloud in your first message and name every FAIL "
                "and WARN:\n\n" + out + note + deploy_drift() + memory_index_size(),
            }
        }
    )


if __name__ == "__main__":
    main()
