# sdr-signal-level

How to measure PER-PACKET SIGNAL LEVEL (RSSI / SNR / noise) for the three SDR
utility meters, which `rtlamr` cannot report at all.

**Read this when:** comparing antennas or antenna POSITIONS, or any time the
question is "is this link strong?" rather than "how many packets arrived?".
Capture rate answers the second question and is measured a different way -
InfluxDB `sensor.*_meter_last_seen`, see CHANGELOG 2026-09-17.

**STATUS: NOT DEPLOYED.** Written 2026-09-17 from the source of every component
(citations inline, R6). Nothing here has been run. Section 6 is the gate that
must pass before any number this produces is believed (R7).

---

## 1. Why rtl_433 cannot simply run alongside the add-on

Bill's question was whether rtl_433 could run next to rtlamr2mqtt "if at same
freq and pointed at same meters". Frequency is not what blocks it - three
independent things do, and all three are in the source:

- **The USB device is claimed exclusively.** `librtlsdr.c:1526` calls
  `libusb_claim_interface`; a second process opening the same dongle gets
  `usb_claim_interface error` [S: osmocom rtl-sdr].
- **`rtl_tcp` serves ONE client at a time.** `listen(listensocket, 1)`
  (`rtl_tcp.c:594`), then a single `accept()` (`:606`) whose worker is
  `pthread_join`ed before the next accept (`:641-644`). A second client waits in
  the backlog until the first disconnects [S].
- **That port is not reachable anyway.** `rtl_tcp` defaults to `127.0.0.1`
  (`rtl_tcp.c:383`) and the add-on sets `host_network: false` [S: rtlamr2mqtt
  add-on 2026.5.9 `config.yaml` - the installed version, from
  `sensor.rtlamr2mqtt_version`]. The listener exists only inside that add-on's
  network namespace.

The add-on image has no rtl_433 either: its Dockerfile builds only osmocom
rtl-sdr [S]. And no rtl_433 add-on is installed here [M: 0 matches for
`rtl_?433` in `.storage/core.entity_registry`, 2026-09-17].

So the live-radio options are (a) stop rtlamr2mqtt for the duration, which takes
the meter alarms blind, or (b) a second dongle, which measures a different
antenna and answers a different question. Section 2 is better than both.

## 2. The route that works: rtlamr's own sample dump, read offline

`rtlamr` writes raw IQ samples **only when it decodes a packet**:

```go
// main.go:283, inside the block loop
if pktFound {
    _, err := sampleWriter.Write(sampleBuf.Bytes())
```

`sampleBuf` is a rolling buffer trimmed to `BufferLength<<1` bytes
(`main.go:229-232`), so each write is one packet plus a little context - not a
continuous stream. The file is opened with `os.Create` (`flags.go:135`), i.e.
**TRUNCATED on every rtlamr start**, and defaults to `os.DevNull`
(`flags.go:37`) so the feature is off unless asked for.

That gives a small file of IQ windows, each containing a packet rtlamr already
decoded, which rtl_433 reads with `-r` and annotates with `-M level`
("Modulation, Frequency, RSSI, SNR, and Noise", rtl_433 README:618) [S].

**The pipeline never stops.** Same dongle, same antenna, same packets.

### Size, from this house's own numbers

`BufferLength = PacketLength + BlockSize` (`decode.go:141`), with the config
taking the max over enabled protocols (`decode.go:106-109`): r900 has the larger
frame at 116 packet symbols and 32 preamble symbols (`r900.go:65-66`) against
scm's 96 / 21 (`scm.go:47-48`). At `-symbollength=80`, SymbolLength = 160
samples (`decode.go:132`), so:

```
  PacketLength   116 x 160                = 18,560 samples
  BlockSize      NextPowerOf2(32 x 160)   =  8,192 samples
  BufferLength   18,560 + 8,192           = 26,752 samples = 53,504 B  [D]
  per decode     53,504 B + up to 1 block = 54-70 KB                   [D]
```

At the measured decode rate of 5.35/min [M: 347 decodes in 64.8 min, 2026-09-17
12:16-13:21 EDT, InfluxDB `last_seen`] that is **17-22 MB/h** [D]. Host free
space is 369.8 GB [M: `df` 2026-09-17], so size is not the constraint - but the
file grows for as long as rtlamr runs, and it lands inside the git tree
(section 4).

## 3. The add-on change

Two custom parameters. **Read the CURRENT values out of the add-on's own
Configuration tab first and append to them** - do not paste this file's copy of
them, which is a snapshot and will drift (R10).

As logged on 2026-09-17 [M: add-on log, which prints the full command line]:

```
  rtlamr:  -unique=false -symbollength=80 -centerfreq=912380000
  rtltcp:  -s 2621440
```

Append:

```
  rtlamr:  ... -samplefile=/config/tmp/rtlamr_912.38M_2621.44k.cu8 -tunergain=40
  rtltcp:  ... -g 40
```

- **`-samplefile` passes through untouched.** `build_rtlamr_args` extends the
  arg list with the custom string verbatim; it only strips `-server` and
  defaults `-unique=true` when absent [S: `buildcmd.py:39-52`].
- **Fixed gain needs BOTH `-g 40` AND `-tunergain=40`. Neither works alone,
  and `-s 2621440` must stay.** AGC moves the very quantity being compared, so
  a survey run under it measures the AGC loop, not the antenna.
  - **`-g 40` on `rtltcp` is the half that SETS it.** gain 0 - the default -
    takes the `rtlsdr_set_tuner_gain_mode(dev, 0)` branch, i.e. automatic;
    non-zero takes mode 1 (manual) and then `rtlsdr_set_tuner_gain(dev, gain)`
    [S: `rtl_tcp.c:509-521`]. `-g` is in dB, scaled by 10 at `rtl_tcp.c:428`,
    and snaps to the tuner's nearest supported step.
  - **`-tunergain=40` on `rtlamr` is the half that KEEPS it.** It sets nothing
    itself (below), but it is the only way to stop rtlamr handing the tuner
    back to AGC. After connecting, rtlamr runs
    `if !gainFlagSet { rcvr.SetGainMode(true) }` [S: `main.go:98-122`, rtlamr
    v0.9.5]; `SetGainMode(true)` sends command 3 with param **0**
    [S: `rtltcp.go:196-199,228-233`]; rtl_tcp passes that param straight to
    `rtlsdr_set_tuner_gain_mode` [S: `rtl_tcp.c:324-326`], and 0 is automatic.
    Any of `-gainbyindex -tunergainmode -tunergain -agcmode` clears
    `gainFlagSet`; `-tunergain=40` is the one that records the value it is
    matching. Use the `=` form - the add-on splits the string on whitespace.
  - **Why the rtlamr half sets nothing.** The flag's own command is sent by
    `rcvr.HandleFlags()`, called at `main.go:328` - BEFORE `rcvr.NewReceiver()`
    at `main.go:341` connects at `main.go:91`. It writes to a nil `TCPConn`,
    the resulting error is panicked, the deferred `recover()` inside
    `HandleFlags` swallows it, and `main.go:328` discards the return value
    [S: `rtltcp.go:101-147,186-188`]. Nothing is logged at any verbosity. Only
    `-centerfreq` and `-samplerate` survive that, because `NewReceiver`
    re-sends those two explicitly after Connect - the same mechanism as ERROR 3
    in `rtlamr2mqtt-recommended.yaml`. So the two flags must agree by hand:
    nothing checks that 40 equals 40.
  - **R13 - this bullet asserted the OPPOSITE until 2026-09-17.** It read
    "`rtlamr` never sets gain at all (no gain flag exists in `flags.go`), so
    gain set here STICKS". Both halves are false, and acting on it would have
    produced a whole survey of AGC decisions with every gate passing. The gain
    flags are real but are registered by the vendored `bemasher/rtltcp`
    package's `RegisterFlags()` [S: `rtltcp.go:83-98`], not by rtlamr's own
    `flags.go` - reading the one file named in the claim is what missed them.
    `rtlamr2mqtt-recommended.yaml:354-356` already recorded the correct
    behaviour on 2026-08-25 and was not cross-read when this was written.
  - Keep `-s 2621440`: `build_rtltcp_args` inserts `-s 2048000` if no `-s` is
    present in the custom string [S: `buildcmd.py:85-87`].
  - Identity of what was read, 2026-09-17 (R16): rtlamr `v0.9.5` (the version
    the add-on Dockerfile pins) and the `bemasher/rtltcp` commit its `go.mod`
    pins, `3aed81c166c5`; `rtl_tcp.c` from osmocom `rtl-sdr` master. The
    add-on ships Alpine's rtl-sdr build, so its line numbers may differ - the
    command numbers and the param semantics are the wire protocol and do not.
- **The filename is load-bearing.** rtl_433 detects centre frequency, sample
  rate and format from the path: a number suffixed `M`/`MHz`, a number suffixed
  `k`/`ksps`, and `cu8` [S: README:627-641]. `rtlamr_912.38M_2621.44k.cu8`
  therefore needs no `-s`/`-f` on the reader side.
- **Restart, not reload** - `shell_command`-style reloads do nothing here.
  Expect a reception gap of about 4 minutes [M: 16:12:01-16:16:41 UTC on
  2026-09-17, the antenna-swap restart].
- **Do the restart on a day OUTSIDE any running prediction window**, or it
  shaves a few minutes off that day's capture.

## 4. Where the file goes

`/config` is the ONLY folder the add-on can write to [S: `config.yaml`
`map: [config:rw]`], and `/config` is this git tree. So:

- Path: `/config/tmp/` (create it; it does not exist yet as of 2026-09-17).
- `.gitignore` already carries `tmp/` for this, added 2026-09-17 with this doc,
  so a 20 MB binary cannot be committed by accident.
- **Copy the dump off before any add-on restart** - `os.Create` truncates it and
  the previous run's samples are gone.

## 5. Reading it, on Windows

rtl_433 ships an official Windows x64 build, so nothing needs installing on the
HA host and the dump can be read straight off the `H:` share [S: release 25.12
asset `rtl_433-win-x64-25.12.zip`].

```powershell
# once: unzip the release to C:\tools\rtl_433\
# copy first - never analyse the live file
copy H:\tmp\rtlamr_912.38M_2621.44k.cu8 C:\sandbox\sdr\
C:\tools\rtl_433\rtl_433.exe -r C:\sandbox\sdr\rtlamr_912.38M_2621.44k.cu8 `
    -M level -R 149 -R 228 -F json:C:\sandbox\sdr\levels.json
```

`-R 149` is ERT Standard Consumption Message (electric + gas), `-R 228` is
Neptune R900 (water) [S: README:245, :324]. If filename detection fails, force
it: `-r cu8:<file> -s 2621440`.

## 6. GATE - run this before believing any level number (R7)

The whole route rests on one untested claim. Check it on the first dump:

1. **Decodes at all?** Non-zero rtl_433 output from a dump whose span contains
   50+ rtlamr decodes. **If zero, [I1] below is falsified and this route is
   dead** - fall back to stopping rtlamr2mqtt and running rtl_433 live on the
   dongle (R12: ask Bill first, the meter alarms go blind).
2. **The right meters?** Decoded ids must be among 20109304 and 43344099 (SCM)
   and 1571014090 (R900). Any other id means the dump is being misread.
3. **Roughly the right count?** Compare rtl_433's decode count against rtlamr's
   own over the same wall-clock span (InfluxDB `last_seen`). A large shortfall
   means the windows are being truncated or spliced badly, not that the link is
   weak.
4. **Level fields populated?** `rssi`, `snr`, `noise` present and not constant.
   A constant value means AGC is still running or `-M level` was dropped.

## 7. What this instrument CANNOT tell you

- **It only sees packets that were decoded.** The dump is written inside
  `if pktFound`. Misses leave no sample, so the level distribution is CENSORED -
  it describes successes only and cannot say how close the failures came. This
  is why it compares POSITIONS but cannot explain the loss mechanism.
- **It is not capture rate.** Capture stays measured by the `last_seen` route.
  Never quote one as evidence for the other.
- **RSSI here is relative to gain**, not dBm. Valid for A/B at a fixed gain
  (BOTH flags of section 3 - `-g 40` alone is not fixed gain); meaningless as
  an absolute figure.
- **Level depends on which hop channel a packet landed on**, and multipath is
  frequency-selective. A single decode says nothing; compare medians with n
  stated (R17).
- **The file is spliced** from non-contiguous windows, so anything rtl_433 infers
  across window boundaries (timing, gaps, rates) is an artefact.

## 8. The placement survey, if the gate passes

The question this was built for: where on the underside of the metal end table
should the antenna hang? It cannot be calculated - indoors, level changes over
about 6.4 in [D: lambda/2 at 915 MHz] and differently per direction, and the
three meters lie in three directions [S: Bill 2026-09-17 - electric outside and
below, gas at ground level on the far side of the house, water in the basement].

```
1. Positions: 4-6 spots about 6 in apart on the underside, plus one off-table
   control. Keep the element perpendicular to the plate and not flat against it.
2. Dwell: n >= 10 decodes PER METER per spot. Gas is the binding constraint at
   ~1.0 decode/min [M: 65 in 64.8 min, 2026-09-17], so >= 10 min per spot.
3. Fixed gain for the whole survey: `-g 40` AND `-tunergain=40`, section 3.
   Note BOTH in the write-up, and confirm they still match before each spot.
4. Per spot, per meter: median SNR, IQR, n. Compare the best spot against the
   current one with Mann-Whitney U; report p, and do not call a winner on
   medians alone (R17).
5. Decide on the WEAKEST meter (gas today), subject to not degrading the other
   two beyond their control spread.
```

**Moving the antenna voids any running capture prediction** - the 09-18..09-24
row in the CHANGELOG ledger says so explicitly. Either survey after it scores,
or mark that row WITHDRAWN (never delete it) and re-register at the chosen spot.

## 9. Rollback

Remove `-samplefile=...` and `-tunergain=40` from the rtlamr custom parameters,
restart the add-on, delete `/config/tmp/*.cu8`. That alone restores as-found
behaviour: with no gain flag on rtlamr, it re-enables AGC on connect regardless
of `-g 40`, so a forgotten `-g 40` left in `rtltcp` is inert rather than
harmful. To KEEP fixed gain, keep both flags and say so - that is the change
from as-found, and it is the pair, never `-g` on its own.

## 10. Open [I], each with its falsifier

- **[I1]** rtl_433 decodes SCM and R900 from spliced 2.62 MS/s `cu8` windows.
  *Falsified by* zero decodes in section 6 step 1.
- **[I2]** the dumped window contains each whole frame. *Falsified by* rtl_433
  finding preambles but failing CRC on most packets.
- **[I3]** the Pulse W5012 is a half-wave dipole needing no ground plane -
  inferred from 179 mm against lambda/2 = 164 mm and 2 dBi against a dipole's
  2.15 dBi [I]. *Falsified by* Pulse documentation calling it a quarter-wave or
  ground-plane type, or by level changing sharply when it is lifted off metal.
  L122.A (05/11) does not state the antenna type.
