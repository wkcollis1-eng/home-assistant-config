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

try:
    import yaml
except ImportError:                       # pragma: no cover
    yaml = None
import sys
import tempfile

# Default matches ha_audit.py so the two agree when this runs on the HA host
# under shell_command, which sets no environment. Off-host sessions set
# HA_CONFIG explicitly (H:/ over Samba).
SRC = os.environ.get("HA_CONFIG", "/config").rstrip("/")
COPY = ["configuration.yaml", "automations.yaml", "scripts.yaml", "scenes.yaml",
        "pipelines.yaml", "entity_notes.yaml", "CLAUDE.md", "ENTITIES.md",
        "AUTOMATIONS.md", "PACKAGES.md", ".HA_VERSION"]
# dashboards/ added 2026-08-25. Without it _dashboard_files() returned []
# in BOTH trees, so entity-ref-unresolved and phantom-entity-id were listed
# COVERED while their dashboard path - the surface CLAUDE.md calls the one
# place a broken entity is completely silent - was never exercised in
# either direction.
COPY_DIRS = ["packages", "scripts", "docs", "dashboards"]
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


# --------------------------------------------------------------------------
# injectors added 2026-08-25.  helpers first.
# --------------------------------------------------------------------------

def _add_pipeline(root, block):
    """Splice a raw YAML block in as the first entry under `pipelines:`."""
    s = _read(root, "pipelines.yaml")
    assert "pipelines:\n" in s, "pipelines: anchor moved"
    _write(root, "pipelines.yaml", s.replace("pipelines:\n", "pipelines:\n" + block, 1))


def _add_automation(root, block):
    _write(root, "automations.yaml",
           _read(root, "automations.yaml").rstrip("\n") + "\n" + block)


def f_manifest_drift(root):
    """A pipeline declared in the manifest with no automation behind it.

    This is the drift pipelines.yaml exists to end, and the rule guarding it
    had never fired in 38 nightly runs and had no injector.
    """
    _add_pipeline(root, """  audit_test_ghost_pipeline:
    label: "ghost"
    kind: accumulator
    defined_in: automations.yaml
    at: '23:44:44'
    stamp: input_datetime.audit_test_stamp
    stale_detector: binary_sensor.audit_test_stale
    buffer_slots: 0
""")


def f_eod_undeclared(root):
    """A pipeline with no `at` key at all - not even `at: null`."""
    _add_pipeline(root, """  audit_test_undeclared:
    label: "undeclared"
    kind: accumulator
    defined_in: automations.yaml
    stamp: input_datetime.audit_test_stamp2
    stale_detector: binary_sensor.audit_test_stale2
    buffer_slots: 0
""")


def f_eod_undocumented(root):
    """A trigger time that is not a row in the EOD schedule table.

    Until 2026-08-25 the check was `at not in <whole of CLAUDE.md>`, so any
    time string appearing in any paragraph satisfied it. 04:44:44 appears
    nowhere, which is what makes this a real test of the row parser.
    """
    _add_pipeline(root, """  audit_test_undocumented:
    label: "undocumented"
    kind: accumulator
    defined_in: automations.yaml
    at: '04:44:44'
    stamp: input_datetime.audit_test_stamp3
    stale_detector: binary_sensor.audit_test_stale3
    buffer_slots: 0
""")
    _add_automation(root, """
- id: audit_test_undocumented
  alias: Audit Test Undocumented
  trigger:
    - platform: time
      at: "04:44:44"
  action:
    - service: input_number.set_value
      target:
        entity_id: input_number.audit_test_undoc
      data:
        value: 1
  mode: single
""")


def f_no_liveness(root):
    """A pipeline that writes slots but stamps nothing."""
    _add_pipeline(root, """  audit_test_no_stamp:
    label: "no stamp"
    kind: accumulator
    defined_in: automations.yaml
    at: null
    buffer_slots: 5
""")


def f_no_detector(root):
    """A pipeline with a stamp but no stale detector."""
    _add_pipeline(root, """  audit_test_no_detector:
    label: "no detector"
    kind: accumulator
    defined_in: automations.yaml
    at: null
    stamp: input_datetime.audit_test_stamp4
    buffer_slots: 5
""")


def f_unlatched_guard(root):
    """A guard reading a statistics sensor directly - the 15-night outage.

    CLAUDE.md cites unlatched-guard as a flagship rule, and it had neither an
    injector nor a single firing in 38 runs.
    """
    _add_pipeline(root, """  audit_test_unlatched:
    label: "unlatched"
    kind: spc
    defined_in: automations.yaml
    at: null
    stamp: input_datetime.audit_test_stamp5
    stale_detector: binary_sensor.audit_test_stale5
    buffer_slots: 5
    guard:
      source: sensor.audit_test_running_watts_24h
""")


def f_stamp_not_snapshotted(root):
    """A capture stamping with a live now() instead of a trigger-time snapshot."""
    _add_pipeline(root, """  audit_test_live_stamp:
    label: "live stamp"
    kind: accumulator
    defined_in: automations.yaml
    at: '03:33:00'
    stamp: input_datetime.audit_test_stamp6
    stale_detector: binary_sensor.audit_test_stale6
    buffer_slots: 0
""")
    _add_automation(root, """
- id: audit_test_live_stamp
  alias: Audit Test Live Stamp
  trigger:
    - platform: time
      at: "03:33:00"
  action:
    - service: input_datetime.set_datetime
      target:
        entity_id: input_datetime.audit_test_stamp6
      data:
        date: "{{ now().date() }}"
  mode: single
""")


def f_eod_race(root):
    """Two same-second automations writing the same entity - write/write.

    DELIBERATELY UNDECLARED: no pipelines.yaml entry. Before 2026-08-25 the
    race check only inspected declared pipelines, so this exact pair produced
    NOTHING. It is the regression test for that scope, and it fails against the
    old rule by construction.
    """
    _add_automation(root, """
- id: audit_test_race_a
  alias: Audit Test Race A
  trigger:
    - platform: time
      at: "03:47:00"
  action:
    - service: input_number.set_value
      target:
        entity_id: input_number.audit_test_shared
      data:
        value: 1
  mode: single

- id: audit_test_race_b
  alias: Audit Test Race B
  trigger:
    - platform: time
      at: "03:47:00"
  action:
    - service: input_number.set_value
      target:
        entity_id: input_number.audit_test_shared
      data:
        value: 2
  mode: single
""")


def f_eod_read_write(root):
    """One same-second automation reads what the other writes.

    Undeclared, like f_eod_race. B reads through is_state(), which _reads()
    could not see until 2026-08-25 - so this injector fails against BOTH the
    old scope and the old read regex, and passes only against the current rule.
    """
    _add_automation(root, """
- id: audit_test_rw_a
  alias: Audit Test RW A
  trigger:
    - platform: time
      at: "03:49:00"
  action:
    - service: input_boolean.turn_on
      target:
        entity_id: input_boolean.audit_test_flag
  mode: single

- id: audit_test_rw_b
  alias: Audit Test RW B
  trigger:
    - platform: time
      at: "03:49:00"
  action:
    - service: input_number.set_value
      target:
        entity_id: input_number.audit_test_rw_out
      data:
        value: "{{ 1 if is_state('input_boolean.audit_test_flag', 'on') else 0 }}"
  mode: single
""")


def f_eod_write_unmodelled(root):
    """A same-second write whose target is a template - the unprovable case.

    FAIL since 2026-08-25: if the checker cannot model the target it cannot
    rule out a collision, and fail-safe means the unprovable case blocks.
    """
    _add_automation(root, """
- id: audit_test_um_a
  alias: Audit Test Unmodelled A
  trigger:
    - platform: time
      at: "03:51:00"
  action:
    - service: input_number.set_value
      target:
        entity_id: "{{ 'input_number.audit_test_' ~ 'dynamic' }}"
      data:
        value: 1
  mode: single

- id: audit_test_um_b
  alias: Audit Test Unmodelled B
  trigger:
    - platform: time
      at: "03:51:00"
  action:
    - service: input_number.set_value
      target:
        entity_id: input_number.audit_test_um_other
      data:
        value: 2
  mode: single
""")


def f_eod_time_unresolvable(root):
    """A time trigger whose `at` is not a literal - excluded from the check."""
    _add_automation(root, """
- id: audit_test_templated_time
  alias: Audit Test Templated Time
  trigger:
    - platform: time
      at: input_datetime.audit_test_when
  action:
    - service: input_number.set_value
      target:
        entity_id: input_number.audit_test_templated
      data:
        value: 1
  mode: single
""")


def f_generated_doc_ghost(root):
    """A generated doc listing an entity id that does not exist."""
    s = _read(root, "ENTITIES.md")
    i = s.index("```\n") + 4
    _write(root, "ENTITIES.md", s[:i] + "sensor.audit_test_ghost_entity\n" + s[i:])


def f_open_question(root):
    """R14: a question asked of Bill that never got an answer."""
    _write(root, "open_questions.yaml", """- asked: 2026-08-24
  question: Does the basement router's plug hang off the UPS?
  blocks: summing router draw with ups_outlet_current_consumption
""")


def f_dashboard_not_pasted(root):
    """A view referencing an entity no live export contains - the P12 shape."""
    rel = "dashboards/views/dehumidifier.yaml"
    s = _read(root, rel)
    anchor = "badges:\n"
    assert anchor in s, "badges anchor moved in %s" % rel
    _write(root, rel, s.replace(
        anchor,
        anchor + "  - type: entity\n    entity: sensor.audit_test_never_pasted\n", 1))


def f_unparseable_yaml(root):
    """A config file that does not parse at all.

    Found 2026-08-25 while fault-testing rule_dashboard_pasted: this raised
    yaml.ParserError out of load() and killed the whole run before any rule
    executed, so the nightly job would have logged a traceback instead of a
    verdict. A config that will not parse is when the audit is most needed.
    """
    _write(root, "dashboards/views/audit_test_broken.yaml",
           "type: sections\ncards:\n  - type: entity\n   entity: sensor.bad_indent\n")


# ---- SOLO: each of these suppresses a rule another injector depends on ----

def f_doc_ids_uncheckable(root):
    """CLAUDE.md with no CONSTRAINTS section - rule_doc_ids cannot run.

    SOLO because it removes the section f_dead_constraint injects into.
    """
    # NOTE 2026-08-25: the first cut of this injector renamed the heading to
    # "## CONSTRAINTS-RENAMED" and the rule went on finding it, because its
    # regex is ^##\s+CONSTRAINTS.*?$ - the suffix still matched. The heading
    # has to stop starting with CONSTRAINTS for the section to be genuinely
    # missing. Direction 1 caught it; by eye it looked obviously correct.
    s = _read(root, "CLAUDE.md")
    _write(root, "CLAUDE.md", s.replace("## CONSTRAINTS (CHECK BEFORE ANY ACTION)",
                                        "## PRECONDITIONS (CHECK BEFORE ANY ACTION)", 1))


def f_eod_doc_uncheckable(root):
    """The EOD schedule table gone from every file that may hold it.

    SOLO: with no table, every declared trigger time would also report
    eod-undocumented, which would mask what this is actually asserting.
    This is the exact failure that would have hit a CLAUDE.md restructuring.
    """
    import re as _re
    s = _read(root, "CLAUDE.md")
    _write(root, "CLAUDE.md", _re.sub(r"(?m)^\d{2}:\d{2}:\d{2}\s+\S.*$", "", s))


def f_open_questions_malformed(root):
    """open_questions.yaml that is not a list. SOLO: same file as f_open_question."""
    _write(root, "open_questions.yaml", "asked: 2026-08-24\nquestion: not a list\n")


def f_duplicate_automation_id(root):
    """Two automations sharing an `id:`.

    HA resolves this quietly and one of the two is inert - so the block you
    edited may not be the block that runs. Found 2026-08-25 when
    new_pipeline.py --apply was run twice; nothing in the audit noticed.
    """
    _add_automation(root, """
- id: audit_test_dup_id
  alias: Audit Test Dup One
  trigger:
    - platform: time
      at: "04:01:00"
  action:
    - service: input_number.set_value
      target:
        entity_id: input_number.audit_test_dup
      data:
        value: 1
  mode: single

- id: audit_test_dup_id
  alias: Audit Test Dup Two
  trigger:
    - platform: time
      at: "04:02:00"
  action:
    - service: input_number.set_value
      target:
        entity_id: input_number.audit_test_dup
      data:
        value: 2
  mode: single
""")


def f_duplicate_pipeline_key(root):
    """The same key twice under `pipelines:`.

    PyYAML keeps the LAST and drops the first with no error at all, so a
    pipeline can cease to exist while every file still appears to declare it.
    """
    block = """  audit_test_dup_key:
    label: "dup one"
    kind: accumulator
    defined_in: automations.yaml
    at: null
    stamp: input_datetime.audit_test_dupkey
    stale_detector: binary_sensor.audit_test_dupkey_stale
    buffer_slots: 0
  audit_test_dup_key:
    label: "dup two"
    kind: accumulator
    defined_in: automations.yaml
    at: null
    stamp: input_datetime.audit_test_dupkey
    stale_detector: binary_sensor.audit_test_dupkey_stale
    buffer_slots: 0
"""
    _add_pipeline(root, block)


FAULTS = [
    ("dead-constraint",        f_dead_constraint),
    ("truncated-id",           f_truncated_id),
    ("generated-doc-stale",    f_generated_doc_stale),
    ("entity-ref-unresolved",  f_entity_ref_unresolved),
    ("choose-without-default", f_choose_without_default),
    ("unguarded-shell-command", f_unguarded_shell_command),
    ("entity-note-orphan",     f_entity_note_orphan),
    ("shell-command-multi-call", f_shell_command_multi_call),
    ("manifest-drift",          f_manifest_drift),
    ("eod-undeclared",          f_eod_undeclared),
    ("eod-undocumented",        f_eod_undocumented),
    ("no-liveness",             f_no_liveness),
    ("no-detector",             f_no_detector),
    ("unlatched-guard",         f_unlatched_guard),
    ("stamp-not-snapshotted",   f_stamp_not_snapshotted),
    ("eod-race",                f_eod_race),
    ("eod-read-write",          f_eod_read_write),
    ("eod-write-unmodelled",    f_eod_write_unmodelled),
    ("generated-doc-ghost",     f_generated_doc_ghost),
    ("open-question",           f_open_question),
    ("dashboard-not-pasted",    f_dashboard_not_pasted),
    ("unparseable-yaml",        f_unparseable_yaml),
    ("duplicate-automation-id", f_duplicate_automation_id),
    ("duplicate-pipeline-key",  f_duplicate_pipeline_key),
    ("eod-time-unresolvable",   f_eod_time_unresolvable),
]

# generated-doc-missing deletes ENTITIES.md, which suppresses the ghost and
# truncated-id checks on that file, so it cannot share a tree with them.
SOLO_FAULTS = [
    ("generated-doc-missing",  f_generated_doc_missing),
    ("doc-ids-uncheckable",    f_doc_ids_uncheckable),
    ("eod-doc-uncheckable",    f_eod_doc_uncheckable),
    ("open-questions-malformed", f_open_questions_malformed),
]

# THE RULE-ID INVENTORY IS DERIVED, NEVER TYPED. Until 2026-08-25 `UNCOVERED`
# was a hand-kept list, and the counts appeared in three more places in
# CLAUDE.md ("32 rule ids... proves 8", "9 of 33", "8 of 32"). All four had
# drifted, and `eod-concurrent` had fallen out of the accounting entirely -
# present in neither FAULTS nor UNCOVERED, so it was invisible to --list while
# looking exactly like a rule someone had considered. That is R10 inside the
# harness that enforces R10, and the R10 answer is to delete the second copy.
def _emitters():
    """{rule_id: {"fail","warn","info"}} scraped from ha_audit.py itself."""
    src = io.open(os.path.join(SRC, "scripts", "ha_audit.py"),
                  encoding="utf-8").read()
    out = {}
    for sev, rid in re.findall(r'\b(fail|warn|info)\(\s*"([a-z0-9-]+)"', src):
        out.setdefault(rid, set()).add(sev)
    # EVERY CALL SITE MUST HAVE YIELDED AN ID. The <20 floor in inventory()
    # only catches the regex failing wholesale; a single
    # fail(SOME_CONSTANT, ...) would drop exactly one id and nothing would say
    # so - the same R8 inversion, one rule at a time. Count the call sites and
    # insist they match.
    # (?<!def ) so the three `def fail(...)` / `def warn(...)` /
    # `def info(...)` definitions are not counted as call sites. Without it
    # this guard fired on a perfectly healthy ha_audit.py - a false alarm in
    # the check written to stop false silence.
    sites = len(re.findall(r'(?<!def )\b(?:fail|warn|info)\(', src))
    matched = len(re.findall(r'\b(?:fail|warn|info)\(\s*"[a-z0-9-]+"', src))
    if sites != matched:
        raise SystemExit(
            "test_ha_audit: %d fail()/warn()/info() call site(s) in ha_audit.py "
            "but only %d gave a literal rule id. The %d unmatched one(s) would "
            "be invisible to the coverage report. Use a literal string, or "
            "teach _emitters() about the new form."
            % (sites, matched, sites - matched))
    return out


def inventory():
    """(testable, info_only) rule ids.

    fired() matches FAIL|WARN only, so an id emitted solely through info() can
    never be asserted by this harness. That is defensible - an INFO that needs
    an action is a WARN (R8) - but it has to be SAID rather than silently
    dropped, which is exactly how eod-concurrent went missing.
    """
    em = _emitters()
    # AN EMPTY SCRAPE MUST NOT READ AS FULL COVERAGE. Found 2026-08-25 by
    # stubbing _emitters() to {}: `uncovered` became [], --list printed
    # "NOT COVERED (0)", and the percentage read 2600%. Silence indistinguishable
    # from success - R8 inverted, inside the code written to fix an R8
    # inversion. ha_audit.py has had 30+ rule ids since it was worth testing,
    # so anything under 20 means the regex stopped matching, not that the rules
    # went away.
    if len(em) < 20:
        raise SystemExit(
            "test_ha_audit: scraped only %d rule id(s) from ha_audit.py - the "
            "inventory regex has stopped matching, so coverage numbers would be "
            "meaningless. Refusing to report. Check the fail()/warn()/info() "
            "call sites." % len(em))
    info_only = set(r for r, sev in em.items() if sev == {"info"})
    return set(em) - info_only, info_only


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


def _creds_from_secrets():
    """(token, url) recovered from SRC/secrets.yaml's ha_audit_cmd, or (None, None).

    HA's `!secret` cannot be used inside a string, so the WHOLE shell_command
    lives in secrets.yaml as one value - which means the token is embedded in a
    command line rather than sitting in a field of its own. Parsing it back out
    is less elegant than a dedicated key and considerably safer than minting a
    duplicate.

    Read from SRC, never from the throwaway tree: the temp trees must never
    contain a credential.
    """
    path = os.path.join(SRC, "secrets.yaml")
    if not os.path.exists(path) or yaml is None:
        return None, None
    try:
        with io.open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:
        # A malformed secrets.yaml is not this harness's problem to report; the
        # audit will still say live-check-skipped, which is the honest outcome.
        return None, None
    cmd = data.get("ha_audit_cmd")
    if not isinstance(cmd, str):
        return None, None
    tok = re.search(r"HA_TOKEN=(\S+)", cmd)
    url = re.search(r"HA_URL=(\S+)", cmd)
    return (tok.group(1) if tok else None), (url.group(1) if url else None)


def run_audit(tree):
    env = dict(os.environ, HA_CONFIG=tree)
    # GIVE THE CHILD AUDIT THE SAME CREDENTIAL THE NIGHTLY RUN USES.
    # Without it the audit under test has no live entity union, sun.sun reports
    # as unresolved, and entity-ref-unresolved fires on the CLEAN tree - so the
    # suite was testing a configuration we do not ship (found 2026-08-25 when
    # Bill ran the button on the HA host). Environment only; nothing is written.
    # Env wins, exactly as CLAUDE.md specifies for the InfluxDB credentials, so
    # an explicit export still overrides this and nothing that worked changes.
    if not env.get("HA_TOKEN"):
        tok, url = _creds_from_secrets()
        if tok:
            env["HA_TOKEN"] = tok
            if url and not env.get("HA_URL"):
                env["HA_URL"] = url
    r = subprocess.run([sys.executable, os.path.join(tree, "scripts", "ha_audit.py")],
                       env=env, capture_output=True, text=True, timeout=600)
    return (r.stdout or "") + (r.stderr or "")


def fired(out):
    """Rule ids that produced a FAIL or WARN."""
    return {r for r, _m in findings(out)}


def findings(out):
    """(rule_id, message) pairs.

    RULE ID ALONE IS NOT ENOUGH. Direction 1 used to subtract clean-tree rule
    IDS from faulty-tree rule IDS, which silently erases any rule that already
    fires for an unrelated reason - the injected fault then reads as "did not
    fire" when it fired correctly with a different message. Found 2026-08-25:
    entity-ref-unresolved fires on the clean tree whenever the live check is
    skipped (the sun.sun false positive), so its injector reported a failure it
    had not caused. Comparing messages distinguishes the two.
    """
    out_set = set()
    for line in out.splitlines():
        m = re.match(r"^(FAIL|WARN)\s+([a-z0-9-]+)\s+(.*)$", line)
        if m:
            out_set.add((m.group(2), m.group(3).strip()))
    return out_set


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
    covered = set(r for r, _ in all_faults)
    testable, info_only = inventory()
    uncovered = sorted(testable - covered)
    ghosts = sorted(covered - testable)
    if a.list:
        print("COVERED (%d):" % len(covered))
        for rid in sorted(covered):
            print("   ", rid)
        print("\nNOT COVERED (%d) - no fault injector written yet:" % len(uncovered))
        for rid in uncovered:
            print("   ", rid)
        if info_only:
            print("\nINFO-ONLY (%d) - untestable here by construction, because "
                  "fired() matches FAIL|WARN:" % len(info_only))
            for rid in sorted(info_only):
                print("   ", rid)
        if ghosts:
            print("\nSTALE INJECTORS (%d) - assert a rule id ha_audit.py no "
                  "longer emits:" % len(ghosts))
            for rid in ghosts:
                print("   ", rid)
        print("\ncoverage: %d of %d testable rule ids (%.0f%%)"
              % (len(covered), len(testable),
                 100.0 * len(covered) / max(len(testable), 1)))
        return 0

    # The clean tree's own findings ARE the baseline. Direction 1 asserts each
    # rule id appears in (faulty - clean), so a genuine WARN in the live house
    # can neither mask a rule nor fail the suite - which it did until
    # 2026-08-25, contradicting DoD step 2 ("WARN count must not INCREASE").
    #
    # This also retires `expected_noise`, whose sentinel was keyed off HA_URL
    # while the audit gates its live fetch on HA_TOKEN. Following the command
    # documented in CLAUDE.md (HA_URL, no token) made the harness expect
    # silence, get live-check-skipped, and report a spurious SUITE FAILED.
    # A skip now appears in BOTH trees and cancels.
    work = tempfile.mkdtemp(prefix="ha_audit_test_")
    failures = []
    try:
        # ---- direction 2: clean tree must be clean ------------------------
        say("DIRECTION 2  clean tree must produce no FAIL/WARN")
        clean = build_tree(os.path.join(work, "clean"))
        clean_out = run_audit(clean)
        clean_findings = findings(clean_out)
        clean_ids = {r for r, _ in clean_findings}
        # When the live check did not run, the audit is measurably worse: the
        # sun.sun false positive returns (CLAUDE.md, SESSION PROTOCOL). Any
        # covered rule firing on the clean tree in that state is an ENVIRONMENT
        # gap, not a broken rule, and saying "X fired on the CLEAN tree" without
        # that context sends you hunting the wrong thing.
        live_skipped = "live-check-skipped" in clean_ids

        # ONLY these rules read the live entity union, so only these can be
        # false-positived by its absence. Attaching the explanation to any
        # other rule is a confident wrong answer - the first cut of this note
        # put it on generated-doc-stale, whose actual fix is gen_reference.py.
        LIVE_DEPENDENT = {"entity-ref-unresolved", "phantom-entity-id",
                          "entity-missing", "doc-ids", "generated-doc-ghost"}

        def why_for(rid):
            if live_skipped and rid in LIVE_DEPENDENT:
                return (" -- ENVIRONMENT, not a broken rule: the live check did "
                        "not run here (no HA_TOKEN), which reintroduces the "
                        "known sun.sun false positive. Give the harness a token "
                        "so it tests the audit as actually deployed.")
            return ""
        if clean_ids:
            # Shown, never hidden (R8), but not a suite failure: these are
            # findings about the HOUSE, not about the audit.
            say("   baseline: %d pre-existing finding(s) in the live config, "
                "excluded from direction 1" % len(clean_ids))
            for rid in sorted(clean_ids):
                say("      - %s" % rid)
        else:
            say("   OK - clean tree silent")
        # R7 direction 2, stated per rule: a covered rule must NOT fire on a
        # clean tree. Sharper than "no findings at all", and unaffected by
        # whatever else the house happens to be reporting today.
        compromised = set()
        for rid, _fn in [(r, f) for r, f in all_faults if not a.only or r == a.only]:
            if rid in clean_ids:
                compromised.add(rid)
                failures.append("%s fired on the CLEAN tree%s" % (rid, why_for(rid)))
                say("   FAIL - %s fired with no fault injected%s" % (rid, why_for(rid)))

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
            # Message-level delta, so a rule that already fires for another
            # reason can still be shown to have fired for THIS fault.
            got = {r for r, _m in findings(run_audit(tree)) - clean_findings}
            for rid, _ in batch:
                ok = rid in got
                say("   %-4s %s" % ("OK" if ok else "FAIL", rid))
                if not ok:
                    failures.append("%s did not fire" % rid)

        for rid, fn in solo:
            say("\nDIRECTION 1  %s (isolated)" % rid)
            tree = build_tree(os.path.join(work, "solo_" + rid))
            fn(tree)
            got = {r for r, _m in findings(run_audit(tree)) - clean_findings}
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
            "covered": len(covered),
            "total_rule_ids": len(testable),
            "uncovered": uncovered,
            "info_only": sorted(info_only),
        }))
        return 1 if failures else 0

    print("\n" + "=" * 60)
    if failures:
        print("SUITE FAILED (%d)" % len(failures))
        for f in failures:
            print("   " + f)
        return 1
    print("SUITE PASSED - %d rule(s) proven in both directions" % len(selected))
    print("%d of %d testable rule ids covered; run --list for the gap"
          % (len(covered), len(testable)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
