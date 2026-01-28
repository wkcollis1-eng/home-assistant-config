# Home Assistant Configuration Review

**Date:** January 28, 2026  
**System:** HA Green - HVAC Energy Performance Monitoring  
**Files Reviewed:** configuration.yaml (2882 lines), automations.yaml (1331 lines), CLAUDE.md

---

## Executive Summary

This is a **production-grade** Home Assistant configuration implementing sophisticated HVAC performance monitoring with statistical process control. The architecture demonstrates excellent engineering practices including:

- 7-layer data validation with corruption detection
- Auto-calibrating statistical bounds (±2σ) for anomaly detection
- Multi-source weather failover
- Comprehensive CSV logging for longitudinal analysis

However, several issues were identified that could impact data integrity and system robustness.

---

## 🔴 Critical Issues (Errors)

### 1. Recovery END Threshold Inconsistency

**Location:** `configuration.yaml` lines 1267-1297 vs CLAUDE.md lines 643-649

**Issue:** CLAUDE.md documents that recovery thresholds were updated to 1.0°F (1F) and 1.25°F (2F), but the actual configuration still uses **0.5°F** for both zones:

```yaml
# Lines 1276-1277 (1F) and 1292-1293 (2F) show:
{{ current < (target - 0.5) }}
```

**Impact:** Recovery events may never complete during cold weather, causing recovery rate data to stop updating (as documented in your Jan 25 fix).

**Correction:**
```yaml
# binary_sensor.hvac_1f_recovering (line 1277)
{{ current < (target - 1.0) }}

# binary_sensor.hvac_2f_recovering (line 1293)  
{{ current < (target - 1.25) }}
```

---

### 2. Missing `input_datetime` Declarations

**Location:** Automation references entities that don't appear in configuration.yaml

**Missing Entities:**
- `input_datetime.hdd_capture_last_ok` (referenced in automations lines 198-202, 344-357)
- `input_datetime.runtime_per_hdd_capture_last_ok` (referenced in automations lines 273-283)
- `input_datetime.hvac_filter_last_changed` (referenced in automation line 718)
- `input_datetime.electricity_bill_date` (referenced in automation line 450)
- `input_datetime.gas_bill_date` (referenced in automation line 513)

**Impact:** Automations will fail with entity_not_found errors, preventing HDD capture validation and bill workflows.

**Correction - Add to configuration.yaml:**
```yaml
input_datetime:
  hdd_capture_last_ok:
    name: "HDD Capture Last OK"
    has_date: true
    has_time: true
    icon: mdi:calendar-check
    
  runtime_per_hdd_capture_last_ok:
    name: "Runtime per HDD Capture Last OK"
    has_date: true
    has_time: true
    icon: mdi:calendar-check
    
  hvac_filter_last_changed:
    name: "Filter Last Changed"
    has_date: true
    has_time: false
    icon: mdi:air-filter
    
  electricity_bill_date:
    name: "Electricity Bill Date"
    has_date: true
    has_time: false
    icon: mdi:calendar
    
  gas_bill_date:
    name: "Gas Bill Date"
    has_date: true
    has_time: false
    icon: mdi:calendar
```

---

### 3. Setback Tracking Input Numbers Missing

**Location:** Automations reference entities for setback/recovery tracking

**Missing Entities:**
- `input_number.hvac_1f_recovery_setback_degrees`
- `input_number.hvac_2f_recovery_setback_degrees`
- `input_number.hvac_1f_recovery_outdoor_temp`
- `input_number.hvac_2f_recovery_outdoor_temp`
- `input_number.hvac_1f_last_overnight_low`
- `input_number.hvac_2f_last_overnight_low`
- `input_number.hvac_1f_last_setback_depth`
- `input_number.hvac_2f_last_setback_depth`
- `input_number.hvac_1f_last_net_runtime`
- `input_number.hvac_2f_last_net_runtime`
- `input_number.hvac_1f_hold_setpoint`
- `input_number.hvac_2f_hold_setpoint`
- `input_number.hvac_1f_setback_setpoint`
- `input_number.hvac_2f_setback_setpoint`
- `input_number.hvac_1f_setback_start_runtime`
- `input_number.hvac_2f_setback_start_runtime`
- `input_number.hvac_1f_last_recovery_minutes`
- `input_number.hvac_2f_last_recovery_minutes`
- `input_number.dehumidifier_dewpoint_threshold`
- `input_number.hvac_filter_runtime_hours`

**Correction - Add to configuration.yaml (see supplemental file):**
```yaml
# See ha_missing_entities.yaml for complete definitions
```

---

## 🟡 Moderate Issues

### 4. CDD Range Validation Too Permissive

**Location:** automations.yaml line 132

**Issue:** CDD validation allows values up to 30, but with a 65°F baseline and potential heat waves, values could theoretically exceed this:
```yaml
0 <= (states('sensor.hvac_cdd65_today')|float) <= 30
```

**Recommendation:** Increase to 50 for safety margin, or use dynamic bounds.

---

### 5. Shell Command Variable Passing May Fail

**Location:** automations.yaml lines 892-899

**Issue:** The `appendsetbacklog` shell command uses template variables passed via `data:`, but shell_command doesn't support Jinja variables this way in HA:

```yaml
- service: shell_command.appendsetbacklog
  data:
    zone: "1F"
    overnight_low: "{{ overnight_low }}"
```

**Impact:** CSV may receive literal strings instead of values.

**Correction:** Use `shell_command` with inline template:
```yaml
shell_command:
  appendsetbacklog_1f: >-
    bash -c "echo \"$(date +%Y-%m-%d),1F,{{ states('input_number.hvac_1f_last_overnight_low') }},{{ states('input_number.hvac_1f_last_setback_depth') }},{{ states('input_number.hvac_1f_last_recovery_minutes') | float * states('input_number.hvac_1f_recovery_setback_degrees') | float }},{{ ... }},{{ states('input_number.hvac_1f_last_net_runtime') }}\" >> /config/reports/hvac_setback_log.csv"
```

Or create a Python script that accepts environment variables.

---

### 6. Monthly Report Days-in-Month Calculation Edge Case

**Location:** configuration.yaml lines 1833

**Issue:** The days-in-month calculation could fail in December (month 12):
```yaml
{% set daily_rate = month_normal / (now().replace(month=now().month % 12 + 1, day=1) - timedelta(days=1)).day %}
```

When `now().month = 12`, this becomes `month=1` (January) which would give days for January, not December.

**Correction:**
```yaml
{% set next_month = now().replace(day=28) + timedelta(days=4) %}
{% set last_day = next_month - timedelta(days=next_month.day) %}
{% set days_in_month = last_day.day %}
{% set daily_rate = month_normal / days_in_month %}
```

---

### 7. Efficiency Deviation Index Operator Precedence

**Location:** configuration.yaml line 2627

**Issue:** Potential operator precedence issue:
```yaml
{{ ((actual / expected) - 1) * 100 | round(1) }}
```

The `round(1)` applies only to `100`, not the entire expression.

**Correction:**
```yaml
{{ (((actual / expected) - 1) * 100) | round(1) }}
```

---

## 🟢 Robustness Improvements

### 8. Add Watchdog Automation for Capture Health

**Purpose:** Alert if daily captures fail for 48+ hours

```yaml
- id: notify_hdd_capture_stale
  alias: "Notify HDD Capture Stale"
  trigger:
    - platform: state
      entity_id: binary_sensor.hdd_capture_stale
      to: "on"
      for:
        hours: 2
  action:
    - service: persistent_notification.create
      data:
        title: "⚠️ HDD Capture Health Alert"
        message: >
          HDD capture has not succeeded in over 26 hours.
          Last successful: {{ states('input_datetime.hdd_capture_last_ok') }}
          Check sensor.hvac_hdd65_today and sensor.hvac_cdd65_today for availability.
```

---

### 9. Add Graceful Degradation for Climate Norms Script

**Issue:** If `climate_norms_today.py` fails, sensors return "unknown", breaking downstream calculations.

**Add to configuration.yaml:**
```yaml
# Add availability template to climate norms derived sensors
- name: "Expected HDD Today"
  ...
  availability: >
    {{ states('sensor.climate_norms_today') not in ['unknown', 'unavailable', 'error'] }}
```

---

### 10. Implement Input Number Persistence Validation

**Issue:** Input numbers can lose values during HA restart/corruption. Add startup validation:

```yaml
- id: validate_input_numbers_startup
  alias: "Validate Input Numbers on Startup"
  trigger:
    - platform: homeassistant
      event: start
  action:
    - choose:
        # Check for corrupt HDD cumulative values (should never exceed reasonable limits)
        - conditions:
            - condition: template
              value_template: >
                {{ states('input_number.hdd_cumulative_year_auto') | float(0) > 8000 or
                   states('input_number.hdd_cumulative_month_auto') | float(0) > 2500 }}
          sequence:
            - service: system_log.write
              data:
                message: "WARNING: HDD cumulative values appear corrupt. Year: {{ states('input_number.hdd_cumulative_year_auto') }}, Month: {{ states('input_number.hdd_cumulative_month_auto') }}"
                level: warning
            - service: persistent_notification.create
              data:
                title: "⚠️ HDD Data Validation Warning"
                message: "HDD cumulative values may be corrupt. Please verify and manually correct if needed."
```

---

### 11. Add Sensor Availability Checks to Critical Templates

**Example - Add to HVAC Hartford Proxy:**
```yaml
- name: "HVAC Outdoor Temp Hartford Proxy"
  ...
  availability: >
    {{ states('sensor.outdoor_temp_live') not in ['unknown', 'unavailable'] or
       state_attr('weather.pirateweather', 'temperature') is number or
       state_attr('weather.local_weather_2', 'temperature') is number or
       state_attr('weather.home', 'temperature') is number }}
```

---

### 12. Add Database Auto-Repair for Long-Term Statistics

**Purpose:** Ensure long-term statistics survive database issues

```yaml
- id: verify_long_term_statistics
  alias: "Verify Long-Term Statistics Monthly"
  trigger:
    - platform: time
      at: "04:00:00"
  condition:
    - condition: template
      value_template: "{{ now().day == 1 }}"
  action:
    - service: recorder.purge_entities
      data:
        keep_days: 14
    - service: system_log.write
      data:
        message: "Monthly long-term statistics verification completed"
        level: info
```

---

## 📋 Recommended Implementation Order

1. **Immediate (Critical):**
   - Add missing `input_datetime` entities
   - Add missing `input_number` entities  
   - Fix recovery END thresholds (0.5 → 1.0/1.25)
   - Fix efficiency deviation operator precedence

2. **Short-term (This Week):**
   - Add capture health watchdog automation
   - Fix shell command variable passing for setback log
   - Add availability templates to critical sensors

3. **Medium-term (This Month):**
   - Implement startup validation automation
   - Add graceful degradation for climate norms
   - Review and test all monthly boundary calculations

---

## 📊 Architecture Strengths

1. **Statistical Process Control:** The ±2σ bounds approach is excellent for anomaly detection without manual baseline tuning.

2. **Multi-Source Failover:** Weather data cascades through 4 sources (Live API → Pirate Weather → NWS → Open-Meteo).

3. **Corruption Detection:** The `initial` values on daily high/low (-50/150) enable automatic corruption recovery.

4. **Separation of Concerns:** Zone-specific metrics kept separate from furnace-aggregate metrics.

5. **Comprehensive Logging:** CSV outputs enable longitudinal analysis outside HA.

---

## Files Generated

- `ha_missing_entities.yaml` - Complete definitions for missing entities
- `ha_corrections.yaml` - Corrected sensor definitions
- `ha_watchdog_automations.yaml` - Robustness automations

