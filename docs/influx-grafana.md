# influx-grafana

InfluxDB 1.x and Grafana: schema, continuous queries, dashboards,
provisioning and query notes.

Moved verbatim out of CLAUDE.md on 2026-09-16 so it loads only when
needed. "Above"/"below" in this text may point into CLAUDE.md.

---

## INFLUXDB / GRAFANA

### InfluxDB 1.x
- **CUTOVER TO 1.12.4 COMPLETED 2026-09-10 — production is now the fork,
  1.8.10 is retired but still installed.** `local_influxdb112` (InfluxDB
  1.12.4) serves the house on `10.0.0.210:8086`, `boot: auto`.
  `a0d7b954_influxdb` (1.8.10) is STOPPED, `boot: manual`, kept installed as
  the rollback. This CLAUDE.md section said "NOT DEPLOYED; tested on Windows
  builds, not on the N100" until today — that was true on 2026-09-08 when it
  was written and became false on 2026-09-10; nobody carried the correction
  from CHANGELOG.md (2026.09.09/2026.09.10 entries have the full cutover
  narrative) back into this "current state" section. Re-verified 2026-09-12:
  `:8086 /ping` → `X-Influxdb-Version: 1.12.4`; `sensor.influxdb_cpu_percent`
  (the 1.8.10 add-on) = `unavailable`; `sensor.influxdb_1_12_local_fork_*`
  active. **Lesson for future sessions: a narrative entry in CHANGELOG.md does
  NOT update this file's own "current state" prose — that has to be done as
  its own edit, the same day, or this file drifts exactly like this.**
- **THE OLD ADD-ON IS ARCHIVED AND IS NOT IN ANY STORE. A BACKUP IS THE ONLY
  WAY BACK TO IT.** `a0d7b954_influxdb` (5.0.2) was deprecated and removed
  from the Community Add-ons store on **2026-08-28**. Searching the store for
  "InfluxDB" now returns `47c55538_influxdbv2`, a DIFFERENT third-party add-on
  shipping InfluxDB 2.x: buckets/orgs/tokens and Flux, no `"Home Assistant"`
  database, and no InfluxQL for the 136 dashboard refs to `bfrwayjkhasjka`.
  Installing it looks like success and restores nothing. This exact
  substitution cost the 2026-08-31 session (see CHANGELOG). This risk is now
  largely moot for day-to-day operation since the fork is production, but it
  still governs the ROLLBACK path: `a0d7b954_influxdb` is stopped, not
  uninstalled, precisely so "start it again" stays available without needing
  the store. If it is ever uninstalled or lost: `hassio.restore_partial` with
  `homeassistant: false` and `addons: [a0d7b954_influxdb]`, and **stop
  `local_influxdb112` first** or the restore comes up dead (both want 8086).
- **CORRECTED 2026-09-08: InfluxDB 1.x IS NOT END-OF-LIFE. This section said it
  was, and the claim was load-bearing and false.** The add-on's own README says
  the maintainers stopped because InfluxData EOL'd 1.x - authoritative for why
  THEY stopped, not for whether 1.x is EOL. The two were conflated here (R16).
  Measured 2026-09-08 from primary sources:

      influxdata/influxdb releases   v1.12.4 2026-04-13 ; v1.12.3 2026-03-12
      endoflife.date                 latest 1.x = 1.13.0 ; EOL date: NONE
      Docker Official Images         influxdb:1.12 rebuilt 2026-08-25
      what ran here on 2026-09-08    1.8.10, released 2021-10-11
                                      (superseded 2026-09-10 - see the cutover
                                      bullet at the top of this section; what
                                      runs here NOW is 1.12.4)

  **The abandoned thing is the ADD-ON, not the database.** The OSS line went
  1.8.10 (2021) then 1.11.7, 1.12.x, 1.13.0 - 1.9/1.10/1.11.0-.6 were never
  public OSS, which is the whole five-year gap. The false claim drove the
  2026-08-31 session to the v2 add-on that restored nothing, and on 2026-09-08
  nearly drove a 171-query rewrite onto VictoriaMetrics.

  **Side-by-side sandbox on a copy of the real DB (CHANGELOG 2026.09.08):**
  1.12.4 opens 1.8.10 data with no migration, identical query results,
  IDENTICAL TSM bytes, +12% write throughput, working `ha_ro` auth, and
  WORKING ROLLBACK after an unclean kill. Cost: 15-22% slower on a mixed
  dashboard load, confined to `GROUP BY "entity_id"` with no `GROUP BY time()`
  bucket - 4 of 170 live Grafana queries, ~+18 ms each. This was the Windows
  sandbox result only; the cutover onto the real N100 is the bullet above.

- **Restoring the add-on does NOT restore the HA integration.** The config
  entry lives in `.storage/core.config_entries`, which a partial add-on
  restore does not touch, and there is no `influxdb:` YAML anywhere to fall
  back on (verified 2026-08-31: absent from configuration.yaml, packages/,
  and the whole git history). Re-add it by hand: Settings → Devices &
  Services → InfluxDB → `configure_v1`.
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
  **Re-measured 2026-09-12** (prompted by "the db seems small" after the
  cutover): 1,540 series (exact cardinality, up 13%), 713 measurements,
  1,551,509 points/24h summed over just the 66 unit-like numeric measurements'
  `value` field (narrower scope than the August figure and still higher),
  70,340,603 all-time in that same scope. History still starts 2026-06-01 for
  `W`/`%`, 2026-06-27 for `kWh`, latest point live as of the measurement.
  Nothing shrank; growth is consistent with rising entity count. `ha_ro` lacks
  admin privilege, so `SHOW STATS`/`SHOW DIAGNOSTICS`/`SHOW SHARDS` are not
  available for a disk-level breakdown this way.
- **InfluxDB "Home Assistant" db is 2.1 GB; the recorder's
  `home-assistant_v2.db` is 4.4 GB** [M, both 2026-09-12] — smaller despite
  InfluxDB's infinite retention against the recorder's 14-day
  `purge_keep_days` (`configuration.yaml:119`). The instinct that InfluxDB
  should therefore be as big or bigger is reasonable and wrong, for two
  measured reasons:
  1. **`purge_keep_days` does not bound the recorder's own long-term store.**
     Confirmed both ends [M, on-host `sqlite3`, 2026-09-12]: `states` and
     `statistics_short_term` each span exactly ~14.28 days (2026-08-29 to
     2026-09-12 — the setting is working, not a stale claim), while
     `statistics` (hourly aggregates, kept FOREVER regardless of the 14-day
     setting) holds 1,329,663 rows across 537 tracked entities back to
     **2025-12-27** — about three months before InfluxDB's own earliest point
     (2026-06-01). Both retention behaviours are doing exactly what they are
     designed to do.
  2. **Per-row storage shape, not corruption, is the rest of the gap** —
     exact byte breakdown via `sqlite3`'s `dbstat`, run ON the host (the
     bundled Windows Python lacks `dbstat`; the host's does not) [M,
     2026-09-12]:
     ```
     states                              1,621.0 MB   (21,616,862 rows)
     states' 5 indexes combined           1,954.8 MB   <- bigger than the table
       ix_states_context_id_bin             553.9 MB
       ix_states_metadata_id_last_updated_ts 447.0 MB
       ix_states_last_updated_ts            383.3 MB
       ix_states_old_state_id                294.7 MB
       ix_states_attributes_id               275.9 MB
     state_attributes (dedup JSON blobs)    403.9 MB   (1,710,146 rows)
     statistics_short_term + its indexes     ~161 MB   (2,038,027 rows)
     statistics (long-term) + its indexes    ~101 MB   (1,329,663 rows)
     events/event_data/misc                    ~5 MB
     ------------------------------------------------
     accounted                             ~4,246 MB  (file is 4,470 MB;
                                             remainder = free pages, WAL, small
                                             tables not itemised above)
     ```
     Two things worth naming: (a) `states`' own secondary indexes cost MORE
     than the row data they index — SQLite pays a full B-tree per index,
     InfluxDB's TSM format does not; (b) `states` writes 21.6M rows in 14.28
     days = ~1.51M rows/day, which lines up with InfluxDB's independently
     measured ~1.55M numeric points/day above — two unrelated pipelines
     converging on the same house-wide write rate, which is itself a
     corroboration that neither is dropping or duplicating data.
  **Both databases verified structurally healthy, 2026-09-12.** The first
  pass at this (same day) raised a false alarm: a Samba-side plain-file copy
  of the live, actively-written `home-assistant_v2.db` returned `database disk
  image is malformed` on `states`/`statistics_short_term` full scans. Cause,
  confirmed on-host: the copy grabbed only the main `.db` file and missed the
  live `-wal` (8.2 MB) / `-shm` sidecar files sitting next to it — a plain
  file copy of a WAL-mode database is not a consistent snapshot. Run directly
  on the host against the real file, `PRAGMA quick_check` and the full
  `PRAGMA integrity_check` both returned **`ok`** (34 s and 114 s
  respectively). Lesson: never diagnose a live WAL-mode SQLite file from a
  Samba-side copy; either read it on-host or use `sqlite3 .backup`
  (lock-aware) run on-host, never a raw `cp` over the network share. Full
  narrative: CHANGELOG.md 2026.09.12.
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

  **`ha_ro` IS NO LONGER READ-ONLY. Changed 2026-08-31 — this bullet said
  `GRANT READ` until then.** The `influxdb` config flow validates the
  credential with a **write probe**, so a READ-only user fails the flow with a
  bare `cannot_connect` that names nothing. Proven both directions that day:
  as READ, `/write` returned 403 and the flow refused; after
  `GRANT ALL ON "Home Assistant" TO "ha_ro"` the flow created the entry
  first try. Use `GRANT ALL`, never `GRANT WRITE` — in InfluxDB 1.x a user
  holds ONE privilege per database, so `GRANT WRITE` silently REVOKES read
  and breaks `spc_seed.py`.

  What that costs, stated honestly: a leaked `ha_ro` can now insert and
  overwrite points, and retention is infinite with no backup of the raw
  series. What still holds: it **cannot DROP a measurement** — that needs
  admin, measured 403 on 2026-08-31 with ALL PRIVILEGES held. Non-admin write
  is the floor HA's own integration imposes; it is not a preference.
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
**THESE FILES ARE NOT DEPLOYED AND NEVER HAVE BEEN. Editing one changes
nothing.** This block said "Provisioned dashboards - survive Grafana rebuilds"
until 2026-09-03; it was false. Measured that day: all five dashboards report
`meta.provisioned = false`, i.e. file-based provisioning loads ZERO dashboards.
Grafana serves only its own database copies, and the drift had reached a month:

```
battery-bank   Grafana 2026-07-21   file 08-21    file newer
energy         Grafana 2026-07-25   file 08-21    file newer
hvac-status    Grafana 2026-07-28   file 08-21    file newer
ups-status     Grafana 2026-08-31   file 08-21    GRAFANA newer - deploying the file REGRESSES it
```

The drift runs BOTH ways, so "just deploy them all" destroys work. Check
direction per dashboard before touching any.

What this cost: the P12 SPC re-sourcing was written to `spc_appliances.json` on
08-22 and never landed, so the Daily series kept querying the retired `spc`
measurement - dead since 08-21 - for thirteen days while UCL/LCL from `W` stayed
current. The chart looked alive and was not. Nothing in this repo compares what
Grafana serves against what the file says, and `ha_audit.py` cannot: Grafana is
not YAML.

**To actually deploy a dashboard:**
`python3 /config/scripts/grafana_snapshot.py --deploy /config/grafana/dashboards/<f>.json`
(overwrites by uid, pins `${DS_INFLUXDB}` placeholders to the real datasource
uid, and prints the version it replaced). `--provstatus` prints the provisioned
flag and served date for every dashboard - run it before believing a file is live.
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
