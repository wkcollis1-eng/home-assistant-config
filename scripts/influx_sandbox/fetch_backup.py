"""Download one HA backup (read-only GET), verify its size, extract the fork's
/data/influxdb into pristine/. Prints structure and non-secret add-on options only.

  python fetch_backup.py <backup_id> <expected_size_bytes>
"""

import hashlib
import io
import json
import os
import shutil
import sys
import tarfile
import time
from pathlib import Path

import requests

ROOT = Path("C:/sandbox/influx-v6")
bid, expected = sys.argv[1], int(sys.argv[2])
out = ROOT / "backup" / f"{bid}.tar"
out.parent.mkdir(parents=True, exist_ok=True)

t0 = time.perf_counter()
h = hashlib.sha256()
n = 0
with requests.get(
    f"http://10.0.0.210:8123/api/backup/download/{bid}",
    params={"agent_id": "hassio.local"},
    headers={"Authorization": f"Bearer {os.environ['HA_TOKEN']}"},
    stream=True,
    timeout=600,
) as r:
    r.raise_for_status()
    with open(out, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
            h.update(chunk)
            n += len(chunk)
print(
    f"downloaded {n:,} B in {time.perf_counter() - t0:.1f}s  expected {expected:,}  {'MATCH' if n == expected else 'SIZE MISMATCH'}"
)
print("sha256", h.hexdigest())

with tarfile.open(out) as outer:
    members = outer.getnames()
    print("outer members:", members)
    meta = json.load(
        outer.extractfile(
            "./backup.json" if "./backup.json" in members else "backup.json"
        )
    )
    print(
        "backup.json: protected=%s compressed=%s type=%s addons=%s"
        % (
            meta.get("protected"),
            meta.get("compressed"),
            meta.get("type"),
            [(a.get("slug"), a.get("version")) for a in meta.get("addons", [])],
        )
    )
    inner_name = next(m for m in members if "local_influxdb112" in m)
    inner_bytes = outer.extractfile(inner_name).read()

pristine = ROOT / "pristine"
if pristine.exists():
    shutil.rmtree(pristine)
with tarfile.open(fileobj=io.BytesIO(inner_bytes), mode="r:gz") as inner:
    names = inner.getnames()
    tops = sorted({"/".join(x.lstrip("./").split("/")[:3]) for x in names})
    print("inner entries:", len(names), "prefixes:", tops[:15])
    addon_json = next((x for x in names if x.lstrip("./") == "addon.json"), None)
    if addon_json:
        aj = json.load(inner.extractfile(addon_json))
        opts = aj.get("options", {}) or {}
        print(
            "addon.json: version=%s options auth=%s reporting=%s log_level=%s envvar_names=%s"
            % (
                aj.get("version"),
                opts.get("auth"),
                opts.get("reporting"),
                opts.get("log_level"),
                [e.get("name") for e in opts.get("envvars", [])],
            )
        )
    print("data/secret present:", any(x.lstrip("./") == "data/secret" for x in names))
    prefix = "data/influxdb/"
    sel = [m for m in inner.getmembers() if m.name.lstrip("./").startswith(prefix)]
    for m in sel:
        m.name = m.name.lstrip("./")[len(prefix) :]
    inner.extractall(pristine, members=[m for m in sel if m.name], filter="data")

tot = sum(p.stat().st_size for p in pristine.rglob("*") if p.is_file())
print(
    "pristine:",
    {d.name: sum(1 for _ in d.rglob("*")) for d in pristine.iterdir()},
    f"{tot:,} B",
)
