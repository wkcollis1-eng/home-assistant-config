#!/usr/bin/env python3
"""navien_xcheck.py - the Navien panel's monthly figures against the Kasa plug and the SDR gas meter.

READ-ONLY: queries InfluxDB and one HA state, prints a report, stores nothing (a
derived view, R10). Built 2026-10-22 from the September cross-check (CHANGELOG
2026.10.02 and 2026.10.22), which it must reproduce: 1054 ft3 whole house, 19.41 h
plug above the recirc threshold, 12.48 h plug at 20-70 W [M].

WHAT IS COMPARED
  panel   input_number.dhw_archive_<mon> (CCF: the save_dhw_button automation in
          packages/gas_dhw.yaml stores therm x its factor, read back from that
          file), dhw_op_hrs_archive_<mon>, dhw_recirc_hrs_archive_<mon>.
          The archive is a 12-slot ring: a slot holds LAST year's figure until
          this year's is saved on the 1st. The save time is read back from
          InfluxDB, and a slot not saved after its month ended is refused (WARN),
          never compared. 2026-10-22: dhw_archive_oct held 16.78, last year's.
  gas     sensor.gas_meter_volume (SDR, +2 ft3 steps). Each interval between
          decodes is labelled by the gas loads running in it:
            navien   Kasa plug sensor.hwh_current_consumption above --fire-w
            furnace  sensor.sem_furnace_power above --furnace-w, compressor off.
                     Heat cycles ran 569-602 W [M, 9 cycles 10-06..10-10];
                     fan-only 126-134 W [M, 2026-08-24..09-23]
            oven     sensor.sem_counter_1_power above --oven-w (the range's CT,
                     Bill 2026-10-02; oven sessions 350-700 W [M])
          Gas falls in 'navien', 'furnace', 'oven', 'shared' (two or more) or
          'none'. Navien gas lies in [navien, navien + shared]. The estimate
          splits each shared interval by rate x on-time, each rate measured
          from that load's own single-load intervals in the same month [D].
  hours   plug time above HA's recirc threshold (the definition behind
          binary_sensor.hwh_recirc_pump_running, packages/spc.yaml) against the
          panel's recirc hours, and against HA's own hwh_recirc_runtime_today
          as a check on this script; plug time at --fire-w..threshold against
          the panel's operating hours.

WHAT THE REPORT DOES NOT ESTABLISH
  - What the panel counts as operating and recirc hours: the Quick Install
    Guide does not define them [I]. Plug hours are a proxy.
  - The condensate pump shares the plug (Bill, 2026-10-22) and is not separable
    from burner or recirc time (open_questions.yaml, 2026-10-22 entry).
  - Cooktop gas has no electrical signature (2-6 ft3 in September [D]) and stays
    in whatever class it falls in. A class boundary can move one 2 ft3 step.
  - One month is n=1. The report prints differences, not verdicts.

Exit 0 only when every comparison ran and every check agreed; 2 when anything
printed a WARN (R8: a comparison that did not run is never silent); 1 when the
selftest fails.

Usage:
  HA_CONFIG='H:/' python scripts/navien_xcheck.py                    # previous month
  HA_CONFIG='H:/' python scripts/navien_xcheck.py --month 2026-09
  HA_CONFIG='H:/' python scripts/navien_xcheck.py --month 2026-10 --end 2026-10-23
  HA_CONFIG='H:/' python scripts/navien_xcheck.py --thm 8.6986 --op 11 --recirc 17
  python scripts/navien_xcheck.py --selftest                         # R7 gate, no network
HA_URL and HA_TOKEN are needed only for the recirc threshold.
"""

import argparse
import bisect
import itertools
import json
import os
import re
import sys
import urllib.request
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import furnace_gas_cycles as F  # R10: its InfluxDB and series helpers

MONTHS = [
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
]
# A slot saved this long after its month ended holds a later year's figure [I]
SAVE_WINDOW_S = 62 * 86400
# Plug vs HA's history_stats [I: HA shows 0.01 h, 31 days = 0.16 h of rounding;
# falsified if a month with no plug outage disagrees by more]
RUNTIME_TOL_H = 0.25


# --- pure core: everything below is exercised by --selftest -------------------


def month_bounds(ym, tz):
    y, m = (int(x) for x in ym.split("-"))
    t0 = datetime(y, m, 1, tzinfo=tz)
    t1 = datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=tz)
    return t0.timestamp(), t1.timestamp()


def save_time(series):
    """(when, value) a helper took its current value: the first point of the final
    run of equal values, so a restart re-writing an unchanged value does not move it."""
    ts, vs = series
    if not ts:
        return None, None
    i = len(vs) - 1
    while i > 0 and vs[i - 1] == vs[i]:
        i -= 1
    return ts[i], vs[-1]


def slot_valid(saved, t1):
    """save_dhw_button writes the PREVIOUS month's slot, so the slot for a month
    ending at t1 holds this year's figure only if it was saved after t1."""
    return saved is not None and t1 <= saved < t1 + SAVE_WINDOW_S


def thm_factor(pkg_text):
    """The therm -> CCF factor save_dhw_button applied (read, never copied: R10)."""
    found = re.findall(r"input_thm \* ([0-9.]+)", pkg_text)
    if len(found) != 1:
        raise ValueError(
            f"expected one 'input_thm * <factor>' in gas_dhw.yaml, found {len(found)}"
        )
    return float(found[0])


def band_hours(nav, t0, t1, idle_w, fire_w, thr):
    """Seconds per plug band over [t0, t1), each value held to the next point
    (InfluxDB writes on change). recirc is > thr, as HA defines it; a sample of
    exactly fire_w is 'op' here but starts no gas span (F.ct_runs is strict) -
    immaterial at the plug's 0.1 W steps."""
    ts, vs = nav
    out = dict.fromkeys(("idle", "post", "op", "recirc"), 0.0)
    for i, (t, v) in enumerate(zip(ts, vs)):
        a, b = max(t, t0), min(ts[i + 1] if i + 1 < len(ts) else t1, t1)
        if b > a:
            k = (
                "recirc"
                if v > thr
                else "op"
                if v >= fire_w
                else "post"
                if v >= idle_w
                else "idle"
            )
            out[k] += b - a
    return out


def ha_runtime(rt, t0, t1, tz):
    """Sum of sensor.hwh_recirc_runtime_today's daily maxima over [t0, t1), days seen."""
    d0 = datetime.fromtimestamp(t0, tz).date()
    d1 = datetime.fromtimestamp(t1 - 1, tz).date()
    day = {}
    for t, v in zip(*rt):
        d = datetime.fromtimestamp(t - 1, tz).date()  # a 00:00:00 reset is the old day
        if d0 <= d <= d1:
            day[d] = max(day.get(d, 0.0), v)
    return sum(day.values()), len(day)


def load_spans(S, o):
    """On-spans per gas load. The furnace CT also carries cooling and fan-only:
    a span with the compressor on at any point is dropped, and fan-only sits
    below --furnace-w. With no compressor data every span stays - the Navien
    then loses gas to 'shared', which widens its range and never narrows it."""
    nav, _ = F.ct_runs(S["nav"], o.fire_w, 0, 0)
    furn, _ = F.ct_runs(S["ct"], o.furnace_w, 0, 0)
    if S["ac"][0]:
        furn = [(a, b) for a, b in furn if (F.max_over(S["ac"], a, b) or 0) < 0.5]
    oven, _ = F.ct_runs(S["oven"], o.oven_w, 0, 0)
    return {"navien": nav, "furnace": furn, "oven": oven}


def pad_merge(spans, lead, settle):
    out = []
    for s, e in sorted(spans):
        s, e = s - lead, e + settle
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def coverage(spans):
    """f(a, b) = seconds of [a, b] inside sorted, disjoint spans."""
    st = [s for s, _ in spans]
    en = [e for _, e in spans]

    def cov(a, b):
        j, tot = bisect.bisect_right(en, a), 0.0
        while j < len(st) and st[j] < b:
            tot += min(en[j], b) - max(st[j], a)
            j += 1
        return tot

    return cov


def classify(dec, vol, spans, t0, t1, lead, settle):
    """Gas per class over the decode intervals inside [t0, t1). A load is on in an
    interval if its span, widened by lead before and settle after, overlaps it:
    the meter reports gas at the first decode after it burns [I: settle is the
    report lag; the report prints three pad settings so its effect is visible]."""
    cov = {k: coverage(pad_merge(v, lead, settle)) for k, v in spans.items()}
    ds = [d for d in dec if t0 <= d < t1]
    vals = [F.step_at(vol, d + F.DECODE_TOL) for d in ds]
    gas = dict.fromkeys((*spans, "shared", "none"), 0.0)
    hrs = dict.fromkeys(gas, 0.0)
    solo = {k: [0.0, 0.0] for k in spans}
    shared, neg, gap = [], 0, 0.0
    for (a, va), (b, vb) in itertools.pairwise(zip(ds, vals)):
        gap = max(gap, b - a)
        if va is None or vb is None:
            continue
        dv = vb - va
        neg += dv < 0
        act = {k: c(a, b) for k, c in cov.items()}
        on = [k for k in act if act[k] > 0]
        cls = on[0] if len(on) == 1 else "shared" if on else "none"
        gas[cls] += dv
        hrs[cls] += b - a
        if len(on) == 1:
            solo[cls][0] += dv
            solo[cls][1] += act[cls]
        elif on:
            shared.append((dv, {k: act[k] for k in on}))
    rate = {k: g / s * 3600 for k, (g, s) in solo.items() if s > 0}
    est, unsplit = gas["navien"], 0.0
    for dv, act in shared:
        if "navien" not in act:
            continue
        if any(k not in rate for k in act):
            unsplit += dv  # a load with no single-load rate this month
            continue
        w = {k: rate[k] * s for k, s in act.items()}
        tot = sum(w.values())
        est += dv * (w["navien"] / tot if tot > 0 else 1 / len(w))
    v0, v1 = F.step_at(vol, t0), F.step_at(vol, t1)
    total = v1 - v0 if v0 is not None and v1 is not None else None
    return {
        "gas": gas,
        "hrs": hrs,
        "rate": rate,
        "est": est,
        "unsplit": unsplit,
        "total": total,
        "outside": total - sum(gas.values()) if total is not None else None,
        "n_dec": len(ds),
        "neg": neg,
        "gap": gap,
    }


# --- network ------------------------------------------------------------------


def ha_state(eid):
    """One live HA state over REST, or None without HA_URL/HA_TOKEN or on error."""
    url, tok = os.environ.get("HA_URL"), os.environ.get("HA_TOKEN")
    if not (url and tok):
        return None
    req = urllib.request.Request(
        f"{url}/api/states/{eid}", headers={"Authorization": f"Bearer {tok}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r).get("state")
    except (OSError, ValueError):
        return None


def panel(c, mon, t1, now, o, tz, factor, warn):
    """Panel figures for the month: archive slots, each proven this year's, or the
    command-line values. Returns {key: (value, source)}; a refused slot is absent."""
    out = {}
    slots = (
        ("ccf", f"input_number.dhw_archive_{mon}", f"dhw_archive_{mon}", o.thm),
        ("op", "h", f"dhw_op_hrs_archive_{mon}", o.op),
        ("recirc", "h", f"dhw_recirc_hrs_archive_{mon}", o.recirc),
    )
    for key, meas, eid, given in slots:
        if given is not None:
            out[key] = (given, "command line")
            continue
        saved, val = save_time(F.fetch(c, meas, eid, 0, now, "input_number"))
        when = (
            f"{datetime.fromtimestamp(saved, tz):%Y-%m-%d %H:%M}" if saved else "never"
        )
        if slot_valid(saved, t1):
            out[key] = (val, f"input_number.{eid}, saved {when}")
        else:
            warn.append(
                f"input_number.{eid} = {val} was saved {when}, not in the {SAVE_WINDOW_S // 86400}"
                f" days after the month ended: it is another year's figure. Not compared."
                f" Fix: Save DHW (Navien) on the 1st, or pass the figure on the command line"
            )
    if "ccf" in out and o.thm is None:
        out["thm"] = (out["ccf"][0] / factor, f"{out['ccf'][1]} / {factor}")
        out["thm_pm"] = 0.005 / factor  # save_dhw_button rounds CCF to 0.01
    elif o.thm is not None:
        out["thm"] = out.pop("ccf")
    return out


def report(o, tz, t0, t1, partial, P, btu, H, ha_h, ha_days, thr, R, nav_gap, warn):
    fmt = "%Y-%m-%d %H:%M"
    print(
        f"Navien cross-check {datetime.fromtimestamp(t0, tz):{fmt}} -> "
        f"{datetime.fromtimestamp(t1, tz):{fmt}} local"
        + (" (PARTIAL month)" if partial else "")
    )
    print("\nPANEL")
    if not P:
        print("  none this year's - see WARN")
    for key, lab in (("thm", "therm"), ("op", "op h"), ("recirc", "recirc h")):
        if key in P:
            print(f"  {lab:9s} {P[key][0]:9.4f}   [{P[key][1]}]")
    pft3 = P["thm"][0] * 100000 / btu if "thm" in P and btu else None
    if pft3 is not None:
        pm = P.get("thm_pm", 0) * 100000 / btu
        print(
            f"  gas       {pft3:9.1f} ft3 [D: therm x 100,000 / {btu:g} Btu/ft3, input_number.gas_btu_factor]"
            + (f" +/- {pm:.1f} (the archive's 0.01 CCF rounding)" if pm else "")
        )

    print("\nSDR GAS")
    d = R[1]
    if d["total"] is None:
        warn.append(
            "gas register unreadable at a month boundary - no gas comparison. Fix: check sensor.gas_meter_volume in InfluxDB"
        )
    else:
        print(
            f"  whole house {d['total']:6.0f} ft3 [M: sensor.gas_meter_volume, register delta]"
        )
        print(
            f"  decodes {d['n_dec']}, longest gap {d['gap'] / 60:.1f} min, backward steps {d['neg']} [M]"
        )
        print(
            f"  {'class':9s} {'ft3':>7s} {'int. h':>7s}   (hours of decode intervals in the class,"
            f" not on-time; pads lead/settle {o.lead:g}/{o.settle:g} s)"
        )
        for k, v in d["gas"].items():
            print(
                f"  {k:9s} {v:7.0f} {d['hrs'][k] / 3600:7.2f}"
                + (
                    "   (no load's signature: cooktop, or a load in a data gap)"
                    if k == "none"
                    else ""
                )
            )
        print(
            f"  {'outside':9s} {d['outside']:7.0f}    -     (before the first / after the last decode)"
        )
        rates = ", ".join(f"{k} {v:.1f}" for k, v in d["rate"].items())
        print(f"  single-load rates, ft3 per padded on-hour [M]: {rates}")
        lo, hi = d["gas"]["navien"], d["gas"]["navien"] + d["gas"]["shared"]
        print(
            f"  NAVIEN    range {lo:.0f}-{hi:.0f} ft3 [M: navien .. navien + shared]; "
            f"estimate {d['est']:.0f} ft3 [D: shared split by rate x on-time]"
        )
        print(
            "  pads 0/0, default, x2 -> estimate "
            + ", ".join(f"{R[i]['est']:.0f}" for i in range(3))
            + " ft3; range low end "
            + ", ".join(f"{R[i]['gas']['navien']:.0f}" for i in range(3))
        )
        if d["unsplit"]:
            warn.append(
                f"{d['unsplit']:.0f} ft3 of shared gas has a load with no single-load rate this month;"
                f" the estimate leaves it out (it is inside the range). Fix: none - widen the range by hand"
            )
        if pft3 is not None and not partial:
            where = "below" if pft3 < lo else "above" if pft3 > hi else "inside"
            print(
                f"  panel - estimate = {pft3 - d['est']:+.0f} ft3 [D]; panel is {where} the range"
            )

    print("\nPLUG HOURS [M: sensor.hwh_current_consumption, time-weighted]")
    print(
        f"  recirc  > {thr:g} W       {H['recirc'] / 3600:6.2f} h | HA hwh_recirc_runtime_today, "
        f"{ha_days} days: {ha_h:.2f} h"
        + (
            f" | panel {P['recirc'][0]:g} h, plug - panel {H['recirc'] / 3600 - P['recirc'][0]:+.2f} h [D]"
            if "recirc" in P and not partial
            else ""
        )
    )
    print(
        f"  op      {o.fire_w:g}-{thr:g} W      {H['op'] / 3600:6.2f} h"
        + (
            f" | panel {P['op'][0]:g} h, plug - panel {H['op'] / 3600 - P['op'][0]:+.2f} h [D]"
            if "op" in P and not partial
            else ""
        )
    )
    print(
        f"  >= {o.fire_w:g} W {(H['op'] + H['recirc']) / 3600:6.2f} h; {o.idle_w:g}-{o.fire_w:g} W "
        f"{H['post'] / 3600:.2f} h; idle {H['idle'] / 3600:.2f} h; longest plug gap {nav_gap / 60:.1f} min"
    )
    if abs(H["recirc"] / 3600 - ha_h) > RUNTIME_TOL_H:
        warn.append(
            f"plug > {thr:g} W ({H['recirc'] / 3600:.2f} h) and HA's runtime ({ha_h:.2f} h) differ by more"
            f" than {RUNTIME_TOL_H} h: the threshold changed in the month, or the plug or HA had an outage"
        )
    if partial:
        warn.append(
            "partial month: the panel figures are whole months, so nothing was compared"
        )
    print()
    for w in warn:
        print(f"WARN: {w}")
    print(
        "NOT ESTABLISHED: panel hour definitions [I]; condensate pump time (shares the plug); cooktop gas;"
        " n=1 month"
    )
    return 2 if warn else 0


def main():
    o = parse(sys.argv[1:])
    if o.selftest:
        return selftest()
    from zoneinfo import ZoneInfo

    cfg = os.environ.get("HA_CONFIG")
    if not cfg:  # never default it (CLAUDE.md, off-host gotchas)
        print(
            "HA_CONFIG is not set - e.g. HA_CONFIG='H:/' off-host, /config on the host"
        )
        return 2
    with open(f"{cfg}/.storage/core.config", encoding="utf-8") as fh:  # read-only
        tz = ZoneInfo(json.load(fh)["data"]["time_zone"])
    with open(f"{cfg}/packages/gas_dhw.yaml", encoding="utf-8") as fh:
        factor = thm_factor(fh.read())
    now = datetime.now(tz)
    ym = o.month or (
        f"{now.year - 1}-12" if now.month == 1 else f"{now.year}-{now.month - 1:02d}"
    )
    t0, t1 = month_bounds(ym, tz)
    month_end = t1
    if o.end:
        t1 = min(
            t1, datetime.strptime(o.end, "%Y-%m-%d").replace(tzinfo=tz).timestamp()
        )
    t1 = min(t1, now.timestamp())
    partial = t1 < month_end
    warn = []
    c = F._creds()
    pad = 3600
    S = {
        "nav": F.fetch(c, "W", "hwh_current_consumption", t0 - pad, t1 + pad, "sensor"),
        "ct": F.fetch(c, "W", "sem_furnace_power", t0 - pad, t1 + pad, "sensor"),
        "ac": F.fetch(
            c,
            "binary_sensor.ac_compressor_running",
            "ac_compressor_running",
            t0 - pad,
            t1 + pad,
        ),
        "oven": F.fetch(c, "W", "sem_counter_1_power", t0 - pad, t1 + pad, "sensor"),
        "vol": F.fetch(c, "ft\u00b3", "gas_meter_volume", t0 - pad, t1 + pad, "sensor"),
        "age": F.fetch(c, "min", "gas_meter_age", t0 - pad, t1 + pad, "sensor"),
        "rt": F.fetch(c, "h", "hwh_recirc_runtime_today", t0, t1 + 60, "sensor"),
        "btu": F.fetch(
            c,
            "BTU/ft\u00b3",
            "gas_btu_factor",
            now.timestamp(),
            now.timestamp(),
            "input_number",
        ),
    }
    for k in ("nav", "vol", "age"):
        if not S[k][0]:
            print(
                f"WARN: no data for '{k}' in range - nothing compared. Fix: check InfluxDB"
            )
            return 2
    for k, eid in (("ct", "sem_furnace_power"), ("oven", "sem_counter_1_power")):
        if not S[k][0]:
            warn.append(
                f"no {eid} data: its gas cannot be told from the Navien's, so the gas figures include it."
                f" Fix: check sensor.{eid} in InfluxDB"
            )
    if not S["ac"][0]:
        warn.append(
            "no ac_compressor_running data: cooling runs count as furnace (Navien range widened, not narrowed)"
        )
    thr = ha_state("input_number.hwh_recirc_power_threshold")
    try:
        thr = float(thr)
    except (TypeError, ValueError):
        warn.append(
            f"input_number.hwh_recirc_power_threshold not read (HA_URL/HA_TOKEN?): using --recirc-w {o.recirc_w:g}"
        )
        thr = o.recirc_w
    btu = F.step_at(S["btu"], now.timestamp())
    if not btu:
        warn.append(
            "input_number.gas_btu_factor not in InfluxDB: panel gas not converted to ft3"
        )
    P = panel(
        c, MONTHS[int(ym[5:7]) - 1], month_end, now.timestamp(), o, tz, factor, warn
    )
    H = band_hours(S["nav"], t0, t1, o.idle_w, o.fire_w, thr)
    ha_h, ha_days = ha_runtime(S["rt"], t0, t1, tz)
    nts = [t for t in S["nav"][0] if t0 <= t < t1]
    nav_gap = max((b - a for a, b in itertools.pairwise(nts)), default=0.0)
    spans = load_spans(S, o)
    dec = F.decode_times(S["age"])
    R = [
        classify(dec, S["vol"], spans, t0, t1, o.lead * k, o.settle * k)
        for k in (0, 1, 2)
    ]
    return report(
        o, tz, t0, t1, partial, P, btu, H, ha_h, ha_days, thr, R, nav_gap, warn
    )


def selftest():
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/New_York")
    t0 = datetime(2026, 11, 10, tzinfo=tz).timestamp()
    t1 = t0 + 86400

    def series(events, base, step=10.0):
        """write-on-change samples; events are (start_min, end_min, value)"""
        ts, vs, last, t = [], [], None, t0 - 3600
        while t <= t1 + 3600:
            m = (t - t0) / 60
            v = next((w for a, b, w in events if a <= m < b), base)
            if v != last:
                ts.append(t)
                vs.append(v)
                last = v
            t += step
        return ts, vs

    # Navien: op-band fires, a post-fire tail, a recirc hour, one fire inside a
    # cooling run, one inside a fan-only run, one inside a furnace heat cycle
    nav_ev = [(60, 70, 25), (70, 75, 15), (200, 230, 25), (310, 320, 25)]
    nav_ev += [(400, 460, 100), (510, 515, 30), (810, 820, 30)]
    ct_ev = [(300, 340, 900), (500, 540, 130), (600, 630, 580), (800, 830, 580)]
    flows_nav = [(60, 70, 30), (200, 230, 30), (310, 320, 30), (400, 460, 25)]
    flows_nav += [(510, 515, 30), (810, 820, 30)]
    flows = flows_nav + [(600, 630, 95), (800, 830, 95), (1000, 1060, 10)]

    def cum(t, fl):
        m = (t - t0) / 60
        return sum(r * max(0.0, min(m, b) - a) / 60 for a, b, r in fl)

    true_nav = cum(t1, flows_nav)  # 57.5 ft3
    # 52.5 ft3: the Navien's gas outside the 800-830 heat cycle
    nav_alone = cum(t1, [f for f in flows_nav if f[0] != 810])
    furn_all = cum(t1, [(600, 630, 95), (800, 830, 95)])  # 95 ft3
    dec = [t0 - 600 + 40.0 * k for k in range(int((86400 + 1200) / 40))]
    vol, last = ([], []), None
    for d in dec:
        v = 1000 + 2 * int(cum(d, flows) // 2)
        if v != last:
            vol[0].append(d)
            vol[1].append(v)
            last = v
    S = {
        "nav": series(nav_ev, 2.0),
        "ct": series(ct_ev, 1.5),
        "ac": series([(300, 340, 1)], 0),
        "oven": series([(1000, 1060, 500)], 0.0),
    }
    o = parse([])
    H = band_hours(S["nav"], t0, t1, o.idle_w, o.fire_w, o.recirc_w)
    sp = load_spans(S, o)
    r = classify(dec, vol, sp, t0, t1, o.lead, o.settle)
    no_furn = classify(dec, vol, dict(sp, furnace=[]), t0, t1, o.lead, o.settle)
    sp_noac = load_spans(dict(S, ac=([], [])), o)
    r_noac = classify(dec, vol, sp_noac, t0, t1, o.lead, o.settle)
    # history_stats: carried-in value from the day before (excluded), two days summed
    day = 86400
    rt = (
        [t0, t0 + 3600, t0 + 7200, t0 + day, t0 + day + 60, t0 + day + 3600],
        [5.0, 0.5, 1.0, 0.0, 0.2, 2.0],
    )
    pkg = 'current_dhw: "{{ (input_thm * 0.9643) | round(2) }}"'

    def raises(text):
        try:
            thm_factor(text)
        except ValueError:
            return True
        return False

    checks = [
        ("A recirc band is 1.00 h", abs(H["recirc"] - 3600) < 1),
        (
            "B op band is 65 min, post-fire 5 min",
            abs(H["op"] - 3900) < 1 and abs(H["post"] - 300) < 1,
        ),
        ("C cooling and fan-only runs are not furnace", len(sp["furnace"]) == 2),
        (
            "D Navien-only class holds no furnace gas",
            abs(r["gas"]["navien"] - nav_alone) <= 2,
        ),
        (
            "E furnace gas lands in 'furnace' or 'shared', never 'navien'",
            r["gas"]["furnace"] + r["gas"]["shared"] - (true_nav - nav_alone)
            >= furn_all - 2,
        ),
        (
            "F estimate within 2 steps of the true Navien gas",
            abs(r["est"] - true_nav) <= 4,
        ),
        (
            "G FAULT no furnace CT: Navien absorbs furnace gas",
            no_furn["est"] - true_nav > 10,
        ),
        (
            "H FAULT no compressor: the cooling-run fire goes to shared",
            r_noac["gas"]["navien"] <= r["gas"]["navien"] - 4,
        ),
        (
            "I conservation: classes + outside = register delta",
            abs(sum(r["gas"].values()) + r["outside"] - r["total"]) < 1e-9,
        ),
        ("J slot saved before the month ended is refused", not slot_valid(t1 - 60, t1)),
        ("K slot saved the next day is accepted", slot_valid(t1 + day, t1)),
        (
            "L slot saved a year later is refused",
            not slot_valid(t1 + 400 * day, t1) and not slot_valid(None, t1),
        ),
        (
            "M save time ignores a restart re-write",
            save_time(([1, 2, 3], [5.0, 8.39, 8.39])) == (2, 8.39),
        ),
        ("N factor read from the automation", thm_factor(pkg) == 0.9643),
        ("O FAULT factor missing or doubled raises", raises("") and raises(pkg + pkg)),
        (
            "P HA runtime sums 2 days, drops the carried-in day",
            ha_runtime(rt, t0, t0 + 2 * day, tz) == (3.0, 2),
        ),
    ]
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("  ok   " if ok else "  FAIL ") + name)
    print(
        f"  (true Navien {true_nav:.1f} ft3, estimate {r['est']:.1f}, range "
        f"{r['gas']['navien']:.0f}-{r['gas']['navien'] + r['gas']['shared']:.0f}, furnace {r['gas']['furnace']:.0f})"
    )
    print(
        "SELFTEST "
        + ("PASSED" if not bad else "FAILED")
        + f" {len(checks) - len(bad)}/{len(checks)}"
    )
    return 1 if bad else 0


def parse(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--month", help="YYYY-MM local (default: the previous month)")
    p.add_argument(
        "--end", help="YYYY-MM-DD local, exclusive: a partial month, nothing compared"
    )
    p.add_argument(
        "--thm", type=float, help="panel therms, instead of the archive slot"
    )
    p.add_argument(
        "--op", type=float, help="panel operating hours, instead of the archive slot"
    )
    p.add_argument(
        "--recirc", type=float, help="panel recirc hours, instead of the archive slot"
    )
    p.add_argument(
        "--fire-w",
        type=float,
        default=20,
        help="plug W above which the Navien is firing or pumping: 20-70 W burned 29.9 ft3/h, "
        "12-20 W 0.76 ft3/h [M, September 2026]",
    )
    p.add_argument(
        "--idle-w",
        type=float,
        default=12,
        help="plug idle ceiling, W (2026-09-16 Kasa-plug entry)",
    )
    p.add_argument(
        "--recirc-w",
        type=float,
        default=70,
        help="used only when input_number.hwh_recirc_power_threshold cannot be read",
    )
    p.add_argument(
        "--furnace-w",
        type=float,
        default=300,
        help="furnace CT W for a heat cycle: heat 569-602 W, fan-only 126-134 W [M]",
    )
    p.add_argument(
        "--oven-w",
        type=float,
        default=300,
        help="range CT W for the oven: sessions 350-700 W [M]",
    )
    p.add_argument(
        "--lead",
        type=float,
        default=30,
        help="s a load counts as on before its span [I]",
    )
    p.add_argument(
        "--settle",
        type=float,
        default=90,
        help="s a load counts as on after its span: report lag [I]",
    )
    p.add_argument(
        "--selftest", action="store_true", help="synthetic fault injection, no network"
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
