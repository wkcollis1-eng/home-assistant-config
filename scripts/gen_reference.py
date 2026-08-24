#!/usr/bin/env python3
"""gen_reference.py - regenerate the reference docs; never hand-maintain them.

WHY THIS EXISTS. CLAUDE.md's ENTITIES section was 548 hand-maintained lines,
32.8% of the whole document, and on 2026-08-22 sixteen of its 328 ids did not
exist - including two whose missing `_1s` suffix had left a pair of alerts
structurally unable to fire. CONSTRAINTS says "use only IDs listed in ENTITIES",
which makes a wrong entry worse than no entry: it is the file instructing you to
use a name that resolves to `unknown`.

THE SPLIT OF RESPONSIBILITY
  .storage/core.entity_registry   TRUTH for "does this id exist"   (derived)
  pipelines.yaml                  TRUTH for pipeline wiring        (declared)
  entity_notes.yaml               MEANING - group and annotation   (hand-kept)
  ENTITIES.md                     GENERATED from all three         (never edit)

Only the annotation is hand-written, and an annotation cannot make an id wrong -
if the id disappears, this script drops it and reports it.

USAGE
  python3 scripts/gen_reference.py           # write all generated docs
  python3 scripts/gen_reference.py --check   # exit 1 if any would change
  python3 scripts/gen_reference.py --seed    # one-time: build entity_notes.yaml

GENERATES
  ENTITIES.md      entity reference   (registry + entity_notes.yaml + pipelines)
  AUTOMATIONS.md   every automation   (id, alias, trigger, mode, file)
  PACKAGES.md      package summary    (domains declared, counts, line counts)

All three were hand-maintained sections of CLAUDE.md totalling 744 lines, 45%
of the document. None of them held a fact the config did not already carry.

`--check` is what ha_audit calls, so a stale ENTITIES.md is a finding rather
than something discovered months later.
"""
import argparse
import io
import json
import os
import re
import sys

CONFIG = os.environ.get("HA_CONFIG", "/config")
P = lambda *a: os.path.join(CONFIG, *a)
DOMAINS = ("sensor", "binary_sensor", "input_number", "input_datetime",
           "input_boolean", "input_select", "input_text", "counter", "switch",
           "automation", "script", "utility_meter", "climate", "number", "select")


def _yaml():
    import yaml

    class Tolerant(yaml.SafeLoader):
        pass

    Tolerant.add_multi_constructor("!", lambda l, s, n: None)
    return yaml, Tolerant


def config_files():
    out = ["configuration.yaml"]
    pkg = P("packages")
    if os.path.isdir(pkg):
        out += ["packages/" + f for f in sorted(os.listdir(pkg))
                if f.endswith((".yaml", ".yml"))]
    return out


def slug(name):
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(name).lower())).strip("_")


def live_entities():
    """Registry first (authoritative), then YAML-declared things not yet registered."""
    ents, by_uid = {}, {}
    reg = P(".storage", "core.entity_registry")
    if os.path.exists(reg):
        with io.open(reg, encoding="utf-8") as fh:
            for e in json.load(fh)["data"]["entities"]:
                ents[e["entity_id"]] = e.get("original_name") or e.get("name") or ""
                if e.get("unique_id"):
                    by_uid[str(e["unique_id"])] = e["entity_id"]
    yaml, Tolerant = _yaml()
    for rel in config_files():
        try:
            with io.open(P(rel), encoding="utf-8") as fh:
                cfg = yaml.load(fh, Loader=Tolerant) or {}
        except (IOError, OSError):
            continue
        for dom in ("input_number", "input_datetime", "input_boolean",
                    "input_select", "input_text", "counter"):
            for k, v in (cfg.get(dom) or {}).items():
                ents.setdefault("%s.%s" % (dom, k),
                                (v or {}).get("name", "") if isinstance(v, dict) else "")
        # utility_meter is a COMPONENT, not an entity domain. It creates
        # sensor.* entities whose object_id comes from `name:` (falling back to
        # the config key), one per tariff when tariffs are declared.
        #
        # 2026-08-24: this used to sit in the loop above and emit
        # "utility_meter.<key>" - an id in a domain that has no entities. All 43
        # YAML meters were therefore documented under names that could never
        # resolve, and not one reached ENTITIES.md. 42 of them have no registry
        # row either (a YAML utility_meter without unique_id is never
        # registered), so they were invisible to BOTH sources CONSTRAINTS names
        # as the only permitted ones - including sensor.sem_ac_daily, which
        # pipelines.yaml declares as the guard source for
        # capture_daily_cooling_kwh_cdd.
        #
        # Same defect class as the known_entities() bug that earned R7: a
        # SYNTHESISED id standing in for a looked-up one. The fix is the same -
        # derive the id the way HA derives it, from name:, not from the key.
        for k, v in (cfg.get("utility_meter") or {}).items():
            v = v if isinstance(v, dict) else {}
            base = slug(v.get("name") or k)
            tariffs = v.get("tariffs") or []
            ids = ["%s_%s" % (base, slug(t)) for t in tariffs] if tariffs else [base]
            for oid in ids:
                ents.setdefault("sensor." + oid, v.get("name") or k)
        blocks = cfg.get("template") or []
        if isinstance(blocks, dict):
            blocks = [blocks]
        for b in blocks:
            if not isinstance(b, dict):
                continue
            for dom in ("sensor", "binary_sensor"):
                for e in (b.get(dom) or []):
                    if isinstance(e, dict) and e.get("name"):
                        eid = by_uid.get(str(e.get("unique_id")))
                        ents.setdefault(eid or "%s.%s" % (dom, slug(e["name"])), e["name"])
    return ents


def pipeline_entities():
    """entity -> pipeline name, from the manifest."""
    yaml, Tolerant = _yaml()
    try:
        with io.open(P("pipelines.yaml"), encoding="utf-8") as fh:
            man = yaml.load(fh, Loader=Tolerant) or {}
    except (IOError, OSError):
        return {}
    out = {}
    for name, p in (man.get("pipelines") or {}).items():
        cand = list(p.get("buffer") or []) + list(p.get("limits") or [])
        for k in ("stamp", "seed_stamp", "stale_detector"):
            if p.get(k):
                cand.append(p[k])
        g = p.get("guard") or {}
        cand += [g.get(k) for k in ("source", "live_source", "activity") if g.get(k)]
        for e in cand:
            if e and "{{" not in e:
                out[e] = name
    return out


def pipeline_names():
    yaml, Tolerant = _yaml()
    try:
        with io.open(P("pipelines.yaml"), encoding="utf-8") as fh:
            man = yaml.load(fh, Loader=Tolerant) or {}
    except (IOError, OSError):
        return []
    return list((man.get("pipelines") or {}).keys())


def load_notes():
    yaml, Tolerant = _yaml()
    try:
        with io.open(P("entity_notes.yaml"), encoding="utf-8") as fh:
            return yaml.load(fh, Loader=Tolerant) or {}
    except (IOError, OSError):
        return {}


def seed_from_claude_md():
    """One-time: lift group + annotation out of the old ENTITIES block."""
    doc = io.open(P("CLAUDE.md"), encoding="utf-8").read()
    notes, group, in_block = {}, None, False
    for line in doc.splitlines():
        if line.startswith("#"):
            in_block = False
            m = re.match(r"^#+\s+(.*?)\s*$", line)
            if m and not m.group(1).lower().startswith(("pending", "changelog")):
                group = m.group(1)
            continue
        if line.startswith("```"):
            in_block = not in_block
            continue
        if not in_block:
            continue
        m = re.match(r"^([a-z_]+\.[a-z0-9_]+)(?:\s{2,}(.*))?$", line)
        if m and m.group(1).split(".")[0] in DOMAINS:
            notes[m.group(1)] = {"group": group or "UNGROUPED",
                                 "note": (m.group(2) or "").strip()}
    return notes


def render(notes, live, pipes):
    groups = {}
    for eid, meta in notes.items():
        if eid not in live:
            continue
        groups.setdefault(meta.get("group") or "UNGROUPED", []).append((eid, meta))
    out = [
        "# ENTITIES — GENERATED, DO NOT EDIT",
        "",
        "Written by `scripts/gen_reference.py` from `.storage/core.entity_registry`,",
        "the YAML helper declarations, and `pipelines.yaml`. Hand edits are lost on",
        "the next run and `ha_audit.py` FAILs when this file is stale.",
        "",
        "To change an annotation, edit `entity_notes.yaml` and regenerate. An id that",
        "disappears from the registry is dropped here automatically — which is the",
        "whole point: the 2026-08-22 audit found 16 of 328 hand-listed ids did not",
        "exist, two of them behind alerts that could never fire.",
        "",
        "**Resolution order when you need an entity id: this file, then the registry.",
        "Never from memory, and never inferred from a pattern.**",
        "",
    ]
    for g in sorted(groups):
        out.append("## %s" % g)
        out.append("")
        out.append("```")
        width = max(len(e) for e, _ in groups[g]) + 2
        for eid, meta in sorted(groups[g]):
            note = meta.get("note") or ""
            pipe = pipes.get(eid)
            if pipe and pipe not in note:
                note = (note + "  " if note else "") + "[pipeline: %s]" % pipe
            out.append(("%-*s%s" % (width, eid, note)).rstrip())
        out.append("```")
        out.append("")
    undocumented = sorted(set(pipes) & set(live) - set(notes))
    if undocumented:
        out.append("## UNDOCUMENTED — in pipelines.yaml, no note in entity_notes.yaml")
        out.append("")
        out.append("```")
        out += ["%-52s [pipeline: %s]" % (e, pipes[e]) for e in undocumented]
        out.append("```")
        out.append("")
    return "\n".join(out)


def _all_automations():
    """(id, alias, trigger summary, mode, file) for every automation."""
    yaml, Tolerant = _yaml()
    out = []
    for rel in ["automations.yaml"] + config_files():
        try:
            with io.open(P(rel), encoding="utf-8") as fh:
                cfg = yaml.load(fh, Loader=Tolerant)
        except (IOError, OSError):
            continue
        seq = cfg if isinstance(cfg, list) else (cfg or {}).get("automation") or []
        for a in seq:
            if not isinstance(a, dict) or not a.get("id"):
                continue
            trg = a.get("trigger") or a.get("triggers") or []
            if isinstance(trg, dict):
                trg = [trg]
            parts = []
            for t in trg:
                if not isinstance(t, dict):
                    continue
                if t.get("at"):
                    parts.append(str(t["at"]))
                elif (t.get("platform") or t.get("trigger")) == "state":
                    e = t.get("entity_id")
                    parts.append("state:%s" % (e if isinstance(e, str) else
                                               _clip(e or [], 40, ",")))
                else:
                    parts.append(str(t.get("platform") or t.get("trigger") or "?"))
            out.append((a["id"], a.get("alias", ""), _clip(parts, 46),
                        a.get("mode", "single"), rel))
    return sorted(out)


def _clip(items, limit, joiner=", "):
    """Join items, dropping WHOLE items rather than cutting one in half.

    A truncated entity id is indistinguishable from a real one - it looks like
    a name you could paste. This never emits a partial token; it drops whole
    entries and says how many.
    Earned 2026-08-24: 16 ids in AUTOMATIONS.md were silently cut mid-name
    (binary_sensor.hvac_ac_short_cycling_aler) and 3 domain counts in
    PACKAGES.md were cut mid-word (shell_comman, sens, scrip).
    A single over-long item is returned INTACT - correctness beats alignment.
    """
    items = [str(i) for i in items]
    kept, used = [], 0
    for it in items:
        add = len(it) + (len(joiner) if kept else 0)
        if kept and used + add > limit:
            return joiner.join(kept) + " +%d more" % (len(items) - len(kept))
        kept.append(it)
        used += add
    return joiner.join(kept)


def render_automations(autos, pipes_by_name):
    out = ["# AUTOMATIONS — GENERATED, DO NOT EDIT", "",
           "Written by `scripts/gen_reference.py` from `automations.yaml` and every",
           "`packages/*.yaml`. Replaced an 86-line hand-kept index in CLAUDE.md that",
           "held nothing the config did not already state.", "",
           "`[pipeline]` marks an automation declared in `pipelines.yaml`.", "",
           "```"]
    w = max(len(a[0]) for a in autos) + 2
    wt = max([len(a[2] or "-") for a in autos] + [48]) + 1
    for aid, alias, trig, mode, rel in autos:
        tag = "  [pipeline]" if aid in pipes_by_name else ""
        out.append(("%-*s%-*s %-10s %s%s"
                    % (w, aid, wt, trig or "-", mode, rel.split("/")[-1], tag)).rstrip())
    out += ["```", "", "%d automations." % len(autos), ""]
    return "\n".join(out)


def render_packages():
    yaml, Tolerant = _yaml()
    rows = []
    for rel in config_files():
        try:
            raw = io.open(P(rel), encoding="utf-8").read()
            cfg = yaml.load(raw, Loader=Tolerant) or {}
        except (IOError, OSError):
            continue
        doms = {}
        for k, v in cfg.items():
            if isinstance(v, dict):
                doms[k] = len(v)
            elif isinstance(v, list):
                doms[k] = len(v)
        rows.append((rel, len(raw.split("\n")), doms))
    out = ["# PACKAGES — GENERATED, DO NOT EDIT", "",
           "Written by `scripts/gen_reference.py`. Replaced a 110-line hand-kept",
           "section in CLAUDE.md. Counts are derived, so they cannot drift.",
           "",
           "Design notes about a package belong in that package's own header",
           "comment, where the code is - not in a summary that has to be kept in",
           "step with it.", "", "```"]
    w = max(len(r[0]) for r in rows) + 2
    for rel, lines, doms in sorted(rows):
        top = _clip(["%s:%d" % (k, n) for k, n in sorted(doms.items())
                     if k not in ("homeassistant",)], 70)
        out.append("%-*s%6d lines   %s" % (w, rel, lines, top))
    out += ["```", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--seed", action="store_true")
    args = ap.parse_args()

    if args.seed:
        notes = seed_from_claude_md()
        yaml, _ = _yaml()
        with io.open(P("entity_notes.yaml"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# Hand-maintained MEANING for entity ids. Existence is derived\n"
                     "# from the registry by scripts/gen_reference.py - an id here that\n"
                     "# no longer exists is simply dropped from ENTITIES.md and\n"
                     "# reported. Seeded 2026-08-23 from CLAUDE.md's old ENTITIES block.\n\n")
            yaml.safe_dump(notes, fh, sort_keys=True, allow_unicode=True, width=100)
        print("seeded entity_notes.yaml with %d annotations" % len(notes))
        return 0

    notes, live, pipes = load_notes(), live_entities(), pipeline_entities()
    autos = _all_automations()
    pipe_names = set(pipeline_names())
    docs = {
        "ENTITIES.md": render(notes, live, pipes),
        "AUTOMATIONS.md": render_automations(autos, pipe_names),
        "PACKAGES.md": render_packages(),
    }
    dead = sorted(set(notes) - set(live))

    if args.check:
        stale = [n for n, body in docs.items()
                 if (io.open(P(n), encoding="utf-8").read()
                     if os.path.exists(P(n)) else None) != body]
        if stale:
            print("STALE, run scripts/gen_reference.py: %s" % ", ".join(sorted(stale)))
            return 1
        print("all generated docs current (%d entities, %d automations)"
              % (len(notes), len(autos)))
        return 0

    for n, body in docs.items():
        io.open(P(n), "w", encoding="utf-8", newline="\n").write(body)
    print("wrote %s" % ", ".join(sorted(docs)))
    print("   %d annotated entities, %d live, %d in pipelines, %d automations"
          % (len(notes), len(live), len(pipes), len(autos)))
    if dead:
        print("dropped %d annotated ids that no longer exist:" % len(dead))
        for d in dead:
            print("   ", d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
