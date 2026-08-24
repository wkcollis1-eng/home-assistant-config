#!/usr/bin/env python
"""Two-direction test harness for scripts/ha_audit.py.

WHY THIS EXISTS. R7 says a gate untested against a known-bad input is not a
gate: prove a rule FIRES on an injected fault AND stays SILENT on a clean tree,
both directions, before trusting it. Until 2026-08-24 that was done by hand,
once, per rule - which means it was done for the rule being written and never
again for the ones already there.

It is not hypothetical. On 2026-08-24 the first cut of `rule_doc_ids` was
silently broken: two layers of escaping turned a `\\b` in its regex into a
literal backspace byte, so the pattern could never match and the rule reported
nothing on a tree that contained 17 real faults. Only direction 1 caught it.
A rule that cannot fail spends trust faster than a rule that is wrong.

HOW IT WORKS. The clean baseline is the REAL config, copied to a scratch tree -
not a synthetic minimal one, because a fixture that does not look like the live
house tests a different program. Faults are then injected into a second copy.

WHY ALL FAULTS AT ONCE (by default). The audit takes ~13.5 s per run, so one
fixture per rule would be a 7-minute suite that nobody runs. Injecting every
fault into one tree and asserting each expected rule id appears costs two runs.
The tradeoff is that faults could in principle mask one another, so `--only`
runs a single fault in isolation when a rule is under suspicion.

USAGE
    python scripts/test_ha_audit.py                # both directions, all faults
    python scripts/test_ha_audit.py --only dead-constraint
    python scripts/test_ha_audit.py --list         # coverage report
    python scripts/test_ha_audit.py --keep         # leave trees for inspection

Set HA_URL to include the live statistics-buffer check; without it the audit
correctly reports live-check-skipped (R8) and the harness expects that WARN.

EXIT 0 = every covered rule fired when it should and the clean tree was clean.
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

# Default matches ha_audit.py so the two agree when this runs on the HA host
# under shell_command, which sets no environment. Off-host sessions set
# HA_CONFIG explicitly (H:/ over Samba).
SRC = os.environ.get("HA_CONFIG", "/config").rstrip("/")
COPY = ["configuration.yaml", "automations.yaml", "scripts.yaml", "scenes.yaml",
        "pipelines.yaml", "entity_notes.yaml", "CLAUDE.md", "ENTITIES.md",
        "AUTOMATIONS.md", "PACKAGES.md", ".HA_VERSION"]
COPY_DIRS = ["packages", "scripts", "docs"]
COPY_STORAGE = ["core.entity_registry", "core.restore_state",
                "core.device_registry", "core.config_entries"]


# --------------------------------------------------------------------------
# fault injectors.  each returns None, mutating the tree at `root` in place.
# every one of these is a defect that actually reached the live config, or the
# exact shape of one that did.
# --------------------------------------------------------------------------

def _read(root, rel):
    return io.open(os.path.join(root, rel), encoding="utf-8").read()


def _write(root, rel, s):
    io.open(os.path.join(root, rel), "w", encoding="utf-8", newline="\n").write(s)


def f_dead_constraint(root):
    """A CONSTRAINT naming an entity that does not exist - the shelly typo."""
    s = _read(root, "CLAUDE.md")
    anchor = "NEVER remove inline YAML comments\n"
    assert anchor in s, "CONSTRAINTS anchor moved"
    _write(root, "CLAUDE.md",
           s.replace(anchor, anchor + "NEVER touch sensor.this_entity_does_not_exist\n", 1))


def f_truncated_id(root):
    """A generated doc carrying an id cut mid-name - the gen_reference bug."""
    s = _read(root, "AUTOMATIONS.md")
    m = re.search(r"binary_sensor\.[a-z0-9_]{20,}", s)
    assert m, "no long binary_sensor id in AUTOMATIONS.md to truncate"
    _write(root, "AUTOMATIONS.md", s.replace(m.group(0), m.group(0)[:-1], 1))


def f_generated_doc_stale(root):
    """A generated doc that no longer matches what the generator would write."""
    _write(root, "PACKAGES.md", _read(root, "PACKAGES.md") + "\nhand-edited line\n")


def f_generated_doc_missing(root):
    """A generated doc deleted outright."""
    os.remove(os.path.join(root, "ENTITIES.md"))


def f_entity_ref_unresolved(root):
    """A template referencing an entity that never existed - the 15-night bug."""
    s = _read(root, "configuration.yaml")
    _write(root, "configuration.yaml", s + """
# injected by test_ha_audit.py
template:
  - sensor:
      - name: "Audit Test Probe"
        unique_id: audit_test_probe
        state: "{{ states('sensor.audit_test_phantom_entity') | float(0) }}"
""")


def f_choose_without_default(root):
    """A choose: with no default: [] - silent no-op when nothing matches."""
    s = _read(root, "automations.yaml")
    _write(root, "automations.yaml", s + """
- id: audit_test_choose_no_default
  alias: Audit Test Choose No Default
  trigger:
    - platform: state
      entity_id: input_boolean.ha_maintenance_mode
  action:
    - choose:
        - conditions:
            - condition: state
              entity_id: input_boolean.ha_maintenance_mode
              state: "on"
          sequence:
            - delay: "00:00:01"
""")


def f_unguarded_shell_command(root):
    """A shell_command fired without the ha_maintenance_mode guard.

    NOTE, found by this harness 2026-08-24: the injector must declare a NEW
    shell_command. The rule computes `called - guarded` per shell_command NAME,
    not per CALL SITE, so adding an unguarded call to a name that is guarded
    somewhere else fires nothing. That is a real limitation of the rule and is
    recorded in CLAUDE.md; this injector deliberately tests only what the rule
    actually covers, rather than papering over the gap by asserting a pass the
    rule cannot deliver.
    """
    s = _read(root, "configuration.yaml")
    _write(root, "configuration.yaml", s + """
# injected by test_ha_audit.py
shell_command:
  audit_test_probe_cmd: "echo probe"
""")
    s = _read(root, "automations.yaml")
    _write(root, "automations.yaml", s + """
- id: audit_test_unguarded_shell
  alias: Audit Test Unguarded Shell
  trigger:
    - platform: time
      at: "03:17:00"
  action:
    - service: shell_command.audit_test_probe_cmd
  mode: single
""")


def f_entity_note_orphan(root):
    """entity_notes.yaml annotating an entity that no longer exists."""
    s = _read(root, "entity_notes.yaml")
    _write(root, "entity_notes.yaml", s + """
sensor.audit_test_orphan_note:
  note: injected by test_ha_audit.py
""")


def f_shell_command_multi_call(root):
    """A SECOND, UNGUARDED call site for a command that is guarded elsewhere.

    This is the exact scenario rule_shell_commands_guarded cannot see: the
    name is already in `guarded` because script.ha_audit guards its own call,
    so `called - guarded` is empty and unguarded-shell-command stays silent.
    The tripwire is the only thing that reports it - which is the point, and
    why this injector asserts on shell-command-multi-call rather than on
    unguarded-shell-command.
    """
    s = _read(root, "automations.yaml")
    _write(root, "automations.yaml", s + """
- id: audit_test_second_call_site
  alias: Audit Test Second Call Site
  trigger:
    - platform: time
      at: "03:19:00"
  action:
    - service: shell_command.ha_audit
  mode: single
""")


FAULTS = [
    ("dead-constraint",        f_dead_constraint),
    ("truncated-id",           f_truncated_id),
    ("generated-doc-stale",    f_generated_doc_stale),
    ("entity-ref-unresolved",  f_entity_ref_unresolved),
    ("choose-without-default", f_choose_without_default),
    ("unguarded-shell-command", f_unguarded_shell_command),
    ("entity-note-orphan",     f_entity_note_orphan),
    ("shell-command-multi-call", f_shell_command_multi_call),
]

# generated-doc-missing deletes ENTITIES.md, which suppresses the ghost and
# truncated-id checks on that file, so it cannot share a tree with them.
SOLO_FAULTS = [
    ("generated-doc-missing",  f_generated_doc_missing),
]

# Rules with no fault injector yet. Listed rather than omitted: an untested
# rule that nobody has written down reads as a tested one (R8 - absent findings
# must never look like clean findings).
UNCOVERED = [
    "chart-window-exceeds-recorder", "dead-shell-command", "doc-ids-uncheckable",
    "empty-buffer", "entity-missing", "eod-race", "eod-read-write",
    "eod-undeclared", "eod-undocumented", "fabricated-constant",
    "fabricated-limit-constant", "generated-doc-ghost",
    "generated-docs-uncheckable", "guard-entity-missing", "legacy-backup-drift",
    "live-check-skipped", "manifest-drift", "no-detector", "no-liveness",
    "phantom-entity-id", "repeated-buffer", "stamp-not-snapshotted",
    "statistics-buffer-truncating", "unlatched-guard",
]


# --------------------------------------------------------------------------

def build_tree(dest):
    os.makedirs(dest, exist_ok=True)
    for rel in COPY:
        src = os.path.join(SRC, rel)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest, rel))
    for d in COPY_DIRS:
        src = os.path.join(SRC, d)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dest, d), dirs_exist_ok=True)
    st = os.path.join(dest, ".storage")
    os.makedirs(st, exist_ok=True)
    for rel in COPY_STORAGE:
        src = os.path.join(SRC, ".storage", rel)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(st, rel))
    return dest


def run_audit(tree):
    env = dict(os.environ, HA_CONFIG=tree)
    r = subprocess.run([sys.executable, os.path.join(tree, "scripts", "ha_audit.py")],
                       env=env, capture_output=True, text=True, timeout=600)
    return (r.stdout or "") + (r.stderr or "")


def fired(out):
    ids = set()
    for line in out.splitlines():
        m = re.match(r"^(FAIL|WARN)\s+([a-z0-9-]+)\s", line)
        if m:
            ids.add(m.group(2))
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", metavar="RULE")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--json", action="store_true",
                    help="machine-readable single line, for script.ha_audit_tests")
    a = ap.parse_args()
    say = (lambda *x: None) if a.json else print

    all_faults = FAULTS + SOLO_FAULTS
    if a.list:
        print("COVERED (%d):" % len(all_faults))
        for rid, _ in all_faults:
            print("   ", rid)
        print("\nNOT COVERED (%d) - no fault injector written yet:" % len(UNCOVERED))
        for rid in UNCOVERED:
            print("   ", rid)
        print("\ncoverage: %d of %d rule ids"
              % (len(all_faults), len(all_faults) + len(UNCOVERED)))
        return 0

    live = "HA_URL" in os.environ
    expected_noise = set() if live else {"live-check-skipped"}
    work = tempfile.mkdtemp(prefix="ha_audit_test_")
    failures = []
    try:
        # ---- direction 2: clean tree must be clean ------------------------
        say("DIRECTION 2  clean tree must produce no FAIL/WARN")
        clean = build_tree(os.path.join(work, "clean"))
        out = run_audit(clean)
        got = fired(out) - expected_noise
        if got:
            failures.append("clean tree was not clean: %s" % sorted(got))
            say("   FAIL - unexpected findings: %s" % sorted(got))
            for l in out.splitlines():
                if l.startswith(("FAIL", "WARN")):
                    say("      " + l)
        else:
            say("   OK - silent%s" % ("" if live else " (live-check-skipped expected, no HA_URL)"))

        # ---- direction 1: each fault must fire its rule -------------------
        selected = [(r, f) for r, f in all_faults if not a.only or r == a.only]
        if a.only and not selected:
            say("no such fault: %s" % a.only)
            return 2

        batch = [(r, f) for r, f in selected if (r, f) in FAULTS]
        solo = [(r, f) for r, f in selected if (r, f) in SOLO_FAULTS]

        if batch:
            say("\nDIRECTION 1  %d fault(s) injected together" % len(batch))
            tree = build_tree(os.path.join(work, "faulty"))
            for rid, fn in batch:
                fn(tree)
            got = fired(run_audit(tree))
            for rid, _ in batch:
                ok = rid in got
                say("   %-4s %s" % ("OK" if ok else "FAIL", rid))
                if not ok:
                    failures.append("%s did not fire" % rid)

        for rid, fn in solo:
            say("\nDIRECTION 1  %s (isolated)" % rid)
            tree = build_tree(os.path.join(work, "solo_" + rid))
            fn(tree)
            got = fired(run_audit(tree))
            ok = rid in got
            say("   %-4s %s" % ("OK" if ok else "FAIL", rid))
            if not ok:
                failures.append("%s did not fire" % rid)
    finally:
        if a.keep:
            say("\ntrees kept at %s" % work)
        else:
            shutil.rmtree(work, ignore_errors=True)

    if a.json:
        import json as _json
        summary = ("SUITE PASSED - %d rule(s) proven in both directions"
                   % len(selected)) if not failures else \
                  ("SUITE FAILED (%d): %s" % (len(failures), "; ".join(failures)))
        sys.stdout.write(_json.dumps({
            "passed": not failures,
            "summary": summary,
            "failures": failures,
            "covered": len(all_faults),
            "total_rule_ids": len(all_faults) + len(UNCOVERED),
        }))
        return 1 if failures else 0

    print("\n" + "=" * 60)
    if failures:
        print("SUITE FAILED (%d)" % len(failures))
        for f in failures:
            print("   " + f)
        return 1
    print("SUITE PASSED - %d rule(s) proven in both directions" % len(selected))
    print("%d of %d rule ids covered; run --list for the gap"
          % (len(all_faults), len(all_faults) + len(UNCOVERED)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
