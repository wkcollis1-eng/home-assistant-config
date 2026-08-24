# BILL — ENGINEERING CONTEXT

## Profile
- Retired engineer, East Hampton CT (Climate Zone 5A)
- Maintains 6 public GitHub repos: `home-assistant-config`, `Residential-HVAC-Performance-Baseline-`, `Lifepo4-Battery-Banks`, `DIY-LiFePO4-UPS`, `Tools`, plus 1 other
- Expertise: KiCad PCB design, ESPHome/Home Assistant firmware, LiFePO4 battery systems, residential energy monitoring
- Works from Windows, using Claude Code over Samba share to HA host (ASRock N100DC-ITX)
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
```

Off-host gotchas, each of which has cost a session:
- **`python3` does not exist on the Windows box.** Use `python`.
- **Without `HA_CONFIG`** the script looks for `/config` and reports
  `pipelines.yaml not found`.
- **Without `HA_URL`** it falls back to `http://localhost:8123`, which is the
  Windows box, not HA. The live statistics-buffer check then cannot run and
  reports `live-check-skipped` as a WARN. That WARN is correct and is a real
  coverage gap (R8) - do not wave it through as an environment quirk. Set the
  URL and re-run so the check actually executes.
- **`git` refuses to operate on `H:`** - "dubious ownership" on the Samba
  share. Not a credential problem. Anything requiring a commit has to happen
  on the host, or with `git -c safe.directory='*'`.

Read the verdict aloud in your first message: FAIL/WARN/INFO counts, and name
every FAIL and WARN. You are inheriting whatever the last session and the
nightly 00:30 run left behind — **an audit you did not read is an audit that did
not run for you.** Then skim `## PENDING` for open items; anything marked
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
| `ha_audit.py` | R5, R8, R9, and R10's doc-drift class | 32 rule ids; `scripts/test_ha_audit.py` proves 8 of them in both directions |
| Claude Code hooks | "never hand-edit a GENERATED doc", "never edit .storage", and running the audit at session start / after any turn that changed `H:` | `~/.claude/settings.json` + `~/.claude/hooks/` |
| deletion | R10 itself | the R10 answer is always to remove the second copy, never to add a checker that keeps two copies in step |

**The hook guard sees the Write/Edit TOOLS only.** A write through Bash
bypasses it; the Stop gate is the backstop, because it catches the consequence
however the edit was made. R1-R4, R6, R7, R11-R14 remain judgement, enforced by
the OUTPUT FORMAT making omission visible.

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

Each rule states the ACTION, then the failure that earned it. A rule with no
scar is a preference; every rule here has one, and it is dated.

### R1 — Say what you are about to do, before doing it
Output `Change type:` and `Impacted files:` before the first edit, plus one
sentence naming the unattended moment the change must survive.
*Earned: changes were made whose purpose could not be stated afterwards.*

### R2 — Never test in production
Copy the config tree to a scratch dir. Inject the exact fault you claim to
catch, prove the check FIRES. Then run it against the clean tree and prove it is
SILENT. Both directions, every time, before the change reaches `H:`.
*2026-08-22: two new audit rules produced false FAILs — a substring match and a
slugify comparison that ignored the registry. Only the two-direction test found
them.*

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
*2026-08-22: recommended `listen_mode: true` for rtlamr2mqtt by reasoning about
what it ought to mean. Reading `meter_reader.py` showed it is a DISCOVERY mode
that publishes nothing — it would have taken the whole SDR stack dark.*

### R7 — A gate untested against a known-bad input is not a gate
Before trusting any new check, prove it fires on a fault AND stays silent on a
clean system. A wrong FAIL spends the reader's trust; a check that cannot fail
spends it faster.
*2026-08-22: `ha_audit.py` vouched for an entity that had never existed, because
`known_entities()` synthesised `<domain>.<unique_id>`. The rule that should have
caught a 15-night outage was structurally incapable of it.*

### R8 — A check that did not run is a WARN, never an INFO
Absent findings must never look like clean findings. Any check that can be
skipped must announce the skip AND name the fix.
*2026-08-23: the statistics-buffer check had never run in production. It
reported at INFO, so nothing distinguished "looked, found nothing" from "never
looked".*

### R9 — Conventions live with the data, not in the readers
When a new pipeline breaks a convention (a sentinel value, a unit, a day
boundary), declare the exception in `pipelines.yaml`. Do not special-case the
consumers.
*2026-08-22/23: `0 means no data` is the SPC convention; the overnight-flow
buffer inverts it (0.00 gal/h is a PERFECT night, -1 means no night). That single
inversion had to be caught separately in the mean sensor, the chart JS, and the
audit rule before it was declared once in the manifest.*

### R10 — Never a second copy of a definition
Before computing something, check whether HA already computes it. If it does,
read it. A recomputation is a copy, and copies drift.
*2026-08-22: `pipelines.yaml` exists because five copies drifted;
`scripts/spc_seed.py` was a sixth; the InfluxDB CQs a seventh, and they had the
Grafana dehumidifier panel 9.0 W off the HA chart and permanently below LCL.*

### R11 — State the limits of what you measured
Give n, the span, and what the result does NOT establish. Flag any figure that
extrapolates beyond its fitted range.
*2026-08-23: 7.64 W/degF was fitted over 1.5 degF and then applied across
11.5 degF — the same 8x extrapolation error the 2026-08-07 note made in the
opposite direction on a 0.78 degF lever arm.*

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

*2026-08-24: needed to know whether the basement router's plug hangs off the UPS,
because if it did, summing it with `ups_outlet_current_consumption` would
double-count by ~65%. Asked once, then answered a different question he raised
and treated that as licence to infer. Cost: a natural-experiment search across 13
days, then a coincident-step test over 843 events, to conclude PARALLEL — which
he could have said in one word. The first script I wrote for it had already
printed its own verdict:* `Do not guess - ask which outlet feeds what.` *Writing
that line and then not following it is the whole failure.*

**The tell:** if the next thing you plan is a regression, a correlation, or a
"natural experiment" to establish something a person could confirm by looking at
a plug or a label — stop and ask instead.

## Engineering Standards (ALWAYS APPLY)
- Measure-first: flag uncertainty before stating any figure; verify specs from primary sources; never assert ungrounded numbers
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
- **DIY LiFePO4 UPS**: Powers N100DC HA host, V1.16 firmware, 53.3Wh/135min runtime
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

So a dashboard change is never "done" when the file is written. The workflow is:
edit the file under `dashboards/` so the repo copy stays true, then **hand the
user the exact YAML and tell them to paste it** into the dashboard's raw
configuration editor. Say plainly that it is not live until they do.

Earned 2026-08-23: P12 repointed two rows at `utility_electric_power_avg`, all
gates passed, and the card went on reading the superseded
`utility_electric_power_mean` — so it showed a 60-min mean from the old sensor
beside a delta and error computed from the new one, and the arithmetic on screen
did not close (394 - 398 displayed as +1 W). The user spotted it from the card.
Every earlier dashboard change this session landed correctly, because those were
handed over as YAML to paste rather than written to the file.
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
  Both of the 2026-08-21 regressions came from trusting docs over the artifact:
  apexcharts-card's documented `data_generator(entity, hass, index)` is really
  `AsyncFunction('entity','start','end','hass','moment', "'use strict'; "+body)`,
  so `const end = ...` was a SyntaxError that hung the card on "loading"; and
  the `statistics` platform's availability propagation was inferred from state
  timestamps for an hour when `components/statistics/sensor.py` settled it in
  one read. `.HA_VERSION` makes the exact source cheap to fetch — use it.
MUST add `default: []` to every `choose:` block
MUST add `availability:` guard to every new template sensor
MUST wrap every `shell_command.*` call with ha_maintenance_mode guard
MUST update §ENTITIES + CHANGELOG.md in same commit as any new entity

---

## DEFINITION OF DONE (no change is "production ready" until this passes)

"Done" = passed a gate proving unattended behavior. A config that parses is not
a config that works, and on 2026-08-22 that distinction cost 15 nights of data.

### Why a validator alone is not the gate

Every one of these passed `homeassistant-config-validator --strict` AND HA's own
`/api/config/core/check_config` with **valid, 0 errors, 0 warnings**:

| Defect | What the validator saw |
|---|---|
| Dehumidifier capture guard read `sensor.*_steady_latched`, an entity that never existed — 15 nights of silent skips | valid YAML, valid schema |
| `hvac_runtime_per_hdd_high/low_alert` gated on `upper > 0` where `upper` came from `float(0)` of a missing entity — **neither alarm could ever fire** | valid |
| `hvac_runtime_per_cdd_7_day_stddev` misspelled, so the band fell back to a hardcoded 2.0 against a real 6.8 — false `low_alert` **ON** for a healthy system | valid |
| `script.ha_audit` raised `from_json` on every single invocation since the day it was written | valid |
| 16 of 290 entity ids in this file's ENTITIES section did not exist | not checked at all |

A schema validator answers "is this well-formed?". It cannot answer "does this
reference resolve?", "can this alarm fire?", or "is this still the metric I
think it is?". Those are what `ha_audit.py` is for. Run both. Neither replaces
the other.

### The gate

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
               9 of 33 rule ids covered; --list prints the gap, --only isolates.
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

### Rules that carry over from 2026-08-22

**R3, R4, R5, R6 and R7 above.** They were restated here in full until
2026-08-24 — five rules, second copy, same scars retold in different words.
That is exactly what R10 forbids, in the file that declares R10: edit one copy
and the two diverge silently. Deleted rather than synchronised, because the
R10 answer is always deletion, never a checker that keeps two copies in step.

---

## STEP 0 — REQUIRED BEFORE ANY EDIT

State inline:
```
Change type: <SENSOR|AUTOMATION|ENTITY rename|DASHBOARD snippet|CSV/reporting|PACKAGE|SCRIPT|DOCUMENTATION>
Impacted files: <list>
```

---

## OUTPUT FORMAT

Every change starts with:

```
Change type: <SENSOR|AUTOMATION|ENTITY rename|DASHBOARD snippet|CSV/reporting|PACKAGE|SCRIPT|DOCUMENTATION>
Impacted files: <list>
Gate: <the verdicts — see SESSION PROTOCOL>
```

Then the work, then what was verified and what was left open.

**Explain your reasoning.** The previous version of this section said "output
ONLY ... never explain unless asked", and it was dead law: every message of the
2026-08-22/23 session broke it, and the explanations are precisely what caught
the `listen_mode` error before deployment, the `-unique` trap, and a `MEAN()`
over a step-function limit. A rule that would have made the work worse is not a
rule, it is a habit that outlived its reason.

What the old rule was right about, kept:
- **Minimal diffs.** Never rewrite a whole file to change five lines.
- **Never remove inline comments.** They carry the incident that earned the code.
- **"NO CHANGE" is a valid answer.** Say it plainly rather than manufacturing work.
- **Do not narrate options you are not going to take.**

## EDIT ORDER (never deviate)

1. `grep -rnw . -e 'ENTITY_ID' --include="*.yaml" --include="*.json" --include="*.py"` — impact scan
2. `packages/*.yaml` — if SPC/SEM/energy-related
3. `configuration.yaml` — sensors, helpers, shell_commands
4. `automations.yaml` — logic
5. `CLAUDE.md` — update §ENTITIES, §PENDING, §ISSUES
6. `CHANGELOG.md` — behavior changes only
7. Validate with `homeassistant-config-validator --strict`
8. Provide diff summary

---

## EOD TIMING SEQUENCE

The old version of this section was labelled FROZEN and listed 9 entries with a
blanket ban on new triggers between 23:54:30 and 23:58:45. By 2026-08-21 there
were **19 capture automations, 9 of them inside that window and 4 documented
nowhere**. A rule nobody can check is worse than no rule: it reads as
protection you do not have. Replaced with the actual intent.

### THE INVARIANT: no two automations may contend for the same state

Sharing a trigger second is NOT a problem. HA runs automations concurrently and
six of these fire together at 23:59:00 with no interaction whatsoever. What
matters is shared state:

- **write/write** — both set the same entity. Last writer wins, silently.
- **read/write** — one reads what the other is writing. It sees the old or the
  new value depending on scheduling, and the result is not reproducible.

`scripts/ha_audit.py` enforces this by computing each automation's read and
write sets and comparing same-second pairs: `eod-race` (write/write) FAILS,
`eod-read-write` WARNs, and same-second automations that share nothing report
`eod-concurrent` as INFO. Stagger only to resolve a real contention or an
ordering dependency — not for tidiness.

### ORDERING DEPENDENCIES (these are why the staggering exists)

- **23:56:30 `capture_daily_monthly_tracking` is immovable.** Every month
  sensor depends on `monthly_tracking_capture_last_ok`.
- New month accumulators go in `capture_daily_monthly_tracking`, NOT
  `capture_daily_hdd`.
- `archive_monthly_hdd` / `_cdd` read the month accumulators, so they must run
  after 23:56:30. They do (23:58:15 / 23:58:30).
- The 00:20 buffer backup runs after all captures; the 00:30 audit after it.

### SNAPSHOT RULE

EOD captures MUST snapshot with a `variables:` block at trigger time — values
AND the capture stamp. Until 2026-08-21 the values obeyed this but the stamps
were written as a live `{{ now().date() }}`, so a capture slipping past
midnight would stamp tomorrow against today's data, and every staleness
detector reads that stamp.

**All 19 pipelines now snapshot (2026-08-22).** The six SPC captures use
`capture_date`; the other 13 use `capture_stamp`, defined as the first step of
`action:` and read by the `input_datetime.set_datetime` call. `ha_audit.py`
reports any regression as `stamp-not-snapshotted`, and the count is 0.

Note automations.yaml still holds 13 OTHER live `now().strftime(...)` stamps.
Those are correct and must stay: they are event-triggered (dehumidifier cycle
start/end, setback marks) where the wall-clock moment IS the datum. The rule
only inspects automations declared in `pipelines.yaml`, which is why it can
tell the two apart — edit by automation, never by a global search-replace.

### LOCAL TIME, NOT UTC — and the two systems differ

HA `time` triggers fire in the instance timezone (`America/New_York`), never
UTC. Verified 2026-08-22 against automations whose `at:` is known:

```
capture_daily_dehumidifier_watts   at: "23:59:00"   fired 03:59:00 UTC
capture_daily_hdd                  at: "23:55:00"   fired 03:55:00 UTC
```

Worth stating explicitly because **InfluxDB is the opposite**: `GROUP BY
time(1d)` there is UTC-aligned unless you add `tz('America/New_York')`. Same
kind of config, opposite default. That mismatch is exactly what put the Grafana
SPC panels four hours off the HA captures for a month — see P12. When a time
window looks wrong, check which system's default you are relying on.

### DST

Spring forward: a mark scheduled inside the missing 02:00–03:00 hour simply
does not fire that night. Any capture that depends on a fixed number of
sub-intervals must tolerate one fewer — `capture_daily_water_overnight` needs
3 of 5 bins and so degrades gracefully.

Fall back: the repeated hour can produce one bin spanning two wall-clock hours,
inflating it. This is a second reason the overnight-flow instrument uses the
MINIMUM: an inflated bin never becomes the minimum, so the leak signal is
untouched. Only the max-derived regen flag can false-positive, once a year.

### THE SCHEDULE (HAND-MAINTAINED, validated by ha_audit)

Corrected 2026-08-24: this was labelled "generated from pipelines.yaml —
regenerate, do not hand-edit". **Nothing generates it.** `gen_reference.py`
writes only ENTITIES.md / AUTOMATIONS.md / PACKAGES.md and merely READS this
file in a one-time migration helper. `ha_audit.py` VALIDATES the table
(`eod-undeclared`), so a session obeying "do not hand-edit" and hunting for a
regenerate command would find none, leave the table stale, and fail the audit.
Add the row by hand when you add a pipeline.

```
TIME      AUTOMATION                          STALE DETECTOR
00:00:45  capture_daily_water_overnight       water_overnight_capture_stale
          (reset mark; bins close at 01/02/03/04/05:00:45, publish at 05:00:45)
00:15:00  daily_energy_csv_export             
00:20:00  nightly_buffer_backup               
00:30:00  nightly_ha_audit                    ha_audit_stale
23:55:00  capture_daily_hdd                   hdd_capture_stale
23:55:15  capture_daily_cdd                   cdd_capture_stale
23:55:30  capture_daily_ac_min_per_cycle      ac_min_per_cycle_capture_stale
23:56:00  capture_daily_runtime_per_hdd       runtime_per_hdd_capture_stale
23:56:15  capture_daily_furnace_min_per_cycle furnace_cycle_capture_stale
23:56:30  capture_daily_monthly_tracking      monthly_report_stale
23:56:45  capture_daily_runtime_per_cdd       runtime_per_cdd_capture_stale
23:57:00  CSV daily report                    
23:58:15  archive_monthly_hdd                 hdd_archive_stale
23:58:30  archive_monthly_cdd                 cdd_archive_stale
23:58:30  CSV monthly report (last day only)  
23:59:00  capture_daily_ac_watts              ac_spc_capture_stale
23:59:00  capture_daily_cooling_kwh_cdd       cooling_kwh_cdd_spc_capture_stale
23:59:00  capture_daily_dehumidifier_watts    dehumidifier_spc_capture_stale
23:59:00  capture_daily_fridge_watts          fridge_spc_capture_stale
23:59:00  capture_daily_furnace_watts         furnace_spc_capture_stale
23:59:00  capture_daily_hwh_recirc_watts      hwh_recirc_spc_capture_stale
23:59:30  capture_daily_dehumidifier_cost     dehumidifier_cost_capture_stale
23:59:30  capture_daily_dehumidifier_duty_kwh dehumidifier_duty_kwh_capture_stale
23:59:45  capture_daily_ac_cost               ac_cost_capture_stale
(event)   archive_monthly_gas_heat_cost       gas_heat_cost_archive_stale
```

Every pipeline above has a capture stamp and a stale detector as of
2026-08-22 (20/20). `ha_audit.py` FAILS if a new capture automation is added
without being declared in `pipelines.yaml`, and WARNs if its trigger time is
missing from the table above.

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

**Removed 2026-08-23** and why, so they are not re-added:
`choose: default: []`, `| float(0)` defaults, `availability:` on new template
sensors, `_1s`/`_2` suffix entities, `shell_command` guards, entity ids in
ENTITIES — all now FAIL or WARN in `ha_audit.py`. The
`23:54:30-23:58:45` trigger ban was RETIRED on 2026-08-21 (nine automations
already ran inside it) and this checklist had gone on asserting it — the
document contradicting itself, which is worse than either rule alone.

CI: yamllint went green 2026-08-21 after 64 errors across 21 files; line endings
are held by `.gitattributes` (`*.yaml text eol=lf`) so Windows/Samba editing
cannot reintroduce CRLF. Deliberately not linted, with reasons, in `.yamllint.yml`.

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

Why it moved out of this file (2026-08-23): the block was 548 lines, 32.8% of
CLAUDE.md, loaded into context every session — and **16 of its 328 ids did not
exist**, two of them behind alerts that could never fire. A hand-maintained list
that CONSTRAINTS calls the only permitted source of ids is a defect generator:
a wrong entry is this file instructing you to use a name that resolves to
`unknown`.

To change an annotation: edit `entity_notes.yaml`, run
`python3 scripts/gen_reference.py`, commit both.

## AUTOMATIONS INDEX — see `AUTOMATIONS.md`, GENERATED

Written by `scripts/gen_reference.py`; `ha_audit.py` FAILs when it is
stale. Was 86 hand-kept lines that held nothing `automations.yaml` did not already state.

Design notes about a package belong in that package's own header comment,
beside the code — not in a summary that has to be kept in step with it.

## KNOWN ISSUES

```
23:58:00 collision              archive_monthly_hdd + accumulate_filter_runtime — separate entities, no data risk
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
Annual HDD65:         6,270 (2025 actual); climate normal 5,270
Annual electricity:   6,730 kWh
Baseline power:       200W (quiet house)
Annual gas:           787 CCF
Site EUI:             41.7 kBTU/ft²-yr
Therms→CCF:           ×0.9643
Electric rate:        $0.29/kWh
```

---

## INFLUXDB / GRAFANA

### InfluxDB 1.x
- **Host**: 10.0.0.210:8086
- **Database**: "Home Assistant"
- **Measurement naming**: unit of measure (e.g., "W" for Watts, "%" for percent)
- **Tags**: `entity_id`, `domain`
- **Configured as a UI CONFIG ENTRY, not YAML.** Nothing appears in
  configuration.yaml; `.storage/core.config_entries` holds it, `options: {}`,
  so there is NO include/exclude filter - every entity HA emits is written.
- **Retention is INFINITE** (`autogen`, duration `0s`). Nothing is ever purged.
  History begins 2026-05-31 for W/degF/%, 2026-06-27 for kWh - that is when it
  was set up, not a retention limit.
- **Coverage measured 2026-08-22**: 1,287 distinct entity_ids, 1,362 series,
  ~963k points/day. 30 sensor/binary_sensors have no series, almost all
  `bills_iphone_*` strings that have not changed since Influx started.
- **Strings and attributes ARE stored**, not just numerics: a non-numeric
  sensor gets a `state` field (plus `*_str` attribute fields). That is how the
  R900 Leak/LeakNow/BackFlow/NoUse fields had history predating their sensors.
- **WRITES HAPPEN ON STATE CHANGE, NOT ON A SAMPLE CLOCK.** An unchanged value
  writes nothing, so a flat line looks like a gap and is not one. This is the
  single most important thing to know when reading the data - it is what made
  dehumidifier_current_consumption look 163 min stale when the unit was simply
  off.
- **Credentials**: `secrets.yaml`, keys `influxdb_url` / `influxdb_db` /
  `influxdb_user` / `influxdb_pass` (added 2026-08-24). Nothing in
  configuration.yaml reads them via `!secret` — the integration is a UI config
  entry and needs no YAML. They exist for `scripts/spc_seed.py`, which reads
  `os.environ`, and for Claude Code sessions, which run OFF-HOST over Samba and
  inherit no HA environment. **Env vars still win**, so a shell export
  overrides the file and nothing that worked before changes:

  ```python
  import os, io, yaml
  _cfg = os.environ.get("HA_CONFIG", "/config")
  _s = yaml.safe_load(io.open(f"{_cfg}/secrets.yaml", encoding="utf-8")) or {}
  USER = os.environ.get("INFLUXDB_USER") or _s.get("influxdb_user", "")
  PASS = os.environ.get("INFLUXDB_PASS") or _s.get("influxdb_pass", "")
  URL  = os.environ.get("INFLUXDB_URL")  or _s.get("influxdb_url", "")
  ```

  Use a READ-ONLY influx user (`GRANT READ ON "Home Assistant"`). Every reader
  of these only runs SELECT, and retention is infinite with no backup of the
  raw series — a leaked read-only credential cannot DROP a measurement.
  **Never echo the value** into a log, a debug URL, a commit or a chat
  transcript; `spc_seed.py` masks it in its debug URL (line 175).

  THE RULE THIS OBEYS: never a credential in a TRACKED file. They were
  hardcoded in `scripts/spc_seed.py` until 2026-08-22 — untracked, but
  `.gitignore` covers only `secrets.yaml` / `secrets_*.yaml`, not `scripts/`,
  so one `git add -A` would have pushed a plaintext password to a public
  GitHub remote. `secrets.yaml` is covered (`.gitignore` line 2, re-verified
  2026-08-24); `scripts/` still is not. The rule is satisfied, not relaxed.

### Continuous Queries (scripts/spc_continuous_queries.sql)
Pre-aggregate daily "running watts" for SPC monitoring.
- **Target measurement**: `spc`
- **CQs**: `spc_fridge_daily`, `spc_furnace_daily`, `spc_ac_daily`, `spc_hwh_recirc_daily`, `spc_dehumidifier_daily`
- **Deploy**: `influx -database "Home Assistant" < spc_continuous_queries.sql`

### Grafana Dashboards (grafana/dashboards/)
Provisioned dashboards — survive Grafana rebuilds.
- **energy.json**: Total power stats, daily kWh, cost estimate, SEM circuits, Kasa plugs
- **battery_bank.json**: Voltage/SOC/Power/Runtime stats, electrical trends, temperature
- **ups.json**: Voltage/Power/Temp stats, electrical trends, temperature
- **spc_appliances.json**: SPC charts with daily values, rolling mean, UCL/LCL

### Grafana Provisioning
```
grafana/provisioning/dashboards/default.yaml
```
Points to `/config/grafana/dashboards` for auto-loading.

### Grafana Query Notes
- Datasource UID: `bfrwayjkhasjka`
- Queries MUST include `GROUP BY "entity_id"` for proper series display
- Use `rawQuery: true` with `alias` field for series naming

---

## FILE MAP

```
ENTITIES.md                     GENERATED — entity reference
AUTOMATIONS.md                  GENERATED — every automation, trigger, mode
PACKAGES.md                     GENERATED — package summary and counts
                                all three by scripts/gen_reference.py;
                                ha_audit FAILs if any is stale. NEVER hand-edit.
scripts/validate_ha.py          the homeassistant-config-validator skill's
                                script, vendored 2026-08-23 — the Layer 0-3 gate
docs/ha-validator-checks.md     what that validator checks, from the skill
entity_notes.yaml               hand-written MEANING for entity ids; the only
                                part of the entity reference a human maintains
configuration.yaml              sensors, helpers, shell_commands
automations.yaml                automation logic
scripts.yaml                    bill archive seed scripts

packages/                       EVERY package, with live line and domain counts:
                                see PACKAGES.md (GENERATED). Deliberately not
                                listed here. Until 2026-08-24 this block carried
                                its own counts and they drifted: spc.yaml read
                                1,787 against a real 3,610, configuration.yaml
                                ~6,500 against 7,415, automations.yaml ~2,500
                                against 4,388 — and audit.yaml, backup_sizing.yaml
                                and utility_meters.yaml were missing outright.
                                A derivable number written down twice is R10.

scripts/
├── climate_norms_today.py      Climate norms lookup
├── setback_csv.py              Setback recovery CSV logging
├── daily_energy_export.py      Energy CSV export to www/energy/
├── test_ha_audit.py            R7 harness for ha_audit.py: proves each covered
│                               rule FIRES on an injected fault and stays SILENT
│                               on a clean tree. `--list` prints coverage (8 of 32
│                               rule ids as of 2026-08-24), `--only RULE` isolates.
├── spc_validator.py            SPC diagnostic tool (queries DB + API)
├── spc_seed.py                 MANUAL CLI backfill from InfluxDB. Manifest-driven —
│                               reads pipelines.yaml, resolves each guard.live_source
│                               to the gate sensor it averages, and queries THAT.
│                               Carries no appliance constants. Prints a plan; writes
│                               nothing back without --apply. Stamps *_spc_last_seed.
├── seed_ac_blower_energy.py    Seeds hvac_ac_blower_daily from furnace+AC correlation
├── spc_continuous_queries.sql  InfluxDB CQs for daily SPC aggregation
├── csv_manager.py              CSV utilities
├── fetch_bdl_degree_days.py    BDL degree day fetcher
├── seed_hdd_archives.yaml      HDD archive seeding
└── seed_dhw_archives.yaml      DHW archive seeding

grafana/
├── dashboards/
│   ├── energy.json             Energy monitoring dashboard
│   ├── hvac_status.json        HVAC system status + cooling efficiency
│   ├── battery_bank.json       Battery bank status dashboard
│   ├── ups.json                UPS status dashboard
│   └── spc_appliances.json     SPC control charts
└── provisioning/
    └── dashboards/
        └── default.yaml        Dashboard provisioning config

dashboards/cards/               Lovelace YAML snippets only
dashboards/views/               HAND-MAINTAINED complete views, for the raw
                                configuration editor. May be deliberately AHEAD
                                of what is live, holding corrections not yet
                                pasted in. Kept in the repo so ha_audit.py can
                                resolve its entity references - a dashboard is
                                the one place a broken entity is completely
                                silent: no log line, no unavailable state, just
                                an empty card.
dashboards/lovelace/            GENERATED by scripts/export_dashboards.py - a
                                mirror of every live dashboard, one file per
                                dashboard plus _dashboards/_resources. This is
                                the ONLY backup of .storage/lovelace.*, which is
                                gitignored and off-limits to edit; before
                                2026-08-24 the 16 views across 4 dashboards had
                                no copy and no history anywhere.
                                RESTORE FROM HERE, paste into the raw editor.
                                NOTHING CHECKS IT FOR STALENESS - ha_audit does
                                not know about it, so re-run the script after
                                any UI dashboard edit (R8: said out loud so the
                                file does not imply a check that is not there).
reports/                        CSV outputs — DO NOT edit manually
www/energy/                     Daily energy CSVs (energy_YYYY-MM-DD.csv)
esphome/                        ESPHome device configs
custom_components/              HACS custom integrations
baseline-repo/                  HVAC Baseline repo reference

.storage/                       BLOCKED — HA-managed JSON — never edit
CLAUDE.md                       this file — authoritative
CHANGELOG.md                    CalVer YYYY.MM — update on behavior changes
```

---

## PENDING (address in next update)

### P2 — Shoulder-season dehumidifier validation [MEDIUM]
```
High-res RH data beyond 15-day retention cliff — need to validate
stall threshold (0.30%/hr) behavior when AC not dominating
NOTE 2026-08-22: there is no retention cliff. InfluxDB "Home Assistant"
runs retention policy autogen with duration 0s = INFINITE, verified by
SHOW RETENTION POLICIES. Full-resolution history is available back to
2026-07 and earlier. The 15-day figure is the RECORDER purge_keep_days,
which bounds the SQLite DB and the HA history UI only (it is 14, not 15 —
configuration.yaml:174). Verified: dehumidifier_power_when_on_steady has
per-day means in InfluxDB from 2026-08-07, and the raw plug series back to
2026-07-23, at full ~5 s cadence.
```

### P3 — Dehumidifier SPC is measuring basement temperature [HIGH]
```
Steady-window watts vs basement temp, 2026-08-08..21 (n=14):
  r2 = 0.922, slope +7.64 +/- 0.64 W/degF, t = 11.9
  raw daily sd 4.60 W -> residual sd 1.29 W after T-normalisation

DOES THE 60 degF CUTOFF MAKE THIS MOOT? No - asked 2026-08-23, answered with
data. Both on-paths do gate on temp >= min_temp (dehumidifier_should_run and
the force-on backstop, verified), but the gate never binds:
  sensor.shelly_temperature_humidity_temperature, 2026-05-31..08-23, n=3230
     range 61.3 .. 72.9 degF     samples below 60 degF: 0 of 3230
     30-day means: 62.7 -> 67.3 -> 70.0 -> 71.2 degF
  (the two basement sensors agree to 0.06 degF, so this is directly
   comparable to the SHT45 node the SPC series uses)
The cutoff truncates the COLD end - deep winter, when the unit stops and the
chart simply has no points. It leaves the entire 61-73 degF shoulder-to-summer
band intact: 11.5 degF of operating range, and the MEAN alone moved 8.5 degF
across those 84 days.

WHY THAT MATTERS MORE THAN A WIDE BAND. At 7.64 W/degF an 8.5 degF seasonal
rise is +65 W. A refrigerant loss of -50 W over the same months nets to +15 W
on the chart - a gentle rise, no alarm, machine failing, instrument says fine.
The confound moves on the SAME TIMESCALE and in the OPPOSITE DIRECTION to the
fault the chart exists to catch. Autumn reverses it: a healthy machine looks
like it is dying. A 7-day rolling window does not help - the limits follow the
drift, which is precisely how the drift hides.

WHAT IS NOT YET EARNED: the 7.64 W/degF slope was fitted over a 1.5 degF span.
Applying it across 11.5 degF is an 8x extrapolation - the same error the
2026-08-07 note on dehumidifier_power_when_on_steady made in the other
direction when it dismissed temperature on a 0.78 degF lever arm. At half the
slope the seasonal drift is still 32 W against a 2-3 W sigma, so the CONCLUSION
is robust; the MAGNITUDE is not.

NO CONFIG CHANGE NEEDED TO DECIDE. Basement temperature and steady watts are
both already in InfluxDB continuously, so the correlation can be re-run at any
time - capturing temperature alongside the subgroup would be redundant.
The autumn cool-down measures the slope over a real lever arm for free. Re-run
the regression once the basement has dropped ~5 degF and compensate then, on
measurement rather than extrapolation.
```

### P9 — the leak alarm watches the wrong field, and it already missed one [HIGH]
```
NOT theoretical any more. From InfluxDB (the decode fields are historised as
fields on the "gal" measurement, so this history predates the sensors):

  LeakNow  0 -> 1  at 2026-08-21 14:43
  LeakNow  1 -> 0  at 2026-08-22 11:28      ~20.7 h continuous-flow flag
  Leak     0 throughout                     <-- the alarm's trigger NEVER MOVED

So automation.sdr_water_leak_flag, which triggers on Leak > 0, would not have
fired for a 21-hour event its own meter detected.

Consumption during the flag window, from the count deltas:
  deep night 23:00-05:00   1.6 gal / 5.00 h = 0.32 gal/h  (7.7 gal/day)
  overnight  22:00-06:30   4.6 gal / 7.97 h = 0.58 gal/h  (13.8 gal/day)
Roughly hourly +0.1 gal ticks through the night with the house asleep - the
signature a register reads as continuous low flow. Small: a flapper seep, a
dripping fixture, or a softener/humidifier bleed, not a burst pipe.

HONEST LIMITS: decode history starts 2026-08-21 13:28, so ~24 h total - this
may be chronic or a one-off, and there is no way to tell yet. InfluxDB writes
are ~15 min apart, so sub-interval continuity cannot be confirmed from this
data; the meter's own register has finer resolution than the samples here.

ACTION: add a second trigger path on sensor.water_meter_leak_now > 0. Keep the
Leak trigger - it is the OUTAGE BACKSTOP (see the ENTITIES note: detection is
in the meter, so the 35-day day-bin count still tells you about a leak that
happened while HA or the SDR was down). LeakNow is the immediate signal;
Leak is the one that survives your stack being off.
```

### P8 — hvac_ac_blower_daily / _monthly were never created [LOW]
```
RESTORED 2026-08-22: this entry was accidentally deleted earlier the same day
when P9 was inserted over the top of it. Recording that because a PENDING item
that vanishes silently is worse than one that is never written.
Documented in ENTITIES as utility meters; present in no config file and no
registry entry. scripts/seed_ac_blower_energy.py seeds _daily, so it seeds
nothing. sensor.hvac_ac_blower_power and _energy DO exist. Commented out in
ENTITIES rather than guessing. Create the meters or retire the script.
```

### INFO HYGIENE (2026-08-23)

**An INFO that fires every run and cannot be actioned is noise, and noise
trains you to skim.** Applied to all five that were being emitted:

| was | now | why |
|---|---|---|
| `eod: no fixed trigger time` | silent | `at: null` is already an explicit declaration; re-reporting it is the checker narrating itself. Only a *missing* `at` key warns now (`eod-undeclared`). |
| `eod-concurrent` x2 | one summary line | CLAUDE.md says sharing a second is not a problem. "Checked, found nothing" is worth one line, not one per group that reads like a finding. |
| `legacy-backup-drift` | WARN, then actioned | An open decision, not information. Criterion was met, so the command was retired and the rule now returns early when it is absent. |
| `live-check-skipped` | WARN | A check that did not run is a coverage gap. See P13. |

The remaining INFO is a single line proving the EOD contention check executed.
If a line cannot change what you do, it does not belong at INFO either.

### P11 — SCM tamper baselines need history before they can alarm [LOW]
```
gas       TamperPhy 3 on all 61 frames ever received; TamperEnc 0
electric  TamperPhy 0 on all 1,704 frames;            TamperEnc 0
A constant is a meter-type characteristic, not an event — alarming on the
VALUE would fire forever and be muted within a day. The signal is a
TRANSITION. Sensors exist now so history accumulates; add a change-detect
alarm once gas has a few weeks of frames. 61 frames is not a baseline.
```

---

### Closed — full detail is in CHANGELOG.md, not here

```
P1    `default: []` on every choose:                             RESOLVED
P4    phantom entity references                                  RESOLVED
P5    fabricated limit constants                                 RESOLVED
P6    statistics sampling_size                                   RESOLVED
P7    R900 leak sensors                                          RESOLVED
P10   rtlamr2mqtt duty cycle                                     DEPLOYED
P12   InfluxDB CQs retired, Grafana SPC re-sourced               RESOLVED
P13   statistics-buffer check                                    RESOLVED
```
## CHANGELOG — see `CHANGELOG.md`

Removed from this file 2026-08-23. It was a second, hand-curated summary of
`CHANGELOG.md`, and by R10 a second copy of a definition is a copy that will
drift — the same defect `pipelines.yaml` exists to end, and the same one that
put the InfluxDB CQs 9.0 W away from the HA charts for a month.

Append behaviour changes to `CHANGELOG.md`. Do not summarise them back here.

