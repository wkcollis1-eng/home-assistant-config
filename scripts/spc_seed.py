#!/usr/bin/env python3
print("[spc_seed] Script starting...", flush=True)
"""
spc_seed.py — Seed SPC day_1..day_7 slots from InfluxDB historical data.

Queries InfluxDB for power data, calculates daily mean watts when above
threshold (running state), and writes service calls to seed the SPC day slots.

Usage:
  python3 spc_seed.py                     # Calculate and write to output file
  python3 spc_seed.py --days 7            # Number of days to look back

Output:
  /config/www/spc_seed_results.yaml       # Service calls to seed the slots
  /config/www/spc_seed_results.json       # JSON for input_number.set_value calls

Environment:
  INFLUXDB_URL - InfluxDB URL (default: http://localhost:8086)
  INFLUXDB_DB  - InfluxDB database name (default: homeassistant)
  SPC_TZ       - Timezone (default: America/New_York)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

# ===================== CONFIG =====================
# 2026-08-22 REWRITE. Everything below used to be a hand-maintained copy of the
# appliance constants, and every one of them was wrong:
#
#   dehumidifier threshold 250 W, band (300, 800]  -> the pre-E080 Santa Fe
#     numbers. spc.yaml moved to 150 W / (150, 800] on 2026-08-07 because a
#     failing unit draws LESS and a 300 W floor hides the very signal the chart
#     exists to catch.
#   dehumidifier metric: MEAN of dehumidifier_current_consumption > threshold
#     -> that is the FULL-RUN mean. The live pipeline has used the WARM-UP
#     EXCLUDED steady window since 2026-08-07. Measured 2026-08-21: full-run
#     457.4 W vs steady 466.4 W. Seeding would have put a 9 W step into the
#     middle of a chart whose process sigma is 2-3 W.
#   capture_stamp: it stamped *_spc_last_capture, so a seed would have
#     impersonated a measured capture and silenced the stale detector -
#     exactly what CLAUDE.md forbids. Seeds stamp *_spc_last_seed.
#
# It is now derived from pipelines.yaml, which is the manifest that exists to
# stop this happening. No appliance constant lives in this file. The metric is
# read from the SAME gate sensor the live statistics sensor consumes, found by
# following guard.live_source to its `entity_id:` in the config - so seeded
# points and captured points are the same measurement by construction.
#
# CREDENTIALS: env only. There is no hardcoded default any more. This file is
# untracked today but .gitignore does not cover scripts/, and the repo pushes
# to a PUBLIC GitHub remote - one `git add -A` was all that stood between a
# plaintext InfluxDB password and the internet.
INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_DB = os.environ.get("INFLUXDB_DB", "Home Assistant")
INFLUXDB_USER = os.environ.get("INFLUXDB_USER", "")
INFLUXDB_PASS = os.environ.get("INFLUXDB_PASS", "")
TZ = ZoneInfo(os.environ.get("SPC_TZ", "America/New_York"))
OUT_DIR = os.environ.get("SPC_OUT_DIR", "/config/www")
HA_CONFIG = os.environ.get("HA_CONFIG", "/config")


def _load_yaml(rel):
    import yaml

    class Tolerant(yaml.SafeLoader):
        pass

    Tolerant.add_multi_constructor("!", lambda l, s, n: None)
    with open(os.path.join(HA_CONFIG, rel), encoding="utf-8") as fh:
        return yaml.load(fh, Loader=Tolerant)


def _gate_sensors():
    """live_source statistics sensor -> the gate sensor it actually averages.

    e.g. sensor.dehumidifier_running_watts_steady_24h
           -> sensor.dehumidifier_power_when_on_steady
    """
    out = {}
    files = ["configuration.yaml"]
    pkg = os.path.join(HA_CONFIG, "packages")
    if os.path.isdir(pkg):
        files += ["packages/" + f for f in sorted(os.listdir(pkg))
                  if f.endswith((".yaml", ".yml"))]
    for rel in files:
        cfg = _load_yaml(rel) or {}
        for e in (cfg.get("sensor") or []):
            if isinstance(e, dict) and e.get("platform") == "statistics" and e.get("unique_id"):
                out["sensor.%s" % e["unique_id"]] = e.get("entity_id")
    return out


def load_appliances():
    """Build the population table from pipelines.yaml. No constants here."""
    man = _load_yaml("pipelines.yaml") or {}
    gates = _gate_sensors()
    out = {}
    for name, pipe in (man.get("pipelines") or {}).items():
        guard = pipe.get("guard") or {}
        band = guard.get("band")
        buf = pipe.get("buffer") or []
        if not band or not buf or not guard.get("live_source"):
            continue  # not a running-watts SPC population (e.g. cooling_kwh_cdd)
        gate = gates.get(guard["live_source"])
        if not gate:
            log("SKIP %s: cannot resolve a gate sensor for %s" % (name, guard["live_source"]))
            continue
        if not pipe.get("seed_stamp"):
            log("SKIP %s: no seed_stamp declared - a seed must never write the "
                "capture stamp" % name)
            continue
        key = name.replace("capture_daily_", "").replace("_watts", "")
        out[key] = {
            # InfluxDB stores entity_id without the domain prefix
            "power_entity": gate.split(".", 1)[1],
            "day_slots": buf,
            "capture_stamp": pipe["seed_stamp"],
            "guard_watts_min": band[0],
            "guard_watts_max": band[1],
        }
    return out


def log(*a):
    msg = f"[spc_seed] {' '.join(str(x) for x in a)}"
    print(msg, file=sys.stderr)
    print(msg)  # Also stdout for shell_command capture


def local_day_bounds_rfc3339(d: date):
    """Return (start, end) as RFC3339 UTC strings for InfluxDB queries."""
    from datetime import timezone
    start = datetime(d.year, d.month, d.day, tzinfo=TZ)
    end = start + timedelta(days=1)
    # Convert to UTC for InfluxDB
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)
    return start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def call_ha_service(domain, service, data):
    """Call a Home Assistant service via Supervisor API."""
    # When running in HA OS, use Supervisor API (no token needed)
    url = f"http://supervisor/core/api/services/{domain}/{service}"
    headers = {
        "Authorization": "Bearer " + os.environ.get("SUPERVISOR_TOKEN", ""),
        "Content-Type": "application/json"
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True
    except Exception as e:
        log(f"    Service call error: {e}")
        return False


def query_influxdb(query):
    """Execute InfluxDB query and return results."""
    params = {"db": INFLUXDB_DB, "q": query}
    if INFLUXDB_USER:
        params["u"] = INFLUXDB_USER
    if INFLUXDB_PASS:
        params["p"] = INFLUXDB_PASS
    url = f"{INFLUXDB_URL}/query?{urllib.parse.urlencode(params)}"

    # Debug: show URL (mask password)
    debug_url = url.replace(INFLUXDB_PASS, "***") if INFLUXDB_PASS else url
    log(f"  InfluxDB URL: {debug_url[:150]}...")

    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data
    except Exception as e:
        log(f"InfluxDB query error: {e}")
        return None


def get_daily_mean_watts(entity_id, day: date):
    """Calendar-day mean of the GATE sensor's own recorded samples.

    Not `MEAN(power) WHERE value > threshold`. That re-derivation was the whole
    defect: it silently reconstructs a DIFFERENT statistic from the one the live
    pipeline captures. The gate sensor only records while its availability
    template passes, so averaging it unfiltered reproduces the deployed metric
    exactly - including the dehumidifier's warm-up exclusion, which no threshold
    can express. Verified 2026-08-22 against 14 days: reconstruction matched the
    recorded daily means to 0.07 W.
    """
    start, end = local_day_bounds_rfc3339(day)
    query = f'''
        SELECT MEAN("value") AS mean_watts, COUNT("value") AS samples
        FROM "W"
        WHERE "entity_id" = '{entity_id}'
          AND time >= '{start}' AND time < '{end}'
    '''
    log(f"    Query: gate={entity_id}, {start} to {end}")
    result = query_influxdb(query)
    if not result:
        log("    No result from InfluxDB")
        return None, 0
    try:
        series = result.get("results", [{}])[0].get("series", [])
        if not series:
            log("    No series in result")
            return None, 0
        values = series[0].get("values", [[]])[0]
        if len(values) >= 3 and values[1] is not None:
            mean_watts = round(float(values[1]), 1)
            samples = int(values[2]) if values[2] else 0
            log(f"    Found: mean={mean_watts}W, samples={samples}")
            return mean_watts, samples
    except (IndexError, KeyError, TypeError, ValueError) as e:
        log(f"  Parse error: {e}")
    return None, 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Seed SPC slots from InfluxDB historical data")
    ap.add_argument("--days", type=int, default=7, help="Days of history to pull")
    ap.add_argument("--out", default=OUT_DIR, help=f"Output directory (default: {OUT_DIR})")
    ap.add_argument("--apply", action="store_true", help="Apply service calls to HA immediately")
    args = ap.parse_args(argv)

    today = datetime.now(TZ).date()
    log(f"=== SPC seed starting - {today} ===")
    log(f"InfluxDB: {INFLUXDB_URL}, DB: {INFLUXDB_DB}")

    # Test InfluxDB connection and show databases
    test_result = query_influxdb("SHOW DATABASES")
    if not test_result:
        log(f"ERROR: Cannot connect to InfluxDB at {INFLUXDB_URL}")
        return 1
    log("InfluxDB connection OK")
    log(f"Available databases: {test_result}")

    os.makedirs(args.out, exist_ok=True)

    all_results = {}
    service_calls = []

    APPLIANCES = load_appliances()
    if not APPLIANCES:
        log("ERROR: no SPC populations resolved from pipelines.yaml")
        return 1
    log("Populations from pipelines.yaml: %s" % ", ".join(sorted(APPLIANCES)))

    for name, config in APPLIANCES.items():
        log(f"Processing {name}...")
        entity = config["power_entity"]

        daily_values = []
        for days_ago in range(1, args.days + 1):
            day = today - timedelta(days=days_ago)

            watts, samples = get_daily_mean_watts(entity, day)

            if watts is None or samples < 10:
                reason = "no data" if watts is None else f"only {samples} samples"
                log(f"  {day}: skip ({reason})")
                daily_values.append({"day": str(day), "watts": None, "samples": samples, "reason": reason})
                continue

            # Guard band check
            if not (config["guard_watts_min"] < watts <= config["guard_watts_max"]):
                reason = f"watts {watts:.1f} outside ({config['guard_watts_min']}, {config['guard_watts_max']}]"
                log(f"  {day}: skip ({reason})")
                daily_values.append({"day": str(day), "watts": watts, "samples": samples, "reason": reason})
                continue

            log(f"  {day}: {watts:.1f}W (samples={samples})")
            daily_values.append({"day": str(day), "watts": watts, "samples": samples})

        all_results[name] = daily_values

        # Generate service calls for valid values
        for i, entry in enumerate(daily_values):
            if entry.get("watts") is not None and "reason" not in entry:
                slot = config["day_slots"][i]
                service_calls.append({
                    "service": "input_number.set_value",
                    "target": {"entity_id": slot},
                    "data": {"value": entry["watts"]}
                })

        # Add stamp service call if any valid data
        valid_count = sum(1 for e in daily_values if e.get("watts") is not None and "reason" not in e)
        if valid_count > 0:
            service_calls.append({
                "service": "input_datetime.set_datetime",
                "target": {"entity_id": config["capture_stamp"]},
                "data": {"date": str(today)}
            })

    # Write JSON output (for automation to consume)
    json_path = os.path.join(args.out, "spc_seed_results.json")
    with open(json_path, "w") as f:
        json.dump({
            "generated": datetime.now(TZ).isoformat(),
            "results": all_results,
            "service_calls": service_calls
        }, f, indent=2)
    log(f"Wrote: {json_path}")

    # Write YAML output (human-readable service calls)
    yaml_path = os.path.join(args.out, "spc_seed_results.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"# SPC Seed Results - Generated {datetime.now(TZ).isoformat()}\n")
        f.write(f"# Copy each block to Developer Tools -> Services\n\n")
        for call in service_calls:
            f.write(f"service: {call['service']}\n")
            f.write(f"target:\n")
            f.write(f"  entity_id: {call['target']['entity_id']}\n")
            f.write(f"data:\n")
            for k, v in call['data'].items():
                if isinstance(v, str):
                    f.write(f"  {k}: \"{v}\"\n")
                else:
                    f.write(f"  {k}: {v}\n")
            f.write("\n")
    log(f"Wrote: {yaml_path}")

    # Summary
    log("=== Summary ===")
    for name, values in all_results.items():
        valid = [v for v in values if v.get("watts") is not None and "reason" not in v]
        log(f"  {name}: {len(valid)}/{len(values)} days with valid data")
        if valid:
            watts_list = [v["watts"] for v in valid]
            log(f"    Values: {', '.join(f'{w:.1f}' for w in watts_list)}")

    log(f"Total service calls: {len(service_calls)}")

    # Apply service calls if requested
    if args.apply and service_calls:
        log("=== Applying service calls to HA ===")
        success = 0
        failed = 0
        for call in service_calls:
            # Parse service domain and name
            domain, svc = call["service"].split(".", 1)
            # Combine target and data for the API call
            payload = {**call.get("target", {}), **call.get("data", {})}
            entity = call.get("target", {}).get("entity_id", "?")

            if call_ha_service(domain, svc, payload):
                log(f"  OK: {entity}")
                success += 1
            else:
                log(f"  FAIL: {entity}")
                failed += 1

        log(f"Applied: {success} succeeded, {failed} failed")
    elif args.apply:
        log("No service calls to apply (no valid data found)")

    log("Done. View results at:")
    log(f"  http://homeassistant.local:8123/local/spc_seed_results.yaml")
    log(f"  http://homeassistant.local:8123/local/spc_seed_results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
