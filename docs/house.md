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

## Active Projects (reference only — details in respective repos)
- **HA Energy Stack**: InfluxDB 1.x + Grafana, SEM-Meter MQTT pipeline, SPC monitoring
- **Battery Bank Monitor**: 12V/500Ah LiFePO4 emergency backup, INA228 monitoring
- **DIY LiFePO4 UPS**: powers the N100DC host via an 18 V U3V70A boost (fitted
  2026-08-29, EN/FET not installed). V1.20 firmware on ESPHome 2026.9.0
  (2026-09-16). 53.3 Wh; ~128 min [D] at 2.089 A / 26.80 W [M, 2026-08-29].
- **HVAC Performance Baseline**: Longitudinal SPC study since 2021, 102.0 CCF/1k HDD65 efficiency
  (ACIS BDL 2025, rebased 2026-10-10, Navien therms->CCF 2026-10-15; was 100.6, and 90.3 on
  NOAA 6,270 HDD - see `docs/baselines.md`)
- **Dehumidifier Control**: Aprilaire E080; RH band, max-runtime cap, stall detection. Setpoints
  live in the `packages/dehumidifier.yaml` helpers, not here (R10; this line said 49/46 %, 150 min)
- **Basement Sensor Node**: XIAO ESP32-C3 + SHT45 + OLED + VEML7700

