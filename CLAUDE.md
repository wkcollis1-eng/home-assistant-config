# Home Assistant Configuration Notes

## Overview
Energy performance tracking and HVAC monitoring system for a 2-zone residential setup.

## Building Details
- **Square footage:** 2,440 ft²
- **Location:** Connecticut (latitude 41.28, longitude -72.81)
- **Heating:** Gas furnace, 60,556 BTU/hr
- **Zones:** 1F and 2F with separate Honeywell Lyric T6 Pro thermostats
- **Notable:** Cathedral ceiling on 2F (causes ~15% extra heat loss)
- **Filter:** MERV 11, 20x25x5" pleated (change at ~1000 runtime hours, typically annual)

## Key Entity IDs

### Thermostats
- `climate.tstat_2d884c_lyric_t6_pro_thermostat` - 1st Floor
- `climate.tstat_2d8878_lyric_t6_pro_thermostat` - 2nd Floor

### Dehumidifier (Basement)
- `switch.dehumidifier` - Main control
- `sensor.dehumidifier_current` - Current draw
- `sensor.shelly_temperature_humidity_temperature` - Basement temp
- `sensor.shelly_temperature_humidity_humidity` - Basement humidity
- `sensor.basement_dew_point` - Calculated dew point
- `input_number.dehumidifier_dewpoint_threshold` - Auto-on threshold (default 52°F)
- `binary_sensor.dehumidifier_should_run` - Conditions met indicator

### Weather
- `sensor.outdoor_temp_live` - Open-Meteo API (10-min updates)
- `sensor.hvac_outdoor_temp_hartford_proxy` - Combined weather source (priority: Live API > Pirate Weather > NWS > Open-Meteo)
- `weather.local_weather_2` - NWS/NOAA
- `weather.home` - Open-Meteo integration
- `weather.pirateweather` - Pirate Weather integration (HACS)

### Pirate Weather Sensors
- `sensor.pirate_weather_temperature` - Current temperature
- `sensor.pirate_weather_feels_like` - Feels like (heat index/wind chill)
- `sensor.pirate_weather_humidity` - Current humidity
- `sensor.pirate_weather_pressure` - Barometric pressure (inHg)
- `sensor.pirate_weather_wind_speed` - Wind speed (mph)
- `sensor.pirate_weather_wind_bearing` - Wind bearing (degrees)
- `sensor.pirate_weather_wind_direction` - Wind direction (compass)
- `sensor.pirate_weather_visibility` - Visibility (miles)
- `sensor.pirate_weather_cloud_cover` - Cloud coverage (%)
- `sensor.pirate_weather_dew_point` - Dew point temperature
- `sensor.pirate_weather_uv_index` - UV index
- `sensor.pirate_weather_ozone` - Ozone (DU)
- `sensor.pirate_weather_condition` - Current condition
- `sensor.pirate_weather_today_high` - Today's forecast high
- `sensor.pirate_weather_today_low` - Today's forecast low
- `sensor.pirate_weather_today_precip_prob` - Today's precipitation probability
- `sensor.pirate_weather_today_condition` - Today's forecast condition
- `sensor.pirate_weather_tomorrow_high` - Tomorrow's forecast high
- `sensor.pirate_weather_tomorrow_low` - Tomorrow's forecast low
- `sensor.pirate_weather_tomorrow_precip_prob` - Tomorrow's precipitation probability
- `sensor.pirate_weather_tomorrow_condition` - Tomorrow's forecast condition
- `sensor.pirate_weather_hdd_forecast_today` - Forecasted HDD for today
- `sensor.pirate_weather_cdd_forecast_today` - Forecasted CDD for today
- `sensor.pirate_weather_hdd_forecast_tomorrow` - Forecasted HDD for tomorrow
- `sensor.pirate_weather_hdd_forecast_7day` - 7-day HDD forecast total
- `sensor.pirate_weather_data_age` - Minutes since last update

### HDD/CDD Tracking
- `sensor.hvac_hdd65_today` - Today's heating degree days
- `sensor.hvac_cdd65_today` - Today's cooling degree days
- `sensor.hdd_rolling_7_day_auto_2` - 7-day rolling HDD (note: `_2` suffix from entity registry)
- `input_number.hdd_day_1` through `hdd_day_7` - Daily HDD storage
- `input_number.hdd_cumulative_month_auto` - Month-to-date HDD
- `input_number.hdd_cumulative_year_auto` - Year-to-date HDD

### Climate Norms (Historical Comparison)
- `sensor.climate_norms_today` - Command-line sensor with all climate attributes
- `sensor.expected_hdd_today` - Expected HDD based on 18-year climate normals
- `sensor.expected_cdd_today` - Expected CDD based on 18-year climate normals
- `sensor.expected_temperature_today` - Expected mean temperature for today
- `sensor.hdd_deviation_today` - Actual HDD minus expected HDD
- `sensor.expected_runtime_today` - Expected HVAC runtime based on climate norms
- `sensor.efficiency_deviation_index` - % deviation from expected performance
- `sensor.climate_norms_status` - Data validation status (OK/Error)
- `binary_sensor.climate_cold_snap_today` - True when HDD > 90th percentile
- `binary_sensor.climate_adjusted_efficiency_alert` - Alert when >15% deviation on cold day

### Energy Metrics
- `sensor.site_eui_estimate` - Site Energy Use Intensity (kBTU/ft²-yr)
- `sensor.hvac_heating_efficiency_mtd` - CCF per 1000 HDD
- `sensor.hvac_building_load_ua_estimate` - Building envelope UA value

### Filter Tracking
- `input_number.hvac_filter_runtime_hours` - Cumulative runtime hours (started at 800)
- `sensor.hvac_filter_hours_remaining` - Hours until 1000hr threshold
- `input_datetime.hvac_filter_last_changed` - Last filter change date
- `input_button.reset_filter_runtime` - Reset after filter change
- `binary_sensor.hvac_filter_change_alert` - Alert when >= 1000 hours

### Efficiency Monitoring
- `sensor.hvac_runtime_per_hdd_7day` - 7-day rolling runtime per HDD (min/HDD)
- `sensor.hvac_total_runtime_per_hdd_today` - Today's runtime per HDD (min/HDD)
- `sensor.hvac_1f_runtime_per_hdd_today` - 1F today's runtime per HDD
- `sensor.hvac_2f_runtime_per_hdd_today` - 2F today's runtime per HDD
- `binary_sensor.hvac_runtime_per_hdd_high_alert` - Exceeds upper bound (+2σ)
- `binary_sensor.hvac_runtime_per_hdd_low_alert` - Below lower bound (-2σ)

### Furnace Cycle Tracking (Actual Cycles)
- `binary_sensor.hvac_furnace_running` - ON when either zone is calling for heat
- `sensor.hvac_furnace_cycles_today` - Actual furnace cycles (overlapping calls = 1 cycle)
- `sensor.hvac_furnace_runtime_today` - Actual furnace runtime (hours)
- `sensor.hvac_furnace_min_per_cycle` - Minutes per actual furnace cycle
- `sensor.hvac_chaining_index` - Zone calls / furnace cycles (1.0=no overlap, 2.0=full overlap)
- `sensor.hvac_zone_overlap_today` - Minutes both zones called simultaneously
- `sensor.hvac_zone_overlap_percent` - Overlap as % of furnace runtime

### Monthly Report Sensors
- `sensor.outdoor_temp_mean_month` - Monthly average outdoor temperature
- `sensor.expected_runtime_month` - Monthly expected runtime total (hours)
- `sensor.efficiency_deviation_month` - Monthly efficiency deviation (%)
- `sensor.runtime_per_hdd_month_calc` - Monthly runtime per HDD (min/HDD)

### Runtime/HDD Statistics (Auto-calculated Bounds)
- `sensor.hvac_runtime_per_hdd_7day_mean` - Rolling 7-day mean
- `sensor.hvac_runtime_per_hdd_7day_stddev` - Rolling 7-day standard deviation
- `sensor.hvac_runtime_per_hdd_upper_bound_1s` - Mean + 2σ boundary
- `sensor.hvac_runtime_per_hdd_lower_bound_1s` - Mean - 2σ boundary
- `sensor.hvac_runtime_per_hdd_data_count` - Number of valid samples (alerts suppressed if <4)
- `input_number.runtime_per_hdd_day_1` through `_7` - Daily storage for std dev calc

### Recovery Time Tracking
- `binary_sensor.hvac_1f_recovering` - 1F currently in setback recovery
- `binary_sensor.hvac_2f_recovering` - 2F currently in setback recovery
- `input_number.hvac_1f_last_recovery_minutes` - Last 1F recovery time
- `input_number.hvac_2f_last_recovery_minutes` - Last 2F recovery time
- `input_datetime.hvac_1f_recovery_start` - Recovery start timestamp
- `input_datetime.hvac_2f_recovery_start` - Recovery start timestamp

### Recovery Rate Tracking (Rolling 7-Recovery Average)
- `sensor.hvac_1f_recovery_rate_avg` - 1F rolling avg min/°F setback
- `sensor.hvac_2f_recovery_rate_avg` - 2F rolling avg min/°F setback
- `sensor.hvac_1f_recovery_rate_last` - 1F last recovery rate (min/°F)
- `sensor.hvac_2f_recovery_rate_last` - 2F last recovery rate (min/°F)
- `sensor.hvac_1f_recovery_rate_weather_adjusted` - 1F weather-adjusted rate
- `sensor.hvac_2f_recovery_rate_weather_adjusted` - 2F weather-adjusted rate
- `sensor.hvac_1f_recovery_rate_std_dev` - 1F rolling std dev
- `sensor.hvac_2f_recovery_rate_std_dev` - 2F rolling std dev
- `sensor.hvac_1f_recovery_rate_upper_bound` - 1F mean + 2σ boundary
- `sensor.hvac_2f_recovery_rate_upper_bound` - 2F mean + 2σ boundary
- `sensor.hvac_1f_recovery_rate_data_count` - 1F valid sample count
- `sensor.hvac_2f_recovery_rate_data_count` - 2F valid sample count
- `binary_sensor.hvac_1f_recovery_rate_alert` - 1F exceeds upper bound (+2σ)
- `binary_sensor.hvac_2f_recovery_rate_alert` - 2F exceeds upper bound (+2σ)
- `input_number.hvac_1f_recovery_rate_1` through `_7` - Rolling storage slots
- `input_number.hvac_2f_recovery_rate_1` through `_7` - Rolling storage slots

### Setback Efficiency Tracking
- `input_datetime.hvac_1f_setback_start` / `hvac_2f_setback_start` - Setback start timestamp
- `input_number.hvac_1f_setback_start_runtime` / `hvac_2f_*` - Runtime at setback start (min)
- `input_number.hvac_1f_setback_start_outdoor_temp` / `hvac_2f_*` - Outdoor temp at setback
- `input_number.hvac_1f_recovery_start_runtime` / `hvac_2f_*` - Runtime at recovery start (min)
- `input_number.hvac_1f_overnight_runtime` / `hvac_2f_*` - Overnight runtime (min)
- `input_number.hvac_1f_overnight_efficiency` / `hvac_2f_*` - Overnight min/HDD
- `input_number.hvac_1f_recovery_efficiency` / `hvac_2f_*` - Recovery min/HDD
- `sensor.hvac_1f_setback_net_benefit` / `hvac_2f_*` - Net benefit (positive = saving)

### Daily Cost Estimates
- `sensor.hvac_daily_gas_cost_estimate` - Today's estimated gas cost
- `sensor.hvac_daily_electric_cost_estimate` - Today's estimated blower electric cost
- `sensor.hvac_daily_total_cost_estimate` - Combined daily HVAC cost

## Baseline Values
- **Building UA:** 449 BTU/hr-°F (manual input_number)
- **Balance Point:** 59°F (manual input_number)
- **Heating Efficiency:** 82.6 CCF/1k HDD (manual input_number)
- **Runtime per HDD:** Auto-calculated (mean ± 2σ from 7-day rolling data)
- **1F Recovery Rate:** Auto-calculated (mean + 2σ from last 7 recoveries)
- **2F Recovery Rate:** Auto-calculated (mean + 2σ from last 7 recoveries)
- **Annual HDD:** 6,270
- **Annual Electricity:** 6,730 kWh
- **Annual Gas:** 787 CCF
- **Site EUI:** 41.7 kBTU/ft²-yr

### Statistical Bounds Approach (Runtime/HDD & Recovery Rates)
- Alerts trigger when current value exceeds ±2σ from rolling mean
- Minimum 4 data points required before alerts activate
- Self-calibrating: bounds adjust automatically as system performance changes
- Catches outliers (~5% false positive rate with 2σ)

## Bill Entry Workflow
1. Enter bill data in `input_number.electricity_bill_*` or `input_number.gas_bill_*`
2. Set bill date in `input_datetime.electricity_bill_date` or `input_datetime.gas_bill_date`
3. Press `input_button.save_electric_bill` or `input_button.save_gas_bill`
4. Automation archives to monthly storage and rotates previous/last year values

## Automations

### HDD Tracking
- `capture_daily_hdd` - Runs at 23:55, captures daily HDD/CDD
- `capture_daily_runtime_per_hdd` - Runs at 23:56, stores daily runtime/HDD for std dev
- `reset_monthly_hdd` - Resets month counters on 1st of month
- `reset_yearly_hdd` - Resets year counters on Jan 1

### Dehumidifier Control
- `dehumidifier_auto_on` - Turns on when temp > 60°F AND dew point > threshold, with 30-min cooldown
- `dehumidifier_auto_off` - Turns off when conditions clear OR after 4 hours max runtime

### Filter Tracking
- `accumulate_filter_runtime` - Adds daily runtime to filter hours at 23:58
- `reset_filter_runtime_button` - Resets hours and records change date
- `notify_filter_change_due` - Alert when filter reaches 1000 hours

### Recovery Time Tracking
- `hvac_1f_recovery_start` / `hvac_1f_recovery_end` - Tracks 1F setback recovery
- `hvac_2f_recovery_start` / `hvac_2f_recovery_end` - Tracks 2F setback recovery

### Efficiency Alerts
- `notify_runtime_per_hdd_high` - Runtime/HDD >5% above baseline
- `notify_runtime_per_hdd_low` - Runtime/HDD >5% below baseline
- `notify_efficiency_degradation` - Heating efficiency > 110% of baseline
- `notify_short_cycling_1f` / `notify_short_cycling_2f` - Cycles < 5 min average

### Bill Archiving
- `save_electric_bill_button` - Archives electric bill to monthly storage
- `save_gas_bill_button` - Archives gas bill to monthly storage

## Dashboards
- **Overview** (`/lovelace/home`) - Main dashboard with device controls
- **Energy Monitoring** (`/lovelace/energy-monitoring`) - Power consumption tracking
- **HVAC Performance** (`/lovelace/hvac-performance`) - Efficiency metrics, recovery rates, baselines
- **Weather** (`/lovelace/weather`) - Pirate Weather dashboard with:
  - Current conditions (temp, humidity, wind, pressure, dew point, UV, visibility, cloud cover)
  - Today/Tomorrow forecasts with HDD/CDD predictions
  - Temperature trend charts (48h)
  - HDD actual vs forecast comparison
  - Humidity & wind charts
- **Energy Performance** (`/lovelace-energy-performance/`) - Five views:
  - Operations: Real-time HVAC metrics
  - Diagnostics: Degree days, efficiency tracking
  - Engineering: Baselines, EUI, bill comparisons
  - Billing & Cost: Bill entry, rate tracking, filter status, daily costs
  - Climate Norms: Historical climate comparison, efficiency deviation index, HDD bands

## File Structure
- `configuration.yaml` - Main config with all sensors and input helpers
- `automations.yaml` - All automations
- `scripts.yaml` - Bill archive seeding script
- `scenes.yaml` - Light scenes
- `secrets.yaml` - Sensitive data
- `climate_daily_norms.csv` - 18-year climate normals by day-of-year (365 rows)
- `scripts/climate_norms_today.py` - Python script for daily climate lookup
- `dashboards/cards/` - **Card snippet library** (see Dashboard Card Library below)
- `reports/hvac_daily_YYYY.csv` - Daily HVAC data (annual rotation)
- `reports/hvac_monthly.csv` - Monthly HVAC summary data

## Dashboard Architecture

### Storage Mode (Active)
Dashboards are managed via HA's UI editor with configuration stored in `.storage/`:
- `.storage/lovelace` - Main dashboard (Home, Energy Monitoring, HVAC Performance, Weather)
- `.storage/lovelace.energy_performance` - Energy Performance dashboard (5 views)
- `.storage/lovelace.map` - Map dashboard

### Card-Level YAML Approach
The UI manages dashboard structure (views, sections, grids) while individual cards use YAML mode for:
- Copy-paste reusability
- Version-controlled snippets
- Easier troubleshooting
- Failure isolation (bad YAML breaks one card, not the whole dashboard)

### Workflow
1. **Clone dashboard first** (Settings → Dashboards → Copy) for safe testing
2. **Add cards via UI**, then switch to Manual/YAML mode for complex cards
3. **Save working cards** to `dashboards/cards/` library
4. **Reuse snippets** by pasting from library

## Dashboard Card Library

Located in `dashboards/cards/` with organized subfolders:

| Folder | Contents | Card Count |
|--------|----------|------------|
| `apexcharts/` | Time series charts, control charts | 10 |
| `mushroom/` | Template cards, entity cards | 18 |
| `climate/` | Thermostat control cards | 4 |
| `gauges/` | Built-in gauge cards | 6 |
| `conditional/` | Alert cards (show/hide based on state) | 4 |
| `weather/` | Weather display cards | 2 |
| `billing/` | Bill entry and cost tracking | 4 |

### Key Card Snippets

**ApexCharts (Complex Charts)**
- `temperature-trend-48h.yaml` - Multi-source outdoor temp comparison
- `runtime-per-hdd-control-chart.yaml` - Statistical process control (±2σ bounds)
- `recovery-rate-trend.yaml` - Setback recovery with baselines
- `temperature-heating-48h.yaml` - Indoor temps with heat call overlay

**Mushroom Template (Dynamic Display)**
- `outdoor-temp-dynamic.yaml` - Color changes by temperature range
- `avg-cycle-*-dynamic.yaml` - Short cycling risk colors
- `efficiency-deviation-dynamic.yaml` - Baseline comparison with alerts

**Conditional (Alert Cards)**
- `filter-alert.yaml` - Shows only when filter change due
- `cold-snap.yaml` - Shows when HDD > 90th percentile
- `climate-efficiency-alert.yaml` - Climate-adjusted efficiency warning

### Using Card Snippets
1. Open dashboard → Edit → Add Card → Manual
2. Open snippet file from `dashboards/cards/`
3. Copy YAML content
4. Paste into card editor
5. Adjust entity IDs if needed
6. Save

## CSV Reports
### Daily Report (`reports/hvac_daily_YYYY.csv`)
Captured at 23:57 daily. Annual rotation on Jan 1st.

| Field | Source |
|-------|--------|
| date | Current date |
| outdoor_high | input_number.outdoor_temp_daily_high (actual observed) |
| outdoor_low | input_number.outdoor_temp_daily_low (actual observed) |
| outdoor_mean | Calculated (high + low) / 2 |
| hdd65 | sensor.hvac_hdd65_today |
| furnace_runtime_min | sensor.hvac_furnace_runtime_today × 60 |
| furnace_cycles | sensor.hvac_furnace_cycles_today |
| avg_min_per_cycle | sensor.hvac_furnace_min_per_cycle |
| zone_calls_total | sensor.hvac_total_cycles_today |
| chaining_index | sensor.hvac_chaining_index |
| runtime_1f_min | sensor.hvac_1f_heat_runtime_today × 60 |
| runtime_2f_min | sensor.hvac_2f_heat_runtime_today × 60 |
| basement_dew_point | sensor.basement_dew_point |

### Monthly Report (`reports/hvac_monthly.csv`)
Captured at 23:58 on last day of each month.

| Field | Source |
|-------|--------|
| month | YYYY-MM format |
| days | input_number.outdoor_temp_days_month (actual days tracked) |
| mean_outdoor_temp | sensor.outdoor_temp_mean_month (accumulated daily averages) |
| total_hdd65 | input_number.hdd_cumulative_month_auto |
| furnace_runtime_hours | sensor.hvac_total_heat_runtime_month |
| avg_runtime_per_hdd | sensor.runtime_per_hdd_month_calc (monthly calculation) |
| heating_efficiency_ccf_per_1k_hdd | sensor.hvac_heating_efficiency_mtd |
| actual_runtime | sensor.hvac_total_heat_runtime_month |
| expected_runtime | sensor.expected_runtime_month (accumulated daily expected) |
| efficiency_deviation_pct | sensor.efficiency_deviation_month (monthly actual vs expected) |
| gas_usage_ccf | input_number.gas_bill_ccf |
| gas_cost | input_number.gas_bill_amount |
| electric_kwh | input_number.electricity_bill_kwh |

### Monthly Tracking Input Numbers
- `input_number.outdoor_temp_sum_month` - Sum of daily mean temps
- `input_number.outdoor_temp_days_month` - Count of days captured
- `input_number.expected_runtime_sum_month` - Sum of daily expected runtimes

### Monthly Tracking Sensors
- `sensor.outdoor_temp_mean_month` - Monthly average outdoor temp (sum/days)
- `sensor.expected_runtime_month` - Monthly expected runtime total
- `sensor.efficiency_deviation_month` - Monthly efficiency deviation %
- `sensor.runtime_per_hdd_month_calc` - Monthly runtime per HDD (min/HDD)

### Related Automations
- `capture_daily_monthly_tracking` - Runs at 23:56:30, accumulates daily values
- `csv_daily_report` - Runs at 23:57, appends daily data
- `csv_monthly_report` - Runs at 23:58 on last day of month
- `csv_yearly_rotation` - Runs Jan 1st 00:01, creates new annual file
- `reset_monthly_hdd` - Runs at 00:01 on day 1, resets all monthly accumulators

## Database Configuration
- **Type:** SQLite (home-assistant_v2.db)
- **Retention:** 14 days (states/events), forever (long-term statistics)
- **Commit interval:** 2 seconds (reduces lock contention)
- **Maintenance:** Weekly purge with repack (Sunday 3 AM via automation)
- **Excluded from recorder:** sensor.time, sensor.date, *_signal_level
- **High-frequency entities:** Shelly voltmeters (~12k updates/day) - consider reducing polling interval to 30-60 sec

### Database Health Checks
```jinja
{# Run in Developer Tools → Template #}
Unavailable: {{ states | selectattr('state', 'eq', 'unavailable') | list | count }}
Unknown: {{ states | selectattr('state', 'eq', 'unknown') | list | count }}
Total entities: {{ states | list | count }}
```

### Manual Maintenance (if needed)
```bash
# Via SSH/Terminal add-on
ha core stop
sqlite3 /config/home-assistant_v2.db "PRAGMA integrity_check;"
sqlite3 /config/home-assistant_v2.db "VACUUM;"
ha core start
```

## Architecture Decisions

### Rolling Window Storage (input_numbers)
The following use input_number arrays for rolling windows. This is intentional:

| Input Numbers | Purpose | Why Not Statistics Sensor |
|---------------|---------|---------------------------|
| `hdd_day_1` through `_7` | 7-day HDD sum | Need end-of-day captures, not continuous samples |
| `runtime_per_hdd_day_1` through `_7` | Std dev calculation | Need discrete daily values for control charts |
| `hvac_1f_recovery_rate_1` through `_7` | Recovery rate avg | Event-driven (per setback recovery), not time-based |
| `hvac_2f_recovery_rate_1` through `_7` | Recovery rate avg | Event-driven (per setback recovery), not time-based |

**Total: 28 input_numbers** - These cannot be replaced with statistics sensors without losing accuracy.

### Monthly Bill Archives (input_numbers)
The 48 monthly archive input_numbers (`electric_archive_*`, `gas_archive_*`) store manually-entered bill data for YoY comparisons. Cannot be replaced with `utility_meter` because:
- No real-time whole-home energy monitor
- Bills are manually entered, not metered
- Need historical data for YoY analysis

**Future optimization**: If adding Shelly Pro 3EM or similar, could migrate to `utility_meter` + HA Energy Dashboard.

## Known Issues

### EUI Calculation
- EUI calculation uses static bill input values (doesn't auto-update daily)

### Entity Registry Note
- `sensor.hdd_rolling_7_day_auto_2` is the correct entity ID (the `_2` suffix is from entity registry)
- Do NOT delete it - it contains the valid 7-day HDD rolling data

---

## Configuration Review - 2025-01-19

### Verified Working
- `configuration.yaml` - YAML syntax OK
- `automations.yaml` - YAML syntax OK
- All sensor entity IDs verified correct

### Runtime/HDD 7-Day Calculation
- Formula: `(hvac_total_heat_runtime_week × 60) / hdd_rolling_7_day_auto_2`
- Updates daily at 11:55 PM
- Stable values indicate consistent heating performance (not a bug)

### Statistical Bounds Implementation
Replaced manual baseline sliders with auto-calculated statistical bounds (±2σ):
- `sensor.hvac_runtime_per_hdd_upper_bound_1s` / `_lower_bound`
- `sensor.hvac_1f_recovery_rate_upper_bound` / `sensor.hvac_2f_recovery_rate_upper_bound`
- Alerts require minimum 4 data points before triggering

## Scripts
- `seed_2024_bill_archive` - Run once to populate 2024 historical data for YoY comparisons
- `seed_2025_electric_archive` - Populate 2025 electric bill data (all 12 months)
- `seed_2025_gas_archive` - Populate 2025 gas bill data (all 12 months)

---

## Climate Norms Feature - 2025-01-20

### Overview
Compares actual HVAC performance against 18-year climate normals for the location. Provides context for whether a day is colder/milder than typical and if the system is responding linearly.

### Data Source
- `climate_daily_norms.csv` - 365 rows with daily HDD/CDD statistics
- Fields: HDD65_mean, HDD65_p10, HDD65_p90, CDD65_mean, Tmean, Tmin, Tmax
- Based on 18 years of historical weather data

### Key Metrics
| Metric | Purpose |
|--------|---------|
| Expected HDD | Climate-normal HDD for today |
| HDD Deviation | Actual - Expected (positive = colder than normal) |
| Efficiency Deviation Index | % runtime difference from expected |
| Cold Snap Indicator | Flags days > 90th percentile HDD |

### Interpretation
- **HDD Deviation ≈ 0**: Normal day for this date
- **HDD Deviation > +5**: Colder than typical
- **HDD Deviation < -5**: Milder than typical
- **Efficiency Deviation ≈ 0%**: System performing as expected
- **Efficiency Deviation > +15%**: Working harder than climate-normal
- **Efficiency Deviation < -15%**: Outperforming baseline

### Alert Logic
Climate-adjusted efficiency alert triggers when:
1. Efficiency deviation > 15%
2. Expected HDD > 20 (meaningful heating day)
3. Actual HDD > Expected HDD (not just a mild day)

This catches real issues while ignoring noise on mild days.

### Files Added
- `/config/climate_daily_norms.csv` - Climate data
- `/config/scripts/climate_norms_today.py` - Daily lookup script
- Dashboard: Energy Performance → Climate Norms tab

### Sensor Configuration
- `sensor.climate_norms_today` - Command-line sensor with 1-hour scan_interval
- Hourly updates ensure day rollover is captured promptly after midnight

---

## Setback Optimization Bug Fix - 2026-01-24

### Issue
Setback net benefit sensors (`sensor.hvac_1f_setback_net_benefit`, `sensor.hvac_2f_setback_net_benefit`) were returning 0 for overnight setbacks.

### Root Cause
The `overnight_runtime` and `recovery_runtime` calculations used `sensor.hvac_*_heat_runtime_today` which resets at midnight. For setbacks spanning midnight (e.g., 10 PM → 6 AM), the calculation produced negative values that were clamped to 0, causing the entire net benefit calculation to return 0.

### Fix Applied
Updated `automations.yaml` to detect midnight boundary crossings and estimate pre-midnight runtime proportionally:
- `hvac_1f_recovery_start` - overnight_runtime calculation
- `hvac_2f_recovery_start` - overnight_runtime calculation
- `hvac_1f_recovery_end` - recovery_runtime calculation
- `hvac_2f_recovery_end` - recovery_runtime calculation

Logic:
1. Compare setback/recovery start date to current date
2. If same day: use simple subtraction (original behavior)
3. If different days: estimate pre-midnight runtime using post-midnight heating rate

### Additional Fix
Fixed entity ID typo in dashboard card snippets:
- `dashboards/cards/mushroom/setback-benefit-1f.yaml`
- `dashboards/cards/mushroom/setback-benefit-2f.yaml`
- Changed `hvac_runtime_per_hdd_7_day` → `hvac_runtime_per_hdd_7day`

### Recovery Rate Sensor Fix (same date)
The recovery rate averages were showing static values (e.g., 2.7, 3.0 min/°F) instead of updating after cold-night recoveries.

**Root Causes:**
1. `binary_sensor.hvac_*_recovering` depended on `hvac_action == 'heating'`, which flickered OFF during furnace cycles, triggering `recovery_end` prematurely (capturing single furnace cycles instead of full recovery)
2. 120-minute cap discarded valid cold-night recoveries that exceeded 2 hours

**Fixes Applied:**
1. Changed recovering sensors to use temperature gap with hysteresis:
   - Starts: gap > 2°F (significant setback detected)
   - Ends: gap ≤ 0.5°F (near setpoint)
   - No longer depends on furnace cycling state
2. Increased recovery time cap from 120 to 180 minutes

### Timezone Mismatch Fix (same date)
Log errors: `TypeError: can't subtract offset-naive and offset-aware datetimes`

**Root Cause:** `as_datetime` filter returns naive datetime, but `now()` returns timezone-aware datetime. Subtraction fails.

**Fix:** Added `| as_local` after `| as_datetime` in all affected locations:
- `configuration.yaml`: `binary_sensor.hdd_capture_stale`, `binary_sensor.runtime_per_hdd_capture_stale`
- `automations.yaml`: `reset_monthly_hdd`, `reset_yearly_hdd`, `hvac_1f_recovery_start` (overnight_hours), `hvac_1f_recovery_end` (recovery_minutes), `hvac_2f_recovery_start`, `hvac_2f_recovery_end`

### Additional Fixes (same date)

**Recovery time cap raised to 300 minutes:**
- Changed from 180 to 300 minutes (5 hours) to capture extreme cold days
- Previously, very cold mornings would silently discard data when recovery exceeded 3 hours
- 300-minute cap still filters stuck sensors while capturing real-world extremes

**Notification entity ID typos fixed:**
- `sensor.hvac_runtime_per_hdd_7_day` → `sensor.hvac_runtime_per_hdd_7day`
- `sensor.hvac_runtime_per_hdd_upper_bound_1s` → `sensor.hvac_runtime_per_hdd_upper_bound`
- `sensor.hvac_runtime_per_hdd_lower_bound_1s` → `sensor.hvac_runtime_per_hdd_lower_bound`

### Daily Outdoor Temp Tracking (same date)
Added actual observed daily high/low tracking instead of using Pirate Weather forecast temps (which were unreliable at 23:57 report time).

**New entities:**
- `input_number.outdoor_temp_daily_high` - Updated every 10 min if current temp exceeds stored high
- `input_number.outdoor_temp_daily_low` - Updated every 10 min if current temp is below stored low

**Automations:**
- `update_outdoor_temp_daily_high_low` - Runs every 10 minutes, updates high/low based on `sensor.hvac_outdoor_temp_hartford_proxy`
- `reset_outdoor_temp_daily_high_low` - Runs at 00:00:30, resets both to current temp for new day

**CSV Report:** Now uses actual observed temps instead of forecast temps.

### Known Limitation: Overnight Efficiency = 0

If `sensor.hvac_*f_setback_net_benefit` shows 0, check:
1. **Setback automation didn't fire** - `hvac_1f_setback_start` triggers on thermostat `temperature` attribute dropping ≥2°F. Some thermostats with built-in schedules may not report setpoint changes in a way that triggers this.
2. **Check input_datetime values** - In Developer Tools → States, verify `input_datetime.hvac_1f_setback_start` has a recent timestamp from last night's setback.
3. **Workaround** - Can manually set `input_datetime.hvac_1f_setback_start` before recovery to test the calculation flow.
