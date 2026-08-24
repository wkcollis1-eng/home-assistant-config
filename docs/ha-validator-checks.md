# Check Catalog & Extension Guide

Read this when a finding's intent is unclear, or when adding/tuning a rule in
`scripts/validate_ha.py`. Findings are tagged so you can map a log line straight
to the rule that produced it.

## Severity model

- **FAIL** — will (or very likely will) prevent the config from loading, or
  silently corrupts it. Blocks deployment always.
- **WARN** — a hardening or correctness risk that HA may tolerate but that has
  bitten this project before (most often missing filter defaults causing
  template errors when a source entity goes `unavailable`). Blocks only under
  `--strict`.
- **INFO** — context, not a defect (CRLF, template count, hass-clean).

## Checks by tag

### `[whitespace]` (Layer 0)
- **FAIL** on any TAB in a line body. YAML forbids tabs for indentation; even a
  tab inside content is treated as suspect because it almost always indicates a
  paste/edit accident. A tab aborts the YAML parse, which also short-circuits
  Layers 1–3 — so fix tabs first, then re-run to see the rest.
- **WARN** on trailing whitespace (cosmetic; harmless to HA).

### `[encoding]` (Layer 0)
- **WARN** on a UTF-8 BOM (HA tolerates it; some external tools don't).
- **INFO** on CRLF — expected for the Windows/Samba workflow.

### `[yaml-parse]` (Layer 1)
- **FAIL** on any structural YAML error, with the line and PyYAML's own problem
  description. This is the authoritative "the file is not valid YAML" signal.

### `[duplicate-key]` (Layer 1)
- **FAIL** on a repeated mapping key at the same level. This is HA's nastiest
  silent failure: standard loaders keep the *last* definition and drop the rest
  with no error, so half a block can vanish. The custom loader records every
  duplicate with its line. Common real causes here: pasting a new
  `input_number`/archive entry whose key already exists, or two template sensors
  sharing a `unique_id` (note: `unique_id` collisions are a registry problem HA
  reports at runtime, not a YAML duplicate-key — Layer 4 catches those).

### `[jinja]` (Layer 2)
- **FAIL** on a Jinja2 template syntax error, reported with the tree path
  (e.g. `template[1].sensor[153].state`) and Jinja's own message. Catches
  unbalanced `{% if/for/set %}` blocks, unterminated `{{ }}`/`{# #}`, bad filter
  syntax. The INFO line reports how many templates were AST-parsed.
- The walker descends through `!include`/`!secret` opaque values too, so a
  template embedded in a tagged value is still checked if present inline.

### `[filter-default]` (Layer 3)
- **WARN** on `| float` or `| int` with **no** argument list. When the source
  entity is `unavailable`/`unknown`, a bare numeric filter raises and the whole
  template errors. The fix is an explicit default: `| float(0)` (or
  `| float(none)` when you want to branch on missing), `| int(0)`. The check is
  deliberately narrow — `| float(0)` is *not* flagged. `| round(1)` is precision,
  not a default, so it is not treated as a hardening miss.

### `[entity-id]` (Layer 3)
- **WARN** when an id passed to `states()/is_state()/state_attr()/has_value()` is
  not lowercase `domain.object_id` shape. Templated ids (built from variables) and
  whitelisted ids (see `PROTECTED_ENTITY_IDS`) are skipped.
  NOTE 2026-08-24: that whitelist holds exactly one id,
  `sensor.shelly_plus_uni_voltge`, which does not exist — not in the 1,857
  known ids, not in any YAML, and no Shelly Plus Uni device is installed. The
  entry was inert even when the device was present, because this check only
  flags ids of the wrong SHAPE and that id is well-formed. Left in
  `scripts/validate_ha.py` rather than removed: that file is a vendored copy of
  the `homeassistant-config-validator` skill (CLAUDE.md KNOWN DRIFT RISK) and
  editing it widens the divergence for no functional gain.

### `[automation]` / `[trigger-id]` (Layer 3b — runs when the root is a list)
- **WARN** on an automation missing `id:` or `alias:` (recommended for stable UI
  referencing).
- **FAIL** on an automation with no trigger(s) or no action(s). Both legacy
  (`trigger`/`action`) and new (`triggers`/`actions`) key names are accepted.
- **WARN** when a `trigger.id == '...'` reference in a template/condition doesn't
  match any `id:` defined on that automation's triggers (typo guard).

### `[hass]` (Layer 4, only with `--hass`)
- **INFO** when `hass --script check_config` returns clean.
- **FAIL** for each ERROR / "Invalid config" / "not found" line it emits. This is
  the authoritative layer; its result drives the "HA-certified" verdict.

## Extending the validator

All project-specific knobs are near the top of `scripts/validate_ha.py`:

- `PROTECTED_ENTITY_IDS` — entity ids that look like typos but are intentional.
  Add to this set rather than weakening the entity-id heuristic.
- `HA_TAGS` — enumerated HA custom tags. The `add_multi_constructor("!", ...)`
  fallback already catches any `!`-prefixed tag, so you only add here for
  documentation/clarity.
- `HA_TEMPLATE_GLOBALS` — reserved for future name-resolution heuristics; not
  load-bearing today.

To add a new lint rule, follow the existing pattern: walk the parsed tree with
`_walk_strings`, match on the template string, and append a `Finding(level, tag,
msg, line=None)`. Keep the tag short and stable so log lines stay greppable. Add
a row to this catalog and a line to the SKILL.md table.

## Known limits (don't over-claim)

- Without `--hass`, nothing here confirms an entity *exists*, that an integration
  accepts an option, or that a template evaluates without a runtime error. A
  parse-clean PASS is necessary but not sufficient.
- Cross-file references (a template in configuration.yaml pointing at an entity
  defined via an `!include`d file) are not resolved by Layers 0–3; that's Layer
  4's job.
- `unique_id` collisions across template entities surface at HA runtime, not as a
  YAML duplicate-key. Use `--hass` to catch them.

## Layer 3c — logic anti-patterns (`logic-timing`)

Regression guards for higher-order logic errors that parse clean but misbehave
at runtime. Currently one rule:

- `logic-timing` (WARN) — a Jinja string that references `last_triggered` **and**
  does time math (`now()`, `as_timestamp`, `total_seconds`, `timedelta`). This is
  the short-cycle-guard footgun: `last_triggered` resets to unknown on HA restart
  (elapsed-time guard fails open) and only reflects *one* automation's firings, so
  any other automation/manual change to the guarded entity is invisible. Fix by
  stamping an `input_datetime` on the entity's state change and reading that.
  Detection is intentionally narrow (both signals required) to stay false-positive
  free; verified zero hits on the production config after the fix.

Two further INFO rules (advisory, never block `--strict`):

- `logic-timer-basis` (INFO, in `layer3b_automations`) — a state trigger with a
  `for:` duration watching a `switch.*` entity. An externally-controlled switch
  can momentarily drop (integration glitch) and silently reset the `for:` timer,
  so a long runtime cap can overrun (observed: a 150-min cap that ran 248 min).
  Base long caps on a debounced/derived sensor instead.
- `logic-precision` (INFO, `layer3d_precision`) — a `statistics` sensor with a
  mean-type `state_characteristic` stored at `precision: 0`. Integer precision
  quantizes sub-unit day-to-day variation; if it feeds an SPC/σ/control-limit
  chart the signal collapses to a flat line. Advisory: it flags any precision:0
  mean and does not trace the downstream chart (which may live in another file),
  so treat it as a prompt to check, not proof of a defect.

The remaining items in the SKILL.md "Logic-error review checklist" are *not*
statically detectable (they need history, cross-entity dataflow, or statistical
context) and are deliberately left as human/AI review steps rather than rules,
to keep the gate free of noisy heuristics.
