# sdr-green-move

Moving the SDR receiver (the NESDR SMArt v5 and the rtlamr2mqtt add-on) off the
N100 and onto the retired HA Green, in the basement.

**Read this when:** before any step of the move; before running
`scripts/sdr_gain_set.py` or changing the rtlamr2mqtt add-on once any step has
been taken; when a meter goes stale and you need to know which host should be
receiving.

**STATUS: PLAN. Nothing done, nothing deployed.** Written 2026-11-03 at Bill's
request. Tracked as `docs/pending.md` P28. Update the status line here as each
stage completes, and record each stage in CHANGELOG.md with its times.
Corrected 2026-11-03 after a consequence review (CHANGELOG [2026.11.03]); each
correction is marked where it was made.

---

## 1. Decisions (Bill, 2026-11-03)

- The dongle that is on the N100 now moves. There is no second dongle.
- The Green decodes the same three meters and nothing else: gas 20109304 (SCM),
  electric 43344099 (SCM), water 1571014090 (R900)
  [S: `docs/addons/rtlamr2mqtt-recommended.yaml` meters block; `docs/sdr-signal-level.md` section 6].
- The Green and the antenna go to the basement. Ethernet is available there.
- The Green runs from a wall adapter. It is not on a UPS.

## 2. The unattended moment

A power cut, or 03:00 with the Green rebooted or its dongle wedged, and nobody
looking. "Working" at that moment means three things:

1. When the power comes back, the Green starts by itself (gate G0, section 4 -
   NOT yet known).
2. The add-on starts and recovers by itself (verified from source, section 3).
3. While the Green is down, the N100 says so through the existing stale alarm
   instead of recording silence as a quiet meter (verified from source,
   section 3).
4. When the Green comes back, the N100's age sensors read the gap correctly.
   Today they subtract a timestamp made by the Green's clock, so this needs the
   Green's clock to be right (added 2026-11-03; section 3, levers in section 10).

## 3. What was checked against source, so it is not re-derived

Sources were read 2026-11-03 (R6): rtlamr2mqtt at tags 2026.5.9 (`96748ef`, the
version the N100 ran at the last check, 2026-09-17) and 2026.10.15 (`90ea229`,
what a fresh install on the Green gets); home-assistant/supervisor at main
`bf3c4c1` (2026-11-02); the Mosquitto add-on at home-assistant/addons master.

**Corrected 2026-11-03:** the 2026.5.9 premise is out of date. The N100 already
runs 2026.10.15 with auto-update on [M: `update.rtlamr2mqtt_update`, 2026-11-03;
`sensor.rtlamr2mqtt_version` reads 2026.10.15 back to its oldest kept state,
2026-10-23T18:14Z], so the move no longer changes the add-on version. Also read
that day, for the rows added below: Home Assistant OS at `dev` (the Green board
files), Linux v6.18 `drivers/rtc`, and aiomqtt 2.5.1.

| claim | evidence |
|---|---|
| The meter entities carry over. Discovery goes to `homeassistant/device/<meter_id>/config`, unique ids are `<meter_id>_reading` and `<meter_id>_lastseen`; neither depends on the host or on `base_topic`. A Green publishing to the same broker takes over the same registry entries, so `sensor.gas_meter_reading` and the rest keep their ids and history. | [S: `ha_messages.py:20,54`, `mqtt_publisher.py:181`] |
| Those files, `config.py`, `buildcmd.py` and the Dockerfile's `rtlamr@v0.9.5` pin are unchanged between 2026.5.9 and 2026.10.15. | [S: `git diff --stat 2026.5.9 2026.10.15`] |
| **Never run the add-on on both hosts at once.** Same discovery topic and unique ids means the two copies overwrite each other's discovery every `discovery_interval`, and the `*_last_seen` series becomes a merge of two antennas. | [S: same lines] |
| An external broker works. With `mqtt.host` set, the add-on skips the Supervisor lookup. Its manifest says `mqtt:need`, but the Supervisor does not enforce `need`. | [S: `helpers/config.py:100-106`; supervisor `const.py:426` defines `NEED_SERVICE` and nothing else references it] |
| A dead Green raises the existing stale alarm. Discovery sets `availability_topic: rtlamr/status`, the add-on's MQTT last will publishes `offline` there, the meter sensors go `unavailable`, the age sensors read that as 99999 min, and the stale binary sensors turn on. The alarm is a persistent notification, not a phone push. | [S: `ha_messages.py:58`, `mqtt_publisher.py:64-68`; `packages/utility_meters.yaml:732-760, 849-863, 1114`] |
| The add-on starts even if the Green's own HA Core fails to start (for example after an unclean power cut): the Supervisor tries Core, files a repair issue if Core is in an error state, then boots `application` add-ons regardless. | [S: supervisor `core.py:300-318`] |
| 2026.10.15 adds self-recovery: on an rtl_tcp read timeout it resets the USB device and restarts rtl_tcp. | [S: `meter_reader.py`, `usb_utils.py` diff] |
| 2026.10.15 pulls a prebuilt image (`image: allangood/rtlamr2mqtt`) instead of building on the device. It has amd64 and arm64 builds (verified 2026-11-03; until then this row said "Not verified"). **Not verified: that it matches the Dockerfile.** | [S: `config.yaml` diff; M: Docker Hub manifest for tag 2026.10.15, 2026-11-03] |
| The add-on slug comes from the repository URL: the first 8 hex digits of SHA-1 of the lower-cased URL. `https://github.com/allangood/rtlamr2mqtt` gives `6713e36e`, the prefix `sdr_gain_set.py` uses, so the N100 was set up with exactly that string. A trailing `/` gives `ef8ce3dc` and `.git` gives `5f228eb6`. | [S: supervisor `store/utils.py:12-15`; D: `sha1(url.lower())[:8]`; `scripts/sdr_gain_set.py:37`] |
| Mosquitto accepts Home Assistant users with no broker configuration, or local users under `logins:`. `homeassistant` and `addons` are reserved names. | [S: mosquitto `DOCS.md:49-56, 152-154`] |
| The Green is wired only (one gigabit Ethernet port, no Wi-Fi listed), has 2 USB 2.0 ports rated 5 V up to 2 A combined, and takes 12 V DC 1 A on a 5.5 x 2.1 mm barrel, about 1.7 W idle and 3 W under load. | [S: Green datasheet as quoted by retailers (ameridroid, thepihut); not measured here] |
| **The age sensors would be measuring the Green's clock** (added 2026-11-03). The add-on stamps `lastseen` with its own host's clock when it publishes, not when it decodes; the N100's age sensors subtract that from the N100's `now()`, clamped only at the top. If the Green's clock is behind by more than a threshold, all three alarms latch on; if it is ahead, they fire late by the error. The time zone does not matter: the stamp carries its offset. | [S: `mqtt_publisher.py:209`; `packages/utility_meters.yaml:727-760`] |
| The Green has a clock chip with a battery holder, an NXP PCF8563, and the kernel sets the system clock from it when its driver loads. With no coin cell it loses its time in a power cut and the driver refuses it ("low voltage detected, date/time is not reliable"), so the Green boots with a past time until NTP corrects it [I]. The cell is an optional CR2032. That the PCF8563 is the clock the kernel reads (`rtc0`) is also [I]: the PMIC's own RTC driver is off in the Green kernel config. Falsifier for the row: the Green's boot log after a cold boot with the WAN unplugged. | [S: HAOS `board/nabucasa/green/patches/linux/0001-arm64-dts-rockchip-Add-NabuCasa-Green-board.patch:482-483`, `board/nabucasa/green/kernel.config`; Linux v6.18 `drivers/rtc/class.c:435`, `drivers/rtc/Kconfig:25-27` (`RTC_HCTOSYS` default y), `drivers/rtc/rtc-pcf8563.c:158-161`; Nabu Casa support 25141580918941, title only (body HTTP 403); community thread 960473, 2025-12-08: same driver message, fixed by fitting a CR2032] |
| **A broker outage now replays a burst** (added 2026-11-03). While the broker is unreachable the add-on keeps up to 100 readings, dropping the oldest, about 19 min of decodes [D: 100 / 5.35 per min, M 2026-09-17], and publishes them on reconnect, each stamped with the publish time. On the N100 a reboot restarts both and empties the queue; with the add-on on the Green, every N100 reboot or Mosquitto restart replays one. Whether the burst spikes the derived electric power is [I]; falsifier: `sensor.utility_electric_power_clean` across the last Mosquitto restart. | [S: `rtlamr2mqtt.py:81`, `meter_reader.py:140-148`, `mqtt_publisher.py:88-95, 209`] |
| Ruled out (added 2026-11-03): a stopped add-on stays stopped through a Supervisor auto-update, so the idle N100 copy cannot start itself; an N100 copy started without the dongle exits at its USB check before the MQTT publisher starts, so it cannot publish `offline` over the Green; a Green that boots before the broker retries every 5 s, indefinitely. | [S: supervisor `bf3c4c1` `apps/app.py` `update()`; `rtlamr2mqtt.py:95-101` against `:173`; `mqtt_publisher.py:88-95`] |

## 4. Gate G0 - does the Green turn itself back on? (Bill, before Stage 2)

**Not known.** The official startup article (Nabu Casa support 25209783508125,
which green.home-assistant.io/guides/start_up_after_power_off redirects to)
could not be read here (HTTP 403). A search summary of it describes pressing the
power button on a Green that "was powered off temporarily", which may mean a
shutdown from the UI rather than a power cut. The one community answer found is
a guess ("I'm pretty sure HA Green normally powers up on the return of power",
community.home-assistant.io thread 1022225, 2026-08-27).

**Test, about a minute, on the bench during Stage 0:** with the Green running
and set up, pull its power plug. Wait 30 s. Plug it back in and do not touch any
button. PASS: the LED returns to its heartbeat and the UI answers at its IP
within a few minutes. FAIL: it stays dark until the button is pressed.

**On FAIL the plan does not meet its unattended moment.** Every power cut would
leave the meters dark until someone presses the button. Do not start Stage 2
until Bill has decided what to do about it (the wall-power decision is the
lever). Logged in `open_questions.yaml`, so the audit WARNs until it is answered.

## 5. Stage 0 - prepare (the running pipeline is not touched)

1. **Pre-register Stage 1 (an on-host session; this needs InfluxDB).** Write a
   PREDICTION LEDGER row in CHANGELOG.md before Stage 1, by the method of the
   2026-09-17 antenna row: daily capture = distinct `*_meter_last_seen` states /
   (86400 s / cadence), cadences 11.42 / 30.0 / 28.0 s for electric / gas /
   water [S: that row]; control = the outage-free days just before Stage 1, n
   stated; band = mean +/- 2 sd sqrt(1/7 + 1/n). Prediction: all three meters'
   7-day means stay inside their bands, because the decode path is unchanged
   (section 3). Computing the band uses pre-move data only, so it is still a
   pre-registration if done any time before Stage 1.
   **Water caveat:** water capture switches level for days at a time on its own
   (`docs/pending.md` P17, 2026-10-16), so a water result alone is weak
   evidence. Gas and electric are the cleaner tests.
2. **Export the live add-on options from the N100.** Add-on page,
   Configuration, the three-dot menu, Edit in YAML: copy everything to a file.
   This is the only copy of the live settings (that they are untracked is P18
   Layer B). Compare it with the last known command line: AGC (no `-g`, no
   `-tunergain`), `-symbollength=80`, `-s 2621440`, `-centerfreq=912380000`,
   `-unique=false`, no `-samplefile` [S: CHANGELOG ledger row 2026-09-18, read
   back from the add-on log]. Any difference is a finding: record it before
   moving. Note the version shown on the Info tab.
3. **Wipe the Green before it goes on the house network.** It very likely
   still holds the pre-July house config [I: falsified if it boots straight to
   onboarding]. Booted normally, it would be a second HA running the same
   automations, sending pushes and connecting to the ESPHome, Kasa and Ecobee
   devices. Reset with the button held from power-on, so the old config never
   starts: hold the reset button, plug in power, release at solid yellow. This
   needs HAOS 13.1 or later and an internet connection; a blinking yellow LED
   means the OS is too old, and the SD-card method applies (Nabu Casa support
   25162566451485). If the normal UI appears instead of onboarding, the reset
   failed: shut down properly and repeat.
4. **Onboard it** with nothing else configured. Settings, System, Network:
   rename the hostname (for example `ha-green-sdr`) so it does not clash with
   the N100 on mDNS. Reserve its IP on the router. Apply OS updates now, not
   later.
5. **Run gate G0** (section 4) while it is on the bench.
6. **A broker login for the Green, on the N100.** Prefer a dedicated, non-admin
   Home Assistant user, local network only: Mosquitto accepts it with no broker
   change (section 3). A local `logins:` user instead means editing and
   restarting the Mosquitto add-on, which drops every MQTT client on the N100
   for the restart, the SEM-Meter pipeline included. Either way it is a change
   to the live N100 (R12).
7. **Install the add-on on the Green, do not start it.** Add the repository as
   exactly `https://github.com/allangood/rtlamr2mqtt` (section 3, slug). Install
   rtlamr2mqtt, paste the exported options, and add the broker:

   ```yaml
   mqtt:
     host: 10.0.0.210
     port: 1883
     user: <green login>
     password: <password>
   ```

   Leave `ha_autodiscovery_topic`, `ha_status_topic` and `base_topic: rtlamr`
   as exported. Start on boot ON, Watchdog ON, auto-update OFF (an update that
   renames topics would break the entities with nobody watching).

## 6. Stage 1 - change the host, keep the antenna where it is

One variable: host and USB port. (Until 2026-11-03 this said "host, add-on
version and USB port"; the N100 already runs the version a fresh install gets,
section 3. Check that both Info tabs show the same version before step 1.)
The Green sits on Ethernet
next to the N100; the antenna stays at its spot under the end table (the dongle
reaches it on the existing 2000 mm MR-195 lead [S: CHANGELOG, 2026-09-17
antenna swap entry]).

**When:** after 05:01:15 and finished well before 23:55. The water overnight
bins run 00:00:45 to 05:00:45 and the softener count reads the water meter at
05:01:15 [S: `docs/eod-timing.md` schedule]. Mid-morning is right. Leave
`input_boolean.sdr_alerts_enabled` on: the alarm is a notification, not a push,
and leaving it on means nothing to remember to switch back.

1. N100: stop the add-on. Set Start on boot OFF. Leave it installed: it is the
   rollback. Write down the time.
2. Move the dongle to a Green USB port.
3. Green: start the add-on. Its log must show `Found 1 RTL-SDR device(s), using
   index 0` [S: `rtlamr2mqtt.py:102`] and then `Connected to MQTT broker at
   10.0.0.210:1883` [S: `mqtt_publisher.py:79`]. Write down the time.
4. N100: `sensor.gas_meter_last_seen`, `sensor.electric_meter_last_seen` and
   `sensor.water_meter_last_seen` update, under the SAME ids. **Any `_2` entity
   means the unique ids did not match: roll back (section 9).**
5. N100: the three `*_meter_age` sensors fall back under their stale thresholds
   and the stale binary sensors turn off.
6. CHANGELOG: the stop and start times, as a step in the capture series.
7. Dwell 7 outage-free days, then score the Stage 1 row.

## 7. Stage 2 - move to the basement

One variable: position. Only after the Stage 1 row is scored and G0 has passed,
or Bill has decided what to do about a G0 failure.

1. Pre-register the Stage 2 row first, by the same method, with a direction per
   meter written before the move. The meters lie in three directions: electric
   outside and below, gas at ground level on the far side of the house, water
   in the basement [S: Bill 2026-09-17, `docs/sdr-signal-level.md` section 8].
   Indoors the effect cannot be calculated (same section), so this is a
   measurement, not a prediction to be argued from geometry.
2. Shut the Green down from its UI, move it with the antenna, power it up, and
   confirm the same as Stage 1 steps 3-5. Write down both times.
3. Choosing the basement spot: the section 8 survey is the instrument, but its
   gate (P17 steps 2 and 3) is not met, and the sample dump would now land on
   the Green (section 8 of this file, item 3). Until then pick the spot by
   judgement and do not move it inside the 7-day window.

## 8. Repo changes after Stage 1, not before

They describe a state that does not exist until Stage 1 is done.

1. `scripts/sdr_gain_set.py` talks to the local Supervisor
   (`http://supervisor`, slug `6713e36e_rtlamr2mqtt`, lines 37-38). Run on the
   N100 after Stage 1, it would edit and restart the idle rollback copy, which
   has no dongle, and its read-back would look like success. Make it refuse
   unless the add-on is started on the host it runs on, and run it from an SSH
   add-on on the Green. **Until that change: do not run it on the N100.**
2. `packages/utility_meters.yaml:1120`: the stale alarm says "Check the
   rtlamr2mqtt add-on log"; name the Green and its address.
3. `docs/sdr-signal-level.md` section 4: the `-samplefile` dump lands in the
   Green's `/config`, not on `H:`. Reading it from Windows needs a Samba share
   on the Green. P17 changes accordingly.
4. P18 Layer B: the options export and the `sdr-config-drift` rule must read
   the Green's Supervisor.
5. `docs/house.md`: the Green is back in service as the SDR receiver, in the
   basement, on wall power. `docs/off-host-access.md`: its address and where its
   add-on log is.
6. `docs/addons/rtlamr2mqtt-recommended.yaml` header: which host runs it.
7. After a clean week on the Green, uninstall the N100 copy, so nothing can
   start it or edit it by mistake.

## 9. Rollback, at any stage

Stop the add-on on the Green. Move the dongle (and the antenna) back to the
N100. On the N100, set Start on boot ON and start the add-on. No settings change
is needed, and the entities resume under the same ids (section 3). Write down
the times in CHANGELOG.

**Check the version first** (added 2026-11-03). The idle N100 copy keeps
auto-updating (auto-update ON [M: `update.rtlamr2mqtt_update`, 2026-11-03])
while the Green's is OFF (section 5 step 7), so the two can drift apart and a
rollback can start a version that has never run here. If the Info tabs differ,
write both versions in the CHANGELOG entry for the rollback. Whether both copies
should get one setting is an open decision (Bill).

## 10. Outage behaviour, accepted with the wall-power decision

In a power cut the Green goes down with the mains while the N100 stays up on
the UPS (about 128 min [D, `docs/house.md`]). About 90 s later the broker gives
up on the Green and publishes its will message [D: 1.5 x 60 s]: 60 s is
aiomqtt's default keepalive [S: `client.py:226` at 2.5.1, the floor of the
image's `aiomqtt>=2.5.1`] and 1.5 x is when [S: MQTT 3.1.1 section 3.1.2.10] has
the broker drop a silent client. The meter sensors
go `unavailable`, their ages jump straight to 99999 min, which is over every
threshold, and the stale binary sensors have no delay, so **all three alarms
fire together**. (Corrected 2026-11-03: this said each stale alarm fires when
its threshold passes.) The live thresholds are the `input_number.sdr_*_stale_minutes`
helpers, which have no `initial:` in the package, so read them from the live
API; the template fallbacks (gas 360, water 60, electric 60 min) apply only when
a helper is unavailable [S: `packages/utility_meters.yaml:849-863`].

Nothing is lost from the totals: the meters transmit their own running counters
[S: `packages/utility_meters.yaml` header], so the first reading after the gap
carries the whole change. What a gap loses is per-interval detail (live power,
reads per minute) and, for a night outage, that night's water overnight bins,
which have their own stale detector [S: `docs/eod-timing.md` schedule].

**When the power comes back** (added 2026-11-03). With no coin cell the Green
boots with a past time until NTP corrects it (section 3). If the internet is
up, that should be quick [I: falsifier, the Green's log time against the N100's
after a cold boot]. If it is still down, every reading looks as old as the
clock error, at least the length of the outage [I], so all three alarms stay on
while the meters are in fact being received. Two levers, neither built:

- A CR2032 in the Green (Bill's proposal, 2026-11-03). It covers this case. It
  does not cover a cell that has gone flat: the kernel logs that at boot,
  nothing in HA watches the Green's log, and the failure comes back with no
  warning.
- Compute the age from when the N100 receives each reading, instead of from
  the Green's stamp. Nothing is lost: the stamp is the publish time, not the
  decode time (section 3), so the N100's receive time carries the same
  information without the Green's clock in it. It needs its own R2 cycle; one
  edge to settle in the sandbox is how the age reads straight after an N100
  restart.

**Open decision, nothing built:** whether the stale alarms should stay quiet
while the house is on battery. Bill's call.
