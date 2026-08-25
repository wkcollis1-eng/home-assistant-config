
# Residential Latent Load Management: Santa Fe Dehumidifier Performance Framework

This module provides a high-fidelity monitoring and control framework for residential dehumidification, specifically optimized for a **Santa Fe Classic** unit integrated via Home Assistant. It transitions moisture control from basic relative humidity (RH) tracking to a precise, dew-point-driven performance baseline.

## Technical Overview
The system treats the dehumidifier as a critical component of the residential thermal envelope. By monitoring instantaneous power consumption alongside basement psychrometric data, the framework calculates real-time efficiency metrics, characterizes the moisture infiltration rate (**Hold Time**), and validates equipment health (**Pull-Down Rate**).

### The "Power Gate" Logic (Critical Configuration)
A central feature of this framework is the **250W Power Gate**. The Santa Fe Classic operates in two distinct electrical tiers:
*   **Fan-Only/Defrost Mode (~120W):** The unit circulates air or melts frost but is not actively removing moisture.
*   **Dehumidification Mode (~540W):** The compressor is engaged, and latent heat is being removed.

**The system uses `input_number.dehumidifier_power_threshold` (defaulted to 250W) as the logical gate.** This ensures that all performance metrics—including runtime, duty cycle, and pull-down rates—differentiate between the unit simply "running" and the unit actually "working." Metrics are only recorded when power exceeds this gate, providing a true representation of energy-to-moisture removal efficiency.

---

## Logic Flow & State Machine

### 1. Demand Calculation (`Should Run` Logic)
The system calculates `sensor.basement_dew_point` using the Magnus-Tetens approximation. Demand is triggered via `binary_sensor.dehumidifier_should_run` when:
*   **Basement Dew Point** > `input_number.dehumidifier_dewpoint_threshold` (Baseline: 52°F).
*   **Basement Temperature** > 60°F (Safety lockout to prevent evaporator icing).

### 2. Control & Protection Logic
*   **Auto-On:** Triggered when demand is present, provided the unit has been off for at least **30 minutes** (Internal pressure equalization and short-cycle protection).
*   **Auto-Off:** Triggered when conditions are cleared **OR** the unit reaches a **4-hour maximum runtime** safety limit.
*   **State Detection:** The `binary_sensor.dehumidifier_compressor_active` uses the 250W gate to filter out fan-only cycles.

### 3. Performance Analytics
Upon cycle completion, the system executes two primary engineering calculations:
*   **Pull-Down Rate:** $\Delta \text{Dew Point} / \text{Cycle Duration}$. This validates that the unit is removing moisture at the expected rate (e.g., °F/hr).
*   **Hold Time:** The duration between the end of the last cycle and the start of the next. This serves as a proxy for the basement's vapor barrier integrity and infiltration levels.

---

## Entity Registry

### Primary Control & Logic
| Entity | Function |
| :--- | :--- |
| `input_number.dehumidifier_dewpoint_threshold` | Target dew point for basement stability (Default: 52°F). |
| `input_number.dehumidifier_power_threshold` | **The Gate:** Differentiates Fan (~120W) from Compressor (~540W). |
| `binary_sensor.dehumidifier_should_run` | Logic gate for automation triggers. |
| `binary_sensor.dehumidifier_compressor_active` | Power-gated sensor used for high-fidelity metric tracking. |

### Performance Telemetry
| Entity | Function |
| :--- | :--- |
| `sensor.dehumidifier_pull_down_rate` | Efficiency: Dew Point °F reduction per hour. |
| `sensor.dehumidifier_hold_time` | Infiltration: Hours environment stayed below threshold. |
| `sensor.dehumidifier_duty_cycle_24h` | Percent of time unit was actively dehumidifying (24h window). |
| `sensor.dehumidifier_dew_point_margin` | Real-time delta between current state and threshold. |

### Operational Tracking
| Entity | Function |
| :--- | :--- |
| `sensor.dehumidifier_runtime_today` | Cumulative **compressor-only** runtime for the current day. |
| `counter.dehumidifier_cycles_today` | Total number of compressor cycles initiated. |
| `sensor.dehumidifier_avg_cycle_minutes` | Mean duration of active dehumidification cycles. |

---
