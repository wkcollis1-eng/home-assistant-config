#!/usr/bin/env python3
"""furnace_gas_cycles.py - gas burned per furnace cycle, from the SDR gas meter.

Phase I of the per-cycle gas SPC (2026-09-23). READ-ONLY: queries InfluxDB and
prints one row per furnace-CT run, then - once clean heating cycles exist - a
fit of gas against run length. Stores nothing in HA: a derived view, not a
second copy of anything in helpers (R10).

WHAT EACH INPUT IS FOR
  sensor.sem_furnace_power             cycle TIMING. Bill 2026-09-23: "Home Kit is
                                       glitchy. Furnace CT may be a more reliable
                                       cycle counter when watts are over 100W".
  binary_sensor.ac_compressor_running  labels a CT run 'cool'
  binary_sensor.hvac_furnace_running   HomeKit heat call. Labels 'heat' and is
                                       SCORED against the CT, never used for timing
  sensor.gas_meter_volume              gas VOLUME. Every change is +2 ft3
                                       [M, 243/243, 09-09..09-23 00:00]
  sensor.gas_meter_age                 reconstructs decode times, because
                                       gas_meter_last_seen is excluded from the
                                       recorder on purpose (configuration.yaml)
  sensor.hwh_current_consumption       Kasa plug on the WHOLE Navien (Bill, 2026-09-16)

WHY "CT ABOVE 100 W" DOES NOT BY ITSELF MEAN HEAT
  Over 2026-08-24..09-23 the CT's 1-min max sat above 100 W for 10,217 minutes
  with the compressor off, at 128-134 W (p10-p90), and for 2,246 minutes with it
  on [M, sem_furnace_power vs sem_ac_power > 300 W]. That is blower-only running
  and cooling. No heat call exists in the record - 0 on-transitions of either
  call_for_heat in 150 days, and the CT history starts 2026-06-27 [M] - so the
  heating CT signature is unmeasured until the first cold night. A run is:
    cool   compressor on at any point in the run
    heat   not cool, and a HomeKit heat call overlaps it; OR, inside the quiet
           window, gas moved with the Navien idle (a call HomeKit missed)
    other  no call and no gas - blower circulation most likely [I; falsified
           if 'other' runs inside the window show gas with the Navien idle]
    unk    no call, and gas unmeasurable or explained by another load
  Over 2026-09-09..09-23 those 'other' runs were ~7.5 min of 126-133 W starting
  near :24-:26 and :54-:56 past the hour [M, this script's first run, 449
  runs]. Bill, 2026-09-23 ~19:45: "ecobee fan recirc has been turned off." So
  after that moment 'other' runs should all but vanish; if they persist, the
  fan-circulation reading of them was wrong. Were circulation ever back on, a
  heat call starting inside a 130 W fan run would merge into one CT run and
  inflate its minutes - a low-gas outlier in the fit. w_med / w_max are
  printed so the first cold night can set --on-w above the fan band if so.

A HEAT CYCLE IS CLEAN (enters the fit) WHEN
  it lies inside 23:00-05:00 local: 0 gas steps in that window on 14 nights
    [M, 2026-09-09..09-23]; Bill moved it from 21:00 on 2026-09-23 (bedtime
    hot water)
  a decode exists in the off-period before AND after, so ticks cannot be
    assigned to the wrong cycle
  the counter is flat across both off-periods (no other load running)
  the Navien plug stays < 12 W from the before-decode to the after-decode
    (idle band, open_questions.yaml, 2026-09-16 Kasa-plug entry)
  no CT sample gap > 60 s inside the run

ERROR BOUNDS
  Each cycle's gas is +-2 ft3 (the step), sd 0.82 ft3 [D: triangular,
  var = 2 * 2^2 / 12]. Residuals are therefore judged in ft3, not as a rate.

Usage:
  HA_CONFIG='H:/' python scripts/furnace_gas_cycles.py           # last 14 days
  python scripts/furnace_gas_cycles.py --start 2026-11-01 --end 2026-11-15
  python scripts/furnace_gas_cycles.py --all                     # list cool/other too
  python scripts/furnace_gas_cycles.py --selftest                # R7 gate, no network
"""

import argparse
import base64
import bisect
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime

GAS_STEP = 2.0  # ft3 per counter change [M, 243/243, 09-09..09-23 00:00]
STEP_SD = math.sqrt(2 * GAS_STEP**2 / 12)  # 0.82 ft3 per cycle [D: triangular]
# 1.61 ft3/min [D: 100,000 BTU/hr (BASELINE_REPORT.md §Primary Heating [S]) /
# 1,037 BTU/ft3 (CLAUDE.md BASELINES, 103,700 BTU/CCF [S]) / 60]. Used ONLY to
# flag impossible and missing gas; the fit measures the real rate.
NAMEPLATE = 100000 / 1037 / 60
QUIET = (23, 5)  # local hours [start, end)
DECODE_TOL = 5  # s; decode times from gas_meter_age are +-3 s (0.1 min rounding)
# Student t, two-sided 95 %, df 1..30 [S: any standard t table]
T95 = [
    12.706,
    4.303,
    3.182,
    2.776,
    2.571,
    2.447,
    2.365,
    2.306,
    2.262,
    2.228,
    2.201,
    2.179,
    2.160,
    2.145,
    2.131,
    2.120,
    2.110,
    2.101,
    2.093,
    2.086,
    2.080,
    2.074,
    2.069,
    2.064,
    2.060,
    2.056,
    2.052,
    2.048,
    2.045,
    2.042,
]


def t95(df):
    if df <= 30:
        return T95[df - 1]
    return 2.021 if df < 60 else 2.000 if df < 120 else 1.980


# --- InfluxDB (read-only) --------------------------------------------------


def _creds():
    import yaml  # only the network path needs it; --selftest runs without

    cfg = os.environ.get("HA_CONFIG", "/config")
    with open(f"{cfg}/secrets.yaml", encoding="utf-8") as fh:
        s = yaml.safe_load(fh) or {}
    return (
        os.environ.get("INFLUXDB_URL") or s.get("influxdb_url", ""),
        os.environ.get("INFLUXDB_DB") or s.get("influxdb_db", "Home Assistant"),
        os.environ.get("INFLUXDB_USER") or s.get("influxdb_user", ""),
        os.environ.get("INFLUXDB_PASS") or s.get("influxdb_pass", ""),
    )


def _query(creds, q):
    url, db, user, pw = creds
    # Basic auth, never u/p in a logged URL (docs/influx-grafana.md, Credentials)
    req = urllib.request.Request(
        f"{url}/query?" + urllib.parse.urlencode({"db": db, "q": q, "epoch": "s"}),
        headers={
            "Authorization": "Basic "
            + base64.b64encode(f"{user}:{pw}".encode()).decode()
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.load(r)["results"][0]
    if "error" in res:
        raise RuntimeError(res["error"])
    return res.get("series", [{}])[0].get("values", [])


def fetch(creds, meas, eid, t0, t1, domain=None):
    """A write-on-change series as (times, values), with the value carried in at t0.
    InfluxDB writes on state CHANGE only, so a flat line is not a gap."""
    cond = f"\"entity_id\" = '{eid}'" + (
        f" AND \"domain\" = '{domain}'" if domain else ""
    )
    prev = _query(
        creds, f'SELECT last("value") FROM "{meas}" WHERE {cond} AND time < {int(t0)}s'
    )
    rows = _query(
        creds,
        f'SELECT "value" FROM "{meas}" WHERE {cond} '
        f"AND time >= {int(t0)}s AND time <= {int(t1)}s",
    )
    pts = [(t0, prev[0][1])] if prev and isinstance(prev[0][1], (int, float)) else []
    pts += [(t, v) for t, v in rows if isinstance(v, (int, float))]
    return [p[0] for p in pts], [p[1] for p in pts]


# --- pure core: everything below is exercised by --selftest -------------------


def step_at(series, t):
    """Value of a write-on-change series at time t, or None before its first point."""
    i = bisect.bisect_right(series[0], t) - 1
    return series[1][i] if i >= 0 else None


def max_over(series, a, b):
    """Max over [a, b], counting the value carried in at a."""
    ts, vs = series
    seg = vs[max(bisect.bisect_right(ts, a) - 1, 0) : bisect.bisect_right(ts, b)]
    return max(seg) if seg else None


def ct_runs(ct, on_w, merge_s, min_s):
    """CT runs above on_w: start = first sample above, end = first sample back at
    or below. A run still open when the data ends is dropped - its gas cannot be
    read yet. Runs split by a dip shorter than merge_s are joined (the burner
    sequence may dip between igniter-off and blower-on [I; falsified if the
    first cold night shows heat runs with internal dips > merge_s])."""
    runs, cur = [], None
    for t, w in zip(*ct):
        if w > on_w:
            if cur is None:
                cur = [t, None]
        elif cur is not None:
            cur[1] = t
            runs.append(cur)
            cur = None
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < merge_s:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    keep = [(a, b) for a, b in merged if b - a >= min_s]
    return keep, len(merged) - len(keep)


def decode_times(age):
    """Decode instants implied by gas_meter_age: each recorded value a at t says the
    last decode was at t - 60a. The template re-renders at every decode (0.0) and
    every minute, so decodes more than a minute apart are recovered to +-3 s;
    two decodes inside one minute collapse to the first, which only ever makes
    a cycle look LESS clean, never more."""
    ds = sorted(t - 60.0 * a for t, a in zip(*age) if a < 99999)
    out = []
    for d in ds:
        if not out or d - out[-1] > 6:
            out.append(d)
    return out


def in_quiet(t, tz):
    h = datetime.fromtimestamp(t, tz).hour
    return h >= QUIET[0] or h < QUIET[1]


def between(xs, a, b):
    return xs[bisect.bisect_left(xs, a) : bisect.bisect_right(xs, b)]


def analyse(S, tz, o):
    runs, short = ct_runs(S["ct"], o.on_w, o.merge_s, o.min_s)
    dec = decode_times(S["age"])
    rows = []
    for k, (s, e) in enumerate(runs):
        prev_e = runs[k - 1][1] if k else S["t0"]
        next_s = runs[k + 1][0] if k + 1 < len(runs) else S["t1"]
        T = (e - s) / 60.0
        why = []
        quiet = in_quiet(s, tz) and in_quiet(e, tz)
        if not quiet:
            why.append("window")

        # gas: last decode before the run, first decode after it has settled
        bef = between(dec, max(prev_e + o.settle_s, s - o.flat_s), s)
        aft = between(dec, e + o.settle_s, min(next_s, e + o.settle_s + o.flat_s))
        dv = None
        if not bef:
            why.append("no-decode-before")
        if not aft:
            why.append("no-decode-after")
        if bef and aft:
            v0 = step_at(S["vol"], bef[-1] + DECODE_TOL)
            v1 = step_at(S["vol"], aft[0] + DECODE_TOL)
            if v0 is None or v1 is None:
                why.append("no-gas-data")
            else:
                dv = round(v1 - v0, 1)
                if step_at(S["vol"], bef[0] + DECODE_TOL) != v0:
                    why.append("gas-before")
                if step_at(S["vol"], aft[-1] + DECODE_TOL) != v1:
                    why.append("gas-after")
        nav = max_over(S["navien"], bef[-1] if bef else s, aft[0] if aft else e)
        if nav is None:
            why.append("no-navien-data")
        elif nav >= o.navien_idle_w:
            why.append("navien")

        ts, ws = S["ct"]
        i, j = bisect.bisect_left(ts, s), bisect.bisect_right(ts, e)
        if any(y - x > o.max_gap_s for x, y in zip(ts[i:j], ts[i + 1 : j])):
            why.append("ct-gap")
        seg = sorted(ws[i : j - 1]) or [0.0]

        call = (max_over(S["call"], s - o.lead_s, e) or 0) >= 1
        cool = (max_over(S["ac"], s, e) or 0) >= 1
        other_load = {"navien", "gas-before", "gas-after"} & set(why)
        if cool:
            lab = "cool"
        elif call:
            lab = "heat"
        elif dv is not None and dv > 0 and quiet and not other_load:
            lab = "heat"  # gas with nothing else running: a call HomeKit missed
        elif dv == 0:
            lab = "other"
        else:
            lab = "unk"
        if dv is not None and (dv < 0 or dv > 2 * NAMEPLATE * T + 2 * GAS_STEP):
            why.append("implausible")  # counter reset, or a gas_meter_scale change
        if lab == "heat" and dv == 0 and NAMEPLATE * T >= 2 * GAS_STEP:
            why.append("NO-GAS")  # called and ran long enough for 2 steps, burned none
        rows.append(
            {
                "s": s,
                "e": e,
                "T": T,
                "lab": lab,
                "call": call,
                "dv": dv,
                "why": why,
                "w_med": seg[len(seg) // 2],
                "w_max": seg[-1],
                "clean": lab == "heat" and not why,
            }
        )
    return rows, short, call_segments(S["call"])


def call_segments(call):
    segs, on = [], None
    for t, v in zip(*call):
        if v >= 1 and on is None:
            on = t
        elif v < 1 and on is not None:
            segs.append((on, t))
            on = None
    return segs


def fit(xs, ys):
    """OLS of gas (ft3) on run minutes: slope = firing rate, intercept = -rate *
    the minutes of each run that burn nothing (purge, ignition, blower tail)."""
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    a = my - b * mx
    sd = math.sqrt(sum((y - a - b * x) ** 2 for x, y in zip(xs, ys)) / (n - 2))
    return {
        "n": n,
        "b": b,
        "a": a,
        "sd": sd,
        "t": t95(n - 2),
        "se_b": sd / math.sqrt(sxx),
        "se_a": sd * math.sqrt(1 / n + mx * mx / sxx),
    }


# --- report ------------------------------------------------------------------


def report(rows, short, segs, tz, o, t0, t1):
    def f(t):
        return datetime.fromtimestamp(t, tz).strftime("%m-%d %H:%M:%S")

    print(f"furnace_gas_cycles: {f(t0)} .. {f(t1)} ({tz}), CT on > {o.on_w:g} W")
    # unk outside the window is routine (Navien, cooking), so only listed with --all
    shown = [
        r
        for r in rows
        if o.all
        or r["lab"] == "heat"
        or (r["lab"] == "unk" and "window" not in r["why"])
    ]
    if shown:
        print(
            f"{'start':15} {'min':>6} {'label':5} {'call':4} {'ft3':>6} {'w_med':>6} "
            f"{'w_max':>6} {'clean':5} reasons"
        )
    for r in shown:
        print(
            f"{f(r['s']):15} {r['T']:6.2f} {r['lab']:5} {'y' if r['call'] else '-':4} "
            f"{'-' if r['dv'] is None else r['dv']:>6} {r['w_med']:6.0f} {r['w_max']:6.0f} "
            f"{'YES' if r['clean'] else '-':5} {','.join(r['why'])}"
        )

    def count(lab):
        return sum(r["lab"] == lab for r in rows)

    print(
        f"runs {len(rows)}: heat {count('heat')}, cool {count('cool')}, other "
        f"{count('other')}, unk {count('unk')}; {short} blip(s) < {o.min_s:g} s dropped"
    )

    heat = [r for r in rows if r["lab"] == "heat"]
    missed = [r for r in heat if not r["call"]]
    phantom = [
        g
        for g in segs
        if not any(r["s"] <= g[1] and g[0] - o.lead_s <= r["e"] for r in rows)
    ]
    print(
        f"HomeKit vs CT [M, this range]: {len(heat) - len(missed)} heat runs with a call, "
        f"{len(missed)} gas-only (call missed), {len(phantom)} call(s) with no CT run"
    )
    lat = sorted(
        r["s"] - max(g[0] for g in segs if g[0] <= r["e"])
        for r in heat
        if r["call"] and any(g[0] <= r["e"] for g in segs)
    )
    if lat:
        print(
            f"  CT start minus call start: median {lat[len(lat) // 2]:.0f} s, "
            f"range {lat[0]:.0f}..{lat[-1]:.0f} s (n={len(lat)})"
        )
    nogas = [r for r in heat if "NO-GAS" in r["why"]]
    if nogas:
        print(
            f"NO-GAS: {len(nogas)} heat run(s) long enough for >= 2 steps burned none: "
            + ", ".join(f(r["s"]) for r in nogas)
        )

    clean = [r for r in rows if r["clean"]]
    if len(clean) < o.min_fit:
        print(
            f"fit: {len(clean)} clean heat cycle(s), need {o.min_fit} - nothing fitted"
        )
        return 0
    res = fit([r["T"] for r in clean], [r["dv"] for r in clean])
    if res is None:
        print("fit: every clean cycle has the same length - slope undefined")
        return 0
    b, a, h = res["b"], res["a"], res["t"]
    print(
        f"fit [M, n={res['n']} clean cycles, sem_furnace_power + gas_meter_volume, this range]:"
    )
    print(
        f"  rate      {b:.3f} +- {h * res['se_b']:.3f} ft3/min (95 %)   "
        f"nameplate {NAMEPLATE:.2f} [D]"
    )
    print(
        f"  intercept {a:.2f} +- {h * res['se_a']:.2f} ft3 (95 %); non-burning "
        f"{(-a / b if b else float('nan')):.2f} min per run [D: -intercept / rate]"
    )
    print(
        f"  residual sd {res['sd']:.2f} ft3 (df {res['n'] - 2}); quantisation "
        f"floor {STEP_SD:.2f} ft3 [D]"
    )
    return 0


# --- R7 self-test: inject each fault, prove it fires; prove a clean cycle passes ---


def selftest():
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/New_York")
    base = datetime(2026, 11, 10, 22, 0, tzinfo=tz).timestamp()  # 22:00 local

    def at(hh, mm):
        return base + ((hh - 22) % 24 * 60 + mm) * 60

    t0, t1 = base, at(6, 0)
    ct, ac, call, nav, vol_steps, no_decode = [], [], [], [], [], []

    def run(s_min, e_min_, w, gas=0.0, hk=True, cool=False, navien=False, blind=False):
        ct.append((s_min, e_min_, w))
        if hk:
            call.append((s_min - 10, e_min_ - 60))
        if cool:
            ac.append((s_min, e_min_))
        if navien:
            nav.append((s_min + 60, s_min + 180))
        if gas:
            vol_steps.append((s_min + 90, gas))
        if blind:
            no_decode.append((e_min_, e_min_ + 900))

    run(at(2, 0), at(2, 10), 520, gas=14)  # A clean heat
    run(at(2, 30), at(2, 40), 520, gas=0)  # B called, burned nothing
    run(at(3, 0), at(3, 10), 520, gas=16, navien=True)  # C Navien firing inside
    run(at(22, 20), at(22, 30), 520, gas=14)  # D before 23:00
    run(at(3, 30), at(3, 40), 520, gas=14, blind=True)  # E no decode after
    run(at(0, 30), at(0, 50), 600, hk=False, cool=True)  # F cooling
    run(at(1, 0), at(1, 20), 130, hk=False)  # G fan circulation
    run(at(4, 0), at(4, 8), 520, gas=12, hk=False)  # H HomeKit missed it
    call.append((at(4, 30), at(4, 40)))  # I phantom call, no CT
    fits = [(23, 10, 6), (23, 20, 8), (23, 40, 12), (0, 10, 16), (1, 40, 4)]
    for hh, mm, dur in fits:  # J fit set, 1.6 ft3/min, 1 min dead
        run(at(hh, mm), at(hh, mm) + dur * 60, 520, gas=round(1.6 * (dur - 1) / 2) * 2)

    def series(events, level_on, level_off, step=2.0):
        pts, t = [], t0
        while t <= t1:
            on = any(a <= t < b for a, b, *_ in events)
            pts.append((t, level_on(t) if on else level_off))
            t += step
        return [p[0] for p in pts], [p[1] for p in pts]

    def ctw(t):
        return next(w for a, b, w in ct if a <= t < b)

    ct_s = series(ct, ctw, 1.5)

    def bin_s(ev):
        return series(ev, lambda t: 1, 0, 30.0)

    dec = [
        t
        for t in range(int(t0), int(t1), 15)
        if not any(a <= t < b for a, b in no_decode)
    ]
    vol, v = ([t0], [1000.0]), 1000.0
    for d in dec:  # the meter reports each cycle's gas at the first decode after it
        add = sum(g for when, g in vol_steps if d - 15 < when <= d)
        if add:
            v += add
            vol[0].append(d)
            vol[1].append(v)
    age_t, age_v, last = [], [], None
    for m in range(
        int(t0), int(t1), 60
    ):  # one value per minute tick; 15 s decodes collapse, as recorded
        for d in dec:
            if m - 60 < d <= m:
                last = d
        if last is not None:
            age_t.append(m)
            age_v.append(round((m - last) / 60, 1))
    S = {
        "ct": ct_s,
        "ac": bin_s(ac),
        "call": bin_s([(a, b) for a, b in call]),
        "navien": series(nav, lambda t: 150, 3.0, 10.0),
        "vol": vol,
        "age": (age_t, age_v),
        "t0": t0,
        "t1": t1,
    }
    o = parse([])
    rows, _short, segs = analyse(S, tz, o)
    by = {round(r["s"]): r for r in rows}

    def g(hh, mm):
        return by.get(round(at(hh, mm)))

    checks = [
        (
            "A clean heat enters the fit",
            g(2, 0) and g(2, 0)["clean"] and g(2, 0)["dv"] == 14,
        ),
        ("B zero gas flagged NO-GAS", g(2, 30) and "NO-GAS" in g(2, 30)["why"]),
        (
            "C Navien overlap excluded",
            g(3, 0) and "navien" in g(3, 0)["why"] and not g(3, 0)["clean"],
        ),
        ("D outside 23-05 excluded", g(22, 20) and "window" in g(22, 20)["why"]),
        (
            "E no decode after excluded",
            g(3, 30) and "no-decode-after" in g(3, 30)["why"],
        ),
        ("F cooling labelled cool", g(0, 30) and g(0, 30)["lab"] == "cool"),
        ("G fan run labelled other", g(1, 0) and g(1, 0)["lab"] == "other"),
        (
            "H missed call still heat",
            g(4, 0) and g(4, 0)["lab"] == "heat" and not g(4, 0)["call"],
        ),
        (
            "I phantom call has no run",
            sum(
                1
                for s in segs
                if not any(r["s"] <= s[1] and s[0] - o.lead_s <= r["e"] for r in rows)
            )
            == 1,
        ),
    ]
    clean = [r for r in rows if r["clean"]]
    res = fit([r["T"] for r in clean], [r["dv"] for r in clean])
    checks.append(
        (
            "J fit recovers 1.6 ft3/min within its CI",
            res and abs(res["b"] - 1.6) <= res["t"] * res["se_b"] + 1e-9,
        )
    )
    checks.append(("K exactly A, H and the 5 fit cycles are clean", len(clean) == 7))
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("  ok   " if ok else "  FAIL ") + name)
    print(
        "SELFTEST "
        + ("PASSED" if not bad else "FAILED")
        + f" {len(checks) - len(bad)}/{len(checks)}"
    )
    return 1 if bad else 0


def parse(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument(
        "--days", type=float, default=14, help="look back this many days (default 14)"
    )
    p.add_argument("--start", help="YYYY-MM-DD local; overrides --days")
    p.add_argument("--end", help="YYYY-MM-DD local, exclusive (default now)")
    p.add_argument(
        "--on-w",
        type=float,
        default=100.0,
        help="CT watts that start a run (Bill 2026-09-23: '~100 W'; fan-only was "
        "128-134 W [M] until recirc was turned off 2026-09-23)",
    )
    p.add_argument(
        "--merge-s",
        type=float,
        default=90,
        help="join runs split by a dip shorter than this",
    )
    p.add_argument(
        "--min-s", type=float, default=20, help="drop runs shorter than this (counted)"
    )
    p.add_argument(
        "--settle-s",
        type=float,
        default=30,
        help="wait after a run before reading the counter [I: meter-report lag]",
    )
    p.add_argument(
        "--flat-s",
        type=float,
        default=600,
        help="off-period span checked for other gas",
    )
    p.add_argument(
        "--lead-s",
        type=float,
        default=120,
        help="a call up to this long before a run counts",
    )
    p.add_argument(
        "--max-gap-s",
        type=float,
        default=60,
        help="CT sample gap inside a run that disqualifies it",
    )
    p.add_argument(
        "--navien-idle-w", type=float, default=12, help="Navien plug idle ceiling (W)"
    )
    p.add_argument(
        "--min-fit", type=int, default=5, help="clean cycles needed before fitting"
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="list every run, not just heat and in-window unk",
    )
    p.add_argument(
        "--selftest", action="store_true", help="synthetic fault injection, no network"
    )
    return p.parse_args(argv)


def main():
    o = parse(sys.argv[1:])
    if o.selftest:
        return selftest()
    from zoneinfo import ZoneInfo

    cfg = os.environ.get("HA_CONFIG", "/config")
    # read-only: HA's configured zone, so the 23:00-05:00 window is house time (R10)
    with open(f"{cfg}/.storage/core.config", encoding="utf-8") as fh:
        tz = ZoneInfo(json.load(fh)["data"]["time_zone"])
    now = datetime.now(tz)
    t1 = (
        datetime.strptime(o.end, "%Y-%m-%d").replace(tzinfo=tz) if o.end else now
    ).timestamp()
    t0 = (
        datetime.strptime(o.start, "%Y-%m-%d").replace(tzinfo=tz).timestamp()
        if o.start
        else t1 - o.days * 86400
    )
    c = _creds()
    S = {
        "ct": fetch(c, "W", "sem_furnace_power", t0, t1, "sensor"),
        "ac": fetch(
            c, "binary_sensor.ac_compressor_running", "ac_compressor_running", t0, t1
        ),
        "call": fetch(
            c, "binary_sensor.hvac_furnace_running", "hvac_furnace_running", t0, t1
        ),
        "vol": fetch(c, "ft\u00b3", "gas_meter_volume", t0, t1, "sensor"),
        "age": fetch(c, "min", "gas_meter_age", t0, t1, "sensor"),
        "navien": fetch(c, "W", "hwh_current_consumption", t0, t1, "sensor"),
        "t0": t0,
        "t1": t1,
    }
    empty = [k for k in ("ct", "ac", "call", "vol", "age", "navien") if not S[k][0]]
    for k in empty:  # R8: a skipped input is a WARN, never silence
        print(
            f"WARN: no data for input '{k}' in range - every run that needs it is unk or excluded"
        )
    if "ct" in empty:
        print(
            "WARN: no CT data, nothing analysed - check sensor.sem_furnace_power in InfluxDB"
        )
        return 2
    rows, short, segs = analyse(S, tz, o)
    return report(rows, short, segs, tz, o, t0, t1)


if __name__ == "__main__":
    sys.exit(main())
