#!/usr/bin/env python3
"""Build climate_daily_norms_bdl.csv -- daily HDD65/CDD65/temperature norms for
Bradley International Airport (BDL, Windsor Locks CT) from the ACIS web service.

Written 2026-09-23 so every degree-day comparison in HA uses BDL data (Bill's
directive, same session; ACIS is "the BDL product" per open_questions.yaml
2026-09-16). It replaces climate_daily_norms.csv as the input to
scripts/climate_norms_today.py. That file is KEPT (CSV rule: never overwrite):
it was 18 samples/day from an unidentified source and does not match BDL -
best-matching 18-year ACIS BDL window 2004-2021 gives MAE 2.76 HDD/day, bias
+1.18 [M, n=365 days]; annual sum 6,128 vs the NCEI 1991-2020 BDL normal 5,873.

Columns (same schema as the old file, so readers change only the path):
  *_mean              NCEI 1991-2020 daily normals for BDL: ACIS StnData
                      "normal": "91". Verified 2026-09-23 [M]: "91" and "1"
                      both return annual HDD 5,873; "81" returns 5,988.
  *_min/_max/_p10/_p90  ACIS BDL OBSERVED values on that calendar date,
                      1991-2020 (the same 30 years as the normals).
                      p10/p90 = statistics.quantiles(n=10, method="inclusive").
  Samples             observed years with a value on that date (30 when complete)
  DayOfYear           1..365 in a NON-leap year. There is no Feb 29 row;
                      climate_norms_today.py maps Feb 29 to Feb 28.

Refuses to overwrite an existing output. Run once, anywhere with internet:
  python3 scripts/build_bdl_daily_norms.py [--out climate_daily_norms_bdl.csv]
"""

import argparse
import csv
import json
import statistics
import sys
import urllib.request
from pathlib import Path

ACIS_URL = "https://data.rcc-acis.org/StnData"
SID = "BDL"
OBS_START, OBS_END = "1991-01-01", "2020-12-31"
NORMALS_YEAR = "2021"  # any non-leap year: ACIS returns the 365 daily normals
HEADER = [
    "Month",
    "Day",
    "HDD65_mean",
    "HDD65_min",
    "HDD65_max",
    "HDD65_p10",
    "HDD65_p90",
    "CDD65_mean",
    "CDD65_min",
    "CDD65_max",
    "CDD65_p10",
    "CDD65_p90",
    "Tmean_mean",
    "Tmin_mean",
    "Tmax_mean",
    "Samples",
    "DayOfYear",
]


def acis(body: dict) -> dict:
    req = urllib.request.Request(
        ACIS_URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    if "error" in d:
        raise RuntimeError(f"ACIS error: {d['error']}")
    return d


def num(v):
    """ACIS value -> float, or None for missing ('M'), trace ('T') or blank."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default=str(Path(__file__).parent.parent / "climate_daily_norms_bdl.csv"),
    )
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists():
        print(
            f"refusing to overwrite {out} (CSV rule: never overwrite)", file=sys.stderr
        )
        return 1

    norms = acis(
        {
            "sid": SID,
            "sdate": f"{NORMALS_YEAR}-01-01",
            "edate": f"{NORMALS_YEAR}-12-31",
            "elems": [
                {"name": e, "normal": "91"}
                for e in ("hdd", "cdd", "avgt", "mint", "maxt")
            ],
        }
    )
    obs = acis(
        {
            "sid": SID,
            "sdate": OBS_START,
            "edate": OBS_END,
            "elems": [{"name": "hdd"}, {"name": "cdd"}],
        }
    )

    by_date = {}  # (month, day) -> {"hdd": [...], "cdd": [...]}
    for dt, h, c in obs["data"]:
        _, m, d = map(int, dt.split("-"))
        if (m, d) == (2, 29):
            continue
        slot = by_date.setdefault((m, d), {"hdd": [], "cdd": []})
        if num(h) is not None and num(c) is not None:
            slot["hdd"].append(num(h))
            slot["cdd"].append(num(c))

    def spread(vals):
        q = statistics.quantiles(vals, n=10, method="inclusive")
        return min(vals), max(vals), round(q[0], 2), round(q[8], 2)

    rows = []
    for doy, (dt, hdd, cdd, avgt, mint, maxt) in enumerate(norms["data"], start=1):
        _, m, d = map(int, dt.split("-"))
        vals = [num(x) for x in (hdd, cdd, avgt, mint, maxt)]
        if None in vals:
            raise RuntimeError(
                f"ACIS normal missing for {dt}: {hdd, cdd, avgt, mint, maxt}"
            )
        s = by_date.get((m, d), {"hdd": [], "cdd": []})
        if len(s["hdd"]) < 25:
            raise RuntimeError(
                f"only {len(s['hdd'])} observed years for {m}/{d}; expected ~30"
            )
        hmin, hmax, hp10, hp90 = spread(s["hdd"])
        cmin, cmax, cp10, cp90 = spread(s["cdd"])
        rows.append(
            [
                m,
                d,
                vals[0],
                hmin,
                hmax,
                hp10,
                hp90,
                vals[1],
                cmin,
                cmax,
                cp10,
                cp90,
                vals[2],
                vals[3],
                vals[4],
                len(s["hdd"]),
                doy,
            ]
        )

    if len(rows) != 365:
        raise RuntimeError(f"expected 365 rows, got {len(rows)}")
    with open(out, "x", newline="") as f:  # "x": fails rather than overwrite
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HEADER)
        w.writerows(rows)
    print(
        json.dumps(
            {
                "out": str(out),
                "rows": len(rows),
                "annual_hdd_normal": sum(r[2] for r in rows),
                "annual_cdd_normal": sum(r[7] for r in rows),
                "samples_min": min(r[15] for r in rows),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
