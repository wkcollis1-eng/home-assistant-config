# HA CONFIG — CLAUDE CODE SESSION RULES

## PROJECT GOALS (never violate — supersede all other rules when in conflict)

```
1. Zero data loss or corruption — archives, CSVs, input_numbers are permanent records
2. All automations must be idempotent, restart-safe, and trigger-reentrant
3. Maximize debuggability — every change leaves clear audit trail in logs + CHANGELOG
4. MUST use explicit variables: snapshots for all EOD and time-critical automations — live sensor reads forbidden at trigger time
5. Strict separation — monthly data updates NEVER mixed with config/automation changes
```

---

## CONSTRAINTS

NEVER infer entity IDs from patterns — use only IDs listed in §ENTITIES
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

---

## EXECUTION PROTOCOL

**Before any edit:**
1. `python3 tools/analyze_ha.py` — record baseline error count
2. `grep -rnw . -e '<entity_id>' --include="*.yaml" --include="*.json" --include="*.py"` — impact scan
3. Automation edits only: `grep -A2 'trigger:' automations.yaml | grep 'id:'` — confirm no trigger ID conflict

**After edit:**
- Re-run analyzer — zero new hard errors (new errors beyond baseline = FAIL regardless of absolute count)
- Update §ENTITIES if any new entity added
- Update CHANGELOG.md if behavior changed
- One logical change per commit

**Output format** — Risk: LOW=new sensor/no deps | MEDIUM=automation logic/helper/existing sensor | HIGH=EOD/_2 entities/shell_command/state machine

*LOW:* diff only (unified, ±3 lines context) + `analyzer: PASS|FAIL`

*MEDIUM:* prepend `Change type / Impacted files / Risk: MEDIUM`

*HIGH:* prepend simulation block:
```
Simulation:
  Trigger / Condition result / Action / Side effects / Race risk
```

Hard errors (block commit): missing entity, invalid template, trigger collision, unsafe shell_command, missing default: []
Never rewrite full files. Touch only lines required by the change.
If no change needed: reply ONLY `NO CHANGE — [reason]`

---

## FAIL-CLOSED

If any CONSTRAINT is violated, requirement is ambiguous, or cannot be resolved from CLAUDE.md alone:
→ `NO CHANGE — [reason]`
→ No partial fixes. No guessing. Wait for user resolution.

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
RULE: EOD automations MUST use `variables:` block — FROZEN = trigger times only; adding logic/entities permitted if variables: block present or added in same commit

---

## DANGEROUS PATTERNS

Reject and output `NO CHANGE` if any edit would introduce:
- template sensor without `availability:` guard
- shell_command call without ha_maintenance_mode condition (unless P2 unresolved — then flag only)
- EOD capture automation without `variables:` snapshot block, or using `states('sensor.xxx')` directly in action instead of snapshot variable
- time trigger in EOD window 23:54:30–23:58:45

Required pattern for new sensors — use verbatim:

```yaml
- name: "Sensor Name"
  availability: "{{ states('sensor.source') not in ['unknown','unavailable','none',''] }}"
  state: >
    {% set v = states('sensor.source') %}
    {{ v | float(0) if v not in ['unknown','unavailable','none',''] else 0 }}
```

---

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

### P4 — Remove notify_efficiency_degradation [LOW]
```
Disabled Feb 2026. Requires explicit instruction — do not remove proactively.
```

### Known Issues
```
shell_command.testcmd        config.yaml:16 — never called — do not remove proactively
23:58:00 collision           archive_monthly_hdd + accumulate_filter_runtime — documented, no data risk
                             FAIL-CLOSED if any new concurrent write added without explicit documentation
_2 suffix entities           8 confirmed canonical IDs — DO NOT DELETE (full audit of "10 sensors" claim incomplete)
duplicate trigger IDs        reset_monthly_hdd + reset_yearly_hdd both define id: scheduled and id: startup
                             fix required before next edit to either automation
voltge typo                  sensor.shelly_plus_uni_voltge — intentional entity registry typo — DO NOT CORRECT
```

---

## ENTITIES

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
weather.home / weather.pirateweather
sensor.pirate_weather_*                          28 sensors — never infer; verify exact IDs in automations.yaml
  temperature, feels_like, humidity, pressure, wind_speed, wind_bearing, wind_direction,
  visibility, cloud_cover, dew_point, uv_index, ozone, condition, data_age,
  today_high/low/precip_prob/condition, tomorrow_high/low/precip_prob/condition,
  hdd_forecast_today/tomorrow/7day, cdd_forecast_today
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
input_datetime.hdd_capture_last_ok
```

### CLIMATE NORMS
```
sensor.climate_norms_today                       DO NOT MODIFY without explicit request
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
input_datetime.runtime_per_hdd_capture_last_ok
input_datetime.furnace_cycle_capture_last_ok
```

### MONTHLY REPORT
```
sensor.outdoor_temp_mean_month
sensor.expected_runtime_month
sensor.efficiency_deviation_month
sensor.hvac_runtime_per_hdd_month
input_datetime.monthly_tracking_capture_last_ok  gates all monthly sensors
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

### MISC
```
sensor.hvac_daily_gas_cost_estimate / _electric_cost_estimate / _total_cost_estimate
input_boolean.ha_maintenance_mode                 PENDING CREATION — gate for all shell_command calls
counter.automation_failures_24h / input_text.last_automation_failure
binary_sensor.hdd_capture_stale / runtime_per_hdd_capture_stale / furnace_cycle_capture_stale
binary_sensor.monthly_report_stale / climate_norms_stale
```

### UPS (DIY LiFePO4 — Shelly Plus Uni)
```
sensor.shelly_plus_uni_voltge                     [INTENTIONAL TYPO — DO NOT CORRECT] battery/bus voltage 0–30V
sensor.shelly_plus_uni_temperature                DS18B20 ambient
binary_sensor.shelly_plus_uni_input               grid power presence (Pololu diode input)
```
Note: input_boolean.ups_* IDs pending confirmation — do not reference in any automation until listed here.
Note: Computer Kasa plug entity IDs pending confirmation — do not infer or fabricate.

---

## MONTHLY DATA ENTRY PROTOCOL

Any gas / electric / DHW / bill entry MUST follow the engineering-monthly-update skill.

```
NEVER edit HA input_number archives directly via YAML
NEVER mix a monthly bill entry commit with any config or automation change
ALWAYS use button/automation paths: save_electric_bill_button, save_gas_bill_button, save_dhw_button
ALWAYS verify Therms→CCF conversion (×0.9643) before archiving DHW figures
```

---

## BASELINES (reference only)

```
Building UA:          493 BTU/hr-°F       Balance point:   59°F
HDD59/HDD65 ratio:    0.844               AFUE:            0.95
BTU/CCF:              103,700             Therms→CCF:      ×0.9643
Heating efficiency:   90.3 CCF/1k HDD (Navien-corrected 2025)
DHW ratio:            28.1% (220.8/787 CCF Navien-metered)
Annual HDD65:         6,270 (2025 actual); climate normal 5,270
Annual electricity:   6,730 kWh           Annual gas:      787 CCF
Site EUI:             41.7 kBtu/ft²-yr
```

---

## FILE MAP
```
configuration.yaml     sensors, helpers, shell_commands
automations.yaml       automations
scripts.yaml           bill archive seed scripts
CLAUDE.md              this file — authoritative
CHANGELOG.md           CalVer YYYY.MM — update on behavior changes
tools/analyze_ha.py    static analyzer — run before every commit
reports/               CSV outputs — DO NOT edit manually
dashboards/cards/      Lovelace YAML snippets only
.storage/              BLOCKED — HA-managed JSON — never edit
scripts/               climate_norms_today.py, setback_csv.py
```

New guardrails → CONSTRAINTS or SYSTEM STATE. Commit as: `docs: update CLAUDE.md — [reason]`
CLAUDE.md gets stricter over time. Any relaxation requires explicit user instruction + CHANGELOG entry.
