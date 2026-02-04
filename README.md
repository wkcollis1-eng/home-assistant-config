# Home Assistant HVAC Monitoring Configuration

> Professional-grade HVAC performance tracking with statistical process control for residential heating systems

![Build Status](https://github.com/wkcollis1-eng/home-assistant-config/workflows/Validate/badge.svg)
![License](https://img.shields.io/badge/license-Personal-lightgrey)

## Overview

This configuration provides industrial-grade monitoring and analysis for a 2-zone residential gas furnace in Connecticut, applying statistical process control methodology typically used in manufacturing to HVAC performance tracking.

**Key Features:**

- **HDD/CDD Tracking** - Heating/cooling degree days with 7-day rolling averages
- **Efficiency Monitoring** - Runtime per HDD with auto-calculated statistical bounds (±2σ)
- **Recovery Rate Analysis** - Setback recovery tracking with weather adjustment
- **Climate Norms Comparison** - 18-year historical data for performance context
- **Filter Tracking** - Runtime-based filter change alerts
- **Furnace Cycle Analysis** - Zone overlap detection and chaining index
- **Daily/Monthly Reporting** - CSV exports for long-term analysis

## 📊 Dashboard Gallery

### Real-time Performance Monitoring

<table>
  <tr>
    <td><img src="docs/images/dashboard-runtime-today.png" alt="Today's Runtime" width="400"/></td>
    <td><img src="docs/images/dashboard-cycle-analysis.png" alt="Cycle Analysis" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><b>Today's Runtime Analysis</b><br/>Zone balance: 55.6% | Runtime per HDD: 7.4 min</td>
    <td align="center"><b>Cycle Length Analysis</b><br/>Average cycle: 6.0 min (1F), 6.6 min (2F)</td>
  </tr>
</table>

### Statistical Efficiency Tracking

<table>
  <tr>
    <td><img src="docs/images/dashboard-efficiency-tracking.png" alt="Efficiency Tracking" width="400"/></td>
    <td><img src="docs/images/dashboard-daily-runtime.png" alt="Daily Runtime" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><b>7-Day Rolling Efficiency</b><br/>Current: 9.1 min/HDD vs control limits (6-14 min/HDD)</td>
    <td align="center"><b>Daily Runtime per HDD</b><br/>Today: 7.5 min/HDD | 7-Day Mean: 9.2 min/HDD</td>
  </tr>
</table>

### System Health & Performance Gauges

<table>
  <tr>
    <td><img src="docs/images/dashboard-system-alerts.png" alt="System Alerts" width="400"/></td>
    <td><img src="docs/images/dashboard-performance-gauges.png" alt="Performance Gauges" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><b>System Health Dashboard</b><br/>Real-time alerts for efficiency degradation & data integrity</td>
    <td align="center"><b>Performance Metrics</b><br/>CCF/1k HDD: 92.0 | Building UA: 378 BTU/hr-°F</td>
  </tr>
</table>

### Zone Balance Analysis

<p align="center">
  <img src="docs/images/dashboard-floor-comparison.png" alt="Floor Comparison" width="420"/>
  <br/>
  <b>Floor Runtime Comparison</b><br/>
  1F: 3.9 min/HDD | 2F: 4.9 min/HDD
</p>

## Use Cases

This configuration is designed for homeowners and DIY enthusiasts who want to:

✅ **Track HVAC efficiency over time** - Monitor if your furnace is running more than expected based on weather conditions  
✅ **Detect performance anomalies early** - Statistical alerts when runtime drifts outside normal operating bounds  
✅ **Compare against climate normals** - Understand if you're using more heat than typical for your local weather patterns  
✅ **Optimize thermostat setback schedules** - Data-driven analysis of recovery times from overnight setbacks  
✅ **Predict filter maintenance needs** - Runtime-based alerts for filter changes instead of arbitrary time intervals  
✅ **Balance multi-zone heating** - Ensure even heat distribution between floors or zones  
✅ **Validate HVAC contractor work** - Objective performance data before and after service calls  
✅ **Support energy-related decisions** - Quantify the impact of insulation, air sealing, or equipment upgrades

## Building Details

| Attribute | Value |
| --- | --- |
| **Square Footage** | 2,440 ft² |
| **Location** | Connecticut (41.28°N, -72.81°W) |
| **Heating** | Gas furnace, 60,556 BTU/hr input |
| **Zones** | 1F and 2F (Honeywell Lyric T6 Pro) |
| **Annual HDD** | 6,270 (65°F base) |
| **Balance Point** | 59.0°F |
| **Site EUI** | 84.4 kBTU/ft²-yr (current estimate) |

## What This Tracks

### Current Performance Metrics

Based on live monitoring data:

- **Zone Balance**: Maintains 55-60% balance between floors (target: balanced distribution)
- **Efficiency**: Current 9.1 min/HDD vs 7-day mean of 9.2 min/HDD
- **Cycle Performance**: 6.0 min average cycle (1F), 6.6 min (2F)
- **Statistical Bounds**: Auto-calculated ±2σ control limits (6-14 min/HDD)
- **Recovery Tracking**: Monitors setback recovery with weather adjustment
- **Zone Overlap**: 19% concurrent operation, chaining index 1.38

### Performance Baselines

These are the targets my system is measured against:

| Metric | Target | Calculated From |
|--------|--------|-----------------|
| **CCF/1k HDD** | 82.6 | 3 years of utility data |
| **Building UA** | 449 BTU/hr-°F | Steady-state analysis |
| **Site EUI** | 41.7 kBTU/ft²-yr | Annual consumption |
| **Balance Point** | 59.0°F | Climate normals analysis |

*Your system will be different—these values are specific to my 2,440 ft² colonial in Connecticut.*

## Why This Configuration Stands Out

| Feature | This Repo | Typical HA Setup |
|---------|-----------|------------------|
| **Statistical Rigor** | ±2σ control limits, 7-day rolling | Manual thresholds |
| **Climate Context** | 18-year daily normals | Current weather only |
| **Zone Analysis** | Balance tracking, overlap detection | Basic on/off |
| **Long-term Data** | CSV exports, monthly aggregation | Lost on restart |
| **Validation** | CI/CD with yamllint + HA check | Manual only |
| **Documentation** | Engineering methodology documented | Config files only |

## System Architecture

```
┌─────────────────────────────────────────────┐
│         Home Assistant Server               │
├─────────────────────────────────────────────┤
│  ┌─────────────┐      ┌─────────────┐      │
│  │ Thermostat  │      │  Weather    │      │
│  │ Integration │      │  Integration│      │
│  │ (2 zones)   │      │ (Pirate)    │      │
│  └──────┬──────┘      └──────┬──────┘      │
│         │                    │              │
│         ▼                    ▼              │
│  ┌─────────────────────────────────┐       │
│  │   Template Sensors              │       │
│  │   • HDD/CDD calculation         │       │
│  │   • Runtime tracking            │       │
│  │   • Efficiency metrics          │       │
│  │   • Statistical bounds          │       │
│  └────────────┬────────────────────┘       │
│               │                             │
│               ▼                             │
│  ┌─────────────────────────────────┐       │
│  │   Dashboards + Alerts           │       │
│  └─────────────────────────────────┘       │
│               │                             │
│               ▼                             │
│  ┌─────────────────────────────────┐       │
│  │   CSV Reports (Long-term)       │       │
│  └─────────────────────────────────┘       │
└─────────────────────────────────────────────┘
```

## File Structure

```
├── configuration.yaml      # Main HA config with sensors and input helpers
├── automations.yaml        # All automations (HDD capture, alerts, etc.)
├── scripts.yaml            # Bill archive seeding scripts
├── scenes.yaml             # Light scenes
├── secrets.yaml            # API keys, passwords (not in repo)
├── climate_daily_norms.csv # 18-year climate normals by day-of-year
├── CLAUDE.md               # Detailed entity reference and architecture notes
├── scripts/
│   └── climate_norms_today.py  # Daily climate lookup script
├── dashboards/
│   └── cards/              # Reusable dashboard card snippets
├── reports/
│   ├── hvac_daily_YYYY.csv # Daily HVAC data
│   └── hvac_monthly.csv    # Monthly summary
├── docs/
│   └── images/             # Dashboard screenshots
├── custom_components/
│   ├── hacs/               # Home Assistant Community Store
│   └── pirateweather/      # Pirate Weather integration
└── themes/                 # UI themes
```

## Sample Output

**Daily HVAC Report** (`reports/hvac_daily_2025.csv`):

```csv
Date,HDD,1F_Runtime,2F_Runtime,Total_Runtime,Runtime_per_HDD,1F_Cycles,2F_Cycles
2025-01-21,29.8,116,145,261,8.8,19,22
2025-01-22,32.1,128,159,287,8.9,21,24
2025-01-23,28.5,110,138,248,8.7,18,20
```

## Validation

### Local Validation

**YAML Syntax Check:**

```bash
yamllint configuration.yaml automations.yaml scripts.yaml scenes.yaml
```

**Home Assistant Config Check (requires Docker):**

```bash
docker run --rm -v "$(pwd)":/config homeassistant/home-assistant:stable \
  python -m homeassistant --script check_config --config /config
```

### Automated CI

This repository uses GitHub Actions to automatically validate on every push:

* **yamllint** - YAML syntax validation
* **HA Config Check** - Home Assistant configuration validation

Check the [Actions tab](https://github.com/wkcollis1-eng/home-assistant-config/actions) for build status.

## Deployment Workflow

### How This Repo Connects to Home Assistant

```
┌─────────────────┐         ┌─────────────────┐
│   This Repo     │         │  Home Assistant │
│   (GitHub)      │         │  (HA OS/Docker) │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │  1. Push changes          │
         ▼                           │
┌─────────────────┐                  │
│  GitHub Actions │                  │
│  (validates)    │                  │
└────────┬────────┘                  │
         │                           │
         │  2. If valid, pull        │
         │     to HA via SMB/SSH     │
         ▼                           ▼
┌─────────────────────────────────────────────┐
│              /config directory              │
│         (mapped as H:\ on Windows)          │
└─────────────────────────────────────────────┘
```

### Making Changes

1. **Edit files** via SMB share (H:) or directly in GitHub
2. **Commit and push:**

   ```bash
   git add -A
   git commit -m "Description of changes"
   git push
   ```
3. **GitHub Actions validates** - check the Actions tab for results
4. **Reload in HA:**
   * YAML changes: Developer Tools → YAML → Reload appropriate section
   * Major changes: Settings → System → Restart

### Reload Commands by File

| File Changed | Reload Method |
| --- | --- |
| `automations.yaml` | Reload Automations |
| `scripts.yaml` | Reload Scripts |
| `scenes.yaml` | Reload Scenes |
| `configuration.yaml` (template sensors) | Reload Template Entities |
| `configuration.yaml` (input_*) | Restart required |
| `configuration.yaml` (major changes) | Full restart |

## Getting Started

1. **Clone or fork this repository**
2. **Review `secrets.yaml.example`** - Copy to `secrets.yaml` and add your API keys
3. **Adjust baseline values** in `configuration.yaml` to match your system
4. **Update `climate_daily_norms.csv`** with your local climate data (or use mine as a starting point)
5. **Configure thermostats** - Update entity IDs in `configuration.yaml` to match your devices
6. **Install custom components** via HACS: Pirate Weather
7. **Import dashboards** from `dashboards/cards/`

## Related Projects

### 📊 [Residential HVAC Performance Baseline](https://github.com/wkcollis1-eng/Residential-HVAC-Performance-Baseline-)

**How This Repo Relates to the Performance Baseline:**

The Performance Baseline repository documents a comprehensive **4-year retrospective analysis** (2022-2025) that established the target performance metrics used in this Home Assistant configuration:

| What It Does | Performance Baseline Repo | This Repo (HA Config) |
|-------------|---------------------------|----------------------|
| **Purpose** | Establishes diagnostic thresholds from utility data | Real-time monitoring against those thresholds |
| **Timeframe** | 4-year retrospective analysis | Live, continuous monitoring |
| **Data Source** | Utility bills, weather normals | HVAC runtime telemetry, sensors |
| **Output** | Target values (82.6 CCF/1k HDD, 449 BTU/hr-°F UA) | Real-time performance vs targets |
| **Methodology** | Billing-aligned statistical analysis | Statistical process control |

**In Practice:**
1. The Baseline repo **calculated** the 82.6 CCF/1k HDD target from 4 years of gas bills
2. This HA config **monitors** actual runtime/HDD against that target in real-time
3. When performance drifts >10% from baseline, alerts trigger investigation
4. The Baseline repo's ±2σ bounds become the control limits in SPC dashboards

**Use Both Together:**
- **Baseline Repo**: Understand *where* the targets came from and *why* they matter
- **This Repo**: Monitor *current* performance and detect deviations early

The Baseline repository provides the scientific foundation; this Home Assistant configuration provides the operational implementation.

## Documentation

See [CLAUDE.md](CLAUDE.md) for detailed documentation including:

* Complete entity ID reference
* Baseline values and statistical approach
* Automation descriptions
* Dashboard architecture
* Database configuration
* Architecture decisions

## Excluded from Version Control

The following are excluded via `.gitignore` for security/size:

* `secrets.yaml` - API keys, passwords
* `.storage/` - Auth tokens, user data, registry
* `home-assistant_v2.db` - Database
* `.cloud/` - Nabu Casa connection
* `deps/` - Python dependencies
* `tts/` - Text-to-speech cache

## Discussion & Contributing

Questions or suggestions? Feel free to [open an issue](https://github.com/wkcollis1-eng/home-assistant-config/issues).

This is a personal configuration, but ideas for improvements are always welcome. If you implement this for your own system, I'd love to hear about your results!

## How This Compares

**To Other Home Assistant HVAC Configurations:**

Most Home Assistant HVAC configurations focus on basic automation (turn on heat at X°). This configuration treats HVAC like an industrial process:

- **Statistical Process Control** - Not just "is it on?", but "is performance within expected bounds?"
- **Climate Normalization** - Compare apples-to-apples across weather variations
- **Long-term Data Retention** - Track trends over months/years
- **Professional Documentation** - Engineering-grade analysis methodology
- **Baseline Validation** - Metrics derived from actual utility bills and steady-state analysis

**To Traditional Energy Monitoring:**

Standard home energy monitors show you *what* you're using. This configuration tells you *whether that's normal* by:
- Comparing current performance to statistically-derived baselines
- Accounting for weather variations using HDD normalization
- Alerting when efficiency degrades beyond acceptable bounds
- Providing context through 18-year climate normals

**Companion Repository:**

For the complete methodology behind the baseline targets used in this configuration, see the [Residential HVAC Performance Baseline](https://github.com/wkcollis1-eng/Residential-HVAC-Performance-Baseline-) repository, which documents the 4-year analysis that established these diagnostic thresholds.

## License

Personal configuration - use at your own risk. Feel free to adapt for your own system.

## About

Developed and maintained by Bill Collis, a retired engineer applying professional engineering methodologies to residential energy optimization. For more detailed analysis and findings, see my [technical reports on GitHub](https://github.com/wkcollis1-eng) and [Substack articles](https://substack.com/@billcollis).

---

*Last Updated: February 2025*
