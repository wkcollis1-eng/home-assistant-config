#!/usr/bin/env python
"""Run ha_audit.py at session start, and again after any turn that touched H:.

WHY THIS EXISTS. CLAUDE.md's SESSION PROTOCOL says to run the audit at the
start of every session and again before saying you are done, and that "an audit
you did not read is an audit that did not run for you." That made compliance a
matter of the model remembering. This makes it the harness's job.

  sessionstart  always runs, injects the verdict into context.
  stop          runs ONLY if something under H: changed since the last run,
                and BLOCKS on FAIL/WARN.

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

LOOP SAFETY. A blocking Stop hook that keeps blocking would wedge the session,
and the original docstring's "a broken gate must never wedge a session" still
holds. After MAX_BLOCKS consecutive blocks the gate downgrades itself to a
message and lets the turn end, saying so.
"""
import glob
import json
import os
import subprocess
import sys

CONFIG = os.environ.get("HA_GATE_CONFIG", "H:/")
URL = os.environ.get("HA_GATE_URL", "http://10.0.0.210:8123")
AUDIT = os.environ.get("HA_GATE_AUDIT", CONFIG.rstrip("/") + "/scripts/ha_audit.py")
STAMP = os.environ.get(
    "HA_GATE_STAMP",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ha_audit_stamp"))
MAX_BLOCKS = 2
_root = CONFIG.rstrip("/")
WATCH = [_root + "/*.yaml", _root + "/*.md",
         _root + "/packages/*.yaml", _root + "/scripts/*.py",
         _root + "/dashboards/*.yaml",
         _root + "/dashboards/*/*.yaml", _root + "/dashboards/*/*/*.yaml",
         _root + "/esphome/*.yaml"]


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


def run_audit():
    env = dict(os.environ, HA_CONFIG=CONFIG, HA_URL=URL)
    try:
        r = subprocess.run([sys.executable, AUDIT], env=env, capture_output=True,
                           text=True, timeout=180)
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
        if not os.path.isdir(repo) or \
                os.path.normcase(os.path.abspath(repo)) == os.path.normcase(here):
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
    return ("\n\nHOOK DEPLOY DRIFT: %s - running hooks in %s against the tracked "
            "copies in %s. One side is stale - re-copy before trusting what the "
            "hooks enforce." % (", ".join(drift), here, repo))


def missing_audit_message():
    return ("HA CONFIG AUDIT DID NOT RUN: %s does not exist. CLAUDE.md: \"If "
            "ha_audit.py cannot run at all, say so and stop. Working blind on a "
            "live house is not a thing to do quietly.\" Check that H: is mounted."
            % AUDIT)


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "sessionstart").lower()

    if mode == "stop":
        if not os.path.exists(AUDIT):
            emit({"systemMessage": missing_audit_message()})
            return
        mtime, blocks = read_stamp()
        if newest() <= mtime:
            return
        out, err = run_audit()
        if err:
            write_stamp(newest(), 0)
            emit({"systemMessage": "HA audit gate: %s" % err})
            return
        v = verdict_line(out)
        clean = v.startswith("0 FAIL") and " 0 WARN," in v
        if clean:
            write_stamp(newest(), 0)
            return
        bad = [l for l in out.splitlines() if l.startswith(("FAIL", "WARN"))]
        if blocks >= MAX_BLOCKS:
            write_stamp(newest(), 0)
            emit({"systemMessage":
                  "HA CONFIG GATE: still not clean after %d blocked stops - "
                  "letting the turn end so the session is not wedged. UNRESOLVED:\n%s\n%s"
                  % (MAX_BLOCKS, "\n".join(bad[:12]), v)})
            return
        if not write_stamp(newest(), blocks + 1):
            # Cannot persist the block count, so cannot guarantee this ever
            # stops. Speak instead of blocking - a gate that cannot count its
            # own retries has no business holding the session open.
            emit({"systemMessage":
                  "HA CONFIG GATE: audit is not clean, but the gate stamp (%s) "
                  "could not be written, so the retry count cannot be tracked. "
                  "NOT blocking, to avoid wedging the session. UNRESOLVED:\n%s\n%s"
                  % (STAMP, "\n".join(bad[:12]), v)})
            return
        emit({"decision": "block",
              "reason": "H: changed this turn and ha_audit.py is not clean. Fix "
                        "these before finishing, or say explicitly what you are "
                        "leaving open and why (CLAUDE.md OUTPUT FORMAT):\n"
                        + "\n".join(bad[:12]) + "\n" + v})
        return

    # ---- session start --------------------------------------------------
    if not os.path.exists(AUDIT):
        emit({"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": missing_audit_message()}})
        return
    out, err = run_audit()
    write_stamp(newest(), 0)
    if err:
        emit({"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext":
                "HA CONFIG AUDIT could not run: %s\nCLAUDE.md: if ha_audit.py "
                "cannot run at all, say so and stop. Working blind on a live "
                "house is not a thing to do quietly." % err}})
        return
    emit({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext":
            "HA CONFIG AUDIT (ran automatically per CLAUDE.md SESSION PROTOCOL).\n"
            "Read this verdict aloud in your first message and name every FAIL "
            "and WARN:\n\n" + out + deploy_drift()}})


if __name__ == "__main__":
    main()
