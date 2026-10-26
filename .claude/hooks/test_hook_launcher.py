"""R2/R7 test of hook_launcher.CODE. Part 1: probe - the launcher must be indistinguishable from `python <script>`
(argv, __name__, __file__, sys.path, stdin, exit code incl. an uncaught exception), and a missing script must give
exit 0 + a valid JSON systemMessage. Part 2: mutations of the launcher must each FAIL part 1. Part 3: the real
hooks, old settings argv vs new, same payload, isolated state (USERPROFILE + CONTEXT_HYGIENE_STATE in a temp home).
Usage: python test_hook_launcher.py <old settings.json> <new settings.json>
Old = the settings before a launcher change; for the 2026-10-18 install that is
C:/sandbox/hook_launcher/settings.orig.json, the rollback copy."""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hook_launcher as launcher  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
PROBE = HERE + "/hook_launcher_probe.py"
fails = []


def run(args, stdin="", env=None, cwd=None):
    r = subprocess.run(
        ["python"] + args,
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        timeout=60,
    )
    return r.returncode, r.stdout, r.stderr


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        fails.append(name)


def probe_suite(code_tmpl, label, quiet=False):
    """Return the list of failed probe checks for a launcher template."""
    bad = []
    cwd = tempfile.mkdtemp()
    open(os.path.join(cwd, "json.py"), "w").write(
        "raise SystemExit('cwd json.py shadowed stdlib')\n"
    )
    for mode in ("0", "2", "raise"):
        d = run([PROBE, mode], stdin="payload-" + mode, cwd=cwd)
        lc = run(
            ["-c", code_tmpl.format(p=PROBE), mode], stdin="payload-" + mode, cwd=cwd
        )
        if d[0] != lc[0]:
            bad.append(f"{mode}: exit {d[0]} vs {lc[0]}")
        try:
            dj, lj = json.loads(d[1]), json.loads(lc[1])
        except ValueError:
            bad.append(f"{mode}: unparsable stdout {lc[1][:120]!r} {lc[2][-200:]!r}")
            continue
        for k in ("argv", "name", "file", "path0", "cwd_on_path", "path_tail", "stdin"):
            if dj[k] != lj[k]:
                bad.append(f"{mode}: {k} {dj[k]!r} vs {lj[k]!r}")
    missing = HERE + "/no_such_hook.py"
    rc, out, err = run(["-c", code_tmpl.format(p=missing), "stop"], cwd=cwd)
    try:
        msg = json.loads(out).get("systemMessage", "")
    except ValueError:
        msg = ""
    if rc != 0 or "HOOK MISSING" not in msg or missing not in msg:
        bad.append(f"missing: rc={rc} out={out[:120]!r} err={err[-120:]!r}")
    shutil.rmtree(cwd)
    if not quiet:
        for b in bad:
            print("     " + b)
    return bad


# Part 1: the real launcher passes the probe
b = probe_suite(launcher.CODE, "launcher")
check(
    "probe: launcher == python <script> (3 modes) and missing -> exit 0 + systemMessage",
    not b,
    b,
)

# Part 2: mutations must be caught
OLD = "import os,runpy,sys;p='{p}';sys.argv[0]=p;sys.path.insert(0,os.path.dirname(p));os.path.exists(p) and runpy.run_path(p,run_name='__main__')"
mutants = {
    "old launcher (silent on missing, cwd on path)": OLD,
    "no run_name": launcher.CODE.replace(",run_name='__main__'", ""),
    "cwd kept on path": launcher.CODE.replace("[x for x in sys.path if x]", "sys.path"),
    # "argv[0] not set" is an equivalent mutant: runpy.run_path sets argv[0] (_ModifiedArgv0); CODE dropped the line.
    "script dir not on path": launcher.CODE.replace(
        "sys.path.insert(0,os.path.dirname(p));", ""
    ),
    "missing -> nothing printed": launcher.CODE.split(" if os.path.exists(p) else ")[
        0
    ].replace("runpy.run_path", "os.path.exists(p) and runpy.run_path"),
}
for name, tmpl in mutants.items():
    check(f"mutation caught: {name}", bool(probe_suite(tmpl, name, quiet=True)))

# Part 3: real hooks, old argv vs new argv from the two settings files, isolated home
old_s, new_s = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:3])
home = tempfile.mkdtemp()
os.makedirs(os.path.join(home, ".claude", "checkpoints"))
state = os.path.join(home, "state")
os.makedirs(state)
tr = os.path.join(home, "t.jsonl")
open(tr, "w").close()
env = dict(os.environ, USERPROFILE=home, CONTEXT_HYGIENE_STATE=state)
base = {
    "session_id": "launcher-test-0000",
    "transcript_path": tr,
    "cwd": "C:/Users/wkcol",
    "permission_mode": "auto",
}
payloads = {
    ("PreToolUse", "Write|Edit|NotebookEdit"): [
        dict(
            base,
            hook_event_name="PreToolUse",
            tool_name="Write",
            tool_input={
                "file_path": "H:/.storage/core.entity_registry",
                "content": "x",
            },
        ),
        dict(
            base,
            hook_event_name="PreToolUse",
            tool_name="Write",
            tool_input={"file_path": os.path.join(home, "scratch.txt"), "content": "x"},
        ),
        # doc_guard.py (2026-10-25) is silent on both paths above; with the empty
        # transcript this one is the deny that makes its comparison non-vacuous
        dict(
            base,
            hook_event_name="PreToolUse",
            tool_name="Write",
            tool_input={"file_path": "H:/dashboards/views/x.yaml", "content": "x"},
        ),
    ],
    ("PostToolUse", "Write|Edit"): [
        dict(
            base,
            hook_event_name="PostToolUse",
            tool_name="Write",
            tool_input={"file_path": os.path.join(home, "scratch.txt")},
            tool_response={},
        )
    ],
    ("PostToolUse", "*"): [
        dict(
            base,
            hook_event_name="PostToolUse",
            tool_name="Bash",
            tool_input={"command": "ls"},
            tool_response={},
        )
    ],
    ("PreToolUse", "*"): [
        dict(
            base,
            hook_event_name="PreToolUse",
            tool_name="Bash",
            tool_input={"command": "ls"},
        )
    ],
    ("PreToolUse", "Read"): [
        dict(
            base,
            hook_event_name="PreToolUse",
            tool_name="Read",
            tool_input={"file_path": PROBE},
        )
    ],
    ("PreToolUse", "Bash"): [
        dict(
            base,
            hook_event_name="PreToolUse",
            tool_name="Bash",
            tool_input={"command": "echo 'a" + "\\" * 2 + "b'"},
        ),
        dict(
            base,
            hook_event_name="PreToolUse",
            tool_name="Bash",
            tool_input={"command": "echo ok"},
        ),
    ],
    ("SessionStart", "compact"): [
        dict(base, hook_event_name="SessionStart", source="compact")
    ],
    ("Stop", "*"): [dict(base, hook_event_name="Stop", stop_hook_active=False)],
    ("UserPromptSubmit", "*"): [
        dict(base, hook_event_name="UserPromptSubmit", prompt="hello")
    ],
    ("PreCompact", "auto"): [
        dict(
            base, hook_event_name="PreCompact", trigger="auto", custom_instructions=None
        )
    ],
}
SKIP = {
    "ha_audit_gate.py"
}  # runs the full live audit (180 s); argv transport is proven by the probe
compared = 0
for ev in new_s["hooks"]:
    for go, gn in zip(old_s["hooks"][ev], new_s["hooks"][ev]):
        for ho, hn in zip(go["hooks"], gn["hooks"]):
            script, modes = launcher.script_of(hn["args"])
            name = script.rsplit("/", 1)[-1]
            check(
                f"{ev} [{gn.get('matcher', '*')}] {name}: same script and modes",
                launcher.script_of(ho["args"]) == (script, modes),
            )
            if name in SKIP:
                print(f"skip {ev} {name} (live audit)")
                continue
            outs = []
            for pl in payloads.get((ev, gn.get("matcher", "*")), []):
                # fresh deny-once state per run, or doc_guard's old-argv deny
                # turns the new-argv run into an allow-repeat
                fresh = [
                    dict(env, DOC_GUARD_STATE=tempfile.mkdtemp(dir=home))
                    for _ in range(2)
                ]
                o = run(ho["args"], json.dumps(pl), env=fresh[0])
                n = run(hn["args"], json.dumps(pl), env=fresh[1])
                check(
                    f"  {name} {modes} payload {pl.get('tool_input', {}) or pl.get('hook_event_name')}: exit {o[0]}/{n[0]}, stdout equal",
                    o[:2] == n[:2],
                    f"old={o} new={n}",
                )
                outs.append(o[:2])
                compared += 1
            if len(outs) >= 2:
                check(
                    f"  {name}: the payloads differ in outcome (comparison is not vacuous)",
                    len(set(outs)) > 1,
                    outs,
                )
shutil.rmtree(home)
print(f"\n{compared} real-hook comparisons; FAILS: {len(fails)}")
sys.exit(1 if fails else 0)
