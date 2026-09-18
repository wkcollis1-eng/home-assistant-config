# off-host-access

How a Windows/Samba session reaches each service, and the off-host
gotchas that each cost a session.

Moved verbatim out of CLAUDE.md on 2026-09-16 so it loads only when
needed. "Above"/"below" in this text may point into CLAUDE.md.

---

### Off-host gotchas (from SESSION PROTOCOL)

Off-host gotchas, each of which has cost a session:
- **`python3` does not exist on the Windows box.** Use `python`.
- **Persistent notifications are NOT entities, and `/api/states` lies about
  them by omission.** They stopped being entities in HA 2023.x; `/api/states`
  simply has no `persistent_notification.*` rows, so "I checked and there were
  none" is not evidence a notification did not fire — it is evidence you looked
  somewhere that cannot hold one. Read them over the websocket:
  `{"type": "persistent_notification/get"}`. Cost two wrong readings in one
  session on 2026-08-31, once as a false "correct, no alert" and once as a false
  "the automation did nothing".
- **Adding a `shell_command:` needs `shell_command.reload`, NOT
  `automation.reload`.** `shell_command` is set up at startup; reloading
  automations leaves a newly declared command unregistered, and the calling
  automation then runs and quietly does nothing. Confirmed 2026-08-31: the
  service was absent from `/api/services` until `shell_command.reload`. Check
  registration there before concluding a script is broken.
  **SUPERSEDED 2026-09-16 (Bill):** adding or changing a `shell_command` needs
  a RESTART, as DEFINITION OF DONE says. Do not rely on the reload claim above.
- **`HA_TOKEN` cannot reach the Supervisor directly, but CAN drive it through
  services.** Every `/api/hassio/*` path returns a flat `401 Unauthorized` to a
  long-lived token — `supervisor/info`, `addons`, `store/addons`, all of them —
  so add-on state cannot be read *through `HA_TOKEN`*. **It CAN be read, over
  SSH — see the next bullet; this said "cannot be read off-host" flatly until
  2026-09-17 (R13).** The `hassio` **services** are wide
  open on the same token: `hassio.addon_start` / `addon_stop` /
  `addon_restart` / `backup_partial` / `restore_partial` / `host_reboot` all
  execute via `POST /api/services/hassio/<service>`. Measured 2026-08-31, when
  the 401 nearly became "you'll have to click this yourself" for a restore that
  was in fact fully drivable. Read add-on state from the `hassio`-platform
  entities in `/api/states` instead (`binary_sensor.<addon>_running`,
  `sensor.<addon>_cpu_percent`, `switch.<addon>`) — and note those entity ids
  are built from the add-on NAME, so a replacement add-on gets different ones
  and dashboards referencing the old names go unresolved.
- **Add-on config and logs ARE readable off-host — but only from a LOGIN
  shell.** `SUPERVISOR_TOKEN` is set by the SSH add-on's profile, not by its
  sshd, so the shell form is the whole trick [M, 2026-09-17]:
  ```bash
  ssh ha-host 'bash -lc "ha apps info 6713e36e_rtlamr2mqtt --raw-json"'   # works
  ssh ha-host  'ha apps info 6713e36e_rtlamr2mqtt --raw-json'             # unauthorized
  ```
  The second returns `Error: unauthorized: missing or invalid API token` and
  looks exactly like a permissions problem that isn't one. `ha addons` still
  works but prints a deprecation notice; `ha apps` is the current name.
  - **Reading is all you get from the CLI.** `ha apps` in this version has no
    `options` subcommand (`changelog info install logs rebuild restart start
    stats stop uninstall update`), so an add-on's config can be read but not
    written from it. Writing means `POST http://supervisor/addons/<slug>/options`
    with `$SUPERVISOR_TOKEN`, from that same login shell.
  - **That POST REPLACES the options dict, it does not merge.** Send the whole
    dict with one field changed - read, modify, write back, then diff the
    read-back. A partial body would silently drop the `meters:` list and take
    the three utility meters with it.
  - **`scp` to `ha-host` fails** - `subsystem request failed on channel 0`, the
    add-on's sshd has no sftp subsystem. Pipe instead:
    `ssh ha-host 'cat > /tmp/f.json' < local.json` [M, 2026-09-17].
  - **The SSH add-on is uid 1000 `hassio` and CANNOT create files in
    `/config`**, which is a root-owned symlink to `/homeassistant`
    (`mkdir: can't create directory '/config/tmp': Permission denied`). Create
    such a directory over the `H:` Samba share instead - that writes as root,
    which is also what add-ons run as, so the result is writable by them
    [M, 2026-09-17: `/config/tmp` created this way, `drwxr-xr-x root root`].
- **Without `HA_CONFIG`** the script looks for `/config` and reports
  `pipelines.yaml not found`.
- **`HA_URL` alone does NOT enable the live check - `HA_TOKEN` does.**
  `_live_states()` only attempts a fetch if `HA_TOKEN` or `SUPERVISOR_TOKEN` is
  set; `HA_URL` is merely the base URL for an attempt that otherwise never
  happens. This file said the opposite until 2026-08-25, and it was true-by-
  accident only because `HA_TOKEN` is a persistent user env var on the Windows
  box. Proven both directions that day: with the token, `0 FAIL, 0 WARN`;
  with `env -u HA_TOKEN`, TWO things degrade - `live-check-skipped` (R8
  coverage gap) **and** the `sun.sun` false positive returns, because the live
  union is what suppresses it. The audit is not "fully offline by design"; it
  is offline-capable and measurably worse offline.
- **Load `secrets.yaml` with `yaml.safe_load` - never grep, `cut`, a
  `split(':')`, or bare `yaml.load`.** Off-host there is no HA environment, so
  credentials come straight from `H:/secrets.yaml` (set `HA_CONFIG='H:/'` - it
  is not a persistent env var, and the snippet falls back to `/config`). Every
  `influxdb_*` value there is quoted, a hand parser keeps the quotes, and the
  failure does not look like a parse bug [M, 2026-09-18, all four `influxdb_*`
  keys, PyYAML 6.0.3, one probe each]:
  - hand-parsed user/pass against the right URL: InfluxDB `/query` returns
    **401** - indistinguishable from a rotated password, and rotating `ha_ro`
    is an open recommendation (Grafana, **Auth**, below), so the wrong
    conclusion is ready-made;
  - hand-parsed URL: `URLError` before any request is sent;
  - `yaml.load(f)` with no `Loader`: `TypeError` on PyYAML 6.

  `safe_load` reads the whole file and the same credentials return 200. The
  snippet is in `docs/influx-grafana.md`, §InfluxDB 1.x, **Credentials**;
  `scripts/grafana_snapshot.py` and `scripts/spc_verify.py` load it the same way.
- **`git` on `H:` WORKS as of 2026-09-10 - both bullets that stood here were
  stale.** They said git "does not just refuse, it hangs" (measured 2026-08-25:
  `git ls-files --error-unmatch` did not return inside 2 minutes, `git diff HEAD`
  was still running after 30), so `check_provenance.py`'s DEFAULT mode "cannot
  complete off-host at all"; and that git refuses `H:` with "dubious ownership".
  Re-measured 2026-09-10 off-host, n=1 each: `status` 1.4 s, `diff HEAD` 0.24 s,
  `ls-files --error-unmatch` 0.10 s, `check_provenance.py` DEFAULT mode 0.34 s.
  Ownership is settled by `safe.directory = *` in the global `~/.gitconfig`.
  What caused the 08-25 hang was never established, so `check_provenance.py`
  keeps its 30 s timeout (line 46) and `--all <files>` stays the git-free
  fallback. Cost of the stale text: a session repeated it and routed a commit
  through `C:\repos` for no reason. **`H:` is the LIVE config and a checkout of
  the same repo: never run a git command that rewrites its working tree
  (checkout, stash, reset --hard, pull over local edits) without asking.** To
  catch up after a push made elsewhere, `git fetch && git reset --mixed
  origin/master` moves HEAD and touches no file.
## OFF-HOST ACCESS — how a Windows/Samba session reaches each service

Quick reference; each service's own section (below, or SESSION PROTOCOL above)
has the full history and gotchas. Everything here was verified 2026-09-11.

| service | reachable directly off-host? | how |
|---|---|---|
| `H:` config tree | yes | Samba mount, `\\10.0.0.210\config` |
| HA REST/WebSocket API | yes | `HA_TOKEN` (persistent Windows user env var) against `10.0.0.210:8123`. Full gotchas (Supervisor 401s, `HA_URL` vs `HA_TOKEN`) in SESSION PROTOCOL above. |
| InfluxDB 1.x | yes | `10.0.0.210:8086`, credentials in `secrets.yaml`, loaded with `yaml.safe_load` only (gotcha above). Full detail and the loading snippet in `docs/influx-grafana.md`, §InfluxDB 1.x, **Credentials**. |
| **Grafana** | **no** | see below |
| git (`H:` as a working tree) | yes | see SESSION PROTOCOL above — works as of 2026-09-10 |
| sandbox / scratch copies | n/a | `C:\sandbox` — fixed local path, see R2 above. Not `H:`, not a temp dir. |

### Grafana has no off-host URL — reach it by SSH'ing on-host instead

`scripts/grafana_snapshot.py`'s default base (`http://a0d7b954-grafana:3000`) is
a Docker-internal hostname; it only resolves on the HA host itself. Verified
2026-09-11: TCP `10.0.0.210:3000` and `:3001` are both closed from the Windows
box (InfluxDB's 8086 and HA's 8123 are open, Grafana's is not) — this is not a
missing env var, there is no host-mapped port to point one at.

**The route that works:** SSH to the host and run the script there, where the
Docker hostname resolves natively and `secrets.yaml` is read as `/config/secrets.yaml`
directly (no `GRAFANA_URL`/`GRAFANA_TOKEN` override needed on-host — those env
vars only matter when the script runs Windows-side; `scripts/grafana_snapshot.py`
reads them at lines 72-73, ahead of `secrets.yaml`).

```bash
ssh ha-host "python3 /config/scripts/grafana_snapshot.py --probe"
# verified 2026-09-11: auth OK, 5 dashboards visible, Grafana 13.2.1
```

- **Credential identity**: `secrets.yaml`'s `grafana_token` belongs to the
  **`ha-grafana-snapshot`** service account (Editor role) — confirmed
  2026-09-11 by using the token, then checking Grafana's per-token "last
  used" timestamp (it matched to the second: `2026-09-11 09:43:08`, right
  after the probe above ran). There is a **second** Editor-role service
  account, `snapshot-bot`, that this token does NOT belong to — its purpose
  is unknown as of 2026-09-11: not referenced by `grafana_token`, not found
  elsewhere in this repo. Either an intended spare/rotation credential or
  cruft; find out before relying on it, and see PENDING.
- **Host/user**: `hassio@10.0.0.210`. This is the **"Advanced SSH & Web
  Terminal"** add-on (container hostname `a0d7b954-ssh`, uid 1000 `hassio`,
  groups `wheel`+`hassio`) — port 22. A second add-on, "Terminal & SSH", is
  also installed but is NOT the one bound to port 22 (its usual default,
  22222, is closed) — don't confuse the two if either gets reconfigured.
- **Auth**: key-only from this box. `~/.ssh/id_ed25519` (comment
  `claude-code@wkcol-win`) is already in the add-on's `authorized_keys`
  config. A password is also configured on the add-on itself — **it is
  IDENTICAL to the InfluxDB `ha_ro` password in `secrets.yaml`**, same secret
  reused across two unrelated surfaces. Flagged 2026-09-11, not yet rotated;
  rotate one so a leak of either credential doesn't hand over both.
- **Client-side alias**: `C:\Users\wkcol\.ssh\config` (Windows-side, NOT part
  of this git repo, so it will not exist on a fresh clone/machine — recreate
  it there if this ever moves):
  ```
  Host ha-host
      HostName 10.0.0.210
      User hassio
      IdentityFile ~/.ssh/id_ed25519
      IdentitiesOnly yes
  ```
- **General pattern, not just Grafana**: anything that only resolves on the
  HA host's own Docker network (other add-on-internal hostnames, `docker
  exec` into a container, etc.) is reachable the same way — `ssh ha-host
  <command>` — rather than assuming it needs an off-host URL that may not
  exist.

---
