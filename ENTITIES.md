# HA ENTITIES — home-assistant-config

Read this file before referencing any entity not in §FRAGILE (CLAUDE.md).
Run impact scan after looking up any entity: `grep -rnw . -e '<entity_id>'`

## THERMOSTATS
```
climate.tstat_2d884c_lyric_t6_pro_thermostat     1F
climate.tstat_2d8878_lyric_t6_pro_thermostat     2F
```

## WEATHER
```
sensor.outdoor_temp_live                         Open-Meteo 10-min
sensor.hvac_outdoor_temp_hartford_proxy          combined source (Live>Pirate>NWS>Open-Meteo)
weather.local_weather_2                          NWS/NOAA  [_2 FRAGILE]
weather.home / weather.pirateweather
sensor.pirate_weather_*                          28 sensors — never infer; verify exact IDs in automations.yaml
```

## HDD/CDD
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

## CLIMATE NORMS
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

## ENERGY METRICS
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

## DHW ARCHIVES
```
input_number.dhw_archive_jan … dhw_archive_dec
input_number.dhw_bill_thm                        entry field (Therms → auto CCF)
input_button.save_dhw
```

## ELECTRIC BILL ARCHIVES
```
input_button.save_electric_bill
input_datetime.electricity_bill_date
input_number.electricity_bill_amount / _previous / _last_year
input_number.electricity_bill_days / _previous
input_number.electricity_bill_kwh / _previous / _last_year
```

## GAS BILL ARCHIVES
```
input_button.save_gas_bill
input_datetime.gas_bill_date
input_number.gas_bill_amount / _previous / _last_year
input_number.gas_bill_days / _previous
input_number.gas_bill_ccf / _previous / _last_year
```

## FILTER
```
input_number.hvac_filter_runtime_hours
sensor.hvac_filter_hours_remaining
input_datetime.hvac_filter_last_changed
input_button.reset_filter_runtime
binary_sensor.hvac_filter_change_alert           fires at >= 1000 hrs
```

## EFFICIENCY MONITORING
```
sensor.hvac_runtime_per_hdd_7_day_2              [_2 FRAGILE] primary operational metric
sensor.hvac_total_runtime_per_hdd_today
sensor.hvac_1f_runtime_per_hdd_today
sensor.hvac_2f_runtime_per_hdd_today
binary_sensor.hvac_runtime_per_hdd_high_alert    >mean+2σ
binary_sensor.hvac_runtime_per_hdd_low_alert     <mean-2σ
```

## FURNACE CYCLE TRACKING
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
sensor.hvac_total_cycles_today / _week / _month
sensor.hvac_1f_heat_cycles_today / hvac_1f_heat_runtime_today
sensor.hvac_2f_heat_cycles_today / hvac_2f_heat_runtime_today
sensor.hvac_total_heat_runtime_today
sensor.hvac_zone_balance_ratio_today
sensor.hvac_1f_heat_cycles_month_2               [_2 FRAGILE]
sensor.hvac_2f_heat_cycles_month_2               [_2 FRAGILE]
```

## RUNTIME/HDD STATISTICS
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

## MONTHLY REPORT
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

## SETBACK RECOVERY (state machine: IDLE→SETBACK_ACTIVE→RECOVERING→IDLE)
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

## DEHUMIDIFIER
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

## MISC
```
sensor.hvac_daily_gas_cost_estimate / _electric_cost_estimate / _total_cost_estimate
input_boolean.ha_maintenance_mode                 PENDING CREATION — gate for all shell_command calls
counter.automation_failures_24h / input_text.last_automation_failure
binary_sensor.hdd_capture_stale / runtime_per_hdd_capture_stale / furnace_cycle_capture_stale
binary_sensor.monthly_report_stale / climate_norms_stale
```

## UPS (DIY LiFePO4 — Shelly Plus Uni)
```
sensor.shelly_plus_uni_voltge                     [INTENTIONAL TYPO — DO NOT CORRECT] battery/bus voltage 0–30V
sensor.shelly_plus_uni_temperature                DS18B20 ambient
binary_sensor.shelly_plus_uni_input               grid power presence (Pololu diode input)
```
Note: input_boolean.ups_* IDs pending confirmation — do not reference in any automation until listed here.
Note: Computer Kasa plug entity IDs pending confirmation — do not infer or fabricate.

## ADDING ENTITIES
New entity → add here in same commit. Update CLAUDE.md §FRAGILE only if _2 suffix.
