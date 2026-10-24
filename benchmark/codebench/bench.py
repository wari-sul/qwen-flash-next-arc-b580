#!/usr/bin/env python3
"""Coding benchmark runner for Strata servers. Results are appended to JSONL so a crash loses nothing.

usage:
  bench.py validate                      # run reference solutions through every grader (no model)
  bench.py run <label> <config.json> <port> [phases]   phases: code,casual,xhigh,tools,agent (default all)
"""
import json, os, re, sys, time, subprocess, tempfile, shutil, hashlib, urllib.request, urllib.error, pwd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tasks_py1, tasks_py2, tasks_other, tasks_tools
TASKS = tasks_py1.T + tasks_py2.T + tasks_other.T
SANDBOX_USER = "bench"
SAMPLING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0}
XHIGH_IDS = ["impl_expr_eval", "impl_ttl_lru", "decide_rate_limiter", "refactor_invoice", "sql_monthly_cumulative"]

SYSTEM_PROPER = """You are a senior software engineer writing production code.
Rules:
- Follow the requirements exactly. If something is ambiguous, choose the most robust interpretation.
- Use only the standard library / built-in features of the target language.
- Consider edge cases, invalid input and the stated input sizes; pick algorithms with appropriate time and memory complexity.
- Reply with exactly ONE fenced code block containing the complete solution (everything needed to run it: imports, the full code of every function/class you were given or asked for, required exports), with no example usage, tests or prints.
- After the code block, give at most 3 short bullet points on key decisions."""

LANG = {"python": (("python", "py", "python3"), "solution.py", "test.py", ["python3", "test.py"]),
        "js": (("javascript", "js", "node", "nodejs"), "solution.js", "test.js", ["node", "test.js"]),
        "sql": (("sql", "sqlite"), "solution.sql", "test.py", ["python3", "test.py"]),
        "bash": (("bash", "sh", "shell"), "solution.sh", "test.py", ["python3", "test.py"])}
LANG_NAME = {"python": "Python 3", "js": "Node.js (JavaScript)", "sql": "SQLite SQL", "bash": "Bash"}

def extract(text, lang):
    blocks = re.findall(r"```([A-Za-z0-9_+-]*)[^\n]*\n(.*?)```", text, re.S)
    tags = LANG[lang][0]
    tagged = [b for t, b in blocks if t.lower() in tags]
    pool = tagged or [b for t, b in blocks if not t] or [b for t, b in blocks]
    if not pool:
        return text.strip()
    return max(pool, key=len)

def run_sandboxed(task, code):
    d = tempfile.mkdtemp(prefix="cb_")
    try:
        _, sol, test, cmd = LANG[task["lang"]]
        with open(os.path.join(d, sol), "w") as f: f.write(code)
        with open(os.path.join(d, test), "w") as f: f.write(task["tests"])
        sandbox = SANDBOX_USER and os.geteuid() == 0
        if sandbox:
            pw = pwd.getpwnam(SANDBOX_USER); os.chown(d, pw.pw_uid, pw.pw_gid)
            for fn in os.listdir(d): os.chown(os.path.join(d, fn), pw.pw_uid, pw.pw_gid)
            cmd = ["/usr/sbin/runuser", "-u", SANDBOX_USER, "--"] + cmd
        t = time.time()
        try:
            r = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=task.get("timeout", 30),
                               env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": d, "LANG": "C.UTF-8"})
            ok = r.returncode == 0 and "PASS" in r.stdout
            detail = (r.stdout + r.stderr)[-600:]
        except subprocess.TimeoutExpired:
            ok, detail = False, "TIMEOUT"
        return ok, detail, round(time.time() - t, 2)
    finally:
        shutil.rmtree(d, ignore_errors=True)

def candidates(text, lang):
    """All code blocks, language-tagged ones first, longest first. A user copies the block that is the solution;
    usage-example blocks cannot pass the tests, so trying each block is fair and model-independent."""
    blocks = re.findall(r"```([A-Za-z0-9_+-]*)[^\n]*\n(.*?)```", text, re.S)
    tags = LANG[lang][0]
    tagged = sorted([b for t, b in blocks if t.lower() in tags], key=len, reverse=True)
    rest = sorted([b for t, b in blocks if t.lower() not in tags], key=len, reverse=True)
    c = tagged + rest
    return c if c else [text.strip()]

def grade_code(task, text):
    first = None
    for i, code in enumerate(candidates(text, task["lang"])[:4]):
        bad = next((b for b in task.get("forbid", []) if b in code), None)
        if bad:
            res = (False, f"forbidden: {bad}", 0.0, code)
        else:
            ok, detail, el = run_sandboxed(task, code)
            res = (ok, detail if i == 0 else f"[block {i}] {detail}", el, code)
        if res[0]:
            return res
        first = first or res
    return first

def build_messages(task, style):
    lang = LANG_NAME[task["lang"]]
    if style == "proper":
        body = f"Language: {lang}\n\n{task['spec']}"
        if task.get("given"):
            body += f"\n\n## Current code\n```{ {'python':'python','js':'javascript','sql':'sql','bash':'bash'}[task['lang']] }\n{task['given']}```"
        return [{"role": "system", "content": SYSTEM_PROPER}, {"role": "user", "content": body}]
    body = task["casual"]
    if task.get("given"):
        body += "\n\n" + task["given"]
    return [{"role": "user", "content": body}]

# ---------------- server access ----------------
class Server:
    def __init__(self, cfg_path, port):
        cfg = json.load(open(cfg_path)); self.key = cfg["api_key"]; self.log = cfg["log"]; self.base = f"http://127.0.0.1:{port}"
    def post(self, path, body, timeout=3600, anth=False):
        h = {"Content-Type": "application/json"}
        if anth: h.update({"x-api-key": self.key, "anthropic-version": "2023-06-01"})
        else: h["Authorization"] = "Bearer " + self.key
        pos = os.path.getsize(self.log) if os.path.exists(self.log) else 0
        t = time.time(); err = None
        try:
            resp = json.load(urllib.request.urlopen(urllib.request.Request(self.base + path, json.dumps(body).encode(), h), timeout=timeout))
        except urllib.error.HTTPError as e:
            resp, err = None, f"HTTP {e.code}: {e.read()[:300]!r}"
        except Exception as e:
            resp, err = None, repr(e)[:300]
        wall = time.time() - t; time.sleep(0.4)
        eng = {}
        try:
            with open(self.log, "rb") as f:
                f.seek(pos); new = f.read().decode("utf-8", "replace")
            m = re.findall(r"prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms \(([\d.]+) tok/s\), (\d+) generated in (\d+) ms \(([\d.]+) tok/s\), drafts accepted (\d+) of (\d+)", new)
            if m:
                eng = dict(prompt_tokens=sum(int(x[0]) for x in m), prompt_reused=sum(int(x[1]) for x in m), prompt_read_ms=sum(int(x[3]) for x in m),
                           gen_tokens=sum(int(x[5]) for x in m), gen_ms=sum(int(x[6]) for x in m),
                           drafts_accepted=sum(int(x[8]) for x in m), drafts_proposed=sum(int(x[9]) for x in m), engine_calls=len(m))
        except FileNotFoundError:
            pass
        return resp, err, round(wall, 2), eng

def usage_of(resp):
    u = (resp or {}).get("usage") or {}
    return {"prompt_tokens": u.get("prompt_tokens", u.get("input_tokens")), "completion_tokens": u.get("completion_tokens", u.get("output_tokens"))}

def out(fh, rec):
    fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
    print(f"[{time.strftime('%H:%M:%S')}] {rec['phase']:6s} {rec['id']:28s} rep{rec.get('rep',0)} ok={rec.get('ok')} "
          f"tok={rec.get('completion_tokens')} wall={rec.get('wall')}s gen_tps={rec.get('gen_tps')} {rec.get('note','')[:60]}", flush=True)

def code_phase(srv, fh, label, style, effort, ids=None, reps=1, phase="code"):
    for rep in range(reps):
        for task in TASKS:
            if ids and task["id"] not in ids: continue
            body = {"model": "x", "messages": build_messages(task, style), "max_tokens": 16000 if effort == "xhigh" else 12000,
                    "reasoning_effort": effort, **SAMPLING}
            resp, err, wall, eng = srv.post("/v1/chat/completions", body)
            rec = dict(model=label, phase=phase, style=style, effort=effort, id=task["id"], cat=task["cat"], lang=task["lang"], rep=rep, wall=wall, **eng)
            if err:
                rec.update(ok=False, note=err); out(fh, rec); continue
            msg = resp["choices"][0]["message"]; text = msg.get("content") or ""
            ok, detail, test_s, code = grade_code(task, text)
            rec.update(usage_of(resp), ok=ok, finish=resp["choices"][0].get("finish_reason"), test_s=test_s,
                       reasoning_chars=len(msg.get("reasoning_content") or ""), answer_chars=len(text), code_lines=code.count("\n") + 1,
                       gen_tps=round(eng["gen_tokens"] / (eng["gen_ms"] / 1000), 1) if eng.get("gen_ms") else None,
                       note="" if ok else detail.replace("\n", " ")[-200:], answer=text, reasoning=(msg.get("reasoning_content") or "")[-4000:])
            out(fh, rec)

def tools_phase(srv, fh, label, reps=2):
    for rep in range(reps):
        for c in tasks_tools.TOOL_CASES:
            body = {"model": "x", "messages": c["messages"], "tools": c["tools"], "max_tokens": 4000, "reasoning_effort": "low", **SAMPLING}
            resp, err, wall, eng = srv.post("/v1/chat/completions", body)
            rec = dict(model=label, phase="tools", id=c["id"], rep=rep, wall=wall, **eng)
            if err: rec.update(ok=False, note=err); out(fh, rec); continue
            msg = resp["choices"][0]["message"]
            try: ok = bool(c["grade"](msg))
            except Exception as e: ok = False
            rec.update(usage_of(resp), ok=ok, finish=resp["choices"][0].get("finish_reason"),
                       note="" if ok else json.dumps({"content": (msg.get("content") or "")[:150], "calls": msg.get("tool_calls")})[:300],
                       gen_tps=round(eng["gen_tokens"] / (eng["gen_ms"] / 1000), 1) if eng.get("gen_ms") else None)
            out(fh, rec)
        for c in tasks_tools.ANTH_CASES:
            body = {"model": "x", "max_tokens": 4000, "messages": c["messages"], "tools": tasks_tools.ANTH_TOOLS, "temperature": 0.6}
            resp, err, wall, eng = srv.post("/v1/messages", body, anth=True)
            rec = dict(model=label, phase="tools", id=c["id"], rep=rep, wall=wall, **eng)
            if err: rec.update(ok=False, note=err); out(fh, rec); continue
            try: ok = bool(c["grade"](resp))
            except Exception: ok = False
            rec.update(usage_of(resp), ok=ok, note="" if ok else json.dumps(resp.get("content"))[:300],
                       gen_tps=round(eng["gen_tokens"] / (eng["gen_ms"] / 1000), 1) if eng.get("gen_ms") else None)
            out(fh, rec)

def repo_tests(d, timeout=90):
    cmd = ["python3", "-m", "unittest", "-q"]
    if os.geteuid() == 0:
        pw = pwd.getpwnam(SANDBOX_USER)
        for root, dirs, files in os.walk(d):
            for x in dirs + files: os.chown(os.path.join(root, x), pw.pw_uid, pw.pw_gid)
        os.chown(d, pw.pw_uid, pw.pw_gid); cmd = ["/usr/sbin/runuser", "-u", SANDBOX_USER, "--"] + cmd
    try:
        r = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=timeout,
                           env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": d, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"})
        return r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT: the test run took longer than %ds" % timeout

def agent_phase(srv, fh, label, reps=2, max_turns=16):
    for rep in range(reps):
        for repo in tasks_tools.REPOS:
            d = tempfile.mkdtemp(prefix="ag_")
            for p, c in repo["files"].items():
                os.makedirs(os.path.dirname(os.path.join(d, p)) or d, exist_ok=True)
                open(os.path.join(d, p), "w").write(c)
            test_hash = {p: hashlib.sha256(c.encode()).hexdigest() for p, c in repo["files"].items() if "test" in p}
            msgs = [{"role": "system", "content": tasks_tools.AGENT_SYSTEM}, {"role": "user", "content": repo["task"]}]
            st = dict(turns=0, tool_calls=0, reads=0, writes=0, test_runs=0, list_calls=0, bad_calls=0, prompt_tokens=0, completion_tokens=0,
                      gen_tokens=0, gen_ms=0, prompt_read_ms=0, wall=0.0, finished=False, error="")
            t0 = time.time()
            for turn in range(max_turns):
                body = {"model": "x", "messages": msgs, "tools": tasks_tools.AGENT_TOOLS, "max_tokens": 8000, "reasoning_effort": "low", **SAMPLING}
                resp, err, wall, eng = srv.post("/v1/chat/completions", body)
                st["turns"] += 1
                for k in ("gen_tokens", "gen_ms", "prompt_read_ms"): st[k] += eng.get(k, 0)
                if err: st["error"] = err; break
                u = usage_of(resp); st["prompt_tokens"] += u["prompt_tokens"] or 0; st["completion_tokens"] += u["completion_tokens"] or 0
                m = resp["choices"][0]["message"]; calls = m.get("tool_calls") or []
                msgs.append({"role": "assistant", "content": m.get("content") or "", **({"tool_calls": calls} if calls else {})})
                if not calls: st["finished"] = True; st["summary"] = (m.get("content") or "")[:400]; break
                for c in calls:
                    st["tool_calls"] += 1; name = c["function"]["name"]
                    try: a = json.loads(c["function"].get("arguments") or "{}")
                    except Exception: a = None
                    try:
                        if a is None: raise ValueError("arguments are not valid JSON")
                        if name == "list_files":
                            st["list_calls"] += 1
                            res = "\n".join(sorted(os.path.relpath(os.path.join(r, f), d) for r, _, fs in os.walk(d) for f in fs if "__pycache__" not in r))
                        elif name == "read_file":
                            st["reads"] += 1; p = os.path.normpath(os.path.join(d, a["path"]))
                            if not p.startswith(d): raise ValueError("path outside repo")
                            res = open(p).read()
                        elif name == "write_file":
                            st["writes"] += 1; p = os.path.normpath(os.path.join(d, a["path"]))
                            if not p.startswith(d): raise ValueError("path outside repo")
                            os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(a["content"]); res = f"wrote {len(a['content'])} bytes to {a['path']}"
                        elif name == "run_tests":
                            st["test_runs"] += 1; ok_, o = repo_tests(d); res = ("PASSED\n" if ok_ else "FAILED\n") + o
                        else:
                            raise ValueError(f"unknown tool {name}")
                    except Exception as e:
                        st["bad_calls"] += 1; res = f"ERROR: {e}"
                    msgs.append({"role": "tool", "tool_call_id": c.get("id", "x"), "content": res[:12000]})
            st["wall"] = round(time.time() - t0, 1)
            passed, tail = repo_tests(d)
            tampered = any(hashlib.sha256(open(os.path.join(d, p)).read().encode()).hexdigest() != h for p, h in test_hash.items())
            rec = dict(model=label, phase="agent", id=repo["id"], rep=rep, ok=passed and not tampered and st["finished"], tests_pass=passed,
                       tests_tampered=tampered, **st, gen_tps=round(st["gen_tokens"] / (st["gen_ms"] / 1000), 1) if st["gen_ms"] else None,
                       note="" if passed else tail.replace("\n", " ")[-200:])
            out(fh, rec)
            shutil.rmtree(d, ignore_errors=True)

def validate():
    bad = 0
    for t in TASKS:
        ok, detail, el = run_sandboxed(t, t["ref"])
        print(f"{'OK ' if ok else 'BAD'} {t['id']:28s} {el:5.2f}s {'' if ok else detail[-300:]}")
        bad += not ok
        if t.get("given"):
            ok2, _, _ = run_sandboxed(t, t["given"])
            print(f"    given code {'PASSES (grader too weak!)' if ok2 else 'fails as expected'}"); bad += ok2
    return bad

if __name__ == "__main__":
    if sys.argv[1] == "validate":
        sys.exit(1 if validate() else 0)
    label, cfg, port = sys.argv[2], sys.argv[3], int(sys.argv[4])
    phases = (sys.argv[5] if len(sys.argv) > 5 else "code,casual,xhigh,tools,agent").split(",")
    srv = Server(cfg, port)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", f"{label}.jsonl"), "a") as fh:
        if "code" in phases: code_phase(srv, fh, label, "proper", "low", reps=2, phase="code")
        if "casual" in phases: code_phase(srv, fh, label, "casual", "low", reps=1, phase="casual")
        if "xhigh" in phases: code_phase(srv, fh, label, "proper", "xhigh", ids=XHIGH_IDS, reps=1, phase="xhigh")
        if "tools" in phases: tools_phase(srv, fh, label, reps=2)
        if "agent" in phases: agent_phase(srv, fh, label, reps=2)
    print("BENCH-DONE", label)
