#!/usr/bin/env python3
"""
daily_energy_export.py  — hardened daily energy CSV export from HA statistics.

Reads Home Assistant's long-term `statistics` table (purge-immune), read-only,
safe alongside a live HA (SQLite WAL). Writes, per day:
  energy_YYYY-MM-DD.csv     wide: hour rows x entity cols + TOTAL row
  energy_daily_master.csv   one row/day: per-entity totals + reconciliation

Topology-aware:
  whole_home = sum(SEM_BRANCHES) + other
  other      = other_attributed(standalone Kasa) + true_residual
  sub-metered Kasa are INSIDE a SEM circuit -> informational, never summed.

Utility meters (rtlamr2mqtt / NooElec V5 SDR, added 2026-08-21):
  gas ft3, water gal, and revenue-grade electric kWh ride the SAME hourly
  statistics-sum-delta path as the SEM circuits - NOT the utility_meter daily
  helper entities, whose midnight reset makes the day boundary ambiguous and
  which cannot be backfilled. Utility columns are BLANK (not 0.0) on days the
  SDR produced no statistics, so pre-install days stay distinguishable from
  genuine zero consumption.

Hardening:
  * atomic writes (temp + fsync + os.replace); master fully rewritten each run
  * header migrated by column NAME (schema-drift safe)
  * self-healing backfill of missing days; --date/--from/--through/--force
  * whole_home<=0 days skipped; _hours column exposes partial/DST/gap days
  * lockfile prevents overlapping runs; never processes 'today' (incomplete)

Usage:
  daily_energy_export.py                      # backfill START..yesterday (gaps only)
  daily_energy_export.py --date 2026-06-29    # one day (recompute)
  daily_energy_export.py --from 2026-06-28 --through 2026-06-30 [--force]
Stdlib only.
"""

import argparse
import csv
import os
import sqlite3
import sys
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# ===================== CONFIG =====================
DB         = os.environ.get("HA_DB", "/config/home-assistant_v2.db")
OUT_DIR    = os.environ.get("ENERGY_OUT_DIR", "/config/www/energy")
TZ         = ZoneInfo(os.environ.get("ENERGY_TZ", "America/New_York"))
RATE       = float(os.environ.get("ENERGY_RATE", "0.29"))
START_DATE = os.environ.get("ENERGY_START", "2026-06-28")   # first FULL day

SEM_WHOLE = "sensor.sem_whole_home_energy"
SEM_BRANCHES = [
    "sensor.sem_ac_energy", "sensor.sem_furnace_energy", "sensor.sem_fridge_energy",
    "sensor.sem_bedroom_office_energy", "sensor.sem_family_room_energy",
    "sensor.sem_master_suite_energy", "sensor.sem_counter_1_energy",
    "sensor.sem_counter_2_energy", "sensor.sem_dishwasher_disposal_energy",
    "sensor.sem_microwave_energy", "sensor.sem_dining_kitchen_lights_energy",
    "sensor.sem_garage_energy", "sensor.sem_dryer_energy",
    "sensor.sem_washer_energy", "sensor.sem_laundry_bedroom_energy",
]
KASA_STANDALONE = [   # no SEM CT -> live inside "Other"; summed to other_attributed
    "sensor.dehumidifier_energy",
    "sensor.hwh_today_s_consumption",
    "sensor.basement_router_today_s_consumption",
]
KASA_SUBMETERED = {   # inside a SEM circuit already counted; informational only
    "sensor.computer_outlet_today_s_consumption": "sensor.sem_bedroom_office_energy",
    "sensor.tv_room_today_s_consumption":          "sensor.sem_bedroom_office_energy",
    "sensor.living_room_tv_sonos_homatics_today_s_consumption": "sensor.sem_family_room_energy",
}

# SDR utility meters (packages/utility_meters.yaml). These are the ENGINEERING
# UNIT template sensors, not the raw *_reading counters: the raw counter is
# scaled by an input_number that can change, and only the scaled sensor is
# guaranteed to be in real units for every historical hour.
UTILITY_GAS   = "sensor.gas_meter_volume"        # ft3
UTILITY_WATER = "sensor.water_meter_volume"      # gal
UTILITY_ELEC  = "sensor.electric_meter_energy"   # kWh, revenue-grade
UTILITY = [UTILITY_GAS, UTILITY_WATER, UTILITY_ELEC]
UTILITY_ROUND = {UTILITY_GAS: 1, UTILITY_WATER: 2, UTILITY_ELEC: 3}

# Therms are DERIVED here rather than read from sensor.gas_meter_therms.
# That sensor multiplies by two input_numbers taken off the CNG bill; editing
# either one steps its statistics sum, which would land as one bogus spike in
# whichever day the edit happened. Deriving from ft3 keeps every historical
# day recomputable, and the factors used are stamped into each daily file.
GAS_BTU = float(os.environ.get("ENERGY_GAS_BTU", "1030"))      # BTU/ft3
GAS_PF  = float(os.environ.get("ENERGY_GAS_PF", "1.0"))        # pressure corr.
# =================================================

SEM_ENTITIES = [SEM_WHOLE] + SEM_BRANCHES + KASA_STANDALONE + list(KASA_SUBMETERED)
ENTITIES = SEM_ENTITIES + UTILITY
# _hours stays a SEM-only coverage figure so its meaning does not shift for
# rows written before the SDR existed.
RECON_COLS = ["_hours", "_branch_sum", "_other", "_other_attributed", "_true_residual",
              "_gas_therms", "_sem_vs_util_pct"]
# Blank rather than 0.0 when absent: a missing SDR day is not a zero-use day.
BLANK_IF_ABSENT = set(UTILITY) | {"_gas_therms", "_sem_vs_util_pct"}
MASTER_HEADER = ["date"] + ENTITIES + RECON_COLS
LOCK = os.path.join(tempfile.gettempdir(), "daily_energy_export.lock")


def log(*a): print("[energy_export]", *a, file=sys.stderr)


def local_day_bounds(d: date):
    """DST-safe local-midnight epoch bounds for calendar date d."""
    start = datetime(d.year, d.month, d.day, tzinfo=TZ)
    end = start + timedelta(days=1)
    return start.timestamp(), end.timestamp()


def query_day(con, start_ts, end_ts):
    ph = ",".join("?" * len(ENTITIES))
    q = f"""
        WITH d AS (
          SELECT sm.statistic_id AS entity, s.start_ts,
                 s.sum - LAG(s.sum) OVER
                   (PARTITION BY sm.statistic_id ORDER BY s.start_ts) AS delta
          FROM statistics s JOIN statistics_meta sm ON s.metadata_id = sm.id
          WHERE sm.statistic_id IN ({ph})
            AND s.start_ts >= ? - 3600 AND s.start_ts < ?
        )
        SELECT start_ts, entity, delta FROM d
        WHERE delta >= 0 AND start_ts >= ?
        ORDER BY start_ts, entity;
    """
    rows = con.execute(q, [*ENTITIES, start_ts, end_ts, start_ts]).fetchall()
    grid = defaultdict(dict)
    for ts, entity, delta in rows:
        hh = datetime.fromtimestamp(ts, TZ).strftime("%H:00")
        grid[hh][entity] = round(delta, 3)
    return grid


def atomic_write(path, write_fn):
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_energy_", suffix=".csv")
    try:
        with os.fdopen(fd, "w", newline="") as f:
            write_fn(f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)   # atomic on same filesystem
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def compute(grid):
    hours = sorted(grid)
    tot = {e: round(sum(grid[h].get(e, 0.0) for h in hours), 3) for e in SEM_ENTITIES}

    # A utility meter that reported nothing all day gets None, not 0.0 - the
    # whole point of the staleness work in packages/utility_meters.yaml is that
    # "silent" and "used nothing" are different failures, and gas legitimately
    # goes days without a tick in summer, so the distinction has to survive
    # into the report.
    for e in UTILITY:
        if any(e in grid[h] for h in hours):
            tot[e] = round(sum(grid[h].get(e, 0.0) for h in hours), UTILITY_ROUND[e])
        else:
            tot[e] = None

    whole = tot.get(SEM_WHOLE, 0.0)
    branch_sum = round(sum(tot.get(e, 0.0) for e in SEM_BRANCHES), 3)
    other = round(whole - branch_sum, 3)
    attributed = round(sum(tot.get(e, 0.0) for e in KASA_STANDALONE), 3)
    residual = round(other - attributed, 3)

    # _hours counts SEM coverage only - see RECON_COLS.
    sem_hours = sum(1 for h in hours if any(e in grid[h] for e in SEM_ENTITIES))

    gas = tot.get(UTILITY_GAS)
    therms = round(gas * GAS_BTU * GAS_PF / 100000, 4) if gas is not None else None

    # Daily SEM-vs-utility error. Positive = SEM reads HIGH. A full calendar
    # day is the only honest window for this: the utility figure is a counter
    # difference at a 30-90 s decode cadence, so any shorter comparison is
    # dominated by where the decode boundaries happen to land.
    # Both sides must cover the SAME day or the ratio is meaningless: on the
    # SDR install day SEM had 19 h and the utility counter 4 h, which produced
    # a nonsense +495%. Require near-full coverage on both, else leave blank.
    util_kwh = tot.get(UTILITY_ELEC)
    util_hours = sum(1 for h in hours if UTILITY_ELEC in grid[h])
    if (util_kwh is not None and util_kwh > 0 and whole > 0
            and util_hours >= 23 and sem_hours >= 23):
        sem_vs_util = round(100 * (whole - util_kwh) / util_kwh, 2)
    else:
        sem_vs_util = None

    recon = {"_hours": sem_hours, "_branch_sum": branch_sum, "_other": other,
             "_other_attributed": attributed, "_true_residual": residual,
             "_gas_therms": therms, "_sem_vs_util_pct": sem_vs_util}
    return hours, tot, whole, recon


def write_daily_file(day_str, grid, tot, recon):
    hours = sorted(grid)
    path = os.path.join(OUT_DIR, f"energy_{day_str}.csv")

    def _cell(h, e):
        # Blank the whole utility column on a day the meter never reported, so
        # a dead SDR cannot read as 24 hours of zero use.
        if e in UTILITY and tot.get(e) is None:
            return ""
        return grid[h].get(e, 0.0)

    def _w(f):
        f.write(f"# HA energy export  date={day_str}  tz={TZ}  rate=${RATE}/kWh  "
                f"hours={recon['_hours']}\n")
        f.write("# groups: SEM_WHOLE | SEM_BRANCHES(partition) | "
                "KASA_STANDALONE(in Other) | KASA_SUBMETERED(subset of a SEM ckt; do NOT sum) | "
                "UTILITY(SDR; independent meters, NOT part of the SEM partition)\n")
        f.write(f"# utility units: {UTILITY_GAS}=ft3  {UTILITY_WATER}=gal  "
                f"{UTILITY_ELEC}=kWh   TOTAL row is per-column units, not all kWh\n")
        f.write(f"# gas therms={recon['_gas_therms']} at btu={GAS_BTU} pf={GAS_PF}  "
                f"sem_vs_util={recon['_sem_vs_util_pct']}%\n")
        w = csv.writer(f)
        w.writerow(["hour"] + ENTITIES)
        for h in hours:
            w.writerow([h] + [_cell(h, e) for e in ENTITIES])
        w.writerow(["TOTAL"] + ["" if tot[e] is None else tot[e] for e in ENTITIES])

    atomic_write(path, _w)
    return path


def load_master(path):
    """Return dict[date_str] -> {col: value} keyed by column NAME (drift-safe)."""
    rows = {}
    if not os.path.exists(path):
        return rows, None
    with open(path, newline="") as f:
        r = csv.reader(f)
        try:
            hdr = next(r)
        except StopIteration:
            return rows, None
        for rec in r:
            if not rec or not rec[0]:
                continue
            rows[rec[0]] = {hdr[i]: rec[i] for i in range(min(len(hdr), len(rec)))}
    return rows, hdr


def write_master(path, rows_by_date):
    def _coerce(colname, d):
        v = d.get(colname, "")
        if colname == "date":
            return v
        try:
            return round(float(v), 4 if colname == "_gas_therms" else 3)
        except (TypeError, ValueError):
            if v in ("", None):
                # Pre-SDR rows carry no utility keys at all; they must stay
                # blank through every rewrite, not silently become 0.0.
                return "" if colname in BLANK_IF_ABSENT else 0.0
            return v

    def _w(f):
        w = csv.writer(f)
        w.writerow(MASTER_HEADER)
        for ds in sorted(rows_by_date):
            row = rows_by_date[ds]
            row["date"] = ds
            w.writerow([_coerce(c, row) for c in MASTER_HEADER])

    atomic_write(path, _w)


def daterange(a: date, b: date):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--from", dest="dfrom")
    ap.add_argument("--through", dest="dthrough")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    today = datetime.now(TZ).date()
    yesterday = today - timedelta(days=1)
    start_default = datetime.strptime(START_DATE, "%Y-%m-%d").date()

    if args.date:
        d0 = d1 = datetime.strptime(args.date, "%Y-%m-%d").date()
        force = True
    else:
        d0 = datetime.strptime(args.dfrom, "%Y-%m-%d").date() if args.dfrom else start_default
        d1 = datetime.strptime(args.dthrough, "%Y-%m-%d").date() if args.dthrough else yesterday
        force = args.force

    if d0 < start_default:
        log(f"clamping start {d0} -> {start_default} (first full day)")
        d0 = start_default
    if d1 > yesterday:
        log(f"clamping end {d1} -> {yesterday} (never process today; it's incomplete)")
        d1 = yesterday
    if d0 > d1:
        log(f"nothing to do (range {d0}..{d1} empty).")
        return 0

    # lock (best-effort, prevents overlapping nightly + manual runs).
    # Stale-lock handling (2026-07-03): a SIGKILLed/OOM-killed run leaves the
    # lockfile behind and previously blocked every subsequent nightly run with
    # a silent exit 3 until manual cleanup (/tmp survives until the next host
    # reboot). If the recorded PID is no longer alive, break the lock.
    def _lock_stale():
        try:
            with open(LOCK) as f:
                pid = int(f.read().strip() or 0)
        except (OSError, ValueError):
            return True          # unreadable/garbled lock -> stale
        if pid <= 0:
            return True
        try:
            os.kill(pid, 0)      # signal 0: existence check only
        except ProcessLookupError:
            return True          # no such process -> stale
        except PermissionError:
            return False         # exists, owned by someone else -> live
        return False             # exists -> live

    def _take_lock():
        lk = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(lk, str(os.getpid()).encode())
        os.close(lk)

    try:
        _take_lock()
    except FileExistsError:
        if _lock_stale():
            log(f"breaking stale lock {LOCK} (holder PID not alive).")
            try:
                os.unlink(LOCK)
            except OSError:
                pass
            try:
                _take_lock()
            except FileExistsError:
                log(f"another run re-took {LOCK}; exiting."); return 3
        else:
            log(f"another run holds {LOCK}; exiting."); return 3

    try:
        master_path = os.path.join(OUT_DIR, "energy_daily_master.csv")
        master, old_hdr = load_master(master_path)
        if old_hdr is not None and old_hdr != MASTER_HEADER:
            log(f"master header differs from canonical; migrating by name "
                f"({len(old_hdr)}->{len(MASTER_HEADER)} cols).")

        want = list(daterange(d0, d1))
        todo = [d for d in want if force or d.strftime("%Y-%m-%d") not in master]
        if not todo:
            log(f"master already complete for {d0}..{d1} ({len(want)} days). "
                f"Rewriting to canonicalize header.")
            write_master(master_path, master)
            return 0
        log(f"processing {len(todo)} day(s) in {d0}..{d1} "
            f"(skipping {len(want)-len(todo)} already present).")

        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)
        written, skipped = 0, 0
        try:
            for d in todo:
                ds = d.strftime("%Y-%m-%d")
                s_ts, e_ts = local_day_bounds(d)
                grid = query_day(con, s_ts, e_ts)
                hours, tot, whole, recon = compute(grid)
                if whole <= 0:
                    log(f"{ds}: whole_home={whole} (no SEM data / gap) — skipped.")
                    skipped += 1
                    continue
                if recon["_hours"] < 23:
                    log(f"{ds}: only {recon['_hours']}h (partial/gap/DST) — writing anyway.")
                daily_path = os.path.join(OUT_DIR, f"energy_{ds}.csv")
                if force or not os.path.exists(daily_path):
                    write_daily_file(ds, grid, tot, recon)
                row = {"date": ds}
                row.update({e: tot[e] for e in ENTITIES})
                row.update(recon)
                master[ds] = row
                written += 1
                log(f"{ds}: whole={whole} branches={recon['_branch_sum']} "
                    f"other={recon['_other']} attributed={recon['_other_attributed']} "
                    f"residual={recon['_true_residual']} ({recon['_hours']}h) | "
                    f"gas={tot[UTILITY_GAS]}ft3 water={tot[UTILITY_WATER]}gal "
                    f"util_elec={tot[UTILITY_ELEC]}kWh "
                    f"sem_vs_util={recon['_sem_vs_util_pct']}%")
        finally:
            con.close()

        write_master(master_path, master)
        log(f"done. wrote {written} day(s), skipped {skipped}. master -> {master_path}")
        return 0
    finally:
        try:
            os.unlink(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
