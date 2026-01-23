# HA Monitor Agent - Discussion Notes

---

## Part 6: Session Notes - 2026-01-23

### Completed This Session
1. **GitHub setup complete:**
   - Repo: https://github.com/wkcollis1-eng/home-assistant-config
   - GitHub CLI authenticated as wkcollis1-eng
   - .gitignore excludes secrets, .storage, database
   - Initial commit pushed

2. **CI/CD pipeline working:**
   - GitHub Actions validates on every push
   - yamllint + HA config check
   - Fixed several lint errors (indentation, duplicate keys, trailing spaces)

3. **Config fixes made:**
   - `scripts.yaml`: Fixed weather_update_script indentation structure
   - `configuration.yaml`: Removed duplicate icon key on hvac_2f_setback_start
   - `automations.yaml`: Changed `service:` to `action:` format for CSV reports

### Issue in Progress: shell_command not loading
- **Symptom:** `shell_command.append_daily_csv` not appearing in Services after restart
- **Impact:** Daily CSV report not populating (last data: none, only header exists)
- **Tried:**
  - Verified automation is enabled
  - Checked automation trace - error "This action requires a target"
  - Restarted HA - shell_command services still don't appear
- **Next step:** Added `shell_command.test_shell` simple command to isolate issue
  - Need to restart HA and check if `shell_command.test_shell` appears
  - Check HA logs for shell_command errors
  - If simple command works, issue is with template syntax in complex commands

---
**Date:** 2026-01-22

---

## Part 1: Errors Fixed Today

### Issue 1: Recovery Minutes Overflow
- `input_number.hvac_1f_last_recovery_minutes` received 780.6 (max 180)
- `input_number.hvac_2f_last_recovery_minutes` received 755.0 (max 180)
- **Fix:** Added clamping in `automations.yaml` lines 676, 764:
  ```yaml
  value: "{{ [recovery_minutes | float, 180] | min }}"
  ```

### Issue 2: Recovery Rate Overflow
- `input_number.hvac_1f_recovery_rate_1` received 327.6 (max 60)
- `input_number.hvac_2f_recovery_rate_1` received 239.3 (max 60)
- **Fix:** Added clamping in `automations.yaml` lines 713, 801:
  ```yaml
  value: "{{ [recovery_rate | float, 60] | min }}"
  ```

### Issue 3: HDD Cumulative State Class
- `sensor.hvac_hdd65_cumulative_month` and `_year` had `state_class: total_increasing`
- Values can decrease slightly due to rounding in `sensor.hvac_hdd65_today`
- **Fix:** Changed to `state_class: total` in `configuration.yaml` lines 1267, 1277

### Issue 4: NWS Data Error
- External service issue, no fix needed

---

## Part 2: HA Monitor Agent Proposal

### Proposed Architecture
```
┌─────────────┐     REST/WS API      ┌─────────────────┐
│ Home        │◄────────────────────►│ Monitor Agent   │
│ Assistant   │                      │ (Your PC)       │
│             │     SMB/Network      │                 │
│ /config     │◄────────────────────►│ - Python        │
└─────────────┘     share            │ - Claude API    │
                                     │ - Local Web UI  │
                                     └─────────────────┘
```

### Core Features
- Log monitoring (poll `/api/error/all` or WS events)
- Entity health (unavailable, unknown, stale detection)
- Value validation (flag out-of-range values)
- Config linting (YAML syntax validation)
- Fix proposals with approval workflow
- Audit log with rollback capability

### Phased Implementation
1. **Phase 1:** Read-only monitoring + Claude analysis
2. **Phase 2:** Fix proposals with approval UI
3. **Phase 3:** Config editing with diff preview and HA reload

---

## Part 3: Architectural Feedback Received

### Key Pivots Recommended
1. **WS/REST primary, SMB optional** - Avoid brittleness of file tailing
2. **Deterministic guardrails before Claude** - Regex patterns, known fixes, range checks first (cuts cost 10x)
3. **Minimal reload granularity** - Use `automation.reload`, `template.reload` not full restart
4. **Rollback as first-class operation** - Pre-change snapshots, one-click revert
5. **Expected range registry** - Structured YAML declaring valid ranges per sensor

### Security Requirements
- Read-only token for Phase 1, separate write token for Phase 2+
- Agent writes only to dedicated directory (e.g., `/config/agent_overlays/`)
- No direct edits to `.storage`
- Strip secrets before sending context to Claude

### Cost Optimization
- Deterministic classification first (most errors are pattern-matchable)
- Only call Claude for unknown/complex issues
- Batch daily analysis rather than continuous
- Estimated: **$3-15/month** in steady state

---

## Part 4: Open Questions for Next Session

### Need from user:
1. **HA Environment**
   - HA version (Core + Supervisor/OS version)?
   - Hardware? (HAOS on RPi/Green/Yellow, Docker, VM, etc.)

2. **PC Environment**
   - OS? (Appears to be Windows based on H:\ drive)
   - Docker or plain Python venv preference?
   - Network connectivity to HA on port 8123?

3. **Preferences**
   - Local web UI framework? (Default: FastAPI + htmx)
   - Notification method? (Browser, HA notification, email?)

### Will provide:
- Repo structure with `pyproject.toml`
- HA WebSocket subscription code for `state_changed` events
- REST polling for `/api/error_log`
- Expected range registry YAML schema pre-populated with HVAC entities
- Guardrail rules for known error patterns (recovery overflow, state_class mismatch)

---

## Tech Stack (Proposed)
```
Python 3.11+
├── homeassistant-api      # HA REST API client
├── websockets             # Real-time HA events
├── anthropic              # Claude API
├── fastapi + uvicorn      # Local web UI
├── pyyaml                 # Config parsing
├── watchdog               # File monitoring (optional)
└── sqlite                 # Local state/history
```

---

## Part 5: Recovery Rate Fix & Setback Efficiency - 2026-01-23

### Recovery Rate Issue
- **Problem:** Rolling average showed 12-13 min/°F instead of expected 2-3 min/°F
- **Cause:** One bad value (60.0) in slot 4 (1F) and slot 3 (2F) from clamped overflow
- **Fix:** Added safeguard in recovery_end automations:
  - Only store to rate slots if `recovery_minutes <= 120` AND `setback_degrees >= 1`
  - Invalid recoveries are discarded instead of stored with clamped values
- **Manual cleanup:** Set bad slots to 0, filled with average (~2.7 for 1F, ~3.0 for 2F)

### New Feature: Setback Efficiency Analysis
Tracks whether overnight setback is actually saving energy.

**New Input Helpers (per floor):**
- `input_number.hvac_*f_setback_start_runtime` - Runtime at setback start
- `input_number.hvac_*f_setback_start_outdoor_temp` - Outdoor temp at setback start
- `input_number.hvac_*f_recovery_start_runtime` - Runtime at recovery start
- `input_number.hvac_*f_overnight_runtime` - Overnight runtime (min)
- `input_number.hvac_*f_overnight_efficiency` - Overnight min/HDD
- `input_number.hvac_*f_recovery_efficiency` - Recovery min/HDD
- `input_datetime.hvac_*f_setback_start` - Setback start timestamp

**New Automations:**
- `hvac_1f_setback_start` / `hvac_2f_setback_start` - Triggers on setpoint drop ≥2°F
- Enhanced `hvac_*f_recovery_start` - Captures runtime, calculates overnight efficiency
- Enhanced `hvac_*f_recovery_end` - Calculates recovery efficiency

**New Sensors:**
- `sensor.hvac_1f_setback_net_benefit` / `sensor.hvac_2f_setback_net_benefit`
  - State: `baseline - (overnight + recovery)` in min/HDD
  - Positive = setback saving energy
  - Negative = setback costing energy
  - Attributes: overnight_efficiency, recovery_efficiency, baseline, interpretation

**Decision Logic:**
- `net_benefit > 5` → "Setback saving energy"
- `net_benefit < -5` → "Setback costing energy"
- Otherwise → "Marginal benefit"
