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
- `sensor.hvac_furnace_runtime_week` - Rolling 7-day furnace runtime (hours)
- `sensor.hvac_furnace_runtime_month` - Month-to-date furnace runtime (hours)
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

### Setback Optimization (Simplified)
- `input_boolean.hvac_1f_setback_active` / `hvac_2f_*` - Setback cycle latch (prevents re-firing)
- `input_datetime.hvac_1f_setback_start` / `hvac_2f_setback_start` - Setback start timestamp
- `input_number.hvac_1f_setback_start_runtime` / `hvac_2f_*` - Furnace runtime at setback start (min)
- `input_number.hvac_1f_hold_setpoint` / `hvac_2f_*` - Comfort setpoint before setback
- `input_number.hvac_1f_setback_setpoint` / `hvac_2f_*` - Setback setpoint
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
| furnace_runtime_hours | sensor.hvac_furnace_runtime_month |
| avg_runtime_per_hdd | sensor.runtime_per_hdd_month_calc (monthly calculation) |
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
- `sensor.runtime_per_hdd_month_calc` - Monthly runtime per HDD (min/HDD)

### Setback Optimization Log (`reports/hvac_setback_log.csv`)
Captured at recovery_end for each zone. Used to empirically optimize setback temps by outdoor low.

| Field | Source |
|-------|--------|
| date | Current date |
| zone | 1F or 2F |
| overnight_low | input_number.outdoor_temp_daily_low (actual observed) |
| setback_depth | hold_setpoint - setback_setpoint (°F) |
| total_runtime_min | Furnace runtime from setback start to recovery end |

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

### New Approach: Empirical Data Collection
Replaced with simple logging to enable direct observation of what works:

**New CSV Log** (`reports/hvac_setback_log.csv`):
| date | zone | overnight_low | setback_depth | total_runtime_min |

**Recommendation Sensor** (`sensor.recommended_setback_depth`):
Based on Pirate Weather forecast low temperature:
- Low > 30°F → 5°F setback (deeper saves gas)
- Low 15-30°F → 3°F setback (balanced)
- Low < 15°F → 1°F setback (avoid recovery penalty)

Thresholds can be adjusted as empirical data is collected.

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
3. **Recovery starts**: When gap > 2°F based on live setpoint (detects thermostat calling for heat)
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
