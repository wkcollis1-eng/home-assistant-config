# file-map

Where things live in the config tree.

Moved verbatim out of CLAUDE.md on 2026-09-16 so it loads only when
needed. "Above"/"below" in this text may point into CLAUDE.md.

---

## FILE MAP

```
ENTITIES.md                     GENERATED — entity reference
AUTOMATIONS.md                  GENERATED — every automation, trigger, mode
PACKAGES.md                     GENERATED — package summary and counts
                                all three by scripts/gen_reference.py;
                                ha_audit FAILs if any is stale. NEVER hand-edit.
scripts/validate_ha.py          the homeassistant-config-validator skill's
                                script, vendored 2026-08-23 — the Layer 0-3 gate
docs/ha-validator-checks.md     what that validator checks, from the skill
entity_notes.yaml               hand-written MEANING for entity ids; the only
                                part of the entity reference a human maintains
open_questions.yaml             R14 made mechanical: every question asked of
                                Bill, with what it blocks. ha_audit WARNs
                                `open-question` until `answered:` is filled in,
                                so it surfaces at the top of every session.
.audit_baseline.json            the finding set `ha_audit.py --baseline` compares
                                against. NEW findings exit non-zero; a FAIL always
                                does, even an unchanged one - a baseline shows the
                                delta, it never blesses a failure.
configuration.yaml              sensors, helpers, shell_commands
automations.yaml                automation logic
scripts.yaml                    weather_update_script only - the archive seed
                                scripts were retired 2026-09-16 (CHANGELOG)

packages/                       EVERY package, with live line and domain counts:
                                see PACKAGES.md (GENERATED). Deliberately not
                                listed here. Until 2026-08-24 this block carried
                                its own counts and they drifted: spc.yaml read
                                1,787 against a real 3,610, configuration.yaml
                                ~6,500 against 7,415, automations.yaml ~2,500
                                against 4,388 — and audit.yaml, backup_sizing.yaml
                                and utility_meters.yaml were missing outright.
                                A derivable number written down twice is R10.

scripts/
├── climate_norms_today.py      Climate norms lookup
├── setback_csv.py              Setback recovery CSV logging
├── daily_energy_export.py      Energy CSV export to www/energy/
├── gate.py                     THE DEFINITION OF DONE GATE, as one command.
│                               Runs steps 1/1b/2/2b in order, stops at the
│                               first failure, and GENERATES the verdict block.
│                               Steps 3-5 stay manual - they touch the live
│                               instance (R12). Use this, not the four separate
│                               invocations; the sequence used to be written out
│                               in three places here and had already drifted.
├── new_pipeline.py             SCAFFOLDS a capture pipeline: automation with the
│                               variables: snapshot, manifest entry, schedule row,
│                               stale detector, helper names - all four pieces
│                               from one declaration. Prints; --apply writes the
│                               first two. Exists because stamp-not-snapshotted
│                               (130) and unguarded-shell-command (111) were the
│                               two most-fired rules across 38 nightly runs -
│                               241 of ~500 findings, both boilerplate omissions
│                               and every one of them a round trip. A generator
│                               makes those rules unfireable; a detector can only
│                               tell you afterwards.
├── audit_log_stats.py          Crosses www/spc/ha_audit.log against the harness
│                               coverage list. Neither signal is worth much
│                               alone - a healthy config is silent too - but a
│                               rule that has NEVER fired AND has no injector is
│                               a rule whose silence proves nothing. That set was
│                               14 on 2026-08-25 and is where both "structurally
│                               incapable of firing" bugs came from.
├── test_ha_audit.py            R7 harness for ha_audit.py: proves each covered
│                               rule FIRES on an injected fault and stays SILENT
│                               on a clean tree. `--list` prints coverage,
│                               `--only RULE` isolates. THE RULE-ID INVENTORY IS
│                               DERIVED from ha_audit.py's source - never write
│                               the count down anywhere, including here.
├── spc_validator.py            SPC diagnostic tool (queries DB + API)
├── spc_seed.py                 MANUAL CLI backfill from InfluxDB. Manifest-driven —
│                               reads pipelines.yaml, resolves each guard.live_source
│                               to the gate sensor it averages, and queries THAT.
│                               Carries no appliance constants. Prints a plan; writes
│                               nothing back without --apply. Stamps *_spc_last_seed.
├── spc_verify.py               NIGHTLY RECONCILIATION (00:25, automation
│                               nightly_spc_verify). Recomputes each appliance's
│                               daily running watts from the RAW InfluxDB series
│                               and compares it to the 23:59 capture — the only
│                               thing checking the captures against the data they
│                               summarise. Day alignment is read off the capture's
│                               own last_changed, never assumed; a slot the guards
│                               declined to overwrite reports HELD and is not
│                               compared. Exit 0/1/2 = ok/drift/could-not-run,
│                               deliberately distinct. `--days N` to tune bands.
├── grafana_snapshot.py         LOCAL Grafana snapshots (every 6h, automation
│                               grafana_snapshot_scheduled). Archival, NOT
│                               verification — a snapshot preserves a wrong panel
│                               faithfully. Needs `grafana_token` in secrets.yaml;
│                               without it exits 2 and says so. `--probe` first.
├── spc_continuous_queries.sql  InfluxDB CQs for daily SPC aggregation
├── csv_manager.py              CSV utilities
└── fetch_bdl_degree_days.py    BDL degree day fetcher

grafana/
├── dashboards/
│   ├── energy.json             Energy monitoring dashboard
│   ├── hvac_status.json        HVAC system status + cooling efficiency
│   ├── battery_bank.json       Battery bank status dashboard
│   ├── ups.json                UPS status dashboard
│   └── spc_appliances.json     SPC control charts
└── provisioning/
    └── dashboards/
        └── default.yaml        Dashboard provisioning config

dashboards/cards/               Lovelace YAML snippets only
dashboards/views/               HAND-MAINTAINED complete views, for the raw
                                configuration editor. May be deliberately AHEAD
                                of what is live, holding corrections not yet
                                pasted in. Kept in the repo so ha_audit.py can
                                resolve its entity references - a dashboard is
                                the one place a broken entity is completely
                                silent: no log line, no unavailable state, just
                                an empty card.
dashboards/lovelace/            GENERATED by scripts/export_dashboards.py - a
                                mirror of every live dashboard, one file per
                                dashboard plus _dashboards/_resources. This is
                                the ONLY backup of .storage/lovelace.*, which is
                                gitignored and off-limits to edit; before
                                2026-08-24 the 16 views across 4 dashboards had
                                no copy and no history anywhere.
                                RESTORE FROM HERE, paste into the raw editor.
                                NOTHING CHECKS IT FOR STALENESS - ha_audit does
                                not know about it, so re-run the script after
                                any UI dashboard edit (R8: said out loud so the
                                file does not imply a check that is not there).
reports/                        CSV outputs — DO NOT edit manually
www/energy/                     Daily energy CSVs (energy_YYYY-MM-DD.csv)
esphome/                        ESPHome device configs
custom_components/              HACS custom integrations
baseline-repo/                  HVAC Baseline repo reference

.storage/                       BLOCKED — HA-managed JSON — never edit
CLAUDE.md                       this file — authoritative
CHANGELOG.md                    CalVer YYYY.MM — update on behavior changes
```

---
