#!/usr/bin/env python3
"""Set the rtlamr2mqtt tuner gain (or AGC) and restart the add-on.

Built 2026-09-17 to drive the gain sweep unattended. It exists because setting
gain on this stack takes TWO flags in two different programs, and getting one
of them wrong fails SILENTLY - see docs/sdr-signal-level.md section 3:

  rtltcp  -g <dB>           the half that SETS gain   [S: rtl_tcp.c:509-521]
  rtlamr  -tunergain=<dB>   the half that KEEPS it    [S: main.go:98-122]

Without the rtlamr half, rtlamr sends tunerGainMode=0 (AUTO) on connect and
silently undoes -g. The VALUE on -tunergain is cosmetic - rtlamr's HandleFlags
runs before it connects and the command is discarded (rtltcp.go:101-147) - so
rtl_tcp's -g is the single source of truth for the actual gain. We write the
value on both anyway so the config reads honestly.

SAFETY. Supervisor REPLACES the options dict rather than merging it, so a
partial write would drop the `meters:` list and take all three utility meters
with it. This does read -> modify -> verify -> write -> read-back, and refuses
to send anything if more than the gain leaves changed.

Usage:
  python3 sdr_gain_set.py 40.2                 set fixed gain, restart
  python3 sdr_gain_set.py agc                  back to automatic gain, restart
  python3 sdr_gain_set.py 40.2 --verbosity debug
  python3 sdr_gain_set.py 40.2 --dry-run       print the diff, touch nothing
"""

import argparse
import copy
import json
import re
import sys
import time
import urllib.request

SLUG = "6713e36e_rtlamr2mqtt"
SUPERVISOR = "http://supervisor"
PROFILE = "/etc/profile.d/homeassistant.sh"

# librtlsdr r82xx_gains[], tenths of a dB [S: librtlsdr.c:966-969].
# The tuner is an R820T2/R860 (Nooelec NESDR SMArt v5, 0bda:2838) [S: vendor
# spec]. rtl_tcp snaps -g to the nearest of these, so asking for an unlisted
# value silently gets you a different one - refuse instead.
GAINS_TENTHS = [
    0,
    9,
    14,
    27,
    37,
    77,
    87,
    125,
    144,
    157,
    166,
    197,
    207,
    229,
    254,
    280,
    297,
    328,
    338,
    364,
    372,
    386,
    402,
    421,
    434,
    439,
    445,
    480,
    496,
]


def token():
    with open(PROFILE) as fh:
        m = re.search(r'SUPERVISOR_TOKEN="([^"]+)"', fh.read())
    if not m:
        sys.exit("no SUPERVISOR_TOKEN in " + PROFILE)
    return m.group(1)


def api(path, body=None, tok=None):
    req = urllib.request.Request(
        SUPERVISOR + path, headers={"Authorization": "Bearer " + tok}
    )
    if body is not None:
        req.data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    return json.load(urllib.request.urlopen(req, timeout=60))


def leaves(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaves(v, p + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, p + "/%d" % i)
    else:
        yield p, o


def set_gain(s, gain):
    """Strip any existing gain flag, then add the new one if not AGC."""
    s = re.sub(r"\s*-tunergain=\S+", "", s)
    s = re.sub(r"\s*-gainbyindex=\S+", "", s)
    s = re.sub(r"\s*-tunergainmode=\S+", "", s)
    return s if gain is None else s + " -tunergain=%s" % gain


SAMPLEFILE = "/config/tmp/rtlamr_912.38M_2621.44k.cu8"


def set_samplefile(s, on):
    """Add or remove rtlamr's IQ dump. The filename is load-bearing: rtl_433
    reads centre frequency and sample rate off the path [S: README:627-641]."""
    s = re.sub(r"\s*-samplefile=\S+", "", s)
    return s + " -samplefile=%s" % SAMPLEFILE if on else s


def set_g(s, gain):
    s = re.sub(r"\s*-g\s+\S+", "", s)
    return s if gain is None else s + " -g %s" % gain


# RTL2832U sample-rate limits [S: librtlsdr.c rtlsdr_set_sample_rate]: legal
# ranges are 225001-300000 and 900001-3200000 Hz; above 2400000 the driver
# warns that samples MAY BE LOST, and that loss is SILENT - nothing in the
# add-on log reports it. Window width = DataRate * symbollength, DataRate is
# 32768 for scm AND r900 [S: rtlamr scm/scm.go:45, r900/r900.go:60], and
# rtlamr re-asserts the rate over the wire on connect via SetSampleRate()
# [S: rtlamr main.go:117] - so rtltcp's -s is OVERRIDDEN by rtlamr and must be
# kept in step with -symbollength or the two disagree silently.
# NOTE symbollength changes the DECODER (chipLength), not only the window, and
# one flag serves scm, scm+, idm and r900 alike [S: rtlamr main.go:77] - so a
# bad value can take all three meters dark, not merely reduce their rate.
DATA_RATE = 32768
SR_HARD_MAX = 3200000
SR_LOSSY_ABOVE = 2400000


def set_symbollength(s, n):
    s = re.sub(r"\s*-symbollength=\S+", "", s)
    return (s + " -symbollength=%d" % n).strip()


def set_s(s, rate):
    s = re.sub(r"\s*-s\s+\S+", "", s)
    return (s + " -s %d" % rate).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gain", help="gain in dB (an r82xx step), or 'agc'")
    ap.add_argument("--verbosity", choices=["info", "debug"])
    ap.add_argument(
        "--samplefile",
        choices=["on", "off"],
        help="turn rtlamr's IQ dump on or off; omit to leave as-is",
    )
    ap.add_argument(
        "--symbollength",
        type=int,
        help="rtlamr chip length; also sets rtltcp -s to 32768*N. "
        "Omit to leave as-is. Changes the DECODER, not just "
        "the window - all three meters ride this one flag.",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-restart", action="store_true")
    a = ap.parse_args()

    if a.gain.lower() == "agc":
        gain = None
    else:
        tenths = round(float(a.gain) * 10)
        if tenths == 0:
            # THE TRAP: rtl_tcp reads -g 0 as "enable automatic gain", not as
            # zero gain - `if (0 == gain) { rtlsdr_set_tuner_gain_mode(dev, 0) }`
            # [S: rtl_tcp.c:509-511], and -g is parsed as (int)(atof(x)*10) at
            # :428, so anything under 0.05 dB lands in that branch. Asking for 0
            # would silently give AGC, and a "no change" result would be read as
            # "the gain flags are not working" - the exact false conclusion this
            # whole script exists to prevent. 0.9 dB is the lowest REACHABLE step.
            sys.exit(
                "-g 0 means AUTOMATIC GAIN to rtl_tcp, not zero gain "
                "[S: rtl_tcp.c:509-511]. Refusing. Use 0.9 for the lowest "
                "reachable manual step, or 'agc' if you meant automatic."
            )
        if tenths not in GAINS_TENTHS:
            near = min(GAINS_TENTHS, key=lambda g: abs(g - tenths))
            sys.exit(
                "%s dB is not an r82xx step. Nearest is %.1f dB. "
                "Refusing - rtl_tcp would snap silently." % (a.gain, near / 10.0)
            )
        gain = a.gain

    if a.symbollength is not None:
        n = a.symbollength
        rate = DATA_RATE * n
        if n < 32 or n > 200:
            sys.exit("symbollength %d is out of any sane range. Refusing." % n)
        if rate > SR_HARD_MAX:
            sys.exit(
                "symbollength %d wants %d Hz, above the RTL2832U's %d Hz "
                "hard limit [S: librtlsdr rtlsdr_set_sample_rate]. Refusing."
                % (n, rate, SR_HARD_MAX)
            )
        if rate > SR_LOSSY_ABOVE:
            print(
                "WARNING: %d Hz is above %d Hz - the driver may drop samples, "
                "and that loss is SILENT. Verify decode before trusting it."
                % (rate, SR_LOSSY_ABOVE)
            )

    tok = token()
    before = api("/addons/%s/info" % SLUG, tok=tok)["data"]["options"]
    after = copy.deepcopy(before)

    cp = after["custom_parameters"]
    if a.samplefile:
        cp["rtlamr"] = set_samplefile(cp["rtlamr"], a.samplefile == "on")
    cp["rtlamr"] = set_gain(cp["rtlamr"], gain)
    cp["rtltcp"] = set_g(cp["rtltcp"], gain)
    if a.symbollength is not None:
        cp["rtlamr"] = set_symbollength(cp["rtlamr"], a.symbollength)
        cp["rtltcp"] = set_s(cp["rtltcp"], DATA_RATE * a.symbollength)
    if a.verbosity:
        after["general"]["verbosity"] = a.verbosity

    if "-samplefile" not in cp["rtlamr"]:
        print("NOTE: -samplefile is not set; this run produces no IQ dump.")

    lb, la = dict(leaves(before)), dict(leaves(after))
    if set(lb) != set(la):
        sys.exit("REFUSING: option key set changed. %s" % (set(lb) ^ set(la)))
    changed = [k for k in lb if lb[k] != la[k]]
    allowed = {
        "/custom_parameters/rtlamr",
        "/custom_parameters/rtltcp",
        "/general/verbosity",
    }
    if set(changed) - allowed:
        sys.exit("REFUSING: unexpected change to %s" % (set(changed) - allowed))

    print("gain target : %s" % (a.gain if gain else "AGC (no gain flags)"))
    for k in changed:
        print("  %s\n    was: %s\n    now: %s" % (k, lb[k], la[k]))
    if not changed:
        print("  (already in that state - nothing to write)")
    print("meters preserved: %s" % [m["name"] for m in after["meters"]])

    if a.dry_run:
        print("\nDRY RUN - nothing written.")
        return
    if not changed and a.no_restart:
        return

    if changed:
        api("/addons/%s/options" % SLUG, {"options": after}, tok=tok)
        back = api("/addons/%s/info" % SLUG, tok=tok)["data"]["options"]
        if dict(leaves(back)) != la:
            sys.exit("REFUSING TO CONTINUE: read-back does not match what was sent.")
        print("written and read back clean.")

    if a.no_restart:
        return
    t0 = time.time()
    api("/addons/%s/restart" % SLUG, {}, tok=tok)
    print("restarted in %.1f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
