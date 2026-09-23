# BILL — ENGINEERING CONTEXT

## Profile
- Retired engineer, East Hampton CT (Climate Zone 5A)
- Maintains 6 public GitHub repos: `home-assistant-config`, `Residential-HVAC-Performance-Baseline-`, `Lifepo4-Battery-Banks`, `DIY-LiFePO4-UPS`, `Tools`, plus 1 other
- Expertise: KiCad PCB design, ESPHome/Home Assistant firmware, LiFePO4 battery systems, residential energy monitoring
- Works from Windows, using Claude Code over Samba share to HA host
  (**ASRock N100DC-ITX, 8 GB RAM, 480 GB NVMe** - per Bill 2026-09-09; cross-checks
  against Supervisor `disk_total` 439.4 GB and a 7.59 GiB container memory limit [M]).
  **Any "eMMC" in an older note refers to the RETIRED HA Green, not this host** - so
  flash-wear arguments inherited from that era do not apply here.
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

Off-host gotchas. Full evidence in `docs/off-host-access.md` - read it before your
first HA API, InfluxDB, Grafana, add-on or git call from Windows.
- **`python3` does not exist on the Windows box.** Use `python`.
- **Persistent notifications are not in `/api/states`.** Absence there is not
  evidence. Read them over the websocket: `{"type": "persistent_notification/get"}`.
- **Adding or changing a `shell_command:` needs a RESTART** (Bill, 2026-09-16; an
  older note here said `shell_command.reload` - superseded). `automation.reload`
  never registers one. Check `/api/services` before concluding a script is broken.
- **`HA_TOKEN` gets 401 on every `/api/hassio/*` read, but the `hassio.*` services
  work** (addon start/stop/restart, backup/restore, host_reboot). Read add-on
  state from the hassio-platform entities in `/api/states`.
- **`HA_TOKEN`, not `HA_URL`, enables the audit's live check.** Without it the
  audit degrades (`live-check-skipped`, and a `sun.sun` false positive returns).
  Without `HA_CONFIG` it reports `pipelines.yaml not found`.
- **git on `H:` works. `H:` is the LIVE config and a checkout of the same repo:
  never run a git command that rewrites its working tree (checkout, stash,
  reset --hard, pull over local edits) without asking.** After a push made
  elsewhere: `git fetch && git reset --mixed origin/master` moves HEAD, touches no file.
- **Grafana has no off-host port.** SSH to the host and run the script there.

Read the verdict aloud in your first message: FAIL/WARN/INFO counts, and name
every FAIL and WARN. You are inheriting whatever the last session and the
nightly 00:30 run left behind — **an audit you did not read is an audit that did
not run for you.** Then run `grep -n '^### P' docs/pending.md` for open items; anything marked
RESOLVED is closed and lives in CHANGELOG.md.

If `ha_audit.py` cannot run at all, say so and stop. Working blind on a live
house is not a thing to do quietly.

### At the END of every session, before saying you are done

```bash
# 1. regenerate if entities, automations or packages changed
python3 scripts/gen_reference.py

# 2. the parse gate — every YAML file you touched
python3 scripts/validate_ha.py --strict <each edited file>

# 3. the semantic gate
python3 scripts/ha_audit.py                       # 0 FAIL required

# 4. the deployed gate (only this one certifies HA will load it)
#    POST /api/config/core/check_config   ->  "valid"
```

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

Most of R1-R14 are behavioural and cannot be checked by a script. Be honest
about which are mechanised, because a rule everyone believes is enforced and
is not is worse than one known to rest on judgement.

| lever | covers | where |
|---|---|---|
| `ha_audit.py` | R5, R8, R9, R19, and R10's doc-drift class | `scripts/test_ha_audit.py --list` prints the live count - **do not write it down here**; three copies of it drifted before 2026-08-25 |
| Claude Code hooks | "never hand-edit a GENERATED doc", "never edit .storage", running the audit at session start / after any turn that changed `H:`, and R20's checkpoint nudge + re-injection after compaction | `~/.claude/settings.json` + `~/.claude/hooks/` |
| deletion | R10 itself | the R10 answer is always to remove the second copy, never to add a checker that keeps two copies in step |


Wiring notes. Full history in `docs/claude-code-enforcement.md` - read it before
changing hooks, deny rules or settings, or when a block message surprises you.
- **This file loads only because `~/.claude/CLAUDE.md` contains `@H:/CLAUDE.md`.**
  The project root is `C:\Users\wkcol`, so a CLAUDE.md on `H:` is never
  auto-loaded. If `H:` is not mounted the import fails silently; the
  SessionStart audit hook is what reports `H:` missing.
- **Hooks run from `~/.claude/hooks/` on C: on purpose.** A guard on the drive it
  guards cannot report that drive missing. `H:/.claude/hooks/` holds the tracked
  source; `deploy_drift()` compares the two at every session start.
- **Settings load only from `~/.claude/settings.json`.** A settings file under
  `H:` never loads, and nothing announces that.
- **Deny rules run before hooks, so `ha_guard.py` is the backstop** and rarely
  fires. A malformed deny rule is silently dropped; the hook catches that.
- **The hook guard sees the Write/Edit tools only.** A Bash write bypasses it;
  the Stop gate, which genuinely blocks, is the backstop.

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
Some unknowns are not derivable from data at any price, because they are facts
about the world only he can see: what is plugged into what, which breaker feeds
which circuit, whether a valve is open, what model the appliance is, whether a
pump was replaced. When work blocks on one of these, **ASK, AND STOP THAT
THREAD.** Carry on with everything that does not depend on the answer, and leave
the dependent part unbuilt until he replies.

Do NOT substitute a statistical proxy. His answer is authoritative and takes him
seconds; inference is expensive, slower, and can only ever be probabilistic
about something he knows for certain.

**IF HE REPLIES WITHOUT ANSWERING, RE-ASK IT.** A reply on another subject is
not permission to proceed, and neither is his silence. Put the open question at
the top of the response, in one line, not buried under the work.

*Why: 2026-08-24, a 13-day statistical search concluded what Bill could have said
in one word.*

**The tell:** if the next thing you plan is a regression, a correlation, or a
"natural experiment" to establish something a person could confirm by looking at
a plug or a label — stop and ask instead.

**Mechanised: `open_questions.yaml`.** Every question to Bill gets an entry with
`asked:`, `question:`, `blocks:` and `answered:`. `ha_audit.py` WARNs
`open-question` for each unanswered one, so it surfaces at every session start.
`blocks:` names what stays unbuilt until he answers.

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

## Engineering Standards (ALWAYS APPLY)
- Measure-first: **the operational form of this is R15-R18 — follow those, not this bullet.** Flag uncertainty before stating any figure; verify specs from primary sources; never assert ungrounded numbers
- Code review: all risks surfaced during review, before sign-off — never after
- ESPHome firmware validation: config → codegen → `g++ -Wall` lambda check → real compile (`src/main.cpp.o` 0 errors). Codegen alone does not compile lambdas
- HA config validation: `homeassistant-config-validator --strict` before deployment

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
- **DIY LiFePO4 UPS**: Powers N100DC HA host via an 18 V U3V70A boost (fitted
  2026-08-29, EN/FET not installed). V1.20 firmware deployed 2026-09-16 on
  ESPHome 2026.9.0 (the "V1.16 deployed, V1.17 written" that stood here was
  three versions stale). 53.3 Wh; runtime ~128 min [D] at the measured 2.089 A / 26.80 W load
  [M, 2026-08-29] — was ~213 min at 1.18 A
- **HVAC Performance Baseline**: Longitudinal SPC study since 2021, 90.3 CCF/1k HDD efficiency
- **Dehumidifier Control**: RH-band (49%/46%), 150min max runtime, stall detection
- **Basement Sensor Node**: XIAO ESP32-C3 + SHT45 + OLED + VEML7700

---

# HA CONFIG — CLAUDE CODE SESSION RULES

## CONSTRAINTS (CHECK BEFORE ANY ACTION)

NEVER infer entity IDs from patterns — use only IDs listed in §ENTITIES
NEVER edit .storage/* — corrupts dashboards unrecoverably

**AND THE COROLLARY, which is the half that actually bites: `dashboards/` is a
SOURCE copy that Home Assistant never loads.** There is no `lovelace:` block in
configuration.yaml and nothing includes `dashboards/views/*`. The live dashboards
are UI-managed in `.storage/lovelace.*` — the SDR one is
`.storage/lovelace.sdr_utility_meters`. Editing a file under `dashboards/`
changes NOTHING the user can see, and because .storage is correctly off-limits,
there is no file you may edit that will.

**`dashboards/` has three subdirectories and only ONE of them is safe to
hand-edit for a correction that isn't live yet:**

| dir | what it is | may you hand-edit it? |
|---|---|---|
| `dashboards/views/` | HAND-MAINTAINED. May be deliberately AHEAD of live, holding corrections not yet pasted in (`dehumidifier.yaml` is a working example) | **YES — this is where a not-yet-live correction or new view goes** |
| `dashboards/cards/` | hand-maintained snippet library, extracted from production for copy-paste | Yes |
| `dashboards/lovelace/` | **GENERATED** by `scripts/export_dashboards.py` — a mirror of what is LIVE right now, stamped "DO NOT HAND-EDIT" at the top of every file | **NO.** Regenerate it with `HA_CONFIG='H:/' python scripts/export_dashboards.py` after a UI paste. The script overwrites the whole file from `.storage` with no staleness check — hand-editing it is either redundant (if it matches live) or gets silently deleted on the next run (if it doesn't) |

So a dashboard change is never "done" when the file is written. The workflow
is: write the correction into `dashboards/views/<name>.yaml` (the dedented
single-view format the raw configuration editor accepts) so the repo holds
it, then **hand the user the exact YAML and tell them to paste it** into the
dashboard's raw configuration editor. Say plainly that it is not live until
they do. Once it is live, re-run `export_dashboards.py` so
`dashboards/lovelace/` catches up — do not hand-edit that file to make it
"match" faster.

*Why: 2026-08-23, a card kept reading a superseded sensor with every gate passing;
2026-09-14, a session hand-edited the GENERATED `dashboards/lovelace/` file and
had a deny rule removed to do it.* **Never remove or loosen a deny rule to make an
edit possible** - find the file you are allowed to edit instead.

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

**Run `python3 scripts/gate.py <edited files>`.** It runs steps 1, 1b, 2 and 2b
in order, stops at the first failure, and PRINTS THE VERDICT BLOCK - generated,
not typed, which is the only reliable defence against the assurance-upgrade
failure the verdict table exists to prevent. Steps 3-5 stay manual because they
touch the live instance (R12).

The steps below are what it runs, kept for when you need one on its own.

Run every step that applies to what you touched. Record the result inline.

```
1. SYNTAX      python3 scripts/validate_ha.py --strict <edited files>
               -> "PASS (parse-clean)" required; any WARN blocks under --strict.
               This IS the homeassistant-config-validator skill's script,
               vendored 2026-08-23. Add --hass on the HA host for Layer 4.
               Also: python -m py_compile every edited .py

1b. ENTITIES   If the change adds, renames or removes an entity:
               python3 scripts/gen_reference.py    then commit ENTITIES.md
               ha_audit FAILs on a stale one, so this is not optional.

2. SEMANTIC    HA_CONFIG=<config> python3 scripts/ha_audit.py   -> 0 FAIL required
               WARN count must not INCREASE. Note it either way.

2b. RULES      If you changed scripts/ha_audit.py or scripts/gen_reference.py:
               python scripts/test_ha_audit.py     -> "SUITE PASSED" required
               R7 made checkable. It injects a known fault per covered rule and
               proves the rule FIRES, then proves a clean tree is SILENT.
               --list prints coverage and the gap; --only isolates one rule.
               Direction 2 asserts per rule, so a genuine WARN in the house
               does not fail the suite.
               NOT OPTIONAL WHEN THE AUDIT ITSELF MOVED. Twice on 2026-08-24 a
               rule shipped structurally incapable of firing, and a rule that
               CANNOT fire looks exactly like a rule with nothing to report.
               Also runnable from the UI, no terminal needed:
               Developer Tools > Actions > "Run HA Audit Self-Tests"
               (script.ha_audit_tests). Needs a RESTART after any change to it -
               shell_command is not reloadable.

3. DEPLOYED    POST /api/config/core/check_config               -> "valid" required
               The instance validating its own live config. Do this BEFORE any
               reload - it is the only check that sees what HA actually loads.

4. RELOAD      template.reload / automation.reload / script.reload as applicable.
               shell_command and statistics changes need a RESTART, not a reload.

5. OBSERVE     Re-read the entities the change was supposed to affect and say
               what they now read. "Reloaded without error" is not evidence.
               A guard is proven by making it fire, not by reading it.

6. ESPHOME     config -> codegen -> g++ -Wall lambda check -> real compile
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

- [ ] `python3 scripts/validate_ha.py --strict <edited files>` — PASS
- [ ] `python3 scripts/ha_audit.py` — 0 FAIL, and WARN count did not increase
- [ ] `python3 scripts/gen_reference.py` — run if entities/automations/packages moved
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
23:58:00 collision              STALE ENTRY, corrected 2026-08-25: no collision (R13 record in docs/rules-history.md)
_2 suffix entities              6 sensors — entity registry artifacts — canonical IDs — DO NOT DELETE
notify_efficiency_degradation   DISABLED Feb 2026 — fixed threshold replaced by ±2σ
Pirate Weather warm bias        reads up to 8.5°F warm on sunny afternoons — use outdoor_temp_live for CDD65
sensor.furnace_running_watts_daily  was unavailable — fixed 2026-07-20 (threshold + capture stamp)
hwh_recirc daily chart flat     was frozen at 144.5W — fixed 2026-07-20 (threshold + energy basis)
```

---

## BASELINES (reference only — do not modify without explicit instruction)

```
Building UA:          493 BTU/hr-°F
Balance point:        59°F
HDD59/HDD65 ratio:    0.844
AFUE:                 0.95
BTU/CCF:              103,700
Heating efficiency:   90.3 CCF/1k HDD (Navien-corrected 2025)
DHW ratio:            28.1% (220.8/787 CCF Navien-metered)
Heating ratio:        71.9% (566/787 CCF)
Annual HDD65:         6,270 (2025 actual); climate normal 5,873 (BDL NCEI 1991-2020 [M: sum of 365 ACIS BDL daily normals]; the 5,270 here until 2026-09-23 was a hard-coded dict's sum, not a BDL normal)
Annual electricity:   6,730 kWh
Baseline power:       200W (quiet house)
Annual gas:           787 CCF
Site EUI:             41.7 kBTU/ft²-yr
Therms→CCF:           ×0.9643
Electric rate:        $0.29/kWh
```

---

## REFERENCE DOCS — read on the trigger, not every session

| file | read it when |
|---|---|
| `docs/off-host-access.md` | before your first HA API, InfluxDB, Grafana, add-on or git call from Windows; when an off-host result surprises you |
| `docs/eod-timing.md` | before adding, moving or removing any time trigger, or anything that snapshots a daily value |
| `docs/influx-grafana.md` | before any InfluxDB query, continuous query or retention change, or any Grafana dashboard or provisioning work |
| `docs/file-map.md` | when you need to know where something lives and a grep has not answered it |
| `docs/pending.md` | at session start, headings only (`grep -n '^### P'`); in full before working an item or touching its entities |
| `docs/ha-ui-actions.md` | when working from the HA UI, or adding or changing a `script.ha_*` action |
| `docs/claude-code-enforcement.md` | before changing hooks, deny rules or settings; when a block message surprises you |
| `docs/rules-history.md` | before changing, narrowing or retiring any rule; when a rule's edge case is unclear; when recording a new scar |
| `docs/sdr-signal-level.md` | before any SDR antenna, antenna-position or signal-strength work; when tempted to judge an RF change by decode rate |

Files that cite a CLAUDE.md section this table lists by name ("SNAPSHOT RULE",
"EOD section", "FILE MAP", "PENDING") mean the doc above that now holds it.

---

## CHANGELOG — see `CHANGELOG.md`

Removed from this file 2026-08-23. It was a second, hand-curated summary of
`CHANGELOG.md`, and by R10 a second copy of a definition is a copy that will
drift — the same defect `pipelines.yaml` exists to end, and the same one that
put the InfluxDB CQs 9.0 W away from the HA charts for a month.

Append behaviour changes to `CHANGELOG.md`. Do not summarise them back here.
