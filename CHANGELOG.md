# Changelog

All notable changes to this Home Assistant HVAC monitoring configuration.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Calendar Versioning](https://calver.org/) (YYYY.MM.DD).

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
