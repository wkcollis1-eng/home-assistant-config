---
name: engineering-monthly-update
description: >
  Monthly data update workflow for wkcollis1-eng repositories. Use this skill
  whenever the user mentions entering a monthly bill, updating monthly data,
  logging a new month, monthly archive, monthly update, or any reference to
  adding a new month of data across home-assistant-config,
  Residential-HVAC-Performance-Baseline-, Lifepo4-Battery-Banks, or
  DIY-LiFePO4-UPS. Also triggers on: "it's the 1st", "bill came in",
  "enter the gas bill", "update the baseline", "log this month",
  "monthly commit", or any CalVer YYYY.MM reference.
---

## DATA SOURCE HIERARCHY

Priority order when multiple sources are available for the same value:

```
1. Archives (input_number.*_archive_*)   permanent records — highest trust
2. HA sensors (sensor.*)                 derived/calculated — use if archive absent
3. Live readings / external meter        current-month entry only
```

CONFLICT EXCEPTION:
If a higher-priority source conflicts with a lower-priority source by >10%:
→ Do not silently prefer the higher source
→ FLAG: state both values, likely cause, which to use
→ Wait for user confirmation before proceeding
→ Document resolution in output report

Common conflict causes:
  archive wrong → sensor correct:   billing period mismatch, prior manual error
  sensor drifted → archive correct: calibration change, integration restart
  both suspect:                     HA downtime gap, CSV corruption — HALT, ask user

## WORKFLOW (follow in order — never skip validation)

```
1. IDENTIFY    — which repo(s) and what data for this month
2. VALIDATE    — sanity check against prior months before any entry
3. ENTER       — update dataset per repo-specific procedure
4. RECALCULATE — derive updated metrics, report before/after
5. DOCUMENT    — CHANGELOG.md + README if threshold crossed
6. COMMIT      — one logical change, CalVer message
7. REPORT      — structured output (see §OUTPUT FORMAT)
```

## SESSION VARIABLE (set this first — used throughout)

```
target_month: YYYY-MM        the month being updated (e.g. 2026-03)
archive_slot: [month name]   the archive slot receiving the data (e.g. "march")

DHW special case:
  If entering DHW on the 1st:
    target_month = current month (when you're doing the entry)
    archive_slot = PREVIOUS month (where the data saves)
    e.g. entering on 2026-03-01 → archive_slot = "february"

Use target_month consistently in:
  commit messages, CHANGELOG entries, output report header
Do not mix bill date, entry date, and archive month — they are three different things.
```

## HALT CONDITIONS (stop execution — do not proceed past these)

```
HALT-1: prior month data missing or zero for any validated field
        → "Prior month [field] is missing. Confirm data or enter manually before proceeding."

HALT-2: validation FLAG unresolved — user has not confirmed the anomaly
        → Do not enter data until user explicitly confirms or corrects the value.

HALT-3: unit ambiguous — Therms vs CCF unclear from user input
        → "Confirm unit: is [value] in Therms or CCF?"
        → Never assume. Never silently convert without confirming unit first.

HALT-4: target_month not established
        → "Which month is this update for?"

HALT-5: archive slot conflict — data already present for target month
        → "[archive_slot] already has value [X]. Overwrite or skip?"
```

## VALIDATION RULES (apply to all repos before any data entry)

```
RULE V1 — Range check
New value within ±25% of trailing 3-month average → PASS
Outside ±25% → FLAG
  Claude must provide: deviation %, likely causal explanation (seasonality, billing period
  shift, equipment change, occupancy effect, meter read anomaly)
  Proceed ONLY IF user explicitly confirms in current turn
  Document justification in output report under FLAGS

RULE V2 — Direction check
Efficiency metrics (CCF/1kHDD, kWh, runtime/HDD) should trend consistently
with HDD. A high-HDD month with lower-than-expected gas use → FLAG if >15% deviation
A low-HDD month with higher-than-expected gas use → FLAG if >15% deviation
  Same override condition as V1: user confirmation required + justification documented

RULE V4 — Unit check
Gas: always CCF in archives — Navien reading is in Therms
  Conversion: CCF = Therms × 0.9643  (1 Thm = 100,000 BTU; 1 CCF = 103,700 BTU)
  Never reverse this formula. Never store Therms in archive fields.
Electric: always kWh
DHW: always CCF in archives — same conversion from Navien Therms reading
Temperature: always °F for HVAC, °C for battery/UPS

RULE V5 — Date alignment
Gas/electric bills: ~10th of month (billing period misalignment expected — note it)
Navien DHW: entered ~1st of month for PREVIOUS month
If user enters DHW on 1st → archives to PREVIOUS month (not current)
```

## DATA SOURCES (where to find prior data for validation)

```
REPO 1 — home-assistant-config

  Gas archives:
    input_number.gas_archive_jan … gas_archive_dec

  Electric archives:
    input_number.electric_archive_jan … electric_archive_dec (suffix _kwh / _amount)

  DHW archives:
    input_number.dhw_archive_jan … dhw_archive_dec

  Current month live metrics:
    sensor.hvac_heating_efficiency_12m, sensor.hvac_building_load_ua_12m
    sensor.site_eui_estimate, sensor.dhw_gas_12m

REPO 2 — Residential-HVAC-Performance-Baseline-

  Monthly dataset:      homeassistant/reports/hvac_monthly.csv  (source of truth for HVAC monthly)
  Daily dataset:        homeassistant/reports/hvac_daily_YYYY.csv
  Utility snapshot:     homeassistant/reports/utility_monthly.csv  (billing + runtime, calendar-month)
  Prior month values:   last row of homeassistant/reports/hvac_monthly.csv

REPO 3 — Lifepo4-Battery-Banks

  Monthly metrics:      data/monthly_metrics.csv (or equivalent — confirm file path)
  Prior month values:   last row of monthly metrics file

REPO 4 — DIY-LiFePO4-UPS

  Operational log:      docs/operational-notes.md
  Prior month data:     HA notification history + UPS dashboard review
  No CSV — narrative log only
```

## REPO 1 — home-assistant-config

### Timing
```
~1st of month:   Enter Navien DHW reading (Therms) for PREVIOUS month
~10th of month:  Enter gas bill + electric bill for prior billing period
```

### DHW Entry Procedure
```
1. Read Navien meter (Therms)
2. Validate: check dhw_archive_[prior_month] via Developer Tools for comparison
3. Pre-convert for reference: CCF = Therms × 0.9643 (automation also converts — confirm match)
4. Enter: input_number.dhw_bill_thm (enter in Therms — automation converts to CCF)
5. Press: input_button.save_dhw
6. Confirm: dhw_archive_[archive_slot] updated with correct CCF value
7. Note: entry on Mar 1 → archive_slot = february
```

### Gas Bill Entry Procedure
```
1. Validate: read gas_archive_[prior_month] via Developer Tools for comparison
2. Apply V1 range check
3. Apply V2 direction check: CCF vs HDD ratio (high HDD → expect higher CCF)
4. Enter: input_number.gas_bill_ccf + input_number.gas_bill_amount
5. Set: input_datetime.gas_bill_date
6. Press: input_button.save_gas_bill
7. Confirm: gas_archive_[archive_slot] updated, sensor.hvac_heating_efficiency_12m recalculated
```

### Electric Bill Entry Procedure
```
1. Validate: read electric_archive_[prior_month]_kwh via Developer Tools for comparison
2. Apply V1 range check
3. Enter: input_number.electricity_bill_kwh + input_number.electricity_bill_amount
3. Set: input_datetime.electricity_bill_date
4. Press: input_button.save_electric_bill
5. Confirm: electric_archive_[archive_slot] updated, sensor.site_eui_estimate recalculated
```

### Key Derived Metrics to Check After Entry
```
sensor.hvac_heating_efficiency_12m    CCF/1kHDD — rolling 12-month
sensor.hvac_building_load_ua_12m      UA BTU/hr-°F — rolling 12-month
sensor.dhw_gas_12m                    rolling 12-month DHW total (CCF)
sensor.site_eui_estimate              kBTU/ft²-yr
```

### Baseline Reference Values
```
Heating efficiency:   90.3 CCF/1kHDD    (V-HVAC-2 threshold)
Building UA:          493 BTU/hr-°F      (V-HVAC-3 threshold)
```

### Commit Pattern
```
git commit -m "2026.MM: Enter [month] gas/electric/DHW bills"
```

## REPO 2 — Residential-HVAC-Performance-Baseline-

### Monthly Data Points
```
Month-end captures (from HA CSV reports):
  total_hdd65              input_number.hdd_cumulative_month_auto
  furnace_runtime_hours    sensor.hvac_furnace_runtime_month_2
  avg_runtime_per_hdd      sensor.hvac_runtime_per_hdd_month
  heating_efficiency       sensor.hvac_heating_efficiency_mtd (CCF/1kHDD)
  mean_outdoor_temp        sensor.outdoor_temp_mean_month
  gas_ccf                  input_number.gas_bill_ccf
  electric_kwh             input_number.electricity_bill_kwh
```

### Validation Checks
```
V-HVAC-1: runtime_per_hdd within ±2σ of 7-day rolling bounds — cross-ref HA alerts
V-HVAC-2: heating_efficiency within ±15% of 90.3 CCF/1kHDD baseline
V-HVAC-3: UA recalculation — flag if >±5% from 493 BTU/hr-°F
V-HVAC-4: HDD65 vs climate normal — note deviation from 5,270 annual normal
          High-HDD years cause natural UA/efficiency drift — document, don't alarm
```

### README Update Triggers
```
UA drifts >±10% from 493 → document with explanation
Efficiency crosses new annual record → update baseline section
HDD year ends >20% above/below normal → note in seasonal context
```

### Commit Pattern
```
git commit -m "2026.MM: Add [Month] HVAC performance data — [key metric] CCF/1kHDD"
```

## REPO 3 — Lifepo4-Battery-Banks

### Monthly Data Points
```
Capacity delivery (%)      actual vs rated capacity
System efficiency (%)      charge/discharge round-trip
Parasitic draw (mA)        ~13.3±4.5 mA baseline
Resting voltage (V)        post-charge relaxation
Temperature coefficient    mV/°C if seasonal shift detected
Pack voltage spread (mV)   inter-cell balance indicator
```

### Baseline Reference Values (flag if metric drifts)
```
Capacity delivery:     99.3% (validated over 94+ days)
System efficiency:     90.3%
Peukert k:             1.003
Parasitic draw:        13.3±4.5 mA
Relaxation time const: 1.8–2.1 days post-charge
Temp coefficient:      2.0–2.69 mV/°C
```

### Validation Checks
```
V-BATT-1: Capacity delivery — flag if <97% (unexplained drop warrants investigation)
V-BATT-2: Parasitic draw — flag if outside 8.8–17.8 mA (±1σ band)
V-BATT-3: Voltage spread — flag if inter-cell spread >50 mV at rest
V-BATT-4: Efficiency — flag if <88% (normal seasonal variation 88–92%)
NOTE: Eco Mode switch (Dec 23) created −9 mV baseline shift — instrumentation
      artifact, not battery change. Account for this in voltage comparisons.
```

### README Update Triggers
```
Study day count milestone (100, 150, 200 days) → update header
New validated metric → add to Key Validated Metrics section
Anomaly explained → add to Known Artifacts section
```

### Commit Pattern
```
git commit -m "2026.MM: Month [N] data — [key finding or metric]"
```

## REPO 4 — DIY-LiFePO4-UPS

### Monthly Data Points
```
Outage events count        from HA history or notification log
Longest outage duration    minutes
False positives (Phase 1b) Kasa flap count
Temperature range          min/max battery temp for the month
Voltage floor observed     lowest recorded filtered voltage
Test mode activations      dry-run tests performed
```

### Validation Checks
```
V-UPS-1: Voltage floor >12.2V during non-outage periods → PASS (no spurious shutdowns)
V-UPS-2: Phase 1b count — >3 Kasa flaps/month → FLAG (consider python-kasa local control)
V-UPS-3: Temperature — min >0°C (no charge inhibit events expected in summer)
          min <0°C → confirm charge inhibit fired correctly
V-UPS-4: If outage occurred — confirm Phase 4 recovery completed cleanly
          If recovery failed → document in operational-notes.md
```

### Operational Notes Update
```
Any real outage → add entry: date, duration, trigger path, recovery outcome
Any hardware anomaly → document in docs/operational-notes.md
Firmware updates (Shelly/Kasa) → note version + any behavior change observed
```

### Commit Pattern
```
git commit -m "2026.MM: Monthly operational log — [summary]"
```

## OUTPUT FORMAT (use for every monthly update session)

```
target_month: YYYY-MM
archive_slot: [month name]
Repo(s) updated: [list]

DATA ENTERED
  [field]: [value] [unit]
  [field]: [value] [unit]

VALIDATION
  V1 range check:    PASS | FLAG — [detail]
  V2 direction check: PASS | FLAG — [detail]
  V3 prior data:     PRESENT | MISSING — [detail]

METRICS (before → after)
  [metric]: [prior] → [new] ([% change])
  [metric]: [prior] → [new] ([% change])

FLAGS (if any)
  [description of anomaly or deviation]

COMMIT MESSAGE (ready to use)
  [repo]: git commit -m "YYYY.MM: [description]"

README UPDATE NEEDED: YES/NO — [reason if YES]
```

## POST-PROCESS ANALYSIS (optional — non-blocking — runs after commit confirmed)

After data is committed, provide this block if anything notable is present:

```
POST-PROCESS ANALYSIS — [target_month]

TREND (last 3 months):
  [metric]: [M-2] → [M-1] → [M] — improving | stable | degrading

VS BASELINE:
  [metric]: [actual] vs [baseline] — [% deviation] — expected | flag

ANOMALIES:
  [observation + causal hypothesis grounded in entered data]

OPTIMIZATION:
  [one specific actionable observation — setback depth, billing timing, etc.]
```

Rules:
  Non-blocking — never delays or conditions commit
  Grounded only in data just entered + live §ENTITIES sensor values
  Do not recommend config/automation changes here — flag for separate session
  Omit sections with nothing notable — empty output is valid

## CROSS-REPO SEQUENCING

When multiple repos update in the same month, follow this order:

```
1. home-assistant-config    enter bills + DHW first — source of truth for gas/electric
2. Residential-HVAC-*       pull from HA CSV reports — depends on HA data being current
3. Lifepo4-Battery-Banks    independent — can update in parallel with HVAC
4. DIY-LiFePO4-UPS          operational log — update last, may reference HVAC month context
```

## CHANGELOG FORMAT (consistent across all repos)

```markdown
## [YYYY.MM] — YYYY-MM-DD

### Data
- Added [Month YYYY] [data type]: [value] [unit]

### Metrics
- [Metric name]: [prior] → [new] ([% change])

### Notes
- [Any anomaly, deviation explanation, or milestone]
```

## COMMIT RULES

```
CalVer format: YYYY.MM in message
Feature branch for structural changes; main for monthly data updates
```
