#!/usr/bin/env python3
"""
Climate Norms Lookup Script for Home Assistant
Reads climate_daily_norms_bdl.csv and outputs today's expected values as JSON.
Run daily at midnight via command_line sensor.
"""

import calendar
import csv
import json
from datetime import datetime
from pathlib import Path

# Path to climate norms CSV (relative to HA config directory)
# 2026-09-23: was climate_daily_norms.csv (kept, unused), which is NOT BDL data -
# annual 6,128 HDD vs the NCEI 1991-2020 BDL normal 5,873 [M]. The _bdl file is
# built by scripts/build_bdl_daily_norms.py from ACIS (see its header).
CSV_PATH = Path(__file__).parent.parent / "climate_daily_norms_bdl.csv"
SOURCE = "NCEI 1991-2020 daily normals, Bradley BDL (ACIS)"


def _key(dt):
    """(month, day) row key. The CSV has no Feb 29 row; Feb 29 uses Feb 28."""
    return (2, 28) if (dt.month, dt.day) == (2, 29) else (dt.month, dt.day)


def _rows():
    with open(CSV_PATH, "r") as f:
        return list(csv.DictReader(f))


def get_climate_norms_today():
    """Look up today's climate norms from CSV."""
    today = datetime.now()
    # The REAL calendar day: binary_sensor.climate_norms_stale compares this
    # attribute with now().timetuple().tm_yday.
    day_of_year = today.timetuple().tm_yday
    # Leap-year clamp (2026-07-03): the norms CSV has 365 rows; Dec 31 of a
    # leap year is day 366 and previously returned {"status": "error"} for the
    # whole day (next occurrence 2028-12-31). Dec 31 uses the day-365 norms.
    # 2026-09-23: clamp replaced by the (month, day) lookup. Matching on
    # DayOfYear returned the NEXT day's norms from Mar 1 of a leap year, and
    # the clamped value (365) tripped climate_norms_stale on a leap Dec 31.

    try:
        rows = _rows()
        key = _key(today)
        # Month normal day by day; a leap-year Feb 29 counts as a second Feb 28.
        month_vals = {
            int(r["Day"]): float(r["HDD65_mean"])
            for r in rows
            if int(r["Month"]) == today.month
        }
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        daily = [
            month_vals[min(d, max(month_vals))] for d in range(1, days_in_month + 1)
        ]
        for row in rows:
            if (int(row["Month"]), int(row["Day"])) == key:
                # Return the key values we need
                return {
                    "day_of_year": day_of_year,
                    "month": int(row["Month"]),
                    "day": int(row["Day"]),
                    "hdd_mean": round(float(row["HDD65_mean"]), 2),
                    "hdd_min": round(float(row["HDD65_min"]), 2),
                    "hdd_max": round(float(row["HDD65_max"]), 2),
                    "hdd_p10": round(float(row["HDD65_p10"]), 2),
                    "hdd_p90": round(float(row["HDD65_p90"]), 2),
                    "cdd_mean": round(float(row["CDD65_mean"]), 2),
                    "cdd_p10": round(float(row["CDD65_p10"]), 2),
                    "cdd_p90": round(float(row["CDD65_p90"]), 2),
                    "tmean": round(float(row["Tmean_mean"]), 1),
                    "tmin": round(float(row["Tmin_mean"]), 1),
                    "tmax": round(float(row["Tmax_mean"]), 1),
                    "samples": int(row["Samples"]),
                    # Replace the hard-coded monthly dicts that the weather
                    # severity sensors carried (2026-09-23, R10).
                    "month_hdd_normal": round(sum(daily), 1),
                    "mtd_hdd_normal": round(sum(daily[: today.day]), 1),
                    "annual_hdd_normal": round(
                        sum(float(r["HDD65_mean"]) for r in rows), 1
                    ),
                    "annual_cdd_normal": round(
                        sum(float(r["CDD65_mean"]) for r in rows), 1
                    ),
                    "source": SOURCE,
                    "status": "ok",
                }

        # Day not found (shouldn't happen with 365-day file)
        return {"status": "error", "message": f"Day {key} not found"}

    except FileNotFoundError:
        return {"status": "error", "message": f"CSV not found: {CSV_PATH}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_smoothed_hdd(window=3):
    """Get smoothed HDD mean using a rolling window around today."""
    today = datetime.now()

    try:
        hdd_values = []
        with open(CSV_PATH, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        # CSV DayOfYear of today's (month, day) row - not tm_yday, which runs one
        # ahead of the 365-row file from Mar 1 of a leap year (see above).
        day_of_year = next(
            int(r["DayOfYear"])
            for r in rows
            if (int(r["Month"]), int(r["Day"])) == _key(today)
        )

        # Calculate days to average (centered window)
        half_window = window // 2
        days_to_check = [
            (day_of_year - half_window + i - 1) % 365 + 1 for i in range(window)
        ]

        for row in rows:
            if int(row["DayOfYear"]) in days_to_check:
                hdd_values.append(float(row["HDD65_mean"]))

        if hdd_values:
            return round(sum(hdd_values) / len(hdd_values), 2)
        return None
    except Exception:
        return None


if __name__ == "__main__":
    result = get_climate_norms_today()

    # Add smoothed value
    smoothed = get_smoothed_hdd(3)
    if smoothed is not None:
        result["hdd_mean_smoothed"] = smoothed

    print(json.dumps(result))
