#!/usr/bin/env python3
"""Graded quality + speed suite for the MTP A/B (code-graded, no model judging)."""
import json, sys, time, re, os, subprocess, tempfile, urllib.request
label = sys.argv[1]; reps = int(sys.argv[2])
cfg = json.load(open(os.environ.get('SCFG','/etc/strata/davidau-iq3s-256k.json'))); KEY = cfg['api_key']; LOG = cfg['log']
U = 'http://127.0.0.1:%s/v1/chat/completions' % os.environ.get('SPORT','8080')
def num(a): m = re.findall(r'-?\d[\d,]*\.?\d*', a.replace(',', '')); return m[-1] if m else None
def pycheck(code, tests):
    m = re.search(r'```(?:python)?\n(.*?)```', code, re.S); src = m.group(1) if m else code
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f: f.write(src + '\n' + tests); p = f.name
    try: return subprocess.run(['python3', p], capture_output=True, timeout=20).returncode == 0
    except Exception: return False
LOGTXT = "\n".join(f"10.0.0.{i%7} - - [x] \"GET / HTTP/1.1\" 200 1" for i in range(50))
def bashcheck(ans):
    m = re.search(r'```(?:bash|sh)?\n(.*?)```', ans, re.S); cmd = (m.group(1) if m else ans).strip().splitlines()
    cmd = [c for c in cmd if c.strip() and not c.strip().startswith('#')]
    if not cmd: return False
    d = tempfile.mkdtemp(); open(f'{d}/access.log', 'w').write(LOGTXT + "\n")
    try: r = subprocess.run(['bash', '-c', cmd[0]], cwd=d, capture_output=True, text=True, timeout=10); return r.stdout.strip().split()[-1:] == ['7']
    except Exception: return False
T = [
 ("arith1", "What is 37*43 - 289? Give only the final number.", lambda a: num(a) == "1302"),
 ("arith2", "Compute (2^10 + 3^5) mod 97. Only the number.", lambda a: num(a) == str((2**10 + 3**5) % 97)),
 ("arith3", "A shop sells pens at 3 for $2. How many dollars do 27 pens cost? Only the number.", lambda a: num(a) in ("18", "18.00", "18.0")),
 ("word1", "A train leaves at 09:40 and arrives at 13:15. How many minutes is the trip? Only the number.", lambda a: num(a) == "215"),
 ("word2", "If 5 machines make 5 widgets in 5 minutes, how many minutes do 100 machines need for 100 widgets? Only the number.", lambda a: num(a) == "5"),
 ("logic1", "Alice is older than Bob. Bob is older than Carol. Is Carol older than Alice? Answer only yes or no.", lambda a: a.strip().lower().startswith("no")),
 ("logic2", "All bloops are razzies. All razzies are lazzies. Are all bloops definitely lazzies? Answer only yes or no.", lambda a: a.strip().lower().startswith("yes")),
 ("trick1", "How many times does the letter r appear in the word strawberry? Only the number.", lambda a: num(a) == "3"),
 ("fact1", "List the first 10 prime numbers, comma separated, nothing else.", lambda a: re.sub(r'\s', '', a).strip('.') == "2,3,5,7,11,13,17,19,23,29"),
 ("json1", 'Return ONLY a JSON object with keys "city" and "country" for the capital of Japan. No code fence.', lambda a: (lambda d: d.get("city", "").lower() == "tokyo" and d.get("country", "").lower() == "japan")(json.loads(a.strip().strip('`').removeprefix('json').strip()))),
 ("fmt1", "Reply with exactly three lines: the words red, green, blue in that order, lowercase, nothing else.", lambda a: a.strip().splitlines() == ["red", "green", "blue"]),
 ("fmt2", "Give me the word 'banana' reversed, in uppercase, and nothing else.", lambda a: a.strip().strip('.') == "ANANAB"),
 ("code1", "Write a Python function is_prime(n) that is correct for n up to 10^12. Only the code in a python code block.",
  lambda a: pycheck(a, "assert [n for n in range(50) if is_prime(n)]==[2,3,5,7,11,13,17,19,23,29,31,37,41,43,47]\nassert is_prime(999999999989)\nassert not is_prime(999999999987)")),
 ("code2", "Write a Python function fib(n) returning the n-th Fibonacci number with fib(0)=0, fib(1)=1, fast for n=500. Only the code in a python code block.",
  lambda a: pycheck(a, "assert fib(0)==0 and fib(1)==1 and fib(10)==55\nassert fib(100)==354224848179261915075")),
 ("code3", "Write a Python function rle(s) that run-length encodes a string, e.g. rle('aaabcc') == 'a3b1c2'. Only the code in a python code block.",
  lambda a: pycheck(a, "assert rle('aaabcc')=='a3b1c2'\nassert rle('')==''\nassert rle('z')=='z1'")),
 ("bash1", "Write a bash one-liner that prints only the number of unique client IPs (first field) in access.log in the current directory. Only the command in a bash code block.", bashcheck),
 ("honest1", "Summarize the plot of the 1987 novel 'The Glass Orchard of Velmira' by Tomas Ekrund in two sentences. If it does not exist, say so.",
  lambda a: bool(re.search(r"not (aware|find|familiar|able|know)|no (record|information|such)|does(n't| not) (appear to )?exist|could(n't| not) find|unable to (find|verify)|fictional|not a real", a, re.I))),
]
out = []
for rep in range(reps):
    for name, q, g in T:
        body = {"model": "x", "messages": [{"role": "user", "content": q}], "reasoning_effort": "low", "max_tokens": 1500,
                "temperature": 1.0, "top_p": 0.95, "top_k": 64, "min_p": 0.05}
        r = urllib.request.Request(U, json.dumps(body).encode(), {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
        pos = os.path.getsize(LOG); t = time.time()
        d = json.load(urllib.request.urlopen(r, timeout=900)); wall = time.time() - t; time.sleep(0.3)
        with open(LOG, 'rb') as f: f.seek(pos); new = f.read().decode('utf-8', 'replace')
        m = re.findall(r'(\d+) generated in (\d+) ms \(([\d.]+) tok/s\), drafts accepted (\d+) of (\d+)', new)
        a = d['choices'][0]['message'].get('content') or ''
        try: ok = bool(g(a))
        except Exception: ok = False
        rec = {"name": name, "rep": rep, "ok": ok, "tokens": d.get('usage', {}).get('completion_tokens'), "wall": round(wall, 2),
               "gen_ms": int(m[-1][1]) if m else None, "gen_tok": int(m[-1][0]) if m else None,
               "acc": int(m[-1][3]) if m else None, "prop": int(m[-1][4]) if m else None, "answer": a[:400]}
        out.append(rec); print(f"{label} r{rep} {name}: ok={ok} {rec['tokens']}tok {m[-1][2] if m else '?'}tok/s drafts {rec['acc']}/{rec['prop']}", flush=True)
json.dump(out, open(f'/root/bench/q-{label}.json', 'w'), indent=1)
ok = sum(r['ok'] for r in out); gt = sum(r['gen_tok'] or 0 for r in out); gm = sum(r['gen_ms'] or 0 for r in out)
print(f"SUMMARY {label}: {ok}/{len(out)} correct, {gt} tokens, aggregate {gt/(gm/1000):.1f} tok/s, wall {sum(r['wall'] for r in out):.0f}s")
