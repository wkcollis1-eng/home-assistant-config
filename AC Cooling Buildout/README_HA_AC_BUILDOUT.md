# HVAC Performance & Analytics System (Home Assistant)

A high-precision, dual-zone HVAC monitoring and diagnostic framework for Home Assistant. This system provides normalized efficiency tracking using Degree Day (HDD/CDD) mathematics, Statistical Process Control (SPC) for fault detection, and long-term data persistence independent of the Home Assistant Recorder.

## 1. System Overview
This implementation transforms raw thermostat state data into actionable engineering insights. It addresses the non-linear relationship between HVAC runtime and outdoor ambient temperatures by normalizing performance against Heating Degree Days (HDD) and Cooling Degree Days (CDD).

### Key Capabilities:
*   **Dual-Stream Symmetry:** The cooling (AC/CDD) pipeline is architected as a functional mirror of the heating (Furnace/HDD) pipeline, ensuring consistent logic across all thermal seasons.
*   **Dual-Zone Monitoring:** Discrete tracking for 1F and 2F zones (split-system configuration).
*   **Efficiency Normalization:** Calculates "Runtime per Degree Day" (min/DD) to track thermodynamic efficiency regardless of weather volatility.
*   **Statistical Process Control (SPC):** Automatically computes 7-day rolling means ($\mu$) and standard deviations ($\sigma$) to trigger alerts when equipment performance deviates beyond $\pm2\sigma$.
*   **Data Persistence:** Uses `input_number` accumulators to maintain monthly and yearly totals that survive Recorder purges and database maintenance.

## 2. Architectural Symmetry (HDD vs. CDD)
The system employs a mirrored architectural pattern for both heating and cooling streams. This design ensures that every heating metric has a direct cooling analog, facilitating year-round comparative analysis and simplifying maintenance.

| Functional Layer | Heating Component (HDD) | Cooling Component (CDD) |
| :--- | :--- | :--- |
| **State Detection** | `hvac_furnace_running` | `hvac_ac_running` |
| **Daily Integration** | `hvac_furnace_runtime_today` | `hvac_ac_runtime_today` |
| **Normalization** | Runtime per HDD | Runtime per CDD |
| **Sliding Window** | `hdd_day_1..7` | `cdd_day_1..7` |
| **SPC Analytics** | 7-day HDD Mean/StdDev | 7-day CDD Mean/StdDev |
| **Persistence** | Furnace Monthly Accumulators | AC Monthly Accumulators |
| **Health Guard** | HDD Pipeline Healthy | CDD Pipeline Healthy |

## 3. Technical Specifications
The system is calibrated based on measured hardware specifications per `SYSTEM_SPECIFICATIONS.md`:
*   **Condenser:** American Standard Silver 14 (4-ton). Measured steady-state draw: **4.9 kW**.
*   **Blower Motor:** Vortica II ECM. Measured draw: **0.21 kW** (Heating/Cooling).
*   **Thermostats:** Honeywell Lyric T6 Pro (Zone 1: `2d884c`, Zone 2: `2d8878`).
*   **Normalization Baseline:** 65°F (CDD65/HDD65).

## 4. Data Pipeline & Automation Sequence
The system executes a strictly timed End-of-Day (EOD) sequence. Although the pipelines mirror each other, they are kept independent—failure in an HDD capture will not suppress a CDD capture.

| Time | Task | Description |
| :--- | :--- | :--- |
| **23:54:30** | High/Low Reset | Resets daily temperature extremes. |
| **23:55:00** | HDD Capture | Shifts 7-day Heating Degree Day window. |
| **23:55:15** | CDD Capture | Shifts 7-day Cooling Degree Day window. |
| **23:56:00** | HDD Runtime | Shifts 7-day Runtime/HDD window. |
| **23:56:30** | Monthly Tracking | Updates MTD and YTD accumulators for all zones. |
| **23:56:45** | CDD Runtime | Shifts 7-day Runtime/CDD window. |
| **23:57:00** | CSV Export | Appends daily metrics to `daily.csv`. |

## 5. Statistical Process Control (SPC) Logic
The system monitors for equipment degradation (e.g., refrigerant loss, dirty coils, or sensor drift) using a rolling statistical window.

*   **Metric:** $Runtime / Degree Day$
*   **Upper Bound:** $\mu + 2\sigma$ (Potential inefficiency/failure).
*   **Lower Bound:** $\mu - 2\sigma$ (Potential sensor fault).
*   **Gating:** Alerts are suppressed until $n \ge 3$ valid samples exist in the 7-day window to prevent "bootstrap noise" during seasonal transitions.

## 6. Entity Schema
### Primary Sensors
*   `binary_sensor.hvac_ac_running`: Master compressor state (OR logic of zone calls).
*   `sensor.hvac_runtime_per_cdd_7_day`: The primary efficiency metric for cooling.
*   `sensor.hvac_ac_min_per_cycle`: Monitored to detect short-cycling (Threshold: <8 min).

### Health & Diagnostics
*   `binary_sensor.cdd_pipeline_healthy`: Composite sensor validating proxy availability and capture timeliness.
*   `binary_sensor.cdd_capture_stale`: Problem sensor if EOD automation fails (>26h since last OK).

## 7. Governance
### Work Rules for System Updates
1.  **Idempotency:** CDD and HDD pipelines must remain independent to isolate failure domains.
2.  **Validation:** All configuration changes require `ha config check` before deployment.
3.  **Timestamping:** All `input_datetime` entities must track both date and time (`has_date: true`, `has_time: true`).
4.  **SPC Seeding:** On initial seasonal startup, seed values provide the baseline until the 7-day window populates with live data.
