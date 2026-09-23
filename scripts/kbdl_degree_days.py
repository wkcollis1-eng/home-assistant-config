#!/usr/bin/env python3
"""Trailing-24-hour HDD65 / CDD65 for Bradley (KBDL), from the station's own
METAR observations on api.weather.gov, computed the way NWS/ACIS compute a
day's degree days: 65 - (Tmax + Tmin) / 2 of the observed temperatures.

Why this exists (2026-09-23, Bill: "switch to the NWS KBDL hourly observations")
--------------------------------------------------------------------------------
sensor.hvac_hdd65_today was 65 - the 24 h MEAN of a proxy temperature chain
(Open-Meteo grid point -> Pirate Weather -> NWS KHFD -> Open-Meteo home). None
of those is a BDL observation, and a mean is not how BDL's HDD is defined.
Scored against ACIS BDL daily HDD, KBDL METARs over 2024-09-01..2026-09-22
[M, n=752 days, 486 heating; IEM archive of the same METAR stream]:
    65 - (max+min)/2, trailing 24 h:  bias +0.06  sd 0.57  MAE 0.34 HDD/day
    65 - mean of the same obs:        bias +0.03  sd 1.42  MAE 0.90 HDD/day

Which observations
------------------
api.weather.gov also serves KBDL's 5-minute observations. Their temperature is
whole degrees C (a 1.8 F step) and the IEM archive holds none of them for BDL,
so they are untested here (R15) and are DROPPED: only observations whose minute
is not a multiple of 5 are used - the :51 routine METARs and the specials, which
carry the 0.1 C T-group. That exact filter is what was scored above.

Output
------
Always prints ONE JSON object and exits 0, so HA's command_line sensor keeps
its attributes (a non-zero exit resets them to {} - HA 2026.9.3
command_line/sensor.py). status:
    ok            hdd65/cdd65 are good; the template uses them
    insufficient  too few obs or a long gap; the template falls back to the proxy
    error         the fetch failed; the template falls back to the proxy
MIN_OBS and MAX_GAP_H sit beyond anything seen in 752 days (min 20 obs, max gap
4 h [M]), so they trip only on a real outage. Their exact values are judgement.
"""

import argparse
import gzip
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.weather.gov/stations/{sid}/observations?start={start}&limit=500"
USER_AGENT = "home-assistant-config/kbdl_degree_days.py"
MIN_OBS = 12  # of ~24-30 per 24 h window
MAX_GAP_H = 6.0  # largest hole in the window, edges included
REJECT_QC = ("X", "Q")  # MADIS QC: X = rejected, Q = questioned


def fetch(sid: str, start: datetime) -> list:
    url = API.format(sid=sid, start=start.strftime("%Y-%m-%dT%H:%M:%SZ"))
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json",
            "Accept-Encoding": "gzip",  # ~1-2 MB of JSON per call uncompressed
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return json.loads(body)["features"]


def parse(features: list) -> list:
    """-> sorted [(utc datetime, degF)] of METAR (hourly + special) obs."""
    out = []
    for f in features:
        p = f.get("properties", {})
        t = p.get("temperature") or {}
        v = t.get("value")
        if v is None or t.get("qualityControl") in REJECT_QC:
            continue
        ts = datetime.fromisoformat(p["timestamp"]).astimezone(timezone.utc)
        if ts.minute % 5 == 0:
            continue  # 5-minute obs: whole-degree C, untested (see header)
        out.append((ts, v * 9 / 5 + 32))
    return sorted(out)


def compute(obs: list, start: datetime, end: datetime) -> dict:
    """Degree days from obs in (start, end]. Pure: the replay test calls it."""
    w = [(t, f) for t, f in obs if start < t <= end]
    pts = [start] + [t for t, _ in w] + [end]
    gap = max((b - a).total_seconds() / 3600 for a, b in zip(pts, pts[1:]))
    out = {
        "status": "ok" if len(w) >= MIN_OBS and gap <= MAX_GAP_H else "insufficient",
        "n_obs": len(w),
        "max_gap_h": round(gap, 2),
        "window_start": start.isoformat(timespec="minutes"),
        "window_end": end.isoformat(timespec="minutes"),
        "hdd65": None,
        "cdd65": None,
        "tmax": None,
        "tmin": None,
        "last_obs": None,
    }
    if w:
        hi = max(f for _, f in w)
        lo = min(f for _, f in w)
        mid = (hi + lo) / 2
        out.update(
            {
                "hdd65": round(max(65 - mid, 0), 1),
                "cdd65": round(max(mid - 65, 0), 1),
                "tmax": round(hi, 1),
                "tmin": round(lo, 1),
                "last_obs": w[-1][0].isoformat(timespec="minutes"),
            }
        )
    if out["status"] != "ok":
        out["detail"] = (
            f"{len(w)} obs (min {MIN_OBS}), max gap {gap:.1f} h (max {MAX_GAP_H})"
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sid", default="KBDL")
    args = ap.parse_args()
    end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = end - timedelta(hours=24)
    base = {
        "station": args.sid,
        "method": "65 - (max+min)/2 of METAR obs (hourly + special), trailing 24 h",
    }
    try:
        obs = parse(fetch(args.sid, start))
    except Exception as e:  # network / HTTP / JSON -> announce it, never crash
        print(
            json.dumps(
                {
                    **base,
                    "status": "error",
                    "hdd65": None,
                    "cdd65": None,
                    "detail": f"{type(e).__name__}: {e}",
                }
            )
        )
        return 0
    print(json.dumps({**base, **compute(obs, start, end)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
