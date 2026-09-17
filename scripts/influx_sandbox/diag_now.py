"""Are the T3 Grafana-query differences real, or now() moving between calls?
Fresh copies from pristine. For each of the 170 queries:
  self  : same query twice on A (1.12.4) - differs => the query is not repeatable, on either version
  pinned: now() replaced by END literal, A vs B - differs => a real version difference
"""

import json
import shutil


import harness as h

d = h.ROOT / "diag"
if d.exists():
    shutil.rmtree(d)
for lab in ("A", "B"):
    shutil.copytree(h.ROOT / "pristine", d / lab)
A = h.Server("diag_A_1124_fork", "1.12.4", "fork", d / "A", 18086).start()
B = h.Server("diag_B_1131_v6", "1.13.1", "v6", d / "B", 28086).start()
try:
    qs = h.grafana_queries()
    rows = []
    for i, (dash, q) in enumerate(qs):
        a1, b1, a2 = A.q(q), B.q(q), A.q(q)
        pq = q.replace("now()", f"'{h.END}'")
        pa, pb = A.q(pq), B.q(pq)
        rows.append(
            {
                "i": i,
                "uses_now": "now()" in q,
                "orig_AvsB_same": a1 == b1,
                "A_self_same": a1 == a2,
                "pinned_AvsB_same": pa == pb,
                "pinned_error": '"error":' in pa,
                "pinned_empty": '"series"' not in pa,
            }
        )
    tab = {}
    for r in rows:
        k = (
            r["uses_now"],
            r["orig_AvsB_same"],
            r["A_self_same"],
            r["pinned_AvsB_same"],
        )
        tab[str(k)] = tab.get(str(k), 0) + 1
    print("(uses_now, orig A==B, A==A, pinned A==B): count")
    for k, v in sorted(tab.items()):
        print(" ", k, v)
    print(
        "pinned query errors:",
        sum(r["pinned_error"] for r in rows),
        "| pinned empty results:",
        sum(r["pinned_empty"] for r in rows),
    )
    real = [r["i"] for r in rows if not r["pinned_AvsB_same"]]
    print("pinned A!=B (real differences):", real)
    for i in real[:5]:
        pq = qs[i][1].replace("now()", f"'{h.END}'")
        print(i, pq[:200], "\n  A:", A.q(pq)[:300], "\n  B:", B.q(pq)[:300])
    (d / "diag_now.json").write_text(json.dumps(rows, indent=1))
finally:
    A.stop()
    B.stop()
