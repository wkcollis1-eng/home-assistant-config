#!/usr/bin/env python3
"""Fetch HA core source at the pinned .HA_VERSION, and cache it.

WHY. R6 says read the deployed artifact, never the plausible story - and
CONSTRAINTS says the same about HA internals. Both then require you to
hand-build a raw.githubusercontent.com URL out of .HA_VERSION. That friction is
why the two 2026-08-21 regressions came from trusting docs over the artifact:
apexcharts-card's real data_generator signature, and the statistics platform's
availability propagation, which components/statistics/sensor.py settled in one
read after an hour of inferring it from state timestamps.

The cache is the point as much as the fetch. The second session that needs
components/statistics/sensor.py pays nothing, so the cheap path and the correct
path stop being different paths.

  python3 scripts/ha_source.py statistics/sensor.py
  python3 scripts/ha_source.py --card apexcharts-card
  python3 scripts/ha_source.py statistics/sensor.py --print

Cached under docs/vendor/<version>/. Network only on a miss.
"""
import argparse
import io
import os
import sys
import urllib.request

CONFIG = os.environ.get("HA_CONFIG", "/config").rstrip("/")
P = lambda *a: os.path.join(CONFIG, *a)
RAW = "https://raw.githubusercontent.com/home-assistant/core/%s/homeassistant/components/%s"


def version():
    p = P(".HA_VERSION")
    if not os.path.exists(p):
        sys.exit(".HA_VERSION not found under %s - cannot pin a version, and an "
                 "unpinned fetch is a different artifact from the deployed one" % CONFIG)
    return io.open(p, encoding="utf-8").read().strip()


def fetch(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "ha_source.py"})
    with urllib.request.urlopen(req, timeout=30) as fh:
        body = fh.read().decode("utf-8", "replace")
    io.open(dest, "w", encoding="utf-8", newline="\n").write(body)
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="<domain>/<file>.py, e.g. statistics/sensor.py")
    ap.add_argument("--card", help="a custom card under www/community/ (local, no fetch)")
    ap.add_argument("--print", dest="show", action="store_true", help="print to stdout")
    a = ap.parse_args()

    if a.card:
        # Custom cards are already on disk: the SHIPPED js is the artifact, and
        # its repo README is exactly the "plausible story" R6 warns about.
        d = P("www", "community", a.card)
        if not os.path.isdir(d):
            sys.exit("no such card directory: %s" % d)
        for f in sorted(os.listdir(d)):
            print(os.path.join(d, f))
        return 0

    if not a.path:
        ap.error("give a <domain>/<file>.py, or --card <name>")

    v = version()
    dest = P("docs", "vendor", v, a.path.replace("/", os.sep))
    if os.path.exists(dest):
        print("CACHED  %s  (version %s)" % (dest, v))
        body = io.open(dest, encoding="utf-8").read()
    else:
        url = RAW % (v, a.path)
        print("FETCH   %s" % url)
        try:
            body = fetch(url, dest)
        except Exception as exc:
            sys.exit("fetch failed: %s\nIf this is a 404, check the domain/file "
                     "path against the component tree for %s." % (exc, v))
        print("SAVED   %s" % dest)
    print("        %d lines, HA %s" % (body.count("\n") + 1, v))
    if a.show:
        sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
