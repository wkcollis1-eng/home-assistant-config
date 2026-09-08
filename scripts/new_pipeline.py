#!/usr/bin/env python3
"""Scaffold a complete capture pipeline: all four pieces, from one declaration.

WHY THIS EXISTS - measured, not guessed. Across 38 nightly runs in
www/spc/ha_audit.log the two most-fired rules were:

    130  stamp-not-snapshotted      forgot the variables: snapshot
    111  unguarded-shell-command    forgot the maintenance-mode guard

241 of roughly 500 total findings, both of them boilerplate omissions rather
than judgement failures. Every one of those was a round trip: write, run the
audit, read the finding, go back and add the block you already knew you needed.

The rest of this system is detection - it catches defects after they have been
expressed. Detection cannot make you right the first time; it can only tell you
that you were not. A generator makes the wrong thing unexpressible instead:
emit the snapshot, the stamp, the manifest entry, the schedule row and the
stale detector together, and four rules become structurally unfireable.

  python3 scripts/new_pipeline.py --name capture_daily_widget \\
      --at 23:57:30 --label widget --source sensor.widget_daily_kwh

Prints the four pieces. Writes nothing without --apply, and even then only to
pipelines.yaml and automations.yaml - the package and the CLAUDE.md row are
printed for you to place, because both need a human decision about where.
"""
import argparse
import io
import os
import re
import sys

CONFIG = os.environ.get("HA_CONFIG", "/config").rstrip("/")
P = lambda *a: os.path.join(CONFIG, *a)


def automation_yaml(name, at, source, stamp, buffer_entity):
    """The capture automation, with the snapshot CLAUDE.md requires.

    The `variables:` block is the whole point. Until 2026-08-21 the values
    obeyed the snapshot rule but the stamps were written as a live
    {{ now().date() }}, so a capture slipping past midnight stamped tomorrow
    against today's data - and every staleness detector reads that stamp.
    """
    return """
- id: %(name)s
  alias: %(alias)s
  mode: single
  trigger:
    - platform: time
      at: "%(at)s"
  variables:
    # SNAPSHOT AT TRIGGER TIME - values AND the stamp. Never a live now().
    capture_stamp: "{{ now().strftime('%%Y-%%m-%%d %%H:%%M:%%S') }}"
    capture_value: "{{ states('%(source)s') | float(0) }}"
  condition:
    - condition: template
      value_template: >
        {{ states('%(source)s') not in ['unknown','unavailable','none',''] }}
  action:
    - service: input_number.set_value
      target:
        entity_id: %(buffer)s
      data:
        value: "{{ capture_value }}"
    - service: input_datetime.set_datetime
      target:
        entity_id: %(stamp)s
      data:
        datetime: "{{ capture_stamp }}"
""" % {"name": name, "alias": name.replace("_", " ").title(), "at": at,
       "source": source, "stamp": stamp, "buffer": buffer_entity}


def manifest_entry(name, label, at, stamp, detector, slots):
    return """  %(name)s:
    label: "%(label)s"
    kind: accumulator
    defined_in: automations.yaml
    at: '%(at)s'
    stamp: %(stamp)s
    stale_detector: %(detector)s
    buffer_slots: %(slots)d
""" % {"name": name, "label": label, "at": at, "stamp": stamp,
       "detector": detector, "slots": slots}


def detector_yaml(name, stamp, detector):
    """The stale detector. A pipeline without one cannot be monitored at all."""
    short = detector.split(".", 1)[1]
    return """
# add to the relevant packages/*.yaml
template:
  - binary_sensor:
      - name: "%(title)s"
        unique_id: %(short)s
        device_class: problem
        availability: "{{ states('%(stamp)s') not in ['unknown','unavailable','none',''] }}"
        state: >
          {%% set last = states('%(stamp)s') %%}
          {{ last in ['unknown','unavailable','none',''] or
             (now() - as_datetime(last)).total_seconds() > 172800 }}
        attributes:
          last_ok: "{{ states('%(stamp)s') }}"
          pipeline: "%(name)s"
""" % {"title": short.replace("_", " ").title(), "short": short,
       "stamp": stamp, "name": name}


def contention_check(at, writes):
    """(hard_conflicts, sharers) for the proposed trigger second.

    Returns entities the new pipeline would contend over, and the ids of every
    automation already firing at that second. Reuses ha_audit's own model - see
    the module docstring for why this must not be a second implementation.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import ha_audit as A
    except ImportError:
        return None, None          # audit unavailable: say so, do not guess
    autos = A._automations()
    conflicts, sharers = set(), []
    for aid, a in sorted(autos.items()):
        if at not in A._at_times(a):
            continue
        sharers.append(aid)
        conflicts |= (writes & (A._writes(a) | A._reads(a)))
    return conflicts, sharers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="capture_daily_<thing>")
    ap.add_argument("--at", required=True, help="HH:MM:SS local time")
    ap.add_argument("--label", required=True)
    ap.add_argument("--source", required=True, help="the sensor being captured")
    ap.add_argument("--buffer-slots", type=int, default=0)
    ap.add_argument("--apply", action="store_true",
                    help="append to pipelines.yaml and automations.yaml")
    a = ap.parse_args()

    if not re.match(r"^\d{2}:\d{2}:\d{2}$", a.at):
        sys.exit("--at must be HH:MM:SS")

    short = re.sub(r"^(capture_daily_|archive_monthly_)", "", a.name)
    stamp = "input_datetime.%s_capture_last_ok" % short
    detector = "binary_sensor.%s_capture_stale" % short
    buffer_entity = "input_number.%s_latest" % short

    # ---- refuse a contending second BEFORE printing anything ------------
    writes = {stamp, buffer_entity}
    conflicts, sharers = contention_check(a.at, writes)
    if conflicts is None:
        print("WARNING: could not import ha_audit.py, so the trigger second was "
              "NOT checked for contention. Run scripts/gate.py before trusting "
              "this.\n")
    elif conflicts:
        sys.exit(
            "REFUSING: %s already has automation(s) touching %s at that second "
            "(%s).\nTwo automations writing one entity in the same second is a "
            "blocking FAIL (eod-race) - last writer wins, silently. Pick another "
            "--at; 15s offsets are the house convention."
            % (a.at, ", ".join(sorted(conflicts)), ", ".join(sharers)))
    elif sharers:
        # Sharing a second is NOT a problem on its own - CLAUDE.md is explicit
        # that six captures fire together at 23:59:00 with no interaction. Say
        # it once so the choice is deliberate, then carry on.
        print("NOTE: %d automation(s) already trigger at %s (%s). No shared "
              "entity, so this is fine - HA runs them concurrently.\n"
              % (len(sharers), a.at, ", ".join(sharers[:4])))

    print("=" * 70)
    print("PIPELINE  %s   at %s" % (a.name, a.at))
    print("=" * 70)
    print("\n----- 1. automations.yaml -----")
    print(automation_yaml(a.name, a.at, a.source, stamp, buffer_entity))
    print("----- 2. pipelines.yaml (under `pipelines:`) -----")
    print(manifest_entry(a.name, a.label, a.at, stamp, detector, a.buffer_slots))
    print("----- 3. CLAUDE.md THE SCHEDULE - add this row by hand -----")
    print("(nothing generates that table; ha_audit validates it)\n")
    print("%-9s %-35s %s\n" % (a.at, a.name, detector.split(".", 1)[1]))
    print("----- 4. the stale detector -----")
    print(detector_yaml(a.name, stamp, detector))
    print("----- 5. helpers you must also declare -----")
    print("  %s\n  %s\n" % (stamp, buffer_entity))

    if a.apply:
        # REFUSE TO DOUBLE-APPLY. Found 2026-08-25: running --apply twice wrote
        # two automations with the same `id:` into the LIVE automations.yaml and
        # two identical keys under `pipelines:`. PyYAML takes the LAST duplicate
        # key silently, so one pipeline would simply cease to exist with nothing
        # reporting it - and this script writes to production config, which
        # makes it the most dangerous thing in this package.
        existing_a = io.open(P("automations.yaml"), encoding="utf-8").read()
        existing_p = io.open(P("pipelines.yaml"), encoding="utf-8").read()
        clash = []
        if re.search(r"^\s*-?\s*id:\s*%s\s*$" % re.escape(a.name), existing_a, re.M):
            clash.append("automations.yaml already declares id: %s" % a.name)
        if re.search(r"^\s+%s:\s*$" % re.escape(a.name), existing_p, re.M):
            clash.append("pipelines.yaml already declares %s:" % a.name)
        if clash:
            sys.exit("REFUSING TO APPLY:\n  " + "\n  ".join(clash)
                     + "\nPick a different --name, or remove the existing entry "
                       "first. A duplicate key here fails silently.")
        # R12: snapshot the prior state so it can be put back. This writes to
        # the LIVE automations.yaml and pipelines.yaml, which makes it the only
        # thing in this toolchain that mutates production config - so it takes
        # a timestamped copy of both before touching either.
        stampsuf = __import__("time").strftime("%Y%m%d-%H%M%S")
        for rel in ("automations.yaml", "pipelines.yaml"):
            bak = P("%s.%s.bak" % (rel, stampsuf))
            io.open(bak, "w", encoding="utf-8", newline="\n").write(
                io.open(P(rel), encoding="utf-8").read())
            print("BACKUP  %s" % bak)
        with io.open(P("automations.yaml"), "a", encoding="utf-8", newline="\n") as fh:
            fh.write(automation_yaml(a.name, a.at, a.source, stamp, buffer_entity))
        s = io.open(P("pipelines.yaml"), encoding="utf-8").read()
        assert "pipelines:\n" in s, "pipelines: anchor moved"
        io.open(P("pipelines.yaml"), "w", encoding="utf-8", newline="\n").write(
            s.replace("pipelines:\n", "pipelines:\n"
                      + manifest_entry(a.name, a.label, a.at, stamp, detector,
                                       a.buffer_slots), 1))
        print("APPLIED to automations.yaml and pipelines.yaml.")
        print("Pieces 3, 4 and 5 are still yours to place - then run "
              "scripts/gate.py automations.yaml pipelines.yaml")
    else:
        print("Nothing written. Re-run with --apply to append 1 and 2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
