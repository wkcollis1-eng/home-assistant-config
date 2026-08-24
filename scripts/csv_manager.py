#!/usr/bin/env python3
"""
CSV Manager for Home Assistant HVAC Reports
Replaces complex shell one-liners with maintainable Python.

Usage from shell_command:
  python3 /config/scripts/csv_manager.py append_daily --data '{"date":"2026-02-08",...}'
  python3 /config/scripts/csv_manager.py append_setback --zone 1F --data '{"overnight_low":3.8,...}'
  python3 /config/scripts/csv_manager.py rotate_daily
  python3 /config/scripts/csv_manager.py backup --data '{"hdd_year":397,...}'
"""

import argparse
import csv
import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base path for reports
REPORTS_DIR = Path("/config/reports")

# CSV schemas (header definitions)
SCHEMAS = {
    "daily": [
        "date", "outdoor_high", "outdoor_low", "outdoor_mean", "hdd65", "cdd65",
        "furnace_runtime_min", "furnace_cycles", "avg_min_per_cycle",
        "zone_calls_total", "chaining_index", "runtime_1f_min", "runtime_2f_min",
        "basement_dew_point",
        "ac_runtime_min", "ac_cycles", "ac_min_per_cycle",
        "cool_calls_total", "cool_runtime_1f_min", "cool_runtime_2f_min",
        "dehumidifier_kwh",
    ],
    "monthly": [
        "month", "days", "mean_outdoor_temp", "total_hdd65", "total_cdd65",
        "furnace_runtime_hours", "avg_runtime_per_hdd", "heating_efficiency_ccf_per_1k_hdd",
        "actual_runtime", "expected_runtime", "efficiency_deviation_pct",
        "gas_usage_ccf", "gas_cost", "electric_kwh",
        "avg_runtime_per_cdd", "ac_runtime_hours", "ac_cycles_total", "ac_mpc_mean",
        "furnace_mpc_mean", "furnace_mpc_sigma", "furnace_short_cycle_pct",
        "furnace_cycles_total", "chaining_index_mean",
        "dehumidifier_kwh",
    ],
    "setback": [
        "date", "hold_setpoint", "setback_setpoint", "setback_degrees",
        "recovery_start_temp", "degrees_to_recover", "recovery_minutes",
        "min_per_degree", "outdoor_temp",
    ],
    # Extended 2026-07-03: the schema previously stopped at hdd_d7 while the
    # backup_input_numbers shell_command had grown to ~58 keys; append_row
    # builds rows in schema order, so every unlisted key was SILENTLY DROPPED
    # from the disaster-recovery record (all AC accumulators, CDD windows, SPC
    # seeds, min-per-cycle windows). ensure_csv_exists migrates the existing
    # CSV by column name, so old rows keep their data and gain blank new cols.
    "backup": [
        "timestamp", "hdd_year", "hdd_month", "cdd_year", "cdd_month", "filter_hrs",
        "temp_sum", "temp_days", "expected_runtime",
        "hdd_d1", "hdd_d2", "hdd_d3", "hdd_d4", "hdd_d5", "hdd_d6", "hdd_d7",
        "furnace_rt_acc", "furnace_cy_acc",
        "z1f_rt_acc", "z2f_rt_acc", "z1f_cy_acc", "z2f_cy_acc",
        "ac_rt_acc", "ac_cy_acc",
        "z1f_cool_rt_acc", "z2f_cool_rt_acc", "z1f_cool_cy_acc", "z2f_cool_cy_acc",
        "cdd_d1", "cdd_d2", "cdd_d3", "cdd_d4", "cdd_d5", "cdd_d6", "cdd_d7",
        "cdd_seed_mean", "cdd_seed_stddev",
        "rpc_d1", "rpc_d2", "rpc_d3", "rpc_d4", "rpc_d5", "rpc_d6", "rpc_d7",
        "fmpc_d1", "fmpc_d2", "fmpc_d3", "fmpc_d4", "fmpc_d5", "fmpc_d6", "fmpc_d7",
        "ampc_d1", "ampc_d2", "ampc_d3", "ampc_d4", "ampc_d5", "ampc_d6", "ampc_d7",
    ]
}

ONE_DECIMAL_COLUMNS = {
    # outdoor / climate
    "outdoor_high", "outdoor_low", "outdoor_mean", "hdd65", "cdd65",
    # furnace daily
    "furnace_runtime_min", "avg_min_per_cycle", "chaining_index",
    "runtime_1f_min", "runtime_2f_min", "basement_dew_point",
    # AC / cooling daily
    "ac_runtime_min", "ac_min_per_cycle",
    "cool_runtime_1f_min", "cool_runtime_2f_min",
    # monthly furnace
    "furnace_runtime_hours", "avg_runtime_per_hdd",
    "heating_efficiency_ccf_per_1k_hdd", "mean_outdoor_temp",
    "total_hdd65", "total_cdd65", "efficiency_deviation_pct",
    "furnace_mpc_mean", "furnace_mpc_sigma", "furnace_short_cycle_pct",
    "chaining_index_mean",
    # monthly AC
    "avg_runtime_per_cdd", "ac_runtime_hours", "ac_mpc_mean",
    # bill quantities — one decimal, not integer (moved 2026-07-03: integer
    # rounding cost +-0.5 CCF / +-0.5 kWh per row against the store/display-
    # precision-finer-than-process-sigma standard)
    "gas_usage_ccf", "electric_kwh",
    # setback
    "overnight_low", "setback_depth", "setback_degrees", "recovery_rate",
    "recovery_minutes", "hold_setpoint", "setback_setpoint",
    "recovery_start_temp", "degrees_to_recover", "min_per_degree", "outdoor_temp",
}

INTEGER_COLUMNS = {
    "furnace_cycles", "zone_calls_total",
    "ac_cycles", "cool_calls_total",
    "furnace_cycles_total", "ac_cycles_total",
    "days",
    "total_runtime", "expected_hold", "net_runtime",
}


def ensure_csv_exists(filepath: Path, schema_name: str) -> None:
    """Create CSV with header if missing; otherwise reconcile the existing
    header to the current schema (append-only migration), remapping rows by
    column name so new columns are added blank without shifting old data.

    HALTS (raises ValueError) if the file has mixed-width rows or columns the
    current schema would drop, so misaligned data is never silently corrupted
    -- repair the file by hand, then re-run.
    """
    schema = SCHEMAS[schema_name]

    if not filepath.exists():
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', newline='') as f:
            csv.writer(f, quoting=csv.QUOTE_ALL).writerow(schema)
        logger.info(f"Created new CSV: {filepath}")
        return

    with open(filepath, 'r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader, [])
        rows = list(reader)

    if not header:
        with open(filepath, 'w', newline='') as f:
            csv.writer(f, quoting=csv.QUOTE_ALL).writerow(schema)
        logger.info(f"Wrote header to empty CSV: {filepath}")
        return

    if header == schema:
        return

    width = len(header)
    bad = [i for i, r in enumerate(rows, start=2) if len(r) != width]
    if bad:
        sample = bad[:5]
        raise ValueError(
            f"{filepath.name}: header has {width} columns but data rows "
            f"{sample}{'...' if len(bad) > 5 else ''} have a different count; "
            f"refusing to migrate a mixed-width file. Repair it manually first."
        )

    dropped = [c for c in header if c not in schema]
    if dropped:
        raise ValueError(
            f"{filepath.name}: existing columns {dropped} are absent from the "
            f"current '{schema_name}' schema; refusing to drop data. Update "
            f"the schema or migrate manually."
        )

    migrated = [dict(zip(header, r)) for r in rows]
    atomic_write_dict_rows(filepath, schema, migrated)
    added = [c for c in schema if c not in header]
    logger.info(
        f"Migrated {filepath.name}: added {added}, "
        f"{len(migrated)} rows preserved."
    )


def row_exists(filepath: Path, key_column: str, key_value: str) -> bool:
    """Check if a row with the given key already exists."""
    if not filepath.exists():
        return False

    with open(filepath, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get(key_column) == key_value:
                return True
    return False


def atomic_write_dict_rows(filepath: Path, fieldnames: list, rows: list) -> None:
    """Write CSV rows via temp file + atomic rename to avoid truncation-loss on failures."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{filepath.name}.",
        suffix=".tmp",
        dir=str(filepath.parent)
    )
    try:
        with os.fdopen(fd, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, filepath)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def validate_data(data: dict, schema_name: str, required_fields: list = None) -> bool:
    """Validate data against schema and check for invalid values."""
    schema = SCHEMAS[schema_name]

    # Check required fields
    if required_fields:
        for field in required_fields:
            if field not in data or data[field] is None:
                logger.error(f"Missing required field: {field}")
                return False

    # Schema-specific validation
    if schema_name == "daily":
        # Check for corrupt temperature values
        high = float(data.get("outdoor_high", -999))
        low = float(data.get("outdoor_low", 999))
        if high <= -49 or low >= 149:
            logger.error(f"Invalid temperature values: high={high}, low={low}")
            return False
        if float(data.get("hdd65", -1)) < 0:
            logger.error(f"Invalid HDD value: {data.get('hdd65')}")
            return False
        if float(data.get("cdd65", -1)) < 0:
            logger.error(f"Invalid CDD value: {data.get('cdd65')}")
            return False
        # AC values optional (zero on non-cooling days) but must be non-negative
        ac_rt = float(data.get("ac_runtime_min", 0))
        ac_cy = int(float(data.get("ac_cycles", 0)))
        ac_mpc = float(data.get("ac_min_per_cycle", 0))
        if ac_rt < 0 or ac_cy < 0 or ac_mpc < 0:
            logger.error(f"Invalid AC values: runtime={ac_rt}, cycles={ac_cy}, mpc={ac_mpc}")
            return False
        # If cycles reported, runtime must be non-zero (and vice versa)
        if (ac_cy > 0) != (ac_rt > 0):
            logger.warning(f"AC cycle/runtime mismatch: cycles={ac_cy}, runtime={ac_rt} — writing anyway")

    elif schema_name == "setback":
        degrees = float(data.get("degrees_to_recover", 0))
        recovery = float(data.get("recovery_minutes", 0))
        mpc = float(data.get("min_per_degree", 0))
        if degrees < 1 or recovery <= 0 or mpc <= 0:
            logger.warning(
                f"Invalid setback data: degrees_to_recover={degrees}, "
                f"recovery_minutes={recovery}, min_per_degree={mpc}"
            )
            return False

    return True


def append_row(filepath: Path, data: dict, schema_name: str) -> bool:
    """Append a row to CSV file."""
    schema = SCHEMAS[schema_name]

    # Build row in schema order
    row = []
    for col in schema:
        value = data.get(col, "")
        # Round numeric values; pass through strings/dates/zones unchanged.
        if value is None:
            value = ""
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            number = float(value)
            if col in ONE_DECIMAL_COLUMNS:
                value = round(number, 1)
            elif col in INTEGER_COLUMNS:
                value = int(round(number))
            else:
                value = round(number, 2)
        row.append(value)

    with open(filepath, 'a', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(row)

    logger.info(f"Appended row to {filepath}")
    return True


def cmd_append_daily(args):
    """Append to daily HVAC CSV."""
    data = json.loads(args.data)
    filepath = REPORTS_DIR / f"hvac_daily_{datetime.now().year}.csv"

    ensure_csv_exists(filepath, "daily")

    # Check for duplicate
    date_key = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    if row_exists(filepath, "date", date_key):
        logger.info(f"Row for {date_key} already exists, skipping")
        return True

    # Validate
    if not validate_data(data, "daily"):
        logger.error("Daily data validation failed")
        return False

    return append_row(filepath, data, "daily")


def cmd_update_monthly(args):
    """Patch computed stats into an existing monthly row.

    Reads the monthly CSV, finds the row matching data['month'], merges the
    supplied fields into it (supplied fields overwrite; others are preserved),
    then atomically rewrites the file. If no matching row exists, appends a new
    one so the function is safe to call before appendmonthlycsv has run.
    """
    data = json.loads(args.data)
    filepath = REPORTS_DIR / "hvac_monthly.csv"
    schema = SCHEMAS["monthly"]

    ensure_csv_exists(filepath, "monthly")

    month_key = data.get("month")
    if not month_key:
        logger.error("update_monthly requires 'month' field in data")
        return False

    with open(filepath, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    matched = False
    for row in rows:
        if row.get("month") == month_key:
            row.update({k: v for k, v in data.items() if k in schema})
            matched = True
            break

    if not matched:
        # Row doesn't exist yet — build a sparse row and append
        new_row = {col: data.get(col, "") for col in schema}
        rows.append(new_row)
        logger.info(f"update_monthly: no existing row for {month_key}, appended new row")
    else:
        logger.info(f"update_monthly: patched {len(data)-1} fields into {month_key}")

    # Reformat numeric fields before writing
    for row in rows:
        for col, val in row.items():
            if val == "" or val is None:
                continue
            try:
                num = float(val)
                if col in ONE_DECIMAL_COLUMNS:
                    row[col] = round(num, 1)
                elif col in INTEGER_COLUMNS:
                    row[col] = int(round(num))
                # gas_cost and other 2-decimal cols: leave as-is (already formatted)
            except (ValueError, TypeError):
                pass  # string fields like 'month' — leave unchanged

    atomic_write_dict_rows(filepath, schema, rows)
    return True


def cmd_append_monthly(args):
    """Append to monthly HVAC CSV."""
    data = json.loads(args.data)
    filepath = REPORTS_DIR / "hvac_monthly.csv"

    ensure_csv_exists(filepath, "monthly")

    # Check for duplicate
    month_key = data.get("month", datetime.now().strftime("%Y-%m"))
    if row_exists(filepath, "month", month_key):
        logger.info(f"Row for {month_key} already exists, skipping")
        return True

    return append_row(filepath, data, "monthly")


def cmd_append_setback(args):
    """Append to per-zone setback CSV (hvac_setback_1f.csv / hvac_setback_2f.csv)."""
    data = json.loads(args.data)
    data["date"] = data.get("date", datetime.now().strftime("%Y-%m-%d %H:%M"))

    zone_suffix = args.zone.lower()  # "1f" or "2f"
    filepath = REPORTS_DIR / f"hvac_setback_{zone_suffix}.csv"

    ensure_csv_exists(filepath, "setback")

    # Validate before appending
    if not validate_data(data, "setback"):
        logger.error("Setback data validation failed - not appending")
        return False

    return append_row(filepath, data, "setback")


def cmd_backup(args):
    """Backup input_number values."""
    data = json.loads(args.data)
    data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    filepath = REPORTS_DIR / "input_number_backup.csv"

    ensure_csv_exists(filepath, "backup")

    return append_row(filepath, data, "backup")


def cmd_rotate_daily(args):
    """Rotate daily CSV at year boundary."""
    year = datetime.now().year
    curr_file = REPORTS_DIR / f"hvac_daily_{year}.csv"

    if curr_file.exists():
        logger.info(f"Current year file already exists: {curr_file}")
        return True

    # Create new file with header
    ensure_csv_exists(curr_file, "daily")
    logger.info(f"Created new daily CSV for {year}")
    return True


def cmd_rotate_setback(args):
    """Archive previous year's setback data in per-zone files."""
    year = datetime.now().year
    prev_year = year - 1

    for zone in ("1f", "2f"):
        src_file = REPORTS_DIR / f"hvac_setback_{zone}.csv"
        archive_file = REPORTS_DIR / f"hvac_setback_{zone}_{prev_year}.csv"

        if not src_file.exists():
            logger.warning(f"Source setback file doesn't exist: {src_file}")
            continue

        with open(src_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            all_rows = list(reader)

        prev_year_rows = [r for r in all_rows if r.get("date", "").startswith(str(prev_year))]
        curr_year_rows = [r for r in all_rows if not r.get("date", "").startswith(str(prev_year))]

        if prev_year_rows:
            atomic_write_dict_rows(archive_file, SCHEMAS["setback"], prev_year_rows)
            logger.info(f"Archived {len(prev_year_rows)} rows to {archive_file}")

        atomic_write_dict_rows(src_file, SCHEMAS["setback"], curr_year_rows)
        logger.info(f"Kept {len(curr_year_rows)} rows in {src_file}")

    return True


def main():
    parser = argparse.ArgumentParser(description="CSV Manager for HA HVAC Reports")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # append_daily
    p_daily = subparsers.add_parser("append_daily", help="Append to daily CSV")
    p_daily.add_argument("--data", required=True, help="JSON data")
    p_daily.set_defaults(func=cmd_append_daily)

    # update_monthly
    p_update_monthly = subparsers.add_parser("update_monthly", help="Patch computed stats into monthly row")
    p_update_monthly.add_argument("--data", required=True, help="JSON data (must include 'month')")
    p_update_monthly.set_defaults(func=cmd_update_monthly)

    # append_monthly
    p_monthly = subparsers.add_parser("append_monthly", help="Append to monthly CSV")
    p_monthly.add_argument("--data", required=True, help="JSON data")
    p_monthly.set_defaults(func=cmd_append_monthly)

    # append_setback
    p_setback = subparsers.add_parser("append_setback", help="Append to setback log")
    p_setback.add_argument("--zone", required=True, choices=["1F", "2F"], help="Zone")
    p_setback.add_argument("--data", required=True, help="JSON data")
    p_setback.set_defaults(func=cmd_append_setback)

    # backup
    p_backup = subparsers.add_parser("backup", help="Backup input numbers")
    p_backup.add_argument("--data", required=True, help="JSON data")
    p_backup.set_defaults(func=cmd_backup)

    # rotate_daily
    p_rot_daily = subparsers.add_parser("rotate_daily", help="Rotate daily CSV")
    p_rot_daily.set_defaults(func=cmd_rotate_daily)

    # rotate_setback
    p_rot_setback = subparsers.add_parser("rotate_setback", help="Rotate setback log")
    p_rot_setback.set_defaults(func=cmd_rotate_setback)

    args = parser.parse_args()

    try:
        success = args.func(args)
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.exception(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
