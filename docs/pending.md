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
```
