# Changelog

All notable changes to this Home Assistant HVAC monitoring configuration.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Calendar Versioning](https://calver.org/) (YYYY.MM.DD).

## [2026.08.24] - 2026-08-24

### Dehumidifier dashboard audit — 7 config fixes, 25 dashboard corrections

Audited the dehumidifier view against the deployed artifact
(`.storage/lovelace.lovelace` view 8), the live API, and InfluxDB. All 91
entity references resolve; no phantom ids. What follows is what did not.

**Daily cost was 21 % high, and the constant was the reason.**
`sensor.dehumidifier_daily_cost` computed `runtime_h * 0.568 kW * rate`. The
0.568 was a second copy of the machine's power draw and it had drifted off the
machine: the E080 measures 468.7 W (0.523 kWh / 1.1158 h on 2026-08-24) and
`dehumidifier_running_watts_mean_7d` independently reads 467.3 W. It was also
the wrong shape — runtime is switch-on time, which includes ~57.8 W fan-only
sampling that the constant priced at compressor watts. Now
`dehumidifier_energy_daily * electricity_effective_rate`: a measurement times a
rate. Observed at deploy: 0.17 -> 0.14, YTD 50.41 -> 50.38. The 2026 YTD total
is a blend of two methods either side of this date.

**Three fallbacks disagreed with the helpers they stood in for.** Each was
silent, and each moved a guard:

| where | fallback | helper | effect if the helper went unreadable |
|---|---|---|---|
| `dehumidifier_compressor_active` | `float(250)` | 150 | gate moves 67 %; a running compressor at 150-250 W reads OFF |
| `dehumidifier_rh_stall_shutdown` | `float(0.15)` | 0.05 | runs a 3x stall threshold |
| `dehumidifier_max_runtime_backstop` | `float(4)` | 2.0 | runaway cap DOUBLES to 4 h |

The first two now gate on `is_number()` and go silent instead of substituting a
number — safe because the backstop keys on `switch.dehumidifier` and
`last_on_time`, not on `compressor_active`. The backstop itself must never
disable itself, so it keeps a literal, moved to the conservative end and
documented as deliberately NOT a copy of the helper. Proven both directions
against the live instance: with the threshold helper made unreadable the old
stall condition returned True and the new one returns False.

**`input_select.dehumidifier_last_stop_reason` could not survive a restart.**
It carried `initial: unknown`, and an input_select with `initial:` does not
restore — HA forces that value at every start. The last stop reason was erased
by every restart, at the one moment you most want it. Removed. Proven by
observation rather than inspection: it came through this deploy as
`conditions_cleared`.

**The stall detector could not fire, and is also switched off.** Its gate
required >90 min of continuous runtime, sized for the Santa Fe at ~6.9 h/day.
Over 151 completed E080 cycles from 2026-08-05 to 2026-08-24 the distribution
is p50 15.2, p95 21.1, p99 30.0, max 30.4 min — so the gate was unreachable,
the R7 failure mode where a rule that cannot fire looks like a rule with
nothing to report. Rebased to 40 min: 0 of 151 healthy cycles reach it, 32 %
clear of the observed max, well past the 10-14 min steady window. It is a
warmup skip, not the discriminator — the DP-rate test is. NOTE:
`automation.dehumidifier_rh_stall_shutdown` is currently `off` (last triggered
2026-06-29), so the rebase changes nothing until it is re-enabled.

**`gen_reference.py` documented 43 utility meters under ids that cannot exist.**
It emitted `utility_meter.<key>`; `utility_meter` is a component, not an entity
domain, and it creates `sensor.*` ids from `name:`. 42 of the 43 also have no
registry row, because a YAML utility_meter without `unique_id` is never
registered — so they were invisible to BOTH sources CONSTRAINTS names as the
only permitted ones, including `sensor.sem_ac_daily`, which `pipelines.yaml`
declares as the guard source for `capture_daily_cooling_kwh_cdd`. Same defect
class as the `known_entities()` synthesis that earned R7. Fixed by deriving the
id the way HA does. Deliberately NOT fixed by adding `unique_id` to the meters:
that re-derives entity_ids, and `restore_state` and InfluxDB both key on
entity_id — the failure `dehumidifier_running_watts_latched` already carries a
DO-NOT-FIX comment about.

**Dashboard: 25 corrections**, handed over as YAML rather than written live,
because `dashboards/` is a source copy HA never loads. The substantive one: the
RH Envelope card computed its condensation ceiling from the bank pack alone
while `sensor.basement_condensation_margin` takes `min(pack, manual override)`.
They agreed only because the pack happened to be colder. With a 58 degF slab
entered, the real ceiling is 49.4 % and the recommendation 47.4 %, against the
58.0 % the card would still have printed. The rest were stale literals — 250 W
against a helper at 150, 0.15 degF/h against 0.05, "set 30" against 10,
"2.5 = 150 min" against 2.0 — now computed from the helpers so they cannot go
stale again. Also: a `y: 70` annotation that could never draw against an axis
capped at 62; a cross-check chart plotting smoothed RH while the flag beneath it
uses raw; "RUNNING" shown while the compressor was off at 54.6 W; and a line
reading "last local-control run ended after 500.5 h", which was time since the
stamp, not a duration.

**Card 4 settled from the firmware** (R6). `esphome/basement-th-node.yaml` was
in the repo the whole time while the card said the node YAML "is not in hand".
The rates are 60 s least-squares slopes over a 180-sample ring, Rev 2.2, marked
DIAGNOSTIC ONLY. A least-squares slope carries the natural sign, so they ARE on
the canonical convention; only the degC/h unit on `t_rate_30` differs.

Gates: `validate_ha.py --strict` PASS (parse-clean) on both files; `ha_audit.py`
0 FAIL / 0 WARN / 1 INFO, unchanged from baseline; `test_ha_audit.py` SUITE
PASSED (gen_reference moved); `check_config` **valid, 0 errors, 0 warnings**;
restarted 2026-08-24, 1574 entities before and after. R3: 7,406 of 7,414 lines
untouched in configuration.yaml, 4,374 of 4,388 in automations.yaml, 375 of 376
in gen_reference.py; every file reverses byte-identical.

NOT done, deliberately: the duty/kWh `empty_sentinel: -1` work and the duty
chart's `max: 20` axis (both held by Bill), and the flat-zero "Last season
total" series, which self-populates at the January reset.

### Backup essentials card — already deployed; the handover was wrong

The 2026-08-24 10:15 handover said `dashboards/cards/backup/essentials-overview.yaml`
had never been pasted in. It had. `.storage/lovelace.lovelace` was modified at
10:12 — three minutes before that handover was written, and one `json.load`
away (R6). Verified structurally: the live card is view 6
(`battery-bank-dashboard`), `sections[0].cards[36]`; parsing the live JSON, the
repo YAML and the user's paste, normalising Jinja whitespace and deep-diffing
all three returns **0 differences**. The 309 to 199 line gap is comments and
block-scalar style, which the JSON store strips.

OBSERVE, which that item's existence had skipped: all 27 entity references
resolve; `amps_at_bank_v` = 7 and `age_coverage_ratio` = 0.02 both present. The
router indent is arithmetically honest — `packages/backup_sizing.yaml:89`
defines `monitoring_load` as HA host + UPS outlet + basement router, and the
live values close exactly (11.8 + 16.6 + 11.1 = 39.5).

Two rows read UNKNOWN, neither a defect: `input_button.reset_load_peaks` (state
is last-press, does not restore) and `battery_bank_monitor_runtime_remaining`
(bank IDLE at 99.99% SOC). Both date to the 10:06 restart.

The card's "filling" gate is `age_coverage_ratio >= 0.9`, not 1.0 — 21.6 h of
coverage, so the tile becomes quotable about 2 h 20 m earlier than the
handover's stated 24 h.

### Restart persistence — already implemented at all three layers, no change made

Asked whether `backup_essentials_avg_24h` should be made restart-persistent. It
already is, verified against the source at the pinned `.HA_VERSION` 2026.8.3:

| layer | mechanism |
|---|---|
| `backup_essentials_energy` (integration) | `class IntegrationSensor(RestoreSensor)`; `async_added_to_hass` restores the accumulated total from `.storage/core.restore_state` |
| `backup_essentials_energy_rate` (statistics) | `_async_stats_sensor_startup` then `_initialize_from_database` re-reads `max_age` (24 h) of source history from the recorder; `limit=sampling_size` 1600 vs 1,440 samples |
| recorder retains the source | `exclude:` names 8 entities, none in this chain; `purge_keep_days: 14` |

The 0.02 coverage was not a persistence defect — the accumulator was born at the
10:06 restart, so there was nothing valid to restore. Pre-10:06 `_sampled` rows
exist but are `unavailable` (it guards on the integral, and the integration
platform was not running — the P18 note), and `_add_state_to_queue` skips
`STATE_UNAVAILABLE`. Confirmed numerically: `age_coverage_ratio` and
`buffer_usage_ratio` both 0.02, fitting a 10:06 start; a 09:56 start rounds to
0.03 on both.

### InfluxDB read access for off-host sessions

Read-only influx user `ha_ro` created; `secrets.yaml` gained `influxdb_url` /
`influxdb_db` / `influxdb_user` / `influxdb_pass` (gitignored, `.gitignore`
line 2, re-verified). CLAUDE.md's INFLUXDB section documents the load order —
**environment first, file second**, so a shell export still overrides and
nothing that worked before changes. The rule that earned it is unchanged: never
a credential in a TRACKED file.

First attempt returned HTTP 403, not 401 — authentication succeeded and the
GRANT was missing. `GRANT READ ON "Home Assistant" TO "ha_ro"` fixed it; the
database name needs quoting because of the space.

### Essentials load baseline — 43 days, and a retracted first answer

**The first answer was wrong and is recorded rather than replaced (R13).** A
daily `INTEGRAL(...) GROUP BY time(1d)` over an OPEN-ENDED range reported
2026-07-12 at 1628 W with `sem_fridge_power` at 954.9 W. That was not bad data:
InfluxDB's INTEGRAL carries the last point BEFORE a gap forward, so the first
bucket after an 11-day hole absorbed the entire hole's area. Bounded to start
after the gap, the same day and channel read 58.8 W, and its 11:00-23:00 hours
were normal all along at 95-120 W. The tell that was missed: "45 complete days
out of a 55-day span" had already been observed, and nobody asked what the
missing ten were.

Corrected method: per-day BOUNDED integral (no cross-gap carry possible) plus
explicit head/tail rectangles carrying the last known value across the day
boundary — these series write on state change, so a channel silent overnight is
unchanged, not missing. Day admitted only if the SEM was up 23 h or more,
measured by `sem_fridge_power`'s first-to-last span (it writes every ~3 s, so it
is a true instrument heartbeat). An earlier filter requiring that span on EVERY
channel was wrong for the same reason and discarded 34 of 55 days.

```
43 days, 2026-06-30 .. 2026-08-23
  mean            275.6 W
  median          291.3 W
  sd               76.1 W
  95th percentile 382.8 W
  WORST DAY       452.9 W  on 2026-08-07
```

Cross-checks: worst day 452.9 W vs 451.4 W from long-term statistics by a
different path; validation on the 17.9 h where the real sensor exists gave
`backup_essentials_load` 247.0 W by INTEGRAL, 245.8 W by recorder Riemann-left,
246.6 W by LTS. `ha_n100_pc` + `ups_outlet` exist only from 2026-08-05/06, so
earlier days hold the pair at its measured constant 25.44 W (n=18, sd 1.25 W).

EXCLUDED 2026-07-01 .. 2026-07-12, and not a SEM-only fault: in that window
every series is sparse — Kasa router 255 points, Shelly 255, outdoor temp 245
across 11.5 days against thousands/day — with SEM worst at 8, landing exactly on
the hour. Stack-wide logging degradation that ended when the SEM was
power-cycled at 2026-07-12 11:02.

### The furnace ECM has no inrush — and a second retraction

The winter blower was expected to draw less because it is an ECM, measured at
350-400 W on a Kill-A-Watt with the surge in doubt. Against 1,176,064 samples of
`sem_furnace_power` from 2026-07-13:

```
                   median running   p99.9      max     max/median
furnace ECM             772.1 W    845.4 W   864.1 W      1.1x
fridge (control)        109.9 W    568.8 W  2365.2 W     21.5x
```

The same instrument at the same 2.0 s cadence resolves 21.5x on the fridge, so
it demonstrably catches inrush where inrush exists. 21 start events inspected at
full resolution all step 13 W to ~112 W in one sample and settle with zero
overshoot. **There is no blower surge to miss.**

**RETRACTED, same session:** the claim that 350-400 W was "independently
plausible" by cube law (heating CFM "typically 70-80%" of cooling) used a
generic ratio instead of this equipment. The baseline repo nameplate — American
Standard Silver 95 `S9X1C100U5PSBA`, 1 hp constant-torque ECM rated 746 W max,
hot surface igniter — makes it untenable: measured cooling median 772 W is
already at full tap, and 95,000 BTU/hr output needs at least ~1,370 CFM to hold
temperature rise under 65 degF against ~1,600 CFM cooling. Cube law then gives
**470-750 W**, not 400. Three figures now disagree — repo 210 W, Kill-A-Watt
350-400 W, nameplate-constrained 470-750 W — and if the winter blower is near
500-700 W the winter essentials load is comparable to or higher than summer,
inverting the sizing assumption. Owner decision: wait for the first heat event
and settle it by measurement; the repo's 210 W stands untouched meanwhile.

No heat call exists in the record. Outdoor minimum was 53.3 degF — below the
59 degF balance point — yet the coldest days show the same ~850 W cooling
maximum, and the running histogram is single-moded: 169,588 of 171,316 running
samples in 700-800 W.

### Reference-doc audit — six defects, two of them able to cause wrong actions

- **`gen_reference.py` truncated entity ids silently.** `[:46]` on the trigger
  summary, `[:40]` on the entity list and `[:70]` on package domain counts, with
  no ellipsis — so `binary_sensor.hvac_ac_short_cycling_alert` was published as
  `binary_sensor.hvac_ac_short_cycling_aler`, indistinguishable from a real id.
  16 ids in AUTOMATIONS.md affected; PACKAGES.md showed `shell_comman`, `sens`,
  `scrip`. Replaced with `_clip()`, which drops WHOLE items and says how many
  (`+2 more`), and returns a single over-long item intact — correctness beats
  alignment. The trigger column width is now computed rather than fixed.
- **`ha_audit.py` gained `rule_doc_ids`**, covering the gap `rule_generated_docs`
  left: hand-maintained prose. `dead-constraint` FAILs on an entity id in
  CLAUDE.md CONSTRAINTS that does not resolve; `truncated-id` FAILs on any id in
  a generated doc that is a strict prefix of a real id. Tested both directions
  (R7): 17 findings with faults injected, silent on the clean tree.
- **Dead CONSTRAINT removed.** The NEVER-rule guarding
  `sensor.shelly_plus_uni_voltge` protected an entity that exists nowhere — not
  in the 1,857 known ids, not in any YAML, and no Shelly Plus Uni device is
  installed. `docs/ha-validator-checks.md` annotated; the vestigial
  `PROTECTED_ENTITY_IDS` entry was left in the vendored `validate_ha.py`
  deliberately, to avoid widening the documented drift.
- **Stale KNOWN ISSUE removed.** `shell_command.testcmd` was listed as open at
  `config.yaml:16`; there is no `config.yaml`, and `configuration.yaml:20`
  records it removed 2026-08-22.
- **EOD SCHEDULE relabelled.** It claimed to be generated from `pipelines.yaml`
  and not to be hand-edited. Nothing generates it; `ha_audit` validates it. A
  session obeying the label would find no generator, leave it stale and fail the
  audit.
- **FILE MAP package listing deleted (R10).** It was a second copy of
  PACKAGES.md and had drifted: spc.yaml 1,787 vs a real 3,610,
  configuration.yaml ~6,500 vs 7,415, automations.yaml ~2,500 vs 4,388, with
  audit.yaml, backup_sizing.yaml and utility_meters.yaml missing entirely.
- **CLAUDE.md violated its own R10.** "Rules that carry over from 2026-08-22"
  restated R3, R4, R5, R6 and R7 in different words with the same scars.
  Deleted in favour of a pointer — the R10 answer is deletion, never a checker
  that keeps two copies in step.

### Session protocol — off-host invocation documented

`python3` does not exist on the Windows box; `HA_CONFIG` and `HA_URL` are both
required or the audit either cannot find `pipelines.yaml` or silently skips the
live statistics-buffer check and reports `live-check-skipped` (a real coverage
gap under R8, not an environment quirk). `git` refuses `H:` with "dubious
ownership". All four are now in the SESSION PROTOCOL block.

## [2026.08.23] - 2026-08-23

### SDR reception re-measured — rate confirmed, antenna ruled out

Re-measured because 2026-08-22 recorded 69% capture from a 7-minute sample and
concluded antenna work was worth doing. **The rate held; the conclusion did not.**

**Water capture is 71.3%.** Water is the only meter that can be given a capture
rate at all, because R900 sits on a strict 28 s grid — every gap observed in 20
minutes of frame-level sampling was 28 or 56 s and nothing else. Three
independent instruments agree:

```
  20-min frame poll, direct         16x 28 s, 14x 56 s -> 30/44 = 68.2%
  12-min hand check of minute ticks mean age 27.5 s    ->        67.5%
  16.6 h of minute ticks (993)      mean age 25.3 s    ->        71.3%
```

The last is the one to quote: 993 ticks, exactly the expected count for the
window, hourly range 68.6-72.7%, sd 1.2 pp.

**Yesterday's "packet drops" were mostly the duty cycle, not RF.** The hourly
grid steps once, at 08-22 19:00, exactly when `sleep_for` went 60 -> 0. Share of
samples with `_age` over 2 min: water 5-13% -> 0.0%, gas 5-16% -> ~2%, electric
2-16% -> ~1.5%. The apparent daily rhythm in the 3-day summary (worst at noon,
18:00, 02:00) was a confound — the pre-fix period dominated those hour buckets.
Post-fix there is no time-of-day effect.

**The losses are not signal strength, and this is the strong result.** On a 28 s
grid with independent capture p, `P(age >= 28j) = (1-p)^j`. At p = 0.713 that
predicts **125 double-miss (84 s) gaps** across the window. Observed: about one.
Max age seen in 993 ticks was 78 s; ticks above 56 s numbered 1 against 82
predicted. P(observing <=1 when expecting 125) = 5e-53.

Roughly 29% of frames are lost and **two are essentially never lost in a row.**
RF fading is correlated in time — a fade spans many frames — so a weak-signal
link clusters its misses. This one anti-clusters, about as hard as a process can.
Contention was tested separately and also fails: the 28 s grid gives every missed
frame a known arrival time, and missed slots were no more crowded by SCM decodes
than received ones (0% vs 22% within 2 s).

**The losses are phase-locked to a 5-transmission cycle.** Indexing the 28 s
slots and taking the phase mod 5, over two captures totalling 143 slots:

```
                run 1 (20 min)   run 2 (45 min)   combined
  phase 0          9/ 9            20/20          29/29   100%
  phase 1          0/ 9             0/20           0/29     0%
  phase 2          9/ 9            20/20          29/29   100%
  phase 3          4/ 9             7/19          11/28    39%
  phase 4          9/ 9            19/19          28/28   100%
```

Every missed slot fell in phase 1 or 3; P(that by chance in run 1 alone) = 1.8e-8.
The two runs are 12 minutes apart and share ONE grid - referencing both to a
common epoch gives a residual of 0.0000 slots - and the SAME absolute phases are
clean in both. The cycle is locked to the meter's own clock and has not drifted.

**Phases 0, 2 and 4 are 86 for 86.** That single number is the cleanest
refutation of a signal-strength explanation available in this data: zero misses
in 86 consecutive opportunities is an enormous link margin. Marginal SNR does not
sort itself by phase - it scatters failures across all of them. This link has
margin to spare on three transmissions in five and receives nothing whatsoever on
a fourth.

Confirmed a third time in data the poller never touched. A 140 s (5 x 28 s)
cycle sampled once a minute beats at lcm(60,140) = 420 s, so it must show as
autocorrelation at lag 7 min in the tick-age series. Across 978 contiguous
minute ticks: **lag 7 = +0.673, lag 14 = +0.828**, with anti-phase troughs at
3, 4, 10 and 11, against a noise band of +/-0.064. That covers 16+ hours, and
the underlying schedule is rigid - every single-slot gap measured exactly
28.000 s, every double exactly 56.000 s, sd 0.000.

**This is what rules out gain and antenna position, and it does so without
needing to know the mechanism.** The loss depends on WHICH transmission in a
fixed rotation it is, not on how strong the signal is. Gain and placement act on
signal strength, and they act on every transmission alike; neither can fail 2 of
5 phases while the other 3 run 27 for 27. A phase sitting at 0 of 9 also does
not look weak - it looks absent, which is a tuning or passband condition rather
than a margin condition.

**The mechanism itself is NOT identified here and is not guessed at.** The
candidates - a channel plan the tuned window only partly covers, or a message
variant the decoder handles differently - would be separated by reading
`bemasher/rtlamr` `r900/r900.go` against a captured IQ file, which has not been
done. What the data settles is narrower and sufficient: **moving or re-aiming
the antenna has no measured headroom to recover, and neither does gain.**

**Gas and electric capture rates cannot be computed and are withdrawn.** Their
gaps run 7, 8, 9, 13, 16, 22, 45, 89, 117, 150, 241 s with no quantisation, so
SCM does not transmit on a fixed cadence and there is no denominator. Figures of
53.6% and 66.0% quoted mid-analysis assumed a 31 s grid the histogram disproves.
What is measurable, and what the alarms actually depend on: gas heard every ~78 s
mean, worst silence 241 s; electric every ~32 s, worst 117 s. Gas being slower is
expected — battery-powered, where the electric ERT is mains-powered.

**Nothing operational is degraded.** Water is heard every ~39 s against a 10-min
LeakNow hold; gas against a 360-min stale threshold. Margins are one to two
orders of magnitude.

**The thermal cost of `sleep_for: 0` is real, bounded, and has settled.**
Basement ambient was flat at 70.2-70.6 F across the window, so no seasonal
confound, and rise-above-ambient is the load-invariant quantity:

```
  pre-change    67.0 F rise   cpu 10%
  post-change   74.0 F rise   cpu 15%    delta +7.0 F
  post window first half 73.7 F -> second half 74.3 F   (+0.6, settled)
```

Still host CPU — the dongle exposes no temperature.

### rtl_tcp sample rate 2048000 -> 2359296: no effect. A null result, recorded

Changed 2026-08-23 21:16 to rtlamr's native rate for symbollength 72, ~15% more
bandwidth (+/-1.180 MHz against +/-1.024 MHz). The hypothesis was that a wider
capture window might reach the hop channel that phase 1 sits on. It did not.

**Capture rate, 10.7 h post against 25 h pre, same unbiased minute-tick
estimator:**

```
  water     71.1%  ->  71.0%      (hourly sd 1.3 pp - this is zero)
  gas       42.3s  ->  42.6s      mean age
  electric  36.1s  ->  35.2s      mean age
```

**The phase structure is untouched, and the proof is unusually clean.** A frame
capture 20.3 h after the pre-change one, referenced to the SAME epoch:

```
   phase     PRE            POST
     0      9/9  100%     13/13  100%
     1      0/9    0%      0/13    0%
     2      9/9  100%     13/13  100%
     3      4/9   44%      6/13   46%
     4      9/9  100%     13/13  100%
```

Both captures sit on one 28.000 s grid with a residual of 0.0000 slots, so the
meter's cycle is locked to its own clock to within the 1 s timestamp resolution
over 20.3 hours - under about 7 ppm of drift. **The same ABSOLUTE phase is dead
before and after.** Across both captures the three good phases are 66 for 66 and
the dead one is 0 for 22.

**Cost:** +1.6 F rise above ambient, +0.2 pp CPU on MATCHED CLOCK HOURS. A first
pass compared a daytime PRE window against an overnight POST window and appeared
to show CPU FALLING - the same diurnal confound that faked the "worst hours"
reception pattern on 2026-08-23. Matched hours reverse the sign. Do not compare
a daytime arm against an overnight one on this host.

**The payload carries no per-slot variation.** Captured 29 frames over 19.6 min
with rtlamr's undecoded R900 fields attached, to see whether the meter varies its
MESSAGE across the 5-cycle. Every decoded field was constant on every frame and
every decoded phase: `Unkn1` 163, `Unkn3` 0, `NoUse` 35, `BackFlow` 0, `Leak` 0,
`LeakNow` 1. The same 3-full / 1-partial / 1-dead structure appeared again.

What that settles and what it does not. The phases that DO decode do not differ
in message content, so the cycle is not the meter rotating through message types
it then sends identically well. But the dead phase emits nothing, so its payload
is unobservable BY CONSTRUCTION - a variant rtlamr rejects outright would look
exactly like this. So the message-variant hypothesis is unsupported rather than
excluded, and an RF-layer cause (frequency being the obvious candidate) remains
the leading explanation, still unconfirmed.

**Verdict: neutral, keep or revert.** The theory that the native rate would cut
CPU by avoiding resampling is not supported - CPU rose slightly. What this DOES
settle is that sample rate is not the constraint on the dead phase, and an
RTL-SDR tops out near 2.4 MHz stable, so there is little more bandwidth to buy on
this hardware. The next honest step is capturing IQ to see where those
transmissions actually land, not further config guesses.

### Runtime from an integral, and a fail-open caught within minutes

Bill: *"i would think we would want to capture spikes by time they lasted vs just
a 1 minute average."* Correct, and the design was wrong for the reason he gave.
Runtime is an ENERGY question, so the estimator must weight every level by how
long it lasted. A 1-minute POINT SAMPLE of power does not: a 2,365 W fridge
inrush lasting ~0.5 s is either missed entirely, or caught and then weighted as
if it lasted a full minute - inflating its true 0.33 Wh by about 120x.

Measured over 18 h before changing anything:

```
  TRUE  time-weighted mean                249.8 W
  POINT 1-min point samples               253.9 W    +1.6% bias
  same estimator at 12 sampling phases:   13.5 W spread, 5.4% of TRUE
  energy above 1000 W: 0.39 of 4.32 kWh - 9.1% sits in short excursions
```

The BIAS is small. **The phase dependence is the defect** - an estimator whose
answer moves 5.4% depending on which second it fires is not measuring energy.

New chain: `integration` accumulates power*dt on every ~2 s update ->
`..._energy` -> sampled 1/min -> `statistics change_second` -> x3.6e6 ->
`backup_essentials_avg_24h`. **Sampling a CUMULATIVE accumulator once a minute is
lossless**, because the integration happened between the reads - the same
property that lets the utility register be read every 32 s without losing a
watt-hour. That is why the cadence which aliases POWER is safe on ENERGY.
`backup_essentials_mean_24h` is left defined and marked superseded.

**Then it failed open, and the reload found it.** `homeassistant.reload_all` does
not start the `integration` platform - it has no reload service - so the integral
did not exist, and:

```
  backup_essentials_energy          MISSING
  backup_essentials_energy_sampled  0.0     <- float(0) on a missing entity
  backup_essentials_energy_rate     0.0     <- change_second over a constant
  backup_essentials_avg_24h         0       <- PUBLISHED AS A MEASUREMENT
```

A dead chain reading "0 W" on a runtime gauge means *the bank lasts forever*. I
had guarded the watts sensor against a NEGATIVE rate - the easier and less likely
failure - and not against an ABSENT source. Same shape the config already
documents for meter age: *"a sensor that never existed reports heard 0 min ago /
OK"*.

Closed in two places: the sampler is now unavailable when the integral does not
exist rather than `float(0)`-ing it to a real-looking zero, and the watts sensor
additionally requires `age_coverage_ratio > 0`, because change_second over an
EMPTY buffer also returns exactly 0.0 and is indistinguishable from a true zero
load. Verified: with the integral still absent, `avg_24h` reads `unavailable`.

**Still pending: a real HA restart.** `reload_all` will not bring the integration
platform up. Until then the card continues to read the superseded sensor, which
is working.

### A peak table whose rows invite an addition they must not receive

Asked whether the basement router was double-counted after P16 folded it into
monitoring_load. **It is not** - verified live: monitoring 39.8 W = 11.8 + 16.6 +
11.4, and backup_essentials_load counts it exactly once through that sensor.

But the peak-hold table listed it as a PEER of the monitoring row rather than a
component of it, and that framing exposed a worse trap sitting beside it:

```
  naive sum of the individual rows    4,533 W
  actual simultaneous peak            3,395 W      34% lower
```

The rows cannot sum, because each peak latches independently and they are maxima
taken at DIFFERENT MOMENTS - the fridge peaked 08-24 03:36, the coffee maker
06:49, the furnace the previous evening at 20:57. Only
`backup_essentials_peak_watts` is a sizing number, because it latches the peak of
the SUM rather than the sum of the peaks. An inverter chosen off the addition
would be a third too big.

Fixed in presentation, not in arithmetic: the top row is renamed as the sizing
number, a section header states that the rows below do not add, and the router
moved beneath monitoring as “↳ of which”. The reasoning is in the card so the
rows are not re-flattened later.

**The general shape, third time now:** two numbers placed where a reader will
combine them, without saying they cannot be combined. Previously a 5-min utility
figure beside a 2 s SEM figure, then a 1 h average sold as a runtime number. A
dashboard row is an assertion about what may be compared, and this config keeps
making that assertion by accident.

### The router is independent, resolved by a coincident-step test

Asked why the basement router was missing from the charts. Because it was not in
`backup_essentials_load`, and stacking a series that is not in the sum makes the
stack disagree with the Total line drawn over it - the contradiction already
caught once on 2026-08-23. The blocker was the unresolved question of whether the
router's plug hangs off the UPS, where summing both would double-count.

**BILL CONFIRMED 2026-08-24: straight into the wall.** That is the warrant for
the sum. Everything below only agreed with it - and per R14 it should have been
an answered question, not an investigation.

**Correlation could not answer it and never could have.** The router is nearly
constant - 1.7 W of range - so a slope over all samples is noise, and the two
ranges never overlap (router 10.6-12.3 W, outlet 16.4-22.5 W) so the "parent
cannot draw less than its child" test is vacuous for this pair.

**Nesting predicts something about EVENTS, not variance.** If the outlet carried
the router, it would have to step whenever the router steps. Over 72 h, 843
router steps of at least 0.5 W:

```
  outlet moved the SAME direction      377 of 843  (45%; chance is 50%)
  median outlet-step / router-step      -0.00      (nested would be ~1.0)
  P(this many matches by chance)         0.999
```

Independent circuits. The natural experiments were checked first and were not
available: the only `switch.basement_router` transitions in 13 days are the plug
losing WiFi while the router kept drawing 11 W, and there were no mains outages
in the retained window. Switching the router off to force the test was rejected -
that is the user's network and this session's own link to HA runs over it.

**Folded in, and a duplication removed while there.**
`backup_essentials_load` had been listing the monitoring plugs inline while
`monitoring_load` summed the same plugs separately, so adding the router meant
editing two lists and forgetting one would have been silent. Essentials now
COMPOSES `monitoring_load`. Verified live: 15.2 + 16.5 + 11.3 = 43.0 W monitoring,
and 124.4 + 43.0 = 167 W essentials. The stacked chart needed no new series - its
"Monitoring" area picked the router up automatically and the stack still sums to
the Total line.

### Two chart labels that read as a contradiction

The same entity was drawn on two charts with different time constants and neither
label said so: `Total (bank)` with no `group_by` showed the last RAW sample at
284 W, while `On the bank` with `group_by avg/5min` showed a 5-MINUTE MEAN at
181.2 W. Both correct, and each chart internally consistent - every series on the
stacked chart is raw, both series on the comparison chart are 5-min. Renamed to
`Total (bank) - live`, `Whole home - 5 min avg` and `On the bank - 5 min avg`.
No data changed.

This is the third instance of one failure: a 5-min utility figure beside a 2 s
SEM figure, then a 1 h average sold as a runtime number, now this. The rule
already written on the SDR card - anything a reader may compare must state its
time constant - applies to every chart in this config, not just that one.

**A wrong theory, recorded because it was nearly acted on.** The stacked chart's
axis topped at 3395.0 and half of that is a suspiciously round 1697.5, which
looked like the Total line being stacked on top of the areas and plotted at 2x.
It was not: `backup_essentials_load` really did hit **3395.0 W** at 06:43 on
2026-08-24. The axis was honest. Checking took one query and would have been
skipped by a confident reading of the screenshot.

That spike is the useful finding: the essentials have already drawn 3395 W
simultaneously - about 300 A at 12.8 V - against a 24 h median of 177 W, with
only 13 of 23,405 samples above 1500 W.

### A 1 h average is the wrong runtime number, measured

From the user's review of the card: the router row was not latching, and was a
1 h average the right runtime indicator. It is not, and the margin is not close.

Reconstructing the essentials sum over 72 h and taking the SPREAD of the rolling
average at each window:

```
   15 min  492%        2 h  203%
   30 min  482%        4 h  126%
    1 h    293%        8 h   98%
                      24 h   28%   <- first window that converges
```

At 1 h the value swings **118-652 W**, because an hour may or may not contain a
furnace call - runtime sized off it is wrong by 5x depending on when you look.
24 h is the first window containing whole duty cycles. The 1 h series was
removed from the chart and `sensor.backup_essentials_mean_24h` added instead; a
24 h average cannot be drawn meaningfully on a 12 h graph, so it belongs in the
header as a number.

**It is sampled once a minute first, deliberately.** `backup_essentials_load`
follows six SEM channels publishing every 2 s, so a 24 h `statistics` window on
it directly would be a 43,200-sample deque with the mean recomputed every
update - about 21,600 operations a second.
`sensor.backup_essentials_sampled` (time_pattern /1) makes the same window a
1,440-sample buffer recomputed once a minute. Same answer, four orders of
magnitude less work. Same reasoning as the peak-hold latches.

**RUNTIME DEPENDS ON OUTAGE LENGTH, so the card carries both numbers.** The bank
measured 925 W average across its last outage - but that outage was **12
minutes**, and 925 W is near the p95 of instantaneous essentials (913 W). A
short outage samples the PEAK of the duty cycle; a long one averages it out. On
a ~5.1 kWh usable bank that is roughly 24 h at 208 W against 5.5 h at 925 W.
Both are correct, for different outages, and quoting either alone misleads.

**The router now latches.** The card had
`sensor.basement_router_current_consumption` - the RAW plug reading - in the
peak row, so it showed live watts. `sensor.basement_router_peak_watts` added.

**It is NOT in the essentials sum, and that is deliberate.** Whether the
router's plug hangs off the UPS is unresolved, and if it does then
`ups_outlet_current_consumption` already contains it and summing both
double-counts by about 65%. The nesting test was INCONCLUSIVE for this pair: 0
of 7,056 samples had the outlet below the router, which looks nested, but the
ranges do not overlap (router 10.6-12.3 W, outlet 16.4-22.5 W) so that test is
vacuous here - and the router varies only 1.7 W total, far too little to drive a
slope estimate. Asked the user rather than guessed.

**A chart that contradicted itself.** The router had also been added as a
STACKED AREA while not being part of `backup_essentials_load`, so the stack
summed higher than the "Total (bank)" line drawn over it. Removed from the
stack, and the Total line is now documented as the check: it must sit exactly on
top of the stack, and sitting BELOW means something is stacked that is not in
the sum.

### The bank is not a planning exercise — it has already carried four outages

Adding the monitoring brain to the essentials turned up something that reframes
the whole sizing question. `battery_bank_monitor` is a live ESPHome INA228 that
has been in service through **four outages**, and it already publishes the
numbers the peak-hold work was trying to estimate:

```
  last outage       925 W average, 1665 W PEAK, 12 min, 14.46 Ah, 187.6 Wh
  last discharge    PEAK CURRENT 130.1 A
  state of charge   99.997%      coulombic efficiency 95.78%
  runtime_remaining already exists as a sensor
```

So no runtime estimator was written and no capacity or depth-of-discharge
constants were invented. Both already exist, and inventing them would have
tripped `ha_audit`'s `fabricated-limit-constant` rule for exactly the right
reason. `amps_at_12v` was replaced by `amps_at_bank_v`, which divides by the
bank's OWN reported voltage instead of a nominal 12.5 V, so it stays honest as
the pack sags.

**The monitoring brain is now in the essentials sum**, at the user's request:
`ha_n100_pc_current_consumption` + `ups_outlet_current_consumption`, about
29 W combined. This is the load that runs for the WHOLE outage no matter what
else is shed, so it sets the floor on runtime.

**They were checked for nesting before being summed.** 17.0 W and 12.4 W are
close enough that the PC could plausibly have been plugged INTO the UPS outlet,
in which case adding them would overstate the monitoring load by 73%. Over 24 h
and 15,410 paired samples: correlation **r = +0.004**, slope **+0.001**, and
**7.2% of samples had ups_outlet drawing LESS than the n100** — impossible if
one fed the other. Independent circuits; the sum is correct.

`dashboards/cards/backup/essentials-overview.yaml` presents it: mushroom
headline (load, amps at real bank voltage, SoC, bank state), the peak-hold table
with its reset button, a STACKED 24 h chart because simultaneity is the actual
sizing question, a whole-home-vs-essentials chart showing what gets shed, and
the measured outage evidence last — which is worth more than every estimate
above it.

One behaviour worth knowing: trigger templates have no state until something
fires, so a peak reads `unknown` until its source next changes. A
`homeassistant: start` trigger was added to all six blocks so they re-seed on
restart, but `template.reload` does not fire that event — so a load that is
simply off, like the coffee maker, stays `unknown` until it next runs. That is
correct behaviour reading as "no data yet", not a fault.

### Matched comparison windows, and peak-hold for battery sizing

Two changes from the same question: why is the utility live figure on a 5 min
window when SEM updates every 2 s, and can the spikes be seen for sizing an
inverter.

**The derivative window went 5 -> 10 min, and SHORTENING IT WAS NEVER AN
OPTION.** The meter moves in 0.01 kWh steps, so a difference quotient over T
seconds carries about 36000/T watts of quantisation noise, and the counter only
ticks every ~91 s at this house's baseline. Swept against SEM over 6 h, matching
windows at each T so the comparison is fair:

```
  window   sd vs SEM   mean err   % windows with NO tick at all
   30 s      22.9 pp    +97.8%      99.1%     <- reads 0 W almost always
    1 min    49.6 pp    +88.3%      93.8%
    2 min    74.4 pp    +50.9%      63.8%
    5 min    23.3 pp     -4.8%       1.1%     <- previous
   10 min     6.6 pp     -1.7%       0.0%     <- now
   15 min     4.7 pp     -0.9%       0.0%
```

Below ~5 min most windows contain no tick and the sensor reads 0 W between
spikes of 1200-2600 W. The `sd` dip at 30 s is not accuracy - it is the sensor
being consistently zero, which is why the mean error column has to be read
beside it. `sensor.sem_whole_home_power_10min` was added as the matched partner:
a 5-min utility figure beside a 2 s SEM figure read as a 156 W discrepancy on
2026-08-23 and was nothing but the mismatch. After the change the pair agrees to
**-2.5%** live.

**2 s cannot see motor inrush, and here is the proof rather than the assertion.**

```
AC compressor start 16:07:26   first sample already at running current
    16:07:26.597   2626.5 W      running median 2502 W -> 0x surge captured
Fridge start 09:20:36
    09:20:32.609      7.8 W
    09:20:36.223   2277.4 W      <- one sample, inside the surge
    09:20:36.612    111.9 W      <- 0.4 s later, already running
```

Fridge inrush is **18-21x** running current and only 3 samples of 10,194 in 8 h
landed above half-peak. A captured peak is a LUCKY CATCH and a LOWER bound. Over
3 days: counter 2 (coffee) 1094 W max / 1067 W running = **1.0x, purely
resistive**; furnace 853 W max but 274 samples above half-peak, so that is the
blower sustained on high and NOT a surge.

`packages/backup_sizing.yaml` keeps the luckiest catch per load via
trigger-template latches - deliberately not `statistics` `value_max`, which at
2 s over 24 h would hold a 43,200-sample deque per channel and recompute the max
every update, roughly 21,600 comparisons a second across five channels on a host
already at 15% CPU. `input_button.reset_load_peaks` clears them.

**The HWH is not a water heater.** `sensor.hwh_current_consumption` is a smart
plug on the RECIRCULATION PUMP: 8.4 W standby, ~109 W running, 156 W max,
0.197 kWh across a day. The tank is gas. That removes a 4500 W resistive element
from the essentials list and is the single biggest input to whether 12 V works.

**Scope, set by the user:** fridge, furnace HEAT, Kitchen Counter 2, HWH recirc,
plus flat loads. NEVER AC, dryer or microwave.

**Open and important: the furnace figure here is a COOLING number.** It is
August, so `sem_furnace_power` currently sees the air handler running for the
AC. Heat mode adds the inducer motor and igniter and may run the blower at a
different speed. The furnace is the #1 winter essential and its heat-mode draw
is UNMEASURED. Press the reset button at the first real heat call and re-read
after a week.

### The dashboard half of P12 did not ship, and could not have

The sensors deployed correctly; the CARD did not. `dashboards/views/sdr-meters.yaml`
is a source copy that HA never loads - there is no `lovelace:` block and nothing
includes it. The live dashboard is UI-managed at
`.storage/lovelace.sdr_utility_meters`, which is correctly off-limits to edit.

So both card rows went on reading the superseded `utility_electric_power_mean`
while `sem_vs_utility_delta` and `_error` read the new
`utility_electric_power_avg`. On screen that put a 60-min mean of 398 W next to a
SEM mean of 394 W and a delta of +1 W - arithmetic that does not close, which is
how the user caught it. The two rows still needing a paste into the raw editor:

```
  - entity: sensor.utility_electric_power_avg      # was ..._power_mean
    name: Utility - 60 min mean (counter-derived)
  - entity: sensor.utility_electric_power_avg      # was ..._power_mean
    name: Utility (traceable)
```

Every earlier dashboard change this session DID land, because each was handed
over as YAML for the user to paste. This one was written to the file instead and
silently changed nothing. Recorded as a corollary to the .storage rule in
CLAUDE.md CONSTRAINTS: a dashboard change is not done when the file is written.

### Not a phasing problem — checked, because the card invited the question

Live power showed utility 361 W against SEM 517 W, which looks alarming. It is
the time constant. `utility_electric_power_clean` is a `derivative` with a 5-min
window over a counter that ticks every ~92 s; SEM updates every ~2 s. Smoothing
SEM to the SAME 5-minute constant over 4 h:

```
  SEM instantaneous vs utility     mean +2.06%   sd 27.16 pp   |max| 185%
  SEM smoothed to 5 min            mean +1.34%   sd  9.44 pp   |max|  33%

  ratio SEM(5min)/utility          p10 0.905   median 1.003   p90 1.124
```

A missed leg on a split-phase service sits near 0.50 or 2.00 and survives any
amount of averaging. The median ratio is 1.003 and matching the time constant
cuts the scatter by two thirds. Wiring is fine; the instantaneous comparison is
simply not a comparison.

### Found while answering it: the SEM cross-check is measuring its own estimator

Asked whether decoding the ELECTRIC meter more often would sharpen the SEM
comparison - the one consumer whose value plausibly scales with read rate, since
it reconciles a rate rather than a volume. It would not. But the comparison is
wrong today, by much more than cadence could ever account for.

**The SEM is accurate. The utility side is biased high.** Against the meter's own
cumulative counter over 15 hours:

```
  SEM error vs COUNTER-DELTA power    mean  +0.3%   sd 2.4 pp
  SEM error vs the DEPLOYED mean      mean  -8.9%   sd 8.4 pp
```

`sensor.sem_vs_utility_error` has therefore been reporting the 16 CTs about 9%
low for as long as it has existed. They read true to within half a percent.

**Cause is sampling bias, not calibration.** `utility_electric_power_mean` is a
`statistics` mean over a `derivative` of the energy counter. The derivative only
emits a sample when the counter TICKS, and the counter ticks faster when power is
high - so an unweighted mean over those samples over-weights the high-power
periods. It is worst exactly where you would predict:

```
  hour      counter W   deployed W    over     ticks/h   burstiness (CV)
  05:00         360         438     +21.7%        32          0.67
  06:00         570         795     +39.5%        41          0.71
  10:00         560         560      +0.1%        44          0.38

  correlation(burstiness, overestimate)  r = +0.75, n = 15
```

Near zero in flat hours, worst in bursty ones. A miscalibrated CT would show a
constant ratio instead. `utility_electric_power_clean` clamping negatives to 0
rectifies noise in the same direction and can only add to it.

**Fixed the same day.** The counter is cumulative, so over any window the energy
delta is exact and mean power is (E_end - E_start)/T. Deployed as a `statistics`
`change_second` over `sensor.electric_meter_energy`, converted to watts by a
template:

```
  sensor.utility_electric_power_rate   statistics change_second, kWh/s, precision 9
  sensor.utility_electric_power_avg    x 3.6e6 -> W, the entity to compare against
```

`sem_vs_utility_error` and `_delta` now read the second of those.
`utility_electric_power_mean` is left DECLARED so its history survives and
nothing referencing it breaks, but it is marked superseded in place and must not
be used for the comparison again.

Replayed against 16 h of history with the deployed change_second semantics
before it shipped:

```
  NEW  mean -0.55%   sd 1.89 pp   worst 7.6%
  OLD  mean -7.03%   sd 6.08 pp   worst 24.5%
```

First live reading after reload: utility 395 W, SEM 395.94 W, **error +0.24%,
delta 1 W.** Deployed by reload of the `statistics` and `template` domains only -
`statistics.reload` and `template.reload` both exist, so this needed no restart
and cost no downtime.

**Two defects the deploy gate caught that no parser could**, both worth keeping:

- **Units too small to survive rounding.** `change_second` on a kWh counter is
  kWh PER SECOND - about 1.1e-4 at this house's 400 W. HA rounded the state to
  one decimal, it read `0.0`, and the watts sensor computed 0 W from arithmetic
  that was entirely correct. `precision: 9` fixes it. `validate_ha.py` passed and
  `check_config` returned `valid` throughout, because neither runs the sensor.
  This is precisely the gap the three-verdict vocabulary names: parse-clean is
  not runtime-correct, and only reading the deployed VALUE closes it.
- **A cross-check that failed open.** `sem_vs_utility_delta` guarded only on
  unknown/unavailable, so with the utility side at 0 it published SEM - 0 =
  394 W as though that were a real discrepancy. The error sensor beside it
  already required > 50 W; the delta now does too. A comparison with one side
  missing must go unavailable, not report the other side as the error.

**And this is why more frames would not have helped.** The counter-delta
estimator is already at its quantisation floor: 0.01 kWh over a 1 h window is
10 W, which is 2.5% of this house's 391 W mean load, and the measured sd is
2.4 pp. Moving the decode interval from 32 s to 28 s shifts only the
boundary-timing term, roughly 0.9% to 0.8%. The way to a tighter cross-check is
a longer window - 4 h puts quantisation near 0.6% - or the estimator above.
Neither involves the antenna, the gain, or the capture rate.

### Method note — three estimator errors, and how each was caught

Recorded because every one produced a confident, plausible number first.

- **Harmonic.** Taking the smallest observed gap as the transmit interval gave
  electric an 8 s cadence and 26% capture. Any divisor of the true period also
  makes every gap an integer multiple, so the smallest gap is a lower bound.
- **Unbounded.** Correcting that to "largest T that fits" gave water 65.8 s and a
  capture rate of **131%** — impossible on its face, which is what flagged it.
  T can never exceed the smallest observed gap. Both constraints are needed.
- **Sample-and-hold, the expensive one.** Duration-weighting
  `sensor.water_meter_age` gave 87.4%, and it was wrong enough to reverse a
  conclusion and get written into this file before it was caught. `_age` uses
  `now()`, so HA re-renders it only on the minute tick and on decode — about two
  rows a minute. Between rows the recorded value is HELD while the true age
  keeps ramping: a row reading 12 s can stand for 44 s while the real age climbs
  to 56. Weighting by hold time therefore counts the ramp at its lowest value and
  systematically understates the tail. **A sampled signal may only be averaged by
  its samples, never by their hold times, unless the underlying signal is
  piecewise constant.** The fix is the plain mean of the minute-tick values;
  those are genuine uniform samples of the age process, and there are exactly 993
  of them for a 16.6 h window, which is the check that confirms none are missing.

A related trap in the same data: a decode landing between two minute ticks
renders 0.0, and if the last recorded value was already 0.0, HA stores no row.
So the age history CANNOT be used to count decodes — it silently drops them.
It is a reception *indicator*, not a frame counter.

Finally, the live poller is the weaker of the two instruments and its numbers are
cross-checked rather than trusted: 3 of 56 frames were observed with over 5 s of
lag, one at 33.9 s, longer than the 28 s interval — and a stall fakes a missed
frame. It agrees with the tick estimator to within 3 pp, which is why it is
quoted at all.

### If this is revisited

`_age` is the degradation detector and now has a number attached: **water 71.3%,
sd 1.2 pp, hourly 68.6-72.7%.** A later measurement outside 65-75% is a real
change. A 10-minute A/B test resolves only about +/-19 pp at 95% confidence, so
any experiment needs at least an hour per arm to say anything.

**There is no operational reason to chase the missing 29%.** The meter reading is
a CUMULATIVE counter, so a missed frame costs timing precision and never volume -
the next frame carries the accumulated total. The meter quantises at 0.1 gal and
ticked 889 times in 24 h, one per ~97 s, while we already sample every ~40 s.
Every consumer is a volume-over-a-window measure: the overnight instrument bins
hourly, so a 40 s boundary uncertainty is 1.1% of a bin and would become 0.8% at
100% capture. The 0.05 gal/h seep the instrument was built for is limited by the
meter's own 0.1 gal counter, not by reception, and more frames cannot move that.

If it is ever worth revisiting, the question is a tuning one - sample rate and
centre frequency - not a hardware one, and the phase table above is the metric:
success is phases 1 and 3 coming up off 0% and 44%.

## [2026.08.22] - 2026-08-22

### Dehumidifier SPC Capture Fix

The dehumidifier control chart had captured nothing since 2026-08-07.
`input_datetime.dehumidifier_spc_last_capture` still read `1970-01-01`,
day_2..day_7 were all 0, and mean / sigma / UCL / LCL were `unavailable`.
15 nights, and the only thing that noticed was
`binary_sensor.dehumidifier_spc_capture_stale`, added 2026-08-21 — 14 nights
into the outage.

### Fixed
- **The capture guard read an entity that has never existed.** The steady-mean
  latch is declared as `name: "Dehumidifier Running Watts Latched"` with
  `unique_id: dehumidifier_running_watts_steady_latched`. HA derives entity_id
  from `name:`, not from `unique_id`, so the registry holds
  `sensor.dehumidifier_running_watts_latched` — while all four consumers, plus
  `pipelines.yaml` and the capture-stale card, were written against
  `sensor.dehumidifier_running_watts_STEADY_latched`. The 23:59 guard read
  `unavailable` -> `| float(-1)` -> `w > 0` false -> skip, every night. The
  four consumers now name the entity that exists; the `unique_id` is
  deliberately left mismatched, because changing it would orphan the registry
  entry and drop both the restored latch value and the InfluxDB series.
- **`ha_audit.py` could not see this class of defect, by construction.**
  `known_entities()` synthesised `"<domain>.<unique_id>"` for every YAML
  template entity, which vouched for the phantom id and made every reference
  to it resolve clean. It now resolves `unique_id -> entity_id` through the
  entity registry and falls back to `slugify(name)`, never to `unique_id`.
- **New rule `phantom-entity-id` (FAIL).** Reports any `<domain>.<unique_id>`
  that is referenced in config but is not a real entity, naming the id that
  unique_id actually belongs to. It compares against the registry rather than
  `slugify(name)` because HA fixes entity_id at first registration and never
  revises it when the name changes later — `sensor.site_eui_estimate` is that
  case and is correct as written.

### Recovered
- **7-day buffer backfilled and the fix reloaded live**, 2026-08-22. day_1..7
  were replayed from the deployed gate sensor's own recorded samples in
  InfluxDB (`"W"` where `entity_id = dehumidifier_power_when_on_steady`,
  calendar-day means, `tz('America/New_York')`) — nothing modelled or
  interpolated. Every day cleared the live guard on its own terms
  (cycles >= 2, 150 < W <= 800); cycle counts 9/8/8/6/5/6/8.

  ```
  day_1 466.4 (08-21, n=263)   day_5 472.2 (08-17, n=330)
  day_2 466.8 (08-20, n=226)   day_6 472.9 (08-16, n=325)
  day_3 463.2 (08-19, n=144)   day_7 475.1 (08-15, n=328)
  day_4 467.2 (08-18, n=240)   stamp -> 2026-08-21
  ```

  Known difference from a live capture: the nightly capture writes a trailing
  24 h statistics mean sampled at 23:59, these are calendar-day means — the
  windows differ by one minute of samples.

  Result: mean 469.1 W, sigma 4.30 W, LCL 460.5 / UCL 477.7, and
  `binary_sensor.dehumidifier_spc_capture_stale` cleared to `off`.
  `/api/config/core/check_config` returned `valid` (no errors, no warnings),
  then `template.reload` + `automation.reload`. The latch held 466.9 W across
  the template reload (RestoreEntity), all six populations came back with
  limits, `spc_capture_stale_any` reports `none`. No helper with an `initial:`
  drifted — all 24 already matched, checked before reloading.

### Also fixed, same review
- **`script.ha_audit` had never worked.** Every invocation raised
  `from_json got invalid input '{"fail":...` while quoting what looked like
  flawless JSON. The audit JSON contains only strings, ints, lists and dicts —
  no `true`/`false`/`null` — so it is *also* a valid Python dict literal.
  HA's `_parse_result` (helpers/template/__init__.py, 2026.8.2) runs
  `ast.literal_eval` on every rendered template, so
  `raw: "{{ audit.stdout | trim }}"` silently stopped being a `str` and became
  a dict, wrapped by `RESULT_WRAPPERS` in a subclass whose `__str__` returns
  the original render text — which is precisely why the error message printed
  immaculate JSON while `from_json` was being handed a dict. Verified by
  elimination: `from_json` on the identical 9,032-byte string via
  `/api/template` returns `13`; `MAX_TEMPLATE_OUTPUT` is 256 KiB;
  `shell_command` does not truncate. The script now reads `audit.stdout`
  directly at each point of use and never parks the JSON in a variable.
  `input_datetime.ha_audit_last_run` had been frozen at 2026-08-21 11:06:05
  and `binary_sensor.ha_audit_stale` needs >2 days, so nothing had said so.
- **`phantom-entity-id` matched substrings**, reporting 13 FAILs where 6 were
  real. `sensor.hvac_furnace_runtime_month` is a prefix of the working
  `sensor.hvac_furnace_runtime_month_2`, and the whole `_2` family is
  referenced correctly everywhere. Now a whole-word match.
- **Six genuinely broken entity references**, all confirmed MISSING against
  the live API before being touched. The two that mattered:
  - `sensor.hvac_runtime_per_cdd_7_day_stddev` -> `..._7_day_std_dev`. The
    consumers fall back to `| float(2.0)`; the real value is 6.8. The per-CDD
    control band had been drawn at 25.1–33.1 instead of 15.5–42.7, and
    `binary_sensor.hvac_runtime_per_cdd_low_alert` was **ON** against a
    perfectly healthy 21.2 min/CDD. It cleared to `off` on the fix.
  - `sensor.hvac_runtime_per_hdd_upper_bound` / `_lower_bound` ->
    `..._1s`. Both alerts gate on `upper > 0` / `current < lower` against a
    `| float(0)` fallback, so **neither could ever fire.** Real bounds
    12.8 / 8.4.

  Also `binary_sensor.ac_min_per_cycle_capture_stale` ->
  `ac_min_cycle_capture_stale` (3 refs + manifest) and the `hdd`/`cdd`
  `_archive_stale` detectors -> `_monthly_archive_stale` (manifest only).

  The `_2` / `_1s` collision suffixes are left alone: every consumer already
  names them correctly, only the `unique_id` looks odd, and that is inert.

  `check_config` returned `valid`, then template/automation/script reload.
  `script.ha_audit` now returns `0 FAIL, 24 WARN, 4 INFO across 19 pipelines`.

### Warnings cleared, 24 -> 8
- **All 13 remaining EOD capture stamps snapshotted.** Each now defines
  `capture_stamp` as the first step of `action:` and the
  `input_datetime.set_datetime` call reads that instead of a live `now()`.
  19/19 pipelines compliant. Verified structurally, not by eye: the edited
  file was re-parsed and each of the 13 automations reversed *exactly* to its
  original once `capture_stamp` was removed and the stamp un-substituted, with
  the other 74 automations byte-identical and the comment count unchanged at
  647. The 13 other live `now().strftime(...)` stamps in that file are
  event-triggered and correct — they were not touched.
- **`testcmd` and `test_python` removed.** Install-time smoke tests, called by
  nothing. `echo hello` is indistinguishable from a live command in an audit.
- **`backup_input_numbers` guarded.** The only one of the eight where the guard
  is free: weekly, and legacy anyway (54/121 buffer entities, superseded by
  `spc_buffer_export.py` at 00:20). Missing one week costs nothing.
- **`ha_audit.py` scanned `automations.yaml` but never `scripts.yaml`** when
  collecting shell_command callers and guards — so a command called only from a
  UI script would have been reported dead *and* unguarded, wrong in both
  directions. Empty today, which is when a blind spot is cheap to close.

### Six new audit rules, and what they found

Each was probed against the real config before being written, and each is
regression-tested both ways: it must fire on an injected fault AND stay silent
on a clean tree.

- **`claude-md-entity-missing`** - CLAUDE.md's ENTITIES list is, by its own
  CONSTRAINTS section, the only permitted source of entity ids. **16 of 290 did
  not exist**, including the `_1s` bounds behind the two dead alerts. All 16
  corrected. Two precision guards were needed: fence parity cannot be tracked
  (the OUTPUT FORMAT section nests ```diff inside a fence, inverting every line
  after it), and an entity line must be followed by EOL or *two* spaces, because
  prose uses one and "sensor.hwh_recirc daily flat was frozen at 144.5W" is a
  sentence. The first cut flagged it.
- **`entity-ref-unresolved`** - every literal entity id in config, automations,
  scripts and dashboards must resolve. 641 refs checked. Ids ending in `_` are
  skipped: those are Jinja concatenations like
  `states('input_number.gas_archive_' ~ year)`, and eight of the first fifteen
  hits were exactly that.
- **`statistics-buffer-truncating`** (live) - see below. Degrades to an INFO
  naming the reason when no token is reachable, never to silence.
- **`choose-without-default`** - CLAUDE.md mandates it. **9** were missing, not
  the 5 that P1 recorded.
- **`fabricated-limit-constant`** - a non-zero literal fallback feeding a
  control limit. 12 hits across 6 sensors. `float(0)` is exempt: it cannot
  manufacture a band, because every consumer gates on `> 0`.
- **`chart-window-exceeds-recorder`** - `energy-month-30d.yaml` asked for 30d
  against `purge_keep_days: 14`, with no `statistics: true`. Over half of it had
  never had data to draw. Narrowed to 14d.

### The one that found something nobody was looking for

`sensor.fridge_running_watts_24h`: **buffer 1.00 full, age coverage 0.11.** The
"24h" mean was covering about 2.6 hours, and the length of that window moved
with compressor duty. The fridge SPC capture reads the latch fed by that sensor,
so its daily subgroup was never a calendar day - the one property the entire
calendar-day-subgroup design in `packages/spc.yaml` rests on.

Not one sensor, three. Furnace and AC share the same `sampling_size: 2000` and
are simply idle in August. Sizes are now measured, not guessed - peak samples
per day over 30 days from InfluxDB, plus ~20% headroom:

```
gate sensor                        peak/day     was      now
fridge_power_when_on                 26,714   2,000   33,000
furnace_power_when_on                11,135   2,000   14,000
ac_power_when_on                     11,030   2,000   14,000
dehumidifier_power_when_on           13,798   4,000   17,000   diagnostic only
dehumidifier_power_when_on_steady        452   3,000    3,000   already correct
hwh_recirc_power_when_on                 569   2,000    2,000   already correct
basement_*_delta_sht45_vs_shelly         299     320    1,000   no headroom
```

The dehumidifier SPC series was already correctly sized - the chart repaired
earlier today is sound.

An explicit `sampling_size` is kept rather than dropped to let `max_age` govern
alone. Unbounded would never truncate, but HA publishes `buffer_usage_ratio`
only when a size is set, and that attribute is now the observable the audit
watches. A number the audit checks beats one nobody can see.

**This needs a Home Assistant restart. Statistics sensors do not reload**, so
the audit will keep reporting the truncation until then - correctly, because it
reports the deployed truth rather than the file.

### The leak alarm now has something to watch

`automation.sdr_water_leak_flag` had triggered on `sensor.water_meter_leak`
since the day it was written, and that entity had never been created - so the
alarm could not fire. Its own description had anticipated exactly this:
"confirm it in Developer Tools and disable this automation if absent." It was
absent. `rule_entity_refs_resolve` found it on its first run.

Nothing was missing upstream. rtlamr2mqtt's autodiscovery publishes only
`<meter>_reading` and `<meter>_last_seen` as *entities*, but it carries the whole
decoded R900 frame as *attributes* on `_reading`:

```
Unkn1 163   NoUse 35   BackFlow 0   Unkn3 0   Leak 0   LeakNow 0
```

So no add-on change and no MQTT work - the data had been arriving all along and
only the entities were missing. Four template sensors now surface it:
`water_meter_leak`, `_leak_now`, `_backflow`, `_no_use`.

Field widths and meanings come from the decoder that produces these very
attributes - `bemasher/rtlamr` `r900/r900.go` - rather than from a forum:

```
NoUse      6 bits   day bins of no use
BackFlow   2 bits   backflow past 35d hi/lo
Leak       4 bits   day bins of leak
LeakNow    2 bits   leak past 24h hi/lo
Unkn1 / Unkn3       undecoded - deliberately not exposed
```

**Leak and LeakNow answer different questions**, and the distinction matters for
a leak alarm. `Leak` counts day bins across 35 days, so it stays non-zero for
weeks after a repair - "has this meter seen a leak recently". `LeakNow` is the
past-24 h field - "is water running now". The existing automation triggers on
`Leak`, which is right for a "go look" notice and wrong for "act now"; the
recommendation to add a second LeakNow path is CLAUDE.md P9, not done here
because it changes the alarm design rather than repairing it.

Stated rather than buried: **`NoUse` currently reads 35 on a house consuming
~91 gal/day**, which is not credible as "35 day bins of no use". Either the bin
encoding differs on R900 v4 or the field is offset. It is published as a
diagnostic only and nothing alarms on it - the same caution the leak automation
already carried, that published R900 field ranges do not cover every observed
value.

`initial_state: false` removed and the automation enabled, its precondition now
being met. Alarm chain verified end to end: `leak = 0` (trigger `> 0`),
`sdr_alerts_enabled = on` (condition), automation `on`.

New card `dashboards/cards/utilities/water-meter-r900.yaml` leads with the
question that matters - is there a leak right now - and keeps the 35-day history
as the secondary line, with a conditional decode-staleness warning above the raw
fields so a silent dongle cannot read as a clean bill of health. The mushroom
features it uses (`mushroom-template-card`, `icon_color`, `multiline_secondary`)
were checked against the shipped `www/community/lovelace-mushroom/mushroom.js`,
not the docs.

### The ~112 s cadence, root-caused — and my first fix was wrong

Decomposed over 35 cycles of the add-on log, median 117.5 s vs 119.8 s
accounted:

```
  0.8 s  rtl_tcp + rtlamr startup
 57.0 s  acquisition — waits for the SLOWEST meter; gas is idle in August
  2.0 s  SIGTERM grace, then SIGKILL — every cycle, without exception
 60.0 s  sleep_for
```

That second line is the bigger finding: **"rtl_tcp did not exit after SIGTERM,
sending SIGKILL" fires in every single cycle — 735 times a day on a USB device
driver.** rtl_tcp blocks in a USB read and ignores SIGTERM, and the 2.0 s
timeout is hardcoded in `process_manager.py`, so no configurable grace period
helps. Removing the restarts is the only way to stop paying it.

**The fix is one line: `sleep_for: 60 -> 0`.** In `meter_reader.run()`,
`_sleep_cycle()` is called only `if self.sleep_for > 0`, and the "all meters
read" break is gated the same way — so with 0 the loop reads and enqueues
forever. No restart, no sleep, no SIGKILL, and resolution falls to the meters'
own transmit interval. 0 is the add-on's own default; the 60 was set locally.

It must be paired with `rtlamr: -unique=false` — and **removing the flag does
not work**, because `buildcmd.py` adds `-unique=true` as a default unless
custom_parameters already contains a `-unique` flag. The override has to be
explicit. It matters because rtlamr's `UniqueFilter` suppresses any frame whose
checksum matches the previous one from that meter, in an in-memory map that the
current 2-minute restart happens to wipe. Without restarts it persists, and a
meter with flat consumption goes silent — freezing `last_seen`, tripping
`water_meter_stale`, and gating off the LeakNow alarm. That would contradict the
commissioning note already on the SDR dashboard: *"'Heard ago' is the
instrument; value change is not."*

### What InfluxDB actually retains — audited

```
configured        UI config entry, not YAML; options: {} = NO include/exclude
retention         autogen, duration 0s = INFINITE, nothing is ever purged
coverage          1,287 entity_ids · 1,362 series · ~963k points/day
history begins    2026-05-31 (W, degF, %) · 2026-06-27 (kWh)
disk              33.6 GiB used, 388 GiB free, 8%
strings           stored — non-numerics get a `state` field
attributes        stored — this is why the R900 leak fields had history
                  predating the sensors that expose them
```

**Writes happen on state change, not on a sample clock.** An unchanged value
writes nothing, so a flat line reads as a gap and is not one. That is the single
most important thing to know when reading this data — it is exactly what made
`dehumidifier_current_consumption` look 163 min stale when the unit was simply
off.

It also means the recorder exclusion added today loses nothing: `last_seen`
lives in InfluxDB under its own measurement, permanently. Recorder is the
14-day store; InfluxDB is the forever store.

### Grafana SPC re-sourced, CQs retired

All five continuous queries **dropped** from InfluxDB, and every panel in
`spc_appliances.json` now reads Home Assistant's own entities:

```
Daily    input_number.<pop>_running_watts_day_1     its history IS the daily
                                                    series - one point per
                                                    successful capture
Mean 7d  sensor.<pop>_running_watts_mean_7d         was MOVING_AVERAGE over CQ
                                                    data, a THIRD definition
UCL/LCL  sensor.<pop>_running_watts_upper / _lower
```

The panels had been mixing sources — point series from the CQ, control limits
from HA — which is why the dehumidifier showed a permanent **BELOW LCL**: 457.9
plotted against 460.5–477.7. Now it reads Daily 466.40 inside LCL 461.02 / UCL
476.14. The false out-of-control is gone.

One artifact of my own turned up in that verification and was fixed: the
limit and centre-line queries used `MEAN("value")` over a daily bucket, but
`mean_7d`, `upper` and `lower` are **step functions** that change once a night
when the buffer rotates. Averaging across that step blends the old and new
limit — and it put HWH Recirc outside a band that never existed (daily 109.5
against a blended UCL of 108.77, when the limit actually in force was 109.6).
Switched to `LAST()`. Only the Daily series is raw points with no GROUP BY.

Final check, Grafana against HA, all six populations:

```
population        daily     mean      LCL      UCL   verdict
fridge            114.2    114.6    101.2    128.0   IN CONTROL
furnace           774.2    771.5    767.3    775.7   IN CONTROL
ac               2357.4   2488.4   2305.4   2671.4   IN CONTROL
hwh_recirc        109.5    106.0    102.4    109.6   IN CONTROL
dehumidifier      466.4    469.1    460.5    477.7   IN CONTROL
cooling_kwh_cdd    1.09     0.83      0.0     1.89   IN CONTROL
```

Every figure matches the HA charts exactly — which is the point of the rebuild:
one definition, so the two cannot disagree.

All 24 rewritten queries were executed against InfluxDB before shipping and
every one returned data. `fill(null)` is kept on the limit lines deliberately —
a gap means the limit was genuinely unavailable (fewer than 2 valid slots, or
sigma collapsed), and that is a fact worth seeing rather than papering over.

`scripts/spc_continuous_queries.sql` keeps all five definitions but every
`CREATE` is commented out under a RETIRED header carrying the reasoning, so
they are recoverable without being re-runnable by accident. The historical
`spc` measurement was **not** deleted — 188 points remain and retention is
infinite, so the old output stays queryable for comparison.

Grafana is file-provisioned from `/config/grafana/dashboards`, so the JSON edit
is the deployment.

### The CQs are a sixth copy of the SPC constants, and they drifted

`scripts/spc_continuous_queries.sql` deployed five continuous queries on
2026-07-22 that recompute the SPC daily means inside InfluxDB for
`grafana/dashboards/spc_appliances.json`. They are a parallel implementation of
a metric HA already computes — precisely the drift `pipelines.yaml` exists to
end. Two defects:

**Wrong metric, dehumidifier.** The CQ still reads
`dehumidifier_current_consumption > 250` — full-run power with the pre-E080
threshold. The pipeline moved to the warm-up-excluded steady gate on
2026-08-07; the CQ never did. Measured for 2026-08-21: **CQ 457.4 W vs HA
466.4 W, −9.0 W** against a 2–3 W process sigma. Grafana and HA show different
numbers for the same day under the same label. The other four match HA's
thresholds — verified against the input_numbers.

**Wrong day, all five.** `GROUP BY time(1d)` with no `tz()` aligns buckets to
the UTC epoch, so the bucket stamped `08-21 00:00 UTC` actually covers
`08-20 20:00 → 08-21 20:00` local. Every Grafana SPC point carries four hours
of the previous local day and misses the last four of its own, while HA
captures a true America/New_York calendar day at 23:59. Not comparable even
where the metric agrees.

Recommended: **retire the CQs rather than repair them.** The day slots are
already in InfluxDB — `input_number.<x>_running_watts_day_1..7` are written
like any other entity — so the Grafana panels can read exactly what the HA
charts read, from one definition. Logged as P12; not actioned, because dropping
deployed CQs and editing Grafana dashboards is a decision rather than a repair.

### Deployed and verified, 19:20

`sleep_for: 0` + `rtlamr: -unique=false`, add-on 2026.5.9. Measured over the
first 7.1 minutes, 30 publishes:

```
meter     pub/h   med gap   min   max   unchanged republishes
water        93       42s   28s   56s      10 of 10
electric     93       34s   13s   91s       5 of 10
gas          67       45s   15s  150s       7 of  7
```

- `Sleeping for` / `Waking up` / `All 3 meters read` — **gone** from the log.
- `did not exit after SIGTERM, sending SIGKILL` — **gone**. It was 721/day.
- `*_meter_age` now 0.0–0.1 min across all three; every stale detector off.
- Water republished `1640289` **eleven times unchanged** — that is the proof
  `-unique=false` took effect. Under `-unique=true` with no restarts, ten of
  those would have been suppressed and `last_seen` would have frozen.

**The R900 transmit interval is 28 s, measured.** Water gaps are 28 or 56 s and
nothing else — 28 is the interval, 56 is one missed frame.

> **RE-MEASURED 2026-08-23, and the 69% HELD.** This paragraph originally
> continued: *"Reception is running about 69% ... Antenna work is finally worth
> doing ... small sample though — 7 minutes; re-measure over a day first."*
> Over 16.6 h the rate is **71.3%**, so the 7-minute number was sound. What did
> not hold is the inference drawn from it: the losses turn out to be strongly
> anti-clustered, which is not how a signal-limited link behaves, so antenna
> work has no measured headroom to recover. See **2026-08-23** below.

Costs, against the pre-change baseline: `processor_use` 4% → 17%,
`processor_temperature` 134.6 → 138.2 °F, `last_seen` state changes ~2,200/day →
~6,100/day. The three `*_meter_last_seen` sensors are now excluded from the
recorder — their history carries no information, since `*_meter_age` derives
everything from the live value and is still recorded. `_age` is deliberately
NOT excluded: it is the reception instrument. Recorder is not reloadable, so
that one applies at the next restart.

### The thermal trade, which was the reason for sleep_for in the first place

`sleep_for: 60` was set to cut dongle heat and extend its life. That is a
legitimate goal, and the duty-cycle numbers are worth having before deciding:

```
sleep_for   cycle s   duty %   SIGKILLs/day   resolution
    0          59.8     100%              0   ~20 s (meter interval)
    5          64.8      92%          1,333   ~65 s
   10          69.8      86%          1,238   ~70 s
   30          89.8      67%            962   ~90 s
   60         119.8      50%            721   ~120 s   <- today
  300        359.8      17%            240   ~360 s
```

**Shortening the sleep is the worst of both worlds** — `sleep_for: 5` gives 92%
duty *and* 1,333 SIGKILLs/day. Duty is dominated by the 57 s acquisition
window, which is not controllable (it is however long the slowest meter takes
to be heard), so only a long sleep buys real off-time and a long sleep costs
resolution. The trade is effectively binary.

**And the current setup may not be buying the saving it intends.** rtl_tcp is
SIGKILLed every cycle; SIGKILL runs no cleanup, so `rtlsdr_cancel_async()` and
`rtlsdr_close()` never execute and librtlsdr's tuner power-down never runs.
Streaming stops and the kernel releases the interface on fd close, but the
R820T2 — the hot part — is not being explicitly powered down. Stated as
reasoning from how signals work, **not measured**: an RTL-SDR exposes no
temperature through librtlsdr.

The way to settle it is already built. The SDR view's own note reads *"A rising
baseline that never returns to zero is the degradation signal"* — that
reception-age chart **is** the thermal-degradation detector. Run `sleep_for: 0`
for a week or two and watch the `*_meter_age` baseline; if it climbs, the duty
cycle goes back up. The failure mode is graceful and instrumented, not silent.

Host baseline captured before any change: `processor_use` 4%,
`processor_temperature` 134.6 °F (57 °C).

If heat is the real concern, a heatsink on the RTL2832U plus a USB extension
lead out of the host's warm case addresses it directly — and the extension also
moves the antenna away from the PC's RF noise, so it buys reception too.
Neither costs resolution.

### Two errors of mine, recorded rather than quietly replaced

1. **"Set `listen_mode: true`."** Wrong, and it would have taken the whole SDR
   stack dark. In this add-on `listen_mode` is a *discovery* mode — readings are
   never enqueued, so nothing publishes to MQTT:
   ```python
   if self.listen_mode:  ... logger.info('New meter | ID ...')
   else:                 self.reading_queue.put_nowait(reading)
   ```
2. **"`sleep_for: 0` doubles the SIGKILL rate."** Wrong — it eliminates it.
   There is no sleep cycle left to stop processes for.

Both came from reasoning about what `listen_mode` *ought* to mean rather than
reading it. The add-on is three short files and a 25-second fetch. That is the
same lesson CLAUDE.md's CONSTRAINTS already carry — validate against the
deployed artifact, never the plausible story — and it applies to add-ons, not
just Lovelace cards and HA internals.

Accuracy was never affected by any of this: the meters transmit a cumulative
counter, so a missed frame loses nothing. Totals are exact today. Only the
timing of a tick is coarse.

### Design Philosophy expanded in place, not summarised elsewhere

The fuller wording is now in CLAUDE.md, replacing the terse bullets. What the
expansion buys is the concrete half of each principle — "a second measurement
path, a cross-check, a safe fallback default, not blanket duplication" tells you
what to do where "spend redundancy carefully" does not — plus the calibrating
examples (battery-bank capacity confidence at the outage; INA228 offset
integrating during idle).

Three of those lines were load-bearing today rather than decorative:
*make the slow variable observable* produced the overnight-minimum-flow
instrument and the statistics-buffer rule; *keep gates automated* produced the
DEFINITION OF DONE section and six audit rules; *telemeter while a decision
still exists* is the whole argument for the reception-age chart.

One corollary was added because the day earned it, not because it was already
believed: **a gate that has never been tested against a known-bad input is not
a gate, and an instrument that cannot be wrong is not an instrument.**
`ha_audit.py` vouched for an entity that had never existed; two rules written to
fix that then produced false FAILs; the Grafana panels disagreed with HA for a
month because nothing compared them. The practice that follows — prove a new
check fires on a fault AND stays silent on a clean tree — is now written down.

Deliberately NOT a separate summary document. The recurring defect in this repo
is a second copy of a definition drifting from the first: `pipelines.yaml`
exists because five copies drifted, `spc_seed.py` carried a sixth copy of the
SPC constants, the InfluxDB CQs a seventh. A philosophy summary in its own file
would be that same mistake in the same shape. CLAUDE.md is loaded every
session; that is where it belongs.

### ha_audit taught the buffer conventions instead of assuming one

`rule_buffer_health` reported *"all 7 slots are 0"* for a buffer holding `0.0`
and six `-1`s — wrong on the facts, and wrong on the meaning, because `0.00
gal/h` is a **perfect night** on this buffer while every SPC buffer uses `0` for
"no valid subgroup".

That is the **third** time the same inversion bit in one day: first in
`water_overnight_min_mean_7d` (caught before deploy), then in the chart's
`data_generator` (caught by executing the JS in node), now in the audit rule.

The fix was not a fourth special case. The manifest already carries every other
fact about a pipeline, so it now carries this one:

```yaml
empty_sentinel: -1   # value meaning "no data in this slot" (default 0)
benign_repeat: 0     # a value that may legitimately repeat
```

`benign_repeat` exists because the `repeated-buffer` FAIL was built to catch the
"459 × 3" fabricated-seed signature — a constant *written* rather than measured.
Seven identical `0.00` nights is a genuine measurement of a house with no leak
and must not FAIL.

Regression-tested in four directions:

```
real tree                          0 FAIL, 0 WARN     first fully clean audit
overnight buffer all -1            WARN empty-buffer, naming the sentinel
dehumidifier 7x 459.0              FAIL repeated-buffer
overnight buffer 7x 0.00           silent          <- benign_repeat
overnight buffer 7x 0.37           FAIL repeated-buffer
```

**The lesson, now written into the Design Philosophy: a convention that is not
written down where the data lives will be re-derived, wrongly, by every
consumer.** When a new pipeline breaks one, the exception belongs in the
manifest, not in the readers.

### Nothing hand-maintained, and a session protocol — 1,670 to 883 lines

Second pass on Bill's critique. Every hand-kept list in CLAUDE.md is now
generated, and the file carries explicit start/end instructions instead of
implying them.

```
                     was    now   how
ENTITIES             548     22   generated -> ENTITIES.md
PACKAGES             111      8   generated -> PACKAGES.md
AUTOMATIONS INDEX     87      7   generated -> AUTOMATIONS.md
CHANGELOG RECENT      44     10   deleted; it duplicated CHANGELOG.md (R10)
PENDING              300    139   5 open in full, 8 closed to a ledger
                   -----  -----
total              1,670    883   -47%
```

`scripts/gen_reference.py` builds all three from the registry, `pipelines.yaml`
and `entity_notes.yaml`. `rule_generated_docs` FAILs on missing, stale, or
hand-edited-with-a-ghost — regression-tested in all four states including clean.

### The skills, aligned — and one of them shipped a tool we were missing

CLAUDE.md has mandated `homeassistant-config-validator --strict` for years and
**nothing by that name was installed**; every "validated" claim this session was
really `yaml.safe_load` plus `check_config`. The skill bundles the real script.
It is now vendored at `scripts/validate_ha.py`, with its check list at
`docs/ha-validator-checks.md`, and the gate names it.

Run against the whole config it found exactly one thing, in `spc.yaml`:

```
WARN [entity-id] entity id 'input_datetime.' ... is not lowercase
                 domain.object_id shape
```

A false positive — `states('input_datetime.' ~ stem ~ '_spc_last_capture')`, a
Jinja concatenation, the same class of bug fixed in `rule_entity_refs_resolve`
yesterday. Rather than weaken a vendored checker (which would fork it from the
skill, R10), the template now builds the id with `| format()` in one string.
Identical at runtime — verified by rendering it through `/api/template` and
comparing the output — and unambiguous to any static analysis. **9 files, 0 FAIL,
0 WARN under `--strict`.**

The three-verdict vocabulary from that skill is now CLAUDE.md's: FAIL /
PASS (parse-clean) / PASS (HA-certified), with an explicit rule never to upgrade
one. "Parse-clean" is a real result and not a promise that HA will load the
config — the same distinction the ESP skill draws between codegen and
`src/main.cpp.o` with 0 errors.

### SESSION PROTOCOL

**Start:** run `ha_audit.py` and read the verdict aloud before touching anything.
You inherit whatever the last session and the nightly 00:30 run left behind — an
audit you did not read is an audit that did not run for you. If it cannot run,
say so and stop; working blind on a live house is not a thing to do quietly.

**End:** regenerate the reference docs, `validate_ha.py --strict` every edited
file, `ha_audit.py` to 0 FAIL, `check_config` to valid, append to CHANGELOG.md,
and state what was left open and why.

Run against itself: regenerate clean, 9 files parse-clean, 0 FAIL / 0 WARN / 1
INFO, `check_config` valid.

### CLAUDE.md made actionable — 1,670 lines to 1,013

Bill's critique: *"good human reading doc but not sure it is actionable for
claude code"*, and *"the doc calls out to manually update the entity list. that
seems to be asking for errors."* Both correct. Measured first:

```
1,670 lines
  ENTITIES     548 lines  32.8%   hand-maintained, 328 ids, 16 of them wrong
  PENDING      300 lines  18.0%   8 of 13 items already RESOLVED
  imperative    15 lines           <- the entire executable surface
```

A third of the document was a drift-prone list, a fifth was closed business, and
fifteen lines could actually be executed.

**Design philosophy, sandbox practice and the corollary are now 13 numbered
RULES** — R1..R13, each stating the ACTION first and then the dated failure that
earned it. "Treat slow drift as the primary threat" became "R3: after any
multi-site edit, re-parse and prove the untouched parts are byte-identical."
A rule with no scar is a preference; every one of these has one.

**ENTITIES is now generated.** `scripts/gen_entities.py` builds `ENTITIES.md`
from `.storage/core.entity_registry` (existence), `pipelines.yaml` (wiring) and
`entity_notes.yaml` (meaning, the only hand-kept part). An annotation cannot make
an id wrong — if the id disappears the generator drops it and says so. CLAUDE.md
keeps a 22-line pointer and the resolution rule: **ENTITIES.md, then the
registry, never from memory.**

`rule_claude_md_entities` became `rule_entities_doc` and now FAILs on three
states — missing, stale, or hand-edited-with-a-ghost — tested in all four
including clean. `gen_entities.py --check` is the same comparison for a
pre-commit hook.

**PENDING keeps 5 open items in full; 8 closed ones became a one-line ledger**
pointing at CHANGELOG.md, which is where the detail already lived.

Two of my own errors during this work, per R13: a slice from
`rule_claude_md_entities` to `rule_liveness_coverage` would have deleted six
rules in between — caught by a `NameError`, boundary now derived from the next
top-level `def` instead of a named function. And a heredoc mangled `

def`
into a literal newline for the third time this session; the fix was to stop
using heredocs for code containing escapes.

### P3 answered: the 60 degF cutoff does not make compensation moot

Asked whether temperature compensation is necessary given the unit will not run
below 60 degF. Both on-paths do gate on it — `dehumidifier_should_run` and the
force-on backstop, verified in the config — but the gate **never binds**.

`sensor.shelly_temperature_humidity_temperature`, 2026-05-31 to 08-23, n=3230:

```
range            61.3 .. 72.9 degF
below 60 degF    0 of 3230 samples
30-day means     62.7 -> 67.3 -> 70.0 -> 71.2 degF
```

The two basement sensors agree to 0.06 degF, so this is directly comparable to
the SHT45 node the SPC series uses.

The cutoff truncates the **cold** end — deep winter, when the unit stops and the
chart has no points anyway. It leaves the whole 61–73 degF shoulder-to-summer
band: 11.5 degF of operating range, with the mean alone moving 8.5 degF across
84 days.

**And that is worse than a merely wide band.** At 7.64 W/degF an 8.5 degF
seasonal rise is +65 W. A refrigerant loss of −50 W over the same months nets to
**+15 W** — a gentle rise, no alarm, machine failing, instrument reporting fine.
The confound moves on the same timescale and in the opposite direction to the
fault the chart exists to catch. Autumn reverses it and a healthy machine looks
like it is dying. The 7-day rolling window does not save this; the limits follow
the drift, which is exactly how the drift hides.

**What is not yet earned:** the 7.64 W/degF slope was fitted over a 1.5 degF
span. Applying it across 11.5 degF is an 8× extrapolation — the same error the
2026-08-07 note made in the opposite direction when it dismissed temperature on
a 0.78 degF lever arm. At half the slope the drift is still 32 W against a 2–3 W
sigma, so the conclusion holds; the magnitude does not.

**No config change is needed to decide.** Basement temperature and steady watts
are both already in InfluxDB continuously, so capturing temperature alongside
the subgroup would be redundant — the regression can be re-run at any time. The
autumn cool-down supplies a real lever arm for free. Re-run it once the basement
has dropped ~5 degF and compensate on measurement rather than extrapolation.

### Live check running — audit fully green

Token minted, pasted, restarted. `rule_statistics_buffer` executed in the
nightly audit for the first time: **8 statistics sensors checked, 0 at or above
the 0.85 warn line.** Silence from that rule now means it ran and found nothing,
which is emphatically not what silence meant yesterday.

```
fridge_running_watts_24h   0.65 buffer / 1.00 age coverage
                           (was 1.00 / 0.11 before the sampling_size fix)
```

**The diagnostic was fixed too, because the first version cost a round-trip.**
It read `supervisor -> ... 401` — leading with the one route that can never work
from a `shell_command`, and never mentioning `HA_TOKEN`, which was simply unset
and therefore produced no attempt to report. `HA_TOKEN` is now tried first
(Supervisor stays as a fallback for genuine add-on contexts) and the message
names the action:

```
no credential    -> "HA_TOKEN unset. set HA_TOKEN ... see docs/addons/..."
bad token        -> "HA_TOKEN was rejected - check it is valid / not revoked"
add-on context   -> names SUPERVISOR_TOKEN, still points at the doc
working          -> silent
```

Tested in all four states. The lesson, and it is the same shape as the rest of
this session: **"what failed" is half a diagnostic — the other half is "and here
is what to do about it".**

Final state: **0 FAIL, 0 WARN, 1 INFO across 20 pipelines**, and the one INFO is
a line proving the EOD contention check ran.

### Live-check plumbing wired, token pending

`secrets.yaml` was the stock 4-line template with one unused `some_password`
placeholder, and nothing in the config used `!secret` — this is the first.

Now: `secrets.yaml` holds `ha_audit_cmd` with a `PASTE_LONG_LIVED_TOKEN_HERE`
placeholder, and `packages/audit.yaml` reads `ha_audit: !secret ha_audit_cmd`.
`check_config` returns **valid**, which is the real test — `!secret` resolves at
load time, so a missing or malformed key fails there rather than silently at
00:30.

The whole *command* is the secret, not just the token: `!secret` cannot be used
inside a string, so `HA_TOKEN=!secret x` is impossible. `packages/` is tracked;
`secrets.yaml` is gitignored and has never been committed — verified, 0 commits
touch it in any branch.

One step remains and it is Bill's alone: mint a long-lived token, paste it over
the placeholder, restart. Until then the audit runs and reports
`live-check-skipped`, which is correct — the check genuinely has not run.

### INFO hygiene — 5 INFO down to 1, and two of them were misfiled

"If info is to be ignored it should not be in the audit." Right, and applying it
found that two of the five were not information at all:

```
eod: no fixed trigger time      -> silent    `at: null` is already an explicit
                                             declaration; only a MISSING `at`
                                             key warns now
eod-concurrent x2               -> 1 line    counted, not enumerated
legacy-backup-drift             -> WARN      an open decision, then actioned
live-check-skipped              -> WARN      a coverage gap, see below
```

**`legacy-backup-drift` was an open decision wearing an INFO's clothes.**
CLAUDE.md had already written the criterion — "retire it once the
manifest-driven backup has a few nights of history" — and it was met: three
nights, 570 rows, 128 entities against the legacy command's 54, a strict subset.
So `shell_command.backup_input_numbers` and its weekly automation are retired.
`reports/input_number_backup.csv` is kept as history. The rule now returns early
when the command is absent, and re-arms automatically if it ever comes back —
regression-tested both ways.

**`live-check-skipped` was hiding something real.** The message had changed from
"no token set" to `401 Unauthorized` from `http://supervisor/core/api/states`.
That proxy route is for add-ons; a `shell_command` runs inside HA Core, whose own
SUPERVISOR_TOKEN is not an HA API credential on that path. Which means
**`rule_statistics_buffer` has never executed in the nightly audit** — the rule
that caught `fridge_running_watts_24h` covering 2.6 h instead of 24 only ever ran
when I invoked it by hand with a token. Its findings were absent, not clean.

That is now a WARN, because silence would make "no findings" indistinguishable
from "never looked" — the same doctrine already applied to the SPC watchdogs.
`docs/addons/enable-live-check.md` has the fix; it needs a long-lived token only
Bill can mint, so it is his to action.

Audit is now 0 FAIL, 1 WARN, 1 INFO — and both remaining lines say something
that can change what you do.

### Overnight instrument validated on its first night, 2026-08-23

The five bins were rebuilt independently from `sensor.water_meter_volume`
history and compared against what the automation actually stored:

```
              expected (from CSV)   actual (stored)
minimum             0.000               0.0        MATCH
maximum             1.400               1.4        MATCH
bins                    5                 5        MATCH
stamp                        2026-08-23 05:00:45   local, as designed
```

Bins: 0.10 / 0.00 / 0.10 / 1.40 / 0.00 gal. `capture_stale` cleared on its own,
`day_1 = 0.0` with the other six still at the `-1` sentinel — exactly one night
recorded. The 1.40 gal at 03:13 is a discrete draw, not a trickle.

**And the honest limit, which the first result forces.** The meter resolves
0.1 gal and bins are 1 h wide, so the smallest non-zero bin is 0.1 gal/h. A
continuous drip only guarantees a count in *every* bin above that rate:

```
0.10 gal/h -> 1.0 counts/h -> every bin non-zero, min > 0
0.05 gal/h -> 0.5 counts/h -> about half the bins zero, min = 0
0.00 gal/h ->              -> all zero, min = 0
```

So **min = 0.000 rules out a drip faster than ~0.1 gal/h (2.4 gal/day), not a
slower one.** Night 1 had 3 of 5 bins non-zero, equally consistent with an ice
maker or a ~0.05 gal/h seep. Yesterday's away-window figure of 0.10 gal/h sat
right at that floor, which is why it could not be called either way.

What separates them is the **non-zero bin count across nights**, not the
minimum: a drip holds its rate so the fraction stays constant, while discrete
draws vary with use and eventually produce an all-zero night — and one all-zero
night proves there is no continuous drip at all. `sensor.water_overnight_bins`
is now the companion instrument to watch, and it is already on the card.

### A card for the overnight instrument

`dashboards/cards/utilities/water-overnight-min-flow.yaml`, embedded in the SDR
Meters view: two conditional banners (leak suspected, capture not run), the
7-night chart, and the numbers the chart deliberately does not assert.

Built on the SPC control-chart pattern this config already learned the hard way
— subgroup-ordered x-axis with dates suppressed, slots read directly rather
than through an availability-gated sensor, limit lines returning `[]` when the
source is unavailable, and `t0`/`t1` instead of the reserved `start`/`end`
parameters.

**With one inversion carried over deliberately.** Every other slot-buffer chart
treats `0` as "no valid subgroup" and draws a gap. Here **0.00 gal/h is a
perfect night and must plot**; `-1` is the "no night recorded" sentinel. Copying
the SPC `v > 0` test would have rendered a leak-free week as an empty chart —
the same inversion already caught once in the 7-night mean sensor.

So the three `data_generator` bodies were **executed in node** under the real
`AsyncFunction('entity','start','end','hass','moment', ...)` wrapper rather than
read, against five cases:

```
all -1 (armed, no nights)      -> [null x7]                     gaps
a week of zeros                -> [0,0.02,0,0,0.01,0,0]         zeros PLOT
partial history                -> [null,null,null,null,...]     sentinel gaps
a leak developing              -> [0,0.01,0.04,...,0.31]        slopes up
unknown / unavailable          -> no throw                      nulls
```

Re-run against the embedded copy after templating into the view, to prove the
YAML round-trip did not mangle the JS. The view's 15 original cards remain
byte-identical.

### Local time vs UTC, checked rather than assumed

Asked whether the overnight marks at `05:00:45` were UTC. They are not — HA
`time` triggers fire in the instance timezone. Verified empirically against
automations whose `at:` is known rather than asserted:

```
HA time_zone: America/New_York
capture_daily_dehumidifier_watts   at: "23:59:00"   fired 03:59:00 UTC
capture_daily_hdd                  at: "23:55:00"   fired 03:55:00 UTC
```

The question was well-founded, because **the two systems have opposite
defaults**: InfluxDB's `GROUP BY time(1d)` *is* UTC-aligned unless you add
`tz()`, which is precisely the CQ defect fixed the same day. Both are now
documented in CLAUDE.md's EOD TIMING section.

DST is also now recorded on the automation. Spring forward: the 02:00:45 mark
does not exist, so the night yields 4 bins instead of 5 — the guard needs 3, so
it still captures. Fall back: the repeated hour can produce one bin spanning two
wall-clock hours, which inflates it. That is a second reason the instrument uses
the MINIMUM — an inflated bin never becomes the minimum, so the leak signal is
untouched and only the regen flag can false-positive, once a year.

### Overnight minimum flow — the leak instrument, made regen-proof

Bill's caveat drove the design: the softener regenerates about once a month
around 02:00 and draws tens of gallons. Any metric built on overnight TOTAL or
MEAN would spike one night in thirty and either raise a false alarm or get its
threshold widened until it can no longer see a real leak.

**The MINIMUM across five hourly bins is immune by construction.** A regen
occupies one or two bins; the minimum comes from a clean one. Nothing has to be
excluded, filtered or remembered — the statistic does it.

**And the same pass gives the regen for free.** The maximum hourly bin IS the
regen — "it will stand out" is exactly what a max is for. One capture, two
signals. A regen that *stops* happening is itself a fault worth seeing: salt
bridge, stuck valve, dead controller.

Six marks at :45 past 00:00–05:00 give five bins; :45 because every :00 in that
range is already taken. Registered as pipeline 20 in `pipelines.yaml` with a
stamp and a stale detector, and added to CLAUDE.md's EOD table — `ha_audit`
FAILed on both omissions before they could ship, which is the manifest doing
its job.

**Proven before it had to run unattended**, per the definition-of-done gate. A
synthetic night was driven through the live automation with a 42 gal regen in
bin 3:

```
bin 1 (0.1 gal) -> min=0.1  max=0.1   bins=1
bin 2 (0.1 gal) -> min=0.1  max=0.1   bins=2
bin 3 (42.0 gal)-> min=0.1  max=42.0  bins=3     <- regen did not move the min
bin 4 (0.1 gal) -> min=0.1  max=42.0  bins=4
bin 5 (0.2 gal) -> min=0.1  max=42.0  bins=5
```

The publish branch is gated on `condition: trigger` with an id, which is not
used anywhere else in this config and therefore was not proven idiom. It was
tested by temporarily moving the 05:00:45 trigger to 90 seconds out, reloading,
and watching it fire — it stamped and rotated correctly, then the trigger was
restored.

### Two defects that test caught, both mine

- **`(now() - stamp).days` raises TypeError.** `now()` is tz-aware and
  `as_datetime()` on an input_datetime is naive. Every other daily-capture
  sensor in this config already uses `(now().date() - stamp.date()).days`; I
  deviated. It made the *watchdog* unavailable — i.e. silent, the one thing a
  watchdog must never be. Caught on deploy, not by reading the YAML.
- **Excluding zeros from the 7-day mean was exactly backwards.** The SPC buffers
  treat 0 as "no valid subgroup that day", and I copied that idiom without
  thinking about what it means here: a leak-free night genuinely reads
  **0.00 gal/h**, so excluding zeros would bias the trend upward and hide the
  good nights that prove there is no leak. Slots now hold `-1` for "no night
  recorded" and the mean includes zeros.

A fresh `input_datetime` also defaults to *today*, which made the capture look
already-done and published a phantom 0.0. Parked at 1970-01-01 like every other
never-captured stamp, and the dry-run residue cleared, so the first real reading
will be tonight's.

### LeakNow wired to the phone, and the Leak path kept

Two automations, because there are two questions.
`sdr_water_leak_now` triggers on `LeakNow > 0` held for
`input_number.sdr_leak_now_hold_minutes` (default 10, about five frames at the
measured 112 s cadence) and goes to `notify.mobile_app_bills_iphone`. A
sidebar notification would have been read after the 20.7-hour event ended,
which is the same as not having one.

`sdr_water_leak_now_cleared` fires on the way back down and dismisses the
persistent notification. The 2026-08-21 event self-cleared at 11:28 and nothing
would have said so, leaving a phone alert as the last word on a condition that
had already stopped.

Two deliberate choices:

- **The alarm is NOT gated on `sdr_alerts_enabled`.** That flag exists to mute
  commissioning noise while the dongle is being unplugged, and a real leak is
  not commissioning noise. The staleness alerts and the Leak day-bin notice
  stay muted by it; this one does not.
- **It IS gated on `binary_sensor.water_meter_stale`.** An alarm built on a
  stale decode reports a condition that may have ended hours ago.

`Leak` is kept, not replaced: detection lives in the battery-powered meter, so
the 35-day day-bin count is the backstop that still reports a leak which
happened while HA, the SDR or house power were down.

Verified by firing the automation against the live instance - the push
delivered and every template rendered - then dismissing the test notification.

### SCM status fields, and why nothing alarms on them yet

Gas and electric speak SCM, so they carry `TamperPhy` (bits 24:26),
`TamperEnc` (30:32) and `Type` (26:30) instead of leak fields. Six sensors
added. Measured across the whole retained history:

```
gas       TamperPhy 3 on all 61 frames        TamperEnc 0    Type 12
electric  TamperPhy 0 on all 1,704 frames     TamperEnc 0    Type  5
```

A constant is a meter-type characteristic, not an event. An alarm on "gas
TamperPhy == 3" would fire forever and be muted within a day. The signal worth
having is a **transition** - a tamper field changing on a meter that has never
changed it means someone at the meter, a meter swap, or a decode fault. The
sensors exist so that history accumulates; the alarm waits until the baseline
can be called honestly, because 61 gas frames is not a baseline. `ChecksumVal`
is deliberately not exposed - rtlamr verifies it and drops bad frames, so by
the time a value reaches us it has already said everything it can.

### The audit caught one of mine

`rule_entity_refs_resolve` flagged `automation.sdr_water_meter_leak_now` - an
automation declared three lines above the reference. `known_entities()` had
never included YAML-declared automations or scripts: it resolved template
sensors through the registry and `slugify(name)`, but HA derives an
automation's entity_id from `alias:` by the same rule and nothing was doing
that. Fixed, and regression-tested in both directions.

Also recorded rather than quietly repaired: **P8 was accidentally deleted**
earlier the same day when P9 was inserted over the top of it, and P1 was still
listed as open after being fixed. Both restored. A PENDING item that vanishes
silently is worse than one never written.

### The leak detection is in the meter, not in this config - and it already fired

Traced end to end, because it determines what is tunable and what survives an
outage:

```
Neptune R900 register   computes and TRANSMITS the flags
rtlamr r900.go          Reed-Solomon checks the frame, then
                        leak    = bits[74:78]   (4 bits)
                        leaknow = bits[78:80]   (2 bits)
                        - pure bit slicing, no arithmetic, no state
rtlamr2mqtt             publishes them as MQTT attributes
template sensors        state_attr(...) | int(0)  - passthrough
```

Nothing between the meter and the dashboard computes anything. Consequences:
the detection keeps running while HA, the SDR, or house power are down (the
meter is battery-powered and keeps its own 35-day record); the sensitivity
cannot be tuned; and it can see flow below a turbine's startup threshold, which
is what the leak automation's original description meant by "the one thing the
softener turbine structurally cannot provide".

**And it has already caught something.** The decode fields turn out to be
historised in InfluxDB as fields on the `gal` measurement, so there is history
predating the new sensors:

```
LeakNow  0 -> 1   2026-08-21 14:43
LeakNow  1 -> 0   2026-08-22 11:28     ~20.7 h flagged
Leak     0 throughout                  <-- the alarm's trigger never moved
```

Deep night 23:00-05:00 ran 1.6 gal over 5.00 h = 0.32 gal/h, overnight
22:00-06:30 ran 0.58 gal/h - roughly hourly +0.1 gal ticks with the house
asleep. Small: a flapper seep or a dripping fixture, not a burst.

The point for the alarm design: **`Leak` never moved, so the automation as
configured would not have fired for a 21-hour event its own meter detected.**
P9 is now graded HIGH, with the correction that the `Leak` trigger should be
KEPT rather than replaced - it is the backstop that reports a leak which
happened while the stack was down.

Limits stated: decode history begins 2026-08-21 13:28, about 24 h, so there is
no way yet to say whether this is chronic. InfluxDB writes are ~15 min apart,
so sub-interval continuity cannot be confirmed from these samples - the meter's
register has finer resolution than the data here does.

### SDR Meters view

The whole view now lives at `dashboards/views/sdr-meters.yaml` rather than only
in the UI, which puts it inside `ha_audit.py`'s dashboard scan - a card is the
one place a broken entity is completely silent.

Four cards added, in core-card idiom to match the rest of the view: no mushroom,
no HACS dependency.

- Two `conditional` banners at the very top, above Health, because an active
  leak outranks meter health. Each is hidden when its field is 0 **and** when it
  is unknown or unavailable - a banner that appears on `unknown` is a banner you
  learn to ignore.
- `R900 status fields (water)` after Raw counters, where the decode detail
  belongs, with `NoUse` under its own "encoding unconfirmed" section.
- `Reading the leak fields`, carrying the bit widths from `r900.go` and the
  warning that a stale decode is not a clean bill of health.

Verified rather than eyeballed: all 39 pre-existing entity ids resolved against
the live instance *before* editing, all 44 after; the 15 existing cards are
byte-identical once the 4 new ones are removed from the parsed tree; and every
card template was rendered through `/api/template`.

That last check earned its place. The `Reading the leak fields` table came back
as one line - `>` folds consecutive lines with a space, which collapses a
markdown table. Switched to `|`. Every other markdown card in the view is fine
with `>` because none of them has a table, and nothing about the YAML looked
wrong; only the render showed it.

### Restart, and the buffers that had to be re-seated with it

Restarted 2026-08-22. Pre-flight first: all 24 `input_number`s carrying
`initial:` already equalled their initial value, so nothing would silently
revert; 141 restore-critical entities snapshotted; and
`automation.spc_seed_on_startup` verified to write only when `day_1 == 0`, so it
could not clobber the backfilled dehumidifier buffer. After the restart: **0 of
141 missing, 0 changed.**

The fix landed:

```
sensor.fridge_running_watts_24h    before  buffer 1.00  age coverage 0.11
                                   after   buffer 0.64  age coverage 0.99
basement_*_delta_mean_24h          before  0.91-0.93    after  0.29-0.30
```

But raising `sampling_size` changed what those sensors MEASURE, and every slot
in the fridge / furnace / AC buffers had been captured under the old definition.
Measured steps:

```
fridge    110.9 -> 114.6   +3.7 W    against sigma 4.3   (0.9 sigma)
furnace   775.2 -> 771.5   -3.7 W    against sigma 5.2   (0.7 sigma)
ac       2461.9 -> 2488.4  +26.5 W   against sigma 98.7  (0.3 sigma)
```

Left alone, that is a step in the middle of three control charts and an inflated
sigma for a week - the exact failure `packages/spc.yaml` already ruled on for
the E080 swap ("CLEAR THE 7 DAY SLOTS when deploying this"). All three buffers
were re-seated from calendar-day means of each population's own gate sensor in
InfluxDB, the same method validated against the dehumidifier that morning to
0.07 W. Furnace and AC only ran 08-18..08-21, so they got 4 real slots and 3
zeros rather than invented numbers - the limit sensors already treat 0 as "no
valid subgroup that day".

Result, all six populations on consistent-provenance buffers:

```
population        daily     mean   sigma       LCL       UCL   OOC  stale
fridge            114.2    114.6     6.7     101.2     128.0   off    off
furnace           774.2    771.5     2.1     767.3     775.7   off    off
ac               2357.4   2488.4    91.5    2305.4    2671.4   off    off
hwh_recirc        109.5    106.0     1.8     102.4     109.6   off    off
dehumidifier      466.4    469.1     4.3     460.5     477.7   off    off
cooling_kwh_cdd    1.09     0.83    0.53       0.0      1.89   off    off
```

Worth noting which way the fridge moved: sigma went **up**, 4.3 -> 6.7. The
truncated window had been understating day-to-day variation, so that chart's
limits were too tight and it was primed to cry wolf. The furnace went the other
way, 5.2 -> 2.1, because four clean days beat seven mixed ones.

### Everything the new rules found, fixed

- 9 `choose:` blocks given `default: []` - behaviourally a no-op, verified by
  reversing the parsed tree exactly back to the original.
- Dead references to entities that never existed, removed without changing
  behaviour: the `sensor.hvac_runtime_per_hdd_7_day{,_mean,_std_dev}_2` fallback
  chains always took their else-path, so that path is now written directly.
  `binary_sensor.monthly_tracking_capture_stale` -> `monthly_report_stale`.
- 8 control-limit sensors now go `unavailable` instead of publishing a band
  built from a literal - the runtime-per-HDD pair plus per-CDD, furnace-cycle
  and AC-cycle upper/lower. Same decision as the 24 SPC limits on 2026-08-21.
  Verified before and after: all 12 published values and alert states unchanged,
  because every source is numeric today. The fix only bites when one goes
  missing, which is the point.
- **The Honeywell thermostats have been gone since June 2026 and five dashboard
  cards were still plotting them.** `climate.tstat_2d884c/2d8878_lyric_t6_pro_
  thermostat` -> `climate.main_floor` / `climate.upstairs` across
  temperature-heating-48h and four thermostat cards. Those series had been
  drawing nothing for two months and nothing said so.
- Two more `_2` chart references, in the runtime-per-HDD control chart and the
  runtime-per-HDD gauge.

### Still open - needs a decision

`sensor.water_meter_leak` does not exist, and `packages/utility_meters.yaml`
triggers a leak alarm on it. The automation's own comment anticipated this:
"verify it in Developer Tools and disable this automation if absent". It is
absent, so that alarm cannot fire. Create the sensor from the R900 decode or
disable the automation - not a call to make silently.

### Guards, done the way that does not lose data
All 7 remaining `shell_command` calls are guarded, but never with a bare
`condition:` on the automation — that would skip silently, and none of these has
a retry or a stale detector. Each guard is a `choose:` branch that logs at
warning instead:

- `csv_daily_report`, `csv_monthly_report`, `hvac_1f_recovery_end`,
  `hvac_2f_recovery_end` already had a validity `choose:` with a logging
  `default:`. A maintenance branch was inserted **first** — `choose:` runs the
  first option whose conditions pass, so it pre-empts the append. Kept separate
  from the validity template on purpose: a maintenance skip is not a data fault
  and must not be logged as one.
- `csv_yearly_rotation`, `rotate_setback_log_yearly`, `daily_energy_csv_export`
  were plain sequences. Each is now a `choose:` whose single option is the
  maintenance skip and whose `default:` does the real work. The two rotations
  fire once a year, at 00:03 and 00:05 on Jan 1, so their messages say plainly
  that there is no retry until next year and name the command to run by hand.

Verified live, not by inspection: with `ha_maintenance_mode` ON,
`automation.daily_energy_csv_export_00_15` was triggered manually — it ran
(`last_triggered` advanced to 13:35) while `www/energy/energy_daily_master.csv`
kept its `00:15:00` mtime. It took the skip branch and never invoked the
command. Flag restored to `off`.

Structurally verified as before: 81 untouched automations byte-identical, the
6 targets each still contain both the guard and their shell_command, and the
comment count only went up (653 -> 683).

### scripts/spc_seed.py — rewritten to carry no constants
Every appliance constant in it was wrong, and one was dangerous:

- dehumidifier threshold 250 W and band (300, 800] were the pre-E080 Santa Fe
  numbers; `spc.yaml` moved to 150 W / (150, 800] on 2026-08-07.
- worse, it computed `MEAN(dehumidifier_current_consumption) WHERE value > 250`
  — the **full-run** mean. The live pipeline has captured the warm-up-excluded
  steady window since 2026-08-07. Measured on 2026-08-21: full-run 457.4 W vs
  steady 466.4 W. Seeding would have driven a **-9.0 W** step into a chart whose
  process sigma is 2-3 W — a 3-4 sigma false signal, manufactured by the tool
  meant to repair it.
- it stamped `*_spc_last_capture`, so a seed would have impersonated a measured
  capture and silenced the stale detector. It stamps `*_spc_last_seed` now.

It is now derived from `pipelines.yaml` — the manifest that exists to stop
exactly this. It resolves each `guard.live_source` to the `entity_id:` its
statistics sensor averages and queries **that gate sensor** directly, so a
seeded point and a captured point are the same measurement by construction; no
threshold can express the dehumidifier's warm-up exclusion, and none is used.
Proof: the rewired script independently produced
`466.4 466.8 463.2 467.2 472.2 472.9 475.1` — identical to the seven values
backfilled by hand that morning.

Hardcoded InfluxDB user and password removed; environment only. The file is
untracked, but `.gitignore` covers only `secrets.yaml` / `secrets_*.yaml`, and
this repo pushes to a public GitHub remote — one `git add -A` stood between a
plaintext password and the internet. CLAUDE.md's "Credentials: see
scripts/spc_seed.py" pointer is gone with it.

`shell_command.spc_seed_from_history` deleted rather than wired up: HA does not
set those environment variables, so the wrapper could only ever fail to connect.
It is a CLI tool now, and `spc.yaml`'s header no longer claims the restart
seeder calls it — `automation.spc_seed_on_startup` seeds inline and has since
2026-08-21.

### ha_audit.py had never read dashboards/
No rule opened `dashboards/` — 88 Lovelace card files. Not academic: the
runtime-per-HDD control chart plotted `sensor.hvac_runtime_per_hdd_upper_bound`,
which does not exist, and drew no limit lines. The audit caught that only
because the same dead id also appeared in `configuration.yaml`. A card is the
one place a broken entity is completely silent — no log line, no `unavailable`
state, just an empty series. Now scanned. Still 0 FAIL.

**The audit reads: 0 FAIL, 0 WARN, 4 INFO across 19 pipelines.**

### Left alone deliberately
SUPERSEDED — all seven are now guarded, see above. Kept for the reasoning:
a bare `ha_maintenance_mode` condition was not free for any of them. `appenddailycsv`, `appendmonthlycsv`, `daily_energy_export` and
`appendsetbacklog_1f/_2f` append exactly one row; `rotatedailycsv` and
`rotate_setback_log` rotate. None has a retry or a stale detector, so a bare
`ha_maintenance_mode` condition converts "ran during maintenance" into a
permanent silent hole — and `rotate_setback_log` fires once a year, at
00:05 on Jan 1. The right shape is to fold the guard into each automation's
existing validity `choose:` so the `default:` branch logs the skip;
`appenddailycsv` already has that structure. Per-automation work, not a
search-replace.

`shell_command.spc_seed_from_history` is dead and worse than dead:
`scripts/spc_seed.py` still carries pre-E080 dehumidifier constants
(threshold 250 W, guard band 300-800 W, and it reads the full-run
`dehumidifier_current_consumption` rather than the steady gate). Run today it
would write wrong values straight into the SPC buffer. Delete the command or
fix the constants — but not silently.

### Found, not yet fixed
`rule_fabricated_constants` only scans `packages/spc.yaml`. The HDD/CDD
bounds in `configuration.yaml` carry the same defect it exists to catch —
`| float(18.0)` and `| float(2.0)` against a real mean of 29.1 and std_dev of
6.8. That fallback is what drew the false low alert above. The reference is
fixed so it is unreachable now, but it is one typo from doing it again.
Widen the rule to every config file, and make those limits go `unavailable`
rather than fall back, the way the SPC limits were changed on 2026-08-21.

### Measured
- Steady-window watts track **basement temperature at r² = 0.92, +7.64 ±
  0.64 W/°F** over 2026-08-08..08-21 (n=14, t=11.9). The whole 463.2 -> 476.4
  -> 466.4 W excursion is a 1.5 °F basement temperature swing. Daily sd falls
  from 4.60 W to **1.29 W** after normalising on temperature. Basement temp and
  dew point are collinear at r = 0.9986 and cannot be separated by this data.
  This reverses the 2026-08-07 finding ("basement temperature is NOT the
  explanation"), which was fitted over a 0.78 °F span — too short a lever arm.
  Consequence: the raw-watts chart has a ±8.6 W (2σ) detection floor that is
  mostly weather. Normalising would take it to ±2.6 W. Not implemented.
- The `459 W / 2.1 W` fallback constants in `packages/spc.yaml` describe
  2026-08-05..08-07 only. The process has since run 463-477 W. They are
  unreachable while the limit sensors are available, but they are stale.

## [2026.08.21] - 2026-08-21

### SPC Chart Correctness Fix

Five of the six SPC control charts were drawing nothing, or drawing stale data
under this week's dates. Root causes were in the chart layer and in the limit
sensors, not in the capture math.

### Fixed
- **Sigma collapse** - `*_sigma_7d` returned 0.0 when every valid slot held the
  same value (seed or reset values, e.g. the dehumidifier's three 459.0 W
  slots). UCL and LCL then landed exactly on the centre line: no band on the
  chart, and any deviation trips the out-of-control test. A degenerate sigma
  now falls back to the documented default (guard at half the slot
  resolution - 0.05 W, 0.005 kWh/CDD). Dehumidifier band restored from
  459.0/459.0 to 454.8/463.2.
- **Limits published without data** - `*_mean_7d`, `*_sigma_7d`, `*_upper` and
  `*_lower` had no `availability:` and fell back to hard-coded constants, so
  a population with zero valid slots still drew a control band around a number
  no measurement supported. All 24 limit sensors now require at least 2 valid
  slots (`> 0`) and go unavailable otherwise. The `*_out_of_control` binaries
  read the limits through `| float(0)` and require `u > 0`, so they stay quiet.
- **Charts sourced from recorder history** - The fridge / AC / dehumidifier
  cards plotted `sensor.<x>_running_watts_daily` with `group_by: last / 1d`.
  That sensor is availability-gated to a capture stamp no older than one day,
  so one skipped capture blanked the columns for the whole window. Cards now
  read `input_number.<x>_day_1..7` directly - no recorder dependency, correct
  immediately after restart, unaffected by `purge_keep_days`.
- **Fabricated column dates, and the blank-chart cliff** - The HWH and furnace
  `data_generator` cards dated slot i as "i+1 days ago". Slots rotate only on a
  *successful* capture, so that holds only while every night captures: HWH last
  captured 2026-08-01 but its chart labelled those columns 08-14..08-20.
  Anchoring the columns to `input_datetime.<x>_spc_last_capture` fixed the
  misdating but exposed the deeper problem - apexcharts-card re-stamps
  `xaxis.min/max` from `graph_span` on every refresh
  (`this._apexBrush || (q.xaxis = {min: ..., max: ...})`), so the axis cannot
  follow the data and a stale population falls outside the window entirely.
  On 2026-08-21 HWH had 0 of 7 slots inside a 14d window and dehumidifier 1 of
  7 - both charts drew no bars. Widening `graph_span` only moves the cliff:
  furnace and AC go months without a capture every off-season by design.
  **The x-axis is now subgroup order, not wall-clock time** - the 7 subgroups
  are laid out on the last 7 day-slots of an 8d window so the chart is always
  full, with `xaxis.labels.show: false` and `tooltip.x.show: false` so no date
  is asserted anywhere on the chart. An XmR chart is indexed by subgroup, so
  this is the conventional rendering as well as the only one that survives a
  capture lapse. Real capture dates live in `spc-capture-stale.yaml`.
- **Zero slots broke the chart** - `parseFloat(d.state)` turned a 0 slot into a
  real 0 column, clipped against the hard `yaxis: min:` and dragging the scale
  down; `d.state` on a missing entity threw a TypeError that blanks the card.
  0, NaN, `unknown`, `unavailable` and missing entities now all map to `null`,
  which ApexCharts renders as a gap. Verified: 24 generators x 7 state
  scenarios, zero throws.
- **Clipped y-axes** - Hard-coded min/max (dehumidifier 400-610, HWH 80-120,
  furnace 700-800) hid any point outside the band. Now auto-scaled; UCL and LCL
  are series, so the band always fits.

### Fixed - EOD freeze retired, six blind spots closed (2026-08-21)

**The freeze was obsolete and unenforceable.** CLAUDE.md banned time triggers
between 23:54:30 and 23:58:45 and listed 9 EOD entries. There were 19 capture
automations, **9 inside that window, 4 documented nowhere**. Replaced with the
actual intent - *no two automations may contend for the same state* - plus a
complete schedule generated from `pipelines.yaml`, and the ordering
dependencies that are the real reason for the staggering (23:56:30 immovable;
the monthly archives must follow it).

**`eod-collision` was a false positive and is now `eod-race`.** The old rule
flagged any shared trigger second, which reported the six SPC captures at
23:59:00 as a collision. Verified they are not: no pair writes a shared entity.
The rule now computes read and write sets and only reports genuine contention -
write/write FAILS, read/write WARNs, and same-second automations sharing
nothing report INFO. A rule that cries about six harmless automations is how a
rule teaches you to ignore it.

**Capture stamps now snapshot the date.** CLAUDE.md requires EOD captures to
snapshot at trigger time; the values obeyed but the stamps were a live
`{{ now().date() }}` evaluated at execution. Six captures fire together at
23:59:00 with 60 s to midnight - one slipping past would stamp TOMORROW against
today's data, and every staleness detector reads that stamp. The six SPC
captures now snapshot `capture_date` in the same `variables:` block as the
values. New rule `stamp-not-snapshotted` reports the remaining 13, all of which
fire at 23:55-23:58 with minutes of headroom rather than seconds.

**All six unmonitored pipelines closed. 19/19 now have a stamp and a detector.**
- New stamps: `dehumidifier_duty_kwh_capture_last_ok`, `hdd_archive_last_ok`,
  `cdd_archive_last_ok`, `gas_heat_cost_archive_last_ok`, with a
  `set_datetime` appended as the final action step of each capture so it only
  fires if everything before it did.
- New detectors: `dehumidifier_duty_kwh_capture_stale`, `ac_cost_capture_stale`,
  `dehumidifier_cost_capture_stale` (daily, opportunity-gated like the SPC
  watchdog) and `hdd_archive_stale`, `cdd_archive_stale`,
  `gas_heat_cost_archive_stale` (monthly, 35-day threshold rather than
  month-boundary arithmetic, which assumes the archive runs within the current
  month - these run at 23:58 on a day the detector should not need to know).

Audit: **0 FAIL, 25 WARN, 4 INFO** (was 26 WARN with 6 pipelines unmonitored).
Remaining backlog: 13 `stamp-not-snapshotted`, 8 `unguarded-shell-command`,
3 `dead-shell-command`, and the dehumidifier `empty-buffer` that should clear
after tonight's capture.

Process note: `automations.yaml` was broken twice while inserting the stamps -
first by appending at the end of the automation block (which landed after
`mode:`, outside the action list), then by assuming 2-space list indentation
where the file uses 4. Both were caught immediately by parsing after the write
and reverted; the second attempt was made from a backup taken first. The fix
detects the list indentation from the existing items instead of assuming it.

### Added - packages/audit.yaml, the audit as a UI action (2026-08-21)

`scripts/ha_audit.py` was command-line only. It is now runnable from
**Developer Tools > Actions > "Run HA Audit"** (`script.ha_audit`), which posts
a persistent notification with the full report - FAILs first, then WARN, then
INFO - and records the result in helpers so it is visible without opening a
terminal.

Design points:
- `ha_audit.py` gained `--json` and `--log`. The script parses JSON rather than
  scraping the summary line, so rewording a finding cannot silently break the
  sensors. `--log` archives the human-readable report to
  `www/spc/ha_audit.log` independently of the output mode.
- `shell_command` behaviour verified against HA 2026.8.2
  `components/shell_command/__init__.py` before designing around it:
  `SupportsResponse.OPTIONAL` (so `response_variable` works and Dev Tools shows
  the response), returns {stdout, stderr, returncode}, no truncation, non-zero
  exit is logged rather than raised - so `ha_audit.py` exiting 1 on FAIL does
  not break the script - and `COMMAND_TIMEOUT = 60`. Measured runtime 1.5 s
  over Samba, faster on the host.
- `automation.nightly_ha_audit` at 00:30, after the 00:20 buffer backup. An
  audit you have to remember to run is an audit that does not run - the same
  reasoning that produced the SPC capture watchdog.
- `binary_sensor.ha_audit_failing` and `binary_sensor.ha_audit_stale` are
  separate on purpose: if the audit stops running, the FAIL count freezes at
  its last good value and looks healthy forever.
- Both carry no `availability:` block, deliberately, for the same reason as the
  capture watchdog.

Fixed while building it - the auditor was blind to its own package. Its file
lists were hardcoded, so `packages/audit.yaml` was invisible the moment it was
created, and the shell_command guard check only scanned `automation:` blocks,
so a guard held in a `script:` (which is where `script.ha_audit` holds it) read
as unguarded. Packages are now globbed and scripts are scanned as callers.
Verified: 0 cross-package duplicate keys, 0 FAIL, 26 WARN, 2 INFO.

### Added - pipeline manifest, static audit, buffer backup (2026-08-21, steps 3-4)

**pipelines.yaml (repo root, NOT HA config).** All 19 daily-capture pipelines
declared once: trigger time, capture stamp, seed stamp, buffer slots, stale
detector, season, and for SPC the guard source/band/activity and limit sensors.
Derived FROM the config rather than typed from memory; `ha_audit.py` re-derives
and FAILS on drift, so it cannot rot the way its five predecessors did (the
capture automation, the sensor templates, the dashboard card, CLAUDE.md
§ENTITIES, and spc_validator.py). Three drifts found while building it:
- CLAUDE.md's "EOD TIMING SEQUENCE - FROZEN" lists 9 entries; there are 19
  capture automations. Undocumented: 23:55:15, 23:55:30, 23:56:45, 23:59:30,
  23:59:45. `archive_monthly_hdd` has drifted from 23:58:00 to 23:58:15.
- Stale-detector coverage cannot be established by name - matching
  `capture_daily_cdd` to `cdd_capture_stale` by similarity gives false joins.
  The real relationship is the stamp entity the detector READS.
- 4 pipelines write buffers but stamp nothing, so their liveness cannot be
  monitored even in principle. Listed under `gaps`.

**scripts/ha_audit.py.** Offline static audit (config + registry +
restore_state; no API, no token, runs while HA is down). Every rule names the
incident that earned it: manifest drift, entity resolution, liveness coverage,
EOD collisions vs CLAUDE.md, unlatched statistics guards, fabricated numeric
constants near buffer writes, dead/unguarded shell_commands, repeated or empty
buffers, legacy backup drift. Current: **0 FAIL, 26 WARN, 2 INFO** - the FAIL
rules cover this week's fixes and all pass; the WARNs are a real backlog
(6 pipelines with no liveness signal, 8 unguarded shell_commands, 3 dead ones,
6 undocumented EOD times).

**scripts/spc_buffer_export.py + automation.nightly_buffer_backup (00:20).**
Manifest-driven, append-only CSV at `www/spc/buffer_backup_master.csv`, long
format so adding a pipeline never changes the schema. Reads
`.storage/core.restore_state` directly - no API and no token, so it works while
HA is down, which is when a backup matters. 00:20 because restore_state flushes
every 15 min, so the 23:59 captures are on disk by 00:14; a slot whose
last_changed still predates its capture stamp is reported as STALE-FLUSH rather
than silently backed up. `--restore LATEST` prints a reviewable replay plan and
never writes back on its own. Deduped by entity - found by running the exporter
twice in the same second, which produced a plan setting each entity twice.

**input_boolean.ha_maintenance_mode CREATED.** CLAUDE.md has mandated "MUST wrap
every shell_command call with ha_maintenance_mode guard" for a long time, but
the input_boolean was never defined - the only reference in the entire config
was the guard added that same day. A condition on a non-existent entity is
`unknown`, which never equals "off", so the guard would have silently prevented
the guarded automation from ever running. A safety interlock that disables what
it protects is the same failure class as a watchdog that goes unavailable.

A partial backup already existed and is NOT redundant with this one:
`shell_command.backup_input_numbers` (weekly, Sun 04:00) is a hand-maintained
list of ~57 `states()` calls covering the HDD/CDD/runtime buffers. It predates
the SPC package and was never extended - **54 of 121** buffer entities, none of
the 42 SPC running-watts slots, none of cooling_kwh_cdd, no capture stamps.
Keep both until the manifest-driven backup has a few nights of history.

### Fixed - CI was red and had been for a while (2026-08-21, step 2 of the audit plan)

`.github/workflows/validate.yml` runs yamllint over the whole repo. It was
reporting **64 errors and 5 warnings across 21 files**, so the gate had stopped
being a gate - which is the same failure mode as an unread alarm, and is how
the 7 CRLF card snippets sat broken without anyone noticing.

**Real fixes (26 files, whitespace only, every one verified):**
- CRLF -> LF in 15 YAML files: `configuration.yaml`, `automations.yaml`,
  `packages/watchdog.yaml`, 7 card snippets, `grafana/provisioning/
  dashboards/default.yaml`, both `scripts/seed_*_archives.yaml`.
- Missing final newline added to `configuration.yaml`,
  `packages/energy_export_package.yaml`, `esphome/ina228-bringup.yaml`.
- 11 non-YAML files normalised in the same commit (5 Grafana dashboards, 2
  Python scripts, 3 markdown, 1 SQL) so `.gitattributes` does not surface them
  as a mystery diff inside some later unrelated change.
- Each file was parsed BEFORE and after and the object graphs compared - YAML
  via a loader taught HA's `!include`/`!secret`/`!lambda` tags, JSON via
  `json.loads`, Python via `compile()`. Any file whose parse changed would have
  been reverted; none did. "Whitespace-only by construction" is exactly what
  was said about the apexcharts `data_generator` signature, so it gets checked.

**Scope corrections in `.yamllint.yml`** - each with its reasoning inline,
because silencing a rule and scoping a rule look identical in a diff:
- `baseline-repo/` - a nested repository with its own `.git`,
  `.github/workflows/` and `.markdownlint.json`. It lints itself; linting it
  from here reported errors that can only be fixed in the other repo.
- `secrets.yaml`, `secrets_*.yaml`, `esphome/secrets.yaml` - gitignored, so the
  CI checkout never contains them. Linting them locally made the local run
  disagree with CI, which teaches you to distrust the local run.
- `scripts.yaml`, `automations.yaml`, `scenes.yaml` - UI-managed. HA rewrites
  them wholesale in its own serializer style (2-space sequence indent,
  `metadata: {}`, device_id GUIDs) on every UI edit, so a reformat is reverted
  the next time you touch a script and the job flaps red forever. Their
  validity is NOT unchecked: the `ha-config-check` job parses them in full,
  which is the stronger test.
- `esphome/` exempted from `colons` and `comments-indentation` only. Those
  configs use column-aligned value tables for register maps where the extra
  spaces are the readability, and ESPHome owns their validation via a real
  compile - a far stronger gate than a style rule. Structural rules still
  apply there.

**Prevention - `.gitattributes` (new).** `*.yaml text eol=lf` and friends, so
CRLF cannot come back from Windows/Samba editing. Scoped to text formats
only; CSV is deliberately excluded, since the reporting CSVs are append-only
data files and renormalising them on checkout would rewrite data.

Result: `yamllint --strict` exits 0 with zero errors and zero warnings, so the
job passes regardless of how the action's `strict` input is set. 136 text
files checked: 0 CRLF remaining.

Noted, not fixed: `grafana/dashboards/` holds several near-duplicate exports
(`Battery Bank.json` vs `battery_bank.json`, three `energy_*` variants). Same
class of drift as the duplicate dehumidifier SPC card - worth a pass later.

### Added - SPC capture watchdog (2026-08-21, step 1 of the audit plan)

Coverage audit of stale detection across every daily-capture pipeline:

| | pipelines | with a stale detector |
| --- | --- | --- |
| non-SPC (hdd, cdd, runtime_per_hdd, runtime_per_cdd, furnace_cycle, monthly_tracking, ...) | 10 | 6 |
| SPC (fridge, furnace, ac, hwh_recirc, dehumidifier, cooling_kwh_cdd) | 6 | **0** |

The watchdog pattern already existed and worked; SPC was never wired into it.
That gap is the whole reason the dehumidifier could stop capturing on
2026-08-07 and HWH recirc on 2026-08-01 and go 14 and 20 days unnoticed.

- **binary_sensor.<pop>_spc_capture_stale** x6, modelled on
  `binary_sensor.runtime_per_hdd_capture_stale`, plus an OPPORTUNITY GATE.
  A bare "last capture is old" test is wrong here: furnace and AC legitimately
  go months silent every off-season, and an alarm that cries all summer gets
  switched off. Each detector instead asks whether the pipeline had the chance
  to capture and failed to take it - opportunity being any qualifying activity
  today, the same quantity the capture guard reads. Out of season it is zero
  and the detector stays quiet, with no calendar heuristic to maintain.
  Gated on activity > 0 rather than the guard's own threshold on purpose: an
  appliance that runs for days and never clears its guard band IS the fault
  worth surfacing. This system has had that failure twice - the Santa Fe ->
  E080 swap, and the 300 W furnace floor hiding the low-speed recirc mode.
  Threshold is 2 days, not 1: one missed night is legitimate (the guard band
  rejects thin days by design), two consecutive while running is a signal.
- **binary_sensor.spc_capture_stale_any** - roll-up with a
  `stale_populations` attribute; the single signal to alarm on.
- **automation.notify_spc_capture_stale** - persistent notification with a
  2-hour debounce (the opportunity gate can flip during the morning as an
  appliance starts), listing the stale populations and all six last-capture
  dates, and pointing at the nightly `SPC skipped` log line.
- **dashboards/cards/conditional/spc-capture-stale.yaml** rewritten as a
  conditional entities card over the new sensors. The previous markdown
  version recomputed staleness in Jinja on the card - duplicating the rule
  where nothing validates it, and with no opportunity gate.

Detectors carry no `availability:` block, deliberately, against the file's own
convention: a watchdog that can go unavailable fails in the direction that
hides the fault. A truth-table run (8 cases x 6 detectors) caught exactly that
bug in the first draft - an unparseable stamp returned `false` and the
watchdog went quiet. Now an unparseable stamp reports stale. Final: 0
mismatches across 48 evaluations.

### Fixed - the nightly captures could almost never run (found 2026-08-21, 3rd pass)
- **Every capture guard read a sensor that is unavailable at 23:59.** Each
  `*_running_watts_24h` is the `statistics` platform over a `*_power_when_on`
  sensor, and those are availability-gated to "appliance is above threshold
  right now". Verified in HA 2026.8.2,
  `components/statistics/sensor.py::_add_state_to_queue`:

      self._attr_available = new_state.state != STATE_UNAVAILABLE
      if new_state.state == STATE_UNAVAILABLE:
          self._attr_extra_state_attributes[STAT_SOURCE_VALUE_VALID] = None
          return

  The availability assignment precedes the early return and no `available`
  property overrides it, so a statistics sensor is unavailable for exactly as
  long as its source is. The sample buffer is untouched - only the flag flips.
  The captures fire at a fixed 23:59:00 and read `| float(-1)`, so `w > 0` was
  false whenever the appliance was not running at that instant. Measured
  source-available fractions: dehumidifier steady window ~1.7-2.9 % of the day,
  HWH recirc ~3.1 %, fridge/AC/furnace tens of %. That is exactly the observed
  pattern - dehumidifier silent since 2026-08-07 (the day capture moved to the
  steady series), HWH since 2026-08-01 (four nights after the 07-28 switch to
  `*_running_watts_24h`), fridge/AC/furnace intermittent (AC and furnace
  captured 08-19, skipped 08-20).
  Diagnosis originally inferred from `sensor.dehumidifier_startup_deficit`
  flipping to unavailable in the same second as `power_when_on_steady`, despite
  depending only on the two statistics sensors; then confirmed against source.
- **Sampling bias, same cause.** A subgroup was recorded only on nights the
  appliance ran at 23:59:00, which correlates with load - the centre lines were
  built from busy nights only. The AC chart is the most likely to be biased
  warm; treat its pre-2026-08-21 limits with suspicion.

### Added
- **sensor.{fridge,furnace,ac,hwh_recirc}_running_watts_latched** and
  **sensor.dehumidifier_running_watts_steady_latched** - trigger-based template
  sensors holding the last NUMERIC value of each 24h statistics mean. Verified
  in `components/template/trigger_entity.py`: state is written only on a
  trigger update and restored via `async_restore_last_state()` when the trigger
  has not yet fired, so the value survives both the source going unavailable
  and a restart. A `condition:` keeps a non-numeric transition from clobbering
  the latch (`components/template/config.py::CONFIG_SECTION_SCHEMA` accepts
  `CONF_CONDITIONS` alongside `CONF_TRIGGERS`). The five capture guards, the
  five `today_w` snapshots and the five `*_out_of_control` binaries now read
  the latch. Staleness stays with the existing activity gates - simulated:
  cycles=0 and cycles=1 still skip, cycles=2 captures, and an unpopulated
  latch skips rather than inventing a value.

### Fixed - the seeder was manufacturing data (found 2026-08-21, 2nd pass)
- **`automation.spc_seed_slots_manual` wrote invented values into the charts.**
  On every HA restart, for each population, if `day_1 == 0` it wrote ONE value
  into `day_1`, `day_2` AND `day_3` — falling back to a hard-coded "typical"
  constant whenever the live 24h mean was out of band, which includes the
  common startup case of the source sensor being unavailable (`float(0)` -> out
  of band). It then stamped `*_spc_last_capture` with today's date.
  Observed on the dehumidifier: `day_1..day_3 = 459.0, 459.0, 459.0`, stamped
  2026-08-08. Exactly `459.0` three times is the `else 459` constant; a
  measured mean carries decimals and differs day to day (every other
  population's slots are distinct — fridge 7/7, furnace 7/7, AC 7/7, HWH 5/7).
  Sequence: the 2026-08-07 E080 retune zeroed the slots, the next restart saw
  `day_1 == 0`, and the constant was painted in.
  Three defects followed:
    1. The control chart contained points nobody measured.
    2. Three identical slots make `sd = 0` BY CONSTRUCTION — the seeder, not
       the process, is what collapsed UCL and LCL onto the centre line.
    3. `*_spc_last_capture` could not distinguish measurement from seed, so
       the staleness banner under-reported a real measurement drought.
  Now: seed only from a MEASURED in-band mean, only into `day_1` (one seed
  event is one subgroup, not three), and stamp the new `*_spc_last_seed`.
  With no valid measurement, nothing is written and nothing is invented.
- **Sigma fallback replaced with an unavailability gate.** The first pass
  substituted the documented default when `sd` collapsed to 0. That drew a
  plausible-looking band (454.8-463.2) around a fabricated centre line, which
  is worse than the collapse it replaced. `sd = 0` across two or more subgroups
  is the signature of a repeated value, not of a perfect process, so
  `*_sigma_7d` now goes unavailable and `*_upper`/`*_lower` follow via their
  `is_number()` guards. Verified: dehumidifier limits refuse to publish today;
  after two real captures (458.2, 460.1) they return as 456.5/461.7.

### Added
- **input_datetime.{fridge,furnace,ac,hwh_recirc,dehumidifier}_spc_last_seed** -
  seed provenance, kept separate from the capture stamps so
  `*_spc_last_capture` now means measurement and nothing else.
- **dashboards/cards/apexcharts/spc-running-watts-control-chart.yaml** - all six
  corrected cards (fridge, furnace, AC, HWH recirc, dehumidifier, and a first
  card for cooling kWh/CDD, which had sensors but no chart).
- **dashboards/cards/conditional/spc-capture-stale.yaml** - names any population
  that missed last night's capture and how many days stale it is. Hidden while
  all six are fresh. Needed because a stale population's chart is now correctly
  blank rather than misleadingly full.

### Known Issues (not fixed here - need host access)
- `dehumidifier_spc_last_capture` stuck at 2026-08-08, `hwh_recirc` at
  2026-08-01. Both capture guards are skipping nightly. Run
  `python3 scripts/spc_validator.py --check-capture` on the HA host, or search
  the log for `SPC skipped`, to see which term fails.
- Grafana `spc_appliances.json` is NOT affected by the capture-guard skips: its
  Daily/Mean series come from the InfluxDB continuous queries in
  `scripts/spc_continuous_queries.sql`, which compute the daily mean straight
  from the raw `"W"` measurement and never consult the day_1..7 slots. So
  Grafana can show a daily point on a night HA skipped. Useful as a
  cross-check on which side is at fault - but note the CQs apply only a fixed
  power threshold, with none of the runtime, cycle-count or steady-window
  guards, so a Grafana point is not the same statistic as an HA slot.

### Note
- No new entities. `input_number` slot semantics unchanged: 0 still means "no
  valid subgroup that day" and is excluded from mean and sigma exactly as
  before - the charts now agree with the sensors on that.

---

## [2026.07.28] - 2026-07-28

### SPC Formula Alignment Fix

Fixed mismatch between HA and Grafana SPC charts for all 5 appliances. Both systems now use identical calculation: mean of power samples when appliance is running above threshold.

### Fixed
- **All SPC captures** - Changed from `energy/runtime` to `*_running_watts_24h` sensors
  - Old formula: `total_daily_energy / running_time` (included standby energy, inflated values)
  - New formula: `MEAN(power) WHERE power > threshold` (matches Grafana CQ)
- **Furnace recirc subtraction** - No longer needed; threshold gate (>300W) automatically excludes recirc
- **HWH Recirc condensate netting** - No longer needed; threshold gate (>70W) handles it

### Technical Details
- Captures at 23:59 use trailing 24h mean (≈ calendar day at that time)
- Thresholds: Fridge 50W, AC 300W, Furnace 300W, HWH Recirc 70W, Dehumidifier 250W

---

## [2026.07.23] - 2026-07-23

### Energy Dashboard Accuracy Fix

Fixed fundamental energy calculation errors in Grafana dashboards. InfluxDB INTEGRAL function was returning 6x overestimated values due to sparse SEM data (devices only report on power changes). Replaced all INTEGRAL queries with utility meter queries for accurate energy tracking.

### Added
- **Utility meters for all SEM circuits** - 13 new daily/monthly utility meters in `packages/sem_meter.yaml`:
  - `sem_dishwasher_daily/monthly`, `sem_microwave_daily/monthly`, `sem_garage_daily/monthly`
  - `sem_bedroom_office_daily/monthly`, `sem_family_room_daily/monthly`, `sem_master_suite_daily/monthly`
  - `sem_laundry_bedroom_daily/monthly`, `sem_dining_kitchen_lights_daily/monthly`
  - `sem_counter_1_daily/monthly`, `sem_counter_2_daily/monthly`, `sem_washer_daily/monthly`
  - `sem_other_daily/monthly` (includes integration sensor for Other power)
- **sensor.hvac_indoor_dew_point** - Upstairs dew point (Magnus formula from temp+humidity)
- **sensor.hvac_dp_split** - Outdoor minus indoor DP (positive = latent load on AC)
- **sensor.hvac_dp_split_mean_24h** - 24h rolling mean DP split for daily correlation
- **Dashboard scatter plot** - kWh/CDD vs DP Split to visualize sensible vs latent cooling load

### Fixed
- **Daily Energy by Circuit panel** - Replaced INTEGRAL queries with utility meter queries (was showing ~22 kWh when actual was ~4 kWh)
- **Cost by Circuit panel** - Replaced INTEGRAL queries with utility meter queries
- **Today's Energy by Circuit panel** - Replaced INTEGRAL queries with utility meter queries
- **Cost by Circuit (Today) panel** - Replaced INTEGRAL queries with utility meter queries
- **Root cause**: SEM devices only report when power changes (sparse data), causing INTEGRAL to incorrectly interpolate across gaps. Utility meters track actual cumulative energy from HA's `total_increasing` sensors.

### Changed
- **Cooling efficiency panels** - Now include blower energy (AC + blower kWh/CDD)
- **Threshold** - Updated from 0.88 to 1.14 kWh/CDD to reflect AC+blower baseline

### Removed
- **sensor.hvac_ac_blower_power/energy** - Removed unused template/integration sensors
- **hvac_ac_blower_daily/monthly** - Removed unused utility meters
- **scripts/seed_ac_blower_energy.py** - Removed unused backfill script

---

## [2026.03] - March 2026

### DHW Archive System

Added Navien-metered DHW tracking for accurate heating gas isolation. Replaces fixed 23.9% DHW ratio with actual monthly readings.

### Added
- **DHW monthly archives** - 12 `input_number.dhw_archive_*` entities for Navien-metered DHW (CCF)
- **DHW 12-month sensor** - `sensor.dhw_gas_12m` sums all monthly DHW archives
- **DHW bill entry** - `input_number.dhw_bill_thm` accepts Therms, auto-converts to CCF (× 0.9643)
- **DHW save button** - `input_button.save_dhw` archives to previous month (enter on 1st)
- **DHW save automation** - `save_dhw_button` handles Thm→CCF conversion and archiving
- **DHW seed script** - `script.seed_dhw_archives` loads historical Navien data
- **Dashboard cards** - `dhw-bill-entry.yaml`, `dhw-12m-total.yaml`, `dhw-monthly-summary.yaml`

### Changed
- **Heating efficiency sensor** - Now uses actual DHW subtraction (Total Gas - DHW) instead of fixed 71.9% ratio
- **Building UA sensor** - Now uses actual DHW subtraction instead of fixed ratio
- **DHW ratio** - Corrected from 23.9% to 28.1% based on Navien metering (220.8 CCF / 787 CCF)
- **Gas heating/DHW usage sensors** - Updated ratios (71.9% heating, 28.1% DHW)

### Fixed
- **Heating intensity accuracy** - Previous 106 CCF/1kHDD reduced to 103 CCF/1kHDD with actual DHW subtraction
- **Billing period alignment** - Separate DHW entry (1st of month) reduces misalignment with gas bills (~10th)

---

## [2026.02] - February 2026

### Setback Recovery System Simplification

Major refactor replacing ~60 entities (rolling window slots, transient helpers, complex binary sensors) with a simple state machine using explicit input_boolean latches.

### Added
- **Furnace min/cycle statistical tracking** - 7-day rolling mean, std dev, and ±2σ bounds for furnace cycle length monitoring. Includes daily capture automation, 7 input_number slots, and dashboard cards (mushroom + ApexCharts control chart).
- **Dehumidifier Performance Tracking** - Pull-down rate, hold time, duty cycle, margin sensors
- **Per-zone setback CSV files** - `hvac_setback_1f.csv` and `hvac_setback_2f.csv` via Python script
- **State machine latches** - `input_boolean.hvac_*f_recovering` for explicit state tracking
- **Recovery start temp tracking** - `input_number.hvac_*f_recovery_start_temp`
- **Setback lowered automations** - Capture utility-driven mid-cycle setpoint drops
- **Safety timeout automations** - 14h setback stuck, 4h recovery stuck, 1 AM midnight audit
- **Rolling 12-month efficiency sensors** - `sensor.hvac_heating_efficiency_12m` and `sensor.hvac_building_load_ua_12m` using archived monthly data, immune to midnight oscillation
- **Monthly HDD archives** - 12 `input_number.hdd_archive_*` entities for rolling 12-month calculations
- **HDD archive automation** - `archive_monthly_hdd` captures month total at 23:58 on last day of month

### Fixed
- **PirateWeather recorder exclusion** - Changed from blanket `sensor.pirate_weather_*` glob to selective exclusion. Now records temperature, feels_like, humidity, dew_point, and wind sensors for ApexCharts history. Excludes visibility, cloud_cover, uv_index, ozone, condition, pressure, data_age, and all forecast sensors.
- **archive_monthly_hdd double-count** - Removed redundant `+ sensor.hvac_hdd65_today` from archive variable; `hdd_cumulative_month_auto` already includes today's HDD (added at 23:56:30)
- **Efficiency alert _1s suffix** - Fixed references to `sensor.hvac_runtime_per_hdd_upper_bound_1s` / `_lower_bound_1s` (should be `_upper_bound` / `_lower_bound`)
- **Furnace cycle capture watchdog** - Added `input_datetime.furnace_cycle_capture_last_ok`, `binary_sensor.furnace_cycle_capture_stale`, and `notify_furnace_cycle_capture_stale` automation for monitoring
- **Weekly backup completeness** - Added 6 furnace/zone monthly accumulators and 7 furnace_min_per_cycle_day values to `backup_input_numbers` shell command
- **DHW ratio correction** - Updated from 28.1% to 23.9% per baseline analysis (188 CCF DHW / 787 CCF total annual). Affects `sensor.gas_dhw_usage_month`, `sensor.gas_heating_usage_month`, and 12-month efficiency/UA sensors.
- **Midnight oscillation (final fix)** - Replaced continuously-evaluated MTD sensors with rolling 12-month sensors calculated from archived data. MTD sensors had race conditions at midnight when `now().day` and `captured_today` logic changed simultaneously. New 12-month sensors only update when archives change (monthly).
- **Heating efficiency MTD nightly oscillation** - Eliminated 3-4 point drops at 23:55 by moving HDD/CDD accumulator updates from `capture_daily_hdd` (23:55) to `capture_daily_monthly_tracking` (23:56:30), setting timestamp FIRST before any accumulator updates, and unifying all month sensors to use `monthly_tracking_capture_last_ok`
- **HDD double-counting** - Cumulative month/year sensors now use `captured_today` guard
- **Setback start debounce** - 5-second delay filters Resideo firmware 1-second glitches
- **Recovery rate units** - Changed from °F/hr to min/°F (time per degree, not speed)
- **Weather freshness** - Changed from `last_changed` to `last_updated` for accurate staleness
- **Pirate Weather forecasts** - Migrated to `weather.get_forecasts` service (HA 2024.3+ compatible)
- **Expected runtime sensor** - Dual-source fallback for `_2` suffix entity compatibility
- **Recovery start guard** - Requires comfort setpoint restored before declaring "recovering"
- **Overnight setback cycle hardening** - Time window gates, mode: single, timestamp validation
- **CSV report hardening** - Data validity checks, duplicate prevention, rotation fixes

### Changed
- **Short cycling alert: zone → furnace level** - Replaced `binary_sensor.hvac_short_cycling_alert_1f/_2f` with single `binary_sensor.hvac_furnace_short_cycling_alert`. Uses actual furnace cycles (overlapping zone calls = 1 cycle) instead of per-zone calls. Suppressed during setback recovery. Eliminates false positives during morning recovery when zone calls are short but furnace runs continuously.
- Recovery tracking from 7-slot rolling windows to direct CSV logging
- Setback start stores MTD accumulator snapshot (hours) instead of daily runtime (minutes)
- Recovery minutes subtract 10-minute stability wait from elapsed time
- Heating efficiency MTD minimum HDD guard: 0 → 5 (prevents divide-by-near-zero)
- **Performance vs Baseline sensors** now use 12-month rolling sensors instead of MTD
- **Efficiency/UA alerts** now use 12-month sensors for stability (7-day runtime/HDD remains for operational alerting)
- **Recorder optimization for HA Green** - Increased commit_interval from 2→5 seconds for eMMC longevity; excluded weather sensors (`sensor.pirate_weather_*`, `weather.*`) and `sensor.climate_norms_today` from history (frequent updates, no history needed for analysis)

### Removed
- `notify_efficiency_degradation` automation - Deleted entirely (was disabled with always-false condition; superseded by runtime/HDD ±2σ alerts)
- `binary_sensor.hvac_short_cycling_alert_1f` / `_2f` - Replaced by furnace-level alert
- `notify_short_cycling_1f` / `_2f` automations - Replaced by `notify_short_cycling_furnace`
- 14 `input_number.hvac_*f_recovery_rate_*` rolling window slots
- 4 `input_number.hvac_*f_recovery_transient_*` calculation helpers
- 12 `input_number.hvac_*f_last_*` transient value holders
- 8 `sensor.hvac_*f_recovery_rate_*` statistical sensors
- 4 `binary_sensor.hvac_*f_recovery_*` complex hysteresis sensors
- Recovery rate staleness and alert automations

---

## [2026.01] - January 2026

### Major Robustness Update

Comprehensive audit and hardening of all data pipelines for production-grade reliability.

### Fixed
- **Fail-fast weather proxy** - Returns `unavailable` instead of silent 35°F default
- **Monthly accumulators** - Now immune to recorder 14-day purge
- **Recovery END thresholds** - Increased from 0.5°F to 1.0°F (1F) and 1.25°F (2F)
- **Recovery rate measurement** - Now measures actual thermal recovery, not control-loop gap
- **Setback validation** - Prevents mid-cycle overwrites with explicit latch
- **Entity registry _2 suffix** - All dependencies updated for month sensors

### Added
- **Tier 1 Data Integrity Matrix** - Pipeline health monitoring for HDD, Runtime/HDD, Recovery
- **Climate Norms Feature** - 18-year historical comparison with efficiency deviation index
- **Week/month furnace metrics** - Cycles, overlap, chaining index for extended periods
- **12 watchdog automations** - Staleness detection for all critical pipelines
- **Automation failure tracking** - Counter and dashboard card for error visibility
- **40+ new sensors** - Validation, health monitoring, and extended metrics

### Changed
- Runtime per HDD standardized to furnace runtime (no zone overlap double-counting)
- Recovery START uses hybrid logic (gap > 1 AND furnace running)
- Setback tracking threshold lowered from 2°F to 1°F

## [1.0.0] - January 2025

### Initial Public Release

Production-ready HVAC monitoring configuration with:

- HDD/CDD tracking with 7-day rolling averages
- Statistical Process Control (±2σ bounds)
- Multi-zone runtime analysis
- Filter tracking and alerts
- CSV daily/monthly exports
- Dashboard gallery with 30+ cards

### Documentation
- Comprehensive CLAUDE.md with 600+ entities documented
- Dashboard card library in dashboards/cards/
- Cross-reference to Baseline Analysis repo

---

## Companion Repository

For analysis methodology and baseline data, see:
[Residential-HVAC-Performance-Baseline-](https://github.com/wkcollis1-eng/Residential-HVAC-Performance-Baseline-)
