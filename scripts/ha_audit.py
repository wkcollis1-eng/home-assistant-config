#!/usr/bin/env python3
"""
ha_audit.py — static audit of this config against pipelines.yaml.

Not generic YAML linting; .yamllint.yml already does that in CI. Every rule
here was earned by a failure this system actually had, and each names the
incident it came from. Adding a rule when a new bug is found is how the audit
compounds instead of going stale.

Runs offline: config files, the entity registry, and core.restore_state. No
API, no token, no network. Safe to run while HA is down.

  python3 ha_audit.py            # full report
  python3 ha_audit.py --quiet    # failures only
  HA_CONFIG=/config              # default; set to H:\\ to run off-host

Exit 0 clean, 1 if any FAIL. WARN never blocks.
"""

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required")

CONFIG = os.environ.get("HA_CONFIG", "/config")
P = lambda *a: os.path.join(CONFIG, *a)

class Tolerant(yaml.SafeLoader):
    pass
Tolerant.add_multi_constructor("!", lambda l, s, n: {"__tag__": s})

findings = []
def fail(rule, msg): findings.append(("FAIL", rule, msg))
def warn(rule, msg): findings.append(("WARN", rule, msg))
def info(rule, msg): findings.append(("INFO", rule, msg))


def load(rel, default=None):
    p = P(*rel.split("/"))
    if not os.path.exists(p):
        return default
    with io.open(p, encoding="utf-8") as fh:
        return yaml.load(fh, Loader=Tolerant)


def text(rel):
    p = P(*rel.split("/"))
    return io.open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def config_files():
    """configuration.yaml plus every package.

    Globbed, not listed. A hardcoded list is how packages/audit.yaml was
    invisible to this audit the moment it was created — the same duplication
    failure the manifest exists to end.
    """
    out = ["configuration.yaml"]
    pkg = P("packages")
    if os.path.isdir(pkg):
        out += ["packages/" + f for f in sorted(os.listdir(pkg))
                if f.endswith((".yaml", ".yml"))]
    return out



def _dashboard_files():
    """Every Lovelace YAML snippet under dashboards/, recursively."""
    out, root = [], P("dashboards")
    for dirpath, _dirs, files in os.walk(root):
        for f in sorted(files):
            if f.endswith((".yaml", ".yml")):
                out.append(os.path.relpath(os.path.join(dirpath, f), CONFIG).replace("\\", "/"))
    return out


def slug(name):
    """HA's object_id derivation from a friendly name (slugify, separator '_')."""
    out = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
    return re.sub(r"_+", "_", out)


def _yaml_template_entities():
    """(domain, name, unique_id, file) for every YAML-declared template entity.

    Covers `template:` blocks and legacy platform-style `sensor:` entries.
    """
    out = []
    for rel in config_files():
        cfg = load(rel) or {}
        blocks = cfg.get("template") or []
        if isinstance(blocks, dict):
            blocks = [blocks]
        for b in blocks:
            if not isinstance(b, dict):
                continue
            for dom in ("sensor", "binary_sensor"):
                for s in (b.get(dom) or []):
                    if isinstance(s, dict) and s.get("name"):
                        out.append((dom, s["name"], s.get("unique_id"), rel))
        for s in (cfg.get("sensor") or []):
            if isinstance(s, dict) and s.get("name"):
                out.append(("sensor", s["name"], s.get("unique_id"), rel))
    return out


def known_entities():
    """Everything HA could resolve: registry + YAML-declared helpers/templates.

    2026-08-22 — THE BUG THIS FUNCTION USED TO HAVE. For template entities it
    synthesised "<domain>.<unique_id>" and called that a known entity. HA does
    not derive entity_id from unique_id; it derives it from `name:` and stores
    the result in the registry against the unique_id. So any entity whose
    unique_id differed from slugify(name) was registered under one id while
    this audit vouched for a DIFFERENT id that had never existed — and every
    reference to that phantom resolved clean.

    That is exactly how the dehumidifier SPC capture died. The latch's name
    gave sensor.dehumidifier_running_watts_latched; its unique_id said
    ..._steady_latched; four consumers and pipelines.yaml read the _steady_
    form; the guard got `unavailable` -> float(-1) -> skip, 15 nights running,
    while rule_entities_resolve reported no problem. The registry is
    authoritative and is already loaded here — use it, and fall back to
    slugify(name), never to unique_id.
    """
    ents = set()
    by_uid = {}
    reg = P(".storage", "core.entity_registry")
    if os.path.exists(reg):
        with io.open(reg, encoding="utf-8") as fh:
            for e in json.load(fh)["data"]["entities"]:
                ents.add(e["entity_id"])
                if e.get("unique_id"):
                    by_uid[str(e["unique_id"])] = e["entity_id"]
    rs = P(".storage", "core.restore_state")
    if os.path.exists(rs):
        with io.open(rs, encoding="utf-8") as fh:
            for i in json.load(fh).get("data", []):
                eid = (i.get("state") or {}).get("entity_id")
                if eid:
                    ents.add(eid)
    # YAML-declared helpers keep their key as the object_id.
    for rel in config_files():
        cfg = load(rel) or {}
        for dom in ("input_number", "input_datetime", "input_boolean", "input_select",
                    "input_text", "counter"):
            for k in (cfg.get(dom) or {}):
                ents.add("%s.%s" % (dom, k))
    # utility_meter is a COMPONENT, not an entity domain: it creates sensor.*
    # ids from `name:` (falling back to the config key), one per tariff when
    # tariffs are declared. 2026-08-24: this loop used to emit
    # "utility_meter.<key>", so all 43 YAML meters were absent from the known
    # set and any reference to one would have been reported unresolved. Same
    # synthesis defect this function's own docstring describes for unique_id,
    # in the same function. Fixed alongside the identical bug in
    # scripts/gen_reference.py.
    for rel in config_files():
        for k, v in ((load(rel) or {}).get("utility_meter") or {}).items():
            v = v if isinstance(v, dict) else {}
            base = slug(v.get("name") or k)
            tf = v.get("tariffs") or []
            for oid in (["%s_%s" % (base, slug(t)) for t in tf] if tf else [base]):
                ents.add("sensor." + oid)
    # YAML automations and scripts. Added 2026-08-22: rule_entity_refs_resolve
    # flagged automation.sdr_water_meter_leak_now, which is declared right there
    # in packages/utility_meters.yaml - it was simply not registered yet. HA
    # derives an automation's entity_id from its `alias:`, exactly as it derives
    # a template sensor's from `name:`, so the same slugify applies.
    for rel in ["automations.yaml"] + config_files():
        cfg = load(rel)
        seq = cfg if isinstance(cfg, list) else (cfg or {}).get("automation") or []
        for a in seq:
            if isinstance(a, dict) and a.get("alias"):
                ents.add("automation.%s" % slug(a["alias"]))
        for k, v in ((cfg or {}).get("script") or {}).items() if isinstance(cfg, dict) else []:
            ents.add("script.%s" % k)
    # Template entities not yet registered: registry first, then slugify(name).
    for dom, name, uid, _rel in _yaml_template_entities():
        if uid and str(uid) in by_uid:
            ents.add(by_uid[str(uid)])
        else:
            ents.add("%s.%s" % (dom, slug(name)))
    return ents


def _registry_by_uid():
    reg = P(".storage", "core.entity_registry")
    out = {}
    if os.path.exists(reg):
        with io.open(reg, encoding="utf-8") as fh:
            for e in json.load(fh)["data"]["entities"]:
                if e.get("unique_id"):
                    out[str(e["unique_id"])] = e["entity_id"]
    return out


def rule_unique_id_not_entity_id():
    """A unique_id that is not the entity_id is a trap for every consumer.

    Inert on its own — HA is happy — but it reads like an entity_id and gets
    copied into templates as one. Only reported when something in the config
    or the manifest actually references the phantom "<domain>.<unique_id>",
    because renaming a live unique_id orphans its registry entry and drops the
    restored state; the fix is to correct the CONSUMERS, not the unique_id.

    The comparison is against the REGISTRY, not against slugify(name), and the
    difference is not academic: HA fixes entity_id at first registration and
    never revises it when `name:` later changes. sensor.site_eui_estimate is
    exactly that case — its name now slugifies to site_eui_rolling_12m_bills,
    but the registered id still matches the unique_id and every reference is
    correct. slugify(name) is the fallback for entities not yet registered.
    """
    by_uid = _registry_by_uid()
    live = known_entities()
    text = ""
    # dashboards/ added 2026-08-22. It had never been scanned by any rule, and
    # that is not academic: the runtime-per-HDD control chart plotted
    # sensor.hvac_runtime_per_hdd_upper_bound, which does not exist, and drew no
    # limit lines for it. The audit only caught that because the same dead id
    # also appeared in configuration.yaml. A card is the one place a broken
    # entity is completely silent - no log line, no unavailable state, just an
    # empty series.
    for rel in config_files() + ["automations.yaml", "pipelines.yaml",
                                 "scripts.yaml"] + _dashboard_files():
        try:
            with io.open(P(rel), encoding="utf-8") as fh:
                text += fh.read()
        except (IOError, OSError):
            pass
    for dom, name, uid, rel in _yaml_template_entities():
        if not uid:
            continue
        real = by_uid.get(str(uid)) or "%s.%s" % (dom, slug(name))
        phantom = "%s.%s" % (dom, uid)
        # Belt-and-braces: if the phantom id resolves to a real entity anyway
        # (a second registration under that exact id), the references work and
        # this is not the defect being hunted.
        if phantom == real or phantom in live:
            continue
        # MUST be a whole-word match. `phantom in text` reported six false
        # FAILs on 2026-08-22 because sensor.hvac_furnace_runtime_month is a
        # prefix of sensor.hvac_furnace_runtime_month_2 -- and the _2 form is
        # what every consumer correctly uses. An audit that cries about
        # working references is an audit that gets ignored.
        if re.search(r"(?<![a-z0-9_.])%s(?![a-z0-9_])" % re.escape(phantom), text):
            fail("phantom-entity-id",
                 "%s: '%s' is referenced but no such entity exists -- unique_id "
                 "'%s' belongs to %s (name: %r). Fix the references, not the "
                 "unique_id" % (rel, phantom, uid, real, name))


# --------------------------------------------------------------------------
def _automations():
    autos = {}
    for rel in ["automations.yaml"] + config_files():
        cfg = load(rel)
        seq = cfg if isinstance(cfg, list) else (cfg or {}).get("automation") or []
        for a in seq:
            if isinstance(a, dict) and a.get("id"):
                autos[a["id"]] = a
    return autos


def _writes(a):
    out = set()
    def rec(o):
        if isinstance(o, dict):
            svc = o.get("service") or o.get("action")
            if isinstance(svc, str) and (".set_value" in svc or ".set_datetime" in svc
                                         or ".increment" in svc or ".decrement" in svc):
                t = o.get("target") or {}
                e = t.get("entity_id") if isinstance(t, dict) else None
                for x in ([e] if isinstance(e, str) else (e or [])):
                    if x:
                        out.add(x)
            for v in o.values():
                rec(v)
        elif isinstance(o, list):
            for v in o:
                rec(v)
    rec(a)
    return out


def _reads(a):
    return set(re.findall(r"states\(\s*'([a-z_]+\.[a-z0-9_]+)'", json.dumps(a, default=str)))



def rule_manifest_matches_config(man):
    """The manifest must not drift from the config the way its 5 predecessors did.

    Re-derives capture times and stamps from the automations and compares.
    """
    autos = {}
    for rel in ["automations.yaml"] + config_files():
        cfg = load(rel)
        seq = cfg if isinstance(cfg, list) else (cfg or {}).get("automation") or []
        for a in seq:
            if isinstance(a, dict) and a.get("id"):
                autos[a["id"]] = a
    for name, p in (man.get("pipelines") or {}).items():
        a = autos.get(name)
        if a is None:
            fail("manifest-drift", "%s: declared in pipelines.yaml, no such automation" % name)
            continue
        trg = a.get("trigger") or a.get("triggers") or []
        if isinstance(trg, dict):
            trg = [trg]
        at = next((t.get("at") for t in trg if isinstance(t, dict) and t.get("at")), None)
        if at != p.get("at"):
            fail("manifest-drift", "%s: manifest at=%s, config at=%s" % (name, p.get("at"), at))
    for aid in autos:
        if re.match(r"^(capture_daily_|archive_monthly_)", aid) and aid not in (man.get("pipelines") or {}):
            fail("manifest-drift", "%s: capture automation missing from pipelines.yaml" % aid)


def rule_entities_resolve(man, ents):
    """Every entity the manifest names must exist. Catches renames and typos."""
    for name, p in (man.get("pipelines") or {}).items():
        cand = list(p.get("buffer") or []) + list(p.get("limits") or [])
        for k in ("stamp", "seed_stamp", "stale_detector"):
            if p.get(k):
                cand.append(p[k])
        g = p.get("guard") or {}
        cand += [g.get(k) for k in ("source", "live_source", "activity") if g.get(k)]
        for e in cand:
            if e and "{{" not in e and e not in ents:
                warn("entity-missing", "%s: %s not found in registry or config" % (name, e))


def rule_doc_ids(ents):
    """Entity ids in INSTRUCTION text must resolve, and no id may be truncated.

    Two defects found 2026-08-24, both invisible to every other gate.

    dead-constraint - CONSTRAINTS carried a NEVER-rule naming
        sensor.shelly_plus_uni_voltge. No such entity exists in the 1,857
        known ids and no Shelly Plus Uni device is installed at all. A rule
        guarding a ghost cannot be obeyed or checked, and it spends the
        reader's attention on the way past - the same defect that made the
        hand-kept ENTITIES block a defect generator.

        SCOPED TO CONSTRAINTS DELIBERATELY. The R1-R14 scars, KNOWN ISSUES and
        PENDING all legitimately name entities that never existed or are long
        gone - the *_steady_latched id is quoted in DEFINITION OF DONE
        precisely BECAUSE it never existed. Flagging those would make this
        rule wrong, and a wrong rule spends trust faster than no rule (R7).

    truncated-id - gen_reference.py cut trigger summaries at a fixed width
        with no ellipsis, so binary_sensor.hvac_ac_short_cycling_alert was
        written as binary_sensor.hvac_ac_short_cycling_aler: a string
        indistinguishable from a real id, which resolves to nothing if pasted.
        16 ids were affected. The signature is exact - an id that is a strict
        PREFIX of a real id but is not itself real. Fixed at source the same
        day; this is the regression guard, because the generated docs are
        rewritten by a script whose diff nobody reads.

    NOT-AN-ENTITY exclusions are explicit rather than clever. sensor.py is a
    real substring of components/statistics/sensor.py, which CONSTRAINTS cites
    as a source file to read. A regex cannot tell a filename from an id, so
    the exception is declared here where it can be seen.
    """
    DOMS = re.compile(r"(?<![\w.])(?:sensor|binary_sensor|input_boolean|"
                      r"input_button|input_number|input_datetime|switch|"
                      r"counter)\.[a-z0-9_]+")
    NOT_ENTITIES = {"sensor.py", "sensor.source", "sensor.yaml"}

    doc = text("CLAUDE.md") or ""
    m = re.search(r"^##\s+CONSTRAINTS.*?$(.*?)^---\s*$", doc, re.M | re.S)
    if not m:
        warn("doc-ids-uncheckable",
             "could not find the CONSTRAINTS section in CLAUDE.md - this check "
             "did not run, so its findings are absent, not clean")
    else:
        for eid in sorted(set(DOMS.findall(m.group(1))) - NOT_ENTITIES):
            if eid not in ents:
                fail("dead-constraint",
                     "CLAUDE.md CONSTRAINTS references %s, which does not "
                     "exist. A constraint naming a non-existent entity cannot "
                     "be obeyed - delete it or fix the id." % eid)

    for name in ("ENTITIES.md", "AUTOMATIONS.md", "PACKAGES.md"):
        for eid in sorted(set(DOMS.findall(text(name) or "")) - NOT_ENTITIES):
            if eid in ents:
                continue
            longer = [e for e in sorted(ents) if e.startswith(eid) and e != eid]
            if longer:
                fail("truncated-id",
                     "%s contains %s, a prefix of %s that resolves to nothing. "
                     "A generated doc is cutting ids mid-name - fix "
                     "scripts/gen_reference.py, do not hand-edit the doc."
                     % (name, eid, longer[0]))


def rule_generated_docs(ents):
    """ENTITIES.md / AUTOMATIONS.md / PACKAGES.md must be current, not hand-kept.

    Those three were 744 lines of CLAUDE.md - 45% of it - maintained by hand, and
    on 2026-08-22 sixteen of the 328 entity ids did not exist, two of them behind
    alerts that could never fire. CONSTRAINTS calls that list the only permitted
    source of ids, which makes a wrong entry the file instructing you to use a
    name that resolves to `unknown`. Generation replaced curation on 2026-08-23;
    this rule is what stops the generated copies rotting instead.

    Three failure modes, all FAIL:
      missing  - the doc was deleted
      stale    - regenerating would change it: config moved and nobody re-ran
      ghost    - an id in ENTITIES.md that does not resolve, which gen_reference
                 drops by construction, so a hit means it was hand-edited
    """
    gen = None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gen_reference", P("scripts", "gen_reference.py"))
        gen = importlib.util.module_from_spec(spec)
        os.environ.setdefault("HA_CONFIG", CONFIG)
        spec.loader.exec_module(gen)
        gen.CONFIG = CONFIG
        gen.P = lambda *a: os.path.join(CONFIG, *a)
    except Exception as e:
        warn("generated-docs-uncheckable",
             "could not load scripts/gen_reference.py to compare: %s" % e)
        return

    try:
        notes, live, pipes = gen.load_notes(), gen.live_entities(), gen.pipeline_entities()
        want = {
            "ENTITIES.md": gen.render(notes, live, pipes),
            "AUTOMATIONS.md": gen.render_automations(gen._all_automations(),
                                                     set(gen.pipeline_names())),
            "PACKAGES.md": gen.render_packages(),
        }
    except Exception as e:
        warn("generated-docs-uncheckable", "gen_reference.py raised: %s" % e)
        return

    for name, body in sorted(want.items()):
        path = P(name)
        if not os.path.exists(path):
            fail("generated-doc-missing",
                 "%s does not exist - run scripts/gen_reference.py" % name)
            continue
        if io.open(path, encoding="utf-8").read() != body:
            fail("generated-doc-stale",
                 "%s differs from what scripts/gen_reference.py would write - "
                 "regenerate and commit it" % name)

    for d in sorted(set(notes) - set(live)):
        warn("entity-note-orphan",
             "entity_notes.yaml annotates %s, which no longer exists - remove "
             "the note or restore the entity" % d)

    # ghosts, in case a generated file was hand-edited anyway
    doc = text("ENTITIES.md")
    listed, in_block = set(), False
    for line in (doc or "").splitlines():
        if line.startswith("```"):
            in_block = not in_block
            continue
        if not in_block:
            continue
        mm = re.match(r"^([a-z_]+)\.([a-z0-9_]+)(?:$|  )", line)
        if mm and mm.group(1) in ("sensor", "binary_sensor", "input_number",
                                  "input_datetime", "input_boolean", "input_select",
                                  "input_text", "counter", "switch", "automation",
                                  "script", "utility_meter", "climate", "number",
                                  "select"):
            listed.add("%s.%s" % (mm.group(1), mm.group(2)))
    for e in sorted(listed - ents):
        fail("generated-doc-ghost",
             "ENTITIES.md lists %s, which does not exist - it was hand-edited; "
             "run scripts/gen_reference.py" % e)


def _live_states():
    """/api/states, or None when no token is reachable.

    The audit is offline by design and stays that way: every rule that needs
    this degrades to an INFO saying it was skipped, never to silence. Silence
    would make a missing check indistinguishable from a passing one.
    Inside HA, shell_command inherits SUPERVISOR_TOKEN. Off-host, set HA_URL
    and HA_TOKEN.
    """
    import urllib.request
    # HA_TOKEN FIRST. This script normally runs as a shell_command INSIDE HA
    # Core, and the Supervisor proxy at http://supervisor/core/api is for
    # ADD-ONS - Core's own SUPERVISOR_TOKEN is not accepted there, so leading
    # with it produced a 401 that buried the real cause. Supervisor is kept as a
    # fallback for anyone running this from an add-on context, where it is the
    # correct route.
    FIX = ("set HA_TOKEN (and optionally HA_URL) for the shell_command - see "
           "docs/addons/enable-live-check.md")
    attempts = []
    if os.environ.get("HA_TOKEN"):
        attempts.append(("HA_TOKEN",
                         os.environ.get("HA_URL", "http://localhost:8123").rstrip("/")
                         + "/api/states", os.environ["HA_TOKEN"]))
    if os.environ.get("SUPERVISOR_TOKEN"):
        attempts.append(("SUPERVISOR_TOKEN (add-on route)",
                         "http://supervisor/core/api/states",
                         os.environ["SUPERVISOR_TOKEN"]))
    present = [k for k in ("HA_TOKEN", "SUPERVISOR_TOKEN") if os.environ.get(k)]
    if not attempts:
        return None, "no credential in this environment (HA_TOKEN unset). " + FIX
    why = []
    for label, url, tok in attempts:
        try:
            req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
            with urllib.request.urlopen(req, timeout=10) as fh:
                return json.load(fh), None
        except Exception as e:
            why.append("%s -> %s" % (label, e))
    # Name what was available as well as what failed: "HA_TOKEN unset" is the
    # actionable half and it is invisible if only failures are listed.
    return None, ("credentials present: %s. %s. %s"
                  % (", ".join(present), "; ".join(why),
                     FIX if "HA_TOKEN" not in present else
                     "HA_TOKEN was rejected - check the token is valid and not revoked"))


def rule_statistics_buffer(states):
    """A statistics buffer that fills before max_age silently changes the metric.

    HA keeps at most `sampling_size` samples. Once the buffer is full, max_age
    stops governing and the mean covers only the last N samples - so it becomes
    DUTY-DEPENDENT: a busy day shortens the window, a quiet day lengthens it.
    packages/spc.yaml already records this costing -0.56 W on 2026-08-05, when
    2000 samples turned out to be 2.78 h of dehumidifier run time.

    Static analysis cannot see it - sample cadence is a runtime property - but
    HA publishes buffer_usage_ratio on every statistics sensor, so this reads
    the deployed truth. Measured 2026-08-22: four sensors at 0.91-0.94,
    including fridge_running_watts_24h, which feeds an SPC chart.
    """
    states, why = states
    if states is None:
        # A check that did not run is a COVERAGE GAP, not information. This one
        # is the rule that caught sensor.fridge_running_watts_24h covering 2.6 h
        # instead of 24, and it has never executed in the nightly run. Silence
        # here would make "no findings" indistinguishable from "never looked".
        warn("live-check-skipped",
             "statistics buffer check DID NOT RUN, so its findings are absent "
             "rather than clean: %s" % why)
        return
    for st in states:
        a = st.get("attributes") or {}
        r = a.get("buffer_usage_ratio")
        if r is None:
            continue
        cov = a.get("age_coverage_ratio")
        if r >= 0.98 and cov is not None and cov < 0.99:
            fail("statistics-buffer-truncating",
                 "%s: buffer %.2f full and age coverage only %.2f - sampling_size "
                 "is governing, not max_age, and the mean is duty-dependent"
                 % (st["entity_id"], r, cov))
        elif r >= 0.85:
            warn("statistics-buffer-truncating",
                 "%s: buffer %.0f%% full - raise sampling_size before it starts "
                 "evicting and max_age stops governing" % (st["entity_id"], r * 100))


def rule_entity_refs_resolve(ents):
    """Every literal entity id referenced anywhere in config must exist.

    rule_entities_resolve only checks ids the manifest names. This checks all of
    them - 641 refs across config, automations, scripts and dashboards. It would
    have caught the runtime-per-HDD bounds and the CDD stddev on its own instead
    of by luck, and it turned up a leak alarm whose trigger entity never existed.

    Ids ending in '_' are skipped: those are Jinja concatenations like
    states('input_number.gas_archive_' ~ year) and the regex necessarily
    truncates at the quote. Eight of the first fifteen hits were exactly that.
    """
    pat = re.compile(r"(?:states|is_state|state_attr|is_state_attr)\(\s*'([a-z_]+\.[a-z0-9_]+)'")
    pat2 = re.compile(r"^\s*(?:-\s*)?entity(?:_id)?:\s*([a-z_]+\.[a-z0-9_]+)\s*$", re.M)
    seen = {}
    for rel in config_files() + ["automations.yaml", "scripts.yaml"] + _dashboard_files():
        src = text(rel)
        if not src:
            continue
        for e in pat.findall(src) + pat2.findall(src):
            if e.endswith("_") or e in ents:
                continue
            seen.setdefault(e, [rel, 0])
            seen[e][1] += 1
    for e in sorted(seen):
        rel, n = seen[e]
        warn("entity-ref-unresolved",
             "%s references %s (x%d), which does not exist" % (rel, e, n))


def rule_choose_has_default():
    """CLAUDE.md: MUST add `default: []` to every choose: block.

    Behaviourally a missing default and `default: []` are identical - both do
    nothing. The rule is about intent: an explicit empty default says "nothing
    happens here and that is deliberate", which is the difference between a
    considered fall-through and a forgotten branch.
    """
    def walk(node, path, rel):
        if isinstance(node, dict):
            if "choose" in node and "default" not in node:
                fail("choose-without-default",
                     "%s: choose: block at %s has no default:" % (rel, path or "/"))
            for k, v in node.items():
                walk(v, "%s/%s" % (path, k), rel)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, "%s[%d]" % (path, i), rel)
    for rel in config_files() + ["automations.yaml", "scripts.yaml"]:
        walk(load(rel), "", rel)


def rule_fabricated_limit_constants():
    """A non-zero literal fallback feeding a control limit is a fake measurement.

    rule_fabricated_constants covers packages/spc.yaml only. The same defect
    lives in configuration.yaml and it is not theoretical: while
    sensor.hvac_runtime_per_cdd_7_day_stddev was misspelled, `| float(2.0)` drew
    the per-CDD band at 25.1-33.1 instead of 15.5-42.7 against a real std_dev of
    6.8, and held hvac_runtime_per_cdd_low_alert ON for a healthy 21.2 min/CDD.

    `float(0)` is exempt - it is the mandated safe default and cannot
    manufacture a band, because every limit consumer gates on `> 0`.
    """
    pat = re.compile(r"set\s+(\w*(?:sigma|stddev|std_dev|mean|upper|lower|ucl|lcl|sd)\w*)"
                     r"\s*=\s*states\([^)]*\)\s*\|\s*float\((\d+(?:\.\d+)?)\)", re.I)
    for rel in config_files():
        src = text(rel)
        if not src:
            continue
        for m in pat.finditer(src):
            if float(m.group(2)) == 0:
                continue
            warn("fabricated-limit-constant",
                 "%s:%d: `%s` falls back to the literal %s - if its source ever "
                 "goes missing the limit is drawn from a number nobody measured"
                 % (rel, src[:m.start()].count("\n") + 1, m.group(1), m.group(2)))


def rule_chart_window_vs_recorder():
    """An apexcharts window longer than purge_keep_days can only draw blanks.

    Unless the card sets `statistics: true` it reads recorder states, which are
    purged. energy-month-30d.yaml asks for 30d against purge_keep_days: 14, so
    over half of it has never had data to draw.
    """
    keep = None
    for rel in ("configuration.yaml",):
        cfg = load(rel) or {}
        keep = (cfg.get("recorder") or {}).get("purge_keep_days")
    if not keep:
        return

    def _apex_cards(node, out):
        """Every custom:apexcharts-card dict anywhere in a dashboard config."""
        if isinstance(node, dict):
            if node.get("type") == "custom:apexcharts-card":
                out.append(node)
            for v in node.values():
                _apex_cards(v, out)
        elif isinstance(node, list):
            for v in node:
                _apex_cards(v, out)
        return out

    for rel in _dashboard_files():
        # 2026-08-24, TWO DEFECTS FIXED HERE, both R6 - the rule was written from
        # an assumption about apexcharts-card's API instead of from the shipped JS.
        #
        # 1. It looked for the literal `statistics: true`. That is not an option
        #    the card has. Reading www/community/apexcharts-card/apexcharts-card.js
        #    shows `statistics` is an OBJECT taking `period` (5minute|hour|day|
        #    week|month) and `type` (mean|min|max|sum|state|change), which it
        #    feeds to statistics_during_period. So the escape hatch could never
        #    be satisfied by a correct config, and the fix the message told you
        #    to apply does not exist.
        # 2. The check was whole-FILE. One occurrence anywhere in a 200 KB
        #    dashboard muted every chart in it - a blanket suppression wearing
        #    the clothes of a per-chart exemption.
        #
        # Now parsed and scoped per card, and a card counts as covered only when
        # EVERY series reads statistics; one raw series still draws blanks.
        cfg = load(rel)
        if not cfg:
            continue
        for card in _apex_cards(cfg, []):
            span = card.get("graph_span")
            m = re.match(r"^(\d+)d$", str(span or ""))
            if not m or int(m.group(1)) <= keep:
                continue
            series = card.get("series") or []
            # A series is safe from the purge horizon if it reads long-term
            # statistics OR generates its own points. 2026-08-24: the first
            # version of this check only accepted `statistics`, so a chart whose
            # constant reference line uses a data_generator - the idiom the SPC
            # control limits already use, and the only option for an
            # input_number, which has no state_class and therefore no long-term
            # statistics - stayed flagged with nothing left to fix. A warning
            # you cannot clear teaches you to ignore the rule.
            covered = bool(series) and all(
                isinstance(sr, dict) and (sr.get("statistics") or sr.get("data_generator"))
                for sr in series)
            if covered:
                continue
            title = ((card.get("header") or {}).get("title")
                     or (series[0].get("entity") if series and isinstance(series[0], dict) else "?"))
            warn("chart-window-exceeds-recorder",
                 "%s: chart %r asks for %sd but recorder purge_keep_days is %s - "
                 "the extra %dd can only ever be blank. Give EVERY series a "
                 "`statistics:` block (period: day, type: mean|state|...) or "
                 "shorten the span"
                 % (rel, title, m.group(1), keep, int(m.group(1)) - keep))

    for rel in _dashboard_files():
        src = text(rel)
        if not src:
            continue
        for m in re.finditer(r"^\s*days_to_show:\s*(\d+)\s*$", src, re.M):
            if int(m.group(1)) > keep:
                warn("chart-window-exceeds-recorder",
                     "%s asks for %sd but recorder purge_keep_days is %s - the "
                     "extra %dd can only ever be blank"
                     % (rel, m.group(1), keep, int(m.group(1)) - keep))
        for m in re.finditer(r"^\s*hours_to_show:\s*(\d+)\s*$", src, re.M):
            if int(m.group(1)) > keep * 24:
                warn("chart-window-exceeds-recorder",
                     "%s asks for %sh but recorder keeps %dh"
                     % (rel, m.group(1), keep * 24))


def rule_liveness_coverage(man):
    """Every capture pipeline needs a stamp and a stale detector.

    2026-08-21: SPC had 0/6 coverage while non-SPC had 6/10, which is the only
    reason the dehumidifier could stop capturing for 14 days in silence.
    """
    for name, p in sorted((man.get("pipelines") or {}).items()):
        if not p.get("stamp"):
            warn("no-liveness", "%s: writes %d slots but stamps nothing - staleness "
                 "cannot be detected even in principle" % (name, p.get("buffer_slots", 0)))
        elif not p.get("stale_detector"):
            warn("no-detector", "%s: has a stamp but no stale detector" % name)


_concurrent_ok = []


def rule_eod_collisions(man):
    """Same-second automations that actually contend, and doc drift.

    REWRITTEN 2026-08-21. The first version flagged any two automations sharing
    a trigger second, which reported the six SPC captures at 23:59:00 as a
    collision. They are not: verified that no pair writes a shared entity, and
    HA runs them concurrently without contention. Same-second alone is load,
    not a race. What matters is shared STATE:

      write/write - both set the same entity; last writer wins, silently
      read/write  - one reads what the other is writing; the reader may see
                    the old or the new value depending on scheduling

    The old rule cried about six harmless automations, which is how a rule
    teaches you to ignore it.
    """
    autos = _automations()
    seen = {}
    for name, p in (man.get("pipelines") or {}).items():
        at = p.get("at")
        if not at:
            # `at: null` is an explicit declaration that this pipeline is event-
            # or template-triggered, and re-reporting a declared fact every run
            # is the checker narrating itself. Only an UNDECLARED pipeline - no
            # `at` key at all - is worth a line, because that is a manifest that
            # has not been thought about.
            if "at" not in p:
                warn("eod-undeclared",
                     "%s: no `at` in pipelines.yaml. Declare the trigger time, or "
                     "`at: null` if it is event-triggered." % name)
            continue
        seen.setdefault(at, []).append(name)

    for at, names in sorted(seen.items()):
        if len(names) < 2:
            continue
        contend = False
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = autos.get(names[i]), autos.get(names[j])
                if not a or not b:
                    continue
                wa, wb = _writes(a), _writes(b)
                ww = wa & wb
                rw = (wa & _reads(b)) | (wb & _reads(a))
                if ww:
                    contend = True
                    fail("eod-race", "%s: %s and %s both write %s"
                         % (at, names[i], names[j], ", ".join(sorted(ww))))
                elif rw:
                    contend = True
                    warn("eod-read-write", "%s: %s and %s share %s (one reads what the "
                         "other writes)" % (at, names[i], names[j], ", ".join(sorted(rw))))
        if not contend:
            # Counted, not enumerated. CLAUDE.md's EOD section is explicit that
            # sharing a trigger second is not a problem, so one line per group
            # is a finding-shaped non-finding. The count still proves the check
            # ran, which is the only thing it was ever telling you.
            _concurrent_ok.append((at, len(names)))

    doc = text("CLAUDE.md")
    for at, names in sorted(seen.items()):
        if at and at not in doc:
            warn("eod-undocumented",
                 "%s (%s) is not in CLAUDE.md's EOD TIMING SEQUENCE"
                 % (at, ", ".join(sorted(names))))


def rule_stamp_snapshotted(man):
    """A capture stamp must come from a snapshot, not a live now().

    CLAUDE.md: EOD captures MUST snapshot with `variables:` at trigger time to
    prevent midnight-boundary re-evaluation. Until 2026-08-21 the VALUES obeyed
    that but the stamps did not - they were written as `{{ now().date() }}` at
    execution time. Six captures fire together at 23:59:00; one slipping past
    midnight would stamp tomorrow against today's data, and every staleness
    detector reads that stamp.
    """
    autos = _automations()
    for name in sorted(man.get("pipelines") or {}):
        a = autos.get(name)
        if not a:
            continue
        def rec(o):
            if isinstance(o, dict):
                svc = o.get("service") or o.get("action")
                if isinstance(svc, str) and svc.endswith("input_datetime.set_datetime"):
                    for v in (o.get("data") or {}).values():
                        if isinstance(v, str) and "now()" in v:
                            warn("stamp-not-snapshotted",
                                 "%s: stamps with a live now() instead of a variable "
                                 "snapshotted at trigger time" % name)
                for v in o.values():
                    rec(v)
            elif isinstance(o, list):
                for v in o:
                    rec(v)
        rec(a)


def rule_latched_guards(man):
    """A fixed-time guard must not read an availability-gated statistics sensor.

    2026-08-21: every capture read sensor.<x>_running_watts_24h at 23:59:00.
    The statistics platform mirrors its source's availability
    (components/statistics/sensor.py::_add_state_to_queue sets
    _attr_available before the early return), and the sources are gated on
    "appliance is running right now" - so the guard read -1 unless the
    appliance happened to be running at that second. Dehumidifier: dead 14
    days. HWH: 20 days.
    """
    for name, p in sorted((man.get("pipelines") or {}).items()):
        g = p.get("guard") or {}
        src = g.get("source")
        if not src:
            continue
        if src.endswith("_24h"):
            fail("unlatched-guard",
                 "%s: guard reads %s directly. Statistics sensors are unavailable "
                 "whenever their source is; use the _latched companion." % (name, src))


def rule_fabricated_constants():
    """No numeric-literal fallback may feed a chart, control limit or alarm.

    2026-08-21: the startup seeder's `else 459` painted a constant into three
    dehumidifier slots and stamped it as a capture. Three identical slots make
    sd = 0 by construction, which collapsed UCL and LCL onto the centre line.
    """
    src = text("packages/spc.yaml")
    for m in re.finditer(r"else\s+(\d+(?:\.\d+)?)\s*\}\}", src):
        line = src[:m.start()].count("\n") + 1
        ctx = src[max(0, m.start() - 220):m.start()]
        if re.search(r"_day_\d|set_value|seed", ctx):
            fail("fabricated-constant",
                 "packages/spc.yaml:%d: numeric fallback `else %s` near a buffer write"
                 % (line, m.group(1)))


def _shell_call_sites():
    """Every REAL shell_command call, as a list of (command, file).

    Real means a `service:` or `action:` key whose value is shell_command.<x>.
    Both spellings are in use here - HA renamed `service:` to `action:` in
    2024.8 and this config still contains both - so matching only one would
    miss half the call sites.

    NOT a regex over the JSON blob, which is what the rest of this rule uses.
    packages/energy_export_package.yaml names shell_command.daily_energy_export
    inside a warning MESSAGE as well as calling it, and a regex cannot tell a
    mention from a call. Counting mentions would make the tripwire below fire
    on healthy config on its very first run - a wrong WARN, which spends more
    trust than the gap it reports (R7).

    Measured 2026-08-24: 10 call sites, 10 distinct commands, and the regex set
    and this walker agree exactly.
    """
    out = []

    def walk(node, where):
        if isinstance(node, dict):
            for key in ("service", "action"):
                v = node.get(key)
                if isinstance(v, str) and v.startswith("shell_command."):
                    out.append((v.split(".", 1)[1], where))
            for v in node.values():
                walk(v, where)
        elif isinstance(node, list):
            for v in node:
                walk(v, where)

    seen = []
    for rel in ["automations.yaml", "scripts.yaml"] + list(config_files()):
        if rel in seen:
            continue
        seen.append(rel)
        cfg = load(rel)
        if cfg is None:
            continue
        holders = []
        if isinstance(cfg, list):
            holders = cfg
        elif isinstance(cfg, dict):
            for h in ("automation", "script"):
                b = cfg.get(h)
                if isinstance(b, dict):
                    holders += list(b.values())
                elif isinstance(b, list):
                    holders += b
        for a in holders:
            walk(a, rel)
    return out


def rule_shell_commands_guarded():
    """Every shell_command must be called, and every call guarded.

    CLAUDE.md: MUST wrap every shell_command call with ha_maintenance_mode.
    2026-08-21 found spc_seed_from_history defined but never called, and the
    guard input_boolean itself undefined - a condition on a missing entity is
    `unknown`, never equals "off", and silently disables its own automation.

    TWO KNOWN LIMITATIONS, found 2026-08-24 by scripts/test_ha_audit.py and
    recorded here rather than quietly left in place (R13):

    1. IT IS PER-NAME, NOT PER-CALL-SITE. `called - guarded` is computed over
       shell_command NAMES. If a command is guarded in one automation and
       called UNGUARDED in another, the name is already in `guarded` and this
       stays silent - and the unguarded call is precisely the dangerous one.
       The CLAUDE.md rule is per CALL; this check is per NAME.
    2. THE GUARD IS A SUBSTRING MATCH. An automation counts as guarded if its
       JSON contains "ha_maintenance_mode" anywhere - including inside a log
       message. packages/energy_export_package.yaml legitimately mentions it in
       both a condition and a warning string, so the two cases are
       indistinguishable to this check.

    Fixing either means walking the action tree per call site and confirming a
    real condition dominates the service call. Not done: the rule is still
    correct in the direction it claims (a wholly unguarded command DOES fire),
    and a half-fixed guard-detector would be worse than a documented one.

    LIMITATION 1 NOW HAS A TRIPWIRE (see the end of this function). It is
    latent today - all 10 commands have exactly one call site, so per-NAME and
    per-CALL-SITE agree - and `shell-command-multi-call` WARNs the moment that
    stops being true, which is the moment the blind spot becomes reachable.
    Proven 2026-08-24: with a second unguarded call to shell_command.ha_audit
    injected, unguarded-shell-command stayed SILENT and the tripwire fired.
    """
    declared, called, guarded = set(), set(), set()
    ents = set()
    for rel in config_files():
        cfg = load(rel) or {}
        for k in (cfg.get("shell_command") or {}):
            declared.add(k)
        for k in (cfg.get("input_boolean") or {}):
            ents.add("input_boolean.%s" % k)
        blob = json.dumps(cfg, default=str)
        called.update(re.findall(r"shell_command\.([a-z0-9_]+)", blob))
        # A guard inside a script counts. script.ha_audit holds the guard and
        # calls the shell_command, which the automation-only scan missed.
        callers = list(cfg.get("automation") or [])
        callers += list((cfg.get("script") or {}).values())
        for a in callers:
            b = json.dumps(a, default=str)
            if "shell_command." in b and "ha_maintenance_mode" in b:
                guarded.update(re.findall(r"shell_command\.([a-z0-9_]+)", b))
    # automations.yaml AND scripts.yaml. Leaving scripts.yaml out meant a
    # shell_command called only from a UI script would be reported dead, and
    # its guard would not count -- the rule would have been wrong in both
    # directions. Empty today, which is exactly when a blind spot is cheap to
    # close (checked 2026-08-22: zero shell_command references in scripts.yaml).
    for rel in ("automations.yaml", "scripts.yaml"):
        cfg = load(rel) or ([] if rel == "automations.yaml" else {})
        blob = json.dumps(cfg, default=str)
        called.update(re.findall(r"shell_command\.([a-z0-9_]+)", blob))
        entries = cfg if isinstance(cfg, list) else list(cfg.values())
        for a in entries:
            b = json.dumps(a, default=str)
            if "shell_command." in b and "ha_maintenance_mode" in b:
                guarded.update(re.findall(r"shell_command\.([a-z0-9_]+)", b))

    if "input_boolean.ha_maintenance_mode" not in ents:
        fail("guard-entity-missing",
             "input_boolean.ha_maintenance_mode is referenced as a guard but not defined - "
             "a condition on a missing entity is `unknown` and never matches 'off'")
    for k in sorted(declared - called):
        warn("dead-shell-command", "shell_command.%s is declared but never called" % k)
    for k in sorted(called - guarded):
        warn("unguarded-shell-command",
             "shell_command.%s is called without an ha_maintenance_mode guard" % k)

    # --- TRIPWIRE for this rule's own blind spot (added 2026-08-24) ---------
    # Limitation 1 above is LATENT, not active: every command has exactly one
    # call site today (10 of 10, measured), so per-NAME and per-CALL-SITE agree
    # and nothing is currently mis-reported. It becomes real the moment a
    # command acquires a second call site - and that second call is precisely
    # the one likely to be unguarded, because the first one already satisfies
    # the name-level check and hides it.
    #
    # WHY A TRIPWIRE INSTEAD OF THE REAL FIX. Per-call-site domination analysis
    # has to understand three guard shapes already in use here, two of which
    # guard by NOT RUNNING rather than by a positive condition:
    #   choose + call in default:   inversion  (7 sites)
    #   if ... stop: then call      early exit (2 sites)
    #   automation-level condition:            (1 site, nightly_buffer_backup)
    # Getting polarity backwards inverts the rule - it would pass unguarded
    # calls and FAIL guarded ones - and a naive "condition before the call"
    # check would false-FAIL 8 of the 10 healthy sites. A wrong FAIL costs more
    # than this under-detection. So: make the gap announce itself, and build
    # the analysis only if it ever fires.
    counts = {}
    sites = _shell_call_sites()
    for cmd, _where in sites:
        counts[cmd] = counts.get(cmd, 0) + 1
    for cmd in sorted(counts):
        if counts[cmd] > 1:
            where = ", ".join(sorted(set(w for c, w in sites if c == cmd)))
            warn("shell-command-multi-call",
                 "shell_command.%s is called from %d places (%s). The guard "
                 "check above is per-NAME, so if any ONE of those calls is "
                 "unguarded it will NOT be reported - the guarded call masks "
                 "it. Check each call site by hand, or implement per-call-site "
                 "domination analysis (see this rule's limitations note)."
                 % (cmd, counts[cmd], where))


def rule_buffer_health(man):
    """Repeated or empty buffers. The 459 x 3 signature."""
    rs = P(".storage", "core.restore_state")
    if not os.path.exists(rs):
        return
    with io.open(rs, encoding="utf-8") as fh:
        st = {(i.get("state") or {}).get("entity_id"): str((i.get("state") or {}).get("state"))
              for i in json.load(fh).get("data", [])}
    for name, p in sorted((man.get("pipelines") or {}).items()):
        vals = []
        for e in (p.get("buffer") or []):
            try:
                vals.append(float(st.get(e, "nan")))
            except ValueError:
                pass
        # The "no data" value is per-pipeline, not universally 0. Every SPC
        # buffer uses 0, but capture_daily_water_overnight inverts it: 0.00
        # gal/h is a PERFECT night and -1 means "no night recorded". Assuming
        # 0 here reported "all 7 slots are 0" for a buffer holding 0.0 and six
        # -1s - wrong on the facts and on the meaning. Declared in the manifest.
        sentinel = float(p.get("empty_sentinel", 0))
        live = [v for v in vals if v == v and v != sentinel]
        benign = p.get("benign_repeat")
        if len(live) >= 2 and len(set(live)) == 1 and (
                benign is None or live[0] != float(benign)):
            fail("repeated-buffer",
                 "%s: %d live slots all equal %g - a repeated value, not a sample"
                 % (name, len(live), live[0]))
        elif not live and vals and p.get("season", "none") == "none":
            warn("empty-buffer", "%s: all %d slots read the empty sentinel (%g)"
                 % (name, len(vals), sentinel))


def rule_backup_coverage(man):
    """Every buffer entity must be backed up somewhere.

    2026-08-21: shell_command.backup_input_numbers (weekly, Sun 04:00) is a
    hand-maintained list of ~57 states() calls. It predates the SPC package and
    was never extended, so it covered the HDD/CDD/runtime buffers and none of
    the 42 SPC running-watts slots, none of cooling_kwh_cdd, and no capture
    stamps at all. A hand-maintained list of entities is the same duplication
    that let the other five copies drift; scripts/spc_buffer_export.py reads
    pipelines.yaml instead, so it cannot fall behind without this audit failing.
    """
    legacy = ""
    for rel in ("configuration.yaml",):
        cfg = load(rel) or {}
        legacy += str((cfg.get("shell_command") or {}).get("backup_input_numbers", ""))
    # RETIRED 2026-08-23. This rule existed to track drift between a legacy
    # partial backup and the manifest-driven complete one. The legacy command is
    # gone, so there is no drift to report - and a rule that keeps talking about
    # something that no longer exists is the noise this audit was just cleaned
    # of. Kept rather than deleted so that re-adding the command re-arms the
    # check automatically.
    if not legacy:
        return
    wanted = {e for p in (man.get("pipelines") or {}).values()
              for e in (p.get("buffer") or []) if "{{" not in e}
    gap = sorted(e for e in wanted if e not in legacy)
    if gap:
        warn("legacy-backup-drift",
             "shell_command.backup_input_numbers covers only %d/%d buffer "
             "entities - a strict subset of spc_buffer_export.py, which covers "
             "all %d. CLAUDE.md's retirement criterion (a few nights of "
             "manifest-driven history) is met. Retire it, or delete this rule."
             % (len(wanted) - len(gap), len(wanted), len(wanted)))



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="failures only")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--log", metavar="FILE", help="append the human report to FILE")
    args = ap.parse_args()

    man = load("pipelines.yaml")
    if not man:
        sys.exit("pipelines.yaml not found under %s" % CONFIG)
    ents = known_entities()

    # Union in the LIVE state machine when a token is reachable. Strictly
    # additive: it can only remove false positives, never create findings, and
    # the audit stays fully offline when there is no token (its whole design).
    #
    # 2026-08-24: rule_entity_refs_resolve reported sun.sun x4 as unresolved on
    # the Energy Performance dashboard. sun.sun exists and reads above_horizon.
    # It has no entity-registry row (core integrations with no config entry do
    # not get one) and does not restore, so the offline set cannot see it, and
    # neither can any amount of YAML parsing. A checker that cries wolf about a
    # core entity spends the trust the real findings need (R7).
    _live, _live_err = _live_states()
    if _live:
        ents |= set(s["entity_id"] for s in _live if s.get("entity_id"))

    rule_manifest_matches_config(man)
    rule_entities_resolve(man, ents)
    rule_unique_id_not_entity_id()
    rule_liveness_coverage(man)
    rule_generated_docs(ents)
    rule_doc_ids(ents)
    rule_entity_refs_resolve(ents)
    rule_choose_has_default()
    rule_fabricated_limit_constants()
    rule_chart_window_vs_recorder()
    rule_statistics_buffer(_live_states())
    rule_eod_collisions(man)
    rule_stamp_snapshotted(man)
    rule_latched_guards(man)
    rule_fabricated_constants()
    rule_shell_commands_guarded()
    rule_buffer_health(man)
    rule_backup_coverage(man)

    if _concurrent_ok:
        info("eod-concurrent",
             "%d same-second groups checked, no shared state in any (%s)"
             % (len(_concurrent_ok),
                ", ".join("%s x%d" % (a, n) for a, n in sorted(_concurrent_ok))))

    order = {"FAIL": 0, "WARN": 1, "INFO": 2}
    findings.sort(key=lambda f: (order[f[0]], f[1], f[2]))
    n = {"FAIL": 0, "WARN": 0, "INFO": 0}
    for sev, _r, _m in findings:
        n[sev] += 1
    npipe = len(man.get("pipelines") or {})
    summary = ("%d FAIL, %d WARN, %d INFO across %d pipelines"
               % (n["FAIL"], n["WARN"], n["INFO"], npipe))

    # --log is independent of the output mode, so the human-readable report is
    # still archived when HA calls this with --json.
    if args.log:
        try:
            d = os.path.dirname(args.log)
            if d:
                os.makedirs(d, exist_ok=True)
            with io.open(args.log, "a", encoding="utf-8") as fh:
                fh.write("\n===== %s =====\n" % datetime.now().isoformat(timespec="seconds"))
                for f in findings:
                    fh.write("%-5s %-24s %s\n" % f)
                fh.write(summary + "\n")
        except OSError as exc:
            print("WARN could not write log: %s" % exc, file=sys.stderr)

    if args.json:
        # Key names are a contract with script.ha_audit in packages/audit.yaml.
        # Parsing JSON beats scraping prose: a reworded finding cannot silently
        # break the dashboard the way a regex over the summary line would.
        json.dump({"fail": n["FAIL"], "warn": n["WARN"], "info": n["INFO"],
                   "pipelines": npipe, "summary": summary,
                   "ran_at": datetime.now().isoformat(timespec="seconds"),
                   "findings": [{"severity": a, "rule": b, "message": c}
                                for a, b, c in findings]},
                  sys.stdout, separators=(",", ":"))
        sys.stdout.write("\n")
        return 1 if n["FAIL"] else 0

    for sev, rule, msg in findings:
        if args.quiet and sev != "FAIL":
            continue
        print("%-5s %-24s %s" % (sev, rule, msg))
    print("\n" + summary)
    return 1 if n["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
