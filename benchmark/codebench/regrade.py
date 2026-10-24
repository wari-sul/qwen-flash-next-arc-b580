#!/usr/bin/env python3
"""Re-grade stored code answers with the current grader: regrade.py results/<label>.jsonl -> results/<label>.regraded.jsonl"""
import json, sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench
T = {t["id"]: t for t in bench.TASKS}
p = sys.argv[1]; outp = p.replace(".jsonl", ".regraded.jsonl")
rows = [json.loads(l) for l in open(p) if l.strip()]
flips = 0
for r in rows:
    if r["phase"] in ("code", "casual", "xhigh") and "answer" in r:
        ok, detail, el, code = bench.grade_code(T[r["id"]], r["answer"])
        if ok != r["ok"]:
            flips += 1; print(f"{r['phase']}/{r['id']} rep{r['rep']}: {r['ok']} -> {ok}")
        r.update(ok=ok, test_s=el, code_lines=code.count("\n") + 1, note="" if ok else detail.replace("\n", " ")[-200:])
with open(outp, "w") as f:
    for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("regraded", len(rows), "flips", flips)
