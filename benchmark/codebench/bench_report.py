#!/usr/bin/env python3
"""Aggregate codebench results: bench_report.py results/coder.jsonl results/davidau.jsonl"""
import json, sys, statistics as st
from collections import defaultdict

def load(p):
    return [json.loads(l) for l in open(p) if l.strip()]

def pct(a, b): return f"{a}/{b} ({100*a/b:.0f}%)" if b else "-"
def med(xs):
    xs = [x for x in xs if x is not None]; return round(st.median(xs), 1) if xs else None
def tot(xs): return sum(x for x in xs if x)

runs = {p.split("/")[-1].split(".")[0]: load(p) for p in sys.argv[1:]}
names = list(runs)

def row(label, f):
    print(f"  {label:38s}" + "".join(f"{str(f(runs[n])):>24s}" for n in names))

print(" " * 40 + "".join(f"{n:>24s}" for n in names))
for ph in ("code", "casual", "xhigh", "tools", "agent"):
    print(f"\n== {ph}")
    R = lambda rs, ph=ph: [r for r in rs if r["phase"] == ph]
    row("passed", lambda rs: pct(sum(r["ok"] for r in R(rs)), len(R(rs))))
    if ph in ("code", "casual", "xhigh"):
        row("completion tokens total", lambda rs: tot(r.get("completion_tokens") for r in R(rs)))
        row("completion tokens median/task", lambda rs: med([r.get("completion_tokens") for r in R(rs)]))
        row("wall time total (min)", lambda rs: round(tot(r.get("wall") for r in R(rs)) / 60, 1))
        row("wall time median/task (s)", lambda rs: med([r.get("wall") for r in R(rs)]))
        row("hit max_tokens (finish=length)", lambda rs: sum(r.get("finish") == "length" for r in R(rs)))
        row("answer code lines median", lambda rs: med([r.get("code_lines") for r in R(rs) if r["ok"]]))
        row("test exec time total, passing (s)", lambda rs: round(tot(r.get("test_s") for r in R(rs) if r["ok"]), 1))
    if ph == "agent":
        A = lambda rs: R(rs)
        row("turns (LLM calls) median", lambda rs: med([r["turns"] for r in A(rs)]))
        row("turns total", lambda rs: tot(r["turns"] for r in A(rs)))
        row("tool calls total", lambda rs: tot(r["tool_calls"] for r in A(rs)))
        row("file writes total", lambda rs: tot(r["writes"] for r in A(rs)))
        row("test runs total", lambda rs: tot(r["test_runs"] for r in A(rs)))
        row("malformed/failed tool calls", lambda rs: tot(r["bad_calls"] for r in A(rs)))
        row("finished on its own", lambda rs: sum(r["finished"] for r in A(rs)))
        row("tests edited (tampering)", lambda rs: sum(r["tests_tampered"] for r in A(rs)))
        row("prompt tokens total", lambda rs: tot(r["prompt_tokens"] for r in A(rs)))
        row("completion tokens total", lambda rs: tot(r["completion_tokens"] for r in A(rs)))
        row("wall time median/episode (s)", lambda rs: med([r["wall"] for r in A(rs)]))
        row("wall time total (min)", lambda rs: round(tot(r["wall"] for r in A(rs)) / 60, 1))
    if ph == "tools":
        row("wall median/call (s)", lambda rs: med([r.get("wall") for r in R(rs)]))
    row("decode tok/s (engine, aggregate)", lambda rs, R=R: round(tot(r.get("gen_tokens") for r in R(rs)) / (tot(r.get("gen_ms") for r in R(rs)) / 1000), 1) if tot(r.get("gen_ms") for r in R(rs)) else None)
    row("MTP draft acceptance", lambda rs, R=R: f"{100*tot(r.get('drafts_accepted') for r in R(rs))/tot(r.get('drafts_proposed') for r in R(rs)):.0f}%" if tot(r.get("drafts_proposed") for r in R(rs)) else None)

print("\n== overall")
row("all graded items passed", lambda rs: pct(sum(r["ok"] for r in rs), len(rs)))
row("generated tokens (engine) total", lambda rs: tot(r.get("gen_tokens") for r in rs))
row("total wall time (h)", lambda rs: round(tot(r.get("wall") for r in rs) / 3600, 2))

print("\n== per category (code+casual+xhigh)")
cats = sorted({r["cat"] for rs in runs.values() for r in rs if "cat" in r})
for c in cats:
    row(c, lambda rs, c=c: pct(sum(r["ok"] for r in rs if r.get("cat") == c), sum(1 for r in rs if r.get("cat") == c)))
print("\n== per language")
for lg in ("python", "js", "sql", "bash"):
    row(lg, lambda rs, lg=lg: pct(sum(r["ok"] for r in rs if r.get("lang") == lg), sum(1 for r in rs if r.get("lang") == lg)))

print("\n== per task (code reps / casual / xhigh) and failures")
ids = []
for rs in runs.values():
    for r in rs:
        if r["id"] not in ids: ids.append(r["id"])
for i in ids:
    cells = []
    for n in names:
        s = ""
        for ph in ("code", "casual", "xhigh", "tools", "agent"):
            xs = [r for r in runs[n] if r["id"] == i and r["phase"] == ph]
            if xs: s += ph[0] + "".join("✓" if r["ok"] else "✗" for r in xs) + " "
        cells.append(s.strip())
    print(f"  {i:38s}" + "".join(f"{c:>24s}" for c in cells))
print("\n== failure notes")
for n in names:
    for r in runs[n]:
        if not r["ok"]:
            print(f"  [{n}] {r['phase']}/{r['id']} rep{r.get('rep')}: finish={r.get('finish')} tok={r.get('completion_tokens')} :: {str(r.get('note'))[:230]}")
