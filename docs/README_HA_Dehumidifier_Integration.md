
# Residential Latent Load Management: Basement Dehumidifier (Aprilaire E080)

The basement dehumidifier is an **Aprilaire E080**, free-standing (not ducted), draining to a condensate pump it shares with the Navien water heater. It replaced a Santa Fe Classic, which is retired; E080 cycles are logged from 2026-08-05. Home Assistant switches it through a Kasa smart plug (`switch.dehumidifier`), which also meters its power.

**This file names the helpers; it does not copy their values.** Every threshold is a field-tunable `input_number` declared in `configuration.yaml` - read the live value from the helper, never from a document. Until 2026-09-23 this README restated the Santa Fe's values (a 250 W gate, a 52 °F dew-point target, a 4 h cap) and had drifted off all three: the second-copy failure CLAUDE.md R10 exists to prevent. Entity meanings live in `ENTITIES.md`, which is generated.

## Controlled variable: relative humidity

Control is an RH band on the SHT45 basement node (`sensor.basement_th_node_basement_humidity`). RH was restored as the controlled variable on 2026-08-03 after a four-day dew-point experiment. Why - the Santa Fe's frosted coil was heating the room, and the objective is a mold limit, which follows RH - is in the comment on `binary_sensor.dehumidifier_should_run`. The dew-point band helpers (`input_number.dehumidifier_dp_on_threshold` / `_dp_off_threshold`) are dormant: nothing in YAML reads them.

## The power gate

`binary_sensor.dehumidifier_compressor_active` is on when the plug is on and its power exceeds `input_number.dehumidifier_power_threshold`, which separates the compressor from fan-only running. If the threshold helper cannot be read, the sensor goes unavailable rather than substitute a guess.

Measured on the E080: compressor 465.8 +/- 6.5 W steady [M, n=340 runs, 2026-08-07..09-22, minutes 10-14 of each run]; fan-only ~57.8 W [M, CHANGELOG 2026-08-24 entry].

## Logic flow

| Entity | What it does |
| :--- | :--- |
| `binary_sensor.dehumidifier_should_run` | On when basement temperature >= `dehumidifier_min_temp` AND RH > `dehumidifier_rh_on_threshold`. Unavailable when the sensor or helper cannot be read, so a dead node cannot start the unit. |
| `automation.dehumidifier_auto_on` | Starts the unit on `should_run`, unless local control is on or the min-off lockout (`dehumidifier_min_off_minutes`) has not elapsed. |
| `automation.dehumidifier_auto_off` | Stops it when RH falls to `dehumidifier_rh_off_threshold`, subject to the min-run guard (`dehumidifier_min_run_minutes`) and the condensation veto. |
| `automation.dehumidifier_max_runtime_backstop` | Stops it after `dehumidifier_max_runtime_hours` of switch-on wall-clock time, which no power dip resets. |
| `automation.dehumidifier_force_on_backstop` | Runs it, bypassing min-off, when RH exceeds the mold ceiling (`dehumidifier_rh_force_on`) or the basement dew point closes on the coldest measured surface. |
| `automation.dehumidifier_control_sensor_loss_shutdown` | Stops it when the SHT45 RH has been unreadable for 10 min. |
| `automation.dehumidifier_rh_stall_shutdown` | Stops it when dew-point improvement stalls below `dehumidifier_dp_stall_threshold`. **Disabled** - the automation was `off` on 2026-09-23. |
| `input_boolean.dehumidifier_local_control` | Hands control to the E080's own humidistat for commissioning runs. HA holds the plug on, and reminds hourly once `dehumidifier_local_control_max_hours` is passed. |

## Performance analytics

Each compressor cycle is bracketed by `dehumidifier_cycle_start_capture` and `dehumidifier_cycle_end_capture`, which trigger on `compressor_active`, not on the switch.

| Entity | Measures |
| :--- | :--- |
| `sensor.dehumidifier_pull_down_rate` | Basement dew-point drop per hour over the last cycle. |
| `sensor.dehumidifier_hold_time` | Hours between the end of one cycle and the start of the next. |
| `sensor.dehumidifier_duty_cycle_24h` | Share of the last 24 h with the compressor running. |
| `sensor.dehumidifier_runtime_today` | Compressor-only runtime today. |
| `counter.dehumidifier_cycles_today` | Compressor cycles started today. |
| `sensor.dehumidifier_avg_cycle_minutes` | Mean cycle length. |
| `sensor.dehumidifier_dew_point_margin` | Basement dew point against `dehumidifier_dewpoint_threshold`. Display only: no control reads that helper. |

Compressor health is watched by the steady-watts SPC in `packages/spc.yaml`. Those watts rise with inlet temperature, +5.20 +/- 0.35 W/°F [M, n=46 daily means, 2026-08-08..09-22, basement 67.8-71.9 °F] - see `docs/pending.md` P3 before reading a seasonal drift as a fault.

**Hold time is not an infiltration measure on its own.** Over 2026-08-07..09-22 the basement's moisture gain between cycles tracked main-floor humidity (t=11.1) and not outdoor humidity (t=0.17, p=0.86) [M, n=340 off-periods, Newey-West standard errors].

## What is not measured

**Water removed.** The ratings are 65 pt/day and IEF 2.35 L/kWh [S: ENERGY STAR record 4510066, test per 10 CFR 430 Subpart B App. X1], and 80 pt/day at 80 °F / 60 % RH and 185 CFM free-standing [S: Aprilaire 10015109 B2209062A, Specifications]. The condensate goes to a shared pump whose cycles (median 15 s) are below its Kasa plug's polling resolution, and it is not weighed (Bill, 2026-09-23), so litres per kWh is unverified.

What is verified is the electrical side: 3.98 +/- 0.10 A [M, n=340 runs] against 5.1 A rated at the 80 °F point [S: Aprilaire 10015109, Specifications] - lower, as expected at a 67.5-72.0 °F inlet [M].
