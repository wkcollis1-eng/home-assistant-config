# rules-history

Scars behind the numbered rules and CONSTRAINTS in CLAUDE.md: the dated
incidents that earned them. CLAUDE.md holds the rule and a one-line why;
this file holds the evidence. Add a new scar here in the same commit as
its rule (R13).

Moved verbatim out of CLAUDE.md on 2026-09-16 so it loads only when
needed. "Above"/"below" in this text may point into CLAUDE.md.

---

### RULES preamble, before 2026-09-16

Each rule states the ACTION, then the failure that earned it. A rule with no
scar is a preference; every rule here has one, and it is dated.

### R2

*2026-08-22: two new audit rules produced false FAILs — a substring match and a
slugify comparison that ignored the registry. Only the two-direction test found
them.*

### R6

*2026-08-22: recommended `listen_mode: true` for rtlamr2mqtt by reasoning about
what it ought to mean. Reading `meter_reader.py` showed it is a DISCOVERY mode
that publishes nothing — it would have taken the whole SDR stack dark.*

### R7

*2026-08-22: `ha_audit.py` vouched for an entity that had never existed, because
`known_entities()` synthesised `<domain>.<unique_id>`. The rule that should have
caught a 15-night outage was structurally incapable of it.*

### R8

*2026-08-23: the statistics-buffer check had never run in production. It
reported at INFO, so nothing distinguished "looked, found nothing" from "never
looked".*

### R9

*2026-08-22/23: `0 means no data` is the SPC convention; the overnight-flow
buffer inverts it (0.00 gal/h is a PERFECT night, -1 means no night). That single
inversion had to be caught separately in the mean sensor, the chart JS, and the
audit rule before it was declared once in the manifest.*

### R10

*2026-08-22: `pipelines.yaml` exists because five copies drifted;
`scripts/spc_seed.py` was a sixth; the InfluxDB CQs a seventh, and they had the
Grafana dehumidifier panel 9.0 W off the HA chart and permanently below LCL.*

### R11

*2026-08-23: 7.64 W/degF was fitted over 1.5 degF and then applied across
11.5 degF — the same 8x extrapolation error the 2026-08-07 note made in the
opposite direction on a 0.78 degF lever arm.*

### R14 - the incident

*2026-08-24: needed to know whether the basement router's plug hangs off the UPS,
because if it did, summing it with `ups_outlet_current_consumption` would
double-count by ~65%. Asked once, then answered a different question he raised
and treated that as licence to infer. Cost: a natural-experiment search across 13
days, then a coincident-step test over 843 events, to conclude PARALLEL — which
he could have said in one word. The first script I wrote for it had already
printed its own verdict:* `Do not guess - ask which outlet feeds what.` *Writing
that line and then not following it is the whole failure.*


### R14 - mechanised as open_questions.yaml

**MECHANISED 2026-08-25: `open_questions.yaml`.** R14's failure mode was not
forgetting to ask, it was asking and then losing the question - so "remember to
re-ask" was never going to hold. Every question to Bill gets an entry with
`asked:`, `question:`, `blocks:` and `answered:`. `ha_audit.py` WARNs
`open-question` for every unanswered one, with the days outstanding, and
because the session protocol reads the audit verdict aloud at start-up, an
unanswered question is now surfaced at the top of every session by a mechanism
that does not depend on any session remembering anything. `blocks:` names what
stays unbuilt until he answers.


### R15

*2026-08-25: the gas meter's hop set was reconstructed from plot markers and then
reported in the same voice as the electric meter's stated 909.59-921.78 MHz. One
was [S] and the other was [I], and nothing in the text said so. Two config
changes were proposed on the strength of the [I] before the data refuted it.*

### R16

*2026-08-25, twice in one day: Itron 50/51/52/53ESS channel figures quoted for a
meter that turned out to be a Vision VM1991 with a Hunt AirPoint radio, and the
EWQ100GDL* band plan quoted for a gas module whose behaviour matches EO9100G.
Both were introduced to Bill as "primary sources".*

### R17

*2026-08-25: water "87.5%" on 8 slots, electric "56.7%" on a 5.7-minute sample,
and "electric 1.12x / water 0.95x" from the 915.5 run - the last two were z=+0.56
and z=-0.19, i.e. nothing, and were reported as findings.*

### R18

*2026-08-25, the same error twice in one day without noticing: the water meter's
"28.000 s grid" was our receiver seeing every other 14 s transmission, and the
electric counter's "86 s tick" was our 32 s sampler reading multi-unit jumps as
single ticks. True values 14.0 s and 53.8 s. Both were the instrument's blind
spot mistaken for a property of the world.*

### R19

*2026-09-16: a generated UPS view left 24 apexcharts `y:` keys bare; the paste
stored them as `"true"` and every threshold line on six charts vanished with every
gate passing. Five more had sat unnoticed in the dehumidifier view.* Gate:
`dashboard-bare-boolean` before a paste, `dashboard-boolean-key` after one.

### R20

*2026-09-23: at a 400K window over 09-16..09-23, 13 of 29 Reads after a compaction
re-read a file read before it [M, n=29 Reads, 5 compactions] - detail the summary
did not carry. The session-start audit verdict, added by a hook, is only
summarised at a compaction, because the audit hook matches `startup|resume`. The
same day Bill lowered the auto-compact window to 200K for a cost trial, which
multiplies compactions (28 a week against 1 at 400K [I, transcript replay]), so the
loss would have multiplied with it.* Gate: `context_hygiene.py` `posttooluse` and
`sessionstart` (matcher `compact`); 58 checks, 10 of 10 mutations caught. Two of
the new tests first let a mutation through - each claimed a case it never built.

### CONSTRAINTS - dashboards/ is a source copy

Earned 2026-08-23: P12 repointed two rows at `utility_electric_power_avg`, all
gates passed, and the card went on reading the superseded
`utility_electric_power_mean` — so it showed a 60-min mean from the old sensor
beside a delta and error computed from the new one, and the arithmetic on screen
did not close (394 - 398 displayed as +1 W). The user spotted it from the card.
Every earlier dashboard change this session landed correctly, because those were
handed over as YAML to paste rather than written to the file.

**Re-earned 2026-09-14, harder:** a session hand-edited
`dashboards/lovelace/lovelace.yaml` directly — twice, including a 716-line new
view — without registering the file's own "DO NOT HAND-EDIT" banner, and had
a deny rule on that path *removed* to make the second edit possible. Had
`export_dashboards.py` run before the new view was pasted live, it would have
been silently deleted with nothing but a printed warning to notice. It happened
to survive only because the paste beat the next script run. The deny rule was
restored the same session; the fix that should have been reached for instead
was `dashboards/views/heating-hvac-diagnostics.yaml`, which was never
permission-denied and never needed to be.

### CONSTRAINTS - validate against the deployed artifact

  Both of the 2026-08-21 regressions came from trusting docs over the artifact:
  apexcharts-card's documented `data_generator(entity, hass, index)` is really
  `AsyncFunction('entity','start','end','hass','moment', "'use strict'; "+body)`,
  so `const end = ...` was a SyntaxError that hung the card on "loading"; and
  the `statistics` platform's availability propagation was inferred from state
  timestamps for an hour when `components/statistics/sensor.py` settled it in
  one read. `.HA_VERSION` makes the exact source cheap to fetch — use it.

### CONSTRAINTS - entity annotation is NOT ENFORCED

**NOT ENFORCED, and this used to say MUST.** Measured 2026-08-26: 236 of 410
YAML-declared entities carry no annotation. A rule with a 236-case backlog is
not a rule, and a check for it would open with 236 findings - the noise the
INFO HYGIENE section says trains you to skim. `generated-doc-stale` cannot help
either: it only asks whether ENTITIES.md matches what the generator WOULD
write, so an unannotated entity leaves the doc "current" while the config
references something the doc does not mention.

Earned the same day: `binary_sensor.ha_eod_contention` and
`input_number.ha_eod_contention_count` shipped in 2d1acd3 with no annotation
and nothing caught it. Reworded rather than mechanised, because the enforcement
table above sets the standard - be honest about which rules are mechanised,
since a rule everyone believes is enforced and is not is worse than one known
to rest on judgement.

### DEFINITION OF DONE - why a validator alone is not the gate

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


### DEFINITION OF DONE - step 2b history

               The rule-id inventory is DERIVED from ha_audit.py's source, so
               it cannot drift the way the three hand-kept counts in this file
               had by 2026-08-25. Direction 2 now asserts per rule that a
               covered rule does NOT fire on a clean tree, instead of demanding
               the whole tree be finding-free - so a genuine WARN in the house
               no longer fails the suite, which contradicted step 2 above.

### DEFINITION OF DONE - rules that carry over; STEP 0 (merged into OUTPUT FORMAT)

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


### OUTPUT FORMAT - explain your reasoning

**Explain your reasoning.** The previous version of this section said "output
ONLY ... never explain unless asked", and it was dead law: every message of the
2026-08-22/23 session broke it, and the explanations are precisely what caught
the `listen_mode` error before deployment, the `-unique` trap, and a `MEAN()`
over a step-function limit. A rule that would have made the work worse is not a
rule, it is a habit that outlived its reason.


### PRE-COMMIT CHECKLIST - removed items

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

### ENTITIES - why it moved out

Why it moved out of this file (2026-08-23): the block was 548 lines, 32.8% of
CLAUDE.md, loaded into context every session — and **16 of its 328 ids did not
exist**, two of them behind alerts that could never fire. A hand-maintained list
that CONSTRAINTS calls the only permitted source of ids is a defect generator:
a wrong entry is this file instructing you to use a name that resolves to
`unknown`.


### AUTOMATIONS INDEX - duplicate of the PACKAGES paragraph

Design notes about a package belong in that package's own header comment,
beside the code — not in a summary that has to be kept in step with it.


### KNOWN ISSUES - 23:58:00 collision entry

23:58:00 collision              STALE ENTRY, corrected 2026-08-25: there is no collision. Measured across all
                                111 time-triggered automations — 23:58:00 holds accumulate_filter_runtime ALONE;
                                archive_monthly_hdd has moved to 23:58:15. Kept rather than deleted (R13) because
                                a hand-cleared "no data risk" judgement outlived the arrangement it described,
                                which is the drift this file exists to catch. The only shared seconds in the live
                                config are 00:00:00 x2, 23:59:00 x6 and 23:59:30 x2, none of them contending.
