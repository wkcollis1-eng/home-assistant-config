# eod-timing

End-of-day automation timing. `scripts/ha_audit.py` parses the schedule
table in this file (`_EOD_DOCS`) - keep rows as `HH:MM:SS  name`.

Moved verbatim out of CLAUDE.md on 2026-09-16 so it loads only when
needed. "Above"/"below" in this text may point into CLAUDE.md.

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
write sets and comparing same-second pairs. **FAIL-SAFE as of 2026-08-25 — all
three contention outcomes BLOCK:**

| finding | when | severity |
|---|---|---|
| `eod-race` | both write the same entity | **FAIL** |
| `eod-read-write` | one reads what the other writes | **FAIL** (was WARN) |
| `eod-write-unmodelled` | the write target is a template, so contention **cannot be ruled out** | **FAIL** (was WARN) |
| `eod-time-unresolvable` | `at:` is not a literal, so the automation was not compared at all | WARN |
| `eod-concurrent` | same second, nothing shared | INFO, one line |

The third row is the point of the word fail-safe: when the checker cannot
*prove* two automations do not collide, it blocks rather than staying quiet.
Treating "could not check" as "no finding" is R8, applied to the one rule
protecting the midnight window.

**SCOPE, corrected 2026-08-25: this now examines EVERY time-triggered
automation — 111 of them — not just the ~20 declared in `pipelines.yaml`.**
Until that date an undeclared pair sharing a second and an entity produced
nothing at all, which made it a race check that could not see most races.
Widening it immediately surfaced a group nobody had been checking:
`00:00:00 x2` (`dehumidifier_cycle_counter_reset` +
`reset_automation_failure_counter`). They share no state, so it is fine — but
nothing had established that.

Stagger only to resolve a real contention or an ordering dependency — not for
tidiness. Sharing a second is still not a problem; six captures fire together
at 23:59:00 with no interaction.

`scripts/new_pipeline.py` refuses to scaffold a pipeline onto a second where
its entities would collide, so the common case never reaches the gate at all.

### ORDERING DEPENDENCIES (these are why the staggering exists)

- **23:56:30 `capture_daily_monthly_tracking` is immovable.** Every month
  sensor depends on `monthly_tracking_capture_last_ok`.
- New month accumulators go in `capture_daily_monthly_tracking`, NOT
  `capture_daily_hdd`.
- `archive_monthly_hdd` / `_cdd` read the month accumulators, so they ran
  after 23:56:30 (23:58:15 / 23:58:30). Both retired 2026-09-23.
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
