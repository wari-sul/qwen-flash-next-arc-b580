#!/usr/bin/env python3
"""Run the hard test set against Strata with the model's default reasoning (no effort override), save full replies."""
import json, time, re, os, urllib.request
cfg = json.load(open(os.environ.get('SCFG','/etc/strata/davidau-iq3s-256k.json'))); K = cfg['api_key']; LOG = cfg['log']
U = 'http://127.0.0.1:%s/v1/chat/completions' % os.environ.get('SPORT','8080')
T = {
"t01": "How many positive integers n ≤ 1000 make n² + 1 divisible by 5? Explain briefly.",
"t02": "What are the last two digits of 7^2026?",
"t03": "Two fair dice are rolled. Given that at least one die shows a 6, what is the probability that the sum is prime? Give an exact fraction.",
"t04": "Pipe A fills a tank in 6 hours, pipe B in 4 hours, and drain C empties a full tank in 3 hours. All three are opened on an empty tank. After 2 hours, drain C is closed. How many hours in total does it take to fill the tank?",
"t05": "Monty Hall variant: There are 3 doors, one car and two goats. You pick door 1. The host does NOT know where the car is; he opens door 3 at random, and it happens to show a goat. What is your probability of winning if you switch to door 2? Explain.",
"t06": "A says: \"B is a knave.\" B says: \"A and C are the same type.\" Knights always tell the truth and knaves always lie. What is C? Prove it.",
"t07": """Four friends (Ana, Ben, Cy, Dee) live in houses 1–4 in a row, with house 1 on the far left. Each has a different pet (cat, dog, fish, bird) and a different drink (tea, coffee, milk, water).
1. The cat owner lives next to the dog owner.
2. Ana lives somewhere to the left of Ben.
3. The person in house 3 drinks milk.
4. Cy doesn't own the fish and doesn't drink tea.
5. The fish is in house 1.
6. The bird owner drinks coffee.
7. Dee lives next to the water drinker.
8. Ana doesn't drink water.
9. The tea drinker lives to the left of the bird owner.
10. Dee doesn't own the cat.
11. Ben doesn't own the bird.
12. Ben doesn't live in house 4.
Give each person's house, pet and drink.""",
"t08": "Write a Python function `longest_palindrome(s: str) -> str` that returns the longest palindromic substring, using the first one if there's a tie. It must handle a 5,000-character string in well under a second. Code only.",
"t09": "Write a Python class `LRUCache(capacity)` with `get(key)` (returns -1 if missing) and `put(key, value)`, both O(1), without using `functools` or `OrderedDict`. Code only.",
"t10": "Write one sentence of exactly 12 words in which every word starts with the letter \"s\" and the 5th word is \"silver\". Then list the words numbered 1–12.",
"t11": "Summarize the main conclusion of the 2019 paper \"Recursive Lattice Folding for Sparse MoE Routing\" by Hendrika Voss.",
"t12": "On a Linux server, `df -h` shows a filesystem 100% full, but `du -sh` on its mount point shows only 40% used. Give the most common cause and the exact command to find the culprit, then explain how to free the space without a reboot.",
"t13": "{REASON:help} Show me the detailed help menu.",
}
T["t07L"] = "{REASON:logic} " + T["t07"]
out = {}
for k, q in T.items():
    b = {"model": "x", "messages": [{"role": "user", "content": q}], "max_tokens": 16000,
         "temperature": 1.0, "top_p": 0.95, "top_k": 64, "min_p": 0.05}
    pos = os.path.getsize(LOG); t = time.time()
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(U, json.dumps(b).encode(), {"Authorization": "Bearer " + K, "Content-Type": "application/json"}), timeout=3600))
    except Exception as e:
        out[k] = {"error": str(e)}; print(k, "ERROR", e, flush=True); continue
    wall = time.time() - t; time.sleep(0.5)
    new = open(LOG, 'rb').read()[pos:].decode('utf-8', 'replace')
    m = re.findall(r'prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms \(([\d.]+) tok/s\), (\d+) generated in (\d+) ms \(([\d.]+) tok/s\)', new)
    msg = d['choices'][0]['message']; u = d.get('usage', {})
    out[k] = {"q": q, "answer": msg.get('content') or '', "reasoning": msg.get('reasoning_content') or '',
              "prompt_tokens": u.get('prompt_tokens'), "completion_tokens": u.get('completion_tokens'),
              "reasoning_tokens": (u.get('completion_tokens_details') or {}).get('reasoning_tokens'),
              "finish": d['choices'][0].get('finish_reason'), "wall": round(wall, 1),
              "gen_tps": float(m[-1][7]) if m else None}
    print(k, out[k]["completion_tokens"], "tok", out[k]["gen_tps"], "tok/s", out[k]["wall"], "s", out[k]["finish"], flush=True)
    json.dump(out, open('/root/bench/hardtest-%s.json' % os.environ.get('SLABEL','main'), 'w'), indent=1, ensure_ascii=False)
print("HARDTEST-DONE")
