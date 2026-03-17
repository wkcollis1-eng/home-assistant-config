# HA CONFIG — CLAUDE CODE SESSION RULES

## PROJECT GOALS (never violate — supersede all other rules when in conflict)

```
1. Zero data loss or corruption — archives, CSVs, input_numbers are permanent records
2. All automations must be idempotent, restart-safe, and trigger-reentrant
3. Maximize debuggability — every change leaves clear audit trail in logs + CHANGELOG
4. MUST use explicit variables: snapshots for all EOD and time-critical automations — live sensor reads forbidden at trigger time
   → Applies to new and edited EOD automations; pre-existing violations tracked in §PENDING P3 (closed Mar 2026)
5. Strict separation — monthly data updates NEVER mixed with config/automation changes
```

---

## CONSTRAINTS (CHECK BEFORE ANY ACTION)

NEVER infer entity IDs from patterns — use only IDs listed in §ENTITIES
NEVER edit .storage/* — corrupts dashboards unrecoverably
NEVER overwrite/truncate CSV files — append/rotate only
NEVER add time triggers between 23:54:30–23:58:45
NEVER use `| float` or `| int` without default: use `| float(0)` `| int(0)`
NEVER commit multiple unrelated changes in one commit
  → "Unrelated" = more than one automation ID or more than one sensor name; cross-file changes require justification in diff header
NEVER remove inline YAML comments
NEVER reuse an automation trigger ID — all trigger IDs must be globally unique across automations.yaml
NEVER auto-resolve §PENDING items unless explicitly instructed (see PENDING POLICY)

MUST run `python3 tools/analyze_ha.py` before every commit — zero hard errors required
MUST add `default: []` to every `choose:` block
MUST add `availability:` guard to every new template sensor
MUST wrap every `shell_command.*` call with ha_maintenance_mode guard (§PENDING P2)
  → While P2 unresolved: flag each unguarded call as ⚠ P2 UNRESOLVED in diff header; proceed only if user says "proceed" in the current turn
MUST update §ENTITIES + CHANGELOG.md in same commit as any new entity

---

## FAIL-CLOSED POLICY

If ANY of the following occur:
- Entity ID not found in §ENTITIES
- `python3 tools/analyze_ha.py` would produce new hard errors
- Requirement is ambiguous — cannot be resolved from CLAUDE.md alone without inferring
- Trigger collision detected anywhere in automations.yaml
- Unguarded shell_command call and user has not said "proceed" in the current turn
- Concurrent writes to archive_monthly_hdd and accumulate_filter_runtime outside the documented 23:58:00 known collision

Then:
→ OUTPUT ONLY "NO CHANGE — [reason]"
→ DO NOT GUESS, DO NOT PARTIALLY FIX
→ DO NOT PROCEED until ambiguity is resolved by user

---

## PENDING POLICY

PENDING items: DO NOT address unless explicitly instructed.
Exception: P1 (default: [] additions) MUST be addressed if the automation being edited matches a P1 automation ID in §PENDING.
All other PENDING items: treat as read-only context.

---

## STEP 0 — REQUIRED BEFORE ANY EDIT

1. `python3 tools/analyze_ha.py` — record baseline error count
2. `grep -rnw . -e '<entity_id>' --include="*.yaml" --include="*.json" --include="*.py"` — impact scan
3. For automation edits: `grep -A2 'trigger:' automations.yaml | grep 'id:'` — confirm no trigger ID conflicts

New errors beyond baseline = FAIL regardless of absolute count.
HIGH risk: re-run analyzer after edit; report both counts.

---

## OUTPUT FORMAT

**LOW / DOCUMENTATION** — output only:
```diff
[minimal diff — unified format, ±3 lines context max]
```
`analyzer: PASS|FAIL`

**MEDIUM** — prepend:
```
Change type: <SENSOR|AUTOMATION|ENTITY rename|DASHBOARD|CSV|ANALYZER|DOCUMENTATION>
Impacted files: <list>
Risk class: MEDIUM
```

**HIGH** — prepend simulation block before diff:
```
Simulation:
  Trigger: [what fires it]
  Condition result: [PASS/FAIL + reason]
  Action: [what executes]
  Side effects: [any other entity written]
  Race risk: [none | describe]
```

Hard errors (block commit): missing entity, invalid template, trigger collision, unsafe shell_command, missing default: []
Soft warnings (do not block): non-critical availability gaps

If no change needed: reply ONLY `NO CHANGE — [reason]`
Never rewrite full files. Explain reasoning only for MEDIUM/HIGH or when asked.

Diff discipline:
- Touch only lines required by the change
- DO NOT reorder YAML keys or reformat unrelated sections
- Unrelated lines in diff → remove or output NO CHANGE

---

## COMMIT OUTCOMES (required — order is your choice)

- `python3 tools/analyze_ha.py` passes with zero new hard errors
- §ENTITIES updated if any new entity added
- CHANGELOG.md updated if behavior changed
- One logical change per commit

---

## EOD TIMING SEQUENCE — FROZEN

```
23:55:00  capture_daily_hdd               hdd_day_1–7 only + hdd_capture_last_ok
23:56:00  capture_daily_runtime_per_hdd   runtime_per_hdd_day_1–7
23:56:15  capture_daily_furnace_min_per_cycle
23:56:30  capture_daily_monthly_tracking  ALL month accumulators → sets monthly_tracking_capture_last_ok
23:57:00  csv_daily_report
23:58:00  archive_monthly_hdd + accumulate_filter_runtime  [known collision — separate entities, no data risk]
23:58:30  csv_monthly_report (last day of month only)
```

RULE: 23:56:30 is immovable — all month sensors depend on `monthly_tracking_capture_last_ok`
RULE: New month accumulators → add to `capture_daily_monthly_tracking`, NOT `capture_daily_hdd`
RULE: EOD automations MUST use `variables:` block — all four confirmed present (P3 closed Mar 2026)
RULE: FROZEN = trigger times only; adding logic/entities permitted if variables: block present or added in same commit

```yaml
# Snapshot pattern — prevents midnight boundary re-eval
variables:
  hdd_today: "{{ states('sensor.hvac_hdd65_today') | float(0) }}"
action:
  - service: input_number.set_value
    data:
      value: "{{ hdd_today }}"
```

---

## TEMPLATE PATTERNS

```yaml
# Defensive sensor (REQUIRED for all new sensors)
- name: "Sensor Name"
  availability: "{{ states('sensor.source') not in ['unknown','unavailable','none',''] }}"
  state: >
    {% set v = states('sensor.source') %}
    {{ v | float(0) if v not in ['unknown','unavailable','none',''] else 0 }}

# Maintenance guard (REQUIRED before every shell_command)
- condition: state
  entity_id: input_boolean.ha_maintenance_mode
  state: "off"
- service: shell_command.COMMAND_NAME

# choose block (REQUIRED default)
- choose:
    - conditions: [...]
      sequence: [...]
  default: []
```

---

## PROTECTED SYSTEMS — DO NOT MODIFY WITHOUT EXPLICIT REQUEST

```
EOD TIMING SEQUENCE        23:54:30–23:58:45 — frozen, no additions or shifts
_2 suffix entities         8 confirmed (see §ENTITIES FRAGILE) — canonical IDs — DO NOT DELETE
runtime_per_hdd alerts     notify_runtime_per_hdd_high/low — entity IDs hardcoded in message templates
climate_norms calculations sensor.climate_norms_today + dependent sensors
```

---

## CHANGE RISK CLASSIFICATION

```
LOW:    new sensor, no downstream dependencies, no automation logic
MEDIUM: automation logic change, new helper, existing sensor modification
HIGH:   EOD timing sequence, _2 suffix entities, shared accumulators,
        alert thresholds, shell_command calls, state machine transitions
```

---

## DANGEROUS PATTERNS — AUTO-REJECT

Reject and output NO CHANGE if edit would introduce any of:

```
- numeric_state trigger on raw live sensor (outdoor_temp_live, pirate_weather_*, voltge)
  without `for:` debounce duration
- template sensor without availability: guard
- shell_command call without ha_maintenance_mode condition (unless P2 unresolved — then flag only)
- notify service call without explicit message payload
- two automations writing same input_number simultaneously without sequencing
- time trigger in EOD window 23:54:30–23:58:45
- automation trigger ID already present anywhere in automations.yaml
- direct state transition IDLE→RECOVERING in setback state machine
  (valid: IDLE→SETBACK_ACTIVE→RECOVERING→IDLE only)
- EOD capture automation without variables: snapshot block
- EOD automation action using states('sensor.xxx') directly instead of snapshot variable
- time-critical automation without variables: snapshot block
  → "EOD dependency" = any automation reading an input_number or input_datetime written in the 23:54:30–23:58:45 window
- `| float` or `| int` without (0) default
- service call targeting a template-derived entity where that sensor lacks availability: guard
```

---

## PRE-COMMIT CHECKLIST

- [ ] analyzer: zero hard errors
- [ ] New entity IDs added to §ENTITIES
- [ ] CHANGELOG.md updated if behavior changed
- [ ] No `_1s` `_3` or unexpected suffix entities introduced
- [ ] Automation trigger ID globally unique — grep confirmed
- [ ] Multi-line Jinja2 uses `>` or `|` with 2-space indent

---

## ENTITIES

### FRAGILE — _2 SUFFIX (entity registry conflicts — canonical, NOT typos — DO NOT DELETE)
8 confirmed. Treat any _2 suffix entity encountered in config as fragile until full audit complete.
```
sensor.hdd_rolling_7_day_auto_2                  7-day rolling HDD
sensor.hvac_runtime_per_hdd_7_day_2              7-day runtime/HDD — hardcoded in notify_runtime_per_hdd_high/low
sensor.hvac_runtime_per_hdd_7_day_mean_2         rolling mean — hardcoded in notification messages
sensor.hvac_runtime_per_hdd_7_day_std_dev_2      rolling std dev — hardcoded in notification messages
sensor.hvac_furnace_runtime_month_2              MTD furnace runtime
sensor.hvac_furnace_cycles_month_2               MTD furnace cycles
sensor.hvac_1f_heat_cycles_month_2               1F zone MTD cycles — used in chaining index
sensor.hvac_2f_heat_cycles_month_2               2F zone MTD cycles — used in chaining index
weather.local_weather_2                          NWS/NOAA [also in WEATHER]
```

### THERMOSTATS
```
climate.tstat_2d884c_lyric_t6_pro_thermostat     1F
climate.tstat_2d8878_lyric_t6_pro_thermostat     2F
```

### WEATHER
```
sensor.outdoor_temp_live                         Open-Meteo 10-min
sensor.hvac_outdoor_temp_hartford_proxy          combined source (Live>Pirate>NWS>Open-Meteo)
weather.local_weather_2                          NWS/NOAA  [_2 FRAGILE]
weather.home                                     Open-Meteo
weather.pirateweather                            Pirate Weather (HACS)
sensor.pirate_weather_temperature
sensor.pirate_weather_feels_like
sensor.pirate_weather_humidity
sensor.pirate_weather_pressure
sensor.pirate_weather_wind_speed
sensor.pirate_weather_wind_bearing
sensor.pirate_weather_wind_direction
sensor.pirate_weather_visibility
sensor.pirate_weather_cloud_cover
sensor.pirate_weather_dew_point
sensor.pirate_weather_uv_index
sensor.pirate_weather_ozone
sensor.pirate_weather_condition
sensor.pirate_weather_today_high
sensor.pirate_weather_today_low
sensor.pirate_weather_today_precip_prob
sensor.pirate_weather_today_condition
sensor.pirate_weather_tomorrow_high
sensor.pirate_weather_tomorrow_low
sensor.pirate_weather_tomorrow_precip_prob
sensor.pirate_weather_tomorrow_condition
sensor.pirate_weather_hdd_forecast_today
sensor.pirate_weather_cdd_forecast_today
sensor.pirate_weather_hdd_forecast_tomorrow
sensor.pirate_weather_hdd_forecast_7day
sensor.pirate_weather_data_age
```

### HDD/CDD
```
sensor.hvac_hdd65_today
sensor.hvac_cdd65_today
sensor.hdd_rolling_7_day_auto_2                  [_2 FRAGILE]
input_number.hdd_day_1 … hdd_day_7
input_number.hdd_cumulative_month_auto
input_number.hdd_cumulative_year_auto
input_number.cdd_cumulative_month_auto
input_number.cdd_cumulative_year_auto
input_datetime.hdd_capture_last_ok               EOD capture timestamp
```

### CLIMATE NORMS
```
sensor.climate_norms_today
sensor.expected_hdd_today
sensor.expected_cdd_today
sensor.expected_temperature_today
sensor.hdd_deviation_today
sensor.expected_runtime_today
sensor.efficiency_deviation_index
sensor.climate_norms_status
binary_sensor.climate_cold_snap_today
binary_sensor.climate_adjusted_efficiency_alert
```

### ENERGY METRICS
```
sensor.site_eui_estimate
sensor.hvac_heating_efficiency_12m
sensor.hvac_building_load_ua_12m
sensor.dhw_gas_12m
sensor.hvac_heating_efficiency_mtd
sensor.hvac_building_load_ua_estimate
sensor.gas_heating_usage_month
sensor.gas_dhw_usage_month
```

### DHW ARCHIVES
```
input_number.dhw_archive_jan … dhw_archive_dec
input_number.dhw_bill_thm                        entry field (Therms → auto CCF)
input_button.save_dhw
```

### ELECTRIC BILL ARCHIVES
```
input_button.save_electric_bill
input_datetime.electricity_bill_date
input_number.electricity_bill_amount / _previous / _last_year
input_number.electricity_bill_days / _previous
input_number.electricity_bill_kwh / _previous / _last_year
```

### GAS BILL ARCHIVES
```
input_button.save_gas_bill
input_datetime.gas_bill_date
input_number.gas_bill_amount / _previous / _last_year
input_number.gas_bill_days / _previous
input_number.gas_bill_ccf / _previous / _last_year
```

### FILTER
```
input_number.hvac_filter_runtime_hours
sensor.hvac_filter_hours_remaining
input_datetime.hvac_filter_last_changed
input_button.reset_filter_runtime
binary_sensor.hvac_filter_change_alert           fires at >= 1000 hrs
```

### EFFICIENCY MONITORING
```
sensor.hvac_runtime_per_hdd_7_day_2              [_2 FRAGILE] primary operational metric
sensor.hvac_total_runtime_per_hdd_today
sensor.hvac_1f_runtime_per_hdd_today
sensor.hvac_2f_runtime_per_hdd_today
binary_sensor.hvac_runtime_per_hdd_high_alert    >mean+2σ
binary_sensor.hvac_runtime_per_hdd_low_alert     <mean-2σ
```

### FURNACE CYCLE TRACKING
```
binary_sensor.hvac_furnace_running
binary_sensor.hvac_furnace_short_cycling_alert   suppressed during recovery
sensor.hvac_furnace_cycles_today
sensor.hvac_furnace_cycles_week
sensor.hvac_furnace_cycles_month_2               [_2 FRAGILE]
sensor.hvac_furnace_runtime_today
sensor.hvac_furnace_runtime_week
sensor.hvac_furnace_runtime_month_2              [_2 FRAGILE]
sensor.hvac_furnace_min_per_cycle
sensor.hvac_furnace_min_per_cycle_week
sensor.hvac_furnace_min_per_cycle_month
sensor.hvac_furnace_cycle_mean_7d
sensor.hvac_furnace_cycle_sigma_7d
sensor.hvac_furnace_cycle_upper_bound
sensor.hvac_furnace_cycle_lower_bound
sensor.hvac_furnace_cycle_data_count
input_number.furnace_min_per_cycle_day_1 … _7
sensor.hvac_furnace_cycles_per_day_week / _month
sensor.hvac_chaining_index / _week / _month
sensor.hvac_zone_overlap_today / _week / _month / _percent
sensor.hvac_total_cycles_week / _month
sensor.hvac_1f_heat_cycles_today / hvac_1f_heat_runtime_today
sensor.hvac_2f_heat_cycles_today / hvac_2f_heat_runtime_today
sensor.hvac_total_heat_runtime_today
sensor.hvac_zone_balance_ratio_today
sensor.hvac_1f_heat_cycles_month_2               [_2 FRAGILE]
sensor.hvac_2f_heat_cycles_month_2               [_2 FRAGILE]
```

### RUNTIME/HDD STATISTICS
```
sensor.hvac_runtime_per_hdd_7_day_mean_2         [_2 FRAGILE]
sensor.hvac_runtime_per_hdd_7_day_std_dev_2      [_2 FRAGILE]
sensor.hvac_runtime_per_hdd_upper_bound
sensor.hvac_runtime_per_hdd_lower_bound
sensor.hvac_runtime_per_hdd_data_count           alerts suppressed if <4
input_number.runtime_per_hdd_day_1 … _7
input_datetime.runtime_per_hdd_capture_last_ok   EOD capture timestamp
input_datetime.furnace_cycle_capture_last_ok     EOD capture timestamp
```

### MONTHLY REPORT
```
sensor.outdoor_temp_mean_month
sensor.expected_runtime_month
sensor.efficiency_deviation_month
sensor.hvac_runtime_per_hdd_month
input_datetime.monthly_tracking_capture_last_ok  EOD capture timestamp — gates all monthly sensors
input_number.outdoor_temp_sum_month / _days_month
input_number.outdoor_temp_daily_high / _daily_low
input_number.expected_runtime_sum_month
input_number.furnace_runtime_month_acc / furnace_cycles_month_acc
input_number.zone_1f_runtime_month_acc / zone_1f_cycles_month_acc
input_number.zone_2f_runtime_month_acc / zone_2f_cycles_month_acc
```

### SETBACK RECOVERY (state machine: IDLE→SETBACK_ACTIVE→RECOVERING→IDLE)
```
input_boolean.hvac_1f_setback_active / hvac_2f_setback_active
input_boolean.hvac_1f_recovering / hvac_2f_recovering
input_datetime.hvac_1f_setback_start / hvac_2f_setback_start
input_datetime.hvac_1f_recovery_start / hvac_2f_recovery_start
input_number.hvac_1f_hold_setpoint / hvac_2f_hold_setpoint
input_number.hvac_1f_setback_setpoint / hvac_2f_setback_setpoint
input_number.hvac_1f_recovery_start_temp / hvac_2f_recovery_start_temp
input_number.hvac_1f_last_recovery_minutes / hvac_2f_last_recovery_minutes
sensor.recommended_setback_depth
```

### DEHUMIDIFIER
```
switch.dehumidifier
sensor.dehumidifier_current
sensor.shelly_temperature_humidity_temperature
sensor.shelly_temperature_humidity_humidity
sensor.basement_dew_point
input_number.dehumidifier_dewpoint_threshold      default 52°F
binary_sensor.dehumidifier_should_run
counter.dehumidifier_cycles_today
input_number.dehumidifier_cycle_start_dp
input_number.dehumidifier_last_pull_down_rate
input_number.dehumidifier_last_cycle_minutes
input_number.dehumidifier_last_hold_hours
input_select.dehumidifier_last_stop_reason        conditions_cleared|max_runtime
input_datetime.dehumidifier_cycle_start_time
input_datetime.dehumidifier_last_cycle_end_time
sensor.dehumidifier_runtime_today / _week
sensor.dehumidifier_duty_cycle_24h
sensor.dehumidifier_avg_cycle_minutes
sensor.dehumidifier_dew_point_margin
sensor.dehumidifier_pull_down_rate
sensor.dehumidifier_hold_time                     only valid for conditions_cleared stops
```

### DAILY COST
```
sensor.hvac_daily_gas_cost_estimate
sensor.hvac_daily_electric_cost_estimate
sensor.hvac_daily_total_cost_estimate
```

### GUARDS / MODES
```
input_boolean.ha_maintenance_mode                 PENDING CREATION — gate for all shell_command calls
```

### STALE DETECTION
```
binary_sensor.hdd_capture_stale
binary_sensor.runtime_per_hdd_capture_stale
binary_sensor.furnace_cycle_capture_stale
binary_sensor.monthly_report_stale
binary_sensor.climate_norms_stale
```

### AUTOMATION HEALTH
```
counter.automation_failures_24h
input_text.last_automation_failure
```

### UPS (DIY LiFePO4 — Shelly Plus Uni)
```
sensor.shelly_plus_uni_voltge                     [INTENTIONAL TYPO — DO NOT CORRECT] battery/bus voltage 0–30V
sensor.shelly_plus_uni_temperature                DS18B20 ambient
binary_sensor.shelly_plus_uni_input               grid power presence (Pololu diode input)
```
Note: UPS phase latch entity IDs (input_boolean.ups_* — pending confirmation) to be added when HA integration commit lands. Do not reference input_boolean.ups_* in any automation until listed here.

### POWER MONITORING (Kasa plugs)
```
switch.dehumidifier / sensor.dehumidifier_current  [listed above]
```
Note: Computer Kasa plug entity IDs (pending confirmation) to be added here. Do not infer or fabricate Kasa entity IDs.

---

## AUTOMATIONS INDEX

### HDD
```
capture_daily_hdd                23:55 — hdd_day_1–7 + hdd_capture_last_ok ONLY
capture_daily_runtime_per_hdd   23:56
capture_daily_furnace_min_per_cycle  23:56:15
capture_daily_monthly_tracking  23:56:30 — ALL month accumulators + monthly_tracking_capture_last_ok
reset_monthly_hdd               1st of month  [⚠ duplicate trigger IDs: scheduled, startup — see §KNOWN ISSUES]
reset_yearly_hdd                Jan 1         [⚠ duplicate trigger IDs: scheduled, startup — see §KNOWN ISSUES]
update_outdoor_temp_daily_high_low  state change — tracks daily high/low  [P1: missing default: []]
reset_outdoor_temp_daily_high_low   midnight reset
```

### DEHUMIDIFIER
```
dehumidifier_auto_on            temp>60°F AND dp>threshold, 30-min cooldown
dehumidifier_auto_off           conditions clear OR 4h max runtime
dehumidifier_cycle_start_capture
dehumidifier_cycle_end_capture  10-min short cycle guard
dehumidifier_cycle_counter_reset midnight
```

### SETBACK RECOVERY
```
hvac_1f_setback_start / hvac_2f_setback_start     6PM+, 5s debounce
hvac_1f_setback_lowered / hvac_2f_setback_lowered
hvac_1f_recovery_start / hvac_2f_recovery_start
hvac_1f_recovery_end / hvac_2f_recovery_end        10-min stability wait → CSV log → clear latches
hvac_1f_setback_stuck_clear / hvac_2f_setback_stuck_clear   14h timeout
hvac_1f_recovery_stuck_clear / hvac_2f_recovery_stuck_clear  4h timeout
hvac_setback_midnight_audit     1AM — clears stuck latches
```

### EFFICIENCY ALERTS
```
notify_runtime_per_hdd_high     >mean+2σ  [refs _2 entities — DO NOT CHANGE entity IDs]
notify_runtime_per_hdd_low      <mean-2σ  [refs _2 entities — DO NOT CHANGE entity IDs]
notify_efficiency_degradation   DISABLED Feb 2026 — retired [tracked §PENDING P4]
notify_short_cycling_furnace    avg cycle <5min, suppressed during recovery
```

### FILTER
```
accumulate_filter_runtime       23:58
reset_filter_runtime_button
notify_filter_change_due        >= 1000 hrs
```

### BILL ARCHIVING
```
save_electric_bill_button
save_gas_bill_button
save_dhw_button                 Thm→CCF (×0.9643), archives to PREVIOUS month
```

### CSV / REPORTING
```
csv_daily_report                23:57 → shell_command.appenddailycsv          [⚠ P2 unguarded]
csv_monthly_report              23:58:30 last day → shell_command.appendmonthlycsv  [⚠ P2 unguarded]
csv_yearly_rotation             Jan 1 → shell_command.rotatedailycsv          [⚠ P2 unguarded]
backup_input_numbers_weekly     → shell_command.backup_input_numbers           [⚠ P2 unguarded]
rotate_setback_log_yearly       → shell_command.rotate_setback_log             [⚠ P2 unguarded]
hvac_1f_recovery_end            → shell_command.appendsetbacklog_1f            [⚠ P2 unguarded]
hvac_2f_recovery_end            → shell_command.appendsetbacklog_2f            [⚠ P2 unguarded]
daily_hvac_summary              daily summary notification
database_maintenance_weekly     weekly HA database purge
database_size_monitor           monitors DB size, alerts if oversized
```

### STALE / HEALTH MONITORING
```
notify_hdd_capture_stale
notify_runtime_per_hdd_capture_stale
notify_furnace_cycle_capture_stale
notify_monthly_report_stale
notify_climate_norms_stale
notify_climate_norms_failure
notify_weather_sources_down
notify_thermostat_offline
notify_pirate_weather_stale
track_automation_failures       increments counter.automation_failures_24h on automation error
reset_automation_failure_counter  midnight reset
validate_input_numbers_startup  HA start — validates key input_numbers in range  [P1: missing default: []]
```

---

## MONTHLY DATA ENTRY PROTOCOL

Any gas / electric / DHW / bill entry MUST follow the engineering-monthly-update skill.
Cross-repo sequencing is strict — never shortcut it.

```
NEVER edit HA input_number archives directly via YAML
NEVER mix a monthly bill entry commit with any config or automation change
ALWAYS use the documented button/automation paths (save_electric_bill_button, save_gas_bill_button, save_dhw_button)
ALWAYS verify Therms→CCF conversion (×0.9643) before archiving DHW figures
```

---

## PENDING

### P1 — Add `default: []` to choose: blocks [LOW — P1 exception ACTIVE]
```
Confirmed automation IDs (audit Mar 2026):
  update_outdoor_temp_daily_high_low   2 choose: blocks, 0 default:
  validate_input_numbers_startup       3 choose: blocks, 0 default:
P1 exception fires automatically when either ID is being edited.
```

### P2 — Add ha_maintenance_mode guard to all shell_command calls [HIGH — data risk]
```
Steps:
1. Create input_boolean.ha_maintenance_mode (toggle, default OFF)
2. Wrap all 7 shell_command calls in §AUTOMATIONS CSV/REPORTING
3. Add Lovelace toggle (red when ON)
4. Add to §ENTITIES
While P2 unresolved: flag each unguarded call as ⚠ P2 UNRESOLVED; proceed only if user says "proceed".
```

### P3 — CLOSED (audit Mar 2026)
```
variables: snapshot blocks confirmed present in all four EOD capture automations. ✓
```

### P4 — Remove notify_efficiency_degradation [LOW]
```
Disabled Feb 2026. Delete block, remove from §AUTOMATIONS INDEX + §KNOWN ISSUES, CHANGELOG entry.
Do not remove proactively — requires explicit instruction.
```

---

## KNOWN ISSUES

```
shell_command.testcmd        config.yaml:16 — never called — do not remove proactively
23:58:00 collision           archive_monthly_hdd + accumulate_filter_runtime — separate entities, no data risk
                             FAIL-CLOSED if any new concurrent write added without explicit documentation
_2 suffix entities           8 confirmed — canonical IDs — DO NOT DELETE (full audit of "10 sensors" claim incomplete)
notify_efficiency_degradation  DISABLED Feb 2026 — tracked §PENDING P4
duplicate trigger IDs        reset_monthly_hdd and reset_yearly_hdd both define trigger id: scheduled and id: startup
                             violates NEVER reuse trigger ID — fix required before next edit to either automation
```
Note: `sensor.shelly_plus_uni_voltge` — intentional entity registry typo — DO NOT CORRECT. See §ENTITIES UPS.

---

## BASELINES (reference only — do not modify without explicit instruction)

```
Building UA:          493 BTU/hr-°F
Balance point:        59°F
HDD59/HDD65 ratio:    0.844
AFUE:                 0.95
BTU/CCF:              103,700
Heating efficiency:   90.3 CCF/1k HDD (Navien-corrected 2025)
DHW ratio:            28.1% (220.8/787 CCF Navien-metered)
Heating ratio:        71.9% (566/787 CCF)
Annual HDD65:         6,270 (2025 actual); climate normal 5,270
Annual electricity:   6,730 kWh
Annual gas:           787 CCF
Site EUI:             41.7 kBTU/ft²-yr
Therms→CCF:           ×0.9643
```

---

## FILE MAP
```
configuration.yaml     sensors, helpers, shell_commands   (~3,832 lines)
automations.yaml       57 automations                     (~2,136 lines)
scripts.yaml           bill archive seed scripts
CLAUDE.md              this file — authoritative
CHANGELOG.md           CalVer YYYY.MM — update on behavior changes
tools/analyze_ha.py    static analyzer — run before every commit
reports/               CSV outputs — DO NOT edit manually
dashboards/cards/      Lovelace YAML snippets only
.storage/              BLOCKED — HA-managed JSON — never edit
scripts/               climate_norms_today.py, setback_csv.py
```

---

## MAINTAINING THIS FILE

When a new guardrail or gotcha is discovered:
```
1. Add to CONSTRAINTS / DANGEROUS PATTERNS / KNOWN ISSUES as appropriate
2. Update §PENDING or §KNOWN ISSUES if it reveals an open item
3. Commit as: docs: update CLAUDE.md — [one-line reason]
4. If reusable across repos, extract to global skills.md instead
```
CLAUDE.md should get stricter over time, never looser.
Any relaxation requires explicit user instruction and a CHANGELOG entry.
