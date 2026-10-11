# BILL — ENGINEERING CONTEXT

## Profile
- Retired engineer, East Hampton CT (Climate Zone 5A)
- Maintains 6 public GitHub repos: `home-assistant-config`, `Residential-HVAC-Performance-Baseline-`, `Lifepo4-Battery-Banks`, `DIY-LiFePO4-UPS`, `Tools`, plus 1 other
- Expertise: KiCad PCB design, ESPHome/Home Assistant firmware, LiFePO4 battery systems, residential energy monitoring
- Works from Windows, Claude Code over Samba to the HA host: ASRock N100DC-ITX,
  8 GB RAM, 480 GB NVMe (Bill, 2026-09-09). Any "eMMC" in an older note is the
  RETIRED HA Green; its flash-wear arguments do not apply here.
- Unit owner at Edgewater Hill (mixed-use planned community)

## Design Philosophy — the one sentence

**"Designed for no help coming."** Before any change, name the unattended moment
it must survive and what "working" means at exactly that moment. Design flows
from that answer. Right-the-first-time reliability, not repairability.

The operational form of that philosophy is the numbered rules below. If a rule
and the prose ever disagree, follow the rule and fix the prose.

---

## SESSION PROTOCOL — run these, do not skip them

### At the START of every session, before touching anything

```bash
# ON THE HA HOST
cd /config
python3 scripts/ha_audit.py    # inherit the truth, do not assume it

# OFF-HOST (Claude Code on Windows, H: over Samba) - all three are REQUIRED
cd /h
HA_CONFIG='H:/' HA_URL='http://10.0.0.210:8123' python scripts/ha_audit.py
python scripts/check_provenance.py --all <files>   # R17 gate, git-free mode
```

Off-host gotchas (evidence: `docs/off-host-access.md` - read it before the first
HA API, InfluxDB, Grafana, add-on or git call from Windows):
- `python`, not `python3`.
- Persistent notifications are not in `/api/states`; read them over the websocket
  (`{"type": "persistent_notification/get"}`).
- A new or changed `shell_command:` needs a RESTART (Bill, 2026-09-16), never
  `automation.reload`. Check `/api/services` before calling a script broken.
- `HA_TOKEN` gets 401 on `/api/hassio/*` reads, but `hassio.*` services work; read
  add-on state from the hassio entities in `/api/states`.
- The audit needs all three of `HA_CONFIG`, `HA_URL`, `HA_TOKEN`. `HA_TOKEN` is a
  Windows user variable; `HA_URL` is in `~/.claude/settings.json` `env`. Never
  default `HA_CONFIG`: without it a script fails loudly (`pipelines.yaml not
  found`) instead of silently using the live tree when a sandbox was meant.
  Without `HA_URL` the audit tries localhost: `live-check-skipped` plus the
  `sun.sun` false positive. (Corrected 2026-10-04: this said "`HA_TOKEN`, not
  `HA_URL`, enables the live check" - off-host both are needed.)
- **`H:` is the LIVE config and a git checkout: never run a git command that
  rewrites its working tree (checkout, stash, reset --hard, pull over local
  edits) without asking.** After a push made elsewhere:
  `git fetch && git reset --mixed origin/master` (moves HEAD, touches no file).
- Grafana has no off-host port: SSH to the host.

Read the verdict aloud in your first message: FAIL/WARN/INFO counts, and name
every FAIL and WARN. You are inheriting whatever the last session and the
nightly 00:30 run left behind — **an audit you did not read is an audit that did
not run for you.** Then run `grep -n '^### P' docs/pending.md` for open items; anything marked
RESOLVED is closed and lives in CHANGELOG.md.

If `ha_audit.py` cannot run at all, say so and stop. Working blind on a live
house is not a thing to do quietly.

### At the END of every session, before saying you are done

Run the DEFINITION OF DONE gate below: `gen_reference.py` if entities,
automations or packages moved, then `gate.py <edited files>`, then the
deployed gate (`check_config` -> "valid"; only it certifies HA will load it).

Then, in the final message:
- state the three verdicts verbatim — do not upgrade them (see below)
- say what changed, what was verified, and **what you left open and why**
- append to `CHANGELOG.md`; do not summarise it into this file

### Verdict vocabulary — never upgrade an assurance level

Aligned with the `homeassistant-config-validator` skill, which is where
`scripts/validate_ha.py` came from:

| verdict | means | may you say "ready to restart"? |
|---|---|---|
| **FAIL** | a blocking finding, or any WARN under `--strict` | no — fix and re-run |
| **PASS (parse-clean)** | YAML + Jinja parse, no blocking findings. Entity refs, integration schemas and runtime template eval are **unverified** | **no** |
| **PASS (HA-certified)** | `check_config` / `hass --script check_config` ran clean | yes |

"Parse-clean" is a real result and not a promise. The same distinction governs
firmware: ESPHome codegen text-substitutes `id(...)` and does not compile
lambdas, so config-valid is never the gate — `src/main.cpp.o` with **0 errors**
is (`esp-firmware-validation` skill).

### The rules are enforced by three things, and only three

Most of R1-R14 are behavioural; these are the only mechanised levers:

| lever | covers | where |
|---|---|---|
| `ha_audit.py` | R5, R8, R9, R19, and R10's doc-drift class | `scripts/test_ha_audit.py --list` prints the live count - **do not write it down here**; three copies of it drifted before 2026-08-25 |
| Claude Code hooks | "never hand-edit a GENERATED doc", "never edit .storage", running the audit at session start / after any turn that changed `H:`, and R20's checkpoint nudge + re-injection after compaction | `~/.claude/settings.json` + `~/.claude/hooks/` |
| deletion | R10 itself | the R10 answer is always to remove the second copy, never to add a checker that keeps two copies in step |


Wiring notes - where hooks, settings and this file load from, and why - are in
`docs/claude-code-enforcement.md` ("Wiring notes"). Read it before changing
hooks, deny rules or settings, or when a block message surprises you.

R1-R4, R6, R7, R11-R14 remain judgement, enforced by the OUTPUT FORMAT making
omission visible - except R14, which became a file on 2026-08-25 (see below).

### Aligned skills

| skill | gate it owns | local artifact |
|---|---|---|
| `homeassistant-config-validator` | HA YAML, Layers 0–4 | `scripts/validate_ha.py`, `docs/ha-validator-checks.md` |
| `esp-firmware-validation` | ESPHome lambdas → real compile | `esphome/` |
| `engineering-monthly-update` | monthly rollup | `reports/`, archive automations |

`ha_audit.py` is the layer none of the skills cover: it checks that references
**resolve**, that alarms **can fire**, and that the manifest and the config still
agree. A validator answers "is this well-formed"; the audit answers "does this
mean what it claims".

## RULES — execute these, they are not advice

Each rule states the ACTION and a one-line why. The dated scars that earned them
are in `docs/rules-history.md`: read the entry before proposing to change, narrow
or retire a rule, or when a rule's edge case is unclear. A new rule goes here with
its one-line why; its scar goes there, in the same commit.

### R1 — Say what you are about to do, before doing it
Output `Change type:` and `Impacted files:` before the first edit, plus one
sentence naming the unattended moment the change must survive.
*Earned: changes were made whose purpose could not be stated afterwards.*

### R2 — Never test in production
Copy the config tree to `C:\sandbox` (fixed local path on the Windows box,
not a session-specific temp dir — persists across sessions, and is plain
local NTFS so it's faster to iterate on than `H:` over Samba; not git-tracked,
wipe and re-copy fresh from `H:` each time rather than trusting a stale copy).
Inject the exact fault you claim to catch, prove the check FIRES. Then run it
against the clean tree and prove it is SILENT. Both directions, every time,
before the change reaches `H:`.
*Why: 2026-08-22, two new audit rules gave false FAILs that only the two-direction test found.*

### R3 — Verify structurally, never by eye
After any multi-file or multi-site edit: re-parse the file and prove the
untouched parts are byte-identical — typically by reversing the intended edit
and diffing against the original. Report the count of files/entities unchanged.
*2026-08-22: 13 stamp edits and 7 guard edits across a 2,500-line file; eye
review would not have caught a mis-scoped replace.*

### R4 — Never global-search-replace an entity or a template idiom
Edit by automation, by sensor, by span. Count the total occurrences first and
state how many are in scope.
*2026-08-22: `automations.yaml` held 26 `now().strftime(...)` stamps; exactly 13
were the bug and 13 were correct.*

### R5 — Confirm "missing" against the live API before renaming anything
`GET /api/states/<id>` or the entity registry. Never rename on a grep result.
*2026-08-22: 13 reported phantom ids, 6 real — the rest were the checker's own
substring bug.*

### R6 — Read the deployed artifact, never the plausible story
When behaviour surprises you, fetch the source at the version in `.HA_VERSION`,
the shipped JS in `www/community/<card>/`, or the add-on's own repo — before
forming a theory, not after.
*Why: 2026-08-22, reasoning about what `listen_mode` ought to mean nearly took the
SDR stack dark; the source showed it publishes nothing.*

### R7 — A gate untested against a known-bad input is not a gate
Before trusting any new check, prove it fires on a fault AND stays silent on a
clean system. A wrong FAIL spends the reader's trust; a check that cannot fail
spends it faster.
*Why: 2026-08-22, an audit rule vouched for an entity that had never existed, and
could not have caught a 15-night outage.*

### R8 — A check that did not run is a WARN, never an INFO
Absent findings must never look like clean findings. Any check that can be
skipped must announce the skip AND name the fix.
*Why: 2026-08-23, a check that had never run in production reported at INFO,
indistinguishable from clean.*

### R9 — Conventions live with the data, not in the readers
When a new pipeline breaks a convention (a sentinel value, a unit, a day
boundary), declare the exception in `pipelines.yaml`. Do not special-case the
consumers.
*Why: 2026-08-22/23, one sentinel inversion had to be caught separately in three
consumers before it was declared once in the manifest.*

### R10 — Never a second copy of a definition
Before computing something, check whether HA already computes it. If it does,
read it. A recomputation is a copy, and copies drift.
*Why: 2026-08-22, seven copies of the SPC definitions drifted; one kept a Grafana
panel permanently below LCL.*

### R11 — State the limits of what you measured
Give n, the span, and what the result does NOT establish. Flag any figure that
extrapolates beyond its fitted range.
*Why: 2026-08-23, a slope fitted over 1.5 degF was applied across 11.5 degF.*

### R12 — Ask before acting outward
Restarting HA, dropping continuous queries, writing to live helpers, sending a
notification: confirm first unless already authorised for that specific act.
Snapshot the prior state so it can be put back.
*2026-08-22: firing the leak automation to test it sent an unannounced push to
Bill's phone.*

### R13 — Record your own errors where you made them
When you find a defect you introduced, write it into the file it lives in with
the date and the evidence. Do not quietly replace it.
*The audit's own false positives, the `MEAN()` over a step-function limit, and
the deleted P8 are all recorded at their sites rather than tidied away.*

### R14 — Physical facts about the house come from Bill, not from inference
What is plugged into what, which breaker feeds which circuit, whether a valve is
open, a model number, whether a pump was replaced: when work blocks on one, **ASK,
AND STOP THAT THREAD**; carry on with everything that does not depend on it. Never
substitute a statistical proxy. **If he replies without answering, re-ask** -
another subject, or silence, is not permission. Put the open question at the top
of the response, in one line.
**The tell:** the next step is a regression, correlation or "natural experiment"
to establish what a person could confirm by looking at a plug or a label.
**Mechanised:** each question gets an `open_questions.yaml` entry (`asked:`,
`question:`, `blocks:`, `answered:`); `ha_audit.py` WARNs `open-question` until
it is answered, and `blocks:` names what stays unbuilt.
*Why: 2026-08-24, a 13-day statistical search concluded what Bill could have said
in one word.*

### R15 — Every figure carries its provenance tag
No number enters a doc, a CHANGELOG entry or a reply without one of:

    [M] measured  - carries n, the window, and the source series
    [S] spec      - carries the document identifier AND page/section
    [D] derived   - arithmetic on [M] or [S], with the formula shown
    [I] inferred  - a model not yet tested; MUST carry its falsifying observation

**An [I] may never justify a deployed change.** If the only support for a config
edit is a model, the edit waits for the [M].
*Why: 2026-08-25, an [I] reconstruction was reported in the same voice as an [S]
figure, and two config changes were proposed on it before data refuted it.*

### R16 — Identity before spec
Before citing any datasheet, filing or manual, state the identifier read off the
physical device and confirm the document covers THAT identifier. If they do not
match, the claim is [I], not [S].
*Why: 2026-08-25, twice in one day, documents for a different meter and module
were introduced as primary sources.*

### R17 — No naked ratios
A ratio, a percentage change or an "Nx" may not be written without n and a
significance test beside it. If the test has not been run, the number does not
get written. `scripts/check_provenance.py` enforces this on changed lines; an
R15 tag satisfies it.
*Why: 2026-08-25, two ratios reported as findings were z=+0.56 and z=-0.19.*

### R18 — Never measure the instrument with itself
Before quoting any external system's period, rate or interval, confirm the
sampling cadence is FASTER than the quantity being measured. If it is not, the
figure is a bound on the instrument, not a property of the world - say so.
*Why: 2026-08-25, twice in one day, a sampler's blind spot was reported as a
meter's transmit interval.*

### R19 — Quote YAML 1.1 boolean words in anything meant to be pasted
In every dashboard view, card snippet, or other YAML a human will paste, quote
`y n yes no on off` (any case) wherever they appear as a key or a string value,
and `true`/`false` wherever they appear as a key: `'y': 12.4`, `state: 'on'`. The
dashboard editor's parser reads them as booleans, and a key stored as `true` is
silently ignored. Generated YAML counts - quote in the dumper, do not trust it.
*Why: 2026-09-16, bare `y:` keys in a pasted view erased every threshold line on
six charts with every gate passing.* Gate: `dashboard-bare-boolean` before a
paste, `dashboard-boolean-key` after one.

### R20 — What must survive a compaction goes on disk before the compaction
Keep `~/.claude/checkpoints/<session id>.md` current at each milestone, under
8,000 chars, in these sections: goal / verdicts verbatim / tagged figures /
decisions and why / disproven theories / open questions to Bill / next step /
files touched. After a compaction its verdicts are the record and the summary is
a paraphrase; a WARN that it was missing or stale is read aloud in the next message.
*Why: 2026-09-23, a compaction summary is written by the model and only CLAUDE.md,
memory, a few files and hook output come back from disk; 13 of 29 Reads after a
compaction re-read a file already read [M].* Gate: `context_hygiene.py` nudges
from 80% of `autoCompactWindow` until the file is written, re-injects it after
every compaction, and WARNs (R8) when it was stale or missing.

## Home
- 2021 colonial, 2,440 sq ft, Zone 5A
- Annual electricity: 6,730 kWh (baseline 200W, efficient)
- Gas: 787 CCF/year (71.9% heating, 28.1% DHW)
- Navien NPE-240S2 DHW, gas range, 120V washer
- Dehumidifier and computer on Kasa plugs
- 16-CT SEM (Fusion Energy/Sense) whole-home monitor installed June 2026
- Ecobee thermostats (replaced Honeywell T6 Pro, June 2026)

## Active Projects (reference only — details in respective repos)
- **HA Energy Stack**: InfluxDB 1.x + Grafana, SEM-Meter MQTT pipeline, SPC monitoring
- **Battery Bank Monitor**: 12V/500Ah LiFePO4 emergency backup, INA228 monitoring
- **DIY LiFePO4 UPS**: powers the N100DC host via an 18 V U3V70A boost (fitted
  2026-08-29, EN/FET not installed). V1.20 firmware on ESPHome 2026.9.0
  (2026-09-16). 53.3 Wh; ~128 min [D] at 2.089 A / 26.80 W [M, 2026-08-29].
- **HVAC Performance Baseline**: Longitudinal SPC study since 2021, 100.6 CCF/1k HDD65 efficiency
  (ACIS BDL 2025, rebased 2026-10-10; was 90.3 on NOAA 6,270 HDD - see `docs/baselines.md`)
- **Dehumidifier Control**: RH-band (49%/46%), 150min max runtime, stall detection
- **Basement Sensor Node**: XIAO ESP32-C3 + SHT45 + OLED + VEML7700

---

# HA CONFIG — CLAUDE CODE SESSION RULES

## CONSTRAINTS (CHECK BEFORE ANY ACTION)

NEVER infer entity IDs from patterns — use only IDs listed in §ENTITIES
NEVER edit .storage/* — corrupts dashboards unrecoverably

**`dashboards/` is a SOURCE copy HA never loads.** No `lovelace:` block includes it;
live dashboards are UI-managed in `.storage/lovelace.*` (off-limits), so no file
edit changes what Bill sees.

| dir | is | hand-edit? |
|---|---|---|
| `dashboards/views/` | hand-kept; may be AHEAD of live | **YES** - not-yet-live corrections go here |
| `dashboards/cards/` | snippet library | yes |
| `dashboards/lovelace/` | GENERATED mirror of live | **NO** - re-run `HA_CONFIG='H:/' python scripts/export_dashboards.py` after a paste |

Workflow: write `dashboards/views/<name>.yaml` (single-view format), hand Bill the
exact YAML to paste into the raw configuration editor, say it is not live until he
does, then re-run `export_dashboards.py`. **Never remove or loosen a deny rule to
make an edit possible** - find the file you may edit instead.
*Why: 2026-08-23 a card read a superseded sensor with every gate passing;
2026-09-14 a session hand-edited `lovelace/` and had a deny rule removed.*

NEVER overwrite/truncate CSV files — append/rotate only
NEVER add a time trigger that contends with another automation (shared read/write state) — see §EOD TIMING SEQUENCE; `ha_audit.py` checks this. The old blanket 23:54:30–23:58:45 ban was retired 2026-08-21: 9 automations already ran inside it
NEVER use `| float` or `| int` without default: use `| float(0)` `| int(0)`
NEVER commit multiple unrelated changes in one commit
NEVER remove inline YAML comments

MUST pass the DEFINITION OF DONE gate below before calling anything production ready
MUST validate against the DEPLOYED ARTIFACT, never the documentation:
  - custom Lovelace cards -> read the shipped JS in `www/community/<card>/`
  - HA internals -> read the source at the pinned version in `.HA_VERSION`
    (e.g. https://raw.githubusercontent.com/home-assistant/core/<version>/
    homeassistant/components/<domain>/<file>.py)
  *Why: both 2026-08-21 regressions came from trusting docs over the shipped artifact.*
MUST add `default: []` to every `choose:` block
MUST add `availability:` guard to every new template sensor
MUST wrap every `shell_command.*` call with ha_maintenance_mode guard
SHOULD annotate any new entity in `entity_notes.yaml` (so `gen_reference.py`
lists it in ENTITIES.md) and record behaviour changes in CHANGELOG.md, in the
same commit as the entity.

(NOT ENFORCED, so it says SHOULD: measured 2026-08-26, 236 of 410 YAML-declared
entities carry no annotation [M]. A rule believed enforced that is not is worse
than one known to rest on judgement.)

---

## DEFINITION OF DONE (no change is "production ready" until this passes)

"Done" = passed a gate proving unattended behavior. A config that parses is not
a config that works, and on 2026-08-22 that distinction cost 15 nights of data.

A schema validator answers "is this well-formed?"; `ha_audit.py` answers "does
this reference resolve, can this alarm fire?". Run both - five defects that passed
the validator AND `check_config` are in `docs/rules-history.md`. To run any check
from the HA UI with no terminal: `docs/ha-ui-actions.md`.

### The gate

**Run `python3 scripts/gate.py <edited files>`.** It runs steps 1 (with
py_compile), 2 and 2b in order, stops at the first failure, and PRINTS THE
VERDICT BLOCK - generated, not typed, which is the only reliable defence against
the assurance-upgrade failure the verdict table exists to prevent. Step 1b and
steps 3-5 stay manual: 1b because gate.py never runs gen_reference.py
(corrected 2026-10-04 - this said "1, 1b, 2 and 2b"; gate.py's 1b is
py_compile), 3-5 because they touch the live instance (R12).

The steps below are what it runs, kept for when you need one on its own.

Run every step that applies to what you touched. Record the result inline.

```
1.  SYNTAX    validate_ha.py --strict <files> -> "PASS (parse-clean)"; any WARN
              blocks (--hass on the host adds Layer 4). py_compile every .py.
1b. ENTITIES  added/renamed/removed an entity -> gen_reference.py, commit
              ENTITIES.md (ha_audit FAILs on a stale one).
2.  SEMANTIC  HA_CONFIG=<config> ha_audit.py -> 0 FAIL; WARN count must not rise.
2b. RULES     changed ha_audit.py or gen_reference.py -> test_ha_audit.py ->
              "SUITE PASSED". Not optional: a rule that cannot fire looks exactly
              like one with nothing to report. UI: script.ha_audit_tests
              (RESTART after changing it - shell_command is not reloadable).
3.  DEPLOYED  POST /api/config/core/check_config -> "valid", BEFORE any reload.
4.  RELOAD    template/automation/script.reload; shell_command and statistics
              need a RESTART.
5.  OBSERVE   re-read the affected entities and say what they read. A guard is
              proven by making it fire, not by reading it.
6.  ESPHOME   config -> codegen -> g++ -Wall lambda check -> real compile
              (src/main.cpp.o, 0 errors). Codegen alone does not compile lambdas.
```

---

## OUTPUT FORMAT — this is STEP 0, required before any edit

Every change starts with:

```
Change type: <SENSOR|AUTOMATION|ENTITY rename|DASHBOARD snippet|CSV/reporting|PACKAGE|SCRIPT|DOCUMENTATION>
Impacted files: <list>
Gate: <the verdicts — see SESSION PROTOCOL>
```

Then the work, then what was verified and what was left open.

**Explain your reasoning.** Explanations caught three errors before deployment on
2026-08-22/23; an "output only" rule would have hidden them.

Kept from the old "output only" rule:
- **Minimal diffs.** Never rewrite a whole file to change five lines.
- **Never remove inline comments.** They carry the incident that earned the code.
- **"NO CHANGE" is a valid answer.** Say it plainly rather than manufacturing work.
- **Do not narrate options you are not going to take.**

## EDIT ORDER (never deviate)

1. `grep -rnw . -e 'ENTITY_ID' --include="*.yaml" --include="*.json" --include="*.py"` — impact scan
2. `packages/*.yaml` — if SPC/SEM/energy-related
3. `configuration.yaml` — sensors, helpers, shell_commands
4. `automations.yaml` — logic
5. `entity_notes.yaml` + `gen_reference.py`; `docs/pending.md`; §KNOWN ISSUES
6. `CHANGELOG.md` — behavior changes only
7. Validate with `homeassistant-config-validator --strict`
8. Provide diff summary

---

## EOD TIMING SEQUENCE — see `docs/eod-timing.md`

**Read it before adding, moving or removing any time-triggered automation, or
anything that snapshots, archives or resets a daily value.** The invariant: no
two automations may contend for the same state (write/write or read/write);
sharing a trigger second is fine. `ha_audit.py` enforces it with the `eod-*`
findings and parses the schedule table from that file.

---

## TEMPLATE PATTERNS

Defensive template (REQUIRED for all new sensors):
```yaml
- name: "Sensor Name"
  availability: "{{ states('sensor.source') not in ['unknown','unavailable','none',''] }}"
  state: >
    {% set v = states('sensor.source') %}
    {{ v | float(0) if v not in ['unknown','unavailable','none',''] else 0 }}
```

Maintenance guard (REQUIRED before every shell_command):
```yaml
- condition: state
  entity_id: input_boolean.ha_maintenance_mode
  state: "off"
- service: shell_command.COMMAND_NAME
```

choose block (REQUIRED default):
```yaml
- choose:
    - conditions: [...]
      sequence: [...]
  default: []
```

---

## PRE-COMMIT CHECKLIST — only what a machine does NOT check

Everything mechanical is enforced by `scripts/ha_audit.py`,
`scripts/validate_ha.py --strict` and CI. Re-listing those here taught skimming,
so they are gone. What remains needs a human judgement:

- [ ] `CHANGELOG.md` updated if behaviour changed
- [ ] Every risk surfaced in this review, not after it
- [ ] For each new alarm: can it actually fire? Name the state that would trip it
- [ ] For each new limit or fallback: is the number measured, or invented?
- [ ] Anything left undone is stated plainly, not omitted

Items removed on 2026-08-23 because `ha_audit.py` now checks them are listed,
with reasons, in `docs/rules-history.md` - do not re-add them.

## PACKAGES — see `PACKAGES.md`, GENERATED

Written by `scripts/gen_reference.py`; `ha_audit.py` FAILs when it is
stale. Was 110 hand-kept lines whose counts drifted from the files they described.

Design notes about a package belong in that package's own header comment,
beside the code — not in a summary that has to be kept in step with it.

## ENTITIES — see `ENTITIES.md`, do not list them here

**Resolution order for any entity id: `ENTITIES.md`, then
`.storage/core.entity_registry`. Never from memory, never inferred from a
pattern, never from this file.**

`ENTITIES.md` is GENERATED by `scripts/gen_reference.py` from the registry, the
YAML helper declarations and `pipelines.yaml`. `entity_notes.yaml` holds the
hand-written meaning; existence is always derived. `ha_audit.py` FAILs when
`ENTITIES.md` is stale, so drift is caught the same night rather than months
later.

To change an annotation: edit `entity_notes.yaml`, run
`python3 scripts/gen_reference.py`, commit both.

## AUTOMATIONS INDEX — see `AUTOMATIONS.md`, GENERATED

Written by `scripts/gen_reference.py`; `ha_audit.py` FAILs when it is
stale. Was 86 hand-kept lines that held nothing `automations.yaml` did not already state.

## KNOWN ISSUES

```
_2 suffix entities              6 sensors — entity registry artifacts — canonical IDs — DO NOT DELETE
notify_efficiency_degradation   DISABLED Feb 2026 — fixed threshold replaced by ±2σ
Pirate Weather warm bias        reads up to 8.5°F warm on sunny afternoons — use outdoor_temp_live for CDD65
```

---

## REFERENCE DOCS — read on the trigger, not every session

| file | read it when |
|---|---|
| `docs/off-host-access.md` | before your first HA API, InfluxDB, Grafana, add-on or git call from Windows; when an off-host result surprises you |
| `docs/eod-timing.md` | before adding, moving or removing any time trigger, or anything that snapshots a daily value |
| `docs/influx-grafana.md` | before any InfluxDB query, continuous query or retention change, or any Grafana dashboard or provisioning work |
| `docs/baselines.md` | before quoting or using a building, HVAC, gas or electricity baseline (UA, balance point, AFUE, HDD, CCF split, rate) |
| `docs/file-map.md` | when you need to know where something lives and a grep has not answered it |
| `docs/pending.md` | at session start, headings only (`grep -n '^### P'`); in full before working an item or touching its entities |
| `docs/ha-ui-actions.md` | when working from the HA UI, or adding or changing a `script.ha_*` action |
| `docs/claude-code-enforcement.md` | before changing hooks, deny rules or settings; when a block message surprises you |
| `docs/rules-history.md` | before changing, narrowing or retiring any rule; when a rule's edge case is unclear; when recording a new scar |
| `docs/sdr-signal-level.md` | before any SDR antenna, antenna-position or signal-strength work; when tempted to judge an RF change by decode rate |

Files that cite a CLAUDE.md section this table lists by name ("SNAPSHOT RULE",
"EOD section", "FILE MAP", "PENDING", "BASELINES") mean the doc above that now holds it.

---

# Compact instructions

When summarising this conversation, keep verbatim: every gate verdict (the
FAIL/WARN/INFO counts and the PASS level), every figure with its [M]/[S]/[D]/[I]
tag, open questions to Bill, decisions and disproven theories with their why,
files touched, and the next step. Drop tool output a file on disk already holds;
name the file instead. The R20 checkpoint is the record; the summary is a
paraphrase of it.
