#!/usr/bin/env python3
"""
lifepo4_export.py — Weekly LiFePO4 battery data export from HA recorder DB.

Exports to /config/lifepo4_exports/ (accessible via Samba at \\\\homeassistant\\config\\lifepo4_exports\\)

Outputs per run:
  data/combined_output.csv          — appends new hourly voltage rows (DD/MM/YYYY format, local time)
  data/combined_temperature.csv     — appends new hourly temperature rows (°F, local time)
  data/combined_humidity.csv        — appends new hourly humidity rows (%, local time)
  data/high_freq_voltage/           — new weekly HF file (entity_id, voltage, last_changed LOCAL time)

All timestamps use HA Green local time (America/New_York, DST-aware).

Run: python3 /config/scripts/lifepo4_export.py
Called by shell_command.export_lifepo4_weekly every Sunday at 22:30.
"""

import sqlite3
import csv
import sys
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = "/config/home-assistant_v2.db"
EXPORT_DIR = Path("/config/lifepo4_exports/data")
HF_DIR = EXPORT_DIR / "high_freq_voltage"

# HA Green local timezone — handles EST (UTC-5) and EDT (UTC-4) automatically
HA_TZ = ZoneInfo("America/New_York")

# Entity IDs — do not correct the 'voltge' typo, it is intentional
VOLTAGE_ENTITY = "sensor.shelly_plus_uni_voltge"
TEMP_ENTITY = "sensor.shelly_temperature_humidity_temperature"
HUMIDITY_ENTITY = "sensor.shelly_temperature_humidity_humidity"

# How many days to query (must be < recorder purge_keep_days=14)
EXPORT_DAYS = 8  # one day overlap guards against Sunday timing edge cases

# Voltage sanity bounds — reject EMI spikes and sensor errors for hourly CSV
# (HF file keeps all raw readings including spikes, matching existing repo data)
VOLTAGE_MIN = 10.0
VOLTAGE_MAX = 16.0

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("lifepo4_export")

# ============================================================================
# DB HELPERS
# ============================================================================


def get_metadata_id(cursor, entity_id):
    """Return metadata_id for an entity_id (HA 2023+ schema)."""
    cursor.execute(
        "SELECT metadata_id FROM states_meta WHERE entity_id = ?", (entity_id,)
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Entity not found in states_meta: {entity_id}")
    return row[0]


def query_states(cursor, metadata_id, since_ts):
    """
    Return all states for metadata_id since since_ts (Unix float).
    Excludes unknown/unavailable. Returns list of (state_str, last_updated_ts).
    """
    cursor.execute(
        """
        SELECT state, last_updated_ts
        FROM states
        WHERE metadata_id = ?
          AND last_updated_ts >= ?
          AND state NOT IN ('unknown', 'unavailable', '')
        ORDER BY last_updated_ts ASC
        """,
        (metadata_id, since_ts),
    )
    return cursor.fetchall()


# ============================================================================
# TIMESTAMP HELPERS
# ============================================================================


def ts_to_local_parts(ts_float):
    """
    Convert Unix float timestamp to HA Green local time (America/New_York,
    DST-aware). Returns (date_str DD/MM/YYYY, hour_str HH:00).

    Matches the Date/Time columns in combined_output.csv, combined_temperature.csv,
    and combined_humidity.csv.
    """
    dt_local = datetime.fromtimestamp(ts_float, tz=HA_TZ)
    return dt_local.strftime("%d/%m/%Y"), dt_local.strftime("%H:00")


def ts_to_local_iso(ts_float):
    """
    Convert Unix float to ISO 8601 local time string with UTC offset.
    Format: YYYY-MM-DD HH:MM:SS.ffffff±HHMM  (e.g. 2025-03-01 18:45:12.345678-0500)
    Used for the last_changed column in HF voltage files.
    """
    dt_local = datetime.fromtimestamp(ts_float, tz=HA_TZ)
    return dt_local.strftime("%Y-%m-%d %H:%M:%S.%f%z")


# ============================================================================
# EXPORT: HIGH-FREQUENCY VOLTAGE FILE (weekly)
# ============================================================================


def export_hf_voltage(cursor, metadata_id, since_ts, week_start, week_end):
    """
    Write a new weekly HF file: voltage_data_YYYY-MM-DD_to_YYYY-MM-DD.csv
    Columns: entity_id, voltage, last_changed  (local time, DST-aware)
    Keeps all raw readings including spikes — analysis script handles filtering.
    """
    rows = query_states(cursor, metadata_id, since_ts)
    if not rows:
        log.warning("No HF voltage data found in query window")
        return 0

    filename = f"voltage_data_{week_start}_to_{week_end}.csv"
    out_path = HF_DIR / filename

    if out_path.exists():
        log.info(f"HF file already exists, skipping: {filename}")
        return 0

    written = 0
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["entity_id", "voltage", "last_changed"])
        for state_str, ts in rows:
            try:
                float(state_str)  # validate numeric
            except ValueError:
                continue
            writer.writerow([VOLTAGE_ENTITY, state_str, ts_to_local_iso(ts)])
            written += 1

    log.info(f"HF export: {written} records → {filename}")
    return written


# ============================================================================
# EXPORT: HOURLY AGGREGATES (append to cumulative CSVs)
# ============================================================================


def build_hourly_aggregates(rows, value_min=None, value_max=None):
    """
    Aggregate (state_str, ts_float) rows into hourly min/max buckets.
    Timestamps are bucketed by HA Green local hour (America/New_York, DST-aware).
    Returns dict keyed by (date_str DD/MM/YYYY, hour_str HH:00) → (min_val, max_val).
    """
    buckets = {}
    for state_str, ts in rows:
        try:
            val = float(state_str)
        except ValueError:
            continue
        if value_min is not None and val < value_min:
            continue
        if value_max is not None and val > value_max:
            continue
        date_str, hour_str = ts_to_local_parts(ts)
        key = (date_str, hour_str)
        if key not in buckets:
            buckets[key] = (val, val)
        else:
            cur_min, cur_max = buckets[key]
            buckets[key] = (min(cur_min, val), max(cur_max, val))
    return buckets


def _bucket_sort_key(item):
    """Sort key for hourly bucket items: parses DD/MM/YYYY HH:00 into a datetime."""
    (date_str, hour_str), _ = item
    return datetime.strptime(f"{date_str} {hour_str}", "%d/%m/%Y %H:%M")


def append_hourly_csv(csv_path, header, new_rows):
    """
    Append new_rows to csv_path, skipping rows already present (by date+time key).
    new_rows: list of dicts with keys matching header.
    Returns count of rows written.
    """
    # Read existing keys to avoid duplicates
    existing_keys = set()
    if csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_keys.add((row["Date"], row["Time"]))

    written = 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if csv_path.stat().st_size == 0:
            writer.writeheader()
        for row in new_rows:
            key = (row["Date"], row["Time"])
            if key in existing_keys:
                continue
            writer.writerow(row)
            written += 1

    return written


def export_hourly_voltage(cursor, metadata_id, since_ts, csv_path):
    rows = query_states(cursor, metadata_id, since_ts)
    buckets = build_hourly_aggregates(
        rows, value_min=VOLTAGE_MIN, value_max=VOLTAGE_MAX
    )

    sorted_rows = [
        {"Date": d, "Time": t, "Min": round(mn, 3), "Max": round(mx, 3)}
        for (d, t), (mn, mx) in sorted(buckets.items(), key=_bucket_sort_key)
    ]
    n = append_hourly_csv(csv_path, ["Date", "Time", "Min", "Max"], sorted_rows)
    log.info(f"Hourly voltage: {n} new rows appended → {csv_path.name}")
    return n


def export_hourly_sensor(cursor, metadata_id, since_ts, csv_path, value_col):
    """Generic hourly export for temperature or humidity (single value column)."""
    rows = query_states(cursor, metadata_id, since_ts)
    buckets = build_hourly_aggregates(rows)

    sorted_rows = []
    for (d, t), (mn, mx) in sorted(buckets.items(), key=_bucket_sort_key):
        row = {"Date": d, "Time": t}
        row["Min"] = round(mn, 2)
        row["Max"] = round(mx, 2)
        sorted_rows.append(row)

    n = append_hourly_csv(csv_path, ["Date", "Time", "Min", "Max"], sorted_rows)
    log.info(f"Hourly {value_col}: {n} new rows appended → {csv_path.name}")
    return n


# ============================================================================
# MAIN
# ============================================================================


def main():
    log.info("=" * 60)
    log.info("LiFePO4 weekly export starting")

    # Log the active local timezone offset for diagnostic confirmation
    now_local = datetime.now(HA_TZ)
    utc_offset = now_local.strftime("%Z %z")  # e.g. "EST -0500" or "EDT -0400"
    log.info(f"HA Green local timezone: America/New_York  ({utc_offset})")

    # Create output directories
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    HF_DIR.mkdir(parents=True, exist_ok=True)

    # Compute time window
    now_utc = datetime.now(timezone.utc)
    since_dt = now_utc - timedelta(days=EXPORT_DAYS)
    since_ts = since_dt.timestamp()

    # Week boundary strings for HF filename (local date, not UTC)
    week_start = (now_local - timedelta(days=6)).strftime("%Y-%m-%d")
    week_end = now_local.strftime("%Y-%m-%d")

    log.info(f"Query window: {since_dt.strftime('%Y-%m-%d %H:%M UTC')} → now")
    log.info(f"HF file will cover: {week_start} to {week_end}  (local dates)")

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Resolve metadata IDs
        try:
            v_meta = get_metadata_id(cursor, VOLTAGE_ENTITY)
            t_meta = get_metadata_id(cursor, TEMP_ENTITY)
            rh_meta = get_metadata_id(cursor, HUMIDITY_ENTITY)
        except ValueError as e:
            log.error(f"Entity lookup failed: {e}")
            log.error("Check entity IDs in script CONFIGURATION block")
            sys.exit(1)

        # 1 — HF voltage file (weekly, new file each run, local timestamps)
        hf_count = export_hf_voltage(cursor, v_meta, since_ts, week_start, week_end)

        # 2 — Hourly voltage (append to combined_output.csv, local time buckets)
        export_hourly_voltage(
            cursor, v_meta, since_ts, EXPORT_DIR / "combined_output.csv"
        )

        # 3 — Hourly temperature (append to combined_temperature.csv)
        export_hourly_sensor(
            cursor,
            t_meta,
            since_ts,
            EXPORT_DIR / "combined_temperature.csv",
            "temperature",
        )

        # 4 — Hourly humidity (append to combined_humidity.csv)
        export_hourly_sensor(
            cursor, rh_meta, since_ts, EXPORT_DIR / "combined_humidity.csv", "humidity"
        )

        conn.close()

    except sqlite3.Error as e:
        log.error(f"Database error: {e}")
        sys.exit(1)

    log.info("Export complete")
    log.info("Files ready at: /config/lifepo4_exports/data/")
    log.info("Samba path:     \\\\homeassistant\\config\\lifepo4_exports\\data\\")
    log.info("=" * 60)
    return hf_count


if __name__ == "__main__":
    main()
