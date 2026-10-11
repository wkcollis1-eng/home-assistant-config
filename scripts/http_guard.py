"""Outbound-fetch guards for the scripts HA runs as command_line sensors
(fetch_bdl_degree_days.py, kbdl_degree_days.py).

Why (2026-10-10)
----------------
From 2026-10-01 the LAN has had IPv6 addresses and a default route from router
advertisements, but IPv6 traffic goes nowhere [M, 2026-10-10, n=1 probe from the
host: all 5 v6 connects to data.rcc-acis.org / api.weather.gov timed out at 10 s,
all 5 v4 connects ok in 0.02-0.03 s; Windows on the same LAN also failed v6].
urllib tries each getaddrinfo address in turn with the full timeout, v6 first:
3 x 30 s for ACIS, 2 x 30 s for NWS [D] - past command_timeout: 45, so HA killed
every run and blanked every attribute before the script's own stale/error
fallback could print. sensor.bdl_degree_days lost trailing_12 and the three 12M
HVAC sensors went unavailable 2026-10-01 -> 2026-10-10 [M, HA history].

Two guards, both needed:
  prefer_ipv4()    try IPv4 addresses first - the family this house runs on
                   (static 10.0.0.210). Restores FRESH data while v6 is broken.
  within(s, fn)    TimeoutError after s seconds wherever fn is stuck (DNS,
                   connect, slow read). This is the one that keeps the fallback
                   reachable inside command_timeout whatever else goes wrong.
"""

import socket
import threading

# Below command_timeout: 45 (configuration.yaml, both sensors), leaving the
# fallback ~15 s to load the CSV and print before HA's kill.
DEADLINE_S = 30


def prefer_ipv4():
    """Make every later getaddrinfo() in this process list IPv4 first.
    Stable sort: the resolver's order within each family is kept, and v6 is
    still tried if every v4 address fails."""
    gai = socket.getaddrinfo

    def v4_first(*args, **kwargs):
        return sorted(gai(*args, **kwargs), key=lambda r: r[0] != socket.AF_INET)

    socket.getaddrinfo = v4_first


def within(seconds, fn, *args):
    """fn(*args), or TimeoutError after `seconds`. fn runs on a daemon thread
    that is abandoned on timeout, so fn must have no side effects (a fetch that
    only returns data). Portable: no SIGALRM, so it also runs on Windows."""
    box = {}

    def run():
        try:
            box["value"] = fn(*args)
        except BaseException as e:  # re-raised below on the caller's thread
            box["error"] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(seconds)
    if t.is_alive():
        raise TimeoutError(f"no answer within {seconds} s")
    if "error" in box:
        raise box["error"]
    return box["value"]
