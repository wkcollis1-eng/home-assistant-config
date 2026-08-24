#!/usr/bin/env python3
"""
validate_ha.py — deterministic, parse-based validator for Home Assistant YAML.

This is NOT a grep checker. It actually parses the file:
  Layer 0  encoding / whitespace hygiene (tabs, BOM, trailing ws; CRLF is INFO)
  Layer 1  YAML structural parse with HA custom tags + duplicate-key detection
  Layer 2  Jinja2 AST parse of EVERY embedded template (catches {% if %}/{% endif %}
           imbalance, bad filter syntax, unterminated blocks, etc.)
  Layer 3  HA-specific lint heuristics on the PARSED tree (filter defaults,
           entity-id shape, trigger.id cross-refs, required automation keys)
  Layer 4  (optional, authoritative) `hass --script check_config` if hass is on PATH

Exit code 0 = PASS (no FAILs), 1 = FAIL (one or more FAILs), 2 = tool/usage error.

A clean parse is necessary but NOT sufficient: it does not confirm that entity
references resolve, that integration schemas accept the keys, or that templates
evaluate without runtime errors. Only Layer 4 (hass check_config) certifies that.
The verdict banner says which level of assurance was actually reached.
"""

import argparse
import io
import os
import re
import shutil
import subprocess
import sys

try:
    import yaml
except ImportError:
    print("FAIL  [env] PyYAML not installed. `pip install pyyaml`")
    sys.exit(2)

try:
    import jinja2
    _JINJA_ENV = jinja2.Environment()
except ImportError:
    _JINJA_ENV = None  # Layer 2 will be skipped with a WARN


# --------------------------------------------------------------------------- #
# Configurable allow-lists (project-specific). Edit these, not the logic.
# --------------------------------------------------------------------------- #
# Entity IDs that look like typos but are INTENTIONAL and must never be flagged.
PROTECTED_ENTITY_IDS = {
    "sensor.shelly_plus_uni_voltge",  # intentional, do not "correct"
}

# Jinja globals/functions that are legitimately call-able and should not be
# mistaken for undefined names by the heuristics.
HA_TEMPLATE_GLOBALS = {
    "states", "state_attr", "is_state", "is_state_attr", "now", "utcnow",
    "as_timestamp", "as_datetime", "as_local", "strptime", "relative_time",
    "expand", "device_id", "device_attr", "area_id", "area_name",
    "float", "int", "namespace", "range", "min", "max", "average", "iif",
    "has_value", "state_translated",
}


class Finding:
    __slots__ = ("level", "tag", "msg", "line")

    def __init__(self, level, tag, msg, line=None):
        self.level = level  # FAIL | WARN | INFO
        self.tag = tag
        self.msg = msg
        self.line = line

    def render(self):
        loc = f" (line {self.line})" if self.line else ""
        return f"{self.level:<4}  [{self.tag}] {self.msg}{loc}"


# --------------------------------------------------------------------------- #
# YAML loader: register HA custom tags + detect duplicate keys
# --------------------------------------------------------------------------- #
class _OpaqueTag:
    """Stand-in for a value produced by an HA-only tag (!include, !secret, ...)."""
    def __init__(self, tag, value):
        self.tag = tag
        self.value = value


HA_TAGS = [
    "!include", "!include_dir_list", "!include_dir_merge_list",
    "!include_dir_named", "!include_dir_merge_named",
    "!secret", "!env_var", "!input",
]


class DupCheckLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently
    overwriting them (HA's #1 silent-corruption failure mode)."""
    duplicate_keys = []  # list of (key, line)


def _construct_mapping_with_dupcheck(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            DupCheckLoader.duplicate_keys.append(
                (key, key_node.start_mark.line + 1)
            )
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


def _opaque_from_node(loader, node):
    if isinstance(node, yaml.ScalarNode):
        val = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        val = loader.construct_sequence(node)
    else:
        val = loader.construct_mapping(node)
    return _OpaqueTag(node.tag, val)


def _ha_tag_constructor(loader, node):              # add_constructor: 2 args
    return _opaque_from_node(loader, node)


def _ha_multi_constructor(loader, tag_suffix, node):  # add_multi_constructor: 3 args
    return _opaque_from_node(loader, node)


def _install_loader():
    DupCheckLoader.duplicate_keys = []
    DupCheckLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _construct_mapping_with_dupcheck,
    )
    for tag in HA_TAGS:
        DupCheckLoader.add_constructor(tag, _ha_tag_constructor)
    # multi-constructor catches any HA tag we didn't enumerate, e.g. !include_dir_*
    DupCheckLoader.add_multi_constructor("!", _ha_multi_constructor)


# --------------------------------------------------------------------------- #
# Layer 0 — encoding / whitespace hygiene
# --------------------------------------------------------------------------- #
def layer0_hygiene(raw_bytes, findings):
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        findings.append(Finding(
            "WARN", "encoding",
            "UTF-8 BOM at start of file; HA reads it but some tools choke. "
            "Consider stripping."))
    text = raw_bytes.decode("utf-8", errors="replace")
    has_crlf = "\r\n" in text
    if has_crlf:
        # Bill's Samba/Windows workflow produces CRLF. HA tolerates it.
        findings.append(Finding(
            "INFO", "encoding",
            "CRLF line endings detected (expected for the Windows/Samba "
            "workflow). HA accepts these; reported for awareness only."))
    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        body = line.rstrip("\r")
        if "\t" in body:
            findings.append(Finding(
                "FAIL", "whitespace",
                "TAB character in indentation/content — YAML forbids tabs for "
                "indentation; this will break the parse.", i))
        if body != body.rstrip():
            findings.append(Finding(
                "WARN", "whitespace", "trailing whitespace.", i))
    return text


# --------------------------------------------------------------------------- #
# Layer 1 — YAML structural parse + duplicate keys
# --------------------------------------------------------------------------- #
def layer1_yaml(text, findings):
    _install_loader()
    try:
        data = yaml.load(text, Loader=DupCheckLoader)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        line = (mark.line + 1) if mark else None
        prob = getattr(e, "problem", str(e)) or str(e)
        ctx = getattr(e, "context", "") or ""
        findings.append(Finding(
            "FAIL", "yaml-parse",
            f"{ctx + ': ' if ctx else ''}{prob}".strip(), line))
        return None
    for key, line in DupCheckLoader.duplicate_keys:
        findings.append(Finding(
            "FAIL", "duplicate-key",
            f"duplicate mapping key '{key}' — second definition silently "
            f"overwrites the first.", line))
    if data is None:
        findings.append(Finding("WARN", "yaml-parse", "file parsed to empty/null."))
    return data


# --------------------------------------------------------------------------- #
# Layer 2 — Jinja2 AST parse of every embedded template
# --------------------------------------------------------------------------- #
_JINJA_MARKER = re.compile(r"\{\{|\{%|\{#")


def _walk_strings(node, path, out):
    if isinstance(node, str):
        out.append((path, node))
    elif isinstance(node, _OpaqueTag):
        _walk_strings(node.value, path, out)
    elif isinstance(node, dict):
        for k, v in node.items():
            _walk_strings(v, f"{path}.{k}" if path else str(k), out)
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            _walk_strings(v, f"{path}[{i}]", out)


def layer2_jinja(data, findings):
    if data is None:
        return
    if _JINJA_ENV is None:
        findings.append(Finding(
            "WARN", "jinja", "Jinja2 not installed; template AST parse skipped."))
        return
    strings = []
    _walk_strings(data, "", strings)
    checked = 0
    for path, s in strings:
        if not _JINJA_MARKER.search(s):
            continue
        checked += 1
        try:
            _JINJA_ENV.parse(s)
        except jinja2.TemplateSyntaxError as e:
            snippet = s.strip().splitlines()[0][:70] if s.strip() else ""
            findings.append(Finding(
                "FAIL", "jinja",
                f"template syntax error at '{path}': {e.message} "
                f"[near: {snippet!r}]"))
    findings.append(Finding(
        "INFO", "jinja", f"{checked} embedded template(s) AST-parsed."))


# --------------------------------------------------------------------------- #
# Layer 3 — HA-specific lint heuristics (regex over PARSED template strings)
# --------------------------------------------------------------------------- #
# Bare numeric filters with NO argument list are the high-signal hardening miss.
# (| float(0) is fine; | float is the risk. round() w/o args flagged separately.)
_RE_BARE_FLOAT = re.compile(r"\|\s*float\b(?!\s*\()")
_RE_BARE_INT = re.compile(r"\|\s*int\b(?!\s*\()")
_RE_ENTITY = re.compile(r"\b(states|is_state|state_attr|is_state_attr|has_value)"
                        r"\(\s*'([^']+)'")
_RE_ENTITY_DQ = re.compile(r"\b(states|is_state|state_attr|is_state_attr|has_value)"
                           r'\(\s*"([^"]+)"')
_VALID_DOMAIN_ENTITY = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")


def layer3_lint(data, findings):
    if data is None:
        return
    strings = []
    _walk_strings(data, "", strings)
    bare_float = bare_int = 0
    for path, s in strings:
        if not _JINJA_MARKER.search(s):
            continue
        if _RE_BARE_FLOAT.search(s):
            bare_float += 1
            findings.append(Finding(
                "WARN", "filter-default",
                f"`| float` without explicit default at '{path}'. Use "
                f"`| float(0)` (or float(none)) so unavailable states don't "
                f"raise."))
        if _RE_BARE_INT.search(s):
            bare_int += 1
            findings.append(Finding(
                "WARN", "filter-default",
                f"`| int` without explicit default at '{path}'. Use `| int(0)`."))
        for rex in (_RE_ENTITY, _RE_ENTITY_DQ):
            for m in rex.finditer(s):
                eid = m.group(2)
                if eid in PROTECTED_ENTITY_IDS:
                    continue
                # Skip templated entity ids (built from variables) — can't judge.
                if "{" in eid or "~" in eid:
                    continue
                if not _VALID_DOMAIN_ENTITY.match(eid):
                    findings.append(Finding(
                        "WARN", "entity-id",
                        f"entity id '{eid}' at '{path}' is not lowercase "
                        f"domain.object_id shape."))
    return


# --------------------------------------------------------------------------- #
# Layer 3b — automations-specific structural checks
# --------------------------------------------------------------------------- #
def layer3b_automations(data, findings):
    """If the parsed root is a list of automations, enforce required keys and
    cross-check trigger.id references against defined trigger ids."""
    if not isinstance(data, list):
        return
    looks_like_autos = any(
        isinstance(item, dict) and ("trigger" in item or "triggers" in item or "action" in item or "actions" in item)
        for item in data
    )
    if not looks_like_autos:
        return
    for idx, auto in enumerate(data):
        if not isinstance(auto, dict):
            continue
        label = auto.get("alias") or auto.get("id") or f"[index {idx}]"
        for req in ("id", "alias"):
            if req not in auto:
                findings.append(Finding(
                    "WARN", "automation",
                    f"automation '{label}' missing '{req}:' (recommended for "
                    f"stable referencing/UI)."))
        # HA accepts both legacy (trigger/action/condition) and new
        # (triggers/actions/conditions) keys; require one of each pair.
        if "trigger" not in auto and "triggers" not in auto:
            findings.append(Finding(
                "FAIL", "automation",
                f"automation '{label}' has no trigger(s)."))
        if "action" not in auto and "actions" not in auto:
            findings.append(Finding(
                "FAIL", "automation",
                f"automation '{label}' has no action(s)."))
        # trigger.id cross-reference
        trigs = auto.get("triggers") or auto.get("trigger") or []
        if isinstance(trigs, dict):
            trigs = [trigs]
        # INFO: a 'for:' duration on a state trigger watching an externally-
        # controlled switch resets on any momentary drop (integration glitch),
        # silently restarting long runtime caps. Prefer a debounced sensor.
        for _t in trigs:
            if not isinstance(_t, dict):
                continue
            if (_t.get("platform") == "state" or _t.get("trigger") == "state") \
                    and "for" in _t:
                _eids = _t.get("entity_id")
                _eids = [_eids] if isinstance(_eids, str) else (_eids or [])
                _sw = [e for e in _eids
                       if isinstance(e, str) and e.startswith("switch.")]
                if _sw:
                    findings.append(Finding(
                        "INFO", "logic-timer-basis",
                        f"automation '{label}': state trigger with 'for:' on "
                        f"switch {_sw}. An externally-controlled switch can "
                        f"momentarily drop and silently reset the 'for:' timer; "
                        f"base long runtime caps on a debounced sensor "
                        f"(e.g. a delay_off binary_sensor)."))
        defined_ids = {t.get("id") for t in trigs
                       if isinstance(t, dict) and t.get("id")}
        referenced = set()
        for _, s in [(p, v) for p, v in _collect(auto)]:
            for m in re.finditer(r"trigger\.id\s*==\s*'([^']+)'", s):
                referenced.add(m.group(1))
            for m in re.finditer(r'trigger\.id\s*==\s*"([^"]+)"', s):
                referenced.add(m.group(1))
        for ref in referenced - defined_ids:
            findings.append(Finding(
                "WARN", "trigger-id",
                f"automation '{label}' references trigger.id '{ref}' that is "
                f"not defined among its trigger ids {sorted(defined_ids)}."))


def _collect(node, out=None):
    if out is None:
        out = []
    if isinstance(node, str):
        out.append((None, node))
    elif isinstance(node, _OpaqueTag):
        _collect(node.value, out)
    elif isinstance(node, dict):
        for v in node.values():
            _collect(v, out)
    elif isinstance(node, (list, tuple)):
        for v in node:
            _collect(v, out)
    return out


# --------------------------------------------------------------------------- #
# Layer 3c — higher-order logic anti-patterns (regression guards for footguns
# found in real debugging: reboot-fragile / single-writer timing guards).
# --------------------------------------------------------------------------- #
_RE_LAST_TRIGGERED = re.compile(r"last_triggered")
_RE_TIME_MATH = re.compile(r"now\(\)|utcnow\(\)|as_timestamp|total_seconds|timedelta")


def layer3c_logic(data, findings):
    """Flag timing guards built on automation.*.last_triggered.

    Two real failure modes this caused in production:
      (1) last_triggered resets to unknown/None on every HA restart, so an
          elapsed-time guard FAILS OPEN immediately after a reboot.
      (2) it only observes the firings of that ONE automation. If the guarded
          entity (e.g. a switch) is also turned off by other automations or
          manually, those stops are invisible to the guard -> short-cycle.
    Fix pattern: stamp an input_datetime on the actual state change and read
    that, so every path is captured and the value survives restarts.
    """
    if data is None:
        return
    strings = []
    _walk_strings(data, "", strings)
    for path, s in strings:
        if not _JINJA_MARKER.search(s):
            continue
        if _RE_LAST_TRIGGERED.search(s) and _RE_TIME_MATH.search(s):
            findings.append(Finding(
                "WARN", "logic-timing",
                f"timing guard uses 'last_triggered' with time math at "
                f"'{path}'. It resets to unknown on HA restart (fails open) and "
                f"only sees one automation's firings; if the target entity is "
                f"changed by other automations or manually, those events are "
                f"missed. Stamp an input_datetime on the state change instead."))
    return


# --------------------------------------------------------------------------- #
# Layer 3d — statistics precision vs charted signal (SPC quantization)
# --------------------------------------------------------------------------- #
_MEAN_CHARS = {"mean", "average_linear", "average_step", "average_timeless"}


def _find_prec0_means(node, out):
    if isinstance(node, dict):
        if (node.get("platform") == "statistics"
                and node.get("precision") == 0
                and node.get("state_characteristic") in _MEAN_CHARS):
            uid = node.get("unique_id")
            out.append((f"sensor.{uid}" if uid else None, node.get("name")))
        for v in node.values():
            _find_prec0_means(v, out)
    elif isinstance(node, (list, tuple)):
        for v in node:
            _find_prec0_means(v, out)


def layer3d_precision(data, findings):
    """INFO: a statistics *mean* stored at precision: 0 quantizes sub-unit
    day-to-day variation. If it feeds an SPC / sigma / control-limit chart, the
    signal (and the computed sigma) can collapse to a flat line. Use 1-2 dp for
    charted means. (Advisory: fires on any precision:0 mean-type characteristic;
    it does not trace the downstream chart, which may be in another file.)"""
    if data is None:
        return
    cands = []
    _find_prec0_means(data, cands)
    for eid, name in cands:
        findings.append(Finding(
            "INFO", "logic-precision",
            f"statistics mean '{name or eid or '?'}' has precision: 0. Integer "
            f"precision quantizes sub-unit variation; if it feeds an SPC / sigma "
            f"/ control-limit chart the day-to-day signal can collapse. Use "
            f"precision: 1-2 for charted means."))
    return


# --------------------------------------------------------------------------- #
# Layer 4 — authoritative hass check_config (optional)
# --------------------------------------------------------------------------- #
def layer4_hass(config_dir, findings):
    hass = shutil.which("hass")
    if not hass:
        return False
    try:
        proc = subprocess.run(
            [hass, "--script", "check_config", "-c", config_dir],
            capture_output=True, text=True, timeout=600)
    except Exception as e:
        findings.append(Finding("WARN", "hass", f"hass check_config failed to run: {e}"))
        return False
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0 and "ERROR" not in out:
        findings.append(Finding("INFO", "hass",
                                "hass --script check_config returned clean."))
    else:
        for ln in out.splitlines():
            if "ERROR" in ln or "Invalid config" in ln or "not found" in ln.lower():
                findings.append(Finding("FAIL", "hass", ln.strip()))
    return True


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def validate_file(path, run_hass=False, config_dir=None):
    findings = []
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        print(f"FAIL  [io] cannot read {path}: {e}")
        return 2, [], False

    text = layer0_hygiene(raw, findings)
    data = layer1_yaml(text, findings)
    layer2_jinja(data, findings)
    layer3_lint(data, findings)
    layer3b_automations(data, findings)
    layer3c_logic(data, findings)
    layer3d_precision(data, findings)

    hass_ran = False
    if run_hass:
        cfg = config_dir or os.path.dirname(os.path.abspath(path)) or "."
        hass_ran = layer4_hass(cfg, findings)

    return None, findings, hass_ran


def print_report(path, findings, hass_ran, strict=False):
    fails = [f for f in findings if f.level == "FAIL"]
    warns = [f for f in findings if f.level == "WARN"]
    infos = [f for f in findings if f.level == "INFO"]

    print("=" * 68)
    print(f"HA CONFIG VALIDATION — {os.path.basename(path)}")
    print("=" * 68)
    for f in fails:
        print(f.render())
    for f in warns:
        print(f.render())
    for f in infos:
        print(f.render())
    print("-" * 68)
    print(f"FAIL: {len(fails)}   WARN: {len(warns)}   INFO: {len(infos)}"
          f"{'   [strict: WARN blocks]' if strict else ''}")

    blocking = bool(fails) or (strict and bool(warns))
    if blocking:
        why = "FAIL(s)" if fails else "WARN(s) under --strict"
        verdict = (f"FAIL — NOT READY FOR DEPLOYMENT ({why}). "
                   f"Resolve and re-run.")
    elif not hass_ran:
        verdict = ("PASS (parse-clean) — structurally valid YAML + Jinja. "
                   "NOT YET HA-certified: entity refs, integration schemas, and "
                   "runtime template eval are unverified. Run with --hass (or "
                   "`hass --script check_config` on the HA host) before "
                   "deployment for full assurance.")
    else:
        verdict = "PASS (HA-certified) — hass check_config clean. Ready for restart."
    print("VERDICT: " + verdict)
    print("=" * 68)
    return 1 if blocking else 0


def main():
    ap = argparse.ArgumentParser(description="Deterministic HA YAML validator.")
    ap.add_argument("files", nargs="+", help="YAML file(s) to validate.")
    ap.add_argument("--hass", action="store_true",
                    help="Also run `hass --script check_config` (authoritative).")
    ap.add_argument("--config-dir", default=None,
                    help="HA config dir for --hass (defaults to file's dir).")
    ap.add_argument("--strict", action="store_true",
                    help="Treat WARNs as blocking (deployment gate).")
    args = ap.parse_args()

    overall = 0
    for path in args.files:
        _, findings, hass_ran = validate_file(
            path, run_hass=args.hass, config_dir=args.config_dir)
        rc = print_report(path, findings, hass_ran, strict=args.strict)
        overall = max(overall, rc)
    sys.exit(overall)


if __name__ == "__main__":
    main()
