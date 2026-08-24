# HANDOVER — 2026-08-24

Config is clean: **ha_audit 0 FAIL / 0 WARN**, `check_config` valid, generated
docs current. Only open items below. Full detail for everything closed today is
in `CHANGELOG.md` under `[2026.08.24]`; PENDING items are in `CLAUDE.md`.

---

## 1. NEEDS BILL — furnace, at the first heat call

**Press `input_button.reset_load_peaks` at the first real heat call**, then
re-read the peaks after a week. `sensor.furnace_peak_watts` = 839 W is the AC
air handler; heat-mode draw is UNMEASURED and the furnace is the #1 winter
essential.

Three things to capture in that one window, because they are separable only
while it is happening:

| what | why it matters |
|---|---|
| steady blower watts in HEAT | three sources disagree: baseline repo says 210 W, Kill-A-Watt said 350-400 W, nameplate arithmetic says 470-750 W |
| the IGNITION phase specifically | inducer + hot surface igniter, blower still off, 15-45 s. Likely the true peak, and absent from all summer data |
| igniter wattage | silicon nitride (~40-90 W) vs silicon carbide (~300-400 W) is a 4x swing and is not established |

The ECM blower is NOT the thing to watch: it has no inrush (max/median 1.1x
across 1,176,064 samples, against 21.5x for the fridge on the same instrument).
Detail and the retracted cube-law estimate are in CHANGELOG.md.

**If the winter blower is near 500-700 W, the winter essentials load is
comparable to or higher than summer** — which inverts the assumption behind the
bank sizing. That is the reason this matters beyond tidying a number.

**Bill's decision 2026-08-24: do NOT amend the baseline repo's 210 W now.** Wait
for the measurement. The repo knowingly carries a disputed figure; that is a
decision, not an oversight, and not for a later session to "fix" without him.

## 1b. RESOLVED 2026-08-24 — self-test action is live

HA was restarted and `script.ha_audit_tests` was run from Developer Tools >
Actions. It returned, verbatim:

```
summary: SUITE PASSED - 8 rule(s) proven in both directions
passed: true      covered: 8      total_rule_ids: 32      failures: ''
```

So the whole chain works on-host: shell_command -> python3 -> --json -> the
script's from_json parse -> the Actions response pane. Coverage is now 9 of 33
after the multi-call tripwire was added the same day.

## 2. WAITING ON TIME — one number not yet quotable

`sensor.backup_essentials_avg_24h` shows "filling" until
`age_coverage_ratio >= 0.9` (21.6 h of coverage), so it becomes quotable around
**07:40 on 2026-08-25**. `backup_essentials_mean_24h` is superseded — do not
quote it.

Meanwhile the measured baseline is available and does not depend on that sensor:

```
43 days, 2026-06-30 .. 2026-08-23   (InfluxDB, gap-safe, validated +-1.3 W)
  mean 275.6 W   median 291.3 W   p95 382.8 W   WORST DAY 452.9 W (2026-08-07)
```

Cooling-season only. Method, cross-checks and the excluded 2026-07-01..07-12
logging outage are in CHANGELOG.md.

## 3. OPEN PENDING (unchanged this session)

- **P3 [HIGH]** — dehumidifier SPC tracks basement temp; needs autumn cooling for
  a real regression lever arm before compensating.
- **P9 [HIGH]** — LeakNow `for:` semantics. Confirmed working 2026-08-24 (fired
  22:53, correctly), but an HA restart re-fires it for an ongoing condition.
- **P2 [MEDIUM]** — shoulder-season dehumidifier validation.
- **P8 [LOW]** — `hvac_ac_blower_daily` / `_monthly` were never created.
- **P11 [LOW]** — SCM tamper baselines need weeks of history before alarming.

## 4. DECIDED — do not reopen without new reason

- **Dead R900 phase.** 1 of 5 transmissions never decodes; capture is 71%.
  Sample-rate change was a measured null result. Not worth chasing: electric is
  the only meter where tick timing matters and 74% of ticks already resolve
  individually. Would need IQ capture to identify, not more config guesses.
- **`sensor.water_meter_leak_now` = 1** is the softener regen plus a 15-hour run
  of hourly usage, not a leak. Overnight minimum was 0.00 gal/h. Clears itself.
- **Backup essentials card** is deployed and observed (2026-08-24). A prior
  handover claimed otherwise; it was wrong. CHANGELOG.md.
- **`backup_essentials_avg_24h` restart persistence** is already implemented at
  all three layers. No change needed. CHANGELOG.md.

## 5. KNOWN DRIFT RISK

`scripts/validate_ha.py` is a vendored copy of the `homeassistant-config-validator`
skill (2026-08-23). It will silently diverge from the upstream skill. Its
`PROTECTED_ENTITY_IDS` already holds one dead id, left in place deliberately
rather than widening that divergence — see `docs/ha-validator-checks.md`.

---

**Session protocol reminder:** regenerate as the LAST step. A package edit after
`gen_reference.py` put `PACKAGES.md` stale and failed the 00:30 nightly audit on
2026-08-24.

**Off-host reminder:** `python` not `python3`, and both `HA_CONFIG='H:/'` and
`HA_URL='http://10.0.0.210:8123'` are required — see CLAUDE.md SESSION PROTOCOL.

**Hooks are live (2026-08-24), in `~/.claude/settings.json`:** a `PreToolUse`
guard blocks Write/Edit on the three GENERATED docs and on `.storage/*`; a
`SessionStart` hook runs the audit and injects the verdict; a `Stop` hook
re-runs it after any turn that changed something under `H:` and speaks only on
FAIL/WARN. Scripts in `~/.claude/hooks/`. **Known gap: the guard sees the
Write/Edit TOOLS only — a write done through Bash bypasses it.** The Stop gate
is the backstop there, because it catches the consequence however the edit was
made.
