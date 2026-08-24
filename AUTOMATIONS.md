# AUTOMATIONS — GENERATED, DO NOT EDIT

Written by `scripts/gen_reference.py` from `automations.yaml` and every
`packages/*.yaml`. Replaced an 86-line hand-kept index in CLAUDE.md that
held nothing the config did not already state.

`[pipeline]` marks an automation declared in `pipelines.yaml`.

```
accumulate_filter_runtime              23:58:00                                                            single     automations.yaml
archive_monthly_cdd                    23:58:30                                                            single     automations.yaml  [pipeline]
archive_monthly_gas_heat_cost          state:input_button.save_gas_bill                                    single     automations.yaml  [pipeline]
archive_monthly_hdd                    23:58:15                                                            single     automations.yaml  [pipeline]
basement_th_node_offline               state:binary_sensor.basement_th_node_node_status +1 more            single     watchdog.yaml
basement_th_node_sensor_fault          state:binary_sensor.basement_th_node_basement_sensor_fault +1 more  single     watchdog.yaml
capture_daily_ac_cost                  23:59:45                                                            single     automations.yaml  [pipeline]
capture_daily_ac_min_per_cycle         23:55:30                                                            single     automations.yaml  [pipeline]
capture_daily_ac_watts                 23:59:00                                                            single     spc.yaml  [pipeline]
capture_daily_cdd                      23:55:15                                                            single     automations.yaml  [pipeline]
capture_daily_cooling_kwh_cdd          23:59:00                                                            single     spc.yaml  [pipeline]
capture_daily_dehumidifier_cost        23:59:30                                                            single     automations.yaml  [pipeline]
capture_daily_dehumidifier_duty_kwh    23:59:30                                                            single     automations.yaml  [pipeline]
capture_daily_dehumidifier_watts       23:59:00                                                            single     spc.yaml  [pipeline]
capture_daily_fridge_watts             23:59:00                                                            single     spc.yaml  [pipeline]
capture_daily_furnace_min_per_cycle    23:56:15                                                            single     automations.yaml  [pipeline]
capture_daily_furnace_watts            23:59:00                                                            single     spc.yaml  [pipeline]
capture_daily_hdd                      23:55:00                                                            single     automations.yaml  [pipeline]
capture_daily_hwh_recirc_watts         23:59:00                                                            single     spc.yaml  [pipeline]
capture_daily_monthly_tracking         23:56:30                                                            single     automations.yaml  [pipeline]
capture_daily_runtime_per_cdd          23:56:45                                                            single     automations.yaml  [pipeline]
capture_daily_runtime_per_hdd          23:56:00                                                            single     automations.yaml  [pipeline]
capture_daily_water_overnight          00:00:45, 01:00:45, 02:00:45, 03:00:45 +2 more                      single     utility_meters.yaml  [pipeline]
csv_daily_report                       23:57:00                                                            single     automations.yaml
csv_monthly_report                     23:58:45                                                            single     automations.yaml
csv_yearly_rotation                    00:03:00                                                            single     automations.yaml
daily_energy_csv_export                00:15:00                                                            single     energy_export_package.yaml
daily_hvac_summary                     22:00:00                                                            single     automations.yaml
database_maintenance_weekly            03:00:00                                                            single     automations.yaml
database_size_monitor                  05:00:00                                                            single     automations.yaml
dehumidifier_auto_off                  time_pattern, template                                              single     automations.yaml
dehumidifier_auto_on                   state:binary_sensor.dehumidifier_should_run +1 more                 single     automations.yaml
dehumidifier_cycle_counter_reset       00:00:00                                                            single     automations.yaml
dehumidifier_cycle_end_capture         state:binary_sensor.dehumidifier_compressor_active                  single     automations.yaml
dehumidifier_cycle_start_capture       state:binary_sensor.dehumidifier_compressor_active                  single     automations.yaml
dehumidifier_force_on_backstop         numeric_state, numeric_state, time_pattern                          single     automations.yaml
dehumidifier_local_control_enter       state:input_boolean.dehumidifier_local_control                      single     automations.yaml
dehumidifier_local_control_exit        state:input_boolean.dehumidifier_local_control                      single     automations.yaml
dehumidifier_local_control_power_hold  state:input_boolean.dehumidifier_local_control +1 more              single     automations.yaml
dehumidifier_local_control_reminder    time_pattern                                                        single     automations.yaml
dehumidifier_max_runtime_backstop      time_pattern                                                        single     automations.yaml
dehumidifier_rh_stall_shutdown         time_pattern                                                        single     automations.yaml
dehumidifier_sensor_loss_shutdown      state:sensor.basement_th_node_basement_humidity +1 more             single     automations.yaml
dehumidifier_stamp_last_off            state:switch.dehumidifier                                           single     automations.yaml
dehumidifier_stamp_last_on             state:switch.dehumidifier                                           single     automations.yaml
hvac_1f_recovery_end                   template                                                            single     automations.yaml
hvac_1f_recovery_start                 template                                                            single     automations.yaml
hvac_1f_recovery_stuck_clear           state:input_boolean.hvac_1f_recovering                              single     automations.yaml
hvac_1f_setback_lowered                state:climate.main_floor                                            single     automations.yaml
hvac_1f_setback_start                  state:climate.main_floor                                            single     automations.yaml
hvac_1f_setback_stuck_clear            state:input_boolean.hvac_1f_setback_active                          single     automations.yaml
hvac_2f_recovery_end                   template                                                            single     automations.yaml
hvac_2f_recovery_start                 template                                                            single     automations.yaml
hvac_2f_recovery_stuck_clear           state:input_boolean.hvac_2f_recovering                              single     automations.yaml
hvac_2f_setback_lowered                state:climate.upstairs                                              single     automations.yaml
hvac_2f_setback_start                  state:climate.upstairs                                              single     automations.yaml
hvac_2f_setback_stuck_clear            state:input_boolean.hvac_2f_setback_active                          single     automations.yaml
hvac_setback_midnight_audit            01:00:00                                                            single     automations.yaml
nightly_buffer_backup                  00:20:00                                                            single     spc.yaml
nightly_ha_audit                       00:30:00                                                            single     audit.yaml
notify_ac_short_cycling                state:binary_sensor.hvac_ac_short_cycling_alert                     single     automations.yaml
notify_cdd_capture_stale               state:binary_sensor.cdd_capture_stale                               single     automations.yaml
notify_climate_norms_failure           state:sensor.climate_norms_today                                    single     automations.yaml
notify_climate_norms_stale             state:binary_sensor.climate_norms_stale                             single     automations.yaml
notify_filter_change_due               state:binary_sensor.hvac_filter_change_alert                        single     automations.yaml
notify_furnace_cycle_capture_stale     state:binary_sensor.furnace_cycle_capture_stale                     single     automations.yaml
notify_hdd_capture_stale               state:binary_sensor.hdd_capture_stale                               single     automations.yaml
notify_monthly_report_stale            state:binary_sensor.monthly_report_stale                            single     automations.yaml
notify_pirate_weather_stale            template                                                            single     automations.yaml
notify_runtime_per_cdd_capture_stale   state:binary_sensor.runtime_per_cdd_capture_stale                   single     automations.yaml
notify_runtime_per_cdd_high            state:binary_sensor.hvac_runtime_per_cdd_high_alert                 single     automations.yaml
notify_runtime_per_cdd_low             state:binary_sensor.hvac_runtime_per_cdd_low_alert                  single     automations.yaml
notify_runtime_per_hdd_capture_stale   state:binary_sensor.runtime_per_hdd_capture_stale                   single     automations.yaml
notify_runtime_per_hdd_high            state:binary_sensor.hvac_runtime_per_hdd_high_alert                 single     automations.yaml
notify_runtime_per_hdd_low             state:binary_sensor.hvac_runtime_per_hdd_low_alert                  single     automations.yaml
notify_short_cycling_furnace           state:binary_sensor.hvac_furnace_short_cycling_alert                single     automations.yaml
notify_spc_capture_stale               state:binary_sensor.spc_capture_stale_any                           single     spc.yaml
notify_thermostat_offline              state:climate.main_floor +1 more                                    single     automations.yaml
notify_weather_sources_down            state:sensor.hvac_outdoor_temp_hartford_proxy                       single     automations.yaml
reset_automation_failure_counter       00:00:00                                                            single     automations.yaml
reset_filter_runtime_button            state:input_button.reset_filter_runtime                             single     automations.yaml
reset_monthly_hdd                      00:01:00, homeassistant                                             single     automations.yaml
reset_outdoor_temp_daily_high_low      00:00:30, homeassistant                                             single     automations.yaml
reset_season_gas_heat_cost             00:08:00, homeassistant                                             single     automations.yaml
reset_yearly_ac_cost                   00:06:00, homeassistant                                             single     automations.yaml
reset_yearly_dehumidifier_cost         00:04:00, homeassistant                                             single     automations.yaml
reset_yearly_hdd                       00:02:00, homeassistant                                             single     automations.yaml
rotate_setback_log_yearly              00:05:00                                                            single     automations.yaml
save_dhw_button                        state:input_button.save_dhw                                         single     automations.yaml
save_electric_bill_button              state:input_button.save_electric_bill                               single     automations.yaml
save_gas_bill_button                   state:input_button.save_gas_bill                                    single     automations.yaml
sdr_meter_stale_alert                  state:binary_sensor.gas_meter_stale +2 more                         queued     utility_meters.yaml
sdr_water_leak_flag                    numeric_state                                                       single     utility_meters.yaml
sdr_water_leak_now                     numeric_state                                                       single     utility_meters.yaml
sdr_water_leak_now_cleared             numeric_state                                                       single     utility_meters.yaml
spc_seed_on_startup                    homeassistant                                                       single     spc.yaml
spc_seed_slots_manual                  -                                                                   single     spc.yaml
track_automation_failures              event                                                               queued     automations.yaml
update_outdoor_temp_daily_high_low     time_pattern, homeassistant                                         single     automations.yaml
ups_ac_restored_v3                     state:binary_sensor.ups_monitor_on_battery                          single     automations.yaml
ups_critical_shutdown_v3               state:binary_sensor.ups_monitor_voltage_critical                    single     automations.yaml
ups_graceful_shutdown_v3               state:binary_sensor.ups_monitor_voltage_warning +3 more             single     automations.yaml
ups_outage_start_v3                    state:binary_sensor.ups_monitor_on_battery                          single     automations.yaml
ups_voltage_warning_v3                 state:binary_sensor.ups_monitor_voltage_warning                     single     automations.yaml
validate_input_numbers_startup         homeassistant                                                       single     automations.yaml
watchdog_recovery_notification         state:binary_sensor.watchdog_battery_bank_stale +4 more             parallel   watchdog.yaml
watchdog_reload_basement_th            state:binary_sensor.watchdog_basement_th_stale                      single     watchdog.yaml
watchdog_reload_battery_bank           state:binary_sensor.watchdog_battery_bank_stale                     single     watchdog.yaml
watchdog_reload_ecobee                 state:binary_sensor.watchdog_ecobee_stale                           single     watchdog.yaml
watchdog_reload_sem                    state:binary_sensor.watchdog_sem_stale                              single     watchdog.yaml
watchdog_reload_ups                    state:binary_sensor.watchdog_ups_stale                              single     watchdog.yaml
```

111 automations.
