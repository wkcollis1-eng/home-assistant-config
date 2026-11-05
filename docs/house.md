# house and active projects

_Moved verbatim from CLAUDE.md (Home + Active Projects) on 2026-10-25; the pointer left there names this file._

## Home
- 2021 colonial, 2,440 sq ft, Zone 5A
- Annual electricity: 6,730 kWh (baseline 200W, efficient)
- Gas: 787 CCF/year (72.9% heating, 27.1% DHW [D: 212.9 CCF Navien]; was 71.9/28.1% [D]
  until 2026-10-15, which read the Navien therms as CCF)
- Navien NPE-240A2 NG DHW (Bill, 2026-10-21; warranty registration, installed 2021-11-17;
  was "NPE-240S2" here until then), gas range, 120V washer
- Heat & Glo SL-7X-IFT-TG 36" direct-vent NG fireplace, great room, automatic blower (Bill,
  2026-10-23; order S3004842 of 2021-04-19, rating plate not read). Burns: `open_questions.yaml`
- Dehumidifier and computer on Kasa plugs
- 16-CT SEM (Fusion Energy/Sense) whole-home monitor installed June 2026
- Ecobee thermostats (replaced Honeywell T6 Pro, June 2026)
- Water: Connecticut Water, Baker Hill System (PWSID CT0429011), groundwater wells, chlorinated
  [S: 2025 Annual Water Quality Report pp.3,5,7]. All main-meter water passes through a 10" Big
  Blue filter, Pentek NCP-BB, just ahead of the softener, for chlorine and softener resin
  protection (Bill, 2026-11-01). Count: `packages/water_softener.yaml`
- Softener: quoted as "Lantis Pro 10x54 Metered Softener with 16x16 brine tank", to treat iron,
  hardness and manganese, with a separate 4x10 pre carbon filter for chlorine (dealer quote,
  undated, file stamp 2022-04-20; rating plate not read). Lantis is a Blake Water Solutions line
  [S: BWS Lantis City Softener sheet p.1, a different variant]; no BWS page read lists a "Lantis
  Pro". Resin NOT on file, and Bill has no invoice or post-install test (2026-11-01): the quote
  names none and BWS offers "choices of premium grade resins"
  [S: same p.1], with no crosslink figure, so any resin-life figure is [I] for this unit (R16). The
  utility report's data tables give no iron, manganese or hardness [S: 2025 report pp.7-9]. The
  company said the chlorine filter would take resin life from 10-12 years to 25 (Bill, 2026-11-01;
  verbal, no document, so [I]; falsified by this resin failing near 12 years with the filter in).

## Active Projects (reference only — details in respective repos)
- **HA Energy Stack**: InfluxDB 1.x + Grafana, SEM-Meter MQTT pipeline, SPC monitoring
- **Battery Bank Monitor**: 12V/500Ah LiFePO4 emergency backup, INA228 monitoring
- **DIY LiFePO4 UPS**: powers the N100DC host via an 18 V U3V70A boost (fitted
  2026-08-29, EN/FET not installed). V1.20 firmware on ESPHome 2026.9.0
  (2026-09-16). 53.3 Wh; ~128 min [D] at 2.089 A / 26.80 W [M, 2026-08-29].
  Monitor board: UPS-Monitor Rev 3 since 2026-11-04, same XIAO ESP32-C3 and
  INA260 (Bill); INA260 ALERT reaches GPIO3 there (P26).
  XB7 (Xfinity gateway, normally on the UPS bus): 12 V DC, safe zone +/-10 %,
  so 13.2 V max (Bill, 2026-11-04); the design set calls +/-10 % inferred.
  UPS wiring since the 10-31 to 11-04 swap: DigiKey 16 AWG, solid PSU to ideal
  diode, stranded for the rest, replacing Amazon stranded 16 AWG; the XB7 and
  ASRock PC leads were not replaced (Bill, 2026-11-04).
- **HVAC Performance Baseline**: Longitudinal SPC study since 2021, 102.0 CCF/1k HDD65 efficiency
  (ACIS BDL 2025, rebased 2026-10-10, Navien therms->CCF 2026-10-15; was 100.6, and 90.3 on
  NOAA 6,270 HDD - see `docs/baselines.md`)
- **Dehumidifier Control**: Aprilaire E080; RH band, max-runtime cap, stall detection. Setpoints
  live in the `packages/dehumidifier.yaml` helpers, not here (R10; this line said 49/46 %, 150 min)
- **Basement Sensor Node**: XIAO ESP32-C3 + SHT45 + OLED + VEML7700
