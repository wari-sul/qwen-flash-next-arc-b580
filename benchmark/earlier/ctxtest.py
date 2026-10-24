#!/usr/bin/env python3
"""Long-context needle test against the running Strata server. usage: ctxtest.py <ctx> <label>"""
import json, sys, time, re, os, random, urllib.request
CTX = int(sys.argv[1]); label = sys.argv[2]
cfg = json.load(open(os.environ.get('SCFG','/etc/strata/davidau-iq3s-256k.json'))); KEY = cfg['api_key']; LOG = cfg['log']
U = 'http://127.0.0.1:%s/v1/chat/completions' % os.environ.get('SPORT','8080')
W = ("system network storage kernel cluster volume packet router bridge thread process memory cache buffer queue "
     "signal socket daemon backup snapshot replica shard index ledger harbor meadow river valley forest canyon "
     "lantern copper silver amber violet crimson marble granite willow cedar maple falcon heron otter badger").split()
def filler(rng, n_par):
    out = []
    for p in range(n_par):
        sents = []
        for _ in range(rng.randint(4, 7)):
            ws = [rng.choice(W) for _ in range(rng.randint(8, 16))]
            ws[0] = ws[0].capitalize()
            if rng.random() < 0.3: ws.insert(rng.randint(1, len(ws) - 1), str(rng.randint(10, 9999)))
            sents.append(" ".join(ws) + ".")
        out.append(f"[Section {p+1}] " + " ".join(sents))
    return out
def post(body, timeout=7200):
    r = urllib.request.Request(U, json.dumps(body).encode(), {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=timeout))
# calibrate tokens per paragraph
rng = random.Random(7); cal = filler(rng, 60)
d = post({"model": "x", "messages": [{"role": "user", "content": "\n".join(cal)}], "max_tokens": 1, "reasoning_effort": "none"})
tpp = d['usage']['prompt_tokens'] / 60.0
target = int(CTX * 0.88); n_par = int(target / tpp)
rng = random.Random(42); pars = filler(rng, n_par)
names = ["ORCHID", "TUNDRA", "QUASAR", "FALCON", "EMBER"]; depths = [0.05, 0.30, 0.55, 0.80, 0.97]
codes = {n: str(random.Random(n).randint(100000, 999999)) for n in names}
for n, dep in zip(names, depths):
    pars.insert(int(len(pars) * dep), f"IMPORTANT NOTE: the access code for vault {n} is {codes[n]}. Remember it.")
doc = "\n".join(pars)
q = ("Below is a long document. Read it and then answer.\n\n" + doc +
     "\n\nQuestion: The document contains access codes for five vaults (ORCHID, TUNDRA, QUASAR, FALCON, EMBER). "
     "List each vault with its code, one per line, as NAME: CODE. Nothing else.")
pos = os.path.getsize(LOG); t0 = time.time()
d = post({"model": "x", "messages": [{"role": "user", "content": q}], "max_tokens": 1200, "reasoning_effort": "low",
          "temperature": 0.6, "top_p": 0.95, "top_k": 64, "min_p": 0.05})
wall = time.time() - t0; time.sleep(1)
new = open(LOG, 'rb').read()[pos:].decode('utf-8', 'replace')
m = re.findall(r'prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms \(([\d.]+) tok/s\), (\d+) generated in (\d+) ms \(([\d.]+) tok/s\), drafts accepted (\d+) of (\d+)', new)
a = d['choices'][0]['message'].get('content') or ''
found = {n: bool(re.search(rf'{n}\D{{0,12}}{codes[n]}', a)) for n in names}
res = {"label": label, "ctx": CTX, "tokens_per_par": round(tpp, 2), "prompt_tokens": d['usage']['prompt_tokens'],
       "fill": round(d['usage']['prompt_tokens'] / CTX, 3), "wall_s": round(wall, 1), "needles_found": sum(found.values()),
       "found": found, "answer": a[:500], "finish": d['choices'][0].get('finish_reason')}
if m:
    g = m[-1]; res.update(prompt_read_s=int(g[3]) / 1000, prompt_tps=float(g[4]), gen_tok=int(g[5]), gen_tps=float(g[7]), drafts=f"{g[8]}/{g[9]}")
os.makedirs('/root/bench', exist_ok=True); json.dump(res, open(f'/root/bench/ctx-{label}.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'answer'}))
