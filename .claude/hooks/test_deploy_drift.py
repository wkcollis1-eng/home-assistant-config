#!/usr/bin/env python
"""Fire/silent tests for ha_audit_gate.deploy_drift() (CLAUDE.md R7).

Builds a throwaway deployed hooks dir and a throwaway repo (HA_GATE_CONFIG),
loads a copy of the gate from the deployed dir, and checks what it reports.
Touches nothing outside a temp dir. Optional argv[1]: the gate file to test
(default: ha_audit_gate.py beside this file).

    python test_deploy_drift.py [path/to/ha_audit_gate.py]
"""
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "ha_audit_gate.py")
FAILS = 0


def check(name, got, want_in=(), want_out=(), silent=False):
    global FAILS
    ok = (got == "") if silent else (
        got != "" and all(w in got for w in want_in) and not any(w in got for w in want_out))
    FAILS += not ok
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else ": got %r" % got))


def case(mutate, config_sub="cfg", config=None, spy=None):
    """Fresh deployed+repo pair, all in sync; mutate(deployed, repo) breaks it.

    config overrides HA_GATE_CONFIG. spy: a list that receives every path
    deploy_drift() passes to os.path.isdir (patched for that call only).
    """
    root = tempfile.mkdtemp(prefix="drift_")
    dep = os.path.join(root, "deployed")
    repo = os.path.join(root, "cfg", ".claude", "hooks")
    os.makedirs(dep)
    os.makedirs(repo)
    shutil.copy(GATE, os.path.join(dep, "ha_audit_gate.py"))
    for n in ("ha_guard.py", "context_hygiene.py"):
        with open(os.path.join(dep, n), "w") as f:
            f.write("# %s\n" % n)
    for n in os.listdir(dep):
        shutil.copy(os.path.join(dep, n), repo)
    mutate(dep, repo)
    os.environ["HA_GATE_CONFIG"] = config or os.path.join(root, config_sub).replace("\\", "/") + "/"
    spec = importlib.util.spec_from_file_location("gate_%d" % id(root), os.path.join(dep, "ha_audit_gate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    real_isdir = os.path.isdir
    if spy is not None:
        os.path.isdir = lambda p: spy.append(p) or real_isdir(p)
    try:
        return mod.deploy_drift()
    finally:
        os.path.isdir = real_isdir
        shutil.rmtree(root, ignore_errors=True)


def append(path, text="# edited\n"):
    with open(path, "a") as f:
        f.write(text)


print("deploy_drift() against %s" % GATE)
print("fires")
check("sibling hook differs -> named",
      case(lambda d, r: append(os.path.join(r, "ha_guard.py"))),
      want_in=("ha_guard.py (differs)",), want_out=("context_hygiene.py", "ha_audit_gate.py ("))
check("deployed hook has no tracked copy -> named",
      case(lambda d, r: os.remove(os.path.join(r, "context_hygiene.py"))),
      want_in=("context_hygiene.py (no tracked copy)",), want_out=("ha_guard.py",))
check("the gate itself differs -> named (pre-2026-09-16 behaviour kept)",
      case(lambda d, r: append(os.path.join(d, "ha_audit_gate.py"))),
      want_in=("ha_audit_gate.py (differs)",))
check("two drifted hooks -> both named",
      case(lambda d, r: (append(os.path.join(r, "ha_guard.py")),
                         os.remove(os.path.join(r, "context_hygiene.py")))),
      want_in=("ha_guard.py (differs)", "context_hygiene.py (no tracked copy)"))
probed = []
case(lambda d, r: None, config="H:/", spy=probed)
check("drive-root config 'H:/' probes an absolute path, not drive-relative 'H:.claude'",
      "" if probed and all(os.path.isabs(p) for p in probed) else "probed %r" % probed,
      silent=True)
print("silent")
check("all in sync", case(lambda d, r: None), silent=True)
check("repo hooks dir unreachable", case(lambda d, r: shutil.rmtree(r)), silent=True)
check("non-.py files beside the hooks ignored",
      case(lambda d, r: (append(os.path.join(d, ".ha_audit_stamp"), "123"),
                         os.makedirs(os.path.join(d, ".state")))), silent=True)
check("tracked-only file (a test) not deployed",
      case(lambda d, r: append(os.path.join(r, "test_x.py"))), silent=True)
print("FAILS: %d" % FAILS)
sys.exit(1 if FAILS else 0)
