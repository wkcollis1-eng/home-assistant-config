# Home Assistant Configuration

HVAC monitoring and energy performance tracking for a 2-zone residential heating system in Connecticut.

## Overview

This configuration provides:
- **HDD/CDD Tracking** - Heating/cooling degree days with 7-day rolling averages
- **Efficiency Monitoring** - Runtime per HDD with auto-calculated statistical bounds (±2σ)
- **Recovery Rate Analysis** - Setback recovery tracking with weather adjustment
- **Climate Norms Comparison** - 18-year historical data for performance context
- **Filter Tracking** - Runtime-based filter change alerts
- **Furnace Cycle Analysis** - Zone overlap detection and chaining index
- **Daily/Monthly Reporting** - CSV exports for long-term analysis

## Related Repositories

- [wkcollis1-eng/home-assistant-config](https://github.com/wkcollis1-eng/home-assistant-config) - This repository; Home Assistant configuration and HVAC monitoring automation referenced by the baseline analysis project.
- [wkcollis1-eng/Residential-HVAC-Performance-Baseline-](https://github.com/wkcollis1-eng/Residential-HVAC-Performance-Baseline-) - Analysis and documentation that consumes exports and metrics produced by this Home Assistant configuration to benchmark HVAC performance.

## Building Details

| Attribute | Value |
|-----------|-------|
| Square Footage | 2,440 ft² |
| Location | Connecticut (41.28, -72.81) |
| Heating | Gas furnace, 60,556 BTU/hr |
| Zones | 1F and 2F (Honeywell Lyric T6 Pro) |
| Annual HDD | 6,270 |

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
├── custom_components/
│   ├── hacs/               # Home Assistant Community Store
│   └── pirateweather/      # Pirate Weather integration
└── themes/                 # UI themes
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
- **yamllint** - YAML syntax validation
- **HA Config Check** - Home Assistant configuration validation

Check the Actions tab for build status.

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

1. **Edit files** via SMB share (H:\) or directly in GitHub
2. **Commit and push:**
   ```bash
   git add -A
   git commit -m "Description of changes"
   git push
   ```
3. **GitHub Actions validates** - check the Actions tab for results
4. **Reload in HA:**
   - YAML changes: Developer Tools → YAML → Reload appropriate section
   - Major changes: Settings → System → Restart

### Reload Commands by File

| File Changed | Reload Method |
|--------------|---------------|
| `automations.yaml` | Reload Automations |
| `scripts.yaml` | Reload Scripts |
| `scenes.yaml` | Reload Scenes |
| `configuration.yaml` (template sensors) | Reload Template Entities |
| `configuration.yaml` (input_*) | Restart required |
| `configuration.yaml` (major changes) | Full restart |

## Excluded from Version Control

The following are excluded via `.gitignore` for security/size:
- `secrets.yaml` - API keys, passwords
- `.storage/` - Auth tokens, user data, registry
- `home-assistant_v2.db` - Database
- `.cloud/` - Nabu Casa connection
- `deps/` - Python dependencies
- `tts/` - Text-to-speech cache

## Documentation

See [CLAUDE.md](CLAUDE.md) for detailed documentation including:
- Complete entity ID reference
- Baseline values and statistical approach
- Automation descriptions
- Dashboard architecture
- Database configuration
- Architecture decisions

## License

Personal configuration - use at your own risk.
