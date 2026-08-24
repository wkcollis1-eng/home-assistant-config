-- =============================================================================
-- RETIRED 2026-08-22 — DO NOT RE-RUN THIS FILE AS-IS
-- =============================================================================
--
-- All five CQs were DROPPED from InfluxDB on 2026-08-22 and every CREATE
-- statement below is commented out. They are kept only so the definitions are
-- recoverable and so the reasoning is not lost.
--
-- WHY RETIRED. These queries were a SIXTH copy of the SPC appliance constants,
-- recomputing inside InfluxDB a metric Home Assistant already computes. That is
-- the exact drift pipelines.yaml exists to end, and it had already happened:
--
--   1. WRONG METRIC (dehumidifier). The CQ read
--      dehumidifier_current_consumption > 250 — full-run power with the
--      pre-E080 threshold. The HA pipeline moved to the warm-up-excluded
--      steady gate (minutes 10-14 of each run) on 2026-08-07; this never did.
--      Measured 2026-08-21:  CQ 457.4 W  vs  HA 466.4 W  =  -9.0 W, against a
--      2-3 W process sigma.
--
--      The visible symptom: grafana/dashboards/spc_appliances.json plotted the
--      CQ point (457.9) against HA's control limits (460.5-477.7), so the
--      dehumidifier panel showed a permanent BELOW LCL — a false
--      out-of-control produced entirely by the mismatch.
--
--   2. WRONG DAY (all five). GROUP BY time(1d) with no tz() aligns buckets to
--      the UTC epoch, so the bucket stamped 08-21 00:00 UTC actually covered
--      08-20 20:00 -> 08-21 20:00 local. The header below ALREADY said this
--      ("runs at midnight UTC, which is 8PM EDT") and it was never adjusted.
--      Every Grafana SPC point carried four hours of the previous local day.
--
-- WHAT REPLACED THEM. Nothing recomputes anything now. The Grafana panels read
-- the entities HA already writes to InfluxDB:
--     Daily    input_number.<pop>_running_watts_day_1
--     Mean 7d  sensor.<pop>_running_watts_mean_7d
--     UCL/LCL  sensor.<pop>_running_watts_upper / _lower
-- One definition, so the Grafana panels and the HA charts cannot disagree.
--
-- The historical `spc` measurement was NOT deleted — 188 points remain and
-- retention is infinite, so the old output is still queryable for comparison.
--
-- IF YOU EVER RESTORE THESE: fix both defects first. Point the dehumidifier at
-- dehumidifier_power_when_on_steady with no threshold, and add
-- tz('America/New_York') to every GROUP BY — a fixed time(1d, 4h) offset would
-- break at the DST change.
-- =============================================================================

-- =============================================================================
-- SPC Continuous Queries for InfluxDB 1.x
-- =============================================================================
--
-- Purpose: Pre-aggregate daily mean "running watts" for SPC monitoring.
--          Calculates mean power when appliance is above threshold (running state).
--
-- Database: "Home Assistant"
-- Source measurement: "W" (unit_of_measurement from HA)
-- Target measurement: "spc" (new, created by these CQs)
--
-- Installation:
--   influx -database "Home Assistant" < spc_continuous_queries.sql
--
-- Or run each CREATE statement individually in Chronograf/influx CLI.
--
-- Note: CQs run at the END of each GROUP BY interval. A time(1d) CQ runs at
--       midnight UTC, which is 8PM EDT / 7PM EST. Adjust if you need local
--       midnight alignment (use OFFSET or scheduled scripts instead).
--
-- Verification:
--   SHOW CONTINUOUS QUERIES ON "Home Assistant"
--   SELECT * FROM "spc" WHERE time > now() - 7d GROUP BY "appliance"
--
-- =============================================================================

-- Drop existing CQs if re-deploying (uncomment as needed)
-- DROP CONTINUOUS QUERY "spc_fridge_daily" ON "Home Assistant"
-- DROP CONTINUOUS QUERY "spc_furnace_daily" ON "Home Assistant"
-- DROP CONTINUOUS QUERY "spc_ac_daily" ON "Home Assistant"
-- DROP CONTINUOUS QUERY "spc_hwh_recirc_daily" ON "Home Assistant"
-- DROP CONTINUOUS QUERY "spc_dehumidifier_daily" ON "Home Assistant"

-- -----------------------------------------------------------------------------
-- FRIDGE: threshold 50W, source sem_fridge_power
-- -----------------------------------------------------------------------------
-- RETIRED: CREATE CONTINUOUS QUERY "spc_fridge_daily" ON "Home Assistant"
BEGIN
  SELECT MEAN("value") AS "running_watts", COUNT("value") AS "samples"
  INTO "spc"
  FROM "W"
  WHERE "entity_id" = 'sem_fridge_power' AND "value" > 50
  GROUP BY time(1d), "entity_id"
END

-- -----------------------------------------------------------------------------
-- FURNACE: threshold 300W, source sem_furnace_power
-- -----------------------------------------------------------------------------
-- RETIRED: CREATE CONTINUOUS QUERY "spc_furnace_daily" ON "Home Assistant"
BEGIN
  SELECT MEAN("value") AS "running_watts", COUNT("value") AS "samples"
  INTO "spc"
  FROM "W"
  WHERE "entity_id" = 'sem_furnace_power' AND "value" > 300
  GROUP BY time(1d), "entity_id"
END

-- -----------------------------------------------------------------------------
-- AC: threshold 300W, source sem_ac_power
-- -----------------------------------------------------------------------------
-- RETIRED: CREATE CONTINUOUS QUERY "spc_ac_daily" ON "Home Assistant"
BEGIN
  SELECT MEAN("value") AS "running_watts", COUNT("value") AS "samples"
  INTO "spc"
  FROM "W"
  WHERE "entity_id" = 'sem_ac_power' AND "value" > 300
  GROUP BY time(1d), "entity_id"
END

-- -----------------------------------------------------------------------------
-- HWH RECIRC: threshold 70W, source hwh_current_consumption (Kasa plug)
-- NOTE: Verify Kasa plug data is in "W" measurement. If not, change FROM clause.
-- -----------------------------------------------------------------------------
-- RETIRED: CREATE CONTINUOUS QUERY "spc_hwh_recirc_daily" ON "Home Assistant"
BEGIN
  SELECT MEAN("value") AS "running_watts", COUNT("value") AS "samples"
  INTO "spc"
  FROM "W"
  WHERE "entity_id" = 'hwh_current_consumption' AND "value" > 70
  GROUP BY time(1d), "entity_id"
END

-- -----------------------------------------------------------------------------
-- DEHUMIDIFIER: threshold 250W, source dehumidifier_current_consumption (Kasa)
-- NOTE: Verify Kasa plug data is in "W" measurement. If not, change FROM clause.
-- -----------------------------------------------------------------------------
-- RETIRED: CREATE CONTINUOUS QUERY "spc_dehumidifier_daily" ON "Home Assistant"
BEGIN
  SELECT MEAN("value") AS "running_watts", COUNT("value") AS "samples"
  INTO "spc"
  FROM "W"
  WHERE "entity_id" = 'dehumidifier_current_consumption' AND "value" > 250
  GROUP BY time(1d), "entity_id"
END

-- =============================================================================
-- BACKFILL: Run these SELECT INTO queries ONCE to populate historical data
-- =============================================================================
-- Adjust the time range as needed (e.g., last 30 days, last 90 days)
--
-- Fridge backfill (30 days):
-- SELECT MEAN("value") AS "running_watts", COUNT("value") AS "samples"
-- INTO "spc"
-- FROM "W"
-- WHERE "entity_id" = 'sem_fridge_power' AND "value" > 50 AND time > now() - 30d
-- GROUP BY time(1d), "entity_id"
--
-- Repeat for each appliance with appropriate entity_id and threshold.
-- =============================================================================

-- =============================================================================
-- MAPPING TABLE (for reference in Grafana queries)
-- =============================================================================
-- entity_id                      | appliance     | threshold | source
-- -------------------------------|---------------|-----------|------------------
-- sem_fridge_power               | fridge        | 50W       | SEM ch (verified)
-- sem_furnace_power              | furnace       | 300W      | SEM ch (verified)
-- sem_ac_power                   | ac            | 300W      | SEM ch (verified)
-- hwh_current_consumption        | hwh_recirc    | 70W       | Kasa plug
-- dehumidifier_current_consumption | dehumidifier | 250W      | Kasa plug
-- =============================================================================
