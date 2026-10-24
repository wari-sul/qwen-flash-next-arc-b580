#!/usr/bin/env python3
"""MTP A/B bench: same prompts, greedy + sampled, records answers and engine tok/s from the engine log."""
import json, sys, time, re, urllib.request, os
label = sys.argv[1]; reps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
cfg = json.load(open('/etc/strata/davidau-iq3s-256k.json')); KEY = cfg['api_key']; LOG = cfg['log']
U = 'http://127.0.0.1:8080/v1/chat/completions'
P = [
 ("arith", "What is 37*43 - 289? Give only the final number."),
 ("logic", "Alice is older than Bob. Bob is older than Carol. Is Carol older than Alice? Answer yes or no and one sentence why."),
 ("code", "Write a Python function is_prime(n) that is efficient for n up to 10^12. Only the code."),
 ("bash", "Write a bash one-liner that counts unique IP addresses in an nginx access.log (first field)."),
 ("explain", "Explain in 4 sentences how LVM thin provisioning works."),
 ("json", 'Return ONLY a JSON object with keys "city" and "country" for the capital of Japan.'),
 ("prose", "Write a short paragraph (about 80 words) describing a thunderstorm over a city at night."),
 ("fact", "List the first 10 prime numbers, comma separated, nothing else."),
]
def call(msg, temp):
    body = {"model": "x", "messages": [{"role": "user", "content": msg}], "reasoning_effort": "low",
            "max_tokens": 700, "temperature": temp, "top_p": 0.95, "top_k": 64, "min_p": 0.05, "seed": 1}
    if temp == 0: body.update(temperature=0, top_k=1)
    r = urllib.request.Request(U, json.dumps(body).encode(), {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    pos = os.path.getsize(LOG); t = time.time()
    d = json.load(urllib.request.urlopen(r, timeout=900)); wall = time.time() - t
    time.sleep(0.5)
    with open(LOG, 'rb') as f: f.seek(pos); new = f.read().decode('utf-8', 'replace')
    m = re.findall(r'(\d+) generated in (\d+) ms \(([\d.]+) tok/s\), drafts accepted (\d+) of (\d+)', new)
    g = m[-1] if m else None
    msg = d['choices'][0]['message']
    return {"answer": msg.get('content') or '', "reasoning": msg.get('reasoning_content') or '',
            "tokens": d.get('usage', {}).get('completion_tokens'), "wall": round(wall, 2),
            "gen_tps": float(g[2]) if g else None, "drafts": f"{g[3]}/{g[4]}" if g else None}
out = []
for mode, temp in (("greedy", 0), ("sampled", 1.0)):
    for rep in range(reps if mode == "sampled" else 1):
        for name, msg in P:
            r = call(msg, temp); r.update(name=name, mode=mode, rep=rep); out.append(r)
            print(f"{label} {mode} {name} rep{rep}: {r['tokens']} tok, {r['gen_tps']} tok/s, drafts {r['drafts']}, {r['wall']}s", flush=True)
os.makedirs('/root/bench', exist_ok=True)
json.dump(out, open(f'/root/bench/{label}.json', 'w'), indent=1)
