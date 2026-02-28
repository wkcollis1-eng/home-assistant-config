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
- `counter.dehumidifier_cycles_today` - Accurate daily cycle count (off→on transitions)
- `input_number.dehumidifier_cycle_start_dp` - Dew point at cycle start (°F)
- `input_number.dehumidifier_last_pull_down_rate` - Last cycle pull-down rate (°F/h)
- `input_number.dehumidifier_last_cycle_minutes` - Last cycle duration (min)
- `input_number.dehumidifier_last_hold_hours` - Hours between last two cycles (h)
- `input_select.dehumidifier_last_stop_reason` - Why last cycle ended (conditions_cleared/max_runtime)
- `input_datetime.dehumidifier_cycle_start_time` - Current cycle start timestamp
- `input_datetime.dehumidifier_last_cycle_end_time` - Last cycle end timestamp
- `sensor.dehumidifier_runtime_today` - Hours ON today (history_stats)
- `sensor.dehumidifier_runtime_week` - Hours ON rolling 7 days (history_stats)
- `sensor.dehumidifier_duty_cycle_24h` - Rolling 24h avg duty cycle (%)
- `sensor.dehumidifier_avg_cycle_minutes` - Average minutes per cycle today
- `sensor.dehumidifier_dew_point_margin` - Threshold minus current dew point (°F, positive = headroom)
- `sensor.dehumidifier_pull_down_rate` - Last pull-down rate display sensor (°F/h)
- `sensor.dehumidifier_hold_time` - Last hold time display sensor (h, only valid for conditions_cleared stops)

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
- `sensor.site_eui_estimate` - Site EUI from rolling 12-month archive bills (kBTU/ft²-yr)
- `sensor.hvac_heating_efficiency_12m` - CCF per 1000 HDD (rolling 12-month, primary, uses 76.1% heating ratio)
- `sensor.hvac_building_load_ua_12m` - Building envelope UA value (rolling 12-month, primary, uses 76.1% heating ratio)
- `sensor.hvac_heating_efficiency_mtd` - CCF per 1000 HDD (MTD, for monthly CSV only)
- `sensor.hvac_building_load_ua_estimate` - Building envelope UA (MTD, for monthly CSV only)
- `sensor.gas_heating_usage_month` - Heating portion of monthly gas (76.1% of total)
- `sensor.gas_dhw_usage_month` - DHW portion of monthly gas (23.9% of total)

### Filter Tracking
- `input_number.hvac_filter_runtime_hours` - Cumulative runtime hours (started at 800)
- `sensor.hvac_filter_hours_remaining` - Hours until 1000hr threshold
- `input_datetime.hvac_filter_last_changed` - Last filter change date
- `input_button.reset_filter_runtime` - Reset after filter change
- `binary_sensor.hvac_filter_change_alert` - Alert when >= 1000 hours

### Efficiency Monitoring
- `sensor.hvac_runtime_per_hdd_7_day` - 7-day rolling runtime per HDD (min/HDD) (note: `_2` suffix exists as fallback)
- `sensor.hvac_total_runtime_per_hdd_today` - Today's runtime per HDD (min/HDD)
- `sensor.hvac_1f_runtime_per_hdd_today` - 1F today's runtime per HDD
- `sensor.hvac_2f_runtime_per_hdd_today` - 2F today's runtime per HDD
- `binary_sensor.hvac_runtime_per_hdd_high_alert` - Exceeds upper bound (+2σ)
- `binary_sensor.hvac_runtime_per_hdd_low_alert` - Below lower bound (-2σ)

### Furnace Cycle Tracking (Actual Cycles)
- `binary_sensor.hvac_furnace_running` - ON when either zone is calling for heat
- `binary_sensor.hvac_furnace_short_cycling_alert` - Avg cycle < 5 min (suppressed during recovery)
- `sensor.hvac_furnace_cycles_today` - Actual furnace cycles (overlapping calls = 1 cycle)
- `sensor.hvac_furnace_cycles_week` - Rolling 7-day furnace cycle count
- `sensor.hvac_furnace_cycles_month_2` - Month-to-date furnace cycle count
- `sensor.hvac_furnace_runtime_today` - Actual furnace runtime (hours)
- `sensor.hvac_furnace_runtime_week` - Rolling 7-day furnace runtime (hours)
- `sensor.hvac_furnace_runtime_month_2` - Month-to-date furnace runtime (hours)
- `sensor.hvac_furnace_min_per_cycle` - Minutes per actual furnace cycle (today)
- `sensor.hvac_furnace_min_per_cycle_week` - Minutes per actual furnace cycle (7-day)
- `sensor.hvac_furnace_min_per_cycle_month` - Minutes per actual furnace cycle (MTD)
- `sensor.hvac_furnace_cycle_mean_7d` - Rolling 7-day mean
- `sensor.hvac_furnace_cycle_stddev_7d` - Rolling 7-day standard deviation
- `sensor.hvac_furnace_cycle_upper_bound` - Mean + 2σ boundary
- `sensor.hvac_furnace_cycle_lower_bound` - Mean - 2σ boundary
- `sensor.hvac_furnace_cycle_data_count` - Number of valid samples
- `input_number.furnace_min_per_cycle_day_1` through `_7` - Daily storage for std dev calc
- `sensor.hvac_furnace_cycles_per_day_week` - Average cycles per day (7-day)
- `sensor.hvac_furnace_cycles_per_day_month` - Average cycles per day (MTD)
- `sensor.hvac_chaining_index` - Zone calls / furnace cycles today (1.0=no overlap, 2.0=full overlap)
- `sensor.hvac_chaining_index_week` - Zone calls / furnace cycles (7-day)
- `sensor.hvac_chaining_index_month` - Zone calls / furnace cycles (MTD)
- `sensor.hvac_zone_overlap_today` - Minutes both zones called simultaneously (today)
- `sensor.hvac_zone_overlap_week` - Minutes both zones called simultaneously (7-day)
- `sensor.hvac_zone_overlap_month` - Minutes both zones called simultaneously (MTD)
- `sensor.hvac_zone_overlap_percent` - Overlap as % of furnace runtime (today)
- `sensor.hvac_total_cycles_week` - Total zone calls (1F + 2F) rolling 7-day
- `sensor.hvac_total_cycles_month` - Total zone calls (1F + 2F) month-to-date

### Monthly Report Sensors
- `sensor.outdoor_temp_mean_month` - Monthly average outdoor temperature
- `sensor.expected_runtime_month` - Monthly expected runtime total (hours)
- `sensor.efficiency_deviation_month` - Monthly efficiency deviation (%)
- `sensor.hvac_runtime_per_hdd_month` - Monthly runtime per HDD (min/HDD)

### Runtime/HDD Statistics (Auto-calculated Bounds)
- `sensor.hvac_runtime_per_hdd_7_day_mean` - Rolling 7-day mean (note: `_2` suffix exists as fallback)
- `sensor.hvac_runtime_per_hdd_7_day_std_dev` - Rolling 7-day standard deviation (note: `_2` suffix exists as fallback)
- `sensor.hvac_runtime_per_hdd_upper_bound` - Mean + 2σ boundary
- `sensor.hvac_runtime_per_hdd_lower_bound` - Mean - 2σ boundary
- `sensor.hvac_runtime_per_hdd_data_count` - Number of valid samples (alerts suppressed if <4)
- `input_number.runtime_per_hdd_day_1` through `_7` - Daily storage for std dev calc

### Setback Recovery Tracking (State Machine)
Uses explicit `input_boolean` latches for state management. Data logged to per-zone CSV files.

**State Machine:** IDLE → SETBACK_ACTIVE → RECOVERING → IDLE

- `input_boolean.hvac_1f_setback_active` / `hvac_2f_setback_active` - Setback cycle latch
- `input_boolean.hvac_1f_recovering` / `hvac_2f_recovering` - Recovery state latch
- `input_datetime.hvac_1f_setback_start` / `hvac_2f_setback_start` - Setback start timestamp
- `input_datetime.hvac_1f_recovery_start` / `hvac_2f_recovery_start` - Recovery start timestamp
- `input_number.hvac_1f_hold_setpoint` / `hvac_2f_hold_setpoint` - Comfort setpoint before setback
- `input_number.hvac_1f_setback_setpoint` / `hvac_2f_setback_setpoint` - Setback setpoint
- `input_number.hvac_1f_recovery_start_temp` / `hvac_2f_recovery_start_temp` - Temp when recovery started
- `input_number.hvac_1f_last_recovery_minutes` / `hvac_2f_last_recovery_minutes` - Last recovery time
- `sensor.recommended_setback_depth` - Recommended setback depth based on forecast low

### Daily Cost Estimates
- `sensor.hvac_daily_gas_cost_estimate` - Today's estimated gas cost
- `sensor.hvac_daily_electric_cost_estimate` - Today's estimated blower electric cost
- `sensor.hvac_daily_total_cost_estimate` - Combined daily HVAC cost

## Baseline Values
- **Building UA:** 493 BTU/hr-°F (manual input_number; derived using 103,700 BTU/CCF × 0.95 AFUE + 3.6 MMBTU fireplace ÷ HDD59-equivalent)
- **Balance Point:** 59°F (manual input_number)
- **HDD Balance-Point Ratio:** 0.844 (HDD59/HDD65 = 5,294/6,270; converts HDD65 archives to HDD59 equivalent for UA calculation)
- **Fireplace Annual Heat:** 3.6 MMBTU (52 CCF × 103,700 BTU/CCF × 0.675 avg efficiency; added to UA numerator separately)
- **Heating Efficiency:** 90.3 CCF/1k HDD (Navien-corrected 2025 baseline; replaces billing-aligned 89.1 per operational data improvement)
- **AFUE:** 0.95 (tested per manufacturer submittal S9X1C100U-SUB-1D-EN; series marketed as "up to 96%")
- **BTU/CCF:** 103,700 (precise natural gas energy content; METHODOLOGY.md historical calcs used simplified 100,000)
- **Runtime per HDD:** Auto-calculated (mean ± 2σ from 7-day rolling data)
- **Annual HDD:** 6,270 (2025 actual HDD65); climate normal ~5,270 (18-year avg, used in weather severity sensors)
- **Annual Electricity:** 6,730 kWh
- **Annual Gas:** 787 CCF total (599 CCF heating + 188 CCF DHW)
- **DHW Ratio:** 23.9% of total gas (188/787 CCF) - used to isolate heating gas from total bills
- **Heating Ratio:** 76.1% of total gas (599/787 CCF)
- **Site EUI:** 41.7 kBTU/ft²-yr

### Statistical Bounds Approach (Runtime/HDD)
- Alerts trigger when current value exceeds ±2σ from rolling mean
- Minimum 4 data points required before alerts activate
- Self-calibrating: bounds adjust automatically as system performance changes
- Catches outliers (~5% false positive rate with 2σ)
- **Primary operational alert** for efficiency monitoring (Feb 2026)

### UA and CCF/1kHDD Metrics (Dashboard Only)
- `sensor.hvac_building_load_ua_12m` and `sensor.hvac_heating_efficiency_12m` are **annual reconciliation metrics**
- Fixed-threshold alerts disabled because they produce false positives in extreme weather years
- In years with HDD significantly above normal, these metrics naturally drift due to:
  - DHW ratio assumption error (23.9% assumes normal heating load)
  - Infiltration/stack effect scaling nonlinearly with extreme ΔT
- Runtime/HDD ±2σ catches the same operational issues earlier with weather-normalized, self-calibrating bounds

## Bill Entry Workflow
1. Enter bill data in `input_number.electricity_bill_*` or `input_number.gas_bill_*`
2. Set bill date in `input_datetime.electricity_bill_date` or `input_datetime.gas_bill_date`
3. Press `input_button.save_electric_bill` or `input_button.save_gas_bill`
4. Automation archives to monthly storage and rotates previous/last year values

## Automations

### HDD Tracking
- `capture_daily_hdd` - Runs at 23:55, captures daily HDD/CDD
- `capture_daily_runtime_per_hdd` - Runs at 23:56, stores daily runtime/HDD for std dev
- `capture_daily_furnace_min_per_cycle` - Runs at 23:56:15, stores daily min/cycle for std dev
- `reset_monthly_hdd` - Resets month counters on 1st of month
- `reset_yearly_hdd` - Resets year counters on Jan 1

### Dehumidifier Control
- `dehumidifier_auto_on` - Turns on when temp > 60°F AND dew point > threshold, with 30-min cooldown
- `dehumidifier_auto_off` - Turns off when conditions clear OR after 4 hours max runtime; stores stop reason

### Dehumidifier Performance Tracking
- `dehumidifier_cycle_start_capture` - Captures dew point, timestamp, hold time on off→on transition
- `dehumidifier_cycle_end_capture` - Calculates pull-down rate and cycle duration on on→off transition (10-min short cycle guard)
- `dehumidifier_cycle_counter_reset` - Resets daily cycle counter at midnight

### Filter Tracking
- `accumulate_filter_runtime` - Adds daily runtime to filter hours at 23:58
- `reset_filter_runtime_button` - Resets hours and records change date
- `notify_filter_change_due` - Alert when filter reaches 1000 hours

### Setback Recovery Tracking
- `hvac_1f_setback_start` / `hvac_2f_setback_start` - Latches setback, stores hold/setback setpoints (6 PM+, 5s debounce)
- `hvac_1f_setback_lowered` / `hvac_2f_setback_lowered` - Updates stored setback if further lowered
- `hvac_1f_recovery_start` / `hvac_2f_recovery_start` - Latches recovering, stores start temp/time
- `hvac_1f_recovery_end` / `hvac_2f_recovery_end` - Logs to CSV, clears all latches (10-min stability wait)
- `hvac_1f_setback_stuck_clear` / `hvac_2f_setback_stuck_clear` - 14h safety timeout
- `hvac_1f_recovery_stuck_clear` / `hvac_2f_recovery_stuck_clear` - 4h safety timeout
- `hvac_setback_midnight_audit` - Clears any stuck latches at 1 AM

### Efficiency Alerts
- `notify_runtime_per_hdd_high` - Runtime/HDD exceeds mean + 2σ (primary operational alert)
- `notify_runtime_per_hdd_low` - Runtime/HDD below mean - 2σ (primary operational alert)
- `notify_efficiency_degradation` - **DISABLED** Feb 2026 (fixed threshold replaced by ±2σ approach)
- `notify_short_cycling_furnace` - Furnace avg cycle < 5 min (suppressed during recovery)

### Bill Archiving
- `save_electric_bill_button` - Archives electric bill to monthly storage
- `save_gas_bill_button` - Archives gas bill to monthly storage

## Dashboards
- **Overview** (`/lovelace/home`) - Main dashboard with device controls
- **Energy Monitoring** (`/lovelace/energy-monitoring`) - Power consumption tracking
- **HVAC Performance** (`/lovelace/hvac-performance`) - Efficiency metrics, baselines
- **Weather** (`/lovelace/weather`) - Pirate Weather dashboard with current conditions, forecasts, charts
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
- `scripts/setback_csv.py` - Python script for validated setback CSV logging
- `dashboards/cards/` - Card snippet library (see Dashboard Card Library below)
- `reports/hvac_daily_YYYY.csv` - Daily HVAC data (annual rotation)
- `reports/hvac_monthly.csv` - Monthly HVAC summary data
- `reports/hvac_setback_1f.csv` - 1F setback recovery log
- `reports/hvac_setback_2f.csv` - 2F setback recovery log

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
| `apexcharts/` | Time series charts, control charts | 12 |
| `mushroom/` | Template cards, entity cards | 40+ |
| `climate/` | Thermostat control cards | 4 |
| `gauges/` | Built-in gauge cards | 8 |
| `conditional/` | Alert cards (show/hide based on state) | 8 |
| `weather/` | Weather display cards | 2 |
| `billing/` | Bill entry and cost tracking | 4 |

### Key Card Snippets

**ApexCharts (Complex Charts)**
- `temperature-trend-48h.yaml` - Multi-source outdoor temp comparison
- `runtime-per-hdd-control-chart.yaml` - Statistical process control (±2σ bounds)
- `furnace-min-per-cycle-control-chart.yaml` - Furnace cycle length with ±2σ bounds
- `temperature-heating-48h.yaml` - Indoor temps with heat call overlay
- `basement-dehumidifier-48h.yaml` - Dew point, temp, threshold line, on/off overlay

**Mushroom Template (Dynamic Display)**
- `outdoor-temp-dynamic.yaml` - Color changes by temperature range
- `avg-cycle-*-dynamic.yaml` - Short cycling risk colors (per-zone)
- `furnace-min-per-cycle-7day.yaml` - Furnace avg cycle with risk colors
- `efficiency-deviation-dynamic.yaml` - Baseline comparison with alerts
- `furnace-runtime-week.yaml` / `furnace-runtime-month.yaml` - Runtime tracking
- `furnace-cycles-week.yaml` / `furnace-cycles-month.yaml` - Cycle counts
- `zone-overlap-week.yaml` / `zone-overlap-month.yaml` - Zone overlap time
- `chaining-index-week.yaml` / `chaining-index-month.yaml` - Chaining index
- `dehumidifier-runtime-today.yaml` - Daily dehumidifier runtime with color coding
- `dehumidifier-duty-cycle.yaml` - Rolling 24h duty cycle percentage
- `dehumidifier-pull-down-rate.yaml` - Last cycle dew point drop rate

**Conditional (Alert Cards)**
- `filter-alert.yaml` - Shows only when filter change due
- `cold-snap.yaml` - Shows when HDD > 90th percentile
- `climate-efficiency-alert.yaml` - Climate-adjusted efficiency warning

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
| mean_outdoor_temp | sensor.outdoor_temp_mean_month |
| total_hdd65 | input_number.hdd_cumulative_month_auto |
| furnace_runtime_hours | sensor.hvac_furnace_runtime_month_2 |
| avg_runtime_per_hdd | sensor.hvac_runtime_per_hdd_month |
| heating_efficiency_ccf_per_1k_hdd | sensor.hvac_heating_efficiency_mtd |
| actual_runtime | sensor.hvac_furnace_runtime_month_2 |
| expected_runtime | sensor.expected_runtime_month |
| efficiency_deviation_pct | sensor.efficiency_deviation_month |
| gas_usage_ccf | input_number.gas_bill_ccf |
| gas_cost | input_number.gas_bill_amount |
| electric_kwh | input_number.electricity_bill_kwh |

### Setback Recovery Log (`reports/hvac_setback_1f.csv`, `hvac_setback_2f.csv`)
Captured at recovery_end for each zone via `scripts/setback_csv.py`.

| Field | Description |
|-------|-------------|
| date | Recovery date |
| hold_setpoint | Comfort setpoint before setback (°F) |
| setback_setpoint | Setback temperature (°F) |
| setback_degrees | hold_setpoint - setback_setpoint (°F) |
| start_temp | Temperature when recovery started (°F) |
| degrees_to_recover | hold_setpoint - start_temp (°F) |
| recovery_minutes | Time to reach comfort temp (min) |
| min_per_degree | recovery_minutes / degrees_to_recover |
| outdoor_low | Overnight low temperature (°F) |

## Database Configuration
- **Type:** SQLite (home-assistant_v2.db)
- **Retention:** 14 days (states/events), forever (long-term statistics)
- **Commit interval:** 2 seconds (reduces lock contention)
- **Maintenance:** Weekly purge with repack (Sunday 3 AM via automation)
- **Excluded from recorder:** sensor.time, sensor.date, *_signal_level

## Architecture Decisions

### Rolling Window Storage (input_numbers)
The following use input_number arrays for rolling windows. This is intentional:

| Input Numbers | Purpose | Why Not Statistics Sensor |
|---------------|---------|---------------------------|
| `hdd_day_1` through `_7` | 7-day HDD sum | Need end-of-day captures, not continuous samples |
| `runtime_per_hdd_day_1` through `_7` | Std dev calculation | Need discrete daily values for control charts |

**Total: 14 input_numbers** - These cannot be replaced with statistics sensors without losing accuracy.

### Monthly Bill Archives (input_numbers)
The 48 monthly archive input_numbers (`electric_archive_*`, `gas_archive_*`) store manually-entered bill data for YoY comparisons. Cannot be replaced with `utility_meter` because:
- No real-time whole-home energy monitor
- Bills are manually entered, not metered
- Need historical data for YoY analysis

**Future optimization**: If adding Shelly Pro 3EM or similar, could migrate to `utility_meter` + HA Energy Dashboard.

### Monthly HDD Archives (input_numbers)
The 12 `hdd_archive_*` input_numbers store monthly HDD totals for rolling 12-month efficiency calculations:
- Archived automatically at 23:58 on the last day of each month
- Used by `sensor.hvac_heating_efficiency_12m` and `sensor.hvac_building_load_ua_12m`
- Eliminates midnight oscillation issues that affected MTD sensors
- Updates monthly (when archives change), not continuously

### Monthly Accumulators
Month-to-date sensors use accumulated `input_number` values plus today's live value to survive the 14-day recorder purge:
- `input_number.furnace_runtime_month_acc` + `sensor.hvac_furnace_runtime_today`
- `input_number.hdd_cumulative_month_auto` + `sensor.hvac_hdd65_today`
- Uses `captured_today` guard to prevent double-counting after nightly capture
- **Important:** ALL month sensors (HDD, CDD, runtime, cycles) reference `monthly_tracking_capture_last_ok` (set at 23:56:30) to ensure synchronized timestamps. HDD/CDD accumulators are updated in `capture_daily_monthly_tracking`, NOT `capture_daily_hdd`.
- `capture_daily_hdd` (23:55) handles ONLY the 7-day rolling window (`hdd_day_1` through `_7`) and its own staleness timestamp (`hdd_capture_last_ok`)

## Known Issues

### EUI Calculation
- EUI now computed from rolling 12-month archive inputs (electric_archive_*_kwh + gas_archive_*_ccf), updated whenever archives change

### Entity Registry Note
Several sensors have `_2` suffix from entity registry conflicts. The canonical (preferred) entity IDs are:
- `sensor.hdd_rolling_7_day_auto_2` - 7-day rolling HDD
- `sensor.hvac_runtime_per_hdd_7_day` - 7-day runtime per HDD (min/HDD) — `_2` suffix exists as fallback
- `sensor.hvac_runtime_per_hdd_7_day_mean` - Rolling 7-day mean — `_2` suffix exists as fallback
- `sensor.hvac_runtime_per_hdd_7_day_std_dev` - Rolling 7-day standard deviation — `_2` suffix exists as fallback
- `sensor.hvac_furnace_runtime_month_2` - Monthly furnace runtime
- `sensor.hvac_furnace_cycles_month_2` - Monthly furnace cycles

Do NOT delete `_2` entities - they are used as fallbacks in sensor templates.

## Known Limitations

### API-Based Outdoor Temperature Accuracy

Weather APIs (Open-Meteo, Pirate Weather, NWS) report **regional** temperatures, not local microclimate conditions. On cold clear nights, actual temperatures at your location can be 5-10°F colder than API reports due to:

1. **Radiative cooling** - Clear nights allow ground-level temps to drop well below regional averages
2. **Regional averaging** - APIs blend data from stations that may be miles away or at different elevations
3. **Update frequency** - APIs may miss rapid temperature changes between updates

**Impact on metrics:**
- `outdoor_low` in daily CSV may be higher than actual overnight minimum
- HDD calculations may undercount degree-days on very cold nights
- Overnight efficiency (min/HDD) may appear artificially high

**Workaround:** A local Zigbee/Z-Wave outdoor temperature sensor (Shelly H&T, Aqara, etc.) would provide actual readings. Until then, treat overnight temperature data as approximate on clear cold nights.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Companion Repository

For analysis methodology and baseline data, see:
[Residential-HVAC-Performance-Baseline-](https://github.com/wkcollis1-eng/Residential-HVAC-Performance-Baseline-)
