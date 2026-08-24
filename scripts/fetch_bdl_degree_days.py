#!/usr/bin/env python3
"""Fetch official Bradley/BDL (Windsor Locks, CT) monthly HDD65 / CDD65 from the
ACIS web service -- the same data behind NWS xmACIS2 / NOWData -- and upsert them
into a CSV.

Design notes
------------
* Captures only COMPLETED calendar months. The in-progress month is excluded
  until it finishes (ACIS would otherwise return a month-to-date partial).
* Idempotent and self-backfilling: every run requests the whole range and writes
  any month that is missing or whose value changed (e.g. ACIS preliminary -> final,
  or a previously-unavailable month like April that has since been published).
* Skips months ACIS reports as missing ('M') or trace ('T').
* Prints a JSON summary to stdout so a Home Assistant `command_line` sensor can
  use it directly; the CSV write is the capture side-effect.

Usage:
  fetch_bdl_degree_days.py [--csv PATH] [--start YYYY-MM] [--sid BDL]
"""
import argparse
import csv
import json
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ACIS_URL = "https://data.rcc-acis.org/StnData"
HEADER = ["month", "hdd65", "cdd65", "source", "captured_utc"]
SOURCE = "ACIS/xmACIS2 (NWS Bradley KBDL, base 65F)"


def last_completed_month(today: date):
    """Return (year, month) of the most recent fully-completed calendar month."""
    return (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)


def fetch(sid: str, start: str, end: str) -> dict:
    body = {
        "sid": sid,
        "sdate": start,
        "edate": end,
        "elems": [
            {"name": "hdd", "interval": "mly", "duration": "mly", "reduce": "sum"},
            {"name": "cdd", "interval": "mly", "duration": "mly", "reduce": "sum"},
        ],
    }
    req = urllib.request.Request(
        ACIS_URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="/config/reports/bdl_degree_days.csv")
    ap.add_argument("--start", default="2024-07")
    ap.add_argument("--sid", default="BDL")
    args = ap.parse_args()

    cy, cm = last_completed_month(date.today())
    end = f"{cy:04d}-{cm:02d}"  # never request past the last completed month

    try:
        d = fetch(args.sid, args.start, end)
        if "error" in d:
            print(json.dumps({"status": "error", "detail": d["error"]}))
            return 1
    except Exception as e:  # network / parse failure -> report, don't crash HA
        print(json.dumps({"status": "error", "detail": f"{type(e).__name__}: {e}"}))
        return 1

    # Parse ACIS rows -> {month: (hdd, cdd)} for completed months with real data.
    fresh = {}
    for row in d.get("data", []):
        mon, hdd, cdd = row[0], row[1], row[2]
        if hdd in ("M", "T", None) or cdd in ("M", "T", None):
            continue
        try:
            fresh[mon] = (int(round(float(hdd))), int(round(float(cdd))))
        except (TypeError, ValueError):
            continue

    # Load existing CSV (if any).
    p = Path(args.csv)
    existing = {}
    if p.exists():
        with open(p, newline="") as f:
            for r in csv.DictReader(f):
                existing[r["month"]] = r

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    added, updated = [], []
    for mon, (hdd, cdd) in fresh.items():
        if mon not in existing:
            added.append(mon)
        elif (str(existing[mon].get("hdd65")) != str(hdd)
              or str(existing[mon].get("cdd65")) != str(cdd)):
            updated.append(mon)
        else:
            continue  # unchanged -> keep original captured_utc
        existing[mon] = {
            "month": mon, "hdd65": hdd, "cdd65": cdd,
            "source": SOURCE, "captured_utc": stamp,
        }

    # Write back, month-sorted.
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for mon in sorted(existing):
            w.writerow(existing[mon])

    # Trailing 12 completed months -> {abbr: hdd}, the rolling-efficiency denominator.
    ABBR = ["jan", "feb", "mar", "apr", "may", "jun",
            "jul", "aug", "sep", "oct", "nov", "dec"]
    completed = sorted(m for m in existing if m <= end)
    t12 = {}
    for m in completed[-12:]:
        try:
            t12[ABBR[int(m.split("-")[1]) - 1]] = int(round(float(existing[m]["hdd65"])))
        except (ValueError, KeyError, IndexError):
            pass
    t12_sum = sum(t12.values()) if len(t12) == 12 else None

    latest = max(fresh) if fresh else (completed[-1] if completed else None)
    def _row(mon, idx):
        if mon in fresh:
            return fresh[mon][idx]
        if mon in existing:
            return int(round(float(existing[mon]["hdd65" if idx == 0 else "cdd65"])))
        return None
    print(json.dumps({
        "status": "ok",
        "latest_month": latest,
        "latest_hdd": _row(latest, 0) if latest else None,
        "latest_cdd": _row(latest, 1) if latest else None,
        "trailing_12": t12,
        "trailing_12_sum": t12_sum,
        "trailing_12_count": len(t12),
        "added": sorted(added),
        "updated": sorted(updated),
        "rows": len(existing),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
