# Temp/Humidity Sensor PCB — Design Document

**Status:** Pre-fabrication — layout reviewed, fab-ready (Rev C board). The Rev C
board is **unchanged** by the 2026-07-18 display/light-sensor add-on — that add-on is
entirely a STEMMA QT bus + firmware + enclosure change (see §2, §5, §9.3, §10.1).
Firmware is at **Rev 2.1** (2026-07-20, §10.2): display resilience + HA-tunable
display parameters; validated on the deployed esphome 2026.6.4.
**Last updated:** 2026-07-20
**Target fabricator:** OSH Park (2-layer, 1.6 mm FR4)
**Author:** wkcollis1

---

## 1. Purpose

A standalone environmental-sensing node for the unfinished basement, providing
temperature and relative-humidity telemetry to Home Assistant for:

1. **Dehumidifier control** — feeds the RH-band control loop (49 % on / 46 % off,
   3-point deadband) and the RH-based stall detector (0.3 %/hr over a 60-minute
   rolling window).
2. **Battery-bank environment** — monitors the air around the 500 Ah LiFePO4 bank
   and its copper busbars.

This node is intended to replace/supplement the Shelly H&T Gen3 currently used for
basement RH.

### 1.1 Rationale (why build vs. keep the Shelly H&T Gen3)

The deciding factor is **sample cadence**, not headline accuracy:

| Consideration | Shelly H&T Gen3 | This node (XIAO + SHT45) |
|---|---|---|
| Reporting on battery | Only on ≥ 0.5 °C or ≥ 5 % RH change, else every 2 h | n/a |
| Reporting on USB | Every 5 min | Continuous (configurable, e.g. 10–30 s) |
| Behavior inside a 3 % control band | A 3 % move is **below** the 5 % battery threshold — effectively invisible on battery | Fully resolved |
| RH accuracy | Not published by Shelly; internal sensor die not named | ±1.0 % RH (verified, see §8) |
| Long-term drift | Not published | < 0.20 %RH/yr (verified) |
| Integration | Shelly Cloud / MQTT, sleep-based | Native ESPHome → existing MQTT→HA pipeline |

The Shelly's 5 %-RH battery reporting threshold is wider than the entire control
deadband, and its 5-minute USB cadence is coarse for a 0.3 %/hr stall detector.
A continuously-sampled ESPHome node resolves both.

> **Uncertainty flag:** No manufacturer-published RH accuracy figure exists for the
> Shelly H&T Gen3, and Shelly does not name the internal RH die, so no head-to-head
> accuracy delta is asserted here. The comparison stands on cadence + the SHT45's
> independently verified ±1.0 % RH.

---

## 2. System Overview

```
  [ USB-C phone brick ] ──5V──> [ XIAO ESP32-C3 ]
                                     │  onboard reg → 3V3 (700 mA)
                                     │
                    GND / 3V3 ───────┼──> PH1 ──┐  1×4 right-angle header,
                    SDA / SCL ───────┼─(1-2)(3-4)┤ crimped 1×4 0.1″ housing
                                     │          │
                                     │          ▼   STEMMA QT daisy-chain (one I²C bus)
                                     │   [ SHT45  0x44  — external, standoffs, PTFE ]
                                     │          │  (2nd QT port)
                                     │          ▼
                                     │   [ 938 OLED 0x3D — SSD1306, lid/external ]
                                     │          │  (2nd QT port)
                                     │          ▼
                                     │   [ VEML7700 0x10 — right-angle, room-facing ]
                                     │
                    GPIO20 ── R1 ── [ green status LED ] ── GND

  One I²C multi-drop chain @ 100 kHz. VEML7700 lux gates the OLED on/off in
  firmware (lights-on → wake, dark → sleep, §10.1). Chain order is electrically
  arbitrary; physical routing decides it (§9.3). No PCB change — PH1 unchanged.
```

- The **SHT45 breakout is mounted external** to the enclosure on 8–10 mm nylon
  standoffs, opposite face from the PCB, PTFE membrane exposed to basement air.
  This isolates the RH/T element from board self-heating and the sealed-box
  microclimate, and gives it real air exchange.
- The **XIAO + PCB are inside** the IP65 box; the STEMMA cable crosses the wall.
- **Display + light-sensor add-on (2026-07-18):** two more STEMMA QT boards hang off
  the same bus by chaining through the spare QT port on each breakout — an Adafruit
  **938** 1.3″ 128×64 OLED (local temp/RH/dew-point readout) and an Adafruit **5378**
  right-angle VEML7700 lux sensor. **No PCB change:** PH1 and the Rev C board are
  untouched; the chain, firmware, and enclosure mounts carry the whole feature. The
  OLED is presentation-only and never sits in a control path; the lux reading only
  gates the display's own on/off duty cycle (§10.1) to hold down OLED burn-in and
  extend panel life.

---

## 3. Bill of Materials

| Ref | Part | MPN / PID | Notes |
|---|---|---|---|
| U1 | Seeed XIAO ESP32-C3 | — | RISC-V, WiFi/BLE, USB-C, native USB Serial/JTAG |
| — | Adafruit SHT45 Precision T/H w/ PTFE, STEMMA QT | Adafruit **6174** | I²C 0x44; onboard 10 K pull-ups + caps |
| — | STEMMA QT JST-SH 4-pin cable, 150 mm | Adafruit **4397** | Breakout → PH1; board end cut/stripped and **crimped into a 1×4 0.1″ female housing** (§9.2). Cable lay maps 1:1 to PH1 (§9.1). If the wrap-around route runs short: 200/300 mm QT-to-QT = PID 4401/5384 |
| LED | Green diffused LED, 3 mm | Lite-On **LTL-4231N** | Status indicator; Vf ≈ 2.1 V. *Board refdes is `LED` (was D1 in earlier doc revs).* |
| R1 | 1 kΩ, 1/4 W axial | — | **Series** current-limit for the LED (see §6). *Board refdes is `R1` (was R4 in earlier doc revs).* |
| C1 | 0.1 µF, 50 V X7R | C315C104K5R5TA | Local 3V3 decoupling in the PH1 feed path |
| PH1 | 1×4 pin header, 2.54 mm, right-angle | — | Sensor interface, pins overhang left board edge into cavity. Pin order **1=GND, 2=+3V3, 3=SDA, 4=SCL** — matches STEMMA wire lay (black, red, blue, yellow) 1:1. Mates with crimped 1×4 0.1″ female housing |
| 3V3, GND | Test points, THT pad 2.0 mm / 1.0 mm drill | — | Bench probe access to the 3V3 rail and GND |
| H1,H2 | Mounting holes, M3, 3.2 mm NPTH | — | Diagonal pair; board mounts on standoffs |
| — | Enclosure | Zulkit IP65 63×58×35 mm ext. | ABS, waterproof |
| PCB | Custom 2-layer, 1.6 mm FR4, ENIG | OSH Park | **23 × 38 mm**, 2 mm 45° corner chamfers (Rev C; was 23 × 40) — billed rectangle 1.355 in² → ~$6.77/set-of-3 at $5/in² |
| — | Adafruit 1.3″ 128×64 OLED, SSD1306, STEMMA QT | Adafruit **938** | Local readout, **off-board**. I²C **0x3D** (938 ships ADDR jumper open = 0x3D default; 0x3C needs the jumper bridged — verify by scan §5; shipped firmware uses 0x3D); ships default-I²C (J1/J2 closed), auto-reset (RST not needed); ~25–40 mA @ 3.3 V; dual QT ports (daisy-chain) |
| — | Adafruit Right-Angle VEML7700 Lux Sensor, STEMMA QT | Adafruit **5378** | Display-blank trigger, **off-board**. I²C **0x10** (fixed, Vishay datasheet); senses **parallel to the PCB** (edge-on) — mount room-facing (§9.3); 4.7 K onboard I²C pull-ups; dual QT ports |
| — | STEMMA QT ↔ QT cable(s), JST-SH 4-pin | Adafruit **4401** (200 mm) / **5384** (300 mm) | Chain links SHT45→OLED→VEML7700; count/lengths per final routing (§9.3). Note: no 150 mm QT-to-QT exists |

**Explicitly NOT on the board (by design):**

- **No external I²C pull-up resistors.** The SHT45 breakout already carries 10 K on
  both SDA and SCL (see §5).
- **No ALERT line.** The SHT45 has no alert/interrupt pin; it is polled over I²C.
  (The earlier `ALERT` silk on D3 was leftover from the INA228 boards and has been
  removed.)
- **No 1-Wire / DQ.** The earlier `DQ` silk on GPIO10 was a template leftover
  (DS18B20 nomenclature from the bank-monitor board) and has been removed. No
  DS18B20 on this design.

---

## 4. Pin Assignments (XIAO ESP32-C3)

| Silk | GPIO | Use | Notes |
|---|---|---|---|
| D4 | GPIO6 | **SDA** | I²C data → PH1.3 |
| D5 | GPIO7 | **SCL** | I²C clock → PH1.4 |
| D7 | GPIO20 | **Status LED** | via R1; see caveat below |
| D3 | GPIO5 | *spare* | Broken out only if used; **digital-only** (ADC2 — unreliable w/ WiFi) |
| 5V | — | USB-C 5V in | From phone brick, to onboard regulator |
| 3V3 | — | Sensor supply | To PH1.2 via C1 |
| GND | — | Common | To PH1.1 / LED / C1 (pour-only) |

**Status-LED pin caveat:** GPIO20 is the hardware **UART0 RX** pin. Using it for the
LED consumes UART0, which is harmless here — the ESP32-C3 streams its console/logs
over the **native USB Serial/JTAG** controller (the USB-C port), not UART0. Full
ESPHome logging over USB-C is retained. GPIO20 is **not** a strapping pin, so there
is no boot-mode interference.

**Strapping pins to keep clear:** GPIO2, GPIO8, GPIO9 — none are used on this design.

---

## 5. I²C Bus Design

- **Pull-ups:** rely entirely on the SHT45 breakout's onboard **10 K** on SDA and SCL.
  The XIAO ESP32-C3 has **no** onboard I²C pull-ups, so the breakout provides the
  bus's only pull-ups — which is exactly one correct 10 K per line.
- **Why no external pull-ups were added:** an added 1 K in parallel with the onboard
  10 K would give an effective ~909 Ω:

  ```
  R_eff = (1000 × 10000) / (1000 + 10000) = 909 Ω
  I_sink = 3.3 V / 909 Ω = 3.63 mA per line
  ```

  3.63 mA exceeds the ~3 mA standard-mode sink budget and violates the usual
  "keep total parallel pull-up > 2.2 K" guidance. With the breakout's 10 K alone:

  ```
  I_sink = 3.3 V / 10 000 Ω = 0.33 mA   (comfortable)
  ```

- **Pull-ups after the daisy-chain add-on (2026-07-18):** each added STEMMA QT board
  brings its own pull-ups, so they parallel down. The VEML7700 (5378) carries **4.7 K**
  per line (Adafruit changed this breakout from 10 K in Dec 2019); the 938 OLED's value
  is **not confirmed** — assume Adafruit's ~10 K QT default (flag). Combined:

  ```
  1/R = 1/10 000 (SHT45) + 1/10 000 (OLED, assumed) + 1/4 700 (VEML7700)
      = 0.0001 + 0.0001 + 0.000213 = 0.000413   →   R_eff ≈ 2.4 K
  I_sink = 3.3 V / 2.4 K = 1.4 mA per line       (comfortable, < 3 mA)
  ```

  If the OLED is also 4.7 K, R_eff ≈ 1.9 K → I_sink ≈ 1.7 mA — still inside the
  standard-mode budget. Net effect is a **stiffer, faster bus** than the 10 K-only
  baseline, so 100 kHz gets *more* margin, not less; 400 kHz would now be viable but
  there is no reason to raise it. Only if several more 4.7 K boards were stacked would
  a jumper need lifting.

- **Bus length:** on-board copper measured from layout (Rev C): SCL 37.6 mm, SDA
  33.4 mm (+ 150 mm STEMMA cable ≈ 185–190 mm total — the ~190 mm estimate stands).
  Both lines are routed 0.4 mm on F.Cu only, with **no vias** in either signal path.
- **Clock:** **100 kHz** (standard mode). 10 K over ~190 mm is fine at 100 kHz; do
  **not** raise to 400 kHz, where rise-time margin on 10 K over that length tightens.
- **Addresses (three devices after the 2026-07-18 add-on):** SHT45 = **0x44** (fixed);
  Adafruit 938 OLED (SSD1306) = **0x3D** (938 ships ADDR jumper open = 0x3D default; 0x3C
  needs the jumper bridged — **verify by i2c scan**; the shipped firmware and the
  battery-bank board's 938 both use 0x3D); VEML7700 = **0x10** (fixed, Vishay datasheet).
  No collisions; the three are well separated. Scan the assembled bus once to confirm
  before trusting firmware addresses.
- **Supply to sensor: 3.3 V, not 5 V.** Feeding the breakout VIN at 3.3 V keeps its
  level-shifter and pull-ups referenced to 3.3 V — no 5 V logic reaches the XIAO's
  I²C pins.

---

## 6. Status LED

- **Function:** slow flash = healthy / heartbeat; fast flash = fault detected.
- **Drive:** GPIO20 → R1 (1 kΩ series) → LED → GND. R1 is a **series current-limiting
  resistor** (not a pull-up).
- **Current:**

  ```
  I_LED = (3.3 V − 2.1 V) / 1000 Ω = 1.2 mA
  ```

  Dim-but-clearly-visible for a diffused indicator; well under the LTL-4231N's 20 mA
  max and the XIAO's safe GPIO limit. If a brighter indicator is wanted, 470–680 Ω
  gives ~1.8–2.6 mA.
- **Polarity:** verified in Rev B layout from the pad netlist: LED footprint pad 1
  (cathode) → GND pour; pad 2 (anode) → R1 → GPIO20.

**Note — onboard red charge LED:** the XIAO's onboard **red** LED is hardwired to its
battery-charge IC and stays **lit continuously** whenever USB power is present with no
battery attached (this design has no battery). It is cosmetic, not a fault, and is
**separate** from the green status LED — do not conflate the two during debugging.

### 6.1 Decoupling Rationale (2026-07-04)

Recorded so future cap suggestions get load math instead of a shrug. Two proposals
were evaluated: a 10 µF added near C1, and "0.1 µF in series with 10 µF."

- **Series is a topology error, not a filter.** Capacitors in series combine like
  resistors in parallel:

  ```
  C_series = (0.1 × 10) / (0.1 + 10) = 0.099 µF   ← less than the 0.1 µF alone
  ```

  and in series with the supply line it blocks DC entirely. The intended idea is the
  classic bulk + bypass pair **in parallel** (both 3V3 → GND). Note the pairing lore
  dates from electrolytic days; two parallel values also create an anti-resonance
  peak between them, and a single modern X7R 10 µF MLCC is often flatter. At this
  board's frequencies, all invisible either way.
- **The load doesn't need bulk capacitance.** (Figures re-verified from the SHT4x
  datasheet 2026-07-04.) The rail past C1 feeds only the SHT45: 80 nA idle, 0.4 µA
  average, sub-mA during the 6.9 ms measurement, specified accurate across the
  entire **1.08–3.6 V** supply window → ~2.2 V of droop headroom from 3.3 V. WiFi TX
  ripple on the shared rail (ESP32-C3 draws its ~350 mA peaks from the same
  regulator output) is bounded by the module's own output caps and lands far inside
  that window. Sensirion's design-in requirement is 100 nF close to the sensor —
  present on the breakout (§8) — plus C1 on-board: met twice over.
- **Even the on-chip heater case passes without bulk:**

  ```
  I_heater(max) = 0.200 W / 3.3 V = 60.6 mA
  Cable drop:  28 AWG ≈ 0.213 Ω/m × 0.15 m × 2 = 0.064 Ω
  V_drop = 60.6 mA × 0.064 Ω = 3.9 mV          ← negligible
  ```

  (Rev 2.x firmware does not enable the heater; ESPHome `sht4x` default leaves it
  off — verify in component source if this ever matters.)
- **Verdict:** no additional capacitor needed. If added anyway as cheap insurance:
  **10 µF X5R/X7R MLCC in parallel** with C1 or across PH1 — never in series. Only
  earns its place if the heater is ever enabled (e.g. a decontamination bake).
  Caveat flagged before the fact: the XIAO's regulator part number was **not**
  verified from the Seeed schematic re: max output-capacitance limits — negligible
  risk for a ceramic at trace distance, but noted.

---

## 7. Power

- **Source:** standard USB-C phone charger brick → XIAO USB-C port → onboard regulator
  → 3V3 rail.
- **Budget:**

  ```
  ESP32-C3 + WiFi active:   ~80–120 mA avg, ~350 mA momentary TX peaks
  SHT45 (breakout):         ~µA (negligible)
  938 OLED (when awake):    ~25–40 mA   ← from 3V3 via PH1 → chain
  VEML7700:                 ~0.5 mA (negligible)
  Status LED @ 1 kΩ:        ~1.2 mA
  ──────────────────────────────────────────
  Awake worst case ~160–170 mA avg; OLED duty-cycled low by the lux gate (§10.1),
  so the typical average is far lower. Onboard 3V3 regulator rated 700 mA →
  still large margin.
  ```

- **Display current path & cable drop (2026-07-18):** the OLED's ~25–40 mA is pulled
  from the 3V3 rail through C1, PH1.2, and the STEMMA chain — orders of magnitude above
  the SHT45's µA, but still small. Loop drop over ~0.4 m of 28 AWG (VIN + GND):

  ```
  R_loop ≈ 0.213 Ω/m × 0.4 m × 2 = 0.17 Ω
  V_drop ≈ 40 mA × 0.17 Ω = 6.8 mV              (negligible; OLED runs at 3.3 V in)
  ```

  Conductor gauge assumed 28 AWG (JST-SH cables vary — flag); even at thinner gauge
  the drop stays single-digit mV, and the on-board 1.0 mm 3V3 trace carries 40 mA
  trivially. **But** the OLED adds a charge-pump switching load downstream of C1, so
  the optional **10 µF X7R in parallel** at C1/PH1 (§6.1, §12.1 item 5) now earns its
  place as cheap insurance — populate it if the add-on is built.

- **USB-C cabling caveat:** a USB-C **source** only enables VBUS after detecting the
  sink's CC pull-downs (Rd). The XIAO's CC-resistor population was **not** confirmed
  from a primary schematic. Two safe paths:
  1. **Recommended:** use a **USB-A → USB-C** cable into an A-port brick — legacy VBUS
     is always present, no CC negotiation, question moot.
  2. If using **C → C** from a PD brick, **bench-verify it powers up** before sealing
     the enclosure. (It very likely works, since these boards enumerate over USB-C
     from CC-negotiating hosts — but this was not schematic-confirmed.)
- **Brick quality:** for 24/7 duty, use a reputable brick; the load is light, so
  thermal stress is minimal and longevity is good.

**Grounding / isolation:** this node has **no galvanic connection to the 500 Ah bank**
— it is an air sensor powered from a floating wall brick. No shared ground with the
pack, no ground-loop path. (The "never connect USB while 12 V present" hazard from the
UPS-MONITOR-V2 board does **not** apply here — this board has no 12 V input path.)

---

## 8. Verified Specifications & Sources

All figures below were checked against primary/manufacturer sources on 2026-07-02.

| Item | Spec | Source |
|---|---|---|
| SHT45 RH accuracy | ±1.0 % RH typ. (25–75 % RH) | Sensirion / Adafruit product page |
| SHT45 T accuracy | ±0.1 °C typ. (0–75 °C) | Sensirion / Adafruit product page |
| SHT45 long-term drift | < 0.20 %RH / yr | Sensirion SHT4x datasheet / humidity brochure |
| SHT45 repeatability (high) | 0.08 %RH (3σ) → ~0.027 %RH (1σ) noise | SHT4x datasheet Table 1 |
| SHT45 hysteresis | ±0.8 %RH at 25 °C (deterministic, not filterable) | SHT4x datasheet Table 1 |
| SHT45 high-rep measurement duration | 6.9 ms typ (`tMEAS,h`) | SHT4x datasheet Table 5 |
| SHT45 RH response time | 4 s τ63 @ 1 m/s airflow (longer in still air) | SHT4x datasheet Table 1, fn 9 |
| SHT45 self-heating floor | none stated (no ≥1 Hz limit); ~0.0003 °C at 10 s / high-rep | Computed from Tables 4/5/10 |
| ESPHome `sht4x` precision | `precision:` key, High/Med/Low, default **High**; High → 0xFD high-rep | ESPHome component source (sensor.py, sht4x.cpp) |
| SHT45 I²C address | 0x44 (fixed) | Sensirion SHT4x datasheet; Adafruit pinout |
| SHT45 breakout pull-ups | 10 K on SDA and SCL (onboard) | Adafruit SHT4x pinout (Learn) |
| SHT45 breakout support parts | onboard pull-ups + caps | Adafruit product page |
| PTFE membrane | IP67-rated particle/liquid barrier, response time unaltered | Adafruit product page |
| XIAO 3V3 regulator | 700 mA available on 3V3 pin | Seeed XIAO ESP32-C3 wiki |
| XIAO I²C pull-ups | none onboard | Seeed forum (schematic review) |
| XIAO strapping pins | GPIO2, GPIO8, GPIO9 | Seeed XIAO ESP32-C3 wiki |
| XIAO pin map | D4=GPIO6(SDA), D5=GPIO7(SCL), D7=GPIO20(RX), D10=GPIO10(MOSI) | Seeed / Robocraze pinout |
| XIAO onboard red LED | tied to charge IC; lit when USB powered w/o battery | Mischianti pinout writeup |
| GPIO5 (D3) ADC caveat | ADC2 unreliable with WiFi/BLE active | Mischianti / Seeed wiki |
| LTL-4231N | green, Vf ≈ 2.1 V, 20 mA max | Lite-On datasheet (DigiKey/Jameco) |
| Shelly H&T cadence | battery: ≥0.5 °C/≥5 %RH or 2 h; USB: 5 min | Shelly KB / TapHome integration notes |

---

## 9. Mechanical / Enclosure

- **Board:** **23 × 40 mm** (Rev B), 2-layer, 1.6 mm FR4, ENIG. (Back silk reads
  15/16" × 1 9/16"; 23 mm is actually 0.906" ≈ 29/32" — cosmetic nit only.)
- **Enclosure:** Zulkit IP65 ABS, 63 × 58 × 35 mm external.
- **Mounting:** two M3 (3.2 mm NPTH) holes on a diagonal; PCB on standoffs.
- **Wall penetration:** the STEMMA cable exits to the external sensor — fit a grommet
  (basement) or a sealed cable gland (to preserve IP65) at the penetration.

> Enclosure fit (resolved 2026-07-04): **USB-C faces the box interior** (§9.2), and
> the 38 mm span is the clear distance between the cover-screw corner pillars — the
> board is deliberately registered against them (pillars = lateral stop), landing
> its right edge ≈3.7 mm off the wall (§9.2 geometry). No interference gate remains.

### 9.1 Board Layout Summary (Rev C, reviewed 2026-07-05)

- **Outline:** 23.00 × 38.00 mm, 2 mm 45° chamfers on all four corners. The 38.00 mm
  length equals the inter-pillar span nominally (zero clearance by design); the
  chamfers provide relief at the pillar arcs. **Field-fit accepted** — verify at
  assembly; file an edge if an interference fit shows up (three boards per set).
- **Stackup / pours:** GND zones on both F.Cu and B.Cu, thermal-relief pad
  connections, **40 GND stitching vias** (38× 0.7/0.3 mm, 2× 0.6/0.3 mm). GND is
  pour-only — no GND tracks.
- **Routing:** all signals on F.Cu; no layer changes on any signal; zero vias in
  either I²C path. I²C 0.4 mm; main 3V3 run (U1 → C1 → PH1.2) 1.0 mm — C1 sits in
  the feed path; 3V3 test-point spur 0.3 mm perimeter run (electrically irrelevant
  at µA load).
- **Sensor interface (PH1):** 1×4 right-angle header, body flush with the left board
  edge, pins overhang ~6 mm into the cavity. Net order 1=GND, 2=+3V3, 3=SDA, 4=SCL —
  **1:1 with the STEMMA wire lay** (black, red, blue, yellow), so a straight-lay
  crimp is correct by construction.
- **D9/D10 = NPTH:** the two unused XIAO pads adjacent to the I²C escape are
  non-plated 1.02 mm holes (socket pins pass through, no copper). Both SDA and SCL
  route through the D10–D9 gap: hole-edge-to-copper 0.25 mm (SDA) / 0.27 mm (SCL),
  0.20 mm track-to-track — the geometric optimum for two 0.4 mm lines in the
  1.52 mm gap. Accepted: comfortably fabricable (OSH Park drill positional
  tolerance is better than ±3 mil per their docs), but note it clears KiCad's
  default 0.25 mm hole-clearance constraint by only ~2.5 µm — do not nudge these
  verticals.
- **Fab-rule compliance (OSH Park current published rules):** 2-layer minimums are
  6 mil trace / 6 mil clearance / 10 mil (0.254 mm) drill / 5 mil (0.127 mm)
  annular ring. Board actuals: 0.30 mm min drill ✔, 0.20 mm via annular on 38 vias
  (7.9 mil ✔), 0.15 mm on 2 vias (5.9 mil ✔, tightest margin on the board),
  0.30 mm min track ✔, 0.20 mm min clearance ✔, copper-to-edge ≥ 0.50 mm ✔.
- **LED silk:** '+' / '−' polarity marks placed clear of the pad mask openings
  (2026-07-05 adjustment); '−' marks pad 1 (cathode/GND), '+' marks pad 2 (anode).
  Note the rectangular pad is on the **anode** — inverted from the usual
  square-pad-marks-cathode convention; the silk marks are authoritative.
- **Footprint maintenance hazard:** U1 references the `UPS_Custom` library (not in
  the project configuration) and LED/R1/C1 are local overrides of their library
  copies. A future "Update Footprints from Library" or schematic re-import can
  silently revert these. Action: commit the modified footprints into the
  project-local `UPS_Custom` library so overrides are version-controlled.
- **Hygiene note:** several track endpoints terminate inside pad copper rather than
  on pad centers (R1.2, C1, PH1 entries, LED.2 pass-through overshoot). Connected
  per KiCad (0 unconnected pads); harmless, but re-anchor if those areas are ever
  re-routed.

### 9.2 Enclosure Integration (from mechanical drawing, 2026-07-04)

Read from a dimensioned drawing/render, not a parsed file — confidence flagged
per item.

- **Placement (high confidence):** board (23.00 × 38.00 — matches edge cuts) stands
  against the **right interior wall**; PH1 pins face the cavity; LED and
  H2 at top. **USB-C faces LEFT, into the box interior** — closes the overhang
  question; the power cable runs fully inside the box from penetration to plug, no
  bulkhead coupler needed.
- **15 mm penetration — resolved (2026-07-04):** grommeted through-hole in the
  **back/bottom panel**; **both** the USB-C power cable and the STEMMA harness
  route through it into the box (single shared penetration — supersedes the earlier
  behind-the-breakout two-hole recommendation). Pass check: bare hole 15 mm >
  ~12.35 mm USB-C overmold ✔ (1.3 mm radial margin). **Assembly-sequence catch:** a
  seated grommet's ID will be well under 12.35 mm, so either feed the USB plug
  through the bare hole *before* seating the grommet, or use a **split/slit
  grommet** closed around both cables after routing (the ~6 × 4 mm JST-SH connector
  passes anything). IP65 ends at this hole regardless — accepted for the basement.
- **Box orientation (2026-07-04):** the box stands on a narrow (35 mm) edge face,
  clear cover vertical facing out — LED visible; cables exit the rear horizontally
  (leave rear clearance for the USB cable bend radius). Constraint: the sensor face
  carries the breakout on 8 mm standoffs so it cannot be the resting face — of the
  remaining orientations make it a **vertical side, not the top**: the top face
  sits in the box's own convective plume (~0.3–0.5 W XIAO dissipation) and collects
  dust on the PTFE membrane; a vertical membrane sheds dust and samples
  undisturbed air.
- **Sensor mount (moderate confidence on datums):** SHT45 breakout on the exterior
  **left side wall**, 8 mm standoffs (inside the §2 8–10 mm band), breakout
  ~17.7 × 25.5 mm, corner holes, located ~19 mm up / 3.5 mm in.
- **STEMMA reach — revised for the shared-grommet route** (every leg an estimate;
  bend radii eat the low margin fast):

  ```
  Interior: PH1 → back-panel grommet:            ~35–45 mm
  Exterior: grommet → across back to side edge:  ~25–40 mm
  Wrap around edge + up side face to connector:  ~25–35 mm
  ────────────────────────────────────────────────────────
  Needed ~85–120 mm   vs. 150 mm cable  →  30–65 mm margin
  ```

  Nominally fits — **verify with the physical cable before drilling**. Fallback
  (stock verified 2026-07-04): QT-to-QT cables come in 200 mm (PID 4401) and
  300 mm (PID 5384); note **no 150 mm QT-to-QT exists** — the BOM's 4397 is the
  150 mm QT-to-male-headers variant, and the TB end is cut and stripped in any
  case. At 200 mm the bus grows to ≈240 mm → adds only ~3 pF (~50 mm × ~60 pF/m
  est.) against the 118 pF §5 ceiling — no electrical concern at any length.
- **USB-C plug clearance — bench gate:** the 33 mm hole-center-to-board run must
  absorb the plug overmold **plus** a 90° bend (cable arrives perpendicular to the
  insertion axis). Straight overmolds run roughly 30–40 mm with strain relief
  (estimate — varies widely by cable; not a verified spec), so 33 mm is marginal.
  **Use a right-angle USB-C plug or adapter** — removes the length question and the
  lever-arm strain on the XIAO's soldered SMT connector (a known failure point).
- **Corner pillars — resolved (2026-07-04):** the 38 mm span is the clear distance
  between the internal corner pillars for the cover screws, and the board is
  **deliberately registered against them** — pillars as lateral stop. Landing
  position (assumptions first: quarter-round pillars of radius
  r = (52 − 38)/2 = 7 mm molded into the corners — cross-section not verified; and
  board vertically centered, (52 − 40.06)/2 = 5.97 mm to each wall):

  ```
  Pillar arc: x² + y² = r²   (origin at inner corner; x = dist from right wall)
  y = 5.97 mm → x = √(7² − 5.97²) = √(49.00 − 35.64) = √13.36 = 3.66 mm
  ```

  → board right edge stops ≈3.7 mm off the right wall. **Rev C disposition
  (2026-07-05):** board length trimmed to exactly 38.00 mm; the 2 mm corner
  chamfers seat back into the pillar-arc space, so the fit is not critical for the
  USB-C cable run. Zero nominal clearance is accepted as a **field fit** — verify
  at assembly, file an edge if needed. Right-angle USB-C plug recommendation
  stands.
- **Antenna (given this layout):** board + GND pours on the right wall, sensor on
  the left exterior → mount the U.FL antenna against the **left half of the lid**,
  vertical, maximizing distance from pours, terminal wiring, and the USB run. Mate
  the U.FL once and secure it (Kapton or a silicone dab — connector is rated on the
  order of ~30 mating cycles); cross the pigtail and STEMMA at 90° if they meet.
- **Assembly reliability notes:** terminate the cut STEMMA end in a **crimped 1×4
  0.1″ female housing** onto PH1 — straight lay (black, red, blue, yellow → pins
  1–4), tug-test each crimp. Friction fit replaces the old screw clamp: add a
  retention measure (lacing to the harness or a small adhesive dab on the housing)
  since the box is sealed after assembly. Keep the XIAO socketed (fleet-proven for
  module swaps); seat fully. The red LED in renders is KiCad's generic 3D model —
  the physical part is the green LTL-4231N (§6).

### 9.3 Display & Light-Sensor Add-On — Integration (2026-07-18)

Decisions and open items for the daisy-chain add-on. **The Rev C PCB is unchanged**;
this is purely bus routing + mounting. Confidence flagged per item, per §9.2 style.

- **VEML7700 mount — decided (updated 2026-07-20): top of the enclosure**, using the
  **right-angle** part (5378) flat on the top face, so the sensing window sits
  near-vertical and looks *out into the room* (the part senses parallel to its PCB).
  The rejected alternative — back of the enclosure looking up — would stare at the dark
  underside of the shelf above and defeat the whole point. The near-vertical window
  still sheds settling dust (the argument that ruled out an up-facing mount). The node
  sits on a shelf in a **recessed corner**; light arrives from the open side, so aim
  the window at the open room direction. *Datums TBD — no dimensioned mount yet.*
- **VEML7700 is a threshold, not a photometer:** a shadowed corner lowers absolute lux
  with the lights on but not the on/off *ratio* (off ≈ 0), and the part resolves down
  into the thousandths-of-a-lux range, so "on" still reads clearly. Set the wake
  threshold empirically in place (§10.1); allow dust margin + an annual re-check.
- **OLED mount — decided (2026-07-20): flush on the inside of the existing clear
  cover** (the 938's ~35 × 35 mm board will not fit beside the XIAO board inside the
  63 × 58 × 35 mm box, so lid-mount was the surviving option). Window/orientation datums
  **TBD**. Keep the **green status LED out of the VEML7700's field** — an in-view LED
  raises the lux floor. **Self-glow, accepted and bounded:** with the panel behind the
  cover and the lux sensor on top, the OLED may be the *brightest source in the room*,
  so its own glow/reflections could hold the lux gate above threshold. Rev 2.1's
  **max-on probe** (§10.2) makes the resulting display-keeps-itself-awake latch
  physically impossible regardless of geometry — worst case is a forced blank + re-check
  every 30 min — so the mount does not have to guarantee optical isolation; the tuning
  procedure (§11) still takes a lights-off/display-on reading to set the threshold
  above the self-glow floor.
- **Thermal separation — carry forward §9.2 intent:** the OLED dissipates ~25–40 mA of
  heat; keep it well away from the external SHT45 cluster (different face / the lid) so it
  cannot bias the RH/T the whole design isolates for. The VEML7700's ~0.5 mA is
  thermally irrelevant.
- **Chain routing & penetration — open:** the bus now has two more legs (SHT45→OLED,
  OLED→VEML7700 — order electrically arbitrary, set by physical convenience). Each
  external board needs its QT cable routed to it; plan the added runs alongside the
  existing single back-panel grommet (§9.2), or add penetrations. Verify reach with the
  physical cable before drilling; 200/300 mm QT-to-QT (4401/5384) are the stock lengths.
  Added bus capacitance from two short cables + two devices is a few pF against the §9.2
  ~118 pF ceiling — no electrical concern.

---

## 10. Firmware

- **Platform:** ESPHome (native API; commented MQTT alternative). Deliverable:
  `basement-th-node.yaml` (**Rev 2.1**, 2026-07-20 — §10.2; Rev 2.0 policy below is
  unchanged).
- **I²C:** `sda: GPIO6`, `scl: GPIO7`, `frequency: 100000`, `timeout: 50ms`.
- **Sensor:** `sht4x` platform, address `0x44`, `precision: High` (→ 0xFD
  high-repeatability read, 0.08 %RH noise), `update_interval: 10s`.

**Sensor / control-path policy (deliberate):**
- **RAW is the control + stall source.** The `sht4x` `humidity:` sub-sensor
  (`id: basement_rh`, name "Basement Humidity") is published with **no smoothing**
  (only `filter_out: nan`). HA's 49/46 band control and the 0.3 %/hr stall detector
  read this entity.
- **Smoothing is dashboard-only.** A separate entity
  (`id: basement_rh_smoothed`, "Basement Humidity (Smoothed)") mirrors the raw value
  through a **median-5** filter for cosmetic spike rejection. It must **not** be
  consumed by control or stall logic. Since Rev 2.1 it is a `platform: copy` sensor
  (event-driven off each real SHT45 publish — phase-locked); the Rev 2.0 free-running
  template timer could occasionally double-sample or skip a reading into the median
  window. (Rationale: median rejects single in-range
  spikes without smearing; a mean would smear. Feeding a sliding average into the
  60-min slope regression would inject autocorrelation and overstate confidence —
  hence raw for the stall detector.)
- **Why raw is safe for control:** hysteresis (±0.8 %RH) and the anti-short-cycle
  lockout already dominate the ~0.027 %RH (1σ) high-rep noise; extra filtering on the
  control path only adds lag.
- **Dew point:** native `dew_point` component (`id: basement_dewpoint`) computed from
  the **raw** temp + raw RH, °C (convert in HA if °F preferred). Replaces the earlier
  Magnus lambda.
- **Cadence justification:** SHT4x has no ≥1 Hz self-heating floor; at 10 s / high-rep
  the self-heating rise is ~0.0003 °C (die pad unsoldered per §5.3). 10 s is well above
  the ~4 s physical response and yields ~360 samples per 60-min stall window.
- **Status LED:** GPIO20, 0.5 Hz heartbeat blip when healthy, 5 Hz strobe on fault,
  plus a `problem` binary_sensor ("Basement Sensor Fault") for HA alerting.
- **Hardening:** WiFi reboot-on-loss + AP/captive-portal fallback; `api reboot_timeout:
  0s` (HA outages don't stop sampling); I²C stale-data watchdog (60 s) + bus-stall
  auto-recovery reboot (120 s). Logging over native USB Serial/JTAG (frees GPIO20).
- **RH thresholding** (49/46 band, stall detection) lives in HA logic — there is no
  hardware alert path on this design.

**Validation status (Rev 2.0, esphome 2026.6.4):** passed the full
`esp-firmware-validation` gate — `esphome config` valid; standalone
`g++ -std=c++17 -Wall` on all lambda bodies clean; real `esphome compile` linked to a
working ESP32-C3 image (`src/main.cpp.o` built, **0 errors**, RAM 12.7 %, Flash 51.5 %).
The `sht4x` repeatability-exposure question was resolved from component source, not
memory: `precision:` exists and defaults to `High`. Two portability fixes applied:
`std::isnan` (not bare `isnan`) and a slash-free `friendly_name` (avoids a 2026.7.0
hard error).
> Re-validate if the deployed ESPHome version differs from 2026.6.4.

### 10.1 Local Display + Auto-Blank (2026-07-18, validated 2026-07-18)

> **Amended by Rev 2.1 (§10.2, 2026-07-20):** the wake threshold, blank delay, and
> contrast are now HA-tunable (mirrored to persisted globals); burn-in mitigations 2
> (dim) and 4 (pixel-shift) are implemented; the on-node band now survives node
> reboots; and a **max-on probe** bounds OLED self-glow latch-up. This section stands
> as the 2026-07-18 design record.

Merged into `basement-th-node.yaml` and **through the full `esp-firmware-validation`
gate**: `esphome config` valid; standalone `g++ -std=c++17 -Wall -Wformat` on the new
lambda bodies clean; real `esphome compile` linked a working ESP32-C3 image
(`main.cpp.obj`, **0 errors**, full image, RAM 32.3 %, Flash 53.0 %) on esphome 2026.7.0.
Uses `std::isnan` (matching the node convention), not bare `isnan`. **Re-validate on the
deployed 2026.6.4** — schema for these components is stable, but the version differs.
Presentation-only: the OLED and the lux logic **must not** appear in any control or stall
path (same rule as the smoothed RH entity).

- **Display driver:** ESPHome `ssd1306_i2c`, `model: "SSD1306 128x64"` — **not** SH1106
  (the 938 is SSD1306; choosing SH1106 gives a shifted/garbled raster). Address `0x3D`
  (verify per §5); `reset_pin` omitted (938 auto-resets). I²C stays at 100 kHz.
- **Light sensor:** ESPHome `veml7700` platform, address `0x10`; publish lux as a sensor
  for thresholding + HA visibility.
- **Auto-blank (the point of the light sensor):** the OLED sleeps over I²C
  (`display.turn_off` / `turn_on`, the SSD1306 sleep command) — no power switch and no
  board button (the C3 has no touch peripheral anyway). Implemented as a single **wake
  ≥ 12 lx** threshold that re-arms a **3-min restart-mode blank timer** each reading (the
  timeout supplies the hysteresis — no separate low threshold). 12 lx is a **starting**
  value; tune in place from three readings (lights-on / night-dark / midday daylight-leak,
  §9.3). If the midday leak rivals the sparse lights-on level, switch to a rate-of-change
  (switch-flip) trigger. The basement is dark/empty most of the time, so duty cycle — and
  thus OLED wear — drops hard; this dominates panel lifetime.
- **Burn-in mitigation (belt-and-suspenders; OLED wear ∝ lit-pixel·hours):**
  1. **Black background, white glyphs** — fewest lit pixels; never invert to a white
     background (that lights the whole panel and is the *worst* case, not a fix).
  2. **Dim it** — low SSD1306 contrast (0x81); wear scales hard with luminance
     (~2× life from halving brightness on representative panels).
  3. **Rotate pages** temp / RH / dew-point on a timer; keep static labels minimal
     (fixed chrome/borders are the classic ghost).
  4. **Pixel-shift** the whole layout a few px every few minutes so glyph edges don't
     sit on fixed pixels.
  Auto-blank (duty cycle) dominates all of these; the rest are cheap insurance.
- **Content & layout:** **two 3-row pages**, `font_lg` Roboto **18 px**, left margin x=6,
  rows y=0/22/44 (top/bottom limits + spacing from the battery-bank v7 layout; confirm the
  bottom row clears 64 px on the panel). Page 1 = Temp / RH / Dew point in **°F** (converted
  in-lambda; the sensor path stays °C). Page 2 = RH-vs-band / condensation spread (T−DP) /
  sensor health. The band is computed **on-node** from the live HA thresholds
  `input_number.dehumidifier_rh_on/off_threshold` (imported via `platform: homeassistant`),
  so it keeps working through HA outages once received; shows `RH band --` only before HA
  first reports. Pages auto-cycle every 15 s (no button). Display formatting only — no new
  control math.

### 10.2 Rev 2.1 — Display Resilience + HA-Tunable Parameters (2026-07-20, validated 2026-07-20)

Motivated by a full-system review: the Rev 2.0 band readout survived *HA-only* outages
but not the most likely extended outage. Chain: WiFi drops → `reboot_timeout: 15min`
reboots the node → the `homeassistant`-platform threshold imports re-initialize to NaN
and cannot repopulate with the API unreachable → page 2 shows `RH band --` from ~15 min
into the outage until WiFi returns. Rev 2.1 closes that plus the §10.1 mitigations that
were documented but not implemented. Changes (all presentation/diagnostic path — the
RAW-RH control policy is untouched):

- **Band persistence:** both RH threshold imports mirror into `restore_value` globals
  (NVS); page 2 reads the **globals**, so the band readout survives node reboots of any
  cause (watchdog, OTA, power blip, WiFi-outage reboot cycle). `RH band --` now appears
  only before HA has *ever* reported. NVS wear is negligible (thresholds change rarely).
- **HA-tunable display parameters, same mirror pattern** (HA `input_number` = single
  source of truth → import → persisted global; firmware defaults apply until HA first
  reports and on a factory-fresh flash): `basement_display_lux_wake` (default 12 lx),
  `basement_display_blank_min` (default 3 min), `basement_display_contrast_pct`
  (default 30 %). Threshold tuning is now sliders in the mounted position — no
  edit → validate → OTA cycle per iteration. HA-side entries ship as
  `basement-th-node-input-numbers.yaml` (merge into the existing `input_number:` block —
  a second top-level key silently overwrites).
- **Max-on probe (self-latch breaker), 30 min:** started once per display off→on
  transition (never reset by routine re-arms). It force-blanks the panel; with the OLED
  dark it emits nothing, so the next 2 s lux reading is *true ambient* — genuine light
  re-wakes the display within ~2 s (a barely visible blip), OLED self-glow/reflection
  cannot. Makes the display-keeps-itself-awake latch impossible regardless of mounting
  geometry (§9.3).
- **Burn-in mitigations implemented:** static `contrast: 30%` + runtime
  `set_contrast()` from HA (floor 15 % — SSD1306 stacks are reported to clamp below
  ~15 % with no visible change); **pixel-shift** wear-leveling walks the whole layout
  through 8 positions (X 0–3 px, Y 0–1 px) every 5 min — Y capped at +1 px because the
  bottom row (y=44, 18 px font) nominally ends at pixel 63. Note: the bottom-row
  strings ("Dew …", "Sensor OK/FAULT") contain no descenders; if bottom-row content
  ever gains g/j/p/q/y, re-check clipping on the glass.
- **I²C bus-clear before the recovery reboot (best-effort):** 9 SCL pulses
  (open-drain, ~100 kHz, direct IDF gpio calls) with SDA released, immediately before
  the watchdog reboot — frees a slave stuck mid-byte holding SDA low, which an ESP
  reboot alone cannot (peripherals aren't power-cycled). Post-clear pin-matrix state is
  irrelevant: the node reboots immediately. Does **not** help a truly latched device
  (e.g. OLED charge pump) — that remains the §12.1 item 3 hardware case, which the
  three-device chain has made strictly stronger.
- **Diagnostics + small fixes:** `debug:` free-heap sensor (slow-leak drift visible in
  HA before it becomes a mystery reboot); heartbeat blip widened 100 → 200 ms (a 100 ms
  poll could occasionally skip a 100 ms window); smoothed-RH entity moved to
  `platform: copy` (§10 policy bullet).

**Validation status (Rev 2.1, esphome 2026.6.4 — the deployed version):** passed the
full `esp-firmware-validation` gate — `esphome config` valid; codegen id-resolution
confirmed for every new global/script/call; standalone `g++ -std=c++17 -Wall -Wformat`
on all new/changed lambda bodies clean; real `esphome compile` → `src/main.cpp.o` built
with **0 errors** and the full link completed (`firmware.elf` + ESP32-C3 image,
**RAM 13.1 %, Flash 53.3 %**). The direct IDF gpio calls in the bus-clear compiled
without shims. (RAM reads lower than the 32.3 % recorded on 2026.7.0 in §10.1 —
attributed to version-to-version accounting differences, cause not investigated.) The
HA `input_number` snippet passed layered parse validation (YAML parse + duplicate-key
detection + schema lint, strict) — **parse-clean**; run `hass --script check_config` on
the HA host before restart, per the HA validator's assurance levels.

---

## 11. Pre-Fabrication Checklist

- [x] `ALERT` silk on D3 removed; D3 net confirmed unrouted (verified 2026-07-03: no
      ALERT text anywhere; D3 pad has no net, no copper).
- [x] `DQ` silk on GPIO10 removed; GPIO10 confirmed unused (verified: no DQ text;
      D10 pad no net).
- [x] LED drive chain verified from pad netlist: GPIO20 → R1 → anode; cathode → GND.
- [x] No I²C pull-up footprints present (verified Rev C: only U1, LED, R1, C1, PH1,
      2 test points, 2 mounting holes on board).
- [x] Sensor interface nets at PH1 verified from netlist (2026-07-05): 1=GND,
      2=+3V3, 3=SDA, 4=SCL — matches STEMMA lay 1:1.
- [x] Enclosure internal length clears the 38 mm Rev C board + standoffs (board now
      matches the inter-pillar span nominally; see field-fit gate below).
- [x] Penetration architecture resolved (2026-07-04): single 15 mm grommeted hole
      in the back/bottom panel, shared by the USB-C cable and STEMMA harness (§9.2).
- [ ] Grommet selection: split/slit type, or plug-first sequencing (seat the
      grommet after the USB plug is through the bare hole) — §9.2.
- [ ] Verify the 150 mm STEMMA reaches the wrap-around route with dressing slack
      **before drilling**; fallbacks: 200/300 mm QT-to-QT (PID 4401/5384), TB end
      cut-and-stripped (§9.2).
- [ ] Final orientation: sensor face on a vertical side, not the top (§9.2 —
      thermal plume + dust on the PTFE membrane).
- [x] USB-C overhang direction resolved (mechanical drawing 2026-07-04): connector
      faces the box **interior**; power cable run fully internal (§9.2).
- [x] 38 mm span identified (2026-07-04): clear distance between cover-screw corner
      pillars; board deliberately registered against them, right edge ≈3.7 mm off
      the wall (§9.2 geometry; r = 7 mm pillar assumption affects only that figure).
- [ ] Bench-fit the USB-C plug in the ≈29–33 mm run (shrinks with pillar-registered
      board position, §9.2); procure a right-angle plug or adapter — now strongly
      advised rather than optional.
- [ ] U.FL antenna mated once and secured (Kapton/silicone); antenna mounted on the
      left half of the lid (§9.2).
- [ ] STEMMA conductors NOT tinned; fold-back or 0.14 mm² ferrules; tug-test (§9.2).
- [x] Firmware: confirm the boot-time stale-watchdog hole fix (`last_read_ms == 0`
      guard) is present in the deployed Rev 2.x build — **verified present in the
      Rev 2.1 source (2026-07-20 review)**; the guard also makes the recovery reboot
      one-shot per failure episode (no boot loop, no safe-mode trip).
- [x] Firmware: `wifi_signal` (RSSI) + uptime sensors (Rev 2.0) and free-heap
      diagnostic (**added Rev 2.1**, `debug:` component) all present.
- [ ] HA: baseline RSSI so antenna/connector degradation shows as drift, not as a
      surprise outage.
- [ ] Post-assembly inspection: no solder bridges from XIAO pads D8/GPIO20/3V3 onto
      the masked SDA/SCL traces in the pad row (D9/D10 are NPTH — no solder there;
      §9.1 clearances).
- [ ] Modified footprints committed to project-local library (§9.1 maintenance note).
- [ ] STEMMA cable color mapping confirmed against the actual cable before crimping
      (Adafruit standard: black=GND, red=VIN, blue=SDA, yellow=SCL). PH1 pin order
      now matches this lay 1:1 (2026-07-05), so a straight-lay crimp is correct —
      but a swapped power pair is still not silent; verify colors once.
- [ ] Field-fit gate: confirm the 38.00 mm board seats between the cover-screw
      pillars (zero nominal clearance, chamfers provide arc relief); file an edge
      if interference shows up.
- [x] Final OSH Park DRC pass against current rule set (verified 2026-07-03: current
      published minimums 6/6 mil, 0.254 mm drill, 0.127 mm annular — all pass, §9.1).

**Display + light-sensor add-on (2026-07-18):**

- [ ] i2c-scan the assembled chain: confirm 0x44 (SHT45), **0x3D** (OLED, expected — 0x3C
      only if the ADDR jumper is bridged), 0x10 (VEML7700) — no collision, addresses match
      firmware (§5).
- [ ] Confirm the 938 OLED's onboard I²C pull-up value; re-check R_eff if not ~10 K
      (§5 combined-pull-up math assumes ~10 K).
- [ ] Confirm the 938 SPI/I²C jumpers are left at I²C (ships I²C by default — do not cut).
- [ ] Tune the lux **wake threshold** in the final mounted position — now a slider
      (`input_number.basement_display_lux_wake`, no reflash; §10.2) — from **four**
      readings: lights-on / night-dark / midday leak / **lights-off with the display
      forced on** (sets the threshold above the OLED self-glow floor; the §10.2 max-on
      probe bounds the worst case even if this is misjudged). The blank timer supplies
      the hysteresis. Confirm the status LED is out of the VEML7700's field (§9.3).
- [ ] Execute the decided mounts (§9.3, 2026-07-20): VEML7700 flat on the enclosure
      **top** (window looking out into the room), OLED **flush inside the clear
      cover**; dimension the datums/window; keep the OLED off the SHT45 face for
      thermal separation (§9.3).
- [ ] HA: merge the three `basement_display_*` entries from
      `basement-th-node-input-numbers.yaml` into the **existing** `input_number:`
      block (never as a second top-level key — silent overwrite), then run
      `hass --script check_config` before restart (§10.2).
- [ ] Verify chain cable lengths against the physical routes before drilling any added
      penetration (§9.3); QT-to-QT stock 200/300 mm (4401/5384).
- [ ] Populate the optional 10 µF X7R at C1/PH1 given the OLED switching load
      (§7, §6.1, §12.1 item 5).
- [x] Display firmware through the `esp-firmware-validation` gate — **passed 2026-07-18**
      (esphome 2026.7.0: config valid, g++ lambda check clean, `esphome compile` linked a
      full image, `main.cpp.obj` 0 errors, §10.1). ~~Re-run on the deployed 2026.6.4.~~
      **Closed by Rev 2.1 (2026-07-20): full gate passed on the deployed 2026.6.4**
      (`src/main.cpp.o` 0 errors, full image, RAM 13.1 % / Flash 53.3 %, §10.2).

---

## 12. Assumptions & Open Items

- **Standalone air sensor** — assumed no electrical connection to the battery bank.
  If any node touches the pack, revisit grounding before mains-powering.
- **XIAO CC-resistor population** unconfirmed from schematic — mitigated by A→C cable
  or bench power-up test (§7).
- **Shelly accuracy** unpublished — comparison rests on cadence + verified SHT45 spec.
- **Enclosure internal dimensions** resolved (2026-07-04): 52 mm clear internal
  span, 38 mm between cover-screw corner pillars; board registers against the
  pillars by design (§9.2). Residual assumption: pillar cross-section taken as
  quarter-round r = 7 mm — affects only the ≈3.7 mm wall-offset figure.
- **Wall-penetration method** — RESOLVED (2026-07-04): **single 15 mm grommeted
  hole in the back/bottom panel**, shared by the USB-C power cable and the STEMMA
  harness; USB-C faces the interior so no bulkhead coupler is needed. Remaining
  execution details: split/slit grommet vs plug-first sequencing, and STEMMA length
  verification on the wrap-around route (§9.2, §11).
- **RESOLVED:** ESPHome `sht4x` repeatability exposure — confirmed `precision:` key
  (default High) maps to the 0xFD high-rep command (component source).
- **Display/light-sensor add-on — RESOLVED (2026-07-18):** OLED address settled on
  **0x3D** (938 ADDR-open default; shipped firmware uses it; scan still confirms hardware,
  §5); display firmware **validated** through the full gate (§10.1, checklist §11).
- **Display/light-sensor add-on — still open:** (a) 938 OLED pull-up value unconfirmed
  (assumed ~10 K, §5); (c) mounts **decided 2026-07-20** — VEML7700 on the enclosure top,
  OLED flush inside the clear cover (§9.3) — but datums/window not yet dimensioned;
  (d) chain routing/penetrations not yet planned; (e) lux wake threshold now
  **runtime-tunable from HA** (Rev 2.1, §10.2) but not yet tuned in place (four-reading
  procedure, §11). None of these touch
  the Rev C PCB — the board can fab as-is, independent of the add-on.

### 12.1 Rev C Candidate Changes (logged 2026-07-04 — none justify a respin)

1. **Series 100–220 Ω in SDA and SCL** between U1 and PH1 — ESD injection limiting
   and edge damping for the externally-routed cable. Cost check: rise time is still
   set by the 10 K pull-up (220 Ω ≪ 10 K); added V_OL error =
   0.33 mA × 220 Ω = **73 mV**, negligible against the ~1.5 V V_IL threshold.
2. **TVS/ESD array** on SDA/SCL/3V3 at PH1 — the header faces a human-handled
   external cable.
3. **GPIO-switched sensor power** (high-side P-FET or load switch on the PH1 3V3
   feed; D3/GPIO5 is free and unrouted) — lets firmware hard power-cycle the SHT45
   as the final rung of bus recovery (retry → soft reset → power-cycle → reboot).
   Largest available I²C robustness gain: an ESP reboot alone does **not** cycle
   the sensor rail.
4. **Upsize the two 0.6/0.3 mm vias to 0.7/0.3 mm** — annular margin 5.9 → 7.9 mil.
5. *(Optional)* **10 µF MLCC in parallel at C1/PH1** — see §6.1; earns its place if the
   SHT45 heater is ever enabled **or** the 938 OLED add-on is built (its charge-pump
   switching load downstream of C1 makes the bulk cap cheap insurance — §7).

---

## 13. Revision History

| Date | Change |
|---|---|
| 2026-07-20 | **Firmware Rev 2.1 (display resilience + HA-tunable parameters) + mount decisions.** New §10.2. Review finding closed: WiFi outage → 15-min reboot cycle → `homeassistant`-imported thresholds NaN → band readout dead for the outage's duration; fixed by mirroring both RH thresholds into `restore_value` globals (page 2 reads the globals — band now survives node reboots of any cause). Display parameters (lux wake / blank min / contrast %) moved to HA `input_number`s (source of truth) mirrored to persisted globals with firmware defaults 12 lx / 3 min / 30 %; HA-side entries in `basement-th-node-input-numbers.yaml` (parse-validated; merge into existing `input_number:` block). §10.1 mitigations implemented: contrast dim (30 % default, runtime `set_contrast`, 15 % floor) + 8-position pixel-shift (Y capped +1 px for the y=44 row). New **30-min max-on probe** bounds OLED self-glow latch-up (§9.3, §10.2). Also: smoothed-RH entity → `platform: copy` (phase-locked); best-effort 9-pulse SCL bus-clear before the recovery reboot; free-heap diagnostic; heartbeat blip 100→200 ms. Validated on the **deployed 2026.6.4**: full gate + full link, `src/main.cpp.o` 0 errors, RAM 13.1 % / Flash 53.3 % (closes the §11 re-validate item). Mounts decided (§9.3): VEML7700 flat on the **enclosure top** (window out into the room; back-mount looking up rejected — dark shelf underside), OLED **flush inside the clear cover**; datums still TBD. §11: stale-watchdog-guard + diagnostics items closed; lux tuning is now a four-reading slider procedure (adds lights-off/display-on self-glow reading). |
| 2026-07-18 | **Reconciliation after the add-on firmware was built + validated.** OLED address corrected **0x3C → 0x3D** throughout (§2 diagram, §3 BOM, §5, §10.1, §11) — the 938 ships ADDR-open = 0x3D and the shipped firmware + the battery-bank board's 938 both use it (0x3C only if the jumper is bridged; scan still confirms). §10.1 marked **validated** (esphome 2026.7.0: config valid, g++ lambda check clean, `esphome compile` → full image, `main.cpp.obj` 0 errors, RAM 32.3 % / Flash 53.0 %); display lambdas use `std::isnan` (node convention), not bare `isnan`; re-validate on deployed 2026.6.4. §10.1 content/auto-blank updated to the shipped design (two 3-row pages, `font_lg` 18 px, rows y=0/22/44; °F on-glass; on-node band from HA `input_number.dehumidifier_rh_on/off_threshold`; wake ≥ 12 lx + 3-min restart-timer blank). §11/§12: address + validation items closed; still open — 938 pull-up value, OLED/VEML7700 mounts, chain routing, 12 lx tuning. |
| 2026-07-18 | **Display + ambient-light add-on (STEMMA QT daisy-chain), no PCB change.** Added Adafruit 938 1.3″ 128×64 OLED (SSD1306, I²C 0x3C/0x3D, ~25–40 mA, dual-QT) and Adafruit 5378 right-angle VEML7700 lux sensor (I²C 0x10 fixed, verified Vishay datasheet; 4.7 K pull-ups; senses parallel to PCB) onto the existing bus by chaining through each breakout's 2nd QT port (§2 diagram, §3 BOM). §5: three-device address map (no collisions, scan to confirm) + combined pull-up math (10 K ‖ ~10 K ‖ 4.7 K ≈ 2.4 K → stiffer/faster bus, 100 kHz keeps margin). §7: OLED current path + cable-drop (~6.8 mV) + budget (~160–170 mA awake worst case vs 700 mA reg); optional 10 µF now justified. New §9.3 (VEML7700 right-angle, room-facing from a recessed corner — decided; OLED lid/external + thermal separation from SHT45 — open) and §10.1 (SSD1306 not SH1106; `veml7700` platform; lux-gated `display.turn_off/on` with hysteresis/debounce; burn-in mitigations: black bg, dim, page-rotate, pixel-shift). Verified this rev: VEML7700 = 0x10 (Vishay), 938 = SSD1306 / default-I²C / dual-QT / ~25–40 mA. Unconfirmed: 938 pull-up value (assumed ~10 K), 938 address 0x3C vs 0x3D (scan). Display firmware not yet through the validation gate. |
| 2026-07-02 | Initial design doc. Board revised to 1"×2". Removed ALERT (D3) and DQ (GPIO10) leftovers. Status LED confirmed on D7/GPIO20. No external I²C pull-ups (breakout 10 K). USB-C brick power. |
| 2026-07-03 | **Rev B layout review (fab-ready).** Board resized to 23 × 40 mm (from 1"×2"); cost ~$7.13/set-of-3. Netlist verified: LED chain (GPIO20→R1→anode, cathode→GND), I²C U1→TB2 with zero vias in signal paths, 3V3 feed U1→C1→TB1. OSH Park compliance verified against **current** rules (0.254 mm drill / 0.127 mm annular — old 13/7 mil figures obsolete): all pass; tightest margin 5.9 mil annular on 2 vias. DRC 0 errors / 0 unconnected / 8 benign warnings. Refdes aligned to board (LED, R1); BOM adds 3V3/GND test points + M3 holes. New §9.1 layout summary; new checklist items (USB overhang direction, pad-row bridge inspection, footprint library commit). |
| 2026-07-04 | **Mechanical integration review** (from dimensioned drawing/render). USB-C direction **resolved**: faces box interior; power cable fully internal; two-penetration architecture replaces the single-gland dilemma. STEMMA reach ~80–90 mm vs 150 mm cable ✔. Right-angle USB-C plug recommended (33 mm run marginal for straight overmolds). **Open interference flag: 38 mm internal span vs 40.06 mm board** — caliper gate. New §6.1 decoupling rationale (series-cap topology corrected: 0.1 µF series 10 µF = 0.099 µF; parallel 10 µF optional, not needed — SHT45 load 0.4 µA avg, 1.08–3.6 V window, heater case passes at 3.9 mV cable drop). New §9.2 enclosure integration + assembly reliability notes (no tinning in screw terminals, U.FL securing, antenna on left lid). New §12.1 Rev C candidates (series R, TVS, GPIO-switched sensor power, via upsize). Fixed leftover R4→R1 refs in §2 diagram and §4 pin table. |
| 2026-07-04 (b) | **Enclosure gates closed** (owner input). 38 mm = clear span between cover-screw corner pillars; board registers against pillars by design → right edge ≈3.7 mm off wall (quarter-round r=7 mm assumption); USB run shrinks to ≈29 mm → right-angle plug now strongly advised. 15 mm hole = shared grommet, back/bottom panel, passes USB-C cable + STEMMA harness (supersedes two-hole plan); split-grommet / plug-first sequencing noted. STEMMA reach recomputed for wrap-around route: ~85–120 mm needed vs 150 mm — verify physically; 200/300 mm QT-to-QT fallbacks confirmed in stock (4401/5384; no 150 mm QT-to-QT exists — 4397 is the male-header variant). Box orientation: stands on narrow edge, cover vertical; sensor face must be a vertical side, not top (thermal plume + dust). |
| 2026-07-05 | **Rev C board (fab-ready).** Board trimmed to 23 × 38 mm with 2 mm corner chamfers — 38 mm inter-pillar registration accepted as field fit (chamfers seat into pillar-arc space). TB1/TB2 terminal blocks replaced by **PH1** 1×4 right-angle header at the left edge; pin order set to STEMMA wire lay (1=GND, 2=+3V3, 3=SDA, 4=SCL) so a straight-lay crimp is correct; termination changes from ferrule-in-screw-terminal to crimped 1×4 0.1″ housing. C1 pads swapped to suit — decoupling remains in the U1 → C1 → PH1 feed path. Both I²C lines route the D10–D9 NPTH gap at 0.25/0.27 mm hole-edge clearance (accepted, documented in §9.1 — do not nudge). LED '+'/'−' silk moved clear of pad mask openings. Vias 41 → 40. I²C on-board lengths now SDA 33.4 / SCL 37.6 mm. Cost ~$6.77/set-of-3. |
| 2026-07-02 | Firmware Rev 2.0 built & validated (esphome 2026.6.4): SHT45 `precision: High`, 10 s, raw humidity for control+stall, median-5 dashboard-only entity, native `dew_point`. Added datasheet-verified repeatability/hysteresis/duration/self-heating specs to §8; resolved the `sht4x` precision-exposure question. `std::isnan` + slash-free `friendly_name` fixes. |
