#!/usr/bin/env python3
"""
spc_validator.py — Diagnostic script for SPC chart troubleshooting.

Queries Home Assistant's SQLite database and REST API to validate:
  - Current state of SPC input_numbers (day_1..day_7 slots)
  - Current state of input_datetime capture stamps
  - Recent power/energy/runtime sensor data
  - Whether capture guard conditions would pass tonight

Usage:
  python3 spc_validator.py                    # Full diagnostic report
  python3 spc_validator.py --appliance hwh    # Single appliance
  python3 spc_validator.py --check-capture    # Just show capture readiness

Requires: sqlite3 (stdlib), optionally requests for live API queries.
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ===================== CONFIG =====================
DB = os.environ.get("HA_DB", "/config/home-assistant_v2.db")
TZ = ZoneInfo(os.environ.get("SPC_TZ", "America/New_York"))
HA_URL = os.environ.get("HA_URL", "http://homeassistant.local:8123")
HA_TOKEN = os.environ.get("HA_TOKEN", "")  # Long-lived access token

# SPC appliance definitions
APPLIANCES = {
    "fridge": {
        "power_sensor": "sensor.sem_fridge_power",
        "energy_sensor": "sensor.sem_fridge_daily",
        "runtime_sensor": "sensor.fridge_runtime_today",
        "threshold_input": "input_number.fridge_power_threshold",
        "threshold_default": 50,
        "day_slots": [f"input_number.fridge_running_watts_day_{i}" for i in range(1, 8)],
        "capture_stamp": "input_datetime.fridge_spc_last_capture",
        "daily_sensor": "sensor.fridge_running_watts_daily",
        "guard_runtime_min": 1.0,
        "guard_watts_min": 50,
        "guard_watts_max": 400,
        "energy_netting": None,
    },
    "furnace": {
        "power_sensor": "sensor.sem_furnace_power",
        "energy_sensor": "sensor.sem_furnace_daily",
        "runtime_sensor": "sensor.furnace_runtime_today",
        "threshold_input": "input_number.furnace_power_threshold",
        "threshold_default": 300,
        "day_slots": [f"input_number.furnace_running_watts_day_{i}" for i in range(1, 8)],
        "capture_stamp": "input_datetime.furnace_spc_last_capture",
        "daily_sensor": "sensor.furnace_running_watts_daily",
        "guard_runtime_min": 1.0,
        "guard_watts_min": 300,
        "guard_watts_max": 1000,
        "energy_netting": ("input_number.furnace_recirc_daily_kwh_estimate", 0.72),
    },
    "ac": {
        "power_sensor": "sensor.sem_ac_power",
        "energy_sensor": "sensor.sem_ac_daily",
        "runtime_sensor": "sensor.ac_runtime_today",
        "threshold_input": "input_number.ac_power_threshold",
        "threshold_default": 300,
        "day_slots": [f"input_number.ac_running_watts_day_{i}" for i in range(1, 8)],
        "capture_stamp": "input_datetime.ac_spc_last_capture",
        "daily_sensor": "sensor.ac_running_watts_daily",
        "guard_runtime_min": 0.5,
        "guard_watts_min": 500,
        "guard_watts_max": 5000,
        "energy_netting": None,
    },
    "hwh_recirc": {
        "power_sensor": "sensor.hwh_current_consumption",
        "energy_sensor": "sensor.hwh_recirc_energy_daily",  # NEW: gated energy
        "energy_sensor_old": "sensor.hwh_today_s_consumption",  # OLD: Kasa plug total
        "runtime_sensor": "sensor.hwh_recirc_runtime_today",
        "threshold_input": "input_number.hwh_recirc_power_threshold",
        "threshold_default": 70,
        "day_slots": [f"input_number.hwh_recirc_running_watts_day_{i}" for i in range(1, 8)],
        "capture_stamp": "input_datetime.hwh_recirc_spc_last_capture",
        "daily_sensor": "sensor.hwh_recirc_running_watts_daily",
        "guard_runtime_min": 0.1,
        "guard_watts_min": 80,
        "guard_watts_max": 200,
        "energy_netting": None,
        # Extra diagnostics for HWH
        "gated_power_sensor": "sensor.hwh_recirc_gated_power",
        "integration_sensor": "sensor.hwh_recirc_energy_total",
    },
    "dehumidifier": {
        "power_sensor": "sensor.dehumidifier_current_consumption",
        "energy_sensor": "sensor.dehumidifier_energy_daily",
        "runtime_sensor": "sensor.dehumidifier_runtime_today",
        "threshold_input": "input_number.dehumidifier_power_threshold",
        "threshold_default": 250,
        "day_slots": [f"input_number.dehumidifier_running_watts_day_{i}" for i in range(1, 8)],
        "capture_stamp": "input_datetime.dehumidifier_spc_last_capture",
        "daily_sensor": "sensor.dehumidifier_running_watts_daily",
        "guard_runtime_min": 0.5,
        "guard_watts_min": 300,
        "guard_watts_max": 800,
        "energy_netting": None,
    },
}


def log(*a):
    print("[spc_validator]", *a, file=sys.stderr)


def get_entity_state_from_db(con, entity_id):
    """Query current state from states_meta + states tables."""
    q = """
        SELECT s.state, s.last_updated_ts
        FROM states s
        JOIN states_meta sm ON s.metadata_id = sm.metadata_id
        WHERE sm.entity_id = ?
        ORDER BY s.last_updated_ts DESC
        LIMIT 1
    """
    row = con.execute(q, (entity_id,)).fetchone()
    if row:
        state, ts = row
        updated = datetime.fromtimestamp(ts, TZ) if ts else None
        return state, updated
    return None, None


def get_states_history(con, entity_id, hours=24):
    """Get state history for the past N hours."""
    cutoff = (datetime.now(TZ) - timedelta(hours=hours)).timestamp()
    q = """
        SELECT s.state, s.last_updated_ts
        FROM states s
        JOIN states_meta sm ON s.metadata_id = sm.metadata_id
        WHERE sm.entity_id = ? AND s.last_updated_ts >= ?
        ORDER BY s.last_updated_ts ASC
    """
    rows = con.execute(q, (entity_id, cutoff)).fetchall()
    return [(state, datetime.fromtimestamp(ts, TZ)) for state, ts in rows if ts]


def get_statistics_sum(con, entity_id, start_ts, end_ts):
    """Query statistics table for energy delta over a time range."""
    q = """
        SELECT SUM(delta) FROM (
            SELECT s.sum - LAG(s.sum) OVER (ORDER BY s.start_ts) AS delta
            FROM statistics s
            JOIN statistics_meta sm ON s.metadata_id = sm.id
            WHERE sm.statistic_id = ?
              AND s.start_ts >= ? - 3600 AND s.start_ts < ?
        ) WHERE delta >= 0
    """
    row = con.execute(q, (entity_id, start_ts, end_ts)).fetchone()
    return row[0] if row and row[0] else 0.0


def try_float(val, default=0.0):
    """Safely convert to float."""
    if val in (None, "unknown", "unavailable", ""):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def analyze_appliance(con, name, config):
    """Analyze a single appliance's SPC state."""
    print(f"\n{'='*60}")
    print(f"  {name.upper()} SPC ANALYSIS")
    print(f"{'='*60}")

    # Get current states
    threshold_val, _ = get_entity_state_from_db(con, config["threshold_input"])
    threshold = try_float(threshold_val, config["threshold_default"])
    print(f"\nThreshold: {threshold} W (from {config['threshold_input']})")
    if threshold == 0:
        print("  WARNING: Threshold is 0! This will gate on standby power.")
        print("  FIX: Set initial: value in YAML or set via Developer Tools.")

    # Get runtime
    runtime_val, runtime_ts = get_entity_state_from_db(con, config["runtime_sensor"])
    runtime = try_float(runtime_val, 0)
    print(f"\nRuntime Today: {runtime:.2f} h (updated: {runtime_ts})")
    print(f"  Guard requires: >= {config['guard_runtime_min']} h")
    runtime_ok = runtime >= config["guard_runtime_min"]
    print(f"  Status: {'PASS' if runtime_ok else 'FAIL'}")

    # Get energy
    energy_val, energy_ts = get_entity_state_from_db(con, config["energy_sensor"])
    energy = try_float(energy_val, 0)
    print(f"\nEnergy Today: {energy:.4f} kWh (from {config['energy_sensor']})")

    # For HWH, also show old vs new energy source
    if "energy_sensor_old" in config:
        old_energy_val, _ = get_entity_state_from_db(con, config["energy_sensor_old"])
        old_energy = try_float(old_energy_val, 0)
        print(f"  Plug total (OLD source): {old_energy:.4f} kWh")
        print(f"  Gated recirc (NEW source): {energy:.4f} kWh")
        if old_energy > 0 and energy > 0:
            standby = old_energy - energy
            print(f"  Standby+condensate delta: {standby:.4f} kWh (~{standby*1000/24:.1f}W avg)")

    # Apply energy netting if configured
    net_energy = energy
    if config["energy_netting"]:
        netting_input, netting_default = config["energy_netting"]
        netting_val, _ = get_entity_state_from_db(con, netting_input)
        netting = try_float(netting_val, netting_default)
        net_energy = energy - netting
        print(f"  Netting: -{netting:.3f} kWh ({netting_input})")
        print(f"  Net energy: {net_energy:.4f} kWh")

    # Compute capture watts
    if runtime > 0:
        computed_w = (net_energy * 1000) / runtime
    else:
        computed_w = -1
    print(f"\nComputed Watts: {computed_w:.1f} W (energy*1000/runtime)")
    print(f"  Guard requires: {config['guard_watts_min']} < W <= {config['guard_watts_max']}")
    watts_ok = config["guard_watts_min"] < computed_w <= config["guard_watts_max"]
    print(f"  Status: {'PASS' if watts_ok else 'FAIL'}")

    # Overall capture readiness
    capture_ready = runtime_ok and watts_ok
    print(f"\n>>> CAPTURE TONIGHT: {'WILL SUCCEED' if capture_ready else 'WILL SKIP'}")
    if not capture_ready:
        if not runtime_ok:
            print(f"    Reason: Insufficient runtime ({runtime:.2f} < {config['guard_runtime_min']} h)")
        if not watts_ok:
            print(f"    Reason: Computed watts outside guard band ({computed_w:.1f} not in ({config['guard_watts_min']}, {config['guard_watts_max']}])")

    # Show day slots
    print(f"\n7-Day Buffer (day_1=yesterday, day_7=oldest):")
    slot_values = []
    for i, slot in enumerate(config["day_slots"], 1):
        val, _ = get_entity_state_from_db(con, slot)
        v = try_float(val, 0)
        slot_values.append(v)
        marker = " <-- most recent" if i == 1 else ""
        print(f"  day_{i}: {v:6.1f} W{marker}")

    valid = [v for v in slot_values if 0 < v <= config["guard_watts_max"]]
    if valid:
        mean = sum(valid) / len(valid)
        print(f"  Mean ({len(valid)} valid): {mean:.1f} W")
    else:
        print("  Mean: N/A (no valid slots)")

    # Show capture stamp
    stamp_val, _ = get_entity_state_from_db(con, config["capture_stamp"])
    print(f"\nLast Capture Stamp: {stamp_val}")
    if stamp_val and stamp_val not in ("unknown", "unavailable"):
        try:
            stamp_date = datetime.strptime(stamp_val, "%Y-%m-%d").date()
            days_ago = (datetime.now(TZ).date() - stamp_date).days
            print(f"  Days since capture: {days_ago}")
            if days_ago > 1:
                print("  WARNING: Stamp > 1 day old -> Daily sensor will be UNAVAILABLE")
        except ValueError:
            print(f"  WARNING: Could not parse stamp date: {stamp_val}")
    else:
        print("  WARNING: Stamp not set -> Daily sensor will be UNAVAILABLE")

    # Show daily sensor state
    daily_val, daily_ts = get_entity_state_from_db(con, config["daily_sensor"])
    print(f"\nDaily Sensor: {daily_val} (updated: {daily_ts})")

    # HWH-specific: check gated power chain
    if "gated_power_sensor" in config:
        print(f"\n--- HWH Gated Power Chain ---")
        gated_val, _ = get_entity_state_from_db(con, config["gated_power_sensor"])
        print(f"  Gated Power: {gated_val} W")
        integ_val, _ = get_entity_state_from_db(con, config["integration_sensor"])
        print(f"  Integration Total: {integ_val} kWh")
        print(f"  Daily Meter: {energy:.4f} kWh")

    return {
        "name": name,
        "capture_ready": capture_ready,
        "runtime": runtime,
        "computed_w": computed_w,
        "day_1": slot_values[0] if slot_values else 0,
        "stamp": stamp_val,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="SPC Chart Validator")
    ap.add_argument("--appliance", "-a", choices=list(APPLIANCES.keys()),
                    help="Analyze single appliance")
    ap.add_argument("--check-capture", "-c", action="store_true",
                    help="Show capture readiness summary only")
    ap.add_argument("--db", default=DB, help=f"HA database path (default: {DB})")
    args = ap.parse_args(argv)

    print(f"SPC Validator - {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Database: {args.db}")

    if not os.path.exists(args.db):
        log(f"ERROR: Database not found: {args.db}")
        log("Set HA_DB environment variable or use --db flag")
        return 1

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True, timeout=30)
    try:
        if args.appliance:
            appliances = {args.appliance: APPLIANCES[args.appliance]}
        else:
            appliances = APPLIANCES

        results = []
        for name, config in appliances.items():
            result = analyze_appliance(con, name, config)
            results.append(result)

        # Summary
        print(f"\n{'='*60}")
        print("  SUMMARY")
        print(f"{'='*60}")
        print(f"\n{'Appliance':<15} {'Capture':<12} {'Runtime':<10} {'Watts':<10} {'Day1':<8} {'Stamp'}")
        print("-" * 75)
        for r in results:
            status = "READY" if r["capture_ready"] else "SKIP"
            print(f"{r['name']:<15} {status:<12} {r['runtime']:.2f} h     {r['computed_w']:>6.1f} W   {r['day_1']:>6.1f}   {r['stamp'] or 'unset'}")

        # Recommendations
        print(f"\n--- RECOMMENDATIONS ---")
        for r in results:
            if not r["capture_ready"]:
                print(f"\n{r['name'].upper()}:")
                if r["runtime"] < APPLIANCES[r["name"]]["guard_runtime_min"]:
                    print(f"  - Insufficient runtime. Check if threshold is too high.")
                    print(f"    Current threshold can be checked in Developer Tools > States")
                if r["computed_w"] <= APPLIANCES[r["name"]]["guard_watts_min"]:
                    print(f"  - Computed watts too LOW. Possible causes:")
                    print(f"    * Energy sensor not accumulating (check hwh_recirc_gated_power chain)")
                    print(f"    * Utility meter not resetting correctly")
                elif r["computed_w"] > APPLIANCES[r["name"]]["guard_watts_max"]:
                    print(f"  - Computed watts too HIGH. Possible causes:")
                    print(f"    * Using wrong energy source (old Kasa total vs new gated)")
                    print(f"    * Energy netting value incorrect")

        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
