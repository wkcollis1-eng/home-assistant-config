# HA CONFIG — CLAUDE CODE SESSION RULES

## CONSTRAINTS (CHECK BEFORE ANY ACTION)

NEVER infer entity IDs from patterns — use only IDs listed in §ENTITIES
NEVER edit .storage/* — corrupts dashboards unrecoverably
NEVER overwrite/truncate CSV files — append/rotate only
NEVER add time triggers between 23:54:30–23:58:45
NEVER use `| float` or `| int` without default: use `| float(0)` `| int(0)`
NEVER commit multiple unrelated changes in one commit
NEVER remove inline YAML comments

MUST run `python3 tools/analyze_ha.py` before every commit — zero hard errors required
MUST add `default: []` to every `choose:` block
MUST add `availability:` guard to every new template sensor
MUST wrap every `shell_command.*` call with ha_maintenance_mode guard (§PENDING item 2)
MUST update §ENTITIES + CHANGELOG.md in same commit as any new entity

---

## STEP 0 — REQUIRED BEFORE ANY EDIT

State inline:
```
Change type: <SENSOR|AUTOMATION|ENTITY rename|DASHBOARD snippet|CSV/reporting|ANALYZER|DOCUMENTATION>
Impacted files: <list>
```

---

## OUTPUT FORMAT (follow exactly — no exceptions)

For all changes output ONLY:
```
Change type: ...
Impacted files: ...
```diff
[minimal diff — changed lines only, no full file rewrites]
analyzer: PASS|FAIL
```
If no change needed: reply ONLY "NO CHANGE"
Never rewrite full files. Never explain unless asked.

---

## ENTITY LOOKUP

§ENTITIES below lists all valid entity IDs.
If you need the full pirate_weather sensor list or full setback entity list, type: ENTITIES FULL

---

## EDIT ORDER (never deviate)

1. `grep -rnw . -e 'ENTITY_ID' --include="*.yaml" --include="*.json" --include="*.py"` — impact scan
2. `configuration.yaml` — sensors, helpers, shell_commands
3. `automations.yaml` — logic
4. `CLAUDE.md` — update §ENTITIES, §PENDING, §ISSUES
5. `CHANGELOG.md` — behavior changes only
6. `python3 tools/analyze_ha.py` — zero hard errors
7. Provide diff summary

---

## EOD TIMING SEQUENCE — FROZEN

```
23:55:00  capture_daily_hdd               hdd_day_1–7 only + hdd_capture_last_ok
23:56:00  capture_daily_runtime_per_hdd   runtime_per_hdd_day_1–7
23:56:15  capture_daily_furnace_min_per_cycle
23:56:30  capture_daily_monthly_tracking  ALL month accumulators → sets monthly_tracking_capture_last_ok
23:57:00  CSV daily report
23:58:00  archive_monthly_hdd + accumulate_filter_runtime  [known collision — separate entities, no data risk]
23:58:30  CSV monthly report (last day of month only)
```

RULE: 23:56:30 timestamp is immovable — all month sensors depend on `monthly_tracking_capture_last_ok`
RULE: New month accumulators → add to `capture_daily_monthly_tracking`, NOT `capture_daily_hdd`
RULE: EOD capture automations MUST use `variables:` block to snapshot sensor values at trigger time

```yaml
# Pattern — snapshot at trigger, use variable in action (prevents midnight boundary re-eval)
variables:
  hdd_today: "{{ states('sensor.hvac_hdd65_today') | float(0) }}"
action:
  - service: input_number.set_value
    data:
      value: "{{ hdd_today }}"
```

---

## TEMPLATE PATTERNS

Defensive template (REQUIRED for all new sensors):
```yaml
- name: "Sensor Name"
  availability: "{{ states('sensor.source') not in ['unknown','unavailable','none',''] }}"
  state: >
    {% set v = states('sensor.source') %}
    {{ v | float(0) if v not in ['unknown','unavailable','none',''] else 0 }}
```

Maintenance guard (REQUIRED before every shell_command):
```yaml
- condition: state
  entity_id: input_boolean.ha_maintenance_mode
  state: "off"
- service: shell_command.COMMAND_NAME
```

choose block (REQUIRED default):
```yaml
- choose:
    - conditions: [...]
      sequence: [...]
  default: []
```

---

## PRE-COMMIT CHECKLIST

- [ ] `python3 tools/analyze_ha.py` — zero hard errors
- [ ] New entity IDs added to §ENTITIES
- [ ] CHANGELOG.md updated if behavior changed
- [ ] No `_1s` `_3` or unexpected suffix entities
- [ ] No service calls without availability guard
- [ ] No new time triggers 23:54:30–23:58:45
- [ ] All `choose:` blocks have `default: []`
- [ ] All new template sensors have `availability:` + `| float(0)` / `| int(0)`
- [ ] All shell_command calls have ha_maintenance_mode guard
- [ ] Multi-line Jinja2 uses `>` (strip newlines) or `|` (preserve) with 2-space indent
- [ ] All triggers reachable; conditions not mutually exclusive; templates resolve on `unknown`
- [ ] One logical change per commit

---

## ENTITIES

### FRAGILE — _2 SUFFIX (entity registry conflicts — canonical, NOT typos — DO NOT DELETE)
```
sensor.hdd_rolling_7_day_auto_2                  7-day rolling HDD
sensor.hvac_runtime_per_hdd_7_day_2              7-day runtime/HDD — USED DIRECTLY in notify_runtime_per_hdd_high/low messages
sensor.hvac_runtime_per_hdd_7_day_mean_2         rolling mean — USED DIRECTLY in notification messages
sensor.hvac_runtime_per_hdd_7_day_std_dev_2      rolling std dev — USED DIRECTLY in notification messages
sensor.hvac_furnace_runtime_month_2              MTD furnace runtime
sensor.hvac_furnace_cycles_month_2               MTD furnace cycles
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
weather.local_weather_2                          NWS/NOAA
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
sensor.hvac_furnace_cycles_per_day_week
sensor.hvac_furnace_cycles_per_day_month
sensor.hvac_chaining_index
sensor.hvac_chaining_index_week
sensor.hvac_chaining_index_month
sensor.hvac_zone_overlap_today
sensor.hvac_zone_overlap_week
sensor.hvac_zone_overlap_month
sensor.hvac_zone_overlap_percent
sensor.hvac_total_cycles_week
sensor.hvac_total_cycles_month
```

### RUNTIME/HDD STATISTICS
```
sensor.hvac_runtime_per_hdd_7_day_mean_2         [_2 FRAGILE]
sensor.hvac_runtime_per_hdd_7_day_std_dev_2      [_2 FRAGILE]
sensor.hvac_runtime_per_hdd_upper_bound
sensor.hvac_runtime_per_hdd_lower_bound
sensor.hvac_runtime_per_hdd_data_count           alerts suppressed if <4
input_number.runtime_per_hdd_day_1 … _7
```

### MONTHLY REPORT
```
sensor.outdoor_temp_mean_month
sensor.expected_runtime_month
sensor.efficiency_deviation_month
sensor.hvac_runtime_per_hdd_month
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
sensor.dehumidifier_runtime_today
sensor.dehumidifier_runtime_week
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

---

## AUTOMATIONS INDEX

### HDD
```
capture_daily_hdd                23:55 — hdd_day_1–7 + hdd_capture_last_ok ONLY
capture_daily_runtime_per_hdd   23:56
capture_daily_furnace_min_per_cycle  23:56:15
capture_daily_monthly_tracking  23:56:30 — ALL month accumulators + monthly_tracking_capture_last_ok
reset_monthly_hdd               1st of month
reset_yearly_hdd                Jan 1
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
notify_efficiency_degradation   DISABLED Feb 2026
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
CSV daily report                23:57 → shell_command.appenddailycsv       [needs ha_maintenance_mode guard]
CSV monthly report              23:58:30 last day → shell_command.appendmonthlycsv  [needs guard]
CSV yearly rotation             Jan 1 → shell_command.rotatedailycsv       [needs guard]
Backup Input Numbers Weekly     → shell_command.backup_input_numbers        [needs guard]
Rotate Setback Log Yearly       → shell_command.rotate_setback_log          [needs guard]
1F Recovery End                 → shell_command.appendsetbacklog_1f         [needs guard]
2F Recovery End                 → shell_command.appendsetbacklog_2f         [needs guard]
```

---

## PENDING (incomplete — address in next update)

### P1 — Add `default: []` to 5 choose: blocks [LOW EFFORT]
```
Update Outdoor Temp Daily High/Low   step[1] step[2]
Validate Input Numbers on Startup    step[1] step[2] step[3]
```

### P2 — Add ha_maintenance_mode guard to all shell_command calls [MEDIUM]
```
Steps:
1. Create input_boolean.ha_maintenance_mode (toggle, default OFF)
2. Wrap all 7 shell_command calls listed in §AUTOMATIONS CSV/REPORTING
3. Add Lovelace toggle (red when ON)
4. Add to §ENTITIES
5. Add to pre-commit checklist
```

### P3 — Add variables: snapshot blocks to EOD capture automations [LOW EFFORT]
```
capture_daily_hdd               snapshot hdd/cdd at 23:55
capture_daily_runtime_per_hdd   snapshot at 23:56
capture_daily_monthly_tracking  snapshot all at 23:56:30
Pattern: see §EOD TIMING SEQUENCE
```

---

## KNOWN ISSUES

```
shell_command.testcmd           defined config.yaml:16 — never called — safe to remove
23:58:00 collision              archive_monthly_hdd + accumulate_filter_runtime — separate entities, no data risk
_2 suffix entities              10 sensors — entity registry artifacts — canonical IDs — DO NOT DELETE
notify_efficiency_degradation   DISABLED Feb 2026 — fixed threshold replaced by ±2σ
```

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
configuration.yaml     sensors, helpers, shell_commands   (~3,800 lines)
automations.yaml       56 automations                     (~2,000 lines)
scripts.yaml           bill archive seed scripts
CLAUDE.md              this file — authoritative
CHANGELOG.md           CalVer YYYY.MM — update on behavior changes
tools/analyze_ha.py    static analyzer — run before every commit
reports/               CSV outputs — DO NOT edit manually
dashboards/cards/      Lovelace YAML snippets only
.storage/              BLOCKED — HA-managed JSON — never edit
scripts/               climate_norms_today.py, setback_csv.py
```
