#!/usr/bin/env python3
"""
spc_verify.py — nightly reconciliation of the SPC captures against raw InfluxDB.

WHY THIS EXISTS
---------------
The SPC daily "running watts" that the Grafana panels and the HA dashboard plot
are computed ONCE, by HA, from a `statistics` sensor, and then latched into an
input_number at 23:59. Nothing has ever checked that number against the raw
power series it is supposed to summarise. That is not a hypothetical gap:
CLAUDE.md records the InfluxDB continuous queries sitting 9.0 W away from the
HA charts for a MONTH, and the SPC panels reading four hours off the captures
for a MONTH. Both were found by hand, late, and by accident.

A Grafana snapshot cannot catch that class of bug - it archives whatever the
chart displayed, including the wrong value. Catching it needs two INDEPENDENT
computations of the same quantity, compared. That is all this script does:

    HA side    input_number.<appliance>_running_watts_day_1   (the capture)
    raw side   MEAN(value) FROM "W" WHERE value > threshold   (from InfluxDB)

DAY ALIGNMENT - the thing that makes this trustworthy
-----------------------------------------------------
The capture's own `last_changed` is the alignment. A value latched at 23:59:00
on day D holds day D's mean, so the day being verified is READ OFF THE CAPTURE,
never assumed. This matters: comparing the capture to the wrong calendar day
produces a few percent of fake divergence that looks exactly like a real
offset, and picking the alignment by "which one fits better" is how you talk
yourself into the wrong answer.

The timestamp must fall in the 23:59 capture WINDOW, not merely on the right
date. Same-date is not the same as same-capture: an HA restart replaying
restore_state rewrites the entity mid-afternoon, and a value carried over from a
previous day then looks freshly captured. Rows failing that test are reported
HELD and NOT compared - a slot the guards deliberately declined to overwrite is
not a discrepancy, and comparing it invents one.

WHY IT READS .storage AND NOT THE HA API
----------------------------------------
Same reason as spc_buffer_export.py: no long-lived token, no HA dependency, and
it still works while HA is down. The capture side comes from
.storage/core.restore_state; only the raw side needs the network.

CREDENTIALS
-----------
The env-var-then-secrets.yaml pattern documented in CLAUDE.md. HA's
shell_command environment sets no INFLUXDB_* vars, so the secrets.yaml fallback
is what makes this runnable as a shell_command at all.

APPEND-ONLY
-----------
CLAUDE.md: never overwrite or truncate a CSV. Every run appends.

EXIT CODE
---------
0 = every comparable appliance within band.
1 = at least one DRIFT (a real disagreement).
2 = the check could not run (InfluxDB unreachable, secrets missing, bad parse).

2 is deliberately distinct from 1. If a crash also exited 1 the automation would
raise "SPC Reconciliation Drift" for what is actually a broken checker, and an
alert that lies about its own cause is worse than no alert. Missing raw data for
one appliance is neither: that is NO-RUN/NO-POINT and stays exit 0.

USAGE
-----
    python3 /config/scripts/spc_verify.py              # verify last night
    python3 /config/scripts/spc_verify.py --days 14    # tune the band
    python3 /config/scripts/spc_verify.py --json       # machine readable
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

import yaml

CFG = os.environ.get('HA_CONFIG', '/config')
LOG_DIR = os.path.join(CFG, 'www', 'spc')
LOG_TXT = os.path.join(LOG_DIR, 'spc_verify.log')
LOG_CSV = os.path.join(LOG_DIR, 'spc_verify_history.csv')

# appliance -> (raw influx entity_id tag, threshold input_number, default W)
APPLIANCES = {
    'fridge':       ('sem_fridge_power',                  'fridge_power_threshold',        50.0),
    'furnace':      ('sem_furnace_power',                 'furnace_power_threshold',      300.0),
    'ac':           ('sem_ac_power',                      'ac_power_threshold',           300.0),
    'hwh_recirc':   ('hwh_current_consumption',           'hwh_recirc_power_threshold',    70.0),
    'dehumidifier': ('dehumidifier_current_consumption',  'dehumidifier_power_threshold', 150.0),
}

# Per-appliance tolerance (percent). The capture is a rolling 24h `statistics`
# mean closing at 23:59 with a sampling_size cap; the raw side is a calendar-day
# mean. They are NOT the same quantity, so a few percent is definitional and not
# a fault. Bands are set from the 2026-08-31 measured spread with headroom, and
# are meant to catch a pipeline BREAKING, not to police normal scatter.
# Measured 2026-08-31 with the alignment taken from the capture's own
# last_changed: fridge -0.01%, furnace -0.00%, ac +0.00%, hwh_recirc -0.04%.
# Those four agree to four decimal places because both sides are the unweighted
# mean of the SAME above-threshold samples - so their bands are tight, and any
# real break will be obvious rather than lost in slack.
#
# dehumidifier is the deliberate exception. Its capture reads the STEADY series
# (packages/spc.yaml, "2026-08-07: reads the STEADY series, not the full-run
# one"), a fixed 10-14 min in-run window that excludes compressor ramp-up, so it
# sits ~2% ABOVE a full-run gated mean BY DESIGN. Do not "fix" that +2%: it is
# the two statistics differing, exactly as intended. Its band is wider to hold
# that offset without crying wolf.
BANDS = {
    'fridge': 3.0,
    'furnace': 2.0,
    'ac': 3.0,
    'hwh_recirc': 2.0,
    'dehumidifier': 6.0,
}


def load_secrets():
    try:
        return yaml.safe_load(io.open(os.path.join(CFG, 'secrets.yaml'),
                                      encoding='utf-8')) or {}
    except OSError:
        return {}


_S = load_secrets()
IX_URL = os.environ.get('INFLUXDB_URL') or _S.get('influxdb_url', 'http://127.0.0.1:8086')
IX_USER = os.environ.get('INFLUXDB_USER') or _S.get('influxdb_user', '')
IX_PASS = os.environ.get('INFLUXDB_PASS') or _S.get('influxdb_pass', '')
IX_DB = os.environ.get('INFLUXDB_DB') or _S.get('influxdb_db', 'Home Assistant')


def influx(query):
    prm = {'q': query, 'db': IX_DB, 'epoch': 's'}
    if IX_USER:
        prm['u'] = IX_USER
        prm['p'] = IX_PASS
    url = IX_URL.rstrip('/') + '/query?' + urllib.parse.urlencode(prm)
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def first_series(res):
    try:
        return res['results'][0]['series'][0]['values']
    except (KeyError, IndexError, TypeError):
        return []


def restore_state():
    """entity_id -> (float_or_None, last_changed_datetime_or_None)"""
    path = os.path.join(CFG, '.storage', 'core.restore_state')
    out = {}
    for item in json.load(io.open(path, encoding='utf-8')).get('data', []):
        st = item.get('state') or {}
        eid = st.get('entity_id')
        if not eid:
            continue
        try:
            val = float(st.get('state'))
        except (TypeError, ValueError):
            val = None
        lc = st.get('last_changed')
        try:
            lc = dt.datetime.fromisoformat(lc) if lc else None
        except ValueError:
            lc = None
        out[eid] = (val, lc)
    return out


# The captures fire at 23:59:00 local. Matching only the DATE of last_changed is
# NOT enough: anything else that writes the entity that same calendar day - an HA
# restart replaying restore_state is the common one - makes a value carried over
# from a PREVIOUS day look freshly captured, and the row gets compared instead of
# held. Measured 2026-09-03: HA restarted 17:48 on 09-02, so ac/furnace day_1
# carried 09-01 values with a 09-02 last_changed, and this check reported
# "ac OK -2.19%" [M, n=1 capture, 2026-09-02] against 09-02 raw when the
# honest answer was HELD. Only the
# band's slack kept that from being a false DRIFT. So require the timestamp to
# sit in the capture window itself.
CAPTURE_HHMM = (23, 59)
CAPTURE_SLOP_S = 300          # 23:59:00 +/- 5 min, generous for a slow trigger


def captured_on(lc, day):
    """True only if `lc` is plausibly THIS day's 23:59 capture."""
    if lc is None:
        return False
    local = lc.astimezone()
    target = dt.datetime.combine(day, dt.time(*CAPTURE_HHMM)).astimezone()
    return abs((local - target).total_seconds()) <= CAPTURE_SLOP_S


def local_day_bounds(day):
    """UTC ISO bounds for a LOCAL calendar day, using the host's own offset so
    the query matches what the 23:59 capture actually summarised."""
    start = dt.datetime.combine(day, dt.time(0, 0)).astimezone()
    end = start + dt.timedelta(days=1)
    fmt = '%Y-%m-%dT%H:%M:%SZ'
    return (start.astimezone(dt.timezone.utc).strftime(fmt),
            end.astimezone(dt.timezone.utc).strftime(fmt))


def capture_from_influx(app, day):
    """The 23:59 write for `day`, read back from the day_1 series in InfluxDB.

    restore_state holds ONLY the most recent capture, so historical days must
    come from somewhere else or --days would silently compare an old raw mean
    against today's capture and invent divergence.
    """
    start = dt.datetime.combine(day, dt.time(23, 58)).astimezone()
    end = start + dt.timedelta(minutes=7)
    fmt = '%Y-%m-%dT%H:%M:%SZ'
    q = ('SELECT LAST("value") FROM "W" WHERE "entity_id" = \'%s_running_watts_day_1\' '
         'AND time >= \'%s\' AND time < \'%s\''
         % (app, start.astimezone(dt.timezone.utc).strftime(fmt),
            end.astimezone(dt.timezone.utc).strftime(fmt)))
    rows = first_series(influx(q))
    return rows[0][1] if rows and rows[0][1] is not None else None


def raw_mean(entity, threshold, day):
    lo, hi = local_day_bounds(day)
    q = ('SELECT MEAN("value") FROM "W" WHERE "entity_id" = \'%s\' '
         'AND "value" > %s AND time >= \'%s\' AND time < \'%s\''
         % (entity, threshold, lo, hi))
    rows = first_series(influx(q))
    return rows[0][1] if rows and rows[0][1] is not None else None


def verify_day(states, day, want_day=True):
    results = []
    for app, (raw_ent, th_ent, th_default) in APPLIANCES.items():
        th_val, _ = states.get('input_number.' + th_ent, (None, None))
        threshold = th_val if th_val is not None else th_default
        cap, lc = states.get('input_number.%s_running_watts_day_1' % app, (None, None))
        cap_day = lc.astimezone().date() if lc else None

        row = {'appliance': app, 'day': day.isoformat(), 'threshold': threshold,
               'capture': cap, 'capture_day': cap_day.isoformat() if cap_day else None,
               'raw': None, 'diff_w': None, 'diff_pct': None,
               'band': BANDS.get(app), 'status': None}

        if not want_day:
            # Historical day: restore_state only carries the latest capture, so
            # read that day's own 23:59 write back out of InfluxDB instead.
            try:
                cap = capture_from_influx(app, day)
            except (urllib.error.URLError, OSError, ValueError):
                cap = None
            row['capture'] = cap
            row['capture_day'] = day.isoformat() if cap is not None else None

        if cap is None:
            # In historical mode this is USUALLY benign: InfluxDB writes on
            # state change, so a capture identical to the previous day's writes
            # no point at all. It is not evidence the capture did not happen.
            # The nightly mode never hits this - it reads restore_state.
            row['status'] = 'NO-POINT' if not want_day else 'NO-CAPTURE'
            results.append(row)
            continue
        if want_day and not captured_on(lc, day):
            # The guards declined to overwrite this slot, or something else
            # wrote it. Either way it is not this day's capture: holding an
            # older value is not a discrepancy, and comparing it invents one.
            row['status'] = 'HELD'
            results.append(row)
            continue
        try:
            raw = raw_mean(raw_ent, threshold, day)
        except (urllib.error.URLError, OSError, ValueError) as e:
            row['status'] = 'RAW-ERROR'
            row['error'] = str(e)[:120]
            results.append(row)
            continue
        row['raw'] = raw
        if raw is None:
            row['status'] = 'NO-RUN'
            results.append(row)
            continue
        row['diff_w'] = cap - raw
        row['diff_pct'] = (cap - raw) / raw * 100 if raw else None
        row['status'] = ('DRIFT' if abs(row['diff_pct']) > BANDS.get(app, 10.0)
                         else 'OK')
        results.append(row)
    return results


def append_log(lines):
    os.makedirs(LOG_DIR, exist_ok=True)
    with io.open(LOG_TXT, 'a', encoding='utf-8') as f:
        for ln in lines:
            f.write(ln + '\n')


def append_csv(rows):
    os.makedirs(LOG_DIR, exist_ok=True)
    new = not os.path.exists(LOG_CSV)
    cols = ['run_ts', 'day', 'appliance', 'threshold', 'capture', 'raw',
            'diff_w', 'diff_pct', 'band', 'status']
    with io.open(LOG_CSV, 'a', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        if new:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=1,
                    help='verify the last N days (default 1 = last night)')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--no-write', action='store_true',
                    help='do not append to the log/CSV')
    args = ap.parse_args()

    states = restore_state()
    today = dt.datetime.now().astimezone().date()
    run_ts = dt.datetime.now().astimezone().replace(microsecond=0).isoformat()

    all_rows = []
    for back in range(1, args.days + 1):
        day = today - dt.timedelta(days=back)
        # Only the most recent capture is in restore_state, so the day-match
        # guard applies to it alone; historical days are compared informationally.
        all_rows += verify_day(states, day, want_day=(back == 1))

    for r in all_rows:
        r['run_ts'] = run_ts

    if args.json:
        print(json.dumps(all_rows, indent=1, default=str))
    else:
        for r in all_rows:
            if r['diff_pct'] is None:
                print('%s  %-13s %-11s capture=%-9s raw=%-9s'
                      % (r['day'], r['appliance'], r['status'],
                         r['capture'], r['raw']))
            else:
                print('%s  %-13s %-11s capture=%-9.1f raw=%-9.1f '
                      'diff=%+7.1f W (%+6.2f%%, band +/-%.0f%%)'
                      % (r['day'], r['appliance'], r['status'], r['capture'],
                         r['raw'], r['diff_w'], r['diff_pct'], r['band']))

    drift = [r for r in all_rows if r['status'] == 'DRIFT']
    if not args.no_write:
        lines = ['%s  %s' % (run_ts, '-' * 60)]
        for r in all_rows:
            lines.append(
                '  %s %-13s %-11s cap=%s raw=%s diff=%s'
                % (r['day'], r['appliance'], r['status'], r['capture'],
                   None if r['raw'] is None else round(r['raw'], 1),
                   None if r['diff_pct'] is None else '%+.2f%%' % r['diff_pct']))
        if drift:
            for r in drift:
                lines.append('  WARN SPC-DRIFT  %s  capture %.1f vs raw %.1f '
                             '(%+.2f%%, band +/-%.0f%%)'
                             % (r['appliance'], r['capture'], r['raw'],
                                r['diff_pct'], r['band']))
        append_log(lines)
        append_csv(all_rows)

    return 1 if drift else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as exc:                     # noqa: BLE001
        # Exit 2, never 1: see EXIT CODE in the module docstring.
        msg = '%s: %s' % (type(exc).__name__, exc)
        print('SPC-VERIFY ERROR  ' + msg, file=sys.stderr)
        try:
            append_log(['%s  SPC-VERIFY ERROR  %s'
                        % (dt.datetime.now().astimezone().replace(
                            microsecond=0).isoformat(), msg)])
        except OSError:
            pass
        sys.exit(2)
