# pending

Open items. Anything RESOLVED is closed and lives in CHANGELOG.md.

Moved verbatim out of CLAUDE.md on 2026-09-16 so it loads only when
needed. "Above"/"below" in this text may point into CLAUDE.md.

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

UPDATE 2026-09-23 - re-run on a wider lever arm (4.0 degF, not yet ~5):
  daily means 2026-08-08..09-22 (n=46), basement 67.84 .. 71.85 degF:
    slope +5.20 +/- 0.35 W/degF, t = 14.7, r2 = 0.831
    raw daily sd 5.26 W -> residual sd 2.18 W after T-normalisation
  per run (n=340), inlet 67.5 .. 72.0 degF: +5.14 +/- 0.25 W/degF, t = 20.8
  [M: steady window = minutes 10-14 of each run; inlet = basement SHT45
   temperature at run start; run = plug power > 150 W]
  Same method on the original 08-08..21 window: +6.55 +/- 1.04 (n=14),
  consistent with the 7.64 +/- 0.64 above (z = 0.89 [D]). The narrow-span
  slope was imprecise, not wrong; the wider span brings it down.
  CAVEAT: runs start at a fixed RH, so inlet temperature and humidity move
  together (r = 1.00 per run). This is the combined inlet effect; the two
  cannot be separated from these data. That does not matter for
  compensating the chart; it does for explaining the machine.
  THE CONCLUSION STANDS: at 5.20 W/degF the 8.5 degF seasonal move above is
  44 W [D: 5.20 x 8.5] against a 2.18 W residual sd.
  STILL NOT EARNED: the 61.3 degF low of the n=3230 series above is 6.5 degF
  below the fitted minimum [D: 67.84 - 61.3]. Re-fit when the basement
  reaches ~63 degF; no compensation is built yet.
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

### P14 — `snapshot-bot` Grafana service account is unaccounted for [LOW]
```
Two Editor-role Grafana service accounts exist: ha-grafana-snapshot and
snapshot-bot. secrets.yaml's grafana_token is confirmed (2026-09-11, via
last-used-timestamp correlation) to belong to ha-grafana-snapshot.
snapshot-bot's token is not referenced anywhere in this repo or in any
documented env var. Either an intended spare/rotation credential nobody
wrote down, or leftover from something retired. Find out which before
trusting it for anything; if leftover, delete the service account rather
than leave a live Editor-role token with no known owner or purpose.
```

### P16 — press "Reset peaks" at the first real heat call (multiple reasons stacked now) [MEDIUM]
```
Pre-existing reason: sensor.furnace_peak_watts is a COOLING-mode number until
the furnace's first heat call this winter (heat mode adds the inducer motor
and igniter, unmeasured). See backup_sizing.yaml and the card header.

Added 2026-09-11: sensor.backup_essentials_peak_watts (the actual SIZING
number) is latched at 3395 W, occurred 2026-08-24T06:43:08 - from BEFORE the
coffee-maker-to-Family-Room swap, i.e. it includes a load no longer on the
bank. It will not self-correct on its own (a new peak would have to exceed
3395, unlikely soon) and will not be reset early: input_button.reset_load_
peaks clears ALL peaks at once (fridge, furnace, HWH, monitoring), and Bill
chose to wait rather than lose the furnace's cooling-mode baseline before a
heat-mode reading exists. Until the reset, 3395 W looking stale on the card
is EXPECTED, not a bug - do not "helpfully" reset early.
```

---

### P17 — SDR per-packet signal level: implement and gate it [MEDIUM]
```
NEXT SESSION ITEM, at Bill's request 2026-09-17. The full procedure is written
up in docs/sdr-signal-level.md - read that, not this summary.

WHAT: rtlamr reports no signal level at all, so antenna and POSITION questions
currently have no instrument (capture rate is the wrong one, and it saturates).
The route: rtlamr's own -samplefile dump, which it writes only around packets
it decoded, read offline by rtl_433 -M level on Windows off the H: share. The
pipeline keeps running - no need to stop rtlamr2mqtt.

STATE: nothing deployed, nothing run. Verified only at the source level (R6).

FIRST ACTION is the gate in that doc's section 6, not the survey. The whole
route rests on [I1] "rtl_433 decodes SCM/R900 from spliced 2.62 MS/s cu8
windows", which is UNTESTED. If it produces zero decodes, the route is dead and
the fallback needs Bill's authorisation (it takes the meter alarms blind).

NEEDS BILL (R12): one add-on config change plus a restart - see that doc's
section 3, including why fixed gain takes BOTH rtltcp -g 40 and rtlamr
-tunergain=40 (the first sets it, the second stops rtlamr handing the tuner
back to AGC on connect; -g 40 on its own is inert), and why -s 2621440 must be
kept. The doc's gain bullet asserted the opposite until 2026-09-17 - corrected
in place with the source citations, R13.

DO NOT move the antenna while the 09-18..09-24 ledger row is live; the survey
in section 8 voids it.
```

---

### P18 — SDR reading guard + add-on config drift check: build it [HIGH]
```
NEXT SESSION ITEM, at Bill's request 2026-09-18. The full design is in
CHANGELOG.md [2026.09.18], "NEXT SESSION: SDR reading guard" - read that, not
this summary.

WHY: 9/13 water zeros were a valid-but-wrong add-on protocol (Bill's typo), and
nothing downstream questioned a 0. Two glitches had to be hand-repaired out of
statistics, utility meters, InfluxDB, the CSV and recorder states.

WHAT: Layer A - the three *_meter_* template sensors become trigger-based and
reject/hold implausible readings (limits from measured max rates), with a
10-min alarm and a reanchor script. Layer B - export the rtlamr2mqtt options to
a tracked file, and an ha_audit rule sdr-config-drift.

STATE: design only, replay-tested offline. Nothing deployed.

FIRST ACTION: ask Bill the two open decisions in that entry (hold-vs-unavailable,
drift-rule workflow). Build nothing that depends on them until answered.
```

### P19 — `*_last_year` bill helpers: a second copy, with a guard that misfires [LOW]
```
Found 2026-09-22 building the Cost Overview (CHANGELOG [2026.09.22]).

1. R10. input_number.{electricity,gas}_bill_{amount,kwh|ccf}_last_year now hold
   the same value as the new *_archive_ly_<latest statement month>_* slot. Six
   sensors in configuration.yaml read them (effective_rate_last_year x2,
   usage_change_yoy x2, bill_change_yoy x2; the rate_change_yoy pair reads the
   first two), and the live Billing view shows four.
2. Their Save Bill guard compares ONE field (`archive_val != current_*`). When
   this year's integer kWh or CCF equals last year's for that month, that helper
   silently keeps the PREVIOUS month's last-year value. The new _ly_ roll is
   gated on the year stamp and is not affected.

FIX (not built): point the six sensors at the _ly_ slot for the latest statement
month, then retire the four helpers and their eight save-automation steps.
Touches the existing Billing view's YoY cards, so it needs its own session.
```

### P21 — battery-bank SOC reads high: build V1.28 (SOC from the INA228 CHARGE register) [MEDIUM]
```
Opened 2026-09-24. Everything is in docs/soc-accuracy-turnover.md - read it
before touching battery-bank-monitor.yaml or the router. SOC shows 99.96 %,
true ~96.7 % +/-1.1 % [D, doc s2]. The SW ledger's +/-50 mA deadband drops the
7.3-8.2 mA drain [M]. V1.28 design, gates, and the tests awaiting Bill's go
are in the doc. The router stopgap (20/40 MHz coexistence OFF) makes the
trace quiet AND freezes the SOC display (doc s2).
2026-09-25: V1.28 BUILT, reviewed (3 fixes), real-compiled, merged (Lifepo4
main 9737b61) and copied to esphome/ (blob b5e6f3e). NOT FLASHED: Bill flashes
via Device Builder > Install. Close P21 when the at-flash ledger rows
(CHANGELOG, 2026-09-25) are scored.
2026-09-25 19:38 EDT: FLASHED (config hash 0xb8426c87 = the validated build);
both at-flash ledger rows HIT. STAYS OPEN - the close condition above was
premature (mine, R13): SOC still reads high on the provisional anchor until
the first full recharge. Close when the 3-day idle row (window ends 09-28)
and the first-full-recharge row are scored.
```

### P23 — `ha_audit.py` entity-ref rule is blind to bare list items and flow lists [MEDIUM]
```
Opened 2026-09-26. rule entity-ref-unresolved reads only states('x')-style
calls and single-id `entity(_id):` lines. An id in a bare list (a trigger's
entity_id list, a history-graph entities list) or in [a, b] is never checked.
Proven by R2: a family id injected into the office package's trigger list
passed the audit at 0 FAIL, 0 WARN. Stopgap gate used for the mmwave deploy:
C:/Users/wkcol/ha-data-repairs/refs_check.py (live states + services + the
package's own declarations). Fix: widen the rule, add both shapes to
test_ha_audit.py (fires on the injected id, silent on the clean tree), then
retire refs_check.py rather than keep two checkers (R10). CHANGELOG
[2026.09.26].
```

### P24 — office mmWave bathroom filter live 2026-09-27: scored HIT, open for tuning [LOW]
```
Opened 2026-09-26. Presence lamp control went live ahead of repo item 11
(design doc, "office max gates: measure at the mount"). On the bench, a
person in the bathroom next door read 7.4-10.3 ft, gates 3-4, and fired the
lamp three times [M, design doc line 1214]. Expected symptom until fixed:
the lamp comes on in an empty dark office while the bathroom is in use, and
goes off after the idle timeout. Needs Bill at the mount: measure, set the
gates in esphome/, real-compile, flash via Device Builder. Close when a
bathroom occupancy with the office empty produces no presence edge.
CHANGELOG [2026.09.26].

First at-mount measurement, 2026-09-26 (Bill: "around 9:10 was in the
bathroom"; office empty, label "no one present"). The lamp came on at
21:10:06 EDT. From 21:09:50 the still target read 104.7-121.7 in [M: HA
history, sensor.office_mmwave_still_distance, n=10 changes] = gates 3-4
[D: 29.5 in per gate], inside the bench's 7.4-10.3 ft: the bench result
holds at the mount (n=1). Risk for the fix: his walk-in was first seen as a
moving target at 116.5 in at 21:10:47, also gate 3, so the doorway may share
gates 3-4 with the bathroom and a max-gates cut could see entries late [I:
falsified if the doorway reads under 88.6 in at the mount]. Where the door
sits is part of the mount measurement this item waits for.

At-mount bathroom run, 2026-09-27 (Bill: office empty, label "no one present"
13:13:47-13:26:34Z, repeated trips in and out of the bathroom): 8 presence
edges in 12.8 min, lamp lit once at 13:24:00Z [M: HA history]. Every edge
opened on a moving target at 89.4-118.1 in (gate 3), energy 21-46; the still
target reached 132 in (gate 4), energy up to 99. Nearest reading of the whole
run 89.4 in [M, full-rate target series]. Per-gate peaks, ~1 frame per 5 s
[M]: g2 move 11 / still 17 against 40 / 40, g3 still 47 against 40, g4 still
100. The [I] above is CONFIRMED: 10 of 10 labelled walk-ins 09-26/27 first
read 115-117 in at energy 26-49 [M], so the doorway is gate 3 and no
first-frame or energy rule separates entry from bathroom. Approach does:
every walk-in reached <= 88.6 in with energy > 40 within 1.4-5.0 s [M, n=10];
the bathroom never did.
Candidate fix (DROPPED 2026-09-27, see below): max_move_gate 2 AND max_still_gate 2. Replay of the sampled
per-gate energies, 09-26 14:31Z - 09-27 13:32Z (it matches actual presence
in 81,824 of 82,860 s [M]): 0 dropouts in 15,372 s labelled occupied at every
cap down to move 1 / still 2; empty-room edges 31 actual -> 3 at cap 2, and
all 3 are real walk-ins labelled late (18:51:49Z, 22:53:33Z, 01:10:49Z).
Still must be capped too: still 3 kept one bathroom edge. Cost: lamp-on
+1.4-5.0 s [M, n=10], and nothing detected past 88.6 in (7.4 ft).
Limits: the replay sees ~1 frame in 5 and found 11 of the 31 actual empty
edges at today's 4/4, so its bathroom silence is weak evidence; that the
module reports the NEAREST over-threshold gate is [I]. Falsifier for both: a
live 2/2 write, then the same bathroom run - any presence edge kills it.
A max-gate write RESTARTS the radar [S: esphome 2026.9.0 ld2410.cpp:697-726];
the reconciler re-opens engineering mode under the calibration hold (common
file 1032-1034). The YAML change blocks on open_questions.yaml 2026-09-27
(anywhere still past 7.4 ft?).

Second run, 2026-09-27, and the cap dropped. Bill set both max gates to 2 at
~13:42Z and repeated the run (label "no one present" 13:43:17Z, office empty
from the presence-off at 13:43:47Z to 13:47:51Z): 5 presence edges in 4.1 min,
every one gate 3, 92-118 in, energy <= 43 [M: HA history]. It was NOT a cap
test. The writes were Developer Tools > States "set state": the logbook
entries carry a user id but no context_service, the states read "2" where a
real set_value reads as a float ("70.0", G0 on 09-26), and no engineering-mode
restart followed [M]. That
path changes HA's record only; the radar stayed 4/4, and HA still showed 2/2
afterwards. R13: my instruction said "Set ... from 4 to 2" without naming the
path (dashboard, or Actions > number.set_value), so the ambiguity was mine.
Bill's answer to the open question (2026-09-27): "the door way" - he stays put
there, 115-117 in, gate 3 [M: first reading of 11 of 11 walk-ins]. A 2/2 cap
would read him empty in the doorway, so the cap is dropped.
Proposed instead, NOT built: presence may only START when a target is inside
70 in; once started, any detection holds it. Across both runs the bathroom
never came nearer than 89.4 in [M: 112 target readings, 13 edges, both target
kinds, full-rate distance series], a 19.4 in margin [D: 89.4 - 70]. Every
walk-in reached <= 70 in within 1.7-4.5 s, median 2.9 [M, n=11]; that is the
lamp-on delay the rule would add. Other thresholds tried: <= 88.6 in, 11/11
walk-ins, median 2.1 s, but only 0.8 in of margin [D]; <= 60 in, 10/11 [M].
Failure modes: (1) someone who only ever stands in the doorway never starts
presence; (2) a bathroom trip straight after leaving the office holds
presence and the lamp on, because holding cannot tell doorway from bathroom.
Limits: 2 runs, one morning, one person; other bathroom activity (a shower,
a longer stay) is unmeasured. Falsifier: any bathroom target reported
<= 70 in. Layer (HA package
vs firmware) awaits Bill.

BUILT, 2026-09-27 (Bill: "yes to both" - build it as an HA change, and set
the max gates back to 4 with a real write). Title changed from "max gates
still 4/4 while the lamp is live": 4/4 is now deliberate.
Max gates: a real number.set_value 4 restarted the radar but HA kept the
States-tab '2'; homeassistant.update_entity fixed both, '4.0' from 14:03:04Z
[M]. The ESPHome integration drops a device report equal to its cache [S:
HA 2026.9.3 esphome/entry_data.py:459-470].
Filter: binary_sensor.mmw_office_occupied in packages/mmwave_presence.yaml,
live 14:31Z. The lamp-on trigger and its post-wait re-check follow it;
sensor.mmw_office_state reads DETECTED_FAR for presence with no approach.
Replay of the deployed template text [M]: bathroom 0 occupied edges from 13
raw edges; walk-ins 11/11, 1.7-4.3 s, median 2.4. This supersedes the
1.7-4.5 s / median 2.9 above, which was read from whole-second times. From
09-26 11:41Z to 09-27 13:31Z: raw on-edges 48 -> occupied 17, "no one
present" 36 -> 3 (all late-labelled walk-ins), 1 s lost while seated/moving.
The gate and the details are in CHANGELOG [2026.09.27].
CLOSE WHEN: a live bathroom run with the office empty and labelled shows
DETECTED_FAR and no occupied on-edge, AND a straight walk-in reaches occupied
within 5 s of the presence edge. Both are pre-registered in the CHANGELOG
ledger (2026-09-27). Score from the history of binary_sensor.office_mmwave_
presence, binary_sensor.mmw_office_occupied, sensor.mmw_office_state and
input_select.mmw_office_label, all recorded.
RECORDER CAVEAT: the package excludes the moving/still distance series
(added 2026-09-22). That is not yet in force and starts at the next HA
restart. The filter reads live state, so it keeps working, but the falsifier
above ("any bathroom target <= 70 in") can then no longer be checked from
history. Keeping the two series costs 33,144 rows/day [M: 24 h to 14:40Z,
two test runs included]. That is Bill's decision.
SCORED, 2026-09-27 - HIT, both halves, first run (n=1). With the office
labelled "no one present" (14:42:46-14:46:48Z): 4 presence on-edges, each
DETECTED_FAR, 0 occupied on-edges [M]. Nearest bathroom target 89.0 in
(still, n=14 flag-on readings), margin 19.0 in [D: 89.0 - 70]. Walk-in:
presence -> occupied in 2.4 s, crossing at 65.7 in [M]. The lamp stayed off,
but the room was lit (EMPTY_LIT), so the lamp half did not discriminate.
CLOSE WHEN is met. Kept open for the tuning Bill named ("we need the 2
distance readings for tuning"), at LOW, since the lamp fault is fixed.
RECORDER CAVEAT RESOLVED, same day: Bill kept the two distance series. They
are out of the exclude list (source + derived package, CHANGELOG
[2026.09.27]), so history continues across the next restart. Re-exclude
them when the tuning is done.
PRODUCTION RECORD, 2026-09-28. The only "no one present" occupied on-edge
since 14:31Z 09-27 (00:25:40Z 09-28) was Bill: "yes i entered and forgot to
hit the button" (open_questions.yaml, 2026-09-28). So the filter has 0 false
starts in 12.91 h labelled empty [M: HA history to 09-28 12:20Z].
GO-LIVE DECISIONS, Bill, 2026-09-28 - authoritative, do not re-open:
- Idle timeout: input_number.mmw_office_idle_timeout = 10 "works well for
  me". The off automation waits max(10 - 30, 0) = 0 s past the radar's own
  30 s hold [D: package `for:` template, live values read 09-28], so the lamp
  goes off ~30 s after the last detection. Any value 1-30 behaves the same;
  only above 30 adds time; 0 means never off.
- Lux: input_number.mmw_office_lux_on = 30 "works well for the room". It
  stays a dashboard helper so he can adjust it.
- Heat-on test (collection B, design doc A6) WAIVED: "no curtains in the
  room, no plants that could move with the breeze". Blower-on behaviour is
  therefore unmeasured [M: every mmw_office_cal_class sample since deploy
  is blower_off]; the first heating-season week is a first observation, not
  a gate.
INSTALLED + SEEDS, 2026-09-28 (Bill: "flashed ... change the seeds to
30/10"). Firmware 0.4 is on the node and P25 is closed (CHANGELOG
[2026.09.28]). The seed automation now writes 30 lx / 10 s into a helper
that reads 0, not 18 / 120 [M: loaded config read back after the reload].
A10 (power cycle, sitting still), n = 1, at the 0.4 Install [M: HA
history]: presence on at 12:52:48.5Z, 3 s after boot; off at 50.3 with
the radar's OUT pin following at 50.4, so the module itself dropped the
target. Lamp off at 50.7 (idle 10 waits 0 s past presence-off [D]), back
on at 12:53:17.5 when Bill moved: off for 26.8 s [D]. Not the boot push,
whose earliest time is ~12:52:53.4 [D: first frame + 5 s on a 5 s
interval]. The cause is not established [I]; a node log attached across a
boot would decide it. A10's "recovers unaided" is not shown for someone
who stays still: not passed, not failed. Cost at idle 10: one lamp-off per
node boot while someone sits still. The node ran from 09-26 14:20:22Z to
this Install with no boot [M].
Still open here: the tuning Bill named, then the recorder re-exclusion.
With the re-exclusion, also remove the "Target distance (P24 tuning)"
card from the office view (repo source first, then the H: copy per its
note); after the re-exclusion it draws nothing. Added 2026-09-28.
```

---

### Closed — full detail is in CHANGELOG.md, not here

```
P1    `default: []` on every choose:                             RESOLVED
P4    phantom entity references                                  RESOLVED
P5    fabricated limit constants                                 RESOLVED
P6    statistics sampling_size                                   RESOLVED
P7    R900 leak sensors                                          RESOLVED
P8    hvac_ac_blower_* chain retired — it existed, was not
      "never created"; deliberately removed, see CHANGELOG      RESOLVED
P10   rtlamr2mqtt duty cycle                                     DEPLOYED
P12   InfluxDB CQs retired, Grafana SPC re-sourced               RESOLVED
P13   statistics-buffer check                                    RESOLVED
P15   backup essentials: coffee maker -> SEM Family Room,
      reload + card paste both confirmed live, see CHANGELOG      DEPLOYED
P20   gas heating season store: rollover catch-up, archive
      stamp, Jan-Jun 2025 fill, previous-month DHW pairing
      (Bill, 2026-09-23); CHANGELOG [2026.09.23]                DEPLOYED
P22   battery-bank diag2 test run: 7 tests run, V1.27
      reinstalled, H: diag copy deleted; CHANGELOG [2026.09.25] RESOLVED
P25   office mmWave G0 move 70 made durable: firmware 0.4
      installed, sw 0.4, G0 70.0 at boot; CHANGELOG [2026.09.28] DEPLOYED
```
