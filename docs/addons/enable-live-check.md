# Enabling the statistics-buffer check in the nightly audit

## Why it is failing

`ha_audit.py` tries the Supervisor proxy first:

    http://supervisor/core/api/states   with SUPERVISOR_TOKEN   ->  401 Unauthorized

That proxy path exists for **add-ons** talking to Home Assistant. A
`shell_command` runs inside HA Core itself, and HA Core's own SUPERVISOR_TOKEN
is not accepted as an HA API credential by that route. There is no add-on
config to fix — the route is simply the wrong one for this caller.

The fix is to give the audit a normal Home Assistant token and point it at
localhost, which is the path the code already supports.

## What this buys

The `statistics-buffer-truncating` rule. It is the one that found

    sensor.fridge_running_watts_24h   buffer 1.00 full, age coverage 0.11

i.e. a "24 h" mean that was really covering 2.6 h, with a window length that
moved with compressor duty. That rule has **never executed in the nightly run** —
it only ever ran when invoked by hand with a token in the environment. Until this
is done, its findings are absent rather than clean, which is exactly what the
WARN now says.

## Steps

1. Home Assistant → your profile → **Security** → *Long-lived access tokens* →
   **Create token**. Name it `ha_audit`. Copy it once; it is not shown again.

2. Add it to `secrets.yaml` — which is already gitignored, unlike `scripts/`:

       ha_audit_cmd: >-
         HA_URL=http://localhost:8123
         HA_TOKEN=PASTE_THE_TOKEN_HERE
         python3 /config/scripts/ha_audit.py --json --log /config/www/spc/ha_audit.log

3. In `packages/audit.yaml`, replace the `shell_command` with the secret:

       shell_command:
         ha_audit: !secret ha_audit_cmd

   The whole command including the token lives in `secrets.yaml`, so nothing
   sensitive is in a tracked file. `!secret` cannot be used *inside* a string,
   which is why the entire command is the secret rather than just the token.

4. Restart Home Assistant. `shell_command` is not reloadable.

5. Verify — run **Developer Tools → Actions → "Run HA Audit"**. Expect the
   `live-check-skipped` WARN to disappear and, on this system today, four
   `statistics-buffer-truncating` findings to be absent because the sizes were
   already corrected. Confirm the check ran rather than assuming: the INFO line
   should no longer mention it.

## If you would rather not create a token

Leave it. The WARN is honest — it says the check did not run, which is true, and
it will keep saying so. That is the correct failure direction: a coverage gap
that announces itself. The alternative considered and rejected was moving the
check into `script.ha_audit`'s own template, which needs no credential but would
split one rule across Python and YAML — a second copy of a definition, which is
this repo's recurring defect.
