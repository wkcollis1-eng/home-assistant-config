# Claude Code Directions: AC/CDD Cooling Monitoring Build-Out
**Target files:** `configuration.yaml` · `automations.yaml`  
**Reference:** Existing heating infrastructure is the structural template.  
**Date:** 2026-03-18

---

## Audit Summary — What Exists vs. What Is Missing

### Already present (do NOT duplicate)
| Entity | Notes |
|---|---|
| `sensor.hvac_cdd65_today` | Daily CDD65 computed from outdoor mean — fully implemented |
| `input_number.cdd_cumulative_month_auto` | Monthly CDD accumulator — populated in `capture_daily_monthly_tracking` |
| `input_number.cdd_cumulative_year_auto` | Yearly CDD accumulator — same |
| `sensor.hvac_cdd65_cumulative_month` (implied) | Absent as named template but CDD month accumulator feeds monthly CSV |
| Climate norms CDD attributes | `cdd_mean`, `cdd_p10`, `cdd_p90` from `climate_norms_today.py` |

### Structural gaps — everything below must be added

The heating side has this full chain for every entity type. The cooling side has only CDD accumulation. The AC compressor is common to both zones (same split system), exactly mirroring the furnace which is common to both zone heat calls.

---

## Step 1 — Binary Sensors (configuration.yaml, template section)

Add these three binary sensors immediately after the `hvac_furnace_running` block (around line 1519).

```yaml
      - name: "HVAC 1F Call For Cool"
        unique_id: hvac_1f_call_for_cool
        state: >
          {% if states('climate.tstat_2d884c_lyric_t6_pro_thermostat') not in ['unavailable', 'unknown'] %}
            {{ state_attr('climate.tstat_2d884c_lyric_t6_pro_thermostat', 'hvac_action') == 'cooling' }}
          {% else %}
            false
          {% endif %}

      - name: "HVAC 2F Call For Cool"
        unique_id: hvac_2f_call_for_cool
        state: >
          {% if states('climate.tstat_2d8878_lyric_t6_pro_thermostat') not in ['unavailable', 'unknown'] %}
            {{ state_attr('climate.tstat_2d8878_lyric_t6_pro_thermostat', 'hvac_action') == 'cooling' }}
          {% else %}
            false
          {% endif %}

      # AC Running - ON when EITHER zone is calling for cool (actual compressor cycles)
      - name: "HVAC AC Running"
        unique_id: hvac_ac_running
        device_class: running
        state: >
          {{ is_state('binary_sensor.hvac_1f_call_for_cool', 'on') or
             is_state('binary_sensor.hvac_2f_call_for_cool', 'on') }}
```

**Note:** Thermostat entity ID mapping is 1F = `tstat_2d884c`, 2F = `tstat_2d8878` — same as heating sensors. Confirm this matches your registry if the `_2`-suffix issue ever reappears.

---

## Step 2 — history_stats Sensors (configuration.yaml, sensor platform section)

Add after the `hvac_furnace_cycles_week` block (around line 3791) and before the dehumidifier runtime block. Follow the exact same structure as the heating history_stats entries.

```yaml
  # === AC COOLING RUNTIME / CYCLES (mirrors heating pattern) ===

  - platform: history_stats
    name: "HVAC 1F Cool Cycles Today"
    unique_id: hvac_1f_cool_cycles_today
    entity_id: binary_sensor.hvac_1f_call_for_cool
    state: "on"
    type: count
    start: "{{ now().replace(hour=0, minute=0, second=0, microsecond=0) }}"
    end: "{{ now() }}"

  - platform: history_stats
    name: "HVAC 1F Cool Runtime Today"
    unique_id: hvac_1f_cool_runtime_today
    entity_id: binary_sensor.hvac_1f_call_for_cool
    state: "on"
    type: time
    start: "{{ now().replace(hour=0, minute=0, second=0, microsecond=0) }}"
    end: "{{ now() }}"

  - platform: history_stats
    name: "HVAC 2F Cool Cycles Today"
    unique_id: hvac_2f_cool_cycles_today
    entity_id: binary_sensor.hvac_2f_call_for_cool
    state: "on"
    type: count
    start: "{{ now().replace(hour=0, minute=0, second=0, microsecond=0) }}"
    end: "{{ now() }}"

  - platform: history_stats
    name: "HVAC 2F Cool Runtime Today"
    unique_id: hvac_2f_cool_runtime_today
    entity_id: binary_sensor.hvac_2f_call_for_cool
    state: "on"
    type: time
    start: "{{ now().replace(hour=0, minute=0, second=0, microsecond=0) }}"
    end: "{{ now() }}"

  - platform: history_stats
    name: "HVAC AC Cycles Today"
    unique_id: hvac_ac_cycles_today
    entity_id: binary_sensor.hvac_ac_running
    state: "on"
    type: count
    start: "{{ now().replace(hour=0, minute=0, second=0, microsecond=0) }}"
    end: "{{ now() }}"

  - platform: history_stats
    name: "HVAC AC Runtime Today"
    unique_id: hvac_ac_runtime_today
    entity_id: binary_sensor.hvac_ac_running
    state: "on"
    type: time
    start: "{{ now().replace(hour=0, minute=0, second=0, microsecond=0) }}"
    end: "{{ now() }}"

  - platform: history_stats
    name: "HVAC 1F Cool Runtime Week"
    unique_id: hvac_1f_cool_runtime_week
    entity_id: binary_sensor.hvac_1f_call_for_cool
    state: "on"
    type: time
    start: "{{ now() - timedelta(days=7) }}"
    end: "{{ now() }}"

  - platform: history_stats
    name: "HVAC 2F Cool Runtime Week"
    unique_id: hvac_2f_cool_runtime_week
    entity_id: binary_sensor.hvac_2f_call_for_cool
    state: "on"
    type: time
    start: "{{ now() - timedelta(days=7) }}"
    end: "{{ now() }}"

  - platform: history_stats
    name: "HVAC 1F Cool Cycles Week"
    unique_id: hvac_1f_cool_cycles_week
    entity_id: binary_sensor.hvac_1f_call_for_cool
    state: "on"
    type: count
    start: "{{ now() - timedelta(days=7) }}"
    end: "{{ now() }}"

  - platform: history_stats
    name: "HVAC 2F Cool Cycles Week"
    unique_id: hvac_2f_cool_cycles_week
    entity_id: binary_sensor.hvac_2f_call_for_cool
    state: "on"
    type: count
    start: "{{ now() - timedelta(days=7) }}"
    end: "{{ now() }}"

  - platform: history_stats
    name: "HVAC AC Runtime Week"
    unique_id: hvac_ac_runtime_week
    entity_id: binary_sensor.hvac_ac_running
    state: "on"
    type: time
    start: "{{ now() - timedelta(days=7) }}"
    end: "{{ now() }}"

  - platform: history_stats
    name: "HVAC AC Cycles Week"
    unique_id: hvac_ac_cycles_week
    entity_id: binary_sensor.hvac_ac_running
    state: "on"
    type: count
    start: "{{ now() - timedelta(days=7) }}"
    end: "{{ now() }}"

  # NOTE: Month AC runtime/cycles use accumulated template sensors (immune to recorder purge)
```

---

## Step 3 — input_number Accumulators (configuration.yaml, input_number section)

Add after `zone_2f_cycles_month_acc` block (around line 806). Follow the exact same pattern.

```yaml
  # === AC COOLING MONTHLY ACCUMULATORS ===

  ac_runtime_month_acc:
    name: "AC Runtime Month Accumulated"
    min: 0
    max: 1000
    step: 0.01
    unit_of_measurement: "h"
    mode: box
    icon: mdi:air-conditioner

  ac_cycles_month_acc:
    name: "AC Cycles Month Accumulated"
    min: 0
    max: 5000
    step: 1
    unit_of_measurement: "cycles"
    mode: box
    icon: mdi:counter

  zone_1f_cool_runtime_month_acc:
    name: "1F Cool Runtime Month Accumulated"
    min: 0
    max: 1000
    step: 0.01
    unit_of_measurement: "h"
    mode: box
    icon: mdi:home-floor-1

  zone_2f_cool_runtime_month_acc:
    name: "2F Cool Runtime Month Accumulated"
    min: 0
    max: 1000
    step: 0.01
    unit_of_measurement: "h"
    mode: box
    icon: mdi:home-floor-2

  zone_1f_cool_cycles_month_acc:
    name: "1F Cool Cycles Month Accumulated"
    min: 0
    max: 5000
    step: 1
    unit_of_measurement: "cycles"
    mode: box
    icon: mdi:home-floor-1

  zone_2f_cool_cycles_month_acc:
    name: "2F Cool Cycles Month Accumulated"
    min: 0
    max: 5000
    step: 1
    unit_of_measurement: "cycles"
    mode: box
    icon: mdi:home-floor-2
```

Also add yearly accumulators. The monthly accumulators above reset on the 1st of each month (Step 8). Yearly accumulators persist until Jan 1, giving a full-season total that survives the monthly resets. Only compressor-level yearly tracking is needed — zone-level yearly is not tracked on the heating side and is not required here:

```yaml
  # === AC COOLING YEARLY ACCUMULATORS ===
  # Reset Jan 1 by reset_yearly_hdd. Updated nightly alongside monthly tracking.

  ac_runtime_year_acc:
    name: "AC Runtime Year Accumulated"
    min: 0
    max: 10000
    step: 0.01
    unit_of_measurement: "h"
    mode: box
    icon: mdi:air-conditioner

  ac_cycles_year_acc:
    name: "AC Cycles Year Accumulated"
    min: 0
    max: 50000
    step: 1
    unit_of_measurement: "cycles"
    mode: box
    icon: mdi:counter
```

Also add the SPC seed values. These are the fallback for mean and std dev while the `runtime_per_cdd_day_1..7` window is still populating (first 3–7 days of cooling operation). Once the window has real data the template sensors compute live values automatically — seeds remain as the fallback for any future window drain (e.g., extended HA outage). Add alongside the other SPC-related input_numbers:

```yaml
  # === RUNTIME/CDD SPC SEED VALUES ===
  # Fallback for mean/stddev template sensors until 7-day window self-populates.
  # Update via Developer Tools → Services → input_number.set_value after first week
  # of cooling data. Seeds remain active as drain-recovery fallback thereafter.

  runtime_per_cdd_seed_mean:
    name: "Runtime/CDD Seed Mean"
    min: 0
    max: 200
    step: 0.1
    initial: 18.0
    mode: box
    unit_of_measurement: "min/CDD"
    icon: mdi:chart-bell-curve

  runtime_per_cdd_seed_stddev:
    name: "Runtime/CDD Seed Std Dev"
    min: 0
    max: 50
    step: 0.1
    initial: 2.0
    mode: box
    unit_of_measurement: "min/CDD"
    icon: mdi:sigma
```

Also add the CDD 7-day sliding window input_numbers. These are **absent** — HDD has `hdd_day_1` through `hdd_day_7` but CDD has NO equivalent day slots. Add after the HDD day slots (after line ~594) or alongside the HDD day block, wherever it is cleanest:

```yaml
  # === CDD DAILY SLIDING WINDOW (7-day rolling, mirrors HDD pattern) ===

  cdd_day_1:
    name: "CDD Day 1 (Yesterday)"
    min: 0
    max: 50
    step: 0.1
    mode: box
    unit_of_measurement: "CDD"

  cdd_day_2:
    name: "CDD Day 2"
    min: 0
    max: 50
    step: 0.1
    mode: box
    unit_of_measurement: "CDD"

  cdd_day_3:
    name: "CDD Day 3"
    min: 0
    max: 50
    step: 0.1
    mode: box
    unit_of_measurement: "CDD"

  cdd_day_4:
    name: "CDD Day 4"
    min: 0
    max: 50
    step: 0.1
    mode: box
    unit_of_measurement: "CDD"

  cdd_day_5:
    name: "CDD Day 5"
    min: 0
    max: 50
    step: 0.1
    mode: box
    unit_of_measurement: "CDD"

  cdd_day_6:
    name: "CDD Day 6"
    min: 0
    max: 50
    step: 0.1
    mode: box
    unit_of_measurement: "CDD"

  cdd_day_7:
    name: "CDD Day 7 (Oldest)"
    min: 0
    max: 50
    step: 0.1
    mode: box
    unit_of_measurement: "CDD"

  # === RUNTIME/CDD DAILY SLIDING WINDOW ===

  runtime_per_cdd_day_1:
    name: "Runtime/CDD Day 1 (Yesterday)"
    min: 0
    max: 500
    step: 0.1
    mode: box
    unit_of_measurement: "min/CDD"

  runtime_per_cdd_day_2:
    name: "Runtime/CDD Day 2"
    min: 0
    max: 500
    step: 0.1
    mode: box
    unit_of_measurement: "min/CDD"

  runtime_per_cdd_day_3:
    name: "Runtime/CDD Day 3"
    min: 0
    max: 500
    step: 0.1
    mode: box
    unit_of_measurement: "min/CDD"

  runtime_per_cdd_day_4:
    name: "Runtime/CDD Day 4"
    min: 0
    max: 500
    step: 0.1
    mode: box
    unit_of_measurement: "min/CDD"

  runtime_per_cdd_day_5:
    name: "Runtime/CDD Day 5"
    min: 0
    max: 500
    step: 0.1
    mode: box
    unit_of_measurement: "min/CDD"

  runtime_per_cdd_day_6:
    name: "Runtime/CDD Day 6"
    min: 0
    max: 500
    step: 0.1
    mode: box
    unit_of_measurement: "min/CDD"

  runtime_per_cdd_day_7:
    name: "Runtime/CDD Day 7 (Oldest)"
    min: 0
    max: 500
    step: 0.1
    mode: box
    unit_of_measurement: "min/CDD"
```

---

## Step 4 — Template Sensors (configuration.yaml, template section)

Add in the template sensor block, logically grouped after the existing heating daily/week/month template sensors. Mirror the heating structure exactly.

### 4a. Daily and Week AC analytics

```yaml
      # === AC COOLING DAILY SENSORS ===

      - name: "HVAC Total Cool Runtime Today"
        unique_id: hvac_total_cool_runtime_today
        unit_of_measurement: "h"
        state_class: measurement
        icon: mdi:air-conditioner
        state: >
          {{ (states('sensor.hvac_1f_cool_runtime_today') | float(0) +
              states('sensor.hvac_2f_cool_runtime_today') | float(0)) | round(2) }}

      - name: "HVAC Total Cool Cycles Today"
        unique_id: hvac_total_cool_cycles_today
        unit_of_measurement: "cycles"
        state_class: measurement
        state: >
          {{ states('sensor.hvac_1f_cool_cycles_today') | int(0) +
             states('sensor.hvac_2f_cool_cycles_today') | int(0) }}

      - name: "HVAC AC Min per Cycle"
        unique_id: hvac_ac_min_per_cycle
        unit_of_measurement: "min/cycle"
        state_class: measurement
        icon: mdi:timer-cog
        state: >
          {% set runtime = states('sensor.hvac_ac_runtime_today') | float(0) %}
          {% set cycles = states('sensor.hvac_ac_cycles_today') | int(0) %}
          {% if cycles > 0 and runtime > 0 %}
            {{ ((runtime * 60) / cycles) | round(1) }}
          {% else %}
            0
          {% endif %}

      # CDD Rolling 7-Day (mirrors hdd_rolling_7_day_auto)
      - name: "CDD Rolling 7-Day Auto"
        unique_id: cdd_rolling_7_day_auto
        unit_of_measurement: "CDD"
        state_class: measurement
        icon: mdi:sun-thermometer
        state: >
          {% set days = [
            states('input_number.cdd_day_1') | float(-1),
            states('input_number.cdd_day_2') | float(-1),
            states('input_number.cdd_day_3') | float(-1),
            states('input_number.cdd_day_4') | float(-1),
            states('input_number.cdd_day_5') | float(-1),
            states('input_number.cdd_day_6') | float(-1),
            states('input_number.cdd_day_7') | float(-1)
          ] %}
          {% set valid = days | select('>=', 0) | select('<=', 50) | list %}
          {{ valid | sum | round(1) }}

      # Runtime/CDD 7-day rolling (mirrors runtime_per_hdd_7_day)
      # IMPORTANT: numerator uses hvac_ac_runtime_week (7-day history_stats sensor),
      # NOT hvac_ac_runtime_today — dividing one day of runtime by seven days of CDD
      # would chronically underreport and break comparability with the heating baseline.
      - name: "HVAC Runtime per CDD 7-Day"
        unique_id: hvac_runtime_per_cdd_7_day
        unit_of_measurement: "min/CDD"
        state_class: measurement
        icon: mdi:sun-thermometer
        state: >
          {% set rt_min = states('sensor.hvac_ac_runtime_week') | float(0) * 60 %}
          {% set cdd_7 = states('sensor.cdd_rolling_7_day_auto') | float(0) %}
          {% if cdd_7 > 0 %}
            {{ (rt_min / cdd_7) | round(1) }}
          {% else %}
            0
          {% endif %}
```

### 4b. Monthly accumulated sensors (immune to recorder purge)

Add after the existing `hvac_2f_heat_cycles_month` and `hvac_total_heat_runtime_month` blocks.

```yaml
      # ================================================================
      # AC COOLING MONTHLY ACCUMULATED SENSORS
      # Values accumulated daily at 23:56:30, reset on 1st of month
      # Immune to recorder purge_keep_days — mirrors heating pattern
      # ================================================================

      - name: "HVAC AC Runtime Month"
        unique_id: hvac_ac_runtime_month
        unit_of_measurement: "h"
        state_class: measurement
        icon: mdi:air-conditioner
        state: >
          {% set acc = states('input_number.ac_runtime_month_acc') | float(0) %}
          {% set today = states('sensor.hvac_ac_runtime_today') | float(0) %}
          {% set last_capture = states('input_datetime.monthly_tracking_capture_last_ok') %}
          {% set captured_today = last_capture[:10] == now().strftime('%Y-%m-%d') if last_capture not in ['unknown', 'unavailable', '1970-01-01 00:00:00'] else false %}
          {{ (acc if captured_today else acc + today) | round(2) }}

      - name: "HVAC AC Cycles Month"
        unique_id: hvac_ac_cycles_month
        unit_of_measurement: "cycles"
        state_class: measurement
        icon: mdi:counter
        state: >
          {% set acc = states('input_number.ac_cycles_month_acc') | int(0) %}
          {% set today = states('sensor.hvac_ac_cycles_today') | int(0) %}
          {% set last_capture = states('input_datetime.monthly_tracking_capture_last_ok') %}
          {% set captured_today = last_capture[:10] == now().strftime('%Y-%m-%d') if last_capture not in ['unknown', 'unavailable', '1970-01-01 00:00:00'] else false %}
          {{ acc if captured_today else acc + today }}

      - name: "HVAC 1F Cool Runtime Month"
        unique_id: hvac_1f_cool_runtime_month
        unit_of_measurement: "h"
        state_class: measurement
        icon: mdi:home-floor-1
        state: >
          {% set acc = states('input_number.zone_1f_cool_runtime_month_acc') | float(0) %}
          {% set today = states('sensor.hvac_1f_cool_runtime_today') | float(0) %}
          {% set last_capture = states('input_datetime.monthly_tracking_capture_last_ok') %}
          {% set captured_today = last_capture[:10] == now().strftime('%Y-%m-%d') if last_capture not in ['unknown', 'unavailable', '1970-01-01 00:00:00'] else false %}
          {{ (acc if captured_today else acc + today) | round(2) }}

      - name: "HVAC 2F Cool Runtime Month"
        unique_id: hvac_2f_cool_runtime_month
        unit_of_measurement: "h"
        state_class: measurement
        icon: mdi:home-floor-2
        state: >
          {% set acc = states('input_number.zone_2f_cool_runtime_month_acc') | float(0) %}
          {% set today = states('sensor.hvac_2f_cool_runtime_today') | float(0) %}
          {% set last_capture = states('input_datetime.monthly_tracking_capture_last_ok') %}
          {% set captured_today = last_capture[:10] == now().strftime('%Y-%m-%d') if last_capture not in ['unknown', 'unavailable', '1970-01-01 00:00:00'] else false %}
          {{ (acc if captured_today else acc + today) | round(2) }}

      - name: "HVAC 1F Cool Cycles Month"
        unique_id: hvac_1f_cool_cycles_month
        unit_of_measurement: "cycles"
        state_class: measurement
        icon: mdi:home-floor-1
        state: >
          {% set acc = states('input_number.zone_1f_cool_cycles_month_acc') | int(0) %}
          {% set today = states('sensor.hvac_1f_cool_cycles_today') | int(0) %}
          {% set last_capture = states('input_datetime.monthly_tracking_capture_last_ok') %}
          {% set captured_today = last_capture[:10] == now().strftime('%Y-%m-%d') if last_capture not in ['unknown', 'unavailable', '1970-01-01 00:00:00'] else false %}
          {{ acc if captured_today else acc + today }}

      - name: "HVAC 2F Cool Cycles Month"
        unique_id: hvac_2f_cool_cycles_month
        unit_of_measurement: "cycles"
        state_class: measurement
        icon: mdi:home-floor-2
        state: >
          {% set acc = states('input_number.zone_2f_cool_cycles_month_acc') | int(0) %}
          {% set today = states('sensor.hvac_2f_cool_cycles_today') | int(0) %}
          {% set last_capture = states('input_datetime.monthly_tracking_capture_last_ok') %}
          {% set captured_today = last_capture[:10] == now().strftime('%Y-%m-%d') if last_capture not in ['unknown', 'unavailable', '1970-01-01 00:00:00'] else false %}
          {{ acc if captured_today else acc + today }}

      # Runtime per CDD month (key efficiency metric, mirrors runtime_per_hdd_month)
      - name: "HVAC Runtime per CDD Month"
        unique_id: hvac_runtime_per_cdd_month
        unit_of_measurement: "min/CDD"
        state_class: measurement
        icon: mdi:sun-thermometer
        availability: >
          {{ states('sensor.hvac_ac_runtime_month') not in ['unknown', 'unavailable'] }}
        state: >
          {% set runtime = states('sensor.hvac_ac_runtime_month') | float(0) %}
          {% set cdd = states('input_number.cdd_cumulative_month_auto') | float(0) %}
          {% if cdd > 0 and runtime > 0 %}
            {{ ((runtime * 60) / cdd) | round(1) }}
          {% else %}
            0
          {% endif %}
```

### 4c. SPC statistics and alert binary sensors

The SPC chain mirrors heating exactly — rolling 7-day mean and std dev computed live from the `runtime_per_cdd_day_1..7` sliding window, with `input_number` seed values as the fallback while the window populates. Alerts fire when the live 7-day ratio crosses mean ± 2σ bounds, gated on `count >= 3` to suppress bootstrap noise.

Add the five statistics template sensors in the template sensor block alongside the existing `hvac_runtime_per_hdd_*` statistics sensors. Then add the three binary sensor alerts alongside `hvac_furnace_short_cycling_alert`.

**Template sensors:**

```yaml
      # === RUNTIME/CDD SPC STATISTICS (mirrors runtime_per_hdd pattern) ===

      - name: "HVAC Runtime per CDD 7-Day Mean"
        unique_id: hvac_runtime_per_cdd_7_day_mean
        unit_of_measurement: "min/CDD"
        state_class: measurement
        icon: mdi:chart-bell-curve
        state: >
          {% set days = [
            states('input_number.runtime_per_cdd_day_1') | float(-1),
            states('input_number.runtime_per_cdd_day_2') | float(-1),
            states('input_number.runtime_per_cdd_day_3') | float(-1),
            states('input_number.runtime_per_cdd_day_4') | float(-1),
            states('input_number.runtime_per_cdd_day_5') | float(-1),
            states('input_number.runtime_per_cdd_day_6') | float(-1),
            states('input_number.runtime_per_cdd_day_7') | float(-1)
          ] %}
          {% set valid = days | select('>', 0) | select('<=', 120) | list %}
          {% if valid | length > 0 %}
            {{ (valid | sum / valid | length) | round(1) }}
          {% else %}
            {{ states('input_number.runtime_per_cdd_seed_mean') | float(18.0) }}
          {% endif %}

      - name: "HVAC Runtime per CDD 7-Day Std Dev"
        unique_id: hvac_runtime_per_cdd_7_day_stddev
        unit_of_measurement: "min/CDD"
        state_class: measurement
        icon: mdi:sigma
        state: >
          {% set days = [
            states('input_number.runtime_per_cdd_day_1') | float(-1),
            states('input_number.runtime_per_cdd_day_2') | float(-1),
            states('input_number.runtime_per_cdd_day_3') | float(-1),
            states('input_number.runtime_per_cdd_day_4') | float(-1),
            states('input_number.runtime_per_cdd_day_5') | float(-1),
            states('input_number.runtime_per_cdd_day_6') | float(-1),
            states('input_number.runtime_per_cdd_day_7') | float(-1)
          ] %}
          {% set valid = days | select('>', 0) | select('<=', 120) | list %}
          {% if valid | length > 1 %}
            {% set mean = valid | sum / valid | length %}
            {% set variance = namespace(sum=0) %}
            {% for v in valid %}
              {% set variance.sum = variance.sum + ((v - mean) ** 2) %}
            {% endfor %}
            {{ ((variance.sum / (valid | length - 1)) ** 0.5) | round(1) }}
          {% else %}
            {{ states('input_number.runtime_per_cdd_seed_stddev') | float(2.0) }}
          {% endif %}

      - name: "HVAC Runtime per CDD Upper Bound"
        unique_id: hvac_runtime_per_cdd_upper_bound
        unit_of_measurement: "min/CDD"
        state_class: measurement
        icon: mdi:arrow-up-bold
        state: >
          {% set mean = states('sensor.hvac_runtime_per_cdd_7_day_mean') | float(18.0) %}
          {% set stddev = states('sensor.hvac_runtime_per_cdd_7_day_stddev') | float(2.0) %}
          {{ (mean + (stddev * 2)) | round(1) }}

      - name: "HVAC Runtime per CDD Lower Bound"
        unique_id: hvac_runtime_per_cdd_lower_bound
        unit_of_measurement: "min/CDD"
        state_class: measurement
        icon: mdi:arrow-down-bold
        state: >
          {% set mean = states('sensor.hvac_runtime_per_cdd_7_day_mean') | float(18.0) %}
          {% set stddev = states('sensor.hvac_runtime_per_cdd_7_day_stddev') | float(2.0) %}
          {% set lower = mean - (stddev * 2) %}
          {{ lower | round(1) if lower > 0 else 0 }}

      - name: "HVAC Runtime per CDD Data Count"
        unique_id: hvac_runtime_per_cdd_data_count
        unit_of_measurement: "samples"
        state_class: measurement
        icon: mdi:counter
        state: >
          {% set days = [
            states('input_number.runtime_per_cdd_day_1') | float(-1),
            states('input_number.runtime_per_cdd_day_2') | float(-1),
            states('input_number.runtime_per_cdd_day_3') | float(-1),
            states('input_number.runtime_per_cdd_day_4') | float(-1),
            states('input_number.runtime_per_cdd_day_5') | float(-1),
            states('input_number.runtime_per_cdd_day_6') | float(-1),
            states('input_number.runtime_per_cdd_day_7') | float(-1)
          ] %}
          {{ days | select('>', 0) | select('<=', 120) | list | count }}
```

**Binary sensor alerts:**

```yaml
      # AC short cycling — compressors more sensitive than furnaces;
      # threshold 8 min (vs 5 min for furnace) to protect refrigerant pressures
      - name: "HVAC AC Short Cycling Alert"
        unique_id: hvac_ac_short_cycling_alert
        device_class: problem
        state: >
          {% set runtime = states('sensor.hvac_ac_runtime_today') | float(0) %}
          {% set cycles = states('sensor.hvac_ac_cycles_today') | int(0) %}
          {% if cycles > 3 and runtime > 0 %}
            {{ ((runtime * 60) / cycles) < 8 }}
          {% else %}
            false
          {% endif %}

      - name: "HVAC Runtime per CDD High Alert"
        unique_id: hvac_runtime_per_cdd_high_alert
        device_class: problem
        state: >
          {% set raw = states('sensor.hvac_runtime_per_cdd_7_day') %}
          {% if raw in ['unknown', 'unavailable'] %}
            false
          {% else %}
            {% set val = raw | float(0) %}
            {% set upper = states('sensor.hvac_runtime_per_cdd_upper_bound') | float(0) %}
            {% set count = states('sensor.hvac_runtime_per_cdd_data_count') | int(0) %}
            {{ val > upper and upper > 0 and count >= 3 }}
          {% endif %}

      - name: "HVAC Runtime per CDD Low Alert"
        unique_id: hvac_runtime_per_cdd_low_alert
        device_class: problem
        state: >
          {% set raw = states('sensor.hvac_runtime_per_cdd_7_day') %}
          {% if raw in ['unknown', 'unavailable'] %}
            false
          {% else %}
            {% set val = raw | float(0) %}
            {% set lower = states('sensor.hvac_runtime_per_cdd_lower_bound') | float(0) %}
            {% set count = states('sensor.hvac_runtime_per_cdd_data_count') | int(0) %}
            {{ val < lower and lower > 0 and count >= 3 }}
          {% endif %}
```

### 4d. Health monitoring binary sensors

Mirrors the HDD pipeline health chain exactly. Add alongside the existing `hdd_capture_stale`, `runtime_per_hdd_capture_stale`, and `runtime_per_hdd_pipeline_healthy` sensors.

**Important:** The stale sensors guard against the `1970-01-01 00:00:00` initial state that exists on first boot before any capture has succeeded — copy the pattern from the existing HDD stale sensor exactly, which returns `false` for that initial value rather than attempting the datetime subtraction.

```yaml
      - name: "CDD Capture Stale"
        unique_id: cdd_capture_stale
        device_class: problem
        state: >
          {% set last = states('input_datetime.cdd_capture_last_ok') %}
          {% if last in ['unknown', 'unavailable', '1970-01-01 00:00:00'] %}
            false
          {% else %}
            {{ (now() - last | as_datetime | as_local).total_seconds() / 3600 > 26 }}
          {% endif %}

      - name: "Runtime per CDD Capture Stale"
        unique_id: runtime_per_cdd_capture_stale
        device_class: problem
        state: >
          {% set last = states('input_datetime.runtime_per_cdd_capture_last_ok') %}
          {% if last in ['unknown', 'unavailable', '1970-01-01 00:00:00'] %}
            false
          {% else %}
            {{ (now() - last | as_datetime | as_local).total_seconds() / 3600 > 26 }}
          {% endif %}

      - name: "CDD Pipeline Healthy"
        unique_id: cdd_pipeline_healthy
        icon: mdi:thermometer-check
        state: >
          {% set proxy_ok = states('sensor.hvac_outdoor_temp_hartford_proxy') not in ['unknown', 'unavailable'] %}
          {% set not_stale = is_state('binary_sensor.cdd_capture_stale', 'off') %}
          {% set rolling = states('sensor.cdd_rolling_7_day_auto') | float(-1) %}
          {{ proxy_ok and not_stale and rolling >= 0 }}

      - name: "Runtime per CDD Pipeline Healthy"
        unique_id: runtime_per_cdd_pipeline_healthy
        icon: mdi:chart-timeline-variant-shimmer
        state: >
          {% set cdd_healthy = is_state('binary_sensor.cdd_pipeline_healthy', 'on') %}
          {% set not_stale = is_state('binary_sensor.runtime_per_cdd_capture_stale', 'off') %}
          {% set count = states('sensor.hvac_runtime_per_cdd_data_count') | int(0) %}
          {{ cdd_healthy and not_stale and count >= 4 }}
```

---

## Step 5 — Automation: capture_daily_cdd (automations.yaml)

**DO NOT modify `capture_daily_hdd`.** CDD tracking gets its own separate automation. Merging the CDD shift into `capture_daily_hdd` would couple two independent failure modes — if HDD capture skips due to a bad proxy value or out-of-range reading, it would also suppress CDD capture. The separate automation keeps pipelines independent and failure domains isolated.

Add a **new** automation that maintains the `cdd_day_1` through `cdd_day_7` sliding window. Insert it immediately after the `capture_daily_hdd` block.

```yaml
# AUTO CDD TRACKING - Daily capture at 11:55:15 PM (mirrors capture_daily_hdd)
# ===============================================================
- id: capture_daily_cdd
  alias: "Capture Daily CDD"
  description: "Shifts 7-day CDD sliding window and captures today's CDD value"
  mode: single
  trigger:
    - platform: time
      at: "23:55:15"
  action:
    - variables:
        todays_cdd: "{{ states('sensor.hvac_cdd65_today') | float(-1) }}"
        proxy_ok: "{{ states('sensor.hvac_outdoor_temp_hartford_proxy') not in ['unknown', 'unavailable'] }}"
    - choose:
        - conditions:
            - condition: template
              value_template: "{{ proxy_ok and todays_cdd >= 0 and todays_cdd <= 50 }}"
          sequence:
            - variables:
                d1: "{{ states('input_number.cdd_day_1')|float(0) }}"
                d2: "{{ states('input_number.cdd_day_2')|float(0) }}"
                d3: "{{ states('input_number.cdd_day_3')|float(0) }}"
                d4: "{{ states('input_number.cdd_day_4')|float(0) }}"
                d5: "{{ states('input_number.cdd_day_5')|float(0) }}"
                d6: "{{ states('input_number.cdd_day_6')|float(0) }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.cdd_day_7
              data:
                value: "{{ d6 }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.cdd_day_6
              data:
                value: "{{ d5 }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.cdd_day_5
              data:
                value: "{{ d4 }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.cdd_day_4
              data:
                value: "{{ d3 }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.cdd_day_3
              data:
                value: "{{ d2 }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.cdd_day_2
              data:
                value: "{{ d1 }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.cdd_day_1
              data:
                value: "{{ todays_cdd }}"
            - service: input_datetime.set_datetime
              target:
                entity_id: input_datetime.cdd_capture_last_ok
              data:
                datetime: "{{ now().strftime('%Y-%m-%d %H:%M:%S') }}"
            - service: system_log.write
              data:
                message: "CDD sliding window captured: today={{ todays_cdd }}"
                level: info
      default:
        - service: system_log.write
          data:
            level: warning
            message: >
              CDD capture skipped - proxy_ok={{ proxy_ok }},
              CDD={{ todays_cdd }}
```

---

## Step 6 — Automation: capture_daily_runtime_per_cdd (automations.yaml)

Add after `capture_daily_runtime_per_hdd`. Mirrors it exactly.

```yaml
# RUNTIME PER CDD TRACKING - Daily capture at 11:56:45 PM
# ===============================================================
- id: capture_daily_runtime_per_cdd
  alias: "Capture Daily Runtime per CDD"
  description: "Shifts 7-day runtime/CDD sliding window for cooling efficiency tracking"
  mode: single
  trigger:
    - platform: time
      at: "23:56:45"
  action:
    - variables:
        ac_runtime: "{{ states('sensor.hvac_ac_runtime_today') }}"
        todays_cdd: "{{ states('sensor.hvac_cdd65_today') | float(0) }}"
        upstream_ok: "{{ ac_runtime not in ['unknown', 'unavailable'] and
                         todays_cdd > 0 }}"
        todays_ratio: >
          {% if upstream_ok %}
            {% set rt_min = ac_runtime | float(0) * 60 %}
            {{ (rt_min / todays_cdd) | round(1) }}
          {% else %}
            -1
          {% endif %}
    - choose:
        - conditions:
            - condition: template
              value_template: "{{ upstream_ok and todays_ratio >= 0 }}"
          sequence:
            - variables:
                d1: "{{ states('input_number.runtime_per_cdd_day_1')|float(0) }}"
                d2: "{{ states('input_number.runtime_per_cdd_day_2')|float(0) }}"
                d3: "{{ states('input_number.runtime_per_cdd_day_3')|float(0) }}"
                d4: "{{ states('input_number.runtime_per_cdd_day_4')|float(0) }}"
                d5: "{{ states('input_number.runtime_per_cdd_day_5')|float(0) }}"
                d6: "{{ states('input_number.runtime_per_cdd_day_6')|float(0) }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.runtime_per_cdd_day_7
              data:
                value: "{{ d6 }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.runtime_per_cdd_day_6
              data:
                value: "{{ d5 }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.runtime_per_cdd_day_5
              data:
                value: "{{ d4 }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.runtime_per_cdd_day_4
              data:
                value: "{{ d3 }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.runtime_per_cdd_day_3
              data:
                value: "{{ d2 }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.runtime_per_cdd_day_2
              data:
                value: "{{ d1 }}"
            - service: input_number.set_value
              target:
                entity_id: input_number.runtime_per_cdd_day_1
              data:
                value: "{{ todays_ratio }}"
            - service: input_datetime.set_datetime
              target:
                entity_id: input_datetime.runtime_per_cdd_capture_last_ok
              data:
                datetime: "{{ now().strftime('%Y-%m-%d %H:%M:%S') }}"
            - service: system_log.write
              data:
                message: "Runtime/CDD sliding window captured: ratio={{ todays_ratio }} min/CDD"
                level: info
      default:
        - service: system_log.write
          data:
            level: warning
            message: >
              Runtime/CDD capture skipped - AC_runtime={{ ac_runtime }},
              CDD={{ todays_cdd }}
```

**Also add** both new `input_datetime` entries to the `input_datetime:` section in configuration.yaml, alongside the existing `hdd_capture_last_ok` and `runtime_per_hdd_capture_last_ok` entries. Both require `has_date: true` and `has_time: true` — without these HA creates a time-only entity and the `set_datetime` calls storing full timestamps will fail silently:

```yaml
  cdd_capture_last_ok:
    name: "CDD Capture Last OK"
    has_date: true
    has_time: true
    icon: mdi:check-circle

  runtime_per_cdd_capture_last_ok:
    name: "Runtime/CDD Capture Last OK"
    has_date: true
    has_time: true
    icon: mdi:check-circle
```

---

## Step 7 — Modify capture_daily_monthly_tracking (automations.yaml)

This is the most complex change. Three additions are needed to the existing `capture_daily_monthly_tracking` automation:

### 7a. Add variables snapshot (after existing zone_2f_cycles_acc variable)

```yaml
        # AC cooling daily values
        ac_runtime_today: "{{ states('sensor.hvac_ac_runtime_today') | float(0) }}"
        ac_cycles_today: "{{ states('sensor.hvac_ac_cycles_today') | int(0) }}"
        zone_1f_cool_runtime_today: "{{ states('sensor.hvac_1f_cool_runtime_today') | float(0) }}"
        zone_2f_cool_runtime_today: "{{ states('sensor.hvac_2f_cool_runtime_today') | float(0) }}"
        zone_1f_cool_cycles_today: "{{ states('sensor.hvac_1f_cool_cycles_today') | int(0) }}"
        zone_2f_cool_cycles_today: "{{ states('sensor.hvac_2f_cool_cycles_today') | int(0) }}"
        # AC cooling accumulators
        ac_runtime_acc: "{{ states('input_number.ac_runtime_month_acc') | float(0) }}"
        ac_cycles_acc: "{{ states('input_number.ac_cycles_month_acc') | int(0) }}"
        zone_1f_cool_runtime_acc: "{{ states('input_number.zone_1f_cool_runtime_month_acc') | float(0) }}"
        zone_2f_cool_runtime_acc: "{{ states('input_number.zone_2f_cool_runtime_month_acc') | float(0) }}"
        zone_1f_cool_cycles_acc: "{{ states('input_number.zone_1f_cool_cycles_month_acc') | int(0) }}"
        zone_2f_cool_cycles_acc: "{{ states('input_number.zone_2f_cool_cycles_month_acc') | int(0) }}"
        # AC cooling yearly accumulators
        ac_runtime_year_acc: "{{ states('input_number.ac_runtime_year_acc') | float(0) }}"
        ac_cycles_year_acc: "{{ states('input_number.ac_cycles_year_acc') | int(0) }}"
```

### 7b. Add accumulator update steps (after the existing zone_2f_cycles_month_acc update, before the expected_runtime_sum step)

```yaml
    # ── AC cooling accumulators ──────────────────────────────────
    - service: input_number.set_value
      target:
        entity_id: input_number.ac_runtime_month_acc
      data:
        value: "{{ (ac_runtime_acc + ac_runtime_today) | round(2) }}"
    - service: input_number.set_value
      target:
        entity_id: input_number.ac_cycles_month_acc
      data:
        value: "{{ ac_cycles_acc + ac_cycles_today }}"
    - service: input_number.set_value
      target:
        entity_id: input_number.zone_1f_cool_runtime_month_acc
      data:
        value: "{{ (zone_1f_cool_runtime_acc + zone_1f_cool_runtime_today) | round(2) }}"
    - service: input_number.set_value
      target:
        entity_id: input_number.zone_2f_cool_runtime_month_acc
      data:
        value: "{{ (zone_2f_cool_runtime_acc + zone_2f_cool_runtime_today) | round(2) }}"
    - service: input_number.set_value
      target:
        entity_id: input_number.zone_1f_cool_cycles_month_acc
      data:
        value: "{{ zone_1f_cool_cycles_acc + zone_1f_cool_cycles_today }}"
    - service: input_number.set_value
      target:
        entity_id: input_number.zone_2f_cool_cycles_month_acc
      data:
        value: "{{ zone_2f_cool_cycles_acc + zone_2f_cool_cycles_today }}"
    # ── AC cooling yearly accumulators ───────────────────────────
    - service: input_number.set_value
      target:
        entity_id: input_number.ac_runtime_year_acc
      data:
        value: "{{ (ac_runtime_year_acc + ac_runtime_today) | round(2) }}"
    - service: input_number.set_value
      target:
        entity_id: input_number.ac_cycles_year_acc
      data:
        value: "{{ ac_cycles_year_acc + ac_cycles_today }}"
```

### 7c. Update the system_log.write message to include AC runtime

Append `, AC={{ ac_runtime_today }}h` to the existing log message so cooling data is visible in logs.

---

## Step 8 — Modify reset_monthly_hdd (automations.yaml)

Add AC accumulator resets alongside the furnace/zone heat resets. Insert after `zone_2f_cycles_month_acc` reset. Also update the existing `system_log.write` message at the end of the action to reflect that AC accumulators are now included — change `"Monthly HDD/CDD and furnace accumulators reset completed"` to `"Monthly HDD/CDD, furnace, and AC cooling accumulators reset completed"`:

```yaml
    # Reset AC cooling monthly accumulators
    - service: input_number.set_value
      target:
        entity_id: input_number.ac_runtime_month_acc
      data:
        value: 0
    - service: input_number.set_value
      target:
        entity_id: input_number.ac_cycles_month_acc
      data:
        value: 0
    - service: input_number.set_value
      target:
        entity_id: input_number.zone_1f_cool_runtime_month_acc
      data:
        value: 0
    - service: input_number.set_value
      target:
        entity_id: input_number.zone_2f_cool_runtime_month_acc
      data:
        value: 0
    - service: input_number.set_value
      target:
        entity_id: input_number.zone_1f_cool_cycles_month_acc
      data:
        value: 0
    - service: input_number.set_value
      target:
        entity_id: input_number.zone_2f_cool_cycles_month_acc
      data:
        value: 0
```

Apply the same additions to `reset_yearly_hdd` if AC data is also tracked on a yearly basis (recommended — add yearly accumulators if desired, following the same pattern as `hdd_cumulative_year_auto`).

Add these resets to `reset_yearly_hdd` alongside the existing `hdd_cumulative_year_auto` and `cdd_cumulative_year_auto` resets:

```yaml
    # Reset AC cooling yearly accumulators
    - service: input_number.set_value
      target:
        entity_id: input_number.ac_runtime_year_acc
      data:
        value: 0
    - service: input_number.set_value
      target:
        entity_id: input_number.ac_cycles_year_acc
      data:
        value: 0
```

---

## Step 9 — Update Shell Commands (configuration.yaml)

### 9a. appenddailycsv

Add these fields to the JSON payload in `shell_command.appenddailycsv`, after the `basement_dew_point` line:

```yaml
      "cdd65": {{ states('sensor.hvac_cdd65_today') | float(0) }},
      "ac_runtime_min": {{ (states('sensor.hvac_ac_runtime_today') | float(0) * 60) | round(1) }},
      "ac_cycles": {{ states('sensor.hvac_ac_cycles_today') | int(0) }},
      "ac_min_per_cycle": {{ states('sensor.hvac_ac_min_per_cycle') | float(0) }},
      "cool_calls_total": {{ states('sensor.hvac_total_cool_cycles_today') | int(0) }},
      "cool_runtime_1f_min": {{ (states('sensor.hvac_1f_cool_runtime_today') | float(0) * 60) | round(1) }},
      "cool_runtime_2f_min": {{ (states('sensor.hvac_2f_cool_runtime_today') | float(0) * 60) | round(1) }}
```

### 9b. appendmonthlycsv

Add these fields after `electric_kwh`. Note that `total_cdd65` is included here — the current shell command only has `total_hdd65` and omits CDD entirely despite the accumulator being populated. This is a pre-existing gap that must be fixed as part of this build-out.

```yaml
      "total_cdd65": {{ states('input_number.cdd_cumulative_month_auto') | float(0) }},
      "ac_runtime_hours": {{ states('sensor.hvac_ac_runtime_month') | float(0) }},
      "avg_runtime_per_cdd": {{ states('sensor.hvac_runtime_per_cdd_month') | float(0) }}
```

### 9c. backup_input_numbers

Add to the backup JSON after the existing `z2f_cy_acc` line:

```yaml
      "ac_rt_acc": {{ states('input_number.ac_runtime_month_acc') | float(0) }},
      "ac_cy_acc": {{ states('input_number.ac_cycles_month_acc') | int(0) }},
      "z1f_cool_rt_acc": {{ states('input_number.zone_1f_cool_runtime_month_acc') | float(0) }},
      "z2f_cool_rt_acc": {{ states('input_number.zone_2f_cool_runtime_month_acc') | float(0) }},
      "z1f_cool_cy_acc": {{ states('input_number.zone_1f_cool_cycles_month_acc') | int(0) }},
      "z2f_cool_cy_acc": {{ states('input_number.zone_2f_cool_cycles_month_acc') | int(0) }},
      "cdd_d1": {{ states('input_number.cdd_day_1') | float(0) }},
      "cdd_d2": {{ states('input_number.cdd_day_2') | float(0) }},
      "cdd_d3": {{ states('input_number.cdd_day_3') | float(0) }},
      "cdd_d4": {{ states('input_number.cdd_day_4') | float(0) }},
      "cdd_d5": {{ states('input_number.cdd_day_5') | float(0) }},
      "cdd_d6": {{ states('input_number.cdd_day_6') | float(0) }},
      "cdd_d7": {{ states('input_number.cdd_day_7') | float(0) }},
      "cdd_seed_mean": {{ states('input_number.runtime_per_cdd_seed_mean') | float(0) }},
      "cdd_seed_stddev": {{ states('input_number.runtime_per_cdd_seed_stddev') | float(0) }},
      "rpc_d1": {{ states('input_number.runtime_per_cdd_day_1') | float(0) }},
      "rpc_d2": {{ states('input_number.runtime_per_cdd_day_2') | float(0) }},
      "rpc_d3": {{ states('input_number.runtime_per_cdd_day_3') | float(0) }},
      "rpc_d4": {{ states('input_number.runtime_per_cdd_day_4') | float(0) }},
      "rpc_d5": {{ states('input_number.runtime_per_cdd_day_5') | float(0) }},
      "rpc_d6": {{ states('input_number.runtime_per_cdd_day_6') | float(0) }},
      "rpc_d7": {{ states('input_number.runtime_per_cdd_day_7') | float(0) }}
```

---

## Step 10 — Filter Runtime Fix (automations.yaml)

The `accumulate_filter_runtime` automation currently only counts heat runtime toward filter hours. Since the same air handler filter is used during cooling cycles, AC runtime must be added.

Locate `accumulate_filter_runtime` (~line 1065). Change the condition and value template:

**Condition — change from:**
```yaml
              value_template: >
                {{ is_number(states('sensor.hvac_total_heat_runtime_today')) and
                   (states('sensor.hvac_total_heat_runtime_today')|float) >= 0 }}
```

**To:**
```yaml
              value_template: >
                {{ (is_number(states('sensor.hvac_total_heat_runtime_today')) and
                    states('sensor.hvac_total_heat_runtime_today')|float >= 0) or
                   (is_number(states('sensor.hvac_ac_runtime_today')) and
                    states('sensor.hvac_ac_runtime_today')|float >= 0) }}
```

**Value — change from:**
```yaml
                value: >
                  {{ (states('input_number.hvac_filter_runtime_hours')|float(0) +
                      states('sensor.hvac_total_heat_runtime_today')|float)|round(2) }}
```

**To:**
```yaml
                value: >
                  {{ (states('input_number.hvac_filter_runtime_hours')|float(0) +
                      states('sensor.hvac_total_heat_runtime_today')|float(0) +
                      states('sensor.hvac_ac_runtime_today')|float(0))|round(2) }}
```

---

## Step 11 — Health Monitoring Notify Automations (automations.yaml)

Add alongside the existing `notify_hdd_capture_stale` and `notify_runtime_per_hdd_capture_stale` automations. Mirrors them exactly — only names, IDs, entity references, and messages differ.

Also add the three **alert** notifications that mirror `notify_short_cycling_furnace`, `notify_runtime_per_hdd_high`, and `notify_runtime_per_hdd_low`. The binary sensors for these are defined in Step 4c but without notify automations they will only appear as silent Lovelace problems — no persistent notifications will fire.

```yaml
- id: notify_ac_short_cycling
  alias: "Notify AC Short Cycling"
  description: "Alert when AC compressor is short cycling (<8 min/cycle)"
  mode: single
  trigger:
    - platform: state
      entity_id: binary_sensor.hvac_ac_short_cycling_alert
      to: "on"
      for:
        minutes: 15
  action:
    - service: persistent_notification.create
      data:
        title: "AC Short Cycling Alert"
        message: >
          AC compressor is short cycling: {{ states('sensor.hvac_ac_min_per_cycle') }} min/cycle
          (threshold: 8 min). Cycles today: {{ states('sensor.hvac_ac_cycles_today') }}.
          Check refrigerant charge, filter, and thermostat settings.
        notification_id: ac_short_cycling

- id: notify_runtime_per_cdd_high
  alias: "Notify Runtime per CDD High"
  description: "Alert when runtime/CDD 7-day ratio exceeds mean+2σ upper bound"
  mode: single
  trigger:
    - platform: state
      entity_id: binary_sensor.hvac_runtime_per_cdd_high_alert
      to: "on"
      for:
        hours: 2
  action:
    - service: persistent_notification.create
      data:
        title: "Runtime/CDD High Alert"
        message: >
          AC runtime/CDD ratio {{ states('sensor.hvac_runtime_per_cdd_7_day') }} min/CDD
          exceeds upper bound {{ states('sensor.hvac_runtime_per_cdd_upper_bound') }} (mean + 2σ).
          Possible causes: dirty filter, low refrigerant, high humidity load, or degraded equipment.
        notification_id: runtime_per_cdd_high

- id: notify_runtime_per_cdd_low
  alias: "Notify Runtime per CDD Low"
  description: "Alert when runtime/CDD 7-day ratio falls below mean-2σ lower bound"
  mode: single
  trigger:
    - platform: state
      entity_id: binary_sensor.hvac_runtime_per_cdd_low_alert
      to: "on"
      for:
        hours: 2
  action:
    - service: persistent_notification.create
      data:
        title: "Runtime/CDD Low Alert"
        message: >
          AC runtime/CDD ratio {{ states('sensor.hvac_runtime_per_cdd_7_day') }} min/CDD
          is below lower bound {{ states('sensor.hvac_runtime_per_cdd_lower_bound') }} (mean - 2σ).
          Possible causes: very low humidity, sensor fault, or unusually efficient conditions.
        notification_id: runtime_per_cdd_low

- id: notify_cdd_capture_stale
  alias: "Notify CDD Capture Stale"
  description: "Alert when CDD sliding window capture has not succeeded in 26+ hours"
  mode: single
  trigger:
    - platform: state
      entity_id: binary_sensor.cdd_capture_stale
      to: "on"
      for:
        hours: 2
  action:
    - service: persistent_notification.create
      data:
        title: "CDD Capture Stale"
        message: >
          CDD capture has not succeeded in over 26 hours.
          Last OK: {{ states('input_datetime.cdd_capture_last_ok') }}.
          Check outdoor proxy sensor and capture_daily_cdd automation.
        notification_id: cdd_capture_stale

- id: notify_runtime_per_cdd_capture_stale
  alias: "Notify Runtime per CDD Capture Stale"
  description: "Alert when runtime/CDD sliding window capture has not succeeded in 26+ hours"
  mode: single
  trigger:
    - platform: state
      entity_id: binary_sensor.runtime_per_cdd_capture_stale
      to: "on"
      for:
        hours: 2
  action:
    - service: persistent_notification.create
      data:
        title: "Runtime/CDD Capture Stale"
        message: >
          Runtime/CDD capture has not succeeded in over 26 hours.
          Last OK: {{ states('input_datetime.runtime_per_cdd_capture_last_ok') }}.
          Check AC runtime sensor and capture_daily_runtime_per_cdd automation.
        notification_id: runtime_per_cdd_capture_stale
```

The existing EOD sequence runs at:
- 23:54:30 — daily high/low reset  
- 23:55:00 — `capture_daily_hdd`  
- **23:55:15 — `capture_daily_cdd` (NEW)**  
- 23:56:00 — `capture_daily_runtime_per_hdd`  
- 23:56:15 — `capture_daily_furnace_min_per_cycle`  
- 23:56:30 — `capture_daily_monthly_tracking`  
- **23:56:45 — `capture_daily_runtime_per_cdd` (NEW)**  
- 23:57:00 — `appenddailycsv`  
- 23:58:00 — `accumulate_filter_runtime`  
- 23:58:30 — `appendmonthlycsv` (last day only)  

No conflicts. CDD window capture runs 15 seconds after HDD, runtime/CDD capture runs 15 seconds after monthly tracking — both after all source data is stable.

---

## Step 12 — Update HVAC Daily Electric Cost Estimate (configuration.yaml)

**Verified gap:** `sensor.hvac_daily_electric_cost_estimate` (line ~2304 of configuration.yaml) uses only `sensor.hvac_furnace_runtime_today` with `blower_kw = 0.5`. During cooling season the AC condenser is the dominant load — this sensor will read near $0 all summer and the downstream `sensor.hvac_daily_total_cost_estimate` will under-report accordingly.

**Two corrections in this step — not one:**

1. **`blower_kw` is wrong for heating too.** The existing template hardcodes `blower_kw = 0.5`, but SYSTEM_SPECIFICATIONS.md documents a measured draw of **0.21 kW** during heating operation (Vortica II ECM motor). The 0.5 kW figure is 2.4× the actual draw, meaning the heating electricity cost estimate has been overstated since deployment. Correct it here.

2. **`condenser_kw` from primary source.** SYSTEM_SPECIFICATIONS.md documents a measured steady-state outdoor unit draw of **4.9 kW** (American Standard Silver 14, 4-ton). Use this directly — bottom-up derivation from billing data is not viable because the dehumidifier and AC are concurrent summer loads that cannot be separated without circuit-level monitoring (Fusion Energy CT system, planned but not yet installed).

Add `input_number.ac_condenser_kw` to the `input_number:` section alongside the other system constants:

```yaml
  ac_condenser_kw:
    name: "AC Condenser Power Draw"
    min: 0
    max: 10
    step: 0.1
    initial: 4.9
    mode: box
    unit_of_measurement: "kW"
    icon: mdi:air-conditioner
```

Then replace the existing `hvac_daily_electric_cost_estimate` template sensor with:

```yaml
      # Uses furnace blower runtime (heating) + AC compressor runtime (cooling)
      # blower_kw = 0.21: measured ECM draw per SYSTEM_SPECIFICATIONS.md (corrected from 0.5)
      # condenser_kw drawn from input_number: 4.9 kW measured steady-state per SYSTEM_SPECIFICATIONS.md
      # AC total = blower + condenser (blower runs during both heat and cool calls)
      - name: "HVAC Daily Electric Cost Estimate"
        unique_id: hvac_daily_electric_cost_estimate
        unit_of_measurement: "$"
        state_class: measurement
        icon: mdi:currency-usd
        state: >
          {% set heat_runtime = states('sensor.hvac_furnace_runtime_today') | float(0) %}
          {% set ac_runtime = states('sensor.hvac_ac_runtime_today') | float(0) %}
          {% set blower_kw = 0.21 %}
          {% set condenser_kw = states('input_number.ac_condenser_kw') | float(4.9) %}
          {% set elec_rate = states('sensor.electricity_effective_rate') | float(0.27) %}
          {% set heat_cost = heat_runtime * blower_kw * elec_rate %}
          {% set ac_cost = ac_runtime * (blower_kw + condenser_kw) * elec_rate %}
          {{ (heat_cost + ac_cost) | round(2) }}
```

**Note on future calibration:** The 4.9 kW figure is a steady-state measurement from SYSTEM_SPECIFICATIONS.md — it is the best available primary source until the Fusion Energy CT monitoring system is installed. At that point, verify against actual circuit data and update `input_number.ac_condenser_kw` via Developer Tools if needed. The `| float(4.9)` fallback in the template ensures the sensor remains functional even if the input_number entity is temporarily unavailable.

---

## Step 13 — Update Daily HVAC Summary Automation (automations.yaml)

**Verified gap:** `daily_hvac_summary` (line ~876 of automations.yaml) has condition `{{ states('sensor.hvac_hdd65_today') | float(0) > 0 }}`. On any day where HDD = 0 (every day from roughly May through September in CT), the automation is silently suppressed — no evening summary fires for the entire cooling season.

Replace the existing `daily_hvac_summary` automation with:

```yaml
- id: daily_hvac_summary
  alias: "Daily HVAC Summary"
  trigger:
    - platform: time
      at: "22:00:00"
  condition:
    - condition: template
      value_template: >
        {{ states('sensor.hvac_hdd65_today') | float(0) > 0 or
           states('sensor.hvac_cdd65_today') | float(0) > 0 }}
  action:
    - service: persistent_notification.create
      data:
        title: "📊 Daily HVAC Summary"
        message: >
          {% if states('sensor.hvac_hdd65_today') | float(0) > 0 %}
          🔥 Heating: HDD={{ states('sensor.hvac_hdd65_today') }}
          Runtime={{ states('sensor.hvac_total_heat_runtime_today') }}h
          {% endif %}
          {% if states('sensor.hvac_cdd65_today') | float(0) > 0 %}
          ❄️ Cooling: CDD={{ states('sensor.hvac_cdd65_today') }}
          AC Runtime={{ states('sensor.hvac_ac_runtime_today') }}h
          {% endif %}
          Zone Balance: {{ states('sensor.hvac_zone_balance_ratio_today') }}%
```

**Note:** The condition now passes on any day with meaningful thermal load (HDD > 0 OR CDD > 0). Shoulder-season days where both HDD and CDD are 0 (rare, but possible in May/October) will correctly suppress the notification since there is nothing to report.

---



For ENTITIES.md and Claude Code awareness:

| Entity | Type | Description |
|---|---|---|
| `binary_sensor.hvac_1f_call_for_cool` | binary_sensor | Zone 1F cooling active |
| `binary_sensor.hvac_2f_call_for_cool` | binary_sensor | Zone 2F cooling active |
| `binary_sensor.hvac_ac_running` | binary_sensor | Compressor running (OR of zones) |
| `binary_sensor.hvac_ac_short_cycling_alert` | binary_sensor | AC short cycling (<8 min/cycle) |
| `binary_sensor.hvac_runtime_per_cdd_high_alert` | binary_sensor | Runtime/CDD above mean+2σ |
| `binary_sensor.hvac_runtime_per_cdd_low_alert` | binary_sensor | Runtime/CDD below mean-2σ |
| `binary_sensor.cdd_capture_stale` | binary_sensor | CDD window capture >26h ago |
| `binary_sensor.runtime_per_cdd_capture_stale` | binary_sensor | Runtime/CDD capture >26h ago |
| `binary_sensor.cdd_pipeline_healthy` | binary_sensor | Proxy OK + not stale + rolling valid |
| `binary_sensor.runtime_per_cdd_pipeline_healthy` | binary_sensor | CDD healthy + not stale + count≥4 |
| `sensor.hvac_1f_cool_runtime_today` | history_stats | Zone 1F cool runtime today (h) |
| `sensor.hvac_2f_cool_runtime_today` | history_stats | Zone 2F cool runtime today (h) |
| `sensor.hvac_ac_runtime_today` | history_stats | Compressor runtime today (h) |
| `sensor.hvac_1f_cool_cycles_today` | history_stats | Zone 1F cool cycles today |
| `sensor.hvac_2f_cool_cycles_today` | history_stats | Zone 2F cool cycles today |
| `sensor.hvac_ac_cycles_today` | history_stats | Compressor cycles today |
| `sensor.hvac_1f_cool_runtime_week` | history_stats | Zone 1F cool runtime 7d (h) |
| `sensor.hvac_2f_cool_runtime_week` | history_stats | Zone 2F cool runtime 7d (h) |
| `sensor.hvac_ac_runtime_week` | history_stats | Compressor runtime 7d (h) |
| `sensor.hvac_total_cool_runtime_today` | template | Sum of zone cool runtimes today |
| `sensor.hvac_total_cool_cycles_today` | template | Sum of zone cool cycles today |
| `sensor.hvac_ac_min_per_cycle` | template | AC min/cycle today |
| `sensor.cdd_rolling_7_day_auto` | template | 7-day CDD rolling sum |
| `sensor.hvac_runtime_per_cdd_7_day` | template | Runtime/CDD 7-day (min/CDD) — numerator is hvac_ac_runtime_week |
| `sensor.hvac_ac_runtime_month` | template | AC runtime MTD (acc + today) |
| `sensor.hvac_ac_cycles_month` | template | AC cycles MTD |
| `sensor.hvac_1f_cool_runtime_month` | template | Zone 1F cool runtime MTD |
| `sensor.hvac_2f_cool_runtime_month` | template | Zone 2F cool runtime MTD |
| `sensor.hvac_runtime_per_cdd_month` | template | Runtime/CDD MTD (min/CDD) |
| `sensor.hvac_runtime_per_cdd_7_day_mean` | template | 7-day rolling mean (min/CDD) |
| `sensor.hvac_runtime_per_cdd_7_day_stddev` | template | 7-day rolling std dev (min/CDD) |
| `sensor.hvac_runtime_per_cdd_upper_bound` | template | SPC upper bound mean+2σ |
| `sensor.hvac_runtime_per_cdd_lower_bound` | template | SPC lower bound mean-2σ |
| `sensor.hvac_runtime_per_cdd_data_count` | template | Valid samples in 7-day window |
| `input_number.ac_runtime_month_acc` | input_number | AC runtime accumulator |
| `input_number.ac_cycles_month_acc` | input_number | AC cycles accumulator |
| `input_number.ac_runtime_year_acc` | input_number | AC runtime yearly accumulator |
| `input_number.ac_cycles_year_acc` | input_number | AC cycles yearly accumulator |
| `input_number.zone_1f_cool_runtime_month_acc` | input_number | Zone 1F cool runtime acc |
| `input_number.zone_2f_cool_runtime_month_acc` | input_number | Zone 2F cool runtime acc |
| `input_number.zone_1f_cool_cycles_month_acc` | input_number | Zone 1F cool cycles acc |
| `input_number.zone_2f_cool_cycles_month_acc` | input_number | Zone 2F cool cycles acc |
| `input_number.cdd_day_1..7` | input_number | CDD 7-day sliding window |
| `input_number.runtime_per_cdd_day_1..7` | input_number | Runtime/CDD 7-day sliding window |
| `input_number.runtime_per_cdd_seed_mean` | input_number | SPC fallback mean (update after first week) |
| `input_number.runtime_per_cdd_seed_stddev` | input_number | SPC fallback std dev (update after first week) |
| `input_number.ac_condenser_kw` | input_number | AC condenser power draw (kW) for cost estimate |
| `input_datetime.cdd_capture_last_ok` | input_datetime | Last successful CDD window capture |
| `input_datetime.runtime_per_cdd_capture_last_ok` | input_datetime | Last successful runtime/CDD capture |

---

## Implementation Notes for Claude Code

1. **Verify thermostat entity IDs** before writing binary sensors. Run `ha state list | grep tstat` in the HA terminal to confirm `tstat_2d884c` = 1F and `tstat_2d8878` = 2F. If `_2` suffix entities exist in the registry, use whichever is currently active.

2. **Validate YAML after each section** with `ha config check` before restarting.

3. **Two new `input_datetime` entries** — `cdd_capture_last_ok` and `runtime_per_cdd_capture_last_ok` — both need `has_date: true` and `has_time: true` in their definitions, and must appear in the `input_datetime:` section of configuration.yaml before the automations that set them are triggered. Without `has_date`/`has_time`, HA creates a time-only entity and the `set_datetime` calls storing full `%Y-%m-%d %H:%M:%S` timestamps will fail silently, leaving the stale sensors permanently `false`.

4. **Do not add** a `hvac_cdd65_cumulative_month` or `hvac_cdd65_cumulative_year` template sensor — these would duplicate the existing `input_number.cdd_cumulative_month_auto` which is already populated correctly by `capture_daily_monthly_tracking`.

5. **No week history_stats month sensors** — same rationale as heating (fail after day 14). Monthly data comes from accumulators only.

6. **SPC/statistical bounds for runtime_per_cdd** use the same rolling 7-day live computation as heating — no seasonal baseline required. The mean and std dev template sensors compute from `runtime_per_cdd_day_1..7` as soon as data exists, with `count >= 3` gating the alerts during bootstrap. `input_number.runtime_per_cdd_seed_mean` (18.0) and `runtime_per_cdd_seed_stddev` (2.0) are the fallback while the window is empty and remain as drain-recovery fallback thereafter. Update the seed values via Developer Tools after the first week of cooling operation to reflect your actual system performance. The `| float(18.0)` / `| float(2.0)` literals in the upper/lower bound sensors are a last-resort guard only if the input_number entities themselves are unavailable.

7. **The CDD day_1..7 slots will initialize to 0** when created. The rolling window will be fully populated after 7 days of operation. The `cdd_rolling_7_day_auto` sensor correctly uses `select('>=', 0)` to exclude uninitialized `-1` slots — use the same `-1` default approach as HDD (`float(-1)` in the shift automation variables, valid range `0–50`).

8. **Do NOT modify `capture_daily_hdd`** to add CDD shifting. `capture_daily_cdd` is a separate automation (Step 5). Modifying the existing automation couples unrelated failure modes — a bad HDD reading that causes the HDD capture to skip would also suppress the CDD window shift. The pipelines must remain independent.

9. **`appendmonthlycsv` has a pre-existing CDD gap** — the current shell command includes `total_hdd65` but omits `total_cdd65` entirely, even though `input_number.cdd_cumulative_month_auto` has been populated correctly all along. Step 9b corrects this. Do not skip Step 9b on the assumption that CDD is already being exported — it is not.

10. **Recorder purge and history_stats:** The `history_stats` sensors in Step 2 (today and week) depend on recorder history. If `purge_keep_days` is set to 7 or less, the week sensors will under-report on days near the purge boundary. The month sensors in Step 4b are immune — they use `input_number` accumulators that are independent of the recorder. This matches the same constraint that already applies to the heating history_stats sensors.

11. **`blower_kw` correction affects the heating cost estimate too.** Changing `blower_kw` from 0.5 to 0.21 (measured per SYSTEM_SPECIFICATIONS.md) reduces `hvac_daily_electric_cost_estimate` during heating season by ~58%. This is a correction of a pre-existing overstatement, not a new behavior — the heating cost estimate has been running high since deployment. `input_number.ac_condenser_kw` initializes at 4.9 kW (measured steady-state per SYSTEM_SPECIFICATIONS.md). Update it via Developer Tools after Fusion Energy CT monitoring is installed and actual circuit draw is confirmed.
