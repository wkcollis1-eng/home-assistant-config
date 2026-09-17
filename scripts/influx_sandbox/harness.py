"""Side-by-side sandbox: InfluxDB 1.12.4 (fork config) vs 1.13.1 (v6.0.0 add-on config).

Nothing here talks to the LAN. Every server binds 127.0.0.1, and the services that
could reach out or mutate the copies on a wall-clock timer are disabled on BOTH
sides (subscriber, continuous queries, retention enforcement) - see render_conf().

  python harness.py selftest              R7: synthetic DB, prove each check fires AND stays silent
  python harness.py run --pristine DIR    the real test on an extracted add-on /data/influxdb tree

DIR must contain meta/, data/, wal/. It is never opened by a server; copies are.
"""

import argparse
import hashlib
import json
import re
import shutil
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import psutil
import requests
from scipy import stats

ROOT = Path("C:/sandbox/influx-v6")
BIN = {v: ROOT / "bin" / v / "influxd.exe" for v in ("1.12.4", "1.13.1")}
DB = "Home Assistant"
DASH = Path("H:/grafana/dashboards")
# Fixed analysis windows. END is before the source backup (2026-09-17 05:31 local)
# so nothing either server writes during the run can land inside them.
END = "2026-09-17T00:00:00Z"
W24 = f"time >= '{END}' - 24h AND time < '{END}'"
W14D = f"time >= '{END}' - 14d AND time < '{END}'"
PROBE_TS = 1797206400  # 2026-12-14T00:00:00Z: far past END, forces a NEW shard group

LOG = []


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    LOG.append(line)


# --------------------------------------------------------------------------- config
def render_conf(kind, data_root, port, auth, cq=False):
    """kind='fork': v5.0.2 influxdb.conf as the fork ships it (no index-version => inmem).
    kind='v6'  : v6.0.0 influxdb.gtpl rendered (index-version = "tsi1").
    Sandbox-only deviations, IDENTICAL on both kinds: 127.0.0.1 binds, log level info
    (production warn; info is what prints index_version per shard), reporting off,
    and subscriber / continuous_queries / retention disabled so the copies are not
    mutated or forwarded anywhere by timers."""
    d = Path(data_root).as_posix()
    idx = '  index-version = "tsi1"\n' if kind == "v6" else ""
    realm = "InfluxDB" if kind == "v6" else "Hass.io InfluxDB"
    return (
        "reporting-disabled = true\n"
        f'bind-address = "127.0.0.1:{port + 2}"\n'
        f'[meta]\n  dir = "{d}/meta"\n'
        f'[data]\n  dir = "{d}/data"\n  engine = "tsm1"\n{idx}  wal-dir = "{d}/wal"\n'
        f'[http]\n  bind-address = "127.0.0.1:{port}"\n  auth-enabled = {str(auth).lower()}\n'
        f'  realm = "{realm}"\n  log-enabled = false\n  https-enabled = false\n  flux-enabled = true\n'
        '[logging]\n  level = "info"\n'
        "[subscriber]\n  enabled = false\n"
        f"[continuous_queries]\n  enabled = {str(cq).lower()}\n"
        "[retention]\n  enabled = false\n"
    )


# --------------------------------------------------------------------------- server
class Server:
    def __init__(self, tag, ver, kind, data_root, port, auth=False):
        self.tag, self.ver, self.kind, self.root, self.port, self.auth = (
            tag,
            ver,
            kind,
            Path(data_root),
            port,
            auth,
        )
        self.url = f"http://127.0.0.1:{port}"
        self.conf = ROOT / "conf" / f"{tag}.conf"
        self.log = ROOT / "logs" / f"{tag}.log"
        self.p = None

    def start(self):
        self.conf.parent.mkdir(parents=True, exist_ok=True)
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self.conf.write_text(render_conf(self.kind, self.root, self.port, self.auth))
        t0 = time.perf_counter()
        self.p = subprocess.Popen(
            [str(BIN[self.ver]), "-config", str(self.conf)],
            stdout=open(self.log, "wb"),
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        while True:
            if self.p.poll() is not None:
                raise RuntimeError(
                    f"{self.tag} exited rc={self.p.returncode}; see {self.log}"
                )
            try:
                if requests.get(self.url + "/ping", timeout=1).status_code == 204:
                    break
            except requests.RequestException:
                pass
            if time.perf_counter() - t0 > 900:
                raise TimeoutError(self.tag)
            time.sleep(0.05)
        self.startup_s = time.perf_counter() - t0
        return self

    def stop(self, hard=False):
        if not self.p or self.p.poll() is not None:
            return
        if hard:
            self.p.kill()  # TerminateProcess: unclean, cache/WAL unflushed
        else:
            self.p.send_signal(signal.CTRL_BREAK_EVENT)
            try:
                self.p.wait(120)
            except subprocess.TimeoutExpired:
                say(f"  {self.tag}: graceful stop timed out, killing")
                self.p.kill()
        self.p.wait(60)

    def private_mib(self):
        return round(psutil.Process(self.p.pid).memory_info().private / 2**20, 1)

    def q(self, query, db=DB, auth=None, raw=False):
        r = requests.get(
            self.url + "/query",
            params={"db": db, "q": query, "epoch": "ms"},
            auth=auth,
            timeout=600,
        )
        return r if raw else r.text

    def write(self, lines, db=DB, auth=None, precision="s"):
        r = requests.post(
            self.url + "/write",
            params={"db": db, "precision": precision},
            data=lines,
            auth=auth,
            timeout=600,
        )
        if r.status_code != 204:
            raise RuntimeError(f"{self.tag} write {r.status_code}: {r.text[:200]}")


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def scan_log(text):
    lines = text.splitlines()
    bad = [ln for ln in lines if re.search(r"lvl=(error|warn)\b|panic|fatal", ln, re.I)]
    idx = Counter(re.findall(r'msg="Opened shard".*?index_version=(\w+)', text))
    return {
        "error_or_warn_lines": len(bad),
        "first_bad": bad[:5],
        "opened_shards_by_index": dict(idx),
    }


def shards_on_disk(root):
    """{shard_path: 'tsi1' if it has an index/ dir else 'inmem'}"""
    out = {}
    data = Path(root) / "data"
    for sd in data.glob("*/*/*"):
        if sd.is_dir() and sd.name.isdigit():
            out[str(sd.relative_to(data))] = (
                "tsi1" if (sd / "index").is_dir() else "inmem"
            )
    return out


# --------------------------------------------------------------------------- query sets
def grafana_queries():
    qs = []

    def walk(o, dash):
        if isinstance(o, dict):
            if isinstance(o.get("query"), str) and re.search(
                r"(?i)\bselect\b", o["query"]
            ):
                qs.append((dash, o["query"]))
            for v in o.values():
                walk(v, dash)
        elif isinstance(o, list):
            for v in o:
                walk(v, dash)

    for f in sorted(DASH.glob("*.json")):
        walk(json.loads(f.read_text(encoding="utf-8")), f.name)
    return [
        (d, q.replace("$timeFilter", W24).replace("$__interval", "1m")) for d, q in qs
    ]


def names(srv, query, db=DB):
    j = json.loads(srv.q(query, db=db))
    vals = []
    for s in j["results"][0].get("series", []) or []:
        vals += [v[0] for v in s["values"]]
    return vals


def identity_suite(srv):
    """Deterministic query set -> {label: result text}. Values and metadata, whole DB."""
    out = {}
    meta = {
        "show_measurements": "SHOW MEASUREMENTS",
        "show_rps": "SHOW RETENTION POLICIES",
        "show_cqs": "SHOW CONTINUOUS QUERIES",
        "show_field_keys": "SHOW FIELD KEYS",
        "show_tag_keys": "SHOW TAG KEYS",
        "tag_values_entity_id": 'SHOW TAG VALUES WITH KEY = "entity_id"',
        "series_exact_card": "SHOW SERIES EXACT CARDINALITY",
        "measurement_exact_card": "SHOW MEASUREMENT EXACT CARDINALITY",
        "spc_W_daily_means_14d": f'SELECT mean("value") FROM "W" WHERE {W14D} GROUP BY time(1d), "entity_id"',
        "entity_group_no_time_24h": f'SELECT mean("value") FROM "W" WHERE {W24} GROUP BY "entity_id"',
    }
    # Digest, not body: raw_24h on the real store is too large to hold twice.
    # '"error":' is the InfluxDB error KEY; a data value "error" never has the colon.
    dig = lambda t: ("ERR:" if '"error":' in t else "") + sha(t)  # noqa: E731
    for k, qq in meta.items():
        out[k] = dig(srv.q(qq))
    for m in names(srv, "SHOW MEASUREMENTS"):
        mm = m.replace('"', '\\"')
        out[f"count_14d[{m}]"] = dig(
            srv.q(f'SELECT count(*) FROM "{mm}" WHERE {W14D} GROUP BY *')
        )
        out[f"first_point[{m}]"] = dig(
            srv.q(f'SELECT * FROM "{mm}" ORDER BY time ASC LIMIT 1')
        )
        out[f"raw_24h[{m}]"] = dig(srv.q(f'SELECT * FROM "{mm}" WHERE {W24}'))
    out["show_users"] = dig(srv.q("SHOW USERS", db=""))
    return out


def compare(a, b):
    keys = sorted(set(a) | set(b))
    diff = [k for k in keys if a.get(k) != b.get(k)]
    errs = [k for k in keys if (a.get(k) or "").startswith("ERR:")]
    return {
        "n": len(keys),
        "identical": len(keys) - len(diff),
        "differ": diff[:20],
        "n_differ": len(diff),
        "a_side_query_errors": errs[:10],
    }


# --------------------------------------------------------------------------- tests
def t_timing(A, B, queries, rounds):
    """Interleaved A/B, order alternating per round. Returns per-round totals + per-query medians."""
    per = {i: {"A": [], "B": []} for i in range(len(queries))}
    tot = {"A": [], "B": []}
    ident = None
    for r in range(rounds):
        ta = tb = 0.0
        first = []
        for i, (_, qq) in enumerate(queries):
            order = (("A", A), ("B", B)) if r % 2 == 0 else (("B", B), ("A", A))
            res = {}
            for lab, srv in order:
                t0 = time.perf_counter()
                res[lab] = srv.q(qq)
                dt = time.perf_counter() - t0
                per[i][lab].append(dt)
                if lab == "A":
                    ta += dt
                else:
                    tb += dt
            if r == 0:
                first.append(res["A"] == res["B"])
        tot["A"].append(ta)
        tot["B"].append(tb)
        if r == 0:
            ident = first
    return tot, per, ident


def paired(a, b):
    """median of each, ratio of medians, Wilcoxon signed-rank p on paired rounds."""
    ma, mb = sorted(a)[len(a) // 2], sorted(b)[len(b) // 2]
    try:
        p = float(stats.wilcoxon(a, b).pvalue)
    except ValueError:
        p = 1.0
    return {
        "n": len(a),
        "median_A_ms": round(ma * 1e3, 2),
        "median_B_ms": round(mb * 1e3, 2),
        "ratio_B_over_A": round(mb / ma, 3) if ma else None,
        "wilcoxon_p": round(p, 4),
    }


_PAYLOAD = {}


def bench_payload(n_points, batch=5000):
    """Identical, pre-generated payload for every run, so the timer sees only the server."""
    if n_points not in _PAYLOAD:
        base = 1767225600  # 2026-01-01, spans several 7-day shard groups at 1 s spacing
        _PAYLOAD[n_points] = [
            "\n".join(
                f"bench,host=h{i % 100},region=r{i % 7} value={(i * 7919) % 100003 / 97.0:.4f},n={i}i {base + i}"
                for i in range(s, min(s + batch, n_points))
            )
            for s in range(0, n_points, batch)
        ]
    return _PAYLOAD[n_points]


def bench_write(srv, db, n_points=2_000_000):
    batches = bench_payload(n_points)
    srv.q(f'CREATE DATABASE "{db}"', db="")
    t0 = time.perf_counter()
    for lines in batches:
        srv.write(lines, db=db)
    return n_points / (time.perf_counter() - t0)


def full_run(pristine, run_dir, rounds, inject_diff=False, n_bench=2_000_000):
    R = {"pristine": str(pristine), "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    run_dir = Path(run_dir)
    if run_dir.exists():
        shutil.rmtree(run_dir)
    for lab in ("A", "B"):
        t0 = time.perf_counter()
        shutil.copytree(pristine, run_dir / lab)
        say(f"copy {lab}: {time.perf_counter() - t0:.1f}s")
    R["pristine_bytes"] = sum(
        f.stat().st_size for f in Path(pristine).rglob("*") if f.is_file()
    )
    R["shards_before"] = Counter(shards_on_disk(run_dir / "A").values())

    A = Server("A_1124_fork", "1.12.4", "fork", run_dir / "A", 18086).start()
    B = Server("B_1131_v6", "1.13.1", "v6", run_dir / "B", 28086).start()
    try:
        # T1 startup
        R["T1_startup"] = {
            s.tag: {
                "startup_s": round(s.startup_s, 2),
                "private_MiB": s.private_mib(),
                **scan_log(s.log.read_text(errors="replace")),
            }
            for s in (A, B)
        }
        say("T1", json.dumps(R["T1_startup"], indent=1))

        if inject_diff:  # R7 fault injection: identity MUST report this
            B.write("W,domain=sensor,entity_id=injected_fault value=1 1789000000")

        # T2 identity, whole DB
        R["T2_identity"] = compare(identity_suite(A), identity_suite(B))
        say("T2", json.dumps(R["T2_identity"]))

        # T3 Grafana queries: identity + timing
        gq = grafana_queries()
        tot, per, ident = t_timing(A, B, gq, rounds)
        # R13 2026-09-17: 62 of the 170 queries use now() (not $timeFilter). An aggregate
        # without GROUP BY time() stamps its row with now()-24h, which moves between the
        # A and B calls, so 35 "differ" here on ANY version. diag_now.py proved it on fresh
        # copies: all 35 also differ A-vs-A, and 170/170 are identical with now() pinned.
        R["T3_grafana"] = {
            "queries": len(gq),
            "identical_results_round1": sum(ident),
            "differ_idx": [i for i, ok in enumerate(ident) if not ok][:20],
            "round_totals": paired(tot["A"], tot["B"]),
        }
        flagged = []
        for i, d in per.items():
            pr = paired(d["A"], d["B"])
            if (
                pr["wilcoxon_p"] < 0.01
                and pr["ratio_B_over_A"]
                and abs(pr["ratio_B_over_A"] - 1) > 0.2
            ):
                flagged.append({"dash": gq[i][0], "q": gq[i][1][:160], **pr})
        R["T3_grafana"]["per_query_flagged_p<0.01_and_|r-1|>0.2"] = sorted(
            flagged, key=lambda x: -x["ratio_B_over_A"]
        )
        R["T3_mem_after_queries_MiB"] = {A.tag: A.private_mib(), B.tag: B.private_mib()}
        say("T3", json.dumps(R["T3_grafana"], indent=1)[:3000])

        # T4 new shard: tsi1 on B, inmem on A, same series key as real data
        before = {s.tag: shards_on_disk(s.root) for s in (A, B)}
        key = json.loads(A.q('SHOW SERIES FROM "W" LIMIT 1'))["results"][0]["series"][
            0
        ]["values"][0][0]
        eid = re.search(r"entity_id=([^,]+)", key).group(1)
        for s in (A, B):
            s.write(f"{key} value=123.456 {PROBE_TS}")
        new = {
            s.tag: {
                k: v
                for k, v in shards_on_disk(s.root).items()
                if k not in before[s.tag]
            }
            for s in (A, B)
        }
        mixed = {
            s.tag: s.q(
                f'SELECT count("value"), last("value") FROM "W" WHERE "entity_id" = \'{eid}\' '
                f"AND time >= '{END}' - 14d AND time <= {PROBE_TS}s + 1h GROUP BY \"entity_id\""
            )
            for s in (A, B)
        }
        tv = {
            s.tag: s.q('SHOW TAG VALUES FROM "W" WITH KEY = "entity_id"')
            for s in (A, B)
        }
        R["T4_new_shard"] = {
            "series_key": key,
            "new_shards": new,
            "mixed_range_query_identical": mixed[A.tag] == mixed[B.tag],
            "mixed_range_result_B": mixed[B.tag][:300],
            "tag_values_identical_after_tsi1_shard": tv[A.tag] == tv[B.tag],
        }
        say("T4", json.dumps(R["T4_new_shard"], indent=1))

        # T5 write throughput, 3 runs, alternating order
        thr = {A.tag: [], B.tag: []}
        for k in range(3):
            for s in (A, B) if k % 2 == 0 else (B, A):
                thr[s.tag].append(bench_write(s, f"sbx_bench{k}", n_bench))
        R["T5_write_pts_per_s"] = {t: [round(x) for x in v] for t, v in thr.items()}
        R["T5_mem_after_writes_MiB"] = {A.tag: A.private_mib(), B.tag: B.private_mib()}
        say(
            "T5",
            json.dumps(R["T5_write_pts_per_s"]),
            json.dumps(R["T5_mem_after_writes_MiB"]),
        )

        # T6 graceful restart: B reopens a MIXED inmem+tsi1 store
        for s in (A, B):
            s.stop()
        A.tag, B.tag = A.tag + "_restart", B.tag + "_restart"
        A.log, B.log = ROOT / "logs" / f"{A.tag}.log", ROOT / "logs" / f"{B.tag}.log"
        A.conf, B.conf = (
            ROOT / "conf" / f"{A.tag}.conf",
            ROOT / "conf" / f"{B.tag}.conf",
        )
        A.start(), B.start()
        R["T6_restart"] = {
            s.tag: {
                "startup_s": round(s.startup_s, 2),
                **scan_log(s.log.read_text(errors="replace")),
                "on_disk": dict(Counter(shards_on_disk(s.root).values())),
            }
            for s in (A, B)
        }
        R["T6_identity_after_restart"] = compare(identity_suite(A), identity_suite(B))
        say(
            "T6",
            json.dumps(R["T6_restart"], indent=1),
            json.dumps(R["T6_identity_after_restart"]),
        )
        spc_ref = A.q(
            f'SELECT mean("value") FROM "W" WHERE {W14D} GROUP BY time(1d), "entity_id"'
        )
        bench_ref = {
            k: A.q('SELECT count(*) FROM "bench"', db=f"sbx_bench{k}") for k in range(3)
        }

        # T7 rollback: 1.13.1 killed uncleanly, 1.12.4 (fork config) opens its directory
        B.write(
            f"{key} value=654.321 {PROBE_TS + 60}"
        )  # sits in cache/WAL only at kill time
        B.stop(hard=True)
        RB = Server("B_rollback_1124_fork", "1.12.4", "fork", B.root, 38086).start()
        R["T7_rollback"] = {
            "startup_s": round(RB.startup_s, 2),
            **scan_log(RB.log.read_text(errors="replace")),
            "spc_identical_to_A": RB.q(
                f'SELECT mean("value") FROM "W" WHERE {W14D} GROUP BY time(1d), "entity_id"'
            )
            == spc_ref,
            "bench_counts_identical_to_A": all(
                RB.q('SELECT count(*) FROM "bench"', db=f"sbx_bench{k}") == bench_ref[k]
                for k in range(3)
            ),
            "probe_points_in_tsi1_shard": RB.q(
                f'SELECT count("value") FROM "W" WHERE time >= {PROBE_TS}s - 1h AND time <= {PROBE_TS}s + 1h'
            )[:200],
            "expect_probe_count": 2,
        }
        say("T7", json.dumps(R["T7_rollback"], indent=1))
        RB.stop()

        # T8 auth: user hash written by 1.12.4, verified by 1.13.1 with auth on
        A.stop()
        pw = hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:24]
        C = Server("A_auth_setup_1124", "1.12.4", "fork", A.root, 18086).start()
        users = C.q("SHOW USERS", db="")
        C.q(f"CREATE USER sbx_probe WITH PASSWORD '{pw}'", db="")
        C.q(f'GRANT ALL ON "{DB}" TO sbx_probe', db="")
        C.stop()
        D = Server(
            "A_auth_test_1131_v6", "1.13.1", "v6", A.root, 18086, auth=True
        ).start()
        codes = {
            "no_creds_read": D.q(
                'SELECT count(*) FROM "W" WHERE time > now() - 400d', raw=True
            ).status_code,
            "wrong_pw_read": D.q(
                "SHOW MEASUREMENTS", auth=("sbx_probe", "wrong"), raw=True
            ).status_code,
            "unknown_user_read": D.q(
                "SHOW MEASUREMENTS", auth=("nobody", pw), raw=True
            ).status_code,
            "probe_read": D.q(
                "SHOW MEASUREMENTS", auth=("sbx_probe", pw), raw=True
            ).status_code,
            # R13 2026-09-17: first real run posted this WITHOUT precision=s, so the
            # seconds timestamp was read as ns (1970) and made a stray tsi1 shard (97)
            # in copy A - found by the "Mixed shard index types" warn in the auth-test
            # log, confirmed by influx_inspect export. The 204 stands; the shard was noise.
            "probe_write": requests.post(
                D.url + "/write",
                params={"db": DB, "precision": "s"},
                data=f"{key} value=1 {PROBE_TS + 120}",
                auth=("sbx_probe", pw),
                timeout=60,
            ).status_code,
            "probe_create_db_nonadmin": (
                lambda j: (
                    j.get("error")
                    or (j.get("results") or [{}])[0].get("error")
                    or "NO ERROR - non-admin created a DB"
                )
            )(json.loads(D.q('CREATE DATABASE "x"', db="", auth=("sbx_probe", pw))))[
                :90
            ],
        }
        R["T8_auth"] = {
            "users_admin_flags": [
                (u[0], u[1])
                for u in json.loads(users)["results"][0]["series"][0]["values"]
            ],
            "codes": codes,
            "expect": {
                "no_creds_read": 401,
                "wrong_pw_read": 401,
                "unknown_user_read": 401,
                "probe_read": 200,
                "probe_write": 204,
            },
        }
        say("T8", json.dumps(R["T8_auth"], indent=1))
        D.stop()
    finally:
        for s in list(locals().values()):
            if isinstance(s, Server):
                s.stop(hard=True)
    return R


def selftest():
    """Build a small synthetic 1.12.4 store, then run the full harness twice:
    clean (identity checks must be silent) and with an injected diff (must fire)."""
    st = ROOT / "selftest"
    if st.exists():
        shutil.rmtree(st)
    P = Server("selftest_build_1124", "1.12.4", "fork", st / "pristine", 19086).start()
    P.q(f'CREATE DATABASE "{DB}"', db="")
    lines = []
    t0 = 1786665600  # 2026-08-14, 34 days to END -> several shard groups
    for i in range(0, 34 * 86400, 600):
        for e in range(12):
            lines.append(
                f"W,domain=sensor,entity_id=e{e} value={(i // 600 + e) % 97 / 3:.3f} {t0 + i}"
            )
        lines.append(
            f"gal,domain=sensor,entity_id=water Leak={i % 5}i,NoUse={i % 7}i {t0 + i}"
        )
        lines.append(
            f'kWh,domain=sensor,entity_id=grid value={i / 3600:.3f},friendly_name_str="Grid" {t0 + i}'
        )
        if len(lines) > 5000:
            P.write("\n".join(lines))
            lines = []
    P.write("\n".join(lines))
    # An admin must exist: with none, 1.x skips authentication entirely and every
    # request is a 403 "no user provided" (first selftest run, 2026-09-17). The real
    # store has admins (chronograf/kapacitor, created by the add-on's init script).
    P.q("CREATE USER sbx_admin WITH PASSWORD 'x' WITH ALL PRIVILEGES", db="")
    P.q("CREATE USER ha_ro WITH PASSWORD 'x'", db="")
    P.q(f'GRANT ALL ON "{DB}" TO ha_ro', db="")
    P.stop()
    say("selftest store:", Counter(shards_on_disk(st / "pristine").values()))

    # scan_log must fire on an error line and stay silent on info lines
    assert scan_log('ts=x lvl=error msg="boom"')["error_or_warn_lines"] == 1
    assert (
        scan_log('ts=x lvl=info msg="Opened shard" index_version=inmem')[
            "error_or_warn_lines"
        ]
        == 0
    )
    assert scan_log('lvl=info msg="Opened shard" x=1 index_version=tsi1 path=p')[
        "opened_shards_by_index"
    ] == {"tsi1": 1}

    clean = full_run(st / "pristine", st / "clean", rounds=3, n_bench=100_000)
    fault = full_run(
        st / "pristine", st / "fault", rounds=3, inject_diff=True, n_bench=100_000
    )
    checks = {
        "clean: T2 identity silent": clean["T2_identity"]["n_differ"] == 0,
        "fault: T2 identity FIRES": fault["T2_identity"]["n_differ"] > 0,
        "clean: T4 new shard on A is inmem": list(
            clean["T4_new_shard"]["new_shards"]["A_1124_fork"].values()
        )
        == ["inmem"],
        "clean: T4 new shard on B is tsi1": list(
            clean["T4_new_shard"]["new_shards"]["B_1131_v6"].values()
        )
        == ["tsi1"],
        "clean: T8 auth 401/401/401/200/204": all(
            clean["T8_auth"]["codes"][k] == v
            for k, v in clean["T8_auth"]["expect"].items()
        ),
    }
    for k, v in checks.items():
        say(("PASS " if v else "FAIL ") + k)
    (st / "selftest.json").write_text(
        json.dumps(
            {"checks": checks, "clean": clean, "fault": fault}, indent=1, default=str
        )
    )
    return all(checks.values())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    r = sub.add_parser("run")
    r.add_argument("--pristine", required=True)
    r.add_argument("--rounds", type=int, default=11)
    a = ap.parse_args()
    if a.cmd == "selftest":
        ok = selftest()
        print("SELFTEST", "PASSED" if ok else "FAILED")
        sys.exit(0 if ok else 1)
    out = ROOT / "runs" / time.strftime("%Y%m%d-%H%M%S")
    res = full_run(Path(a.pristine), out / "copies", a.rounds)
    (out / "results.json").write_text(json.dumps(res, indent=1, default=str))
    (out / "console.txt").write_text("\n".join(LOG))
    print("RESULTS", out / "results.json")
