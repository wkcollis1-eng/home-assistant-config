# Changelog

All notable changes to this Home Assistant HVAC monitoring configuration.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Calendar Versioning](https://calver.org/) (YYYY.MM.DD).

## [2026.02] - February 2026

### Setback Recovery System Simplification

Major refactor replacing ~60 entities (rolling window slots, transient helpers, complex binary sensors) with a simple state machine using explicit input_boolean latches.

### Added
- **Dehumidifier Performance Tracking** - Pull-down rate, hold time, duty cycle, margin sensors
- **Per-zone setback CSV files** - `hvac_setback_1f.csv` and `hvac_setback_2f.csv` via Python script
- **State machine latches** - `input_boolean.hvac_*f_recovering` for explicit state tracking
- **Recovery start temp tracking** - `input_number.hvac_*f_recovery_start_temp`
- **Setback lowered automations** - Capture utility-driven mid-cycle setpoint drops
- **Safety timeout automations** - 14h setback stuck, 4h recovery stuck, 1 AM midnight audit

### Fixed
- **Heating efficiency MTD nightly oscillation** - Eliminated 3-4 point drops at 23:55 by moving HDD/CDD accumulator updates from `capture_daily_hdd` (23:55) to `capture_daily_monthly_tracking` (23:56:30), setting timestamp FIRST before any accumulator updates, and unifying all month sensors to use `monthly_tracking_capture_last_ok`
- **HDD double-counting** - Cumulative month/year sensors now use `captured_today` guard
- **Setback start debounce** - 5-second delay filters Resideo firmware 1-second glitches
- **Recovery rate units** - Changed from °F/hr to min/°F (time per degree, not speed)
- **Weather freshness** - Changed from `last_changed` to `last_updated` for accurate staleness
- **Pirate Weather forecasts** - Migrated to `weather.get_forecasts` service (HA 2024.3+ compatible)
- **Expected runtime sensor** - Dual-source fallback for `_2` suffix entity compatibility
- **Recovery start guard** - Requires comfort setpoint restored before declaring "recovering"
- **Overnight setback cycle hardening** - Time window gates, mode: single, timestamp validation
- **CSV report hardening** - Data validity checks, duplicate prevention, rotation fixes

### Changed
- Recovery tracking from 7-slot rolling windows to direct CSV logging
- Setback start stores MTD accumulator snapshot (hours) instead of daily runtime (minutes)
- Recovery minutes subtract 10-minute stability wait from elapsed time
- Heating efficiency MTD minimum HDD guard: 0 → 5 (prevents divide-by-near-zero)

### Removed
- 14 `input_number.hvac_*f_recovery_rate_*` rolling window slots
- 4 `input_number.hvac_*f_recovery_transient_*` calculation helpers
- 12 `input_number.hvac_*f_last_*` transient value holders
- 8 `sensor.hvac_*f_recovery_rate_*` statistical sensors
- 4 `binary_sensor.hvac_*f_recovery_*` complex hysteresis sensors
- Recovery rate staleness and alert automations

---

## [2026.01] - January 2026

### Major Robustness Update

Comprehensive audit and hardening of all data pipelines for production-grade reliability.

### Fixed
- **Fail-fast weather proxy** - Returns `unavailable` instead of silent 35°F default
- **Monthly accumulators** - Now immune to recorder 14-day purge
- **Recovery END thresholds** - Increased from 0.5°F to 1.0°F (1F) and 1.25°F (2F)
- **Recovery rate measurement** - Now measures actual thermal recovery, not control-loop gap
- **Setback validation** - Prevents mid-cycle overwrites with explicit latch
- **Entity registry _2 suffix** - All dependencies updated for month sensors

### Added
- **Tier 1 Data Integrity Matrix** - Pipeline health monitoring for HDD, Runtime/HDD, Recovery
- **Climate Norms Feature** - 18-year historical comparison with efficiency deviation index
- **Week/month furnace metrics** - Cycles, overlap, chaining index for extended periods
- **12 watchdog automations** - Staleness detection for all critical pipelines
- **Automation failure tracking** - Counter and dashboard card for error visibility
- **40+ new sensors** - Validation, health monitoring, and extended metrics

### Changed
- Runtime per HDD standardized to furnace runtime (no zone overlap double-counting)
- Recovery START uses hybrid logic (gap > 1 AND furnace running)
- Setback tracking threshold lowered from 2°F to 1°F

## [1.0.0] - January 2025

### Initial Public Release

Production-ready HVAC monitoring configuration with:

- HDD/CDD tracking with 7-day rolling averages
- Statistical Process Control (±2σ bounds)
- Multi-zone runtime analysis
- Filter tracking and alerts
- CSV daily/monthly exports
- Dashboard gallery with 30+ cards

### Documentation
- Comprehensive CLAUDE.md with 600+ entities documented
- Dashboard card library in dashboards/cards/
- Cross-reference to Baseline Analysis repo

---

## Companion Repository

For analysis methodology and baseline data, see:
[Residential-HVAC-Performance-Baseline-](https://github.com/wkcollis1-eng/Residential-HVAC-Performance-Baseline-)
