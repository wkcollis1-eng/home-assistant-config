# ENTITIES — GENERATED, DO NOT EDIT

Written by `scripts/gen_reference.py` from `.storage/core.entity_registry`,
the YAML helper declarations, and `pipelines.yaml`. Hand edits are lost on
the next run and `ha_audit.py` FAILs when this file is stale.

To change an annotation, edit `entity_notes.yaml` and regenerate. An id that
disappears from the registry is dropped here automatically — which is the
whole point: the 2026-08-22 audit found 16 of 328 hand-listed ids did not
exist, two of them behind alerts that could never fire.

**Resolution order when you need an entity id: this file, then the registry.
Never from memory, and never inferred from a pattern.**

## AUDIT (packages/audit.yaml)

```
automation.nightly_ha_audit       00:30, guarded
binary_sensor.ha_audit_failing    problem; fail_count > 0
binary_sensor.ha_audit_stale      problem; no run in >2 days
input_datetime.ha_audit_last_run
input_number.ha_audit_fail_count
input_number.ha_audit_warn_count
script.ha_audit                   "Run HA Audit" — the one to call
```

## BACKUP SIZING (packages/backup_sizing.yaml)

```
input_button.reset_load_peaks            press after the first real heat call
sensor.backup_essentials_avg_24h         THE runtime number; time-weighted, from the integral
sensor.backup_essentials_energy          integration of essentials; power*dt, every ~2 s
sensor.backup_essentials_energy_rate     change_second, kWh/s; precision 12 or it reads 0
sensor.backup_essentials_energy_sampled  1/min sample of a CUMULATIVE total - lossless
sensor.backup_essentials_load            fridge+furnace+counter2+hwh recirc; attr amps_at_12v
sensor.backup_essentials_mean_24h        SUPERSEDED by backup_essentials_avg_24h; point-samples power
sensor.backup_essentials_peak_watts      THE inverter-sizing number; attr amps_at_12v
sensor.backup_essentials_sampled         1/min sample so the 24h buffer is 1440 not 43200
sensor.basement_router_peak_watts        latching peak; counted via monitoring_load since P16
sensor.coffee_maker_peak_watts           Counter 2; resistive, no inrush
sensor.fridge_peak_watts                 inrush 18-21x running, caught by luck
sensor.furnace_peak_watts                AUGUST VALUE IS COOLING BLOWER, not heat
sensor.hwh_recirc_peak_watts             smart plug on the RECIRC PUMP, not a tank
sensor.monitoring_load                   HA host + UPS outlet + router; runs the WHOLE outage
sensor.monitoring_peak_watts             flat load, peak is near running
```

## CLIMATE NORMS

```
binary_sensor.climate_adjusted_efficiency_alert
binary_sensor.climate_cold_snap_today
sensor.climate_norms_status
sensor.climate_norms_today
sensor.efficiency_deviation_index
sensor.expected_cdd_today
sensor.expected_hdd_today
sensor.expected_runtime_today
sensor.expected_temperature_today
sensor.hdd_deviation_today
```

## DAILY COST

```
sensor.hvac_daily_electric_cost_estimate
sensor.hvac_daily_gas_cost_estimate
sensor.hvac_daily_total_cost_estimate
```

## DEHUMIDIFIER (configuration.yaml)

```
binary_sensor.dehumidifier_should_run
counter.dehumidifier_cycles_today                [pipeline: capture_daily_dehumidifier_watts]
input_datetime.dehumidifier_cycle_start_time
input_datetime.dehumidifier_last_cycle_end_time
input_number.dehumidifier_cycle_start_dp
input_number.dehumidifier_last_cycle_minutes
input_number.dehumidifier_last_hold_hours
input_number.dehumidifier_last_pull_down_rate
input_number.dehumidifier_rh_off_threshold       default 46%
input_number.dehumidifier_rh_on_threshold        default 49%
input_select.dehumidifier_last_stop_reason       conditions_cleared|max_runtime
sensor.basement_dew_point
sensor.dehumidifier_avg_cycle_minutes
sensor.dehumidifier_current
sensor.dehumidifier_dew_point_margin
sensor.dehumidifier_duty_cycle_24h
sensor.dehumidifier_hold_time                    only valid for conditions_cleared stops
sensor.dehumidifier_pull_down_rate
sensor.dehumidifier_runtime_today
sensor.dehumidifier_runtime_week
sensor.shelly_temperature_humidity_humidity
sensor.shelly_temperature_humidity_temperature
switch.dehumidifier
```

## DHW ARCHIVES

```
input_number.dhw_bill_thm  entry field (Therms → auto CCF)
```

## EFFICIENCY MONITORING

```
binary_sensor.hvac_runtime_per_hdd_high_alert  >mean+2σ
binary_sensor.hvac_runtime_per_hdd_low_alert   <mean-2σ
sensor.hvac_1f_runtime_per_hdd_today
sensor.hvac_2f_runtime_per_hdd_today
sensor.hvac_runtime_per_hdd_7_day              [_2 FRAGILE] primary operational metric
sensor.hvac_total_runtime_per_hdd_today
```

## ENERGY METRICS

```
sensor.dhw_gas_12m
sensor.gas_dhw_usage_month
sensor.gas_heating_usage_month
sensor.hvac_building_load_ua_12m
sensor.hvac_building_load_ua_estimate
sensor.hvac_heating_efficiency_12m
sensor.hvac_heating_efficiency_mtd
sensor.site_eui_estimate
```

## FILTER

```
binary_sensor.hvac_filter_change_alert   fires at >= 1000 hrs
input_datetime.hvac_filter_last_changed
input_number.hvac_filter_runtime_hours
sensor.hvac_filter_hours_remaining
```

## FURNACE CYCLE TRACKING

```
binary_sensor.hvac_furnace_running
binary_sensor.hvac_furnace_short_cycling_alert  suppressed during recovery
sensor.hvac_chaining_index
sensor.hvac_chaining_index_month
sensor.hvac_chaining_index_week
sensor.hvac_furnace_cycle_data_count
sensor.hvac_furnace_cycle_lower_bound
sensor.hvac_furnace_cycle_mean_7d
sensor.hvac_furnace_cycle_sigma_7d
sensor.hvac_furnace_cycle_upper_bound
sensor.hvac_furnace_cycles_month_2              [_2 FRAGILE]
sensor.hvac_furnace_cycles_per_day_month
sensor.hvac_furnace_cycles_per_day_week
sensor.hvac_furnace_cycles_today
sensor.hvac_furnace_cycles_week
sensor.hvac_furnace_min_per_cycle
sensor.hvac_furnace_min_per_cycle_month
sensor.hvac_furnace_min_per_cycle_week
sensor.hvac_furnace_runtime_month_2             [_2 FRAGILE]
sensor.hvac_furnace_runtime_today
sensor.hvac_furnace_runtime_week
sensor.hvac_total_cycles_month
sensor.hvac_total_cycles_week
sensor.hvac_zone_overlap_month
sensor.hvac_zone_overlap_percent
sensor.hvac_zone_overlap_today
sensor.hvac_zone_overlap_week
```

## GUARDS / MODES

```
input_boolean.ha_maintenance_mode  gate for all shell_command calls
```

## HDD/CDD

```
input_number.hdd_cumulative_month_auto  [pipeline: capture_daily_monthly_tracking]
input_number.hdd_cumulative_year_auto   [pipeline: capture_daily_monthly_tracking]
sensor.hdd_rolling_7_day_auto_2         [_2 FRAGILE]
sensor.hvac_cdd65_today                 [pipeline: capture_daily_cooling_kwh_cdd]
sensor.hvac_hdd65_today
```

## HVAC COOLING EFFICIENCY (configuration.yaml)

```
sensor.hvac_ac_blower_energy  cumulative kWh (integration sensor)
sensor.hvac_ac_blower_power   furnace power when AC >100W, else 0
```

## KASA PLUGS

```
sensor.basement_router_today_s_consumption
sensor.computer_outlet_today_s_consumption
sensor.dehumidifier_energy
sensor.hwh_current_consumption
sensor.hwh_today_s_consumption                            Hot Water Heater (Basement)
sensor.living_room_tv_sonos_homatics_today_s_consumption
sensor.tv_room_today_s_consumption
```

## KNOWN ISSUES

```
sensor.furnace_running_watts_daily  was unavailable — fixed 2026-07-20 (threshold + capture stamp)
```

## MONTHLY REPORT

```
sensor.efficiency_deviation_month
sensor.expected_runtime_month
sensor.hvac_runtime_per_hdd_month
sensor.outdoor_temp_mean_month
```

## RUNTIME/HDD STATISTICS

```
sensor.hvac_runtime_per_hdd_7_day_mean      [_2 FRAGILE]
sensor.hvac_runtime_per_hdd_7_day_std_dev   [_2 FRAGILE]
sensor.hvac_runtime_per_hdd_data_count      alerts suppressed if <4
sensor.hvac_runtime_per_hdd_lower_bound_1s
sensor.hvac_runtime_per_hdd_upper_bound_1s
```

## SDR ELECTRIC — SEM CROSS-CHECK (packages/utility_meters.yaml)

```
sensor.utility_electric_power_avg   60 min mean W from the COUNTER; use this for the SEM check
sensor.utility_electric_power_rate  statistics change_second, kWh/s; precision 9 or it reads 0.0
```

## SDR WATER METER — R900 (packages/utility_meters.yaml)

```
automation.sdr_water_meter_leak_flag_set     Leak day-bins; OUTAGE BACKSTOP
automation.sdr_water_meter_leak_now          LeakNow; the immediate path, to phone
automation.sdr_water_meter_leak_now_cleared  says when it ends
binary_sensor.water_meter_stale              no decode in > sdr_water_stale_minutes
input_number.sdr_leak_now_hold_minutes       default 10 (~5 frames at 112 s)
sensor.electric_meter_ert_type
sensor.electric_meter_tamper_enc
sensor.electric_meter_tamper_phy
sensor.gas_meter_ert_type
sensor.gas_meter_tamper_enc
sensor.gas_meter_tamper_phy                  SCM; watch for a CHANGE, never the value
sensor.water_meter_age                       minutes since last decode
sensor.water_meter_backflow                  BackFlow, 2 bits, past 35 d 0-3
sensor.water_meter_leak                      Leak, 4 bits, day bins / 35 d
sensor.water_meter_leak_now                  LeakNow, 2 bits, past 24 h 0-3
sensor.water_meter_no_use                    NoUse, 6 bits — ENCODING UNCONFIRMED,
sensor.water_meter_reading                   rtlamr2mqtt; carries the whole
sensor.water_meter_volume                    reading x water_meter_scale, gal  [pipeline: capture_daily_water_overnight]
```

## SDR WATER — OVERNIGHT MINIMUM FLOW (packages/utility_meters.yaml)

```
automation.capture_daily_water_overnight_min    00/01/02/03/04/05 :00:45
binary_sensor.water_overnight_capture_stale     problem; no capture in > 2 days  [pipeline: capture_daily_water_overnight]
binary_sensor.water_overnight_leak_suspected    problem; min > threshold
binary_sensor.water_softener_regen_last_night   max > threshold
input_datetime.water_overnight_capture_last_ok  [pipeline: capture_daily_water_overnight]
input_number.water_overnight_leak_threshold     default 0.25 (above today's 0.10)
input_number.water_overnight_min_bins           default 3
input_number.water_regen_threshold_gal          default 15
sensor.water_overnight_bins                     valid bins last night (need 3 of 5)
sensor.water_overnight_max_flow                 busiest bin = the softener regen
sensor.water_overnight_min_flow                 last night's minimum hourly bin  [pipeline: capture_daily_water_overnight]
sensor.water_overnight_min_mean_7d              the TREND - this is the instrument  [pipeline: capture_daily_water_overnight]
```

## SEM METER (packages/sem_meter.yaml)

```
sensor.sem_ac_current
sensor.sem_line_voltage
sensor.sem_other_power             whole_home minus branch sum
sensor.sem_whole_home_power_10min  matched partner for utility_electric_power_clean
```

## SETBACK RECOVERY (state machine: IDLE→SETBACK_ACTIVE→RECOVERING→IDLE)

```
sensor.recommended_setback_depth
```

## SPC — AC (packages/spc.yaml)

```
binary_sensor.ac_watts_out_of_control
binary_sensor.hvac_ac_running
input_datetime.ac_spc_last_capture     measured captures only  [pipeline: capture_daily_ac_watts]
input_datetime.ac_spc_last_seed        startup seed, never a capture  [pipeline: capture_daily_ac_watts]
input_number.ac_power_threshold        default 300W
sensor.ac_running_watts_24h            statistics; unavailable while AC is off  [pipeline: capture_daily_ac_watts]
sensor.ac_running_watts_daily
sensor.ac_running_watts_latched        last numeric 24h mean; what the capture guard reads  [pipeline: capture_daily_ac_watts]
sensor.ac_running_watts_lower          [pipeline: capture_daily_ac_watts]
sensor.ac_running_watts_mean_7d        [pipeline: capture_daily_ac_watts]
sensor.ac_running_watts_sigma_7d       [pipeline: capture_daily_ac_watts]
sensor.ac_running_watts_upper          [pipeline: capture_daily_ac_watts]
sensor.ac_runtime_today                [pipeline: capture_daily_ac_watts]
```

## SPC — CAPTURE WATCHDOG (packages/spc.yaml)

```
automation.notify_spc_capture_stale              persistent_notification, 2h debounce
binary_sensor.ac_spc_capture_stale               season-aware via runtime_today  [pipeline: capture_daily_ac_watts]
binary_sensor.cooling_kwh_cdd_spc_capture_stale  gated on sensor.hvac_cdd65_today  [pipeline: capture_daily_cooling_kwh_cdd]
binary_sensor.dehumidifier_spc_capture_stale     gated on counter.dehumidifier_cycles_today  [pipeline: capture_daily_dehumidifier_watts]
binary_sensor.fridge_spc_capture_stale           on = ran today, no capture in >2 days  [pipeline: capture_daily_fridge_watts]
binary_sensor.furnace_spc_capture_stale          season-aware via runtime_today  [pipeline: capture_daily_furnace_watts]
binary_sensor.hwh_recirc_spc_capture_stale       [pipeline: capture_daily_hwh_recirc_watts]
binary_sensor.spc_capture_stale_any              roll-up; attr stale_populations
```

## SPC — COOLING EFFICIENCY (packages/spc.yaml)

```
binary_sensor.cooling_kwh_cdd_out_of_control
input_datetime.cooling_kwh_cdd_spc_last_capture  [pipeline: capture_daily_cooling_kwh_cdd]
sensor.cooling_kwh_cdd_daily
sensor.cooling_kwh_cdd_lower                     [pipeline: capture_daily_cooling_kwh_cdd]
sensor.cooling_kwh_cdd_mean_7d                   [pipeline: capture_daily_cooling_kwh_cdd]
sensor.cooling_kwh_cdd_sigma_7d                  [pipeline: capture_daily_cooling_kwh_cdd]
sensor.cooling_kwh_cdd_upper                     [pipeline: capture_daily_cooling_kwh_cdd]
```

## SPC — DEHUMIDIFIER (packages/spc.yaml)

```
binary_sensor.dehumidifier_watts_out_of_control
input_datetime.dehumidifier_spc_last_capture     measured captures only  [pipeline: capture_daily_dehumidifier_watts]
input_datetime.dehumidifier_spc_last_seed        startup seed, never a capture  [pipeline: capture_daily_dehumidifier_watts]
sensor.dehumidifier_power_when_on                raw watts, gated on > power_threshold
sensor.dehumidifier_power_when_on_steady         raw watts, gated to minutes 10-14 of a run
sensor.dehumidifier_run_elapsed                  minutes into current run; 0 when compressor off
sensor.dehumidifier_running_watts_24h            statistics, full-run (diagnostic only)
sensor.dehumidifier_running_watts_daily
sensor.dehumidifier_running_watts_latched        last numeric steady-window mean; capture guard reads this.  [pipeline: capture_daily_dehumidifier_watts]
sensor.dehumidifier_running_watts_lower          [pipeline: capture_daily_dehumidifier_watts]
sensor.dehumidifier_running_watts_mean_7d        [pipeline: capture_daily_dehumidifier_watts]
sensor.dehumidifier_running_watts_sigma_7d       [pipeline: capture_daily_dehumidifier_watts]
sensor.dehumidifier_running_watts_steady_24h     statistics on the steady gate; feeds the latch  [pipeline: capture_daily_dehumidifier_watts]
sensor.dehumidifier_running_watts_upper          [pipeline: capture_daily_dehumidifier_watts]
sensor.dehumidifier_startup_deficit              steady_24h minus 24h; control-mode signature, not a fault
sensor.dehumidifier_steady_sample_count_24h      samples behind the steady mean
```

## SPC — FRIDGE (packages/spc.yaml)

```
binary_sensor.fridge_compressor_running
binary_sensor.fridge_watts_out_of_control
input_datetime.fridge_spc_last_capture     measured captures only  [pipeline: capture_daily_fridge_watts]
input_datetime.fridge_spc_last_seed        startup seed, never a capture  [pipeline: capture_daily_fridge_watts]
input_number.fridge_power_threshold        default 50W
sensor.fridge_running_watts_24h            statistics; unavailable while fridge is off  [pipeline: capture_daily_fridge_watts]
sensor.fridge_running_watts_daily
sensor.fridge_running_watts_latched        last numeric 24h mean; what the capture guard reads  [pipeline: capture_daily_fridge_watts]
sensor.fridge_running_watts_lower          [pipeline: capture_daily_fridge_watts]
sensor.fridge_running_watts_mean_7d        [pipeline: capture_daily_fridge_watts]
sensor.fridge_running_watts_sigma_7d       [pipeline: capture_daily_fridge_watts]
sensor.fridge_running_watts_upper          [pipeline: capture_daily_fridge_watts]
sensor.fridge_runtime_today                [pipeline: capture_daily_fridge_watts]
```

## SPC — FURNACE (packages/spc.yaml)

```
binary_sensor.furnace_watts_out_of_control
input_datetime.furnace_spc_last_capture     measured captures only  [pipeline: capture_daily_furnace_watts]
input_datetime.furnace_spc_last_seed        startup seed, never a capture  [pipeline: capture_daily_furnace_watts]
input_number.furnace_power_threshold        default 300W
sensor.furnace_running_watts_24h            statistics; unavailable while blower is off  [pipeline: capture_daily_furnace_watts]
sensor.furnace_running_watts_latched        last numeric 24h mean; what the capture guard reads  [pipeline: capture_daily_furnace_watts]
sensor.furnace_running_watts_lower          [pipeline: capture_daily_furnace_watts]
sensor.furnace_running_watts_mean_7d        [pipeline: capture_daily_furnace_watts]
sensor.furnace_running_watts_sigma_7d       [pipeline: capture_daily_furnace_watts]
sensor.furnace_running_watts_upper          [pipeline: capture_daily_furnace_watts]
sensor.furnace_runtime_today                [pipeline: capture_daily_furnace_watts]
```

## SPC — HWH RECIRC (packages/spc.yaml)

```
binary_sensor.hwh_recirc_pump_running
binary_sensor.hwh_recirc_watts_out_of_control
input_datetime.hwh_recirc_spc_last_capture     measured captures only  [pipeline: capture_daily_hwh_recirc_watts]
input_datetime.hwh_recirc_spc_last_seed        startup seed, never a capture  [pipeline: capture_daily_hwh_recirc_watts]
input_number.hwh_recirc_power_threshold        default 70W
sensor.hwh_recirc_running_watts_24h            statistics; unavailable while pump is off  [pipeline: capture_daily_hwh_recirc_watts]
sensor.hwh_recirc_running_watts_daily
sensor.hwh_recirc_running_watts_latched        last numeric 24h mean; what the capture guard reads  [pipeline: capture_daily_hwh_recirc_watts]
sensor.hwh_recirc_running_watts_lower          [pipeline: capture_daily_hwh_recirc_watts]
sensor.hwh_recirc_running_watts_mean_7d        [pipeline: capture_daily_hwh_recirc_watts]
sensor.hwh_recirc_running_watts_sigma_7d       [pipeline: capture_daily_hwh_recirc_watts]
sensor.hwh_recirc_running_watts_upper          [pipeline: capture_daily_hwh_recirc_watts]
sensor.hwh_recirc_runtime_today                [pipeline: capture_daily_hwh_recirc_watts]
```

## SYSTEM (configuration.yaml / packages/spc.yaml)

```
automation.nightly_rolling_buffer_backup  00:20, guarded
```

## THERMOSTATS (Ecobee — replaced Honeywell T6 Pro June 2026)

```
climate.main_floor                     1F Ecobee
climate.upstairs                       2F Ecobee
sensor.main_floor_current_temperature  1F current temp (watchdog monitored)
sensor.upstairs_current_temperature    2F current temp (watchdog monitored)
```

## WATCHDOG (packages/watchdog.yaml)

```
binary_sensor.watchdog_battery_bank_stale        Battery Bank monitor stale detection
binary_sensor.watchdog_ecobee_stale              Ecobee temps stale (either sensor)
binary_sensor.watchdog_sem_stale                 SEM Meter stale detection
binary_sensor.watchdog_ups_stale                 UPS monitor stale detection
input_boolean.watchdog_auto_reload_battery_bank  Enable auto-reload
input_boolean.watchdog_auto_reload_ecobee
input_boolean.watchdog_auto_reload_sem
input_boolean.watchdog_auto_reload_ups
input_number.watchdog_reload_backoff             Reload backoff period (minutes)
input_number.watchdog_threshold_battery_bank     Stale threshold (minutes)
input_number.watchdog_threshold_ecobee
input_number.watchdog_threshold_sem
input_number.watchdog_threshold_ups
script.spc_force_seed_all                        Force seed all SPC day slots from 24h stats
script.watchdog_reload_all_stale                 Manual reload all stale integrations
sensor.watchdog_stale_sensor_count               Count of stale systems
```

## WEATHER

```
sensor.hvac_outdoor_temp_hartford_proxy            combined source (Live>Pirate>NWS>Open-Meteo)
sensor.outdoor_temp_live                           Open-Meteo 10-min — authoritative CDD65 source
sensor.pirate_weather_cdd_forecast_today
sensor.pirate_weather_cloud_cover
sensor.pirate_weather_condition
sensor.pirate_weather_data_age
sensor.pirate_weather_dew_point
sensor.pirate_weather_feels_like
sensor.pirate_weather_hdd_forecast_7_day
sensor.pirate_weather_hdd_forecast_today
sensor.pirate_weather_hdd_forecast_tomorrow
sensor.pirate_weather_humidity
sensor.pirate_weather_ozone
sensor.pirate_weather_pressure
sensor.pirate_weather_temperature
sensor.pirate_weather_today_condition
sensor.pirate_weather_today_high
sensor.pirate_weather_today_low
sensor.pirate_weather_today_precip_probability
sensor.pirate_weather_tomorrow_condition
sensor.pirate_weather_tomorrow_high
sensor.pirate_weather_tomorrow_low
sensor.pirate_weather_tomorrow_precip_probability
sensor.pirate_weather_uv_index
sensor.pirate_weather_visibility
sensor.pirate_weather_wind_bearing
sensor.pirate_weather_wind_direction
sensor.pirate_weather_wind_speed
```

## UNDOCUMENTED — in pipelines.yaml, no note in entity_notes.yaml

```
binary_sensor.ac_cost_capture_stale                  [pipeline: capture_daily_ac_cost]
binary_sensor.ac_min_cycle_capture_stale             [pipeline: capture_daily_ac_min_per_cycle]
binary_sensor.cdd_capture_stale                      [pipeline: capture_daily_cdd]
binary_sensor.cdd_monthly_archive_stale              [pipeline: archive_monthly_cdd]
binary_sensor.dehumidifier_cost_capture_stale        [pipeline: capture_daily_dehumidifier_cost]
binary_sensor.dehumidifier_duty_kwh_capture_stale    [pipeline: capture_daily_dehumidifier_duty_kwh]
binary_sensor.furnace_cycle_capture_stale            [pipeline: capture_daily_furnace_min_per_cycle]
binary_sensor.gas_heat_cost_archive_stale            [pipeline: archive_monthly_gas_heat_cost]
binary_sensor.hdd_capture_stale                      [pipeline: capture_daily_hdd]
binary_sensor.hdd_monthly_archive_stale              [pipeline: archive_monthly_hdd]
binary_sensor.monthly_report_stale                   [pipeline: capture_daily_monthly_tracking]
binary_sensor.runtime_per_cdd_capture_stale          [pipeline: capture_daily_runtime_per_cdd]
binary_sensor.runtime_per_hdd_capture_stale          [pipeline: capture_daily_runtime_per_hdd]
input_datetime.ac_cost_capture_last_ok               [pipeline: capture_daily_ac_cost]
input_datetime.ac_min_per_cycle_capture_last_ok      [pipeline: capture_daily_ac_min_per_cycle]
input_datetime.cdd_archive_last_ok                   [pipeline: archive_monthly_cdd]
input_datetime.cdd_capture_last_ok                   [pipeline: capture_daily_cdd]
input_datetime.dehumidifier_cost_capture_last_ok     [pipeline: capture_daily_dehumidifier_cost]
input_datetime.dehumidifier_duty_kwh_capture_last_ok [pipeline: capture_daily_dehumidifier_duty_kwh]
input_datetime.furnace_cycle_capture_last_ok         [pipeline: capture_daily_furnace_min_per_cycle]
input_datetime.gas_heat_cost_archive_last_ok         [pipeline: archive_monthly_gas_heat_cost]
input_datetime.hdd_archive_last_ok                   [pipeline: archive_monthly_hdd]
input_datetime.hdd_capture_last_ok                   [pipeline: capture_daily_hdd]
input_datetime.monthly_tracking_capture_last_ok      [pipeline: capture_daily_monthly_tracking]
input_datetime.runtime_per_cdd_capture_last_ok       [pipeline: capture_daily_runtime_per_cdd]
input_datetime.runtime_per_hdd_capture_last_ok       [pipeline: capture_daily_runtime_per_hdd]
input_number.ac_cost_year_acc                        [pipeline: capture_daily_ac_cost]
input_number.ac_cycles_month_acc                     [pipeline: capture_daily_monthly_tracking]
input_number.ac_cycles_year_acc                      [pipeline: capture_daily_monthly_tracking]
input_number.ac_min_per_cycle_day_1                  [pipeline: capture_daily_ac_min_per_cycle]
input_number.ac_min_per_cycle_day_2                  [pipeline: capture_daily_ac_min_per_cycle]
input_number.ac_min_per_cycle_day_3                  [pipeline: capture_daily_ac_min_per_cycle]
input_number.ac_min_per_cycle_day_4                  [pipeline: capture_daily_ac_min_per_cycle]
input_number.ac_min_per_cycle_day_5                  [pipeline: capture_daily_ac_min_per_cycle]
input_number.ac_min_per_cycle_day_6                  [pipeline: capture_daily_ac_min_per_cycle]
input_number.ac_min_per_cycle_day_7                  [pipeline: capture_daily_ac_min_per_cycle]
input_number.ac_running_watts_day_1                  [pipeline: capture_daily_ac_watts]
input_number.ac_running_watts_day_2                  [pipeline: capture_daily_ac_watts]
input_number.ac_running_watts_day_3                  [pipeline: capture_daily_ac_watts]
input_number.ac_running_watts_day_4                  [pipeline: capture_daily_ac_watts]
input_number.ac_running_watts_day_5                  [pipeline: capture_daily_ac_watts]
input_number.ac_running_watts_day_6                  [pipeline: capture_daily_ac_watts]
input_number.ac_running_watts_day_7                  [pipeline: capture_daily_ac_watts]
input_number.ac_runtime_month_acc                    [pipeline: capture_daily_monthly_tracking]
input_number.ac_runtime_year_acc                     [pipeline: capture_daily_monthly_tracking]
input_number.cdd_cumulative_month_auto               [pipeline: capture_daily_monthly_tracking]
input_number.cdd_cumulative_year_auto                [pipeline: capture_daily_monthly_tracking]
input_number.cdd_day_1                               [pipeline: capture_daily_cdd]
input_number.cdd_day_2                               [pipeline: capture_daily_cdd]
input_number.cdd_day_3                               [pipeline: capture_daily_cdd]
input_number.cdd_day_4                               [pipeline: capture_daily_cdd]
input_number.cdd_day_5                               [pipeline: capture_daily_cdd]
input_number.cdd_day_6                               [pipeline: capture_daily_cdd]
input_number.cdd_day_7                               [pipeline: capture_daily_cdd]
input_number.cooling_kwh_cdd_day_1                   [pipeline: capture_daily_cooling_kwh_cdd]
input_number.cooling_kwh_cdd_day_2                   [pipeline: capture_daily_cooling_kwh_cdd]
input_number.cooling_kwh_cdd_day_3                   [pipeline: capture_daily_cooling_kwh_cdd]
input_number.cooling_kwh_cdd_day_4                   [pipeline: capture_daily_cooling_kwh_cdd]
input_number.cooling_kwh_cdd_day_5                   [pipeline: capture_daily_cooling_kwh_cdd]
input_number.cooling_kwh_cdd_day_6                   [pipeline: capture_daily_cooling_kwh_cdd]
input_number.cooling_kwh_cdd_day_7                   [pipeline: capture_daily_cooling_kwh_cdd]
input_number.dehumidifier_cost_year_acc              [pipeline: capture_daily_dehumidifier_cost]
input_number.dehumidifier_duty_day_1                 [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_duty_day_2                 [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_duty_day_3                 [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_duty_day_4                 [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_duty_day_5                 [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_duty_day_6                 [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_duty_day_7                 [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_kwh_day_1                  [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_kwh_day_2                  [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_kwh_day_3                  [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_kwh_day_4                  [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_kwh_day_5                  [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_kwh_day_6                  [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_kwh_day_7                  [pipeline: capture_daily_dehumidifier_duty_kwh]
input_number.dehumidifier_running_watts_day_1        [pipeline: capture_daily_dehumidifier_watts]
input_number.dehumidifier_running_watts_day_2        [pipeline: capture_daily_dehumidifier_watts]
input_number.dehumidifier_running_watts_day_3        [pipeline: capture_daily_dehumidifier_watts]
input_number.dehumidifier_running_watts_day_4        [pipeline: capture_daily_dehumidifier_watts]
input_number.dehumidifier_running_watts_day_5        [pipeline: capture_daily_dehumidifier_watts]
input_number.dehumidifier_running_watts_day_6        [pipeline: capture_daily_dehumidifier_watts]
input_number.dehumidifier_running_watts_day_7        [pipeline: capture_daily_dehumidifier_watts]
input_number.expected_runtime_sum_month              [pipeline: capture_daily_monthly_tracking]
input_number.fridge_running_watts_day_1              [pipeline: capture_daily_fridge_watts]
input_number.fridge_running_watts_day_2              [pipeline: capture_daily_fridge_watts]
input_number.fridge_running_watts_day_3              [pipeline: capture_daily_fridge_watts]
input_number.fridge_running_watts_day_4              [pipeline: capture_daily_fridge_watts]
input_number.fridge_running_watts_day_5              [pipeline: capture_daily_fridge_watts]
input_number.fridge_running_watts_day_6              [pipeline: capture_daily_fridge_watts]
input_number.fridge_running_watts_day_7              [pipeline: capture_daily_fridge_watts]
input_number.furnace_cycles_month_acc                [pipeline: capture_daily_monthly_tracking]
input_number.furnace_min_per_cycle_day_1             [pipeline: capture_daily_furnace_min_per_cycle]
input_number.furnace_min_per_cycle_day_2             [pipeline: capture_daily_furnace_min_per_cycle]
input_number.furnace_min_per_cycle_day_3             [pipeline: capture_daily_furnace_min_per_cycle]
input_number.furnace_min_per_cycle_day_4             [pipeline: capture_daily_furnace_min_per_cycle]
input_number.furnace_min_per_cycle_day_5             [pipeline: capture_daily_furnace_min_per_cycle]
input_number.furnace_min_per_cycle_day_6             [pipeline: capture_daily_furnace_min_per_cycle]
input_number.furnace_min_per_cycle_day_7             [pipeline: capture_daily_furnace_min_per_cycle]
input_number.furnace_running_watts_day_1             [pipeline: capture_daily_furnace_watts]
input_number.furnace_running_watts_day_2             [pipeline: capture_daily_furnace_watts]
input_number.furnace_running_watts_day_3             [pipeline: capture_daily_furnace_watts]
input_number.furnace_running_watts_day_4             [pipeline: capture_daily_furnace_watts]
input_number.furnace_running_watts_day_5             [pipeline: capture_daily_furnace_watts]
input_number.furnace_running_watts_day_6             [pipeline: capture_daily_furnace_watts]
input_number.furnace_running_watts_day_7             [pipeline: capture_daily_furnace_watts]
input_number.furnace_runtime_month_acc               [pipeline: capture_daily_monthly_tracking]
input_number.hdd_day_1                               [pipeline: capture_daily_hdd]
input_number.hdd_day_2                               [pipeline: capture_daily_hdd]
input_number.hdd_day_3                               [pipeline: capture_daily_hdd]
input_number.hdd_day_4                               [pipeline: capture_daily_hdd]
input_number.hdd_day_5                               [pipeline: capture_daily_hdd]
input_number.hdd_day_6                               [pipeline: capture_daily_hdd]
input_number.hdd_day_7                               [pipeline: capture_daily_hdd]
input_number.hwh_recirc_running_watts_day_1          [pipeline: capture_daily_hwh_recirc_watts]
input_number.hwh_recirc_running_watts_day_2          [pipeline: capture_daily_hwh_recirc_watts]
input_number.hwh_recirc_running_watts_day_3          [pipeline: capture_daily_hwh_recirc_watts]
input_number.hwh_recirc_running_watts_day_4          [pipeline: capture_daily_hwh_recirc_watts]
input_number.hwh_recirc_running_watts_day_5          [pipeline: capture_daily_hwh_recirc_watts]
input_number.hwh_recirc_running_watts_day_6          [pipeline: capture_daily_hwh_recirc_watts]
input_number.hwh_recirc_running_watts_day_7          [pipeline: capture_daily_hwh_recirc_watts]
input_number.outdoor_temp_days_month                 [pipeline: capture_daily_monthly_tracking]
input_number.outdoor_temp_sum_month                  [pipeline: capture_daily_monthly_tracking]
input_number.runtime_per_cdd_day_1                   [pipeline: capture_daily_runtime_per_cdd]
input_number.runtime_per_cdd_day_2                   [pipeline: capture_daily_runtime_per_cdd]
input_number.runtime_per_cdd_day_3                   [pipeline: capture_daily_runtime_per_cdd]
input_number.runtime_per_cdd_day_4                   [pipeline: capture_daily_runtime_per_cdd]
input_number.runtime_per_cdd_day_5                   [pipeline: capture_daily_runtime_per_cdd]
input_number.runtime_per_cdd_day_6                   [pipeline: capture_daily_runtime_per_cdd]
input_number.runtime_per_cdd_day_7                   [pipeline: capture_daily_runtime_per_cdd]
input_number.runtime_per_hdd_day_1                   [pipeline: capture_daily_runtime_per_hdd]
input_number.runtime_per_hdd_day_2                   [pipeline: capture_daily_runtime_per_hdd]
input_number.runtime_per_hdd_day_3                   [pipeline: capture_daily_runtime_per_hdd]
input_number.runtime_per_hdd_day_4                   [pipeline: capture_daily_runtime_per_hdd]
input_number.runtime_per_hdd_day_5                   [pipeline: capture_daily_runtime_per_hdd]
input_number.runtime_per_hdd_day_6                   [pipeline: capture_daily_runtime_per_hdd]
input_number.runtime_per_hdd_day_7                   [pipeline: capture_daily_runtime_per_hdd]
input_number.water_night_bins                        [pipeline: capture_daily_water_overnight]
input_number.water_overnight_min_day_1               [pipeline: capture_daily_water_overnight]
input_number.water_overnight_min_day_2               [pipeline: capture_daily_water_overnight]
input_number.water_overnight_min_day_3               [pipeline: capture_daily_water_overnight]
input_number.water_overnight_min_day_4               [pipeline: capture_daily_water_overnight]
input_number.water_overnight_min_day_5               [pipeline: capture_daily_water_overnight]
input_number.water_overnight_min_day_6               [pipeline: capture_daily_water_overnight]
input_number.water_overnight_min_day_7               [pipeline: capture_daily_water_overnight]
input_number.zone_1f_cool_cycles_month_acc           [pipeline: capture_daily_monthly_tracking]
input_number.zone_1f_cool_runtime_month_acc          [pipeline: capture_daily_monthly_tracking]
input_number.zone_1f_cycles_month_acc                [pipeline: capture_daily_monthly_tracking]
input_number.zone_1f_runtime_month_acc               [pipeline: capture_daily_monthly_tracking]
input_number.zone_2f_cool_cycles_month_acc           [pipeline: capture_daily_monthly_tracking]
input_number.zone_2f_cool_runtime_month_acc          [pipeline: capture_daily_monthly_tracking]
input_number.zone_2f_cycles_month_acc                [pipeline: capture_daily_monthly_tracking]
input_number.zone_2f_runtime_month_acc               [pipeline: capture_daily_monthly_tracking]
sensor.sem_ac_daily                                  [pipeline: capture_daily_cooling_kwh_cdd]
```
