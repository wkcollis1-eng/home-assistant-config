#!/usr/bin/env python3
"""
spc_buffer_export.py — nightly backup of every rolling-buffer slot.

WHY THIS EXISTS
---------------
The 7-day SPC buffers, the HDD/CDD buffers and the monthly accumulators are
the accumulated measurement history of this house. Every one of them lives in
exactly one place: .storage/core.restore_state. That file is gitignored (it
holds auth tokens), is on the "never edit" list, and has no backup. Lose it and
you lose every buffer at once, with nothing to rebuild from — the recorder only
keeps 14 days and purges, and the InfluxDB continuous queries compute a
different statistic than the capture guards do.

This is the "no help coming" hole in the data layer, so the backup is
deliberately built to work when things are already broken:

  * It reads .storage/core.restore_state directly. No HA API, no long-lived
    token, no network. It works while HA is DOWN, which is exactly when you
    need it.
  * It is append-only (CLAUDE.md: NEVER overwrite/truncate CSV files). Every
    run appends rows; nothing is ever rewritten in place.
  * Long format (one row per entity per run) rather than one column per slot,
    so adding a pipeline never changes the schema and never invalidates old
    rows.
  * It records each value's own last_changed, so a restored value carries its
    provenance and you can tell a real capture from a restore artefact.

TIMING
------
restore_state is flushed by HA every 15 minutes and on clean shutdown, so a
value written by the 23:59 captures is on disk by 00:14 at the latest. The
automation runs at 00:20 for that reason — late enough to be certain, early
enough to be the same "logical day" as the captures it is preserving. If a row
shows a last_changed older than its pipeline's capture stamp, the flush had not
landed; --check reports that rather than silently backing up a stale value.

USAGE
-----
  python3 spc_buffer_export.py                 # append a snapshot
  python3 spc_buffer_export.py --check         # health report, no write
  python3 spc_buffer_export.py --restore LATEST  # print the replay plan
  python3 spc_buffer_export.py --restore 2026-08-21T00:20:01

  HA_CONFIG=/config   (default; set to H:\\ or similar to run off-host)
"""

import argparse
import csv
import io
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

CONFIG = os.environ.get("HA_CONFIG", "/config")
MANIFEST = os.path.join(CONFIG, "pipelines.yaml")
RESTORE_STATE = os.path.join(CONFIG, ".storage", "core.restore_state")
OUT_DIR = os.path.join(CONFIG, "www", "spc")
MASTER = os.path.join(OUT_DIR, "buffer_backup_master.csv")
HEADER = ["exported_at", "pipeline", "kind", "entity", "value", "last_changed"]


def load_manifest():
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML required")
    with io.open(MANIFEST, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_states():
    """entity_id -> (state, last_changed). Read-only; .storage is never written."""
    with io.open(RESTORE_STATE, encoding="utf-8") as fh:
        blob = json.load(fh)
    out = {}
    for item in blob.get("data", []):
        st = item.get("state") or {}
        eid = st.get("entity_id")
        if eid:
            out[eid] = (str(st.get("state")), st.get("last_changed") or "")
    return out


def collect(manifest, states):
    """Every entity worth preserving: buffer slots, capture stamps, seed stamps."""
    rows, missing = [], []
    for name, p in sorted((manifest.get("pipelines") or {}).items()):
        wanted = list(p.get("buffer") or [])
        for key in ("stamp", "seed_stamp"):
            if p.get(key):
                wanted.append(p[key])
        for eid in wanted:
            if eid in states:
                value, changed = states[eid]
                rows.append([name, p.get("kind", "?"), eid, value, changed])
            else:
                missing.append((name, eid))
    return rows, missing


def append_snapshot(rows):
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")
    fresh = not os.path.exists(MASTER) or os.path.getsize(MASTER) == 0
    # 'a' only — the file is never opened for writing or truncation.
    with io.open(MASTER, "a", encoding="utf-8", newline="") as fh:
        wr = csv.writer(fh)
        if fresh:
            wr.writerow(HEADER)
        for r in rows:
            wr.writerow([stamp] + r)
    return stamp, len(rows)


def check(manifest, states, rows):
    """Report the failure modes this system has actually had.

    Returns (severity, kind, pipeline, message). Severity WARN counts as a
    failure; INFO is reported but does not. An empty buffer on a seasonal
    pipeline is INFO on purpose: HDD slots are legitimately zero every summer
    and CDD slots every winter, and a checker that cries for six months is a
    checker you stop reading — the same mistake the SPC stale detectors were
    built to avoid.
    """
    problems = []
    for name, p in sorted((manifest.get("pipelines") or {}).items()):
        buf = p.get("buffer") or []
        if not buf:
            continue
        vals = []
        for eid in buf:
            try:
                vals.append(float(states.get(eid, ("nan", ""))[0]))
            except ValueError:
                vals.append(float("nan"))
        live = [v for v in vals if v == v and v > 0]
        season = p.get("season", "none")
        if not live:
            sev = "INFO" if season != "none" else "WARN"
            problems.append((sev, "EMPTY", name, "all %d slots are 0 or unset%s"
                             % (len(buf), " (%s season)" % season if season != "none" else "")))
        elif len(live) >= 2 and len(set(live)) == 1:
            # This is the 2026-08-21 dehumidifier signature: the startup seeder
            # wrote one constant into three slots and stamped it as a capture.
            problems.append(("WARN", "REPEATED", name,
                             "%d live slots all equal %g - a repeated value, not a sample"
                             % (len(live), live[0])))
        stamp = p.get("stamp")
        if stamp and stamp in states:
            cap = states[stamp][0][:10]
            for eid in buf:
                lc = states.get(eid, ("", ""))[1][:10]
                if lc and cap and lc < cap:
                    problems.append(("WARN", "STALE-FLUSH", name,
                                     "%s last_changed %s predates capture stamp %s"
                                     % (eid, lc, cap)))
                    break
    return problems


def restore_plan(which):
    if not os.path.exists(MASTER):
        sys.exit("no backup at %s" % MASTER)
    with io.open(MASTER, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit("backup is empty")
    stamps = sorted({r["exported_at"] for r in rows})
    target = stamps[-1] if which.upper() == "LATEST" else which
    if target not in stamps:
        sys.exit("no snapshot %r. available: %s ... %s (%d total)"
                 % (target, stamps[0], stamps[-1], len(stamps)))
    # Dedupe by entity, last write wins. Two runs inside the same second share
    # an exported_at, and a replay plan that sets the same entity twice is at
    # best noise and at worst hides a conflict. Found by running the exporter
    # twice back to back, which is exactly why it was run twice.
    sel = list({r["entity"]: r for r in rows if r["exported_at"] == target}.values())
    by_domain = defaultdict(list)
    for r in sel:
        by_domain[r["entity"].split(".")[0]].append(r)
    print("# Replay plan for snapshot %s (%d entities)" % (target, len(sel)))
    print("# Paste into Developer Tools > Actions (YAML mode), one block at a time.")
    print("# Review before running: this OVERWRITES current buffer state.")
    for dom, items in sorted(by_domain.items()):
        svc = {"input_number": "input_number.set_value",
               "input_datetime": "input_datetime.set_datetime"}.get(dom)
        if not svc:
            continue
        for r in sorted(items, key=lambda x: x["entity"]):
            key = "value" if dom == "input_number" else "date"
            val = r["value"][:10] if dom == "input_datetime" else r["value"]
            print("\n- action: %s\n  target:\n    entity_id: %s\n  data:\n    %s: %s"
                  % (svc, r["entity"], key, val))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="health report, write nothing")
    ap.add_argument("--restore", metavar="SNAPSHOT", help="'LATEST' or an exported_at value")
    args = ap.parse_args()

    if args.restore:
        return restore_plan(args.restore)

    manifest = load_manifest()
    states = load_states()
    rows, missing = collect(manifest, states)
    problems = check(manifest, states, rows)

    if args.check:
        # A brand-new *_spc_last_seed helper simply has not been persisted yet.
        hard = [(n, e) for n, e in missing if not e.endswith("_spc_last_seed")]
        soft = [(n, e) for n, e in missing if e.endswith("_spc_last_seed")]
        warn = [p for p in problems if p[0] == "WARN"]
        print("buffer entities tracked   : %d" % len(rows))
        print("missing from restore_state: %d hard, %d not-yet-persisted"
              % (len(hard), len(soft)))
        for name, eid in hard:
            print("   WARN MISSING  %-30s %s" % (name, eid))
        for name, eid in soft:
            print("   INFO new      %-30s %s" % (name, eid))
        print("findings: %d WARN, %d INFO" % (len(warn), len(problems) - len(warn)))
        for sev, kind, name, msg in problems:
            print("   %-4s %-12s %-32s %s" % (sev, kind, name, msg))
        return 1 if (hard or warn) else 0

    stamp, n = append_snapshot(rows)
    print("%s  appended %d rows to %s" % (stamp, n, MASTER))
    for sev, kind, name, msg in problems:
        if sev == "WARN":
            print("  WARN %-12s %-32s %s" % (kind, name, msg))
    for name, eid in missing:
        if not eid.endswith("_spc_last_seed"):
            print("  WARN MISSING      %-28s %s" % (name, eid))
    return 0


if __name__ == "__main__":
    sys.exit(main())
