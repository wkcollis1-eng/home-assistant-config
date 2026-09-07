#!/usr/bin/env python3
"""
grafana_snapshot.py — local (internal) Grafana dashboard snapshots.

WHY LOCAL AND NOT EXTERNAL
--------------------------
The 2026-07-22 attempt at this failed and was abandoned; www/snapshot_update.log
records the exact reason:

    ERROR - Failed to create snapshot: 500 Server Error for url:
            http://a0d7b954-grafana:3000/api/snapshots
    ERROR - Response: {"message":"Failed to create external snapshot"}

It asked for an EXTERNAL snapshot, which publishes to a hosted service Grafana
Labs has retired. That can never succeed. A LOCAL snapshot (`external: false`)
is stored inside this Grafana and works offline, which is also the only kind
that belongs on a house that is "designed for no help coming".

WHAT A SNAPSHOT IS, AND IS NOT
------------------------------
A snapshot freezes the DISPLAYED data into a standalone dashboard copy. It is an
archive, not a check: if a panel is wrong, the snapshot preserves the wrong
number faithfully. Verification of the SPC numbers is scripts/spc_verify.py,
which compares two independent computations. Do not mistake one for the other.

CREDENTIALS
-----------
Needs a Grafana service-account token with at least Editor on the dashboards
being snapshotted. Same env-then-secrets.yaml pattern as everything else:
GRAFANA_TOKEN, else `grafana_token` in secrets.yaml. secrets.yaml is gitignored;
never put this in a tracked file.

USAGE
-----
    python3 /config/scripts/grafana_snapshot.py --probe      # facts first
    python3 /config/scripts/grafana_snapshot.py --list
    python3 /config/scripts/grafana_snapshot.py --uid <uid> [--uid <uid> ...]

EXIT CODES
----------
0 ok, 1 one or more snapshots failed, 2 could not run (no token, unreachable).
Distinct for the same reason as spc_verify.py: an alert that blames the wrong
thing is worse than none.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

import yaml

CFG = os.environ.get('HA_CONFIG', '/config')
LOG = os.path.join(CFG, 'www', 'grafana_snapshot.log')
DEFAULT_URL = 'http://a0d7b954-grafana:3000'


def secrets():
    try:
        return yaml.safe_load(io.open(os.path.join(CFG, 'secrets.yaml'),
                                      encoding='utf-8')) or {}
    except OSError:
        return {}


_S = secrets()
BASE = (os.environ.get('GRAFANA_URL') or _S.get('grafana_url') or DEFAULT_URL).rstrip('/')
TOKEN = os.environ.get('GRAFANA_TOKEN') or _S.get('grafana_token') or ''


def log(msg):
    line = msg if isinstance(msg, str) else json.dumps(msg)
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with io.open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except OSError:
        pass


def call(path, payload=None, method=None, timeout=120, auth=True):
    """Returns (status, parsed_body_or_text). Never raises for HTTP errors."""
    url = BASE + path
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    if auth and TOKEN:
        headers['Authorization'] = 'Bearer ' + TOKEN
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method or ('POST' if data else 'GET'))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode('utf-8', 'replace')
            try:
                return r.status, json.loads(raw)
            except ValueError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw
    except (urllib.error.URLError, OSError) as e:
        return 0, str(e)


def probe():
    """Establish the facts before trusting any of the rest of this script."""
    log('probe: base=%s  token=%s' % (BASE, 'present' if TOKEN else 'ABSENT'))
    st, body = call('/api/health', auth=False)
    log('  /api/health          -> %s %s' % (st, body))
    if st == 0:
        log('  UNREACHABLE. From the HA container Grafana is a docker hostname;'
            ' this only resolves on the host.')
        return 2
    st_s, settings = call('/api/frontend/settings', auth=False)
    if isinstance(settings, dict):
        snap = settings.get('snapshotEnabled', '<absent>')
        ext = (settings.get('externalSnapshotUrl', ''), settings.get('externalEnabled', '<absent>'))
        log('  snapshotEnabled      -> %s' % snap)
        log('  externalEnabled      -> %s  url=%r' % (ext[1], ext[0]))
    else:
        log('  /api/frontend/settings -> %s %s' % (st_s, str(settings)[:200]))
    if not TOKEN:
        log('  NO TOKEN: cannot enumerate dashboards or create snapshots.')
        log('  Create one: Grafana > Administration > Users and access >'
            ' Service accounts > Add service account > Editor > Add token,')
        log('  then put it in secrets.yaml as:  grafana_token: <token>')
        return 2
    st_d, dash = call('/api/search?type=dash-db&limit=100')
    if st_d == 200 and isinstance(dash, list):
        log('  auth OK, %d dashboards visible' % len(dash))
        for d in dash[:25]:
            log('     %-24s %s' % (d.get('uid'), d.get('title')))
        return 0
    log('  /api/search -> %s %s' % (st_d, str(dash)[:200]))
    return 2


def diag():
    """What does GRAFANA actually get? The data layer being healthy in InfluxDB
    does not prove the panels receive it: datasource resolution, credentials and
    the database name all sit between them."""
    st, ds = call('/api/datasources')
    if st != 200 or not isinstance(ds, list):
        log('datasources -> %s %s' % (st, str(ds)[:200]))
        return 2
    log('datasources (%d):' % len(ds))
    for d in ds:
        log('   uid=%-18s default=%-5s type=%-10s name=%s'
            % (d.get('uid'), d.get('isDefault'), d.get('type'), d.get('name')))
        log('        url=%s  database=%r' % (d.get('url'), d.get('database')))
    influx = [d for d in ds if d.get('type') == 'influxdb']
    QUERIES = [
        ('fridge  day_1', 'W', 'fridge_running_watts_day_1'),
        ('cooling day_1', 'kWh/CDD', 'cooling_kwh_cdd_day_1'),
        ('ac      day_1', 'W', 'ac_running_watts_day_1'),
        ('furnace day_1', 'W', 'furnace_running_watts_day_1'),
    ]
    import time as _t
    now_ms = int(_t.time() * 1000)
    for d in influx:
        log('')
        log('--- querying through datasource %s (%s) ---' % (d.get('uid'), d.get('name')))
        for label, meas, ent in QUERIES:
            SQ = chr(39)
            q = ('SELECT "value" FROM "%s" WHERE "entity_id" = '
                 + SQ + '%s' + SQ + ' AND $timeFilter') % (meas, ent)
            payload = {'from': str(now_ms - 30 * 86400000), 'to': str(now_ms),
                       'queries': [{'refId': 'A', 'datasource': {'type': 'influxdb',
                                                                 'uid': d.get('uid')},
                                    'query': q, 'rawQuery': True,
                                    'resultFormat': 'time_series',
                                    'intervalMs': 3600000, 'maxDataPoints': 2000}]}
            stq, body = call('/api/ds/query', payload)
            newest, n = None, 0
            try:
                for fr in body['results']['A']['frames']:
                    vals = fr['data']['values']
                    if vals and vals[0]:
                        n += len(vals[0])
                        newest = max(newest or 0, max(vals[0]))
            except Exception:
                pass
            if newest:
                import datetime as _dt
                ts = _dt.datetime.fromtimestamp(newest / 1000).strftime('%m-%d %H:%M')
                log('   %-14s HTTP %s  points=%-5d newest=%s' % (label, stq, n, ts))
            else:
                log('   %-14s HTTP %s  NO DATA  %s' % (label, stq, str(body)[:160]))
    return 0


def dumpdash(uid):
    """The provisioned FILE is not proof of what Grafana serves. Print the live
    model's queries so a stale served copy cannot hide behind a correct file."""
    st, body = call('/api/dashboards/uid/' + urllib.parse.quote(uid))
    if st != 200 or not isinstance(body, dict):
        log('fetch -> %s %s' % (st, str(body)[:200]))
        return 2
    dash = body.get('dashboard') or {}
    meta = body.get('meta') or {}
    log('uid=%s  title=%r  version=%s' % (uid, dash.get('title'), dash.get('version')))
    log('provisioned=%s  path=%s  updated=%s'
        % (meta.get('provisioned'), meta.get('provisionedExternalId'), meta.get('updated')))
    log('time=%s' % json.dumps(dash.get('time')))
    for p in panel_iter(dash):
        tgts = p.get('targets') or []
        if not tgts:
            continue
        log('')
        log('PANEL %r  ds=%s' % (str(p.get('title'))[:48], json.dumps(p.get('datasource'))))
        for t in tgts:
            log('   %s %-6s %s' % (t.get('refId'), t.get('alias') or '',
                                   (t.get('query') or '')[:150]))
    return 0


def _influx_uid():
    st, ds = call('/api/datasources')
    if st != 200 or not isinstance(ds, list):
        return None
    inf = [d for d in ds if d.get('type') == 'influxdb']
    if not inf:
        return None
    for d in inf:
        if d.get('isDefault'):
            return d.get('uid')
    return inf[0].get('uid')


def _pin_datasource(obj, uid):
    """Replace every ${DS_...} datasource placeholder with a concrete uid.

    A placeholder resolves only while exactly one datasource of that type exists
    and is default. That is a coincidence, not a design, and it breaks silently
    the day a second one appears."""
    n = 0
    if isinstance(obj, dict):
        u = obj.get('uid')
        if isinstance(u, str) and u.startswith('${') and u.endswith('}'):
            obj['uid'] = uid
            n += 1
        for v in obj.values():
            n += _pin_datasource(v, uid)
    elif isinstance(obj, list):
        for v in obj:
            n += _pin_datasource(v, uid)
    return n


def deploy(path):
    """Push a repo dashboard file into Grafana, overwriting by uid.

    This exists because editing grafana/dashboards/*.json does NOTHING on its
    own. Measured 2026-09-03: the P12 re-sourcing was written to
    spc_appliances.json on 08-22 and Grafana served its own 07-28 copy for
    thirteen days, still querying the retired `spc` measurement, with nothing
    anywhere reporting the mismatch."""
    try:
        model = json.load(io.open(path, encoding='utf-8'))
    except (OSError, ValueError) as e:
        log('cannot read %s: %s' % (path, e))
        return 2
    uid = model.get('uid')
    if not uid:
        log('%s has no uid - refusing to deploy a dashboard that cannot be '
            'matched to an existing one' % path)
        return 2
    ds = _influx_uid()
    if not ds:
        log('no influxdb datasource found; cannot pin placeholders')
        return 2
    pinned = _pin_datasource(model, ds)
    model.pop('id', None)
    model.pop('version', None)
    log('deploying %s  uid=%s  datasource placeholders pinned to %s: %d'
        % (path, uid, ds, pinned))
    st, before = call('/api/dashboards/uid/' + urllib.parse.quote(uid))
    if st == 200 and isinstance(before, dict):
        b = before.get('dashboard') or {}
        log('   replacing served version %s (updated %s)'
            % (b.get('version'), (before.get('meta') or {}).get('updated')))
    st, body = call('/api/dashboards/db',
                    {'dashboard': model, 'overwrite': True,
                     'message': 'deployed from repo by grafana_snapshot.py --deploy'})
    if st in (200, 201) and isinstance(body, dict) and body.get('status') == 'success':
        log('   OK -> version %s  url=%s' % (body.get('version'), body.get('url')))
        return 0
    log('   FAILED %s %s' % (st, str(body)[:300]))
    return 1


def provstatus():
    """Is file-based provisioning actually loading anything?"""
    st, body = call('/api/admin/provisioning/dashboards/reload', {})
    log('provisioning reload -> %s %s' % (st, str(body)[:160]))
    if st == 403:
        log('   (token lacks admin; reload skipped, status below still valid)')
    st, dash = call('/api/search?type=dash-db&limit=100')
    if st != 200 or not isinstance(dash, list):
        log('search -> %s %s' % (st, str(dash)[:160]))
        return 2
    log('%-18s %-12s %-22s %s' % ('uid', 'provisioned', 'updated', 'title'))
    for d in dash:
        u = d.get('uid')
        stx, body = call('/api/dashboards/uid/' + urllib.parse.quote(u))
        meta = (body or {}).get('meta') or {} if isinstance(body, dict) else {}
        log('%-18s %-12s %-22s %s'
            % (u, meta.get('provisioned'), str(meta.get('updated'))[:19], d.get('title')))
    return 0


def _targets(dash):
    """{panel title: [query text, ...]} for comparison."""
    out = {}
    for p in panel_iter(dash):
        tg = p.get('targets') or []
        if not tg:
            continue
        title = str(p.get('title') or '(untitled)')
        out.setdefault(title, [])
        for t in tg:
            out[title].append((t.get('refId'), (t.get('query') or '').strip()))
    return out


def _placeholders(obj):
    n = 0
    if isinstance(obj, dict):
        u = obj.get('uid')
        if isinstance(u, str) and u.startswith('${'):
            n += 1
        for v in obj.values():
            n += _placeholders(v)
    elif isinstance(obj, list):
        for v in obj:
            n += _placeholders(v)
    return n


def diffall(dirpath):
    """Compare repo files against served dashboards.

    The point is DIRECTION. These drift both ways: a file can be a month ahead
    of Grafana, or a month behind it, and deploying the wrong direction destroys
    work. Nothing before 2026-09-03 ever compared the two."""
    import datetime as _dt
    try:
        files = sorted(f for f in os.listdir(dirpath) if f.endswith('.json'))
    except OSError as e:
        log('cannot list %s: %s' % (dirpath, e))
        return 2
    log('comparing %d file(s) in %s against Grafana' % (len(files), dirpath))
    for f in files:
        fp = os.path.join(dirpath, f)
        try:
            model = json.load(io.open(fp, encoding='utf-8'))
        except (OSError, ValueError) as e:
            log('%s: unreadable (%s)' % (f, e))
            continue
        uid = model.get('uid')
        fmt = _dt.datetime.fromtimestamp(os.path.getmtime(fp)).strftime('%Y-%m-%d %H:%M')
        log('')
        log('=' * 72)
        log('%s   uid=%s   file mtime %s' % (f, uid, fmt))
        st, body = call('/api/dashboards/uid/' + urllib.parse.quote(str(uid)))
        if st != 200 or not isinstance(body, dict):
            log('   NOT SERVED by Grafana (%s) - deploying would CREATE it' % st)
            continue
        served = body.get('dashboard') or {}
        meta = body.get('meta') or {}
        upd = str(meta.get('updated'))[:16].replace('T', ' ')
        log('   served version %s, updated %s, provisioned=%s'
            % (served.get('version'), upd, meta.get('provisioned')))
        newer = 'FILE is newer' if fmt > upd else ('GRAFANA is newer' if upd > fmt else 'same')
        log('   direction: %s' % newer)
        log('   placeholders in file: %d' % _placeholders(model))
        a, b = _targets(served), _targets(model)
        only_served = sorted(set(a) - set(b))
        only_file = sorted(set(b) - set(a))
        log('   panels with queries: served %d, file %d' % (len(a), len(b)))
        if only_served:
            log('   panels ONLY in Grafana (deploy would REMOVE): %s'
                % ', '.join(x[:34] for x in only_served[:6]))
        if only_file:
            log('   panels ONLY in file (deploy would ADD): %s'
                % ', '.join(x[:34] for x in only_file[:6]))
        changed = []
        for t in sorted(set(a) & set(b)):
            if a[t] != b[t]:
                changed.append(t)
        log('   shared panels with DIFFERENT queries: %d' % len(changed))
        for t in changed[:4]:
            log('      panel %r' % t[:44])
            qa = dict(a[t])
            qb = dict(b[t])
            for ref in sorted(set(qa) | set(qb)):
                if qa.get(ref) != qb.get(ref):
                    log('         %s served: %s' % (ref, (qa.get(ref) or '(none)')[:88]))
                    log('         %s file  : %s' % (ref, (qb.get(ref) or '(none)')[:88]))
    return 0


def panel_iter(dashboard):
    for p in dashboard.get('panels', []) or []:
        if p.get('type') == 'row':
            for sub in p.get('panels', []) or []:
                yield sub
        else:
            yield p


def snapshot(uid, expires=0, timeout_s=180):
    st, body = call('/api/dashboards/uid/' + urllib.parse.quote(uid))
    if st != 200 or not isinstance(body, dict):
        log('  %s: fetch failed -> %s %s' % (uid, st, str(body)[:200]))
        return False
    dash = body.get('dashboard') or {}
    title = dash.get('title', uid)

    # Grafana's own "Local Snapshot" assembles snapshotData client-side. Server
    # side we hand it the dashboard model; panels without snapshotData render
    # from the datasource, which for a LOCAL snapshot on the same Grafana is
    # exactly what we want -- the archive stays queryable and honest rather than
    # carrying a hand-rebuilt copy of the data that could differ from source.
    # Send the dashboard model with its uid INTACT. Grafana authorises snapshot
    # creation by checking read permission against the dashboard the payload
    # names; blanking uid/id leaves nothing to authorise and the request is
    # rejected 403 with a bare "forbidden" that reads like a role problem and is
    # not one. (Measured 2026-09-03: 5/5 dashboards 403 with uid stripped, while
    # the same token held snapshots:create and snapshotEnabled was true.)
    # Grafana's own "Local Snapshot" button sends the model unmodified too.
    payload = {
        'dashboard': dict(dash, title='%s (snapshot)' % title),
        'name': '%s — auto %s' % (title, os.environ.get('SNAP_STAMP', '')),
        'external': False,
    }
    if expires:
        payload['expires'] = int(expires)
    st, body = call('/api/snapshots', payload, timeout=timeout_s)
    if st in (200, 201) and isinstance(body, dict) and body.get('url'):
        log('  %-24s OK  %s' % (uid, body.get('url')))
        return True
    log('  %-24s FAILED %s %s' % (uid, st, str(body)[:250]))
    if st == 403:
        diagnose_403()
    return False


_DIAGNOSED = [False]


def diagnose_403():
    """A bare 'forbidden' sends you to the wrong place. Say WHICH of the two
    causes it is: the token's role, or snapshots disabled server-side."""
    if _DIAGNOSED[0]:
        return
    _DIAGNOSED[0] = True
    log('  --- 403 diagnosis ---')
    st, perms = call('/api/access-control/user/permissions')
    if st == 200 and isinstance(perms, dict):
        snap = sorted(k for k in perms if 'snapshot' in k.lower())
        log('    snapshot permissions held: %s' % (snap or 'NONE'))
        log('    dashboards:create held   : %s' % ('dashboards:create' in perms))
        if not snap:
            log('    => the service account role cannot create snapshots.')
            log('       Grafana > Administration > Users and access > Service')
            log('       accounts > (this account) > set role to Editor or Admin.')
    else:
        log('    /api/access-control/user/permissions -> %s %s' % (st, str(perms)[:160]))
    st, s = call('/api/frontend/settings')
    if isinstance(s, dict):
        log('    snapshotEnabled (server) : %s' % s.get('snapshotEnabled', '<absent>'))
        if s.get('snapshotEnabled') is False:
            log('    => snapshots are DISABLED in grafana.ini. No token can fix')
            log('       that; it needs [snapshots] enabled = true on the add-on.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe', action='store_true')
    ap.add_argument('--diffall', metavar='DIR',
                    help='compare every dashboard file in DIR against what '
                         'Grafana actually serves, and report the drift')
    ap.add_argument('--deploy', metavar='PATH',
                    help='push a repo dashboard JSON into Grafana '
                         '(overwrite by uid, datasource pinned)')
    ap.add_argument('--provstatus', action='store_true',
                    help='reload provisioning and report which dashboards '
                         'Grafana considers provisioned')
    ap.add_argument('--dumpdash', metavar='UID',
                    help='print the LIVE dashboard targets Grafana serves')
    ap.add_argument('--diag', action='store_true',
                    help='list datasources and run the SPC panel queries through Grafana, reporting the newest timestamp each returns')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--inspect', metavar='KEY',
                    help='report whether a stored snapshot froze its DATA '
                         '(panels carrying snapshotData) or only its LAYOUT')
    ap.add_argument('--uid', action='append', default=[])
    ap.add_argument('--expires', type=int, default=0,
                    help='seconds until Grafana deletes it; 0 = never')
    args = ap.parse_args()

    if args.diffall:
        return diffall(args.diffall)
    if args.deploy:
        return deploy(args.deploy)
    if args.provstatus:
        return provstatus()
    if args.dumpdash:
        return dumpdash(args.dumpdash)
    if args.diag:
        return diag()
    if args.probe:
        return probe()
    if args.inspect:
        st, body = call('/api/snapshots/' + urllib.parse.quote(args.inspect))
        if st != 200 or not isinstance(body, dict):
            log('inspect -> %s %s' % (st, str(body)[:200]))
            return 2
        dash = (body.get('dashboard') or {})
        panels = list(panel_iter(dash))
        frozen = [p for p in panels if p.get('snapshotData')]
        log('snapshot %s' % args.inspect)
        log('  title           : %s' % dash.get('title'))
        log('  panels          : %d' % len(panels))
        log('  with snapshotData: %d' % len(frozen))
        log('  => %s' % ('DATA FROZEN - a true archive' if frozen else
                         'LAYOUT ONLY - panels re-query the live datasource, so '
                         'this preserves dashboard STRUCTURE at a point in time, '
                         'NOT the numbers that were on screen'))
        return 0
    if not TOKEN:
        log('no Grafana token (env GRAFANA_TOKEN or secrets.yaml grafana_token)')
        return 2
    if args.list:
        st, dash = call('/api/search?type=dash-db&limit=100')
        if st != 200:
            log('search failed %s %s' % (st, str(dash)[:200]))
            return 2
        for d in dash:
            log('%-24s %s' % (d.get('uid'), d.get('title')))
        return 0

    uids = args.uid
    if not uids:
        st, dash = call('/api/search?type=dash-db&limit=100')
        if st != 200:
            log('search failed %s %s' % (st, str(dash)[:200]))
            return 2
        uids = [d['uid'] for d in dash if d.get('uid')]
    log('snapshotting %d dashboard(s)' % len(uids))
    # NOT all(...): that short-circuits on the first False and silently skips
    # every remaining dashboard, so one bad dashboard would hide the state of
    # all the others. Attempt every one, then aggregate.
    results = [snapshot(u, args.expires) for u in list(uids)]
    good = sum(1 for r in results if r)
    log('done: %d/%d succeeded' % (good, len(results)))
    return 0 if good == len(results) else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as exc:                       # noqa: BLE001
        log('GRAFANA-SNAPSHOT ERROR  %s: %s' % (type(exc).__name__, exc))
        sys.exit(2)
