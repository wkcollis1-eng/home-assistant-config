# influx_sandbox

Runs two InfluxDB 1.x versions side by side on a COPY of the production add-on's
data, on the Windows box. Nothing touches the host except the one backup you
take in step 2.

First used 2026-09-17: 1.12.4 (the `local_influxdb112` fork) against 1.13.1
(the v6.0.0 store add-on's config). Results and limits are in
CHANGELOG 2026.09.17.

All output goes to `C:/sandbox/influx-v6` (`ROOT` in `harness.py`), never to `H:`.

## Run order

1. **Binaries.** Put the official Windows zips in `ROOT/bin/<version>/`. Check
   each sha256 against that version's GitHub release notes. The paths are
   `https://dl.influxdata.com/influxdb/releases/v<ver>/influxdb-<ver>-windows_amd64.zip`.
2. **Source backup (R12: ask Bill first).** `hassio.backup_partial` with
   `addons: [local_influxdb112]`, `homeassistant: false` and **no password**.
   Automatic backups are encrypted, and reading their password is blocked.
3. `python fetch_backup.py <backup_id> <size_bytes>`: downloads the backup
   (GET only), checks its size, and extracts `/data/influxdb` to `ROOT/pristine`.
4. `python harness.py selftest`. It must print `SELFTEST PASSED`: each check
   fires on an injected fault and stays silent on a clean copy (R7).
5. `python harness.py run --pristine C:/sandbox/influx-v6/pristine`
6. `python diag_now.py` if T3 reports differing Grafana queries. 62 of the 170
   use `now()`, and those can never repeat byte for byte. This script pins `now()`.
7. **Clean up.** Delete `pristine/`, `runs/*/copies`, `diag/` and `backup/`.
   They are unencrypted house data.

## Limits

- Windows builds, not the add-on's Debian container on the N100. Timing and
  memory figures do not transfer.
- Only `influxd` runs, never the packaged add-on (s6, nginx, Chronograf,
  Kapacitor).
- Subscriber, continuous queries and retention are disabled on BOTH sides, so
  the copies are never forwarded to the LAN or changed by timers.

For a different version pair, edit `BIN` and `render_conf()` in `harness.py`.
