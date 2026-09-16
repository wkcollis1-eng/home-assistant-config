# ha-ui-actions

Running the audit, gate and self-tests from the HA UI with no terminal.

Moved verbatim out of CLAUDE.md on 2026-09-16 so it loads only when
needed. "Above"/"below" in this text may point into CLAUDE.md.

---

### Running any of this from the HA UI, with no terminal

Developer Tools > Actions, added 2026-08-25. Each returns its output in the
response pane AND as a notification, and each carries the
`ha_maintenance_mode` guard:

| action | what it runs |
|---|---|
| **Run ALL HA Config Checks** (`script.ha_run_all_checks`) | audit + self-tests + coverage, in order, reporting each separately |
| Run HA Audit (`script.ha_audit`) | `ha_audit.py --json` |
| Run Config Gate (`script.ha_gate`) | `gate.py` — steps 1/1b/2/2b |
| Run HA Audit Self-Tests (`script.ha_audit_tests`) | `test_ha_audit.py` both directions |
| HA Audit — Rule Coverage (`script.ha_audit_log_stats`) | which rules have never fired AND have no injector |
| Run Provenance Check (`script.ha_provenance`) | R17, git-free mode |
| Regenerate Reference Docs (`script.ha_gen_reference`) | `gen_reference.py`. **Defaults to `--check`, which writes nothing**; flip *Write the files* on to actually regenerate. The one action that writes — run it with Write ON after any RESTART that added entities, because the registry only gains them at startup and `ha_audit` FAILs on a stale generated doc. |

`binary_sensor.ha_eod_contention` (device_class problem) lights whenever any
`eod-*` FAIL is present, separately from `binary_sensor.ha_audit_failing` —
contention is the one failure class that corrupts DATA rather than reporting,
so it gets its own light rather than a share of a number.

`new_pipeline.py` is deliberately NOT exposed as an action: it is the only
script that mutates `automations.yaml`, and a one-click button for that with no
diff and no undo is the wrong shape.

**shell_command is not reloadable — adding or changing any of these needs a
RESTART.**
