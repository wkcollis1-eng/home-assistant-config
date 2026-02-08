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
- `sensor.hvac_heating_efficiency_mtd` - CCF per 1000 HDD
- `sensor.hvac_building_load_ua_estimate` - Building envelope UA value

### Filter Tracking
- `input_number.hvac_filter_runtime_hours` - Cumulative runtime hours (started at 800)
- `sensor.hvac_filter_hours_remaining` - Hours until 1000hr threshold
- `input_datetime.hvac_filter_last_changed` - Last filter change date
- `input_button.reset_filter_runtime` - Reset after filter change
- `binary_sensor.hvac_filter_change_alert` - Alert when >= 1000 hours

### Efficiency Monitoring
- `sensor.hvac_runtime_per_hdd_7_day` - 7-day rolling runtime per HDD (min/HDD)
- `sensor.hvac_total_runtime_per_hdd_today` - Today's runtime per HDD (min/HDD)
- `sensor.hvac_1f_runtime_per_hdd_today` - 1F today's runtime per HDD
- `sensor.hvac_2f_runtime_per_hdd_today` - 2F today's runtime per HDD
- `binary_sensor.hvac_runtime_per_hdd_high_alert` - Exceeds upper bound (+2σ)
- `binary_sensor.hvac_runtime_per_hdd_low_alert` - Below lower bound (-2σ)

### Furnace Cycle Tracking (Actual Cycles)
- `binary_sensor.hvac_furnace_running` - ON when either zone is calling for heat
- `sensor.hvac_furnace_cycles_today` - Actual furnace cycles (overlapping calls = 1 cycle)
- `sensor.hvac_furnace_cycles_week` - Rolling 7-day furnace cycle count
- `sensor.hvac_furnace_cycles_month` - Month-to-date furnace cycle count
- `sensor.hvac_furnace_runtime_today` - Actual furnace runtime (hours)
- `sensor.hvac_furnace_runtime_week` - Rolling 7-day furnace runtime (hours)
- `sensor.hvac_furnace_runtime_month` - Month-to-date furnace runtime (hours)
- `sensor.hvac_furnace_min_per_cycle` - Minutes per actual furnace cycle (today)
- `sensor.hvac_furnace_min_per_cycle_week` - Minutes per actual furnace cycle (7-day)
- `sensor.hvac_furnace_min_per_cycle_month` - Minutes per actual furnace cycle (MTD)
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
- `sensor.hvac_runtime_per_hdd_7_day_mean` - Rolling 7-day mean
- `sensor.hvac_runtime_per_hdd_7_day_std_dev` - Rolling 7-day standard deviation
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

### Setback Optimization (Simplified)
- `input_boolean.hvac_1f_setback_active` / `hvac_2f_*` - Setback cycle latch (prevents re-firing)
- `input_datetime.hvac_1f_setback_start` / `hvac_2f_setback_start` - Setback start timestamp
- `input_number.hvac_1f_setback_start_runtime` / `hvac_2f_*` - MTD furnace runtime at setback start (h)
- `input_number.hvac_1f_hold_setpoint` / `hvac_2f_*` - Comfort setpoint before setback
- `input_number.hvac_1f_setback_setpoint` / `hvac_2f_*` - Setback setpoint
- `input_number.hvac_1f_last_total_runtime` / `hvac_2f_*` - Last total furnace runtime during setback (min)
- `input_number.hvac_1f_last_expected_hold` / `hvac_2f_*` - Last expected hold runtime (min)
- `sensor.recommended_setback_depth` - Recommended setback depth based on forecast low

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
- `dehumidifier_auto_off` - Turns off when conditions clear OR after 4 hours max runtime; stores stop reason

### Dehumidifier Performance Tracking
- `dehumidifier_cycle_start_capture` - Captures dew point, timestamp, hold time on off→on transition
- `dehumidifier_cycle_end_capture` - Calculates pull-down rate and cycle duration on on→off transition (10-min short cycle guard)
- `dehumidifier_cycle_counter_reset` - Resets daily cycle counter at midnight

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
| `apexcharts/` | Time series charts, control charts | 11 |
| `mushroom/` | Template cards, entity cards | 35 |
| `climate/` | Thermostat control cards | 4 |
| `gauges/` | Built-in gauge cards | 7 |
| `conditional/` | Alert cards (show/hide based on state) | 8 |
| `weather/` | Weather display cards | 2 |
| `billing/` | Bill entry and cost tracking | 4 |

### Key Card Snippets

**ApexCharts (Complex Charts)**
- `temperature-trend-48h.yaml` - Multi-source outdoor temp comparison
- `runtime-per-hdd-control-chart.yaml` - Statistical process control (±2σ bounds)
- `recovery-rate-trend.yaml` - Setback recovery with baselines
- `temperature-heating-48h.yaml` - Indoor temps with heat call overlay
- `basement-dehumidifier-48h.yaml` - Dew point, temp, threshold line, on/off overlay

**Mushroom Template (Dynamic Display)**
- `outdoor-temp-dynamic.yaml` - Color changes by temperature range
- `avg-cycle-*-dynamic.yaml` - Short cycling risk colors
- `efficiency-deviation-dynamic.yaml` - Baseline comparison with alerts
- `furnace-runtime-week.yaml` - 7-day furnace runtime
- `furnace-runtime-month.yaml` - Month-to-date furnace runtime
- `furnace-cycles-week.yaml` - 7-day furnace cycle count with avg/day
- `furnace-cycles-month.yaml` - Month-to-date furnace cycle count with avg/day
- `zone-overlap-week.yaml` - 7-day zone overlap time
- `zone-overlap-month.yaml` - Month-to-date zone overlap time
- `chaining-index-week.yaml` - 7-day chaining index with status
- `chaining-index-month.yaml` - Month-to-date chaining index with status
- `min-per-cycle-week.yaml` - 7-day avg minutes per furnace cycle
- `min-per-cycle-month.yaml` - Month-to-date avg minutes per furnace cycle
- `dehumidifier-runtime-today.yaml` - Daily dehumidifier runtime with color coding
- `dehumidifier-duty-cycle.yaml` - Rolling 24h duty cycle percentage
- `dehumidifier-pull-down-rate.yaml` - Last cycle dew point drop rate
- `dehumidifier-dew-point-margin.yaml` - Headroom below threshold
- `dehumidifier-cycles-today.yaml` - Daily cycle count from counter
- `dehumidifier-hold-time.yaml` - Hold time between cycles (conditions_cleared only)

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
| furnace_runtime_hours | sensor.hvac_furnace_runtime_month |
| avg_runtime_per_hdd | sensor.hvac_runtime_per_hdd_month (monthly calculation) |
| heating_efficiency_ccf_per_1k_hdd | sensor.hvac_heating_efficiency_mtd |
| actual_runtime | sensor.hvac_furnace_runtime_month |
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
- `sensor.hvac_runtime_per_hdd_month` - Monthly runtime per HDD (min/HDD)

### Setback Optimization Log (`reports/hvac_setback_log.csv`)
Captured at recovery_end for each zone. Used to empirically optimize setback temps by outdoor low.

| Field | Source |
|-------|--------|
| date | Current date |
| zone | 1F or 2F |
| overnight_low | input_number.outdoor_temp_daily_low (actual observed) |
| setback_depth | hold_setpoint - setback_setpoint (°F) |
| recovery_minutes | Time from recovery_start to recovery_end minus 10min stability wait (min) |
| setback_degrees | Gap at recovery start: hold_setpoint - current_temp (°F) |
| recovery_rate | recovery_minutes / setback_degrees (min/°F) |
| total_runtime | Actual furnace runtime from setback start to recovery end via MTD accumulator (min) |
| expected_hold | Expected runtime if comfort temp held all night: hdd_setback × baseline_min_per_hdd (min) |
| net_runtime | expected_hold - total_runtime (positive = saved, negative = cost) |

**Net Runtime Benefit Calculation:**
```
setback_hours = (recovery_end - setback_start) in hours
hdd_setback = max(65 - overnight_low, 0) × (setback_hours / 24)
expected_hold = hdd_setback × baseline_min_per_hdd
total_runtime = (current_MTD_hours - start_MTD_hours) × 60
net_runtime = expected_hold - total_runtime
```

**Interpretation:**
- `net_runtime > 0`: Setback saved furnace runtime (good)
- `net_runtime ≈ 0`: Marginal benefit
- `net_runtime < 0`: Recovery penalty exceeded overnight savings (setback too deep for conditions)

**Finding your breakpoint:** Plot overnight_low vs net_runtime. The temperature where net_runtime crosses zero is your optimal setback threshold.

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
- EUI now computed from rolling 12-month archive inputs (electric_archive_*_kwh + gas_archive_*_ccf), updated whenever archives change

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
- Formula: `(hvac_furnace_runtime_week × 60) / hdd_rolling_7_day_auto_2`
- Uses furnace runtime (actual on-time) not sum of zone calls
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

## Setback Optimization Simplified - 2026-01-27

### Previous Approach (Removed)
The original setback efficiency tracking used complex calculations with degree-hours, overnight efficiency (min/HDD), recovery efficiency (min/HDD), and net benefit sensors. This approach was:
- Difficult to validate (calculations were unintuitive)
- Over-engineered for the actual goal: finding optimal setback depth by outdoor temp

### New Approach: Net Runtime Benefit
Replaced with a single intuitive metric that directly answers "did setback save furnace time?"

**Key Metric - Net Runtime (minutes):**
```
net_runtime = expected_hold_runtime - actual_runtime
```
- Positive = setback saved time (good)
- Negative = recovery penalty exceeded savings (setback too deep)

**CSV Log** (`reports/hvac_setback_log.csv`):
| date | zone | overnight_low | setback_depth | recovery_minutes | setback_degrees | recovery_rate | total_runtime | expected_hold | net_runtime |

**Recommendation Sensor** (`sensor.recommended_setback_depth`):
Based on Pirate Weather forecast low temperature:
- Low > 30°F → 5°F setback (deeper saves gas)
- Low 15-30°F → 3°F setback (balanced)
- Low < 15°F → 1°F setback (avoid recovery penalty)

Thresholds adjustable as data is collected. Plot overnight_low vs net_runtime to find optimal breakpoints.

### Entities Removed
- `input_number.hvac_*f_setback_start_outdoor_temp`
- `input_number.hvac_*f_recovery_start_runtime`
- `input_number.hvac_*f_overnight_runtime`
- `input_number.hvac_*f_overnight_efficiency`
- `input_number.hvac_*f_recovery_efficiency`
- `input_number.hvac_*f_setback_degree_hours`
- `input_number.hvac_*f_setback_temp_sum`
- `input_number.hvac_*f_setback_sample_count`
- `sensor.hvac_*f_setback_net_benefit`
- `sensor.hvac_*f_setback_daily_savings`
- `sensor.hvac_total_setback_daily_savings`

### Automations Removed
- `hvac_1f_degree_hours_sample` / `hvac_2f_degree_hours_sample`
- `reset_hold_setpoint_afternoon`

### Entities Kept (for recovery rate tracking)
- `input_number.hvac_*f_hold_setpoint` - Comfort setpoint (used by recovering binary sensor)
- `input_number.hvac_*f_setback_start_runtime` - For total runtime calculation
- `input_datetime.hvac_*f_setback_start` - Setback timestamp
- `input_boolean.hvac_*f_setback_active` - Setback latch

### Entities Added
- `input_number.hvac_*f_setback_setpoint` - Stores setback temp for depth calculation
- `sensor.recommended_setback_depth` - Forecast-based recommendation

---

## Runtime per HDD Standardization - 2026-01-24

### Change
Standardized all runtime per HDD sensors to use **furnace runtime** instead of **sum of zone call times**.

### Rationale
Previously, runtime per HDD calculations used `hvac_total_heat_runtime_*` which sums 1F + 2F thermostat call times. When zones overlap (both calling simultaneously), runtime was double-counted, artificially inflating the metric and penalizing efficient operation.

Now uses `hvac_furnace_runtime_*` which tracks actual furnace on-time via `binary_sensor.hvac_furnace_running` (ON when either zone is calling).

**Example:** If 1F calls for 3 hours and 2F calls for 2 hours with 1 hour overlap:
- Old method: 3 + 2 = 5 hours (inflated)
- New method: 4 hours (actual furnace operation)

### Sensors Updated
| Sensor | Old Source | New Source |
|--------|------------|------------|
| `hvac_total_runtime_per_hdd_today` | `hvac_total_heat_runtime_today` | `hvac_furnace_runtime_today` |
| `hvac_runtime_per_hdd_7day` | `hvac_total_heat_runtime_week` | `hvac_furnace_runtime_week` |
| `hvac_runtime_per_hdd_month` | `hvac_total_heat_runtime_month` | `hvac_furnace_runtime_month` |
| `runtime_per_hdd_month_calc` | `hvac_total_heat_runtime_month` | `hvac_furnace_runtime_month` |
| `efficiency_deviation_index` | `hvac_total_heat_runtime_today` | `hvac_furnace_runtime_today` |
| `efficiency_deviation_month` | `hvac_total_heat_runtime_month` | `hvac_furnace_runtime_month` |
| `hvac_daily_gas_cost_estimate` | `hvac_total_heat_runtime_today` | `hvac_furnace_runtime_today` |
| `hvac_daily_electric_cost_estimate` | `hvac_total_heat_runtime_today` | `hvac_furnace_runtime_today` |
| `hvac_heating_efficiency_mtd` | `hvac_total_heat_runtime_month` | `hvac_furnace_runtime_month` |
| `hvac_building_load_ua_estimate` | `hvac_total_heat_runtime_month` | `hvac_furnace_runtime_month` |
| `appendmonthlycsv` (shell_command) | `hvac_total_heat_runtime_month` | `hvac_furnace_runtime_month` |

### New History Stats Sensors
- `sensor.hvac_furnace_runtime_week` - Rolling 7-day furnace runtime
- `sensor.hvac_furnace_runtime_month` - Month-to-date furnace runtime

### Zone-Specific Sensors (Unchanged)
- `hvac_1f_runtime_per_hdd_today` - Still uses 1F zone call time (intentional for zone analysis)
- `hvac_2f_runtime_per_hdd_today` - Still uses 2F zone call time (intentional for zone analysis)

### Impact
- Runtime/HDD values will be **lower** than before (no overlap double-counting)
- Historical data in `input_number.runtime_per_hdd_day_1..7` will gradually update over 7 days
- Statistical bounds (mean ± 2σ) will recalibrate automatically

---

## Recovery END Threshold Fix - 2026-01-25

### Issue
Recovery rate history was frozen/missing during cold weather. The rolling 7-recovery averages stopped updating because recovery events were never completing.

### Root Cause
The recovery END threshold (gap ≤ 0.5°F) was too strict for real-world thermostat behavior during cold weather. Temperature traces showed:
- Temps rise quickly at first during recovery
- Then asymptotically approach setpoint
- Hover at ~0.6–1.1°F below setpoint for extended periods
- Rarely cross the 0.5°F threshold on very cold days

This caused `binary_sensor.hvac_*_recovering` to never turn OFF, so `recovery_end` automations never fired, and no recovery data was recorded.

### Fix Applied
Increased recovery END thresholds to account for thermostat resolution and thermal stratification:

| Zone | Old Threshold | New Threshold | Rationale |
|------|---------------|---------------|-----------|
| 1F | ≤ 0.5°F | ≤ 1.0°F | Standard zone |
| 2F | ≤ 0.5°F | ≤ 1.25°F | Cathedral ceiling causes additional stratification |

### Files Modified
- `configuration.yaml`: `binary_sensor.hvac_1f_recovering`, `binary_sensor.hvac_2f_recovering`

### Impact
- Recovery events will now complete reliably on cold days
- Rolling recovery rate averages will update properly
- Setback net benefit calculations will have valid data
- No downside: the 0.5–1.0°F difference is within thermostat resolution

---

## Setback Latch Fix - 2026-01-25

### Issue
Setback tracking data was being overwritten mid-cycle when thermostat reported attribute changes.

### Root Cause
The `hvac_*f_setback_start` automations triggered on any ≥2°F setpoint drop, which could fire multiple times per setback cycle.

### Fix Applied
Added explicit `input_boolean` latch to enforce one setback-start capture per cycle.

**Entities:**
- `input_boolean.hvac_1f_setback_active` - Latch for 1F setback cycle
- `input_boolean.hvac_2f_setback_active` - Latch for 2F setback cycle

**State Machine:**
```
setback_start fires → setback_active = ON → (tracks setback)
                                          ↓
recovery_end fires  → setback_active = OFF → ready for next cycle
```

---

## Daily Outdoor Temp Tracking Fix - 2026-01-25

### Issue
Daily report showed `outdoor_low=-50` and `outdoor_mean=-17.6` for Jan 24 despite HDD being correct. The -50 value is the input_number minimum, indicating corrupt/uninitialized state.

### Root Cause
`input_number.outdoor_temp_daily_low` had no `initial` value. When Home Assistant restarts, input_numbers without stored state default to their `min` value (-50). Since no actual temperature is lower than -50°F, the update automation never corrected it.

### Fix Applied

**1. Added initial values to input_numbers** (`configuration.yaml`):
- `outdoor_temp_daily_high`: `initial: -50` (any real temp is higher)
- `outdoor_temp_daily_low`: `initial: 150` (any real temp is lower)

**2. Hardened update automation** (`automations.yaml`):
- Detects corrupt values (high ≤ -49 or low ≥ 149)
- Auto-corrects to current temp when corruption detected
- Logs warning when auto-correction occurs

**3. Hardened midnight reset automation** (`automations.yaml`):
- Validates sensor reading before reset (must be between -40°F and 120°F)
- If sensor unavailable at midnight: resets to initial values instead of hardcoded 35°F
- Update automation will auto-correct when sensor becomes available

### Resilience Layers
1. **Initial values**: Proper defaults on HA restart
2. **Corruption detection**: Auto-fix within 10 minutes of valid sensor data
3. **Sensor validation**: Rejects obviously bad readings
4. **Logging**: Warnings logged when auto-correction occurs

---

## Recovery Rate Measurement Fix - 2026-01-26

### Issue
Recovery rate metrics were measuring **control-loop gap decay** instead of **actual thermal recovery**. Both floors showed artificially long recovery times (often maxing at 180 minutes) even when thermostat temperature showed the space reached comfort in 20-40 minutes.

### Root Cause
The previous implementation had three problems:

1. **Recovery END used live setpoint**: `binary_sensor.hvac_*_recovering` checked `target - current` where `target` was the **live thermostat setpoint**. If the setpoint changed (schedule transition, user adjustment, API lag), the recovery metric tracked that new gap rather than the actual thermal recovery.

2. **No stability requirement**: Recovery ended immediately when temperature crossed threshold, making it sensitive to single-sample noise and furnace cycling.

3. **180-minute cap hid errors**: Long recovery durations were silently capped, hiding the magnitude of the measurement problem.

### Engineering-Grade Recovery Definition (NEW)
Recovery now ends when:
- **Temperature reaches within 0.5°F of hold_setpoint** (the stored comfort temperature from before setback)
- **AND** that condition has been true for **10 continuous minutes** (stability filter)

This measures actual thermal recovery, not control-system gap decay.

### Files Modified

**configuration.yaml** - Binary sensor logic:
```yaml
# OLD: Used live setpoint, ended immediately
{% set target = state_attr(..., 'temperature') %}
{{ gap > 1.0 }}

# NEW: Uses stored hold_setpoint, 0.5°F threshold
{% set hold_setpoint = states('input_number.hvac_*f_hold_setpoint') %}
{% set target = hold_setpoint if hold_setpoint > 50 else live_setpoint %}
{{ current < (target - 0.5) }}
```

**automations.yaml** - Recovery end trigger:
```yaml
# OLD: Immediate trigger
trigger:
  - platform: state
    entity_id: binary_sensor.hvac_*f_recovering
    to: "off"

# NEW: 10-minute stability requirement
trigger:
  - platform: state
    entity_id: binary_sensor.hvac_*f_recovering
    to: "off"
    for:
      minutes: 10
```

**automations.yaml** - Setback degrees calculation:
```yaml
# OLD: Used live setpoint
{% set target = state_attr(..., 'temperature') %}

# NEW: Uses hold_setpoint for consistent denominator
{% set hold = states('input_number.hvac_*f_hold_setpoint') %}
{% set target = hold if hold > 50 else live %}
```

**automations.yaml** - Recovery time cap:
```yaml
# OLD: 180-minute cap
value: "{{ [recovery_minutes | float, 180] | min }}"

# NEW: 300-minute cap (matches rate storage sanity check)
value: "{{ [recovery_minutes | float, 300] | min }}"
```

### Impact
| Before | After |
|--------|-------|
| Recovery = time until HA gap clears | Recovery = time until house reaches stable comfort temp |
| Could show 180+ min | Will show realistic 15-45 min |
| Sensitive to setpoint changes | Immune to setpoint/API quirks |
| Not comparable day-to-day | Comparable across conditions |

### How It Works Now
1. **Setback starts**: `hold_setpoint` stores the comfort temperature (e.g., 67°F)
2. **Setback period**: Temperature drops to setback level (e.g., 63°F)
3. **Recovery starts**: When gap > 1°F AND furnace is running (hybrid logic)
4. **Recovery ends**: When `current_temp >= hold_setpoint - 0.5°F` for 10 continuous minutes
5. **Recovery rate**: `recovery_minutes / (hold_setpoint - temp_at_recovery_start)`

The metric now answers: "How long did it take for the house to actually warm up?" rather than "How long did it take for HA's gap calculation to clear?"

---

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

## Configuration Audit & Robustness Improvements - 2026-01-28

### Critical Fixes Applied

| Issue | Location | Fix |
|-------|----------|-----|
| Recovery END thresholds | `configuration.yaml` ~line 1277, 1293 | 1F: 0.5°F → 1.0°F, 2F: 0.5°F → 1.25°F (cathedral ceiling) |
| Operator precedence | `configuration.yaml` ~line 2646 | `* 100 \| round(1)` → `* 100) \| round(1)` in efficiency deviation |
| Days-in-month calculation | `configuration.yaml` ~line 1846 | Fixed December edge case with safe algorithm |
| Shell command variables | `configuration.yaml` lines 20-22 | Split `appendsetbacklog` into zone-specific `_1f` and `_2f` commands |

### Shell Command Variable Fix (Critical)

Home Assistant's `shell_command` does **not** support runtime variables via `data:`. The original `appendsetbacklog` command received literal `{{ zone }}` text instead of actual values.

**Old (broken):**
```yaml
shell_command:
  appendsetbacklog: '... {{ zone }},{{ overnight_low }} ...'
# Called with: service: shell_command.appendsetbacklog data: { zone: "1F" }
# Result: CSV contained "{{ zone }}" literally
```

**New (working):**
```yaml
shell_command:
  appendsetbacklog_1f: '... {{ states("input_number.hvac_1f_last_overnight_low") }} ...'
  appendsetbacklog_2f: '... {{ states("input_number.hvac_2f_last_overnight_low") }} ...'
# Called with: service: shell_command.appendsetbacklog_1f (no data)
# Result: CSV contains actual values
```

### New Watchdog Automations

| Automation ID | Trigger | Action |
|--------------|---------|--------|
| `notify_hdd_capture_stale` | `binary_sensor.hdd_capture_stale` ON for 2h | Persistent notification |
| `notify_runtime_per_hdd_capture_stale` | `binary_sensor.runtime_per_hdd_capture_stale` ON for 2h | Persistent notification |
| `validate_input_numbers_startup` | HA start + 60s | Checks for corrupt cumulative values |
| `notify_climate_norms_failure` | `sensor.climate_norms_today` = "error" for 2h | Persistent notification |
| `notify_weather_sources_down` | Weather source = Open-Meteo for 6h | Persistent notification |
| `notify_thermostat_offline` | Either thermostat unavailable 15min | Persistent notification |
| `clear_stale_setback_latch_1f` | `input_boolean.hvac_1f_setback_active` ON 18h | Auto-clear latch |
| `clear_stale_setback_latch_2f` | `input_boolean.hvac_2f_setback_active` ON 18h | Auto-clear latch |
| `database_size_monitor` | Monday 5 AM | Log reminder |
| `backup_input_numbers_weekly` | Sunday 4 AM | Backup critical values to CSV |
| `rotate_setback_log_yearly` | Jan 1 00:05 | Archive previous year data |
| `notify_pirate_weather_stale` | Data age > 120 min for 30min | Persistent notification |

### New Dashboard Cards

| Card | Location | Purpose |
|------|----------|---------|
| `hdd-capture-stale.yaml` | `dashboards/cards/conditional/` | Shows when HDD capture stale |
| `runtime-capture-stale.yaml` | `dashboards/cards/conditional/` | Shows when runtime/HDD capture stale |
| `climate-norms-error.yaml` | `dashboards/cards/conditional/` | Shows when climate script errors |
| `weather-fallback.yaml` | `dashboards/cards/conditional/` | Shows when using fallback weather |
| `system-health-summary.yaml` | `dashboards/cards/mushroom/` | Combined health status (green/red) |

### Additional Robustness Improvements

| Change | Location | Description |
|--------|----------|-------------|
| REST timeout | `configuration.yaml` line 46 | Added `timeout: 30` to Open-Meteo REST sensor |
| Availability templates | `configuration.yaml` | Added to `hvac_outdoor_temp_hartford_proxy` and `expected_hdd_today` |
| Notification rate limiting | `automations.yaml` | Added 24h cooldown + 30min delay to efficiency alert |
| CDD validation cap | `automations.yaml` | Increased from 30 to 50 for extreme heat |
| Recovery rate clamp | `automations.yaml` | Added `[rate, 99] \| min` to prevent input_number overflow |
| Timing stagger | `automations.yaml` | `csv_monthly_report` 23:58→23:58:30, `csv_yearly_rotation` 00:01→00:03 |

### New Shell Commands

| Command | Purpose |
|---------|---------|
| `backup_input_numbers` | Weekly backup of critical accumulated values to CSV |
| `rotate_setback_log` | Yearly archive of setback log data |

### New CSV Report

**`reports/input_number_backup.csv`** - Weekly backup of accumulated values

| Field | Source |
|-------|--------|
| timestamp | Backup datetime |
| hdd_year | `input_number.hdd_cumulative_year_auto` |
| hdd_month | `input_number.hdd_cumulative_month_auto` |
| cdd_year | `input_number.cdd_cumulative_year_auto` |
| cdd_month | `input_number.cdd_cumulative_month_auto` |
| filter_hrs | `input_number.hvac_filter_runtime_hours` |
| temp_sum | `input_number.outdoor_temp_sum_month` |
| temp_days | `input_number.outdoor_temp_days_month` |
| expected_runtime | `input_number.expected_runtime_sum_month` |
| hdd_d1..d7 | `input_number.hdd_day_1` through `_7` |

### Validation Checks at Startup

The `validate_input_numbers_startup` automation checks for corrupt values:
- HDD cumulative year > 8000 or < 0
- HDD cumulative month > 2500 or < 0
- Filter runtime > 2000 or < 0
- Outdoor temp high/low at initial values (uninitialized)

### Updated Automation Timing (Midnight Sequence)

| Time | Automation | Purpose |
|------|------------|---------|
| 23:55:00 | `capture_daily_hdd` | Capture daily HDD/CDD |
| 23:56:00 | `capture_daily_runtime_per_hdd` | Store runtime/HDD for std dev |
| 23:56:30 | `capture_daily_monthly_tracking` | Accumulate monthly values |
| 23:57:00 | `csv_daily_report` | Append daily CSV |
| 23:58:00 | `accumulate_filter_runtime` | Add runtime to filter hours |
| 23:58:30 | `csv_monthly_report` | Append monthly CSV (last day only) |
| 00:00:30 | `reset_outdoor_temp_daily_high_low` | Reset daily temp trackers |
| 00:01:00 | `reset_monthly_hdd` | Reset monthly counters (1st only) |
| 00:02:00 | `reset_yearly_hdd` | Reset yearly counters (Jan 1 only) |
| 00:03:00 | `csv_yearly_rotation` | Create new annual CSV (Jan 1 only) |
| 00:05:00 | `rotate_setback_log_yearly` | Archive setback log (Jan 1 only) |

### Files Modified
- `configuration.yaml` - All sensor/shell command fixes
- `automations.yaml` - All automation additions/fixes
- `dashboards/cards/conditional/*.yaml` - New alert cards
- `dashboards/cards/mushroom/system-health-summary.yaml` - New health card
- `reports/input_number_backup.csv` - New backup file (header only)

---

## Setback Tracking Threshold Change - 2026-01-28

### Change
Lowered setback_start trigger threshold from `>= 2°F` to `>= 1°F` for both zones.

### Rationale
Previously, setback events were only tracked when the thermostat setpoint dropped by 2°F or more. This missed 1°F setbacks, preventing data collection for analysis of marginal setback benefits.

### Impact
- **Before:** Only 2°F+ setbacks logged to `hvac_setback_log.csv`
- **After:** 1°F+ setbacks logged, enabling analysis of smaller setback benefits

### Note on 0°F Setbacks
Days with no setback (0°F) are still not logged since there's no temperature drop to trigger the automation. To capture these, a scheduled daily automation would be needed.

### Files Modified
- `automations.yaml` - `hvac_1f_setback_start`, `hvac_2f_setback_start` conditions

---

## Review Files Cleanup - 2026-01-28

### Removed Files
The following temporary review/audit files were deleted after their recommendations were implemented and documented in claude.md:

- `ha_corrections.yaml` - Configuration fixes (applied in Configuration Audit section)
- `ha_missing_entities.yaml` - Missing entity analysis (resolved)
- `ha_monitor_agent_notes.md` - Agent session notes (superseded by claude.md)
- `ha_watchdog_automations.yaml` - Watchdog automations (merged into automations.yaml)
- `ha_config_review.md` - Configuration review (issues addressed)

---

## Recovery Rate Cap Fix - 2026-01-28

### Issue
Recovery rate input_numbers (`hvac_*f_recovery_rate_1` through `_7`) have `max: 60`, but the automation capped values at 99. Values between 60-99 would be silently clamped by Home Assistant, causing data integrity issues.

### Fix
Changed automation cap from 99 to 60 to match input_number max:
```yaml
# Before:
value: "{{ [recovery_rate | float | round(1), 99] | min }}"

# After:
value: "{{ [recovery_rate | float | round(1), 60] | min }}"
```

### Files Modified
- `automations.yaml` - Lines 898, 1077 (`hvac_1f_recovery_end`, `hvac_2f_recovery_end`)

---

## Setback Start Validation Fix - 2026-01-28

### Issue
Setback tracking captured incorrect values (both `hold_setpoint` and `setback_setpoint` = 67) when a spurious thermostat attribute change occurred. This caused the setback latch to activate with invalid data, blocking the real 9pm setback from being captured.

### Root Cause
The original condition only checked `(from_temp - to_temp) >= 1` but didn't validate that:
1. Both temperature values were actually valid/present
2. The values were actually different (edge case where both could be identical)

### Fix Applied
Added robust validation to both `hvac_1f_setback_start` and `hvac_2f_setback_start` automations:

```yaml
# Old condition:
{{ (trigger.from_state.attributes.temperature | float(0) -
    trigger.to_state.attributes.temperature | float(0)) >= 1 }}

# New condition:
{% set from_temp = trigger.from_state.attributes.temperature | float(-999) %}
{% set to_temp = trigger.to_state.attributes.temperature | float(-999) %}
{% set drop = from_temp - to_temp %}
{{ from_temp > 50 and to_temp > 50 and from_temp != to_temp and drop >= 1 }}
```

### Validation Checks
| Check | Purpose |
|-------|---------|
| `from_temp > 50` | Rejects null/invalid from_state (defaults to -999) |
| `to_temp > 50` | Rejects null/invalid to_state (defaults to -999) |
| `from_temp != to_temp` | Rejects spurious triggers where both values identical |
| `drop >= 1` | Requires minimum 1°F setback depth |

### Files Modified
- `automations.yaml` - `hvac_1f_setback_start`, `hvac_2f_setback_start` conditions

---

## Recovery START Hybrid Logic Fix - 2026-01-29

### Issue
Recovery binary sensors (`binary_sensor.hvac_*f_recovering`) weren't triggering reliably. Recovery start times were frozen at 2026-01-25, meaning no new recovery events were being captured for 4+ days. The 2F recovery rate slots showed stale values (last 4 slots all 3.0).

### Root Cause
The START condition required gap **greater than** 2°F:
```yaml
{{ (live_setpoint - current) > 2 }}
```

When the house maintained temperature well overnight:
- Setback drops setpoint to 63°F, room cools to 65°F
- Morning schedule raises setpoint to 67°F
- Gap = 67 - 65 = **2°F exactly** (not >2)
- Recovery never triggers

### Fix Applied
Changed to **hybrid logic** requiring both conditions:

| Condition | Purpose |
|-----------|---------|
| `gap > 1` | Lower threshold catches shallow setbacks |
| `furnace_on` | Confirms actual heating demand, prevents false positives |

```yaml
# OLD START condition:
{{ (live_setpoint - current) > 2 }}

# NEW START condition (hybrid):
{% set gap = live_setpoint - current %}
{% set furnace_on = is_state('binary_sensor.hvac_furnace_running', 'on') %}
{{ gap > 1 and furnace_on }}
```

### Why Hybrid Works
1. **Gap > 1°F** catches recovery even when house stayed warm overnight
2. **Furnace running** ensures we only trigger during actual heating demand
3. Together: prevents false positives during normal thermostat cycling while reliably detecting morning recovery

### Files Modified
- `configuration.yaml` - `binary_sensor.hvac_1f_recovering`, `binary_sensor.hvac_2f_recovering` START conditions

### Impact
- Recovery events will now trigger reliably each morning
- Recovery rate rolling averages will update with fresh data
- Setback optimization calculations will have valid measurements

---

## Stale/Default Data Robustness Fixes - 2026-01-29

### Overview
Comprehensive audit identified multiple places where stale or default data could silently corrupt calculations. The main pattern was "silent failure via defaults" where `| float(35)` or similar would mask sensor failures.

### Critical Fixes Applied

#### 1. Outdoor Temp Proxy - Fail-Fast (CRITICAL)
**File:** `configuration.yaml` lines 1357-1387

**Problem:** When all weather sources failed, sensor returned 35°F silently, corrupting all HDD calculations.

**Fix:** Removed the `{{ 35 }}` fallback. Sensor now becomes `unavailable` when no valid source exists. Availability template matches state logic exactly.

```yaml
# OLD: Silent fallback
{% else %}
  {{ 35 }}
{% endif %}

# NEW: Fail-fast (no else clause, becomes unavailable)
{% elif om is number and om > -50 %}
  {{ om | round(1) }}
{% endif %}
```

#### 2. HDD/CDD Sensors - Availability Check
**File:** `configuration.yaml` lines 1401-1431

**Problem:** HDD/CDD sensors used `| float(35)` default for outdoor temp proxy.

**Fix:** Added explicit `availability` templates requiring outdoor temp proxy to be available. State logic uses `| float(none)` to detect failures.

#### 3. HDD Capture - Upstream + Delta Validation
**File:** `automations.yaml` lines 117-145

**Problem:** Capture proceeded even when outdoor temp proxy was unavailable (using masked 35°F default). No validation that cumulative values stayed within bounds.

**Fix:** Added three-layer validation:
```yaml
{# Upstream validation: outdoor temp proxy must be available #}
{% set upstream_ok = proxy not in ['unknown', 'unavailable'] %}
{# Value validation: HDD/CDD must be valid numbers in range #}
{% set values_ok = is_number(hdd) and is_number(cdd) and 0 <= hdd_val <= 65 %}
{# Delta validation: new cumulative shouldn't exceed reasonable bounds #}
{% set delta_ok = (cum_month + hdd_val) <= 2500 and (cum_year + hdd_val) <= 8000 %}
```

#### 4. Runtime/HDD Capture - Upstream Validation
**File:** `automations.yaml` lines 224-248

**Problem:** Capture didn't validate that furnace runtime and HDD sensors were available.

**Fix:** Added upstream validation:
```yaml
{% set upstream_ok = furnace_runtime not in ['unknown', 'unavailable'] and
                     hdd_today not in ['unknown', 'unavailable'] %}
```

#### 5. Recovery Start - Conditional Validation
**File:** `automations.yaml` lines 777-810, 972-1005

**Problem:** Recovery start captured outdoor temp with `| float(35)` default. No validation of hold_setpoint.

**Fix:** Added condition requiring:
- Outdoor temp proxy available
- hold_setpoint > 50 (validates stored value)
- Thermostat current_temperature is a number

#### 6. Recovery End - Smart Defaults
**File:** `automations.yaml` lines 868-888, 1063-1083

**Problem:** Multiple `| float(35)` defaults for overnight_low, setback calculations, baseline_min_per_hdd.

**Fix:**
- overnight_low: Detects initialization value (150) and only then falls back to 35
- setback_depth: Validates hold/setback > 50 before calculating
- setback_hours: Returns 0 (not 8) when unavailable
- baseline_min_per_hdd: Checks for unavailable state, returns 0
- Calculations chain: Return 0 when dependencies are invalid

#### 7. Watchdog Thresholds Tightened
**File:** `configuration.yaml` lines 1340, 1352

**Problem:** 93600 second (26 hour) threshold + 2 hour alert delay = 28 hours before notification.

**Fix:** Changed to 90000 seconds (25 hours). Total delay now ~27 hours, catching failures 1 hour sooner.

### Validation Philosophy

| Layer | Purpose | Example |
|-------|---------|---------|
| **Upstream** | Ensure dependencies are available | `proxy not in ['unknown', 'unavailable']` |
| **Value** | Ensure values are in valid range | `0 <= hdd_val <= 65` |
| **Delta** | Ensure changes are reasonable | `cum_month + hdd_val <= 2500` |
| **Initialization** | Detect unset sentinel values | `val < 140` (vs initial 150) |

### Logging Improvements
Added detailed logging when captures fail:
- HDD capture: Logs proxy state, HDD, CDD, and cumulative values
- Runtime/HDD capture: Logs furnace runtime, HDD, and calculated value

### Files Modified
- `configuration.yaml` - Outdoor temp proxy, HDD/CDD sensors, watchdog thresholds
- `automations.yaml` - HDD capture, runtime/HDD capture, recovery start/end automations

### Impact
- Weather source failures now cascade properly (sensor becomes unavailable)
- HDD/CDD won't capture corrupt values from masked defaults
- Recovery tracking won't use stale/invalid hold_setpoint values
- Faster alerting when daily captures fail
- Clear logging when validation prevents capture

---

## Phase 3: Staleness Detection & Slot Validation - 2026-01-29

### Overview
Added staleness detection for recovery rates and climate norms, plus validation for 7-day rolling slot values to filter out corrupt data.

### 1. Recovery Rate Staleness Tracking

**New Entities:**
- `input_datetime.hvac_1f_recovery_rate_last_updated` - Timestamp when 1F rate last stored
- `input_datetime.hvac_2f_recovery_rate_last_updated` - Timestamp when 2F rate last stored
- `binary_sensor.hvac_1f_recovery_rate_stale` - ON when >14 days since update
- `binary_sensor.hvac_2f_recovery_rate_stale` - ON when >14 days since update

**Automation Changes:**
- `hvac_1f_recovery_end` / `hvac_2f_recovery_end` - Now sets timestamp when recovery rate is stored

**Alert:**
- `notify_recovery_rate_stale` - Fires after 24h of staleness, with diagnostic info

### 2. 7-Day Rolling Slot Validation

**Problem:** Corrupt values in rolling slots (e.g., HDD > 65 or runtime/HDD > 120) would persist for 7 days and skew averages.

**Fix:** All sensors now filter slot values to valid ranges:

| Sensor | Valid Range | Invalid Values |
|--------|-------------|----------------|
| HDD Rolling 7-Day | 0-65 | Excluded from sum |
| Runtime/HDD Mean | 0-120 | Excluded from average |
| Runtime/HDD Std Dev | 0-120 | Excluded from calculation |
| Runtime/HDD Data Count | 0-120 | Not counted |

**Template Pattern:**
```yaml
{% set days = [
  states('input_number.hdd_day_1') | float(-1),
  ...
] %}
{% set valid = days | select('>=', 0) | select('<=', 65) | list %}
{{ valid | sum | round(1) }}
```

### 3. Climate Norms Staleness Detection

**New Entity:**
- `binary_sensor.climate_norms_stale` - ON when `day_of_year` attribute doesn't match today

**Logic:**
```yaml
{% set sensor_doy = state_attr('sensor.climate_norms_today', 'day_of_year') | int(0) %}
{% set actual_doy = now().timetuple().tm_yday %}
{{ status in ['unknown', 'unavailable', 'error'] or sensor_doy != actual_doy }}
```

**Alert:**
- `notify_climate_norms_stale` - Fires after 2h of staleness, with diagnostic info

### Files Modified
- `configuration.yaml`:
  - Added `input_datetime.hvac_*f_recovery_rate_last_updated`
  - Added `binary_sensor.hvac_*f_recovery_rate_stale`
  - Added `binary_sensor.climate_norms_stale`
  - Updated HDD rolling 7-day sensor with validation
  - Updated runtime/HDD mean, std dev, data count sensors with validation
- `automations.yaml`:
  - Updated `hvac_*f_recovery_end` to set timestamp
  - Added `notify_recovery_rate_stale` automation
  - Added `notify_climate_norms_stale` automation

### Staleness Thresholds Summary

| Sensor | Threshold | Alert Delay | Total |
|--------|-----------|-------------|-------|
| HDD Capture | 25 hours | 2 hours | 27h |
| Runtime/HDD Capture | 25 hours | 2 hours | 27h |
| Recovery Rate | 14 days | 24 hours | 14d + 24h |
| Climate Norms | Immediate | 2 hours | 2h |

---

## Robustness Audit Followup Fixes - 2026-01-29

### Overview
External audit identified residual issues after Phase 1-3 fixes. Key finding: `notify_weather_sources_down` automation was still checking for the old 35°F fallback pattern, which no longer occurs.

### 1. Weather Sources Down Alert Fixed

**Problem:** Automation triggered on "weather source = Open-Meteo for 6h" then checked if proxy == 35. Since proxy now fails fast (becomes unavailable), the == 35 condition would never match.

**Fix:** Rewritten to trigger directly on proxy unavailable:
```yaml
trigger:
  - platform: state
    entity_id: sensor.hvac_outdoor_temp_hartford_proxy
    to: "unavailable"
    for:
      minutes: 30
```

Now alerts within 30 minutes of all weather sources failing.

### 2. Weather Source Indicator Fixed

**Problem:** `sensor.hvac_outdoor_weather_source` always showed "Open-Meteo" in the else case, even when Open-Meteo was also down.

**Fix:** Added explicit Open-Meteo validation and "No valid source" fallback:
```yaml
{% elif om is number and om > -50 %}Open-Meteo
{% else %}No valid source{% endif %}
```

### 3. Recovery Rate Avg Sensors - Availability Added

**Problem:** Recovery rate averages returned 0 when no valid samples existed. This 0 would be recorded in long-term statistics as "real data."

**Fix:** Added `availability:` template requiring at least one valid sample:
```yaml
availability: >
  {% set rates = [...] %}
  {{ rates | select('gt', 0) | list | count > 0 }}
```

Now sensors become `unavailable` when no data, preventing false zeros in history.

### 4. Persisted Weather Inputs (Already Robust)

**Analysis:** Recovery start automations already have conditions requiring proxy availability before any writes occur. The `| float(0)` defaults are defensive fallbacks that shouldn't be reached.

### Files Modified
- `automations.yaml`:
  - Rewrote `notify_weather_sources_down` to trigger on proxy unavailable
- `configuration.yaml`:
  - Updated `sensor.hvac_outdoor_weather_source` with "No valid source" fallback
  - Added `availability:` to `sensor.hvac_1f_recovery_rate_avg`
  - Added `availability:` to `sensor.hvac_2f_recovery_rate_avg`

### Robustness Design Principles (Summary)

| Principle | Implementation |
|-----------|----------------|
| **Fail-fast at boundary** | Outdoor temp proxy returns unavailable, not 35°F |
| **Availability chaining** | HDD/CDD unavailable when proxy unavailable |
| **Never default persisted values** | Conditions validate before writes; sentinels detect corruption |
| **Watchdogs alarm on "unavailable"** | All alerts now key off availability, not magic numbers |
| **KPIs unavailable when no data** | Recovery rate avg returns unavailable, not 0 |

---

## Tier 1 Data Integrity Matrix - 2026-01-29

### Overview
Formalizes data quality tracking for the four highest-risk pipelines: stateful, cumulative, and decision-driving metrics where silent data issues can distort weeks of analysis.

### Matrix Summary

| Pipeline | Primary KPIs | Freshness | Coverage | Validity | Composite Health Rule |
|----------|--------------|-----------|----------|----------|----------------------|
| **Outdoor Weather → HDD** | HDD daily, HDD 7-day, CDD | `hdd_capture_age_hours` | `hdd_valid_days_7d` | Temp bounds, HDD 0-65 | Proxy available AND capture <36h AND ≥5 valid days |
| **Runtime ÷ HDD** | Runtime/HDD daily, 7-day mean | `runtime_per_hdd_capture_age_hours` | `runtime_per_hdd_valid_days_7d` | Runtime ≥0, HDD >0 | HDD healthy AND ≥4 valid days AND capture <36h |
| **Setback Recovery** | Recovery rate avg, weather-adjusted | `recovery_last_event_age_hours` | `recovery_events_7d` | ΔT >0, Runtime >0, outdoor available | ≥3 events in 7d AND last event <7d AND proxy available |
| **Setback Optimization** | Net benefit avg, optimal setback trend | `setback_opt_last_run_age_hours` | `setback_opt_valid_days_14d` | Recovery + overnight runtime valid | Recovery healthy AND ≥5 valid days in 14d |

### Status Types

| Type | Purpose | Prevents |
|------|---------|----------|
| **Freshness** | Detects stalled pipelines | "Metric frozen for weeks but looks normal" |
| **Coverage** | Measures completeness in rolling windows | "7-day mean built from only 2 good days" |
| **Validity** | Range + dependency checks | "Math worked but inputs were garbage" |
| **Composite Health** | Single boolean for UI + alerting | Dashboard shows KPI only when trustworthy |

### Entity Naming Pattern

Each pipeline follows this pattern:

```
# Freshness
sensor.<pipeline>_last_capture_ts
sensor.<pipeline>_age_hours
binary_sensor.<pipeline>_stale

# Coverage
sensor.<pipeline>_valid_days_7d (or _events_7d)
sensor.<pipeline>_coverage_pct

# Validity
binary_sensor.<pipeline>_inputs_valid

# Composite Health (drives KPI visibility)
binary_sensor.<pipeline>_healthy
```

### Dashboard Philosophy

Each Tier 1 KPI shows a status badge:

| State | Badge | Meaning |
|-------|-------|---------|
| Healthy | 🟢 | All checks pass, KPI trustworthy |
| Partial | 🟡 | Coverage <100% but usable |
| Stale | 🔴 | Freshness check failed |
| Blocked | 🔴 | Upstream dependency invalid |

### Pipeline Implementations

#### 1. HDD Pipeline

**Existing Entities (already implemented):**
- `sensor.hvac_outdoor_temp_hartford_proxy` - Fail-fast weather source
- `binary_sensor.hdd_capture_stale` - 25h threshold
- `sensor.hvac_hdd65_today` - With availability template

**New Entities:**
- `sensor.hdd_valid_days_7d` - Count of valid slots (0-65 range)
- `binary_sensor.hdd_pipeline_healthy` - Composite health

**Composite Health Rule:**
```yaml
{{ proxy_available and not stale and valid_days >= 5 }}
```

#### 2. Runtime/HDD Pipeline

**Existing Entities:**
- `binary_sensor.runtime_per_hdd_capture_stale` - 25h threshold
- `sensor.hvac_runtime_per_hdd_7_day_mean` - With slot validation
- `sensor.hvac_runtime_per_hdd_data_count` - Valid sample count

**New Entities:**
- `binary_sensor.runtime_per_hdd_pipeline_healthy` - Composite health

**Composite Health Rule:**
```yaml
{{ hdd_healthy and not stale and data_count >= 4 }}
```

#### 3. Recovery Pipeline

**Existing Entities:**
- `binary_sensor.hvac_1f_recovery_rate_stale` / `_2f_` - 14-day threshold
- `sensor.hvac_1f_recovery_rate_data_count` / `_2f_` - Valid sample count
- `sensor.hvac_1f_recovery_rate_avg` / `_2f_` - With availability template

**New Entities:**
- `sensor.hvac_1f_recovery_age_hours` / `_2f_` - Hours since last event
- `binary_sensor.hvac_1f_recovery_inputs_valid` / `_2f_` - Input validation
- `binary_sensor.hvac_1f_recovery_healthy` / `_2f_` - Composite health

**Composite Health Rule:**
```yaml
{{ not stale and data_count >= 3 and inputs_valid and proxy_available }}
```

#### 4. Setback Optimization Pipeline (Future)

Depends on Recovery pipeline health. Implementation deferred until Recovery pipeline data is stable.

### New Entities Summary

| Entity | Type | Pipeline |
|--------|------|----------|
| `sensor.hdd_valid_days_7d` | template | HDD |
| `binary_sensor.hdd_pipeline_healthy` | template | HDD |
| `binary_sensor.runtime_per_hdd_pipeline_healthy` | template | Runtime/HDD |
| `sensor.hvac_1f_recovery_age_hours` | template | Recovery |
| `sensor.hvac_2f_recovery_age_hours` | template | Recovery |
| `binary_sensor.hvac_1f_recovery_inputs_valid` | template | Recovery |
| `binary_sensor.hvac_2f_recovery_inputs_valid` | template | Recovery |
| `binary_sensor.hvac_1f_recovery_healthy` | template | Recovery |
| `binary_sensor.hvac_2f_recovery_healthy` | template | Recovery |

### Dashboard Cards

New cards in `dashboards/cards/mushroom/`:
- `pipeline-health-hdd.yaml` - HDD pipeline status chip
- `pipeline-health-runtime-hdd.yaml` - Runtime/HDD pipeline status chip
- `pipeline-health-recovery-1f.yaml` - 1F Recovery pipeline status chip
- `pipeline-health-recovery-2f.yaml` - 2F Recovery pipeline status chip
- `tier1-health-summary.yaml` - Combined Tier 1 health overview

---

## Week/Month Furnace Metrics - 2026-01-30

### Overview
Added comprehensive week and month-to-date sensors for furnace cycles, zone overlap, and chaining index to complement the existing daily metrics.

### New History Stats Sensors
| Sensor | Type | Period |
|--------|------|--------|
| `sensor.hvac_furnace_cycles_week` | count | 7-day rolling |
| `sensor.hvac_furnace_cycles_month` | count | Month-to-date |
| `sensor.hvac_1f_heat_cycles_week` | count | 7-day rolling |
| `sensor.hvac_2f_heat_cycles_week` | count | 7-day rolling |
| `sensor.hvac_1f_heat_cycles_month` | count | Month-to-date |
| `sensor.hvac_2f_heat_cycles_month` | count | Month-to-date |

### New Template Sensors
| Sensor | Description |
|--------|-------------|
| `sensor.hvac_total_cycles_week` | 1F + 2F zone calls (7-day) |
| `sensor.hvac_total_cycles_month` | 1F + 2F zone calls (MTD) |
| `sensor.hvac_chaining_index_week` | Zone overlap ratio (7-day) |
| `sensor.hvac_chaining_index_month` | Zone overlap ratio (MTD) |
| `sensor.hvac_zone_overlap_week` | Overlap minutes (7-day) |
| `sensor.hvac_zone_overlap_month` | Overlap minutes (MTD) |
| `sensor.hvac_furnace_cycles_per_day_week` | Avg cycles/day (7-day) |
| `sensor.hvac_furnace_cycles_per_day_month` | Avg cycles/day (MTD) |
| `sensor.hvac_furnace_min_per_cycle_week` | Avg min/cycle (7-day) |
| `sensor.hvac_furnace_min_per_cycle_month` | Avg min/cycle (MTD) |

### New Mushroom Cards
Located in `dashboards/cards/mushroom/`:
- `furnace-runtime-week.yaml` / `furnace-runtime-month.yaml`
- `furnace-cycles-week.yaml` / `furnace-cycles-month.yaml`
- `zone-overlap-week.yaml` / `zone-overlap-month.yaml`
- `chaining-index-week.yaml` / `chaining-index-month.yaml`
- `min-per-cycle-week.yaml` / `min-per-cycle-month.yaml`

---

## Recovery End Net Runtime Fix - 2026-01-30

### Issue
The `hvac_*f_recovery_end` automations were aborting before completing all actions (including turning off the setback latch) when the calculated `net_runtime` exceeded the input_number's valid range (-200 to 200).

### Root Cause
When `baseline_min_per_hdd` (from `sensor.hvac_runtime_per_hdd_7_day`) was 0 or unavailable:
- `expected_hold_runtime = 0`
- `net_runtime = 0 - total_runtime` = large negative value (e.g., -302)
- `input_number.hvac_*f_last_net_runtime` rejected the value (outside -200 to 200)
- Automation aborted → setback latch never cleared → CSV never written

### Fix Applied
Added value clamping before storing `net_runtime`:
```yaml
# Before (could abort automation):
value: "{{ net_runtime }}"

# After (clamped to valid range):
value: "{{ [[net_runtime | float, -200] | max, 200] | min }}"
```

### Impact
- Automation now completes reliably even with extreme net_runtime values
- Setback latch properly cleared at end of recovery cycle
- CSV logging executes as expected
- Values outside -200 to 200 are clamped (data loss acceptable for outliers)

### Files Modified
- `automations.yaml` - `hvac_1f_recovery_end`, `hvac_2f_recovery_end`

---

## Automation Failure Tracking - 2026-01-30

### Overview
Added a system to monitor and display automation failures on the dashboard. Captures errors from Home Assistant's system log and provides visibility into automation health.

### How It Works
1. `track_automation_failures` automation listens for `system_log_event` with level ERROR
2. Filters for events containing "automation" in source or message
3. Increments failure counter and stores last failure details
4. Creates persistent notification for each failure
5. Counter resets at midnight

### New Entities

| Entity | Type | Purpose |
|--------|------|---------|
| `counter.automation_failures_24h` | counter | Count of failures in last 24h |
| `input_text.last_automation_failure` | input_text | Description of most recent failure |
| `binary_sensor.automation_failures_active` | binary_sensor | ON when failures > 0 (device_class: problem) |

### New Automations

| Automation | Trigger | Action |
|------------|---------|--------|
| `track_automation_failures` | `system_log_event` (ERROR) | Increment counter, store details, notify |
| `reset_automation_failure_counter` | Midnight (00:00) | Reset counter and clear last failure text |

### Dashboard Card
New mushroom card: `dashboards/cards/mushroom/automation-failures.yaml`
- Shows failure count with color coding (green/orange/red)
- Displays truncated last failure message
- Badge icon appears when failures exist

### Usage
Add the card to any dashboard to monitor automation health:
```yaml
# Copy from dashboards/cards/mushroom/automation-failures.yaml
```

### What Gets Captured
- Automation execution errors (like the net_runtime range issue)
- Template errors in automations
- Service call failures within automations
- Any ERROR level log entry mentioning "automation"

### What Does NOT Get Captured
- Automations that silently don't trigger (use staleness sensors for this)
- Warnings (only ERROR level)
- Sensor calculation errors (unless they cause automation to fail)

---

## Monthly Accumulators Fix - 2026-01-30

### Issue
Month-to-date `history_stats` sensors were undercounting after day 14 due to `recorder.purge_keep_days: 14`. When the recorder purges old data, the history_stats sensors lose visibility into early-month data.

### Affected Sensors (Before Fix)
| Sensor | Problem |
|--------|---------|
| `sensor.hvac_furnace_runtime_month` | Undercount after day 14 |
| `sensor.hvac_furnace_cycles_month` | Undercount after day 14 |
| `sensor.hvac_1f_heat_runtime_month` | Undercount after day 14 |
| `sensor.hvac_2f_heat_runtime_month` | Undercount after day 14 |
| `sensor.hvac_1f_heat_cycles_month` | Undercount after day 14 |
| `sensor.hvac_2f_heat_cycles_month` | Undercount after day 14 |

### Solution
Replaced history_stats month sensors with **accumulated input_numbers** (same pattern as HDD tracking):

1. **Daily capture at 23:56:30**: Add today's values to accumulators
2. **Monthly reset on day 1**: Reset accumulators to 0
3. **Template sensors**: Read `accumulator + today` for real-time values

### New Input Numbers
| Entity | Purpose |
|--------|---------|
| `input_number.furnace_runtime_month_acc` | Accumulated furnace runtime (h) |
| `input_number.furnace_cycles_month_acc` | Accumulated furnace cycles |
| `input_number.zone_1f_runtime_month_acc` | Accumulated 1F runtime (h) |
| `input_number.zone_2f_runtime_month_acc` | Accumulated 2F runtime (h) |
| `input_number.zone_1f_cycles_month_acc` | Accumulated 1F cycles |
| `input_number.zone_2f_cycles_month_acc` | Accumulated 2F cycles |

### Template Sensor Formula
Each month sensor now computes: `accumulator + today's value`
```yaml
state: >
  {% set acc = states('input_number.furnace_runtime_month_acc') | float(0) %}
  {% set today = states('sensor.hvac_furnace_runtime_today') | float(0) %}
  {{ (acc + today) | round(2) }}
```

### Benefits
- **Immune to recorder purge**: Accumulators persist regardless of purge_keep_days
- **Keep purge_keep_days=14**: DB performance maintained
- **Same sensor names**: All existing references continue to work
- **Matches HDD pattern**: Consistent architecture

### Week Sensors Unchanged
The 7-day `history_stats` sensors remain as-is since 14-day retention fully covers them:
- `sensor.hvac_furnace_runtime_week`
- `sensor.hvac_furnace_cycles_week`
- `sensor.hvac_1f_heat_runtime_week` / `_2f_`
- `sensor.hvac_1f_heat_cycles_week` / `_2f_`

### Seeding Script
**Script:** `script.seed_monthly_accumulators`

One-time script to initialize accumulators with current MTD values. Calculates `(month_total - today)` to avoid double-counting since template sensors add today's value automatically.

**Procedure:**
1. Reload scripts: Developer Tools → YAML → Reload Scripts
2. Run script: Developer Tools → Services → `script.seed_monthly_accumulators`
3. Restart HA to load the new template sensors

**Note:** Script must be run while old history_stats sensors still have data. If sensors are already removed/unavailable, manually seed based on available data.

### January 2026 CSV Recovery
CSV data (`reports/hvac_daily_2026.csv`) only goes back to Jan 23 due to recorder purge. Calculated totals from Jan 23-29 (excluding Jan 30 which gets added by template sensor):

| Accumulator | Value | Source |
|-------------|-------|--------|
| `furnace_runtime_month_acc` | 55.5 h | Sum of furnace_runtime_min / 60 |
| `furnace_cycles_month_acc` | 427 | Sum of furnace_cycles |
| `zone_1f_runtime_month_acc` | 30.7 h | Sum of runtime_1f_min / 60 |
| `zone_2f_runtime_month_acc` | 34.7 h | Sum of runtime_2f_min / 60 |
| `zone_1f_cycles_month_acc` | N/A | Not in CSV (zone_calls_total only) |
| `zone_2f_cycles_month_acc` | N/A | Not in CSV (zone_calls_total only) |

**Manual seeding** (after HA restart):
```yaml
action: input_number.set_value
target:
  entity_id: input_number.furnace_runtime_month_acc
data:
  value: 55.5
```

January totals will be incomplete (missing Jan 1-22). February onwards will be accurate.

### Files Modified
- `configuration.yaml` - Added input_numbers, replaced history_stats with template sensors
- `automations.yaml` - Updated `capture_daily_monthly_tracking` and `reset_monthly_hdd`
- `scripts.yaml` - Added `seed_monthly_accumulators` script

---

## Entity Registry _2 Suffix - 2026-01-30

### Background
When replacing `history_stats` month sensors with template sensors (same entity names), Home Assistant's entity registry detected a conflict. The old entity IDs still existed in the registry from the removed history_stats sensors, so HA automatically appended `_2` to the new template sensors.

### Affected Sensors
| New Entity ID (with _2) | Friendly Name |
|-------------------------|---------------|
| `sensor.hvac_1f_heat_cycles_month_2` | HVAC 1F Heat Cycles Month |
| `sensor.hvac_1f_heat_runtime_month_2` | HVAC 1F Heat Runtime Month |
| `sensor.hvac_2f_heat_cycles_month_2` | HVAC 2F Heat Cycles Month |
| `sensor.hvac_2f_heat_runtime_month_2` | HVAC 2F Heat Runtime Month |
| `sensor.hvac_furnace_cycles_month_2` | HVAC Furnace Cycles Month |
| `sensor.hvac_furnace_runtime_month_2` | HVAC Furnace Runtime Month |

### Resolution
Rather than cleaning up the entity registry and renaming, all references in `configuration.yaml` were updated to use the `_2` suffix. This includes:
- Template sensor dependencies (chaining index, overlap, min/cycle, etc.)
- Shell command `appendmonthlycsv`
- Derived sensors (efficiency deviation, heating efficiency, etc.)

### Note
The `unique_id` values in the template sensor definitions remain without `_2` (e.g., `unique_id: hvac_furnace_runtime_month`). The `_2` suffix only applies to the entity_id in the entity registry. If the entity registry is ever cleaned up (removing orphaned entries), the sensors would revert to non-`_2` names and all references would need updating.

---

## Robustness Fixes - 2026-01-30

### 1. Recovery Minutes Range Alignment

**Issue:** Automation clamped recovery minutes to 300, but `input_number.hvac_*f_last_recovery_minutes` had `max: 180`. Values 181-300 would cause service call failures.

**Fix:** Increased input_number max from 180 to 300 to match automation clamps.

| Entity | Old Max | New Max |
|--------|---------|---------|
| `input_number.hvac_1f_last_recovery_minutes` | 180 | 300 |
| `input_number.hvac_2f_last_recovery_minutes` | 180 | 300 |

### 2. Availability Templates for _2 Entity Dependencies

**Issue:** Sensors depending on `_2` suffix entities would silently default to 0 if those entities became unavailable (e.g., during entity registry cleanup).

**Fix:** Added `availability:` templates to all sensors that reference `_2` entities. Sensors now become `unavailable` instead of returning misleading zeros.

| Sensor | Dependencies |
|--------|--------------|
| `sensor.hvac_total_cycles_month` | `*_heat_cycles_month_2` |
| `sensor.hvac_chaining_index_month` | `*_heat_cycles_month_2`, `furnace_cycles_month_2` |
| `sensor.hvac_furnace_cycles_per_day_month` | `furnace_cycles_month_2` |
| `sensor.hvac_furnace_min_per_cycle_month` | `furnace_runtime_month_2`, `furnace_cycles_month_2` |
| `sensor.hvac_total_heat_runtime_month` | `*_heat_runtime_month_2` |
| `sensor.hvac_runtime_per_hdd_month` | `furnace_runtime_month_2` |
| `sensor.hvac_zone_balance_month` | `*_heat_runtime_month_2` |
| `sensor.hvac_heating_efficiency_mtd` | `furnace_runtime_month_2` |
| `sensor.hvac_building_load_ua_estimate` | `furnace_runtime_month_2` |
| `sensor.efficiency_deviation_month` | `furnace_runtime_month_2` |
| `sensor.hvac_runtime_per_hdd_month` | `furnace_runtime_month_2` |

### Files Modified
- `configuration.yaml` - Input number ranges, availability templates

---

## Month Sensor Double-Count Gating Fix - 2026-01-31

### Issue
Month-to-date sensors using the `accumulator + today` pattern would double-count the last day of the month. Timeline on Jan 31:
- 23:56:30: `capture_daily_monthly_tracking` adds today's values to accumulators
- 23:58:30: `csv_monthly_report` reads template sensors that compute `acc + today`
- Result: Today counted twice (once in accumulator, once via `+ today`)

### Fix
Added gating logic to all 6 month template sensors. After the daily capture runs, sensors return only the accumulator value (no `+ today` addition) to prevent double-counting.

**New Entity:**
- `input_datetime.monthly_tracking_capture_last_ok` - Timestamp when daily capture succeeded

**Modified Sensors (6 total):**
- `sensor.hvac_furnace_runtime_month_2`
- `sensor.hvac_furnace_cycles_month_2`
- `sensor.hvac_1f_heat_runtime_month_2`
- `sensor.hvac_2f_heat_runtime_month_2`
- `sensor.hvac_1f_heat_cycles_month_2`
- `sensor.hvac_2f_heat_cycles_month_2`

**Gating Logic:**
```yaml
{% set last_capture = states('input_datetime.monthly_tracking_capture_last_ok') %}
{% set captured_today = last_capture[:10] == now().strftime('%Y-%m-%d') if last_capture not in ['unknown', 'unavailable', '1970-01-01 00:00:00'] else false %}
{{ (acc if captured_today else acc + today) | round(2) }}
```

**Behavior:**
- Before 23:56:30: `captured_today = false` → sensor returns `acc + today`
- After 23:56:30: `captured_today = true` → sensor returns just `acc` (today already included)
- Next day: `captured_today = false` again → pattern repeats

### Monthly Report Stale Sentinel
Added detection for missing monthly reports.

**New Entities:**
- `binary_sensor.monthly_report_stale` - ON if past day 1 and last capture was previous month
- `notify_monthly_report_stale` automation - Alerts after 6h of staleness

**Alert Behavior:**
- On Feb 2+ (or any day > 1), if last monthly capture was in January, the sensor triggers
- Provides time to investigate and manually fix if CSV row is missing

### Files Modified
- `configuration.yaml`:
  - Added `input_datetime.monthly_tracking_capture_last_ok`
  - Added `binary_sensor.monthly_report_stale`
  - Updated all 6 month accumulator sensors with gating logic
- `automations.yaml`:
  - Updated `capture_daily_monthly_tracking` to set timestamp
  - Added `notify_monthly_report_stale` automation

### Bill Archive Automation Status
Reviewed and confirmed working. The `target.entity_id` template syntax is correct in modern Home Assistant. All archive input_numbers exist (`electric_archive_*_amount`, `gas_archive_*_amount`, etc.).

---

## Setback Recovery Metrics Fixes - 2026-02-05

### Problems Fixed
Five interrelated bugs in setback recovery tracking that produced incorrect CSV data:

1. **CSV shell commands recomputed values inconsistently** — `total_runtime` column was `recovery_minutes × setback_degrees` (degree-minutes), not actual furnace runtime. `expected_hold` assumed fixed 8-hour window. But `net_runtime` came from the automation's different calculation, making columns internally inconsistent.
2. **Midnight runtime extrapolation overstated runtime** — Recovery-period duty cycle (near 100%) was projected backwards to estimate pre-midnight runtime, systematically overstating actual furnace minutes and driving `net_runtime` to the -200 clamp.
3. **Recovery start fired without active setback** — Normal heating cycles with >1°F gap and furnace running triggered false recovery events, creating spurious data and messy latch behavior.
4. **Recovery minutes inflated by 10 minutes** — The `for: minutes: 10` stability trigger delay was included in the `recovery_minutes` calculation since `now()` was used as the endpoint.
5. **total_runtime and expected_hold not persisted** — Variables computed in the recovery_end automation were local and lost; the shell command could not read them and recomputed different values.

### Fix 1: CSV Shell Commands Read Input Numbers Only
- Rewrote `appendsetbacklog_1f` and `appendsetbacklog_2f` to read exclusively from `input_number.*` states
- Expanded CSV schema from 7 to 10 columns: added `recovery_minutes`, `setback_degrees`, `recovery_rate`
- Only inline computation: `recovery_rate = recovery_minutes / max(setback_degrees, 0.1)`
- Archived old corrupt CSV as `hvac_setback_log_pre_fix.csv`

### Fix 2: MTD Accumulator Snapshots Replace Midnight Extrapolation
- `setback_start` now stores `furnace_runtime_month_acc + furnace_runtime_today` (hours) instead of `furnace_runtime_today × 60` (minutes)
- `recovery_end` computes `(current_mtd - start_mtd) × 60` for exact furnace minutes with no extrapolation
- Changed `hvac_*f_setback_start_runtime` input_numbers: max 1440→1000, unit min→h, step 0.1→0.01
- Month-boundary fallback: if `setback_start` month ≠ current month, uses conservative today-only runtime (~1 day/month edge case)

### Fix 3: Gate Recovery Start on Setback Active
- Added `input_boolean.hvac_*f_setback_active == "on"` condition to both `recovery_start` automations
- Prevents false recovery events during normal heating cycles where gap > 1°F and furnace is running

### Fix 4: Subtract Stability Wait from Recovery Minutes
- Changed `recovery_minutes` to subtract 10 from elapsed time, with floor of 0
- Corrects the systematic ~10 minute inflation caused by `for: minutes: 10` trigger delay

### Fix 5: Store total_runtime and expected_hold Before CSV Log
- Added 4 new input_numbers: `hvac_*f_last_total_runtime`, `hvac_*f_last_expected_hold` (0-1500, step 1, min)
- Recovery_end stores both values before calling `shell_command.appendsetbacklog_*f`
- Values clamped to [0, 1500] to prevent automation abort

### New Entities
- `input_number.hvac_1f_last_total_runtime` — 1F last total furnace runtime during setback (min)
- `input_number.hvac_1f_last_expected_hold` — 1F last expected hold runtime (min)
- `input_number.hvac_2f_last_total_runtime` — 2F last total furnace runtime during setback (min)
- `input_number.hvac_2f_last_expected_hold` — 2F last expected hold runtime (min)

### Modified Entities
- `input_number.hvac_1f_setback_start_runtime` — max: 1000, unit: h, step: 0.01
- `input_number.hvac_2f_setback_start_runtime` — max: 1000, unit: h, step: 0.01

### Files Modified
- `configuration.yaml`:
  - Changed `hvac_1f_setback_start_runtime` and `hvac_2f_setback_start_runtime` (max, unit, step)
  - Added 4 new input_numbers for last_total_runtime and last_expected_hold
  - Rewrote `appendsetbacklog_1f` and `appendsetbacklog_2f` shell commands
- `automations.yaml`:
  - `hvac_1f_setback_start` / `hvac_2f_setback_start` — MTD accumulator snapshot
  - `hvac_1f_recovery_start` / `hvac_2f_recovery_start` — Added setback_active gate
  - `hvac_1f_recovery_end` / `hvac_2f_recovery_end` — New total_runtime calc, -10min recovery, store to input_numbers
- `reports/hvac_setback_log.csv` — Archived old as `hvac_setback_log_pre_fix.csv`, new 10-column header
- `claude.md` — Updated entity list, CSV schema, added changelog

### Deployment Notes
After restarting HA:
1. Manually set both `hvac_*f_setback_start_runtime` to 0 via Developer Tools (old values are in minutes, new schema is hours)
2. First setback cycle after deployment will establish correct MTD baseline
3. Old `hvac_setback_log_pre_fix.csv` preserved for reference (data is not comparable to new schema)

---

## Recovery Metrics Bug Fixes - 2026-02-06

### Issues Fixed

1. **Sensor entity ID mismatch** — Automations referenced `sensor.hvac_runtime_per_hdd_7day` but actual entity is `sensor.hvac_runtime_per_hdd_7_day` (with underscore). Caused `expected_hold` to always be 0.

2. **CSV formula synchronized** — Shell commands in `appendsetbacklog_1f` and `appendsetbacklog_2f` now use same min/°F formula as automations.

### Code Changes

**automations.yaml (lines 1082, 1283):**
```yaml
# OLD: sensor.hvac_runtime_per_hdd_7day
# NEW: sensor.hvac_runtime_per_hdd_7_day
```

**Recovery rate unit: min/°F**
Both automations and CSV shell commands now use `minutes / max(degrees, 0.1)` to give min/°F.
This measures how many minutes of recovery time are needed per degree of setback.

### Manual Reset Required

After deploying, reset these values via Developer Tools → Services:

1. **Start runtime values** — Set to current MTD (~38.26 on 2026-02-06):
   ```yaml
   service: input_number.set_value
   target:
     entity_id:
       - input_number.hvac_1f_setback_start_runtime
       - input_number.hvac_2f_setback_start_runtime
   data:
     value: 38.26
   ```

2. **Recovery rate slots** — Reset all 14 to 15 (old data was inverted):
   ```yaml
   service: input_number.set_value
   target:
     entity_id:
       - input_number.hvac_1f_recovery_rate_1
       - input_number.hvac_1f_recovery_rate_2
       - input_number.hvac_1f_recovery_rate_3
       - input_number.hvac_1f_recovery_rate_4
       - input_number.hvac_1f_recovery_rate_5
       - input_number.hvac_1f_recovery_rate_6
       - input_number.hvac_1f_recovery_rate_7
       - input_number.hvac_2f_recovery_rate_1
       - input_number.hvac_2f_recovery_rate_2
       - input_number.hvac_2f_recovery_rate_3
       - input_number.hvac_2f_recovery_rate_4
       - input_number.hvac_2f_recovery_rate_5
       - input_number.hvac_2f_recovery_rate_6
       - input_number.hvac_2f_recovery_rate_7
   data:
     value: 15
   ```

### Files Modified
- `automations.yaml` — Fixed recovery_rate formula (2 locations), fixed sensor reference (4 locations including alerts), raised recovery clamp 300→480, added net_runtime sanity check
- `configuration.yaml` — Fixed recovery_rate in shell commands (2 locations), changed net_runtime min from -200 to -999
- `reports/hvac_setback_log.csv` — Archived as `hvac_setback_log_inverted_bug_2026-02-06.csv`, recreated with header only

### Additional Enhancements (same date)

1. **Alert sensor names fixed** — Two additional references in efficiency alert notifications updated to use correct entity ID.

2. **Recovery clamp raised to 480 minutes** — Was 300 (5 hours), now 480 (8 hours) to accommodate very cold nights where recovery takes longer.

3. **Net runtime sanity check** — Returns `-999` sentinel value if expected_hold is 0, total_runtime is 0, or total_runtime >= 1400 minutes. Makes data quality issues obvious in CSV rather than silently showing 0.

### Expected Values After Fix
- **recovery_rate**: 5-40 °F/hr (varies by outdoor temp, system capacity)
- **expected_hold**: 50-300 minutes (based on HDD and baseline efficiency)
- **total_runtime**: 30-250 minutes (actual furnace runtime during setback period)
- **net_runtime**: -50 to +150 minutes (negative = savings vs baseline), or -999 if data quality check failed

---

## Dehumidifier Performance Tracking - 2026-02-05

### Overview
Added performance metrics to the dehumidifier control system to track effectiveness over time, detect degradation, and assess whether the dew point threshold is optimally set.

### Key Metrics

| Metric | Sensor | What It Reveals |
|--------|--------|----------------|
| Pull-down rate | `sensor.dehumidifier_pull_down_rate` | °F dew point drop per runtime hour. Declining = degradation |
| Hold time | `sensor.dehumidifier_hold_time` | Hours dew point stays below threshold after cycle. Short = threshold too aggressive |
| Duty cycle | `sensor.dehumidifier_duty_cycle_24h` | Rolling 24h avg % running. >60% = too aggressive or undersized |
| Dew point margin | `sensor.dehumidifier_dew_point_margin` | Threshold minus current dew point. Large margin = threshold could be raised |
| Avg cycle minutes | `sensor.dehumidifier_avg_cycle_minutes` | Getting longer over time = increasing moisture load |
| Stop reason | `input_select.dehumidifier_last_stop_reason` | conditions_cleared vs max_runtime. Contextualizes hold time |

### Threshold Optimality Assessment
- **Too aggressive**: high duty cycle, short hold times, low pull-down rate, frequent max_runtime stops
- **Too permissive**: low duty cycle, dew point frequently near cold surface temps (~55-60°F)
- **Well-set**: duty cycle 20-50%, hold times >2h, pull-down rate >1°F/hr, mostly conditions_cleared stops
- **Undersized unit**: high duty cycle AND low pull-down rate
- Note: All conclusions only apply when basement temp > 60°F (the operational gate)

### Design Decisions
1. **Counter for cycles** (not `history_stats: count`): Avoids boundary-crossing quirks; incremented on explicit `off→on` transitions
2. **Explicit `from/to` triggers**: Prevents restart artifacts (`unavailable→on` not counted as cycle start)
3. **Short cycle guard**: Pull-down rate skipped for cycles <10 min (noise would produce extreme rates)
4. **Negative pull-down preserved**: Colored grey on dashboard; reveals weird cycles rather than hiding them
5. **Stop reason tracking**: `dehumidifier_auto_off` stores `trigger.id` so hold time is only valid for `conditions_cleared` stops (not forced 4h max runtime stops)
6. **`state_class: measurement`** on all display sensors: Enables long-term statistics that survive 14-day recorder purge
7. **Rolling 24h duty cycle**: Uses 7-day avg as proxy (`runtime_week / 7 / 24 * 100`) for smoother threshold tuning signal

### New Entities

| Entity | Type | Purpose |
|--------|------|---------|
| `input_number.dehumidifier_cycle_start_dp` | input_number | Dew point at cycle start (°F) |
| `input_number.dehumidifier_last_pull_down_rate` | input_number | Last pull-down rate storage (°F/h) |
| `input_number.dehumidifier_last_cycle_minutes` | input_number | Last cycle duration (min) |
| `input_number.dehumidifier_last_hold_hours` | input_number | Last hold time storage (h) |
| `input_select.dehumidifier_last_stop_reason` | input_select | conditions_cleared / max_runtime / unknown |
| `input_datetime.dehumidifier_cycle_start_time` | input_datetime | Current cycle start timestamp |
| `input_datetime.dehumidifier_last_cycle_end_time` | input_datetime | Last cycle end timestamp |
| `counter.dehumidifier_cycles_today` | counter | Daily cycle count (reset at midnight) |
| `sensor.dehumidifier_runtime_today` | history_stats | Hours ON today |
| `sensor.dehumidifier_runtime_week` | history_stats | Hours ON rolling 7 days |
| `sensor.dehumidifier_duty_cycle_24h` | template | Rolling 24h duty cycle (%) |
| `sensor.dehumidifier_avg_cycle_minutes` | template | Average min per cycle today |
| `sensor.dehumidifier_dew_point_margin` | template | Threshold minus dew point (°F) |
| `sensor.dehumidifier_pull_down_rate` | template | Pull-down rate display (°F/h) |
| `sensor.dehumidifier_hold_time` | template | Hold time display (h) |

### New Automations

| Automation | Trigger | Action |
|------------|---------|--------|
| `dehumidifier_cycle_start_capture` | `switch.dehumidifier` off→on | Increment counter, store dew point + timestamp, calculate hold time |
| `dehumidifier_cycle_end_capture` | `switch.dehumidifier` on→off | Calculate cycle duration + pull-down rate (10-min guard), store end time |
| `dehumidifier_cycle_counter_reset` | Midnight (00:00) | Reset daily cycle counter |

### Modified Automations

| Automation | Change |
|------------|--------|
| `dehumidifier_auto_off` | Added `input_select.set_value` to store stop reason from `trigger.id` before turning off switch |

### New Dashboard Cards

| Card | Location | Description |
|------|----------|-------------|
| `dehumidifier-runtime-today.yaml` | `mushroom/` | Daily runtime (green/yellow/orange) |
| `dehumidifier-duty-cycle.yaml` | `mushroom/` | Rolling duty cycle % (green/amber/red) |
| `dehumidifier-pull-down-rate.yaml` | `mushroom/` | Pull-down rate (green/amber/red/grey) |
| `dehumidifier-dew-point-margin.yaml` | `mushroom/` | Margin below threshold (green/amber/red) |
| `dehumidifier-cycles-today.yaml` | `mushroom/` | Daily cycle count from counter |
| `dehumidifier-hold-time.yaml` | `mushroom/` | Hold time (N/A for max_runtime stops) |
| `basement-dehumidifier-48h.yaml` | `apexcharts/` | 48h dew point + temp + threshold + on/off overlay |
| `dehumidifier-duty-cycle-gauge.yaml` | `gauges/` | Duty cycle gauge (0-30-60-100%) |

### Files Modified
- `configuration.yaml` — Added input_numbers, input_select, input_datetimes, counter, history_stats, template sensors
- `automations.yaml` — Modified `dehumidifier_auto_off`, added 3 new automations
- `dashboards/cards/mushroom/` — 6 new card files
- `dashboards/cards/apexcharts/` — 1 new card file
- `dashboards/cards/gauges/` — 1 new card file
- `claude.md` — Updated entity list, automations list, card library, added this section

---

## Setback Start Debounce Fix - 2026-02-07

### Issue
Resideo/Honeywell thermostats exhibit a 1-second setpoint glitch at scheduled period change times. At exactly 5:30 AM (1F) and 6:00 AM (2F), the setpoint momentarily drops from 67°F back to 63°F, then immediately recovers to 67°F within 1 second.

**Evidence from logs:**
```
1F: 10:30:00.831Z - setpoint: 67→63°F
1F: 10:30:01.831Z - setpoint: 63→67°F

2F: 11:00:01.067Z - setpoint: 67→63°F
2F: 11:00:02.067Z - setpoint: 63→67°F
```

### Root Cause
This is a known Resideo/Honeywell firmware bug with smart recovery. At scheduled period change times, the thermostat briefly reasserts the previous schedule setpoint before applying the new one. This 1-second glitch triggered the Setback Start automations because:
1. It detected a setpoint drop ≥1°F
2. The setback latch wasn't active (recovery had completed)
3. The automation latched setback_active back ON incorrectly
4. This caused the recovery sequence to restart spuriously

### Fix Applied
Added 5-second debounce to both Setback Start automations. The trigger now requires the setpoint to remain at the new value for 5 seconds before firing:

```yaml
# Before:
trigger:
  - platform: state
    entity_id: climate.tstat_...
    attribute: temperature

# After:
trigger:
  - platform: state
    entity_id: climate.tstat_...
    attribute: temperature
    for:
      seconds: 5
```

### Why 5 Seconds
| Factor | Reasoning |
|--------|-----------|
| Glitch duration | Only 1 second - 5 seconds provides 5x safety margin |
| Real setbacks | Persist indefinitely - no risk of missing legitimate setbacks |
| Response time | Keeps detection responsive (30+ seconds would be overkill) |

### Timestamp Correction for Debounce

The 5-second debounce introduces a timing issue: `now()` in the action block executes 5 seconds after the actual setpoint change. This would corrupt setback duration calculations and CSV timestamps.

**Fix:** Use `trigger.to_state.last_changed` to capture the actual event time:

```yaml
# Before (records automation execution time, 5 seconds late):
datetime: "{{ now().strftime('%Y-%m-%d %H:%M:%S') }}"

# After (records actual setpoint change time):
datetime: "{{ (trigger.to_state.last_changed | as_local).strftime('%Y-%m-%d %H:%M:%S') }}"
```

This fix only applies to automations triggering on thermostat attribute changes with debounce. Recovery Start automations correctly use `now()` since they trigger on binary sensor state changes.

### Files Modified
- `automations.yaml` — `hvac_1f_setback_start`, `hvac_2f_setback_start` triggers and datetime actions

---

## Recovery Rate Units Fix - 2026-02-07

### Issue
The recovery rate calculation formula computed °F/hr but the input_numbers and sensors were labeled as min/°F. This units mismatch caused confusion in dashboards and data interpretation.

### Root Cause
The formula `((deg / mins) * 60)` computes degrees per minute × 60 = **°F/hr** (heating speed).

But `unit_of_measurement: "min/°F"` on all recovery rate entities indicates **min/°F** (time to heat one degree).

### Fix Applied
Changed the formula to compute min/°F directly:

```yaml
# Before (computed °F/hr):
{{ ((deg / mins) * 60) | round(1) }}

# After (computes min/°F):
{{ (mins / deg) | round(1) }}
```

### Interpretation
| Value | Meaning |
|-------|---------|
| 10 min/°F | Fast recovery - 10 minutes per degree |
| 15 min/°F | Typical recovery |
| 30+ min/°F | Slow recovery - check system |
| 60 min/°F | Clamp limit (1 hour per degree) |

Lower values = faster recovery = better performance.

### Files Modified
- `automations.yaml` — `hvac_1f_recovery_end`, `hvac_2f_recovery_end` recovery_rate variable (lines ~1046, ~1254)

---

## Weather Freshness Detection Fix - 2026-02-08

### Issue
The `sensor.pirate_weather_data_age` sensor used `last_changed` to track weather data freshness. This caused false stale-data alerts when the weather conditions remained constant (e.g., stable temperature), because `last_changed` only updates when the *value* changes.

### Root Cause
- `last_changed` — Updates only when entity state value changes
- `last_updated` — Updates whenever HA refreshes the entity (regardless of value change)

The stale weather alert automation (`automations.yaml:2008`) triggers when age > 120 min, which could fire even when the integration was updating successfully but conditions stayed the same.

### Fix Applied
Changed the freshness sensor to use `last_updated`:

```yaml
# Before (tracked value changes only):
{% set last_changed = states.weather.pirateweather.last_changed %}

# After (tracks data refresh time):
{% set last_updated = states.weather.pirateweather.last_updated %}
```

### Files Modified
- `configuration.yaml` — `sensor.pirate_weather_data_age` template (line ~2923)

---

## Known Issues

### Pirate Weather Forecast Sensors Broken (resolved 2026-02-08)

**Status:** Resolved

**Root cause:**
The old templates used `state_attr('weather.pirateweather', 'forecast')`, which no longer provides forecast data after HA 2024.3.

**Fix applied (2026-02-08):**
- Removed the 12 deprecated forecast templates that read from the old weather attribute.
- Added a trigger-based template block that calls `weather.get_forecasts` with `response_variable`.
- Added robust guards for empty or missing forecast lists before reading index 0/1.
- Added startup + periodic refresh triggers and a template reload trigger.
- Added temporary debug sensor: `sensor.pirate_weather_daily_forecast_count`.

**New implementation location:**
- `configuration.yaml` trigger-based weather forecast template block at lines ~3322-3554
- `weather.get_forecasts` call at ~3330
- `response_variable: pirate_weather_daily` at ~3335

**Verification (2026-02-08):**
- `sensor.pirate_weather_daily_forecast_count` = `8`
- `sensor.pirate_weather_daily_forecast_count` attribute `response_keys` = `weather.pirateweather`
- `sensor.pirate_weather_today_high` = `13.0`

---

## CSV/Setback Report Hardening - 2026-02-08

### Issue Summary
Report rows were being written with inconsistent values and occasional corrupt records:
- `hvac_setback_log.csv` could log invalid payloads (0 setback degrees with non-zero recovery minutes).
- `hvac_daily_YYYY.csv` could include invalid startup sentinel temperatures and duplicate same-day entries.
- `rotate_setback_log` used `head -1 "$src" > "$src"`, which truncates the source file before reading.

### Fixes Applied
- Added explicit last-value helpers used by setback CSV writer:
  - `input_number.hvac_1f_last_setback_degrees`
  - `input_number.hvac_1f_last_recovery_rate`
  - `input_number.hvac_2f_last_setback_degrees`
  - `input_number.hvac_2f_last_recovery_rate`
- Updated recovery-end automations to populate those helpers before CSV append.
- Added guard conditions so setback rows are only appended when payload is valid.
- Increased `hvac_*_last_net_runtime` max clamp from `200` to `1500` to reduce clipping.
- Hardened daily/monthly CSV automations with data-validity checks and warning logs on skip.
- Fixed yearly setback rotation command to avoid self-truncation.

### Files Modified
- `configuration.yaml`
  - `shell_command.appendsetbacklog_1f`
  - `shell_command.appendsetbacklog_2f`
  - `shell_command.rotate_setback_log`
  - new `input_number.hvac_*_last_setback_degrees`
  - new `input_number.hvac_*_last_recovery_rate`
  - `input_number.hvac_*_last_net_runtime` max updated to `1500`
- `automations.yaml`
  - `hvac_1f_recovery_end`
  - `hvac_2f_recovery_end`
  - `csv_daily_report`
  - `csv_monthly_report`

### Note
Historical rows already written before this hardening may still contain inaccurate values. New rows written after this change use the corrected pipeline and guards.
