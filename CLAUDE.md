# HA CONFIG — CLAUDE CODE SESSION RULES

## PROJECT GOALS (never violate — supersede all other rules when in conflict)

```
1. Zero data loss or corruption — archives, CSVs, input_numbers are permanent records
2. All automations must be idempotent, restart-safe, and trigger-reentrant
3. Maximize debuggability — every change leaves clear audit trail in logs + CHANGELOG
4. MUST use explicit variables: snapshots for all EOD and time-critical automations — live sensor reads forbidden at trigger time
5. Strict separation — monthly data updates NEVER mixed with config/automation changes
```

## CONSTRAINTS

Entity ID rules:
  Listed in §FRAGILE → use verbatim — no expansion, no inference
  NOT in §FRAGILE → read ENTITIES.md first; expansion allowed ONLY IF grep confirms exact match AND no _2 variant exists
  → flag for ENTITIES.md addition in same commit
  _2 FRAGILE entities → always use listed ID exactly — no substitution ever
NEVER edit .storage/* — corrupts dashboards unrecoverably
NEVER overwrite/truncate CSV files — append/rotate only
NEVER add time triggers between 23:54:30–23:58:45
NEVER use `| float` or `| int` without default: `| float(0)` `| int(0)`
NEVER commit multiple unrelated changes — "unrelated" = more than one automation ID or sensor name
NEVER remove inline YAML comments
NEVER reuse an automation trigger ID — must be globally unique across automations.yaml
NEVER auto-resolve §PENDING items unless explicitly instructed
NEVER use numeric_state trigger on raw live sensor (outdoor_temp_live, pirate_weather_*, voltge) without `for:` debounce
NEVER issue notify service call without explicit message payload
NEVER allow two automations writing the same input_number simultaneously without sequencing
NEVER use direct IDLE→RECOVERING state transition — valid path: IDLE→SETBACK_ACTIVE→RECOVERING→IDLE only
NEVER call a service targeting a template-derived entity where that sensor lacks availability: guard

MUST add `default: []` to every `choose:` block
MUST add `availability:` guard to every new template sensor
MUST wrap every `shell_command.*` call with ha_maintenance_mode guard (§SYSTEM STATE P2)
  → While P2 unresolved: flag ⚠ P2 UNRESOLVED in diff header; proceed only if user says "proceed" in current turn
MUST update §ENTITIES + CHANGELOG.md in same commit as any new entity

## EXECUTION PROTOCOL

Before any edit:
1. `python3 tools/analyze_ha.py` — record baseline error count
2. `grep -rnw . -e '<entity_id>' --include="*.yaml" --include="*.json" --include="*.py"` — impact scan
3. Automation edits only: `grep -A2 'trigger:' automations.yaml | grep 'id:'` — confirm no trigger ID conflict

After edit:
- Re-run analyzer — zero new hard errors
- Update §ENTITIES if any new entity added
- Update CHANGELOG.md if behavior changed
- One logical change per commit

Output format — Risk: LOW=new sensor/no deps | MEDIUM=automation logic/helper/existing sensor | HIGH=EOD/_2 entities/shell_command/state machine

LOW: diff only (unified, ±3 lines context) + `analyzer: PASS|FAIL`

MEDIUM: prepend `Change type / Impacted files / Risk: MEDIUM`

HIGH: prepend simulation block:
```
Simulation:
  Trigger / Condition result / Action / Side effects / Race risk
```

Hard errors (block commit): missing entity, invalid template, trigger collision, unsafe shell_command, missing default: []
Never rewrite full files. Touch only lines required by the change.
If no change needed: NO CHANGE — [reason] + optional ANALYSIS block (see §FAIL-CLOSED)

## FAIL-CLOSED

If any CONSTRAINT is violated, requirement is ambiguous, or cannot be resolved from CLAUDE.md alone:
→ NO CHANGE — [reason]

ANALYSIS block — always permitted after NO CHANGE, never executes, never modifies files:
```
NO CHANGE — [reason]

ANALYSIS (non-executing):
  Observed:  [what triggered the block]
  Cause:     [likely root cause]
  Fix:       [exact instruction that would unblock this]
```

## EOD TIMING SEQUENCE — FROZEN

```
23:55:00  capture_daily_hdd               hdd_day_1–7 only + hdd_capture_last_ok
23:56:00  capture_daily_runtime_per_hdd   runtime_per_hdd_day_1–7
23:56:15  capture_daily_furnace_min_per_cycle
23:56:30  capture_daily_monthly_tracking  ALL month accumulators → sets monthly_tracking_capture_last_ok
23:57:00  csv_daily_report
23:58:00  archive_monthly_hdd + accumulate_filter_runtime  [known collision — separate entities, no data risk]
          accumulate_filter_runtime: live read intentional — accumulator pattern, not snapshot; variables: not required
23:58:30  csv_monthly_report (last day of month only)
```

RULES:
  23:56:30 immovable — all month sensors depend on monthly_tracking_capture_last_ok
  New month accumulators → capture_daily_monthly_tracking only (NOT capture_daily_hdd)
  EOD automations MUST use variables: block; adding logic/entities permitted if block present or added same commit
  Exception — accumulate_filter_runtime: live read intentional; variables: not required

## NEW SENSOR TEMPLATE

Required pattern — use verbatim:

```yaml
- name: "Sensor Name"
  availability: "{{ states('sensor.source') not in ['unknown','unavailable','none',''] }}"
  state: >
    {% set v = states('sensor.source') %}
    {{ v | float(0) if v not in ['unknown','unavailable','none',''] else 0 }}
```

## SYSTEM STATE

### P1 — Add `default: []` to choose: blocks [LOW — exception ACTIVE]
```
update_outdoor_temp_daily_high_low   2 choose: blocks, 0 default:
validate_input_numbers_startup       3 choose: blocks, 0 default:
P1 exception: address automatically when editing either automation ID above.
```

### P2 — Add ha_maintenance_mode guard to all shell_command calls [HIGH — data risk]
```
1. Create input_boolean.ha_maintenance_mode (toggle, default OFF)
2. Wrap these 7 automations:
     csv_daily_report, csv_monthly_report, csv_yearly_rotation,
     backup_input_numbers_weekly, rotate_setback_log_yearly,
     hvac_1f_recovery_end, hvac_2f_recovery_end
3. Add Lovelace toggle (red when ON)
4. Add to §ENTITIES
```

### Known Issues
```
shell_command.testcmd        config.yaml:16 — never called — do not remove proactively
23:58:00 collision           archive_monthly_hdd + accumulate_filter_runtime — FAIL-CLOSED if new concurrent write added without documentation
_2 suffix entities           8 confirmed canonical IDs — DO NOT DELETE (full audit of "10 sensors" claim incomplete)
duplicate trigger IDs        reset_monthly_hdd + reset_yearly_hdd both define id: scheduled and id: startup
                             fix required before next edit to either automation
voltge typo                  sensor.shelly_plus_uni_voltge — intentional entity registry typo — DO NOT CORRECT
```

## ENTITIES

Entity lookup: read ENTITIES.md before referencing any entity not in §FRAGILE below.
New entities: add to ENTITIES.md in same commit; add here only if _2 suffix.

### FRAGILE — _2 SUFFIX (canonical IDs — NOT typos — DO NOT DELETE)
```
sensor.hdd_rolling_7_day_auto_2
sensor.hvac_runtime_per_hdd_7_day_2              hardcoded in notify_runtime_per_hdd_high/low messages — DO NOT CHANGE
sensor.hvac_runtime_per_hdd_7_day_mean_2         hardcoded in notification messages — DO NOT CHANGE
sensor.hvac_runtime_per_hdd_7_day_std_dev_2      hardcoded in notification messages — DO NOT CHANGE
sensor.hvac_furnace_runtime_month_2
sensor.hvac_furnace_cycles_month_2
sensor.hvac_1f_heat_cycles_month_2
sensor.hvac_2f_heat_cycles_month_2
weather.local_weather_2
```

## MONTHLY DATA ENTRY PROTOCOL

Any gas / electric / DHW / bill entry MUST follow the engineering-monthly-update skill.

```
ALWAYS use button/automation paths: input_button.save_electric_bill, input_button.save_gas_bill, input_button.save_dhw
ALWAYS verify Therms→CCF conversion (×0.9643) before archiving DHW figures
```

## FILE MAP
```
configuration.yaml     sensors, helpers, shell_commands
automations.yaml       automations
scripts.yaml           bill archive seed scripts
ENTITIES.md            full entity ID registry — read on demand
CHANGELOG.md           CalVer YYYY.MM — update on behavior changes
tools/analyze_ha.py    static analyzer — run before every commit
reports/               CSV outputs — DO NOT edit manually
dashboards/cards/      Lovelace YAML snippets only
.storage/              BLOCKED — HA-managed JSON — never edit
scripts/               climate_norms_today.py, setback_csv.py
```

New guardrails → CONSTRAINTS or SYSTEM STATE. Commit as: `docs: update CLAUDE.md — [reason]`
CLAUDE.md gets stricter over time. Any relaxation requires explicit user instruction + CHANGELOG entry.
