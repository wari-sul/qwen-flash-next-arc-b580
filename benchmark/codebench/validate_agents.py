import os, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench, tasks_tools
FIX = {
"ag_bugfix": {"textstats/stats.py": '''def words(text):
    return text.split()
def word_count(text):
    return len(words(text))
def avg_word_length(text):
    w = words(text)
    return sum(len(x) for x in w) / len(w) if w else 0.0
'''},
"ag_feature": {"todo.py": '''class TodoList:
    def __init__(self):
        self._items = []; self._next = 1
    def add(self, title, due=None, priority=2):
        if type(priority) is not int or priority not in (1, 2, 3): raise ValueError(priority)
        it = {"id": self._next, "title": title, "done": False, "due": due, "priority": priority}
        self._items.append(it); self._next += 1; return it["id"]
    def complete(self, item_id):
        for it in self._items:
            if it["id"] == item_id: it["done"] = True; return
        raise KeyError(item_id)
    def _sorted(self):
        p = [it for it in self._items if not it["done"]]
        return sorted(p, key=lambda it: (it["priority"], it["due"] is None, it["due"] or 0, it["id"]))
    def pending(self):
        return [it["title"] for it in self._sorted()]
    def overdue(self, today):
        return [it["title"] for it in self._sorted() if it["due"] is not None and it["due"] < today]
'''},
"ag_crossfile": {"config.py": '''def load_config(env):
    raw = env.get("APP_PORT", "8080")
    try: port = int(raw)
    except (TypeError, ValueError): raise ValueError(f"invalid port {raw!r}")
    if not 1 <= port <= 65535: raise ValueError(f"port out of range {port}")
    return {"host": env.get("APP_HOST", "127.0.0.1"), "port": port}
''', "app.py": '''from config import load_config
def server_address(env):
    cfg = load_config(env)
    return f"http://{cfg['host']}:{cfg['port']}"
def is_privileged(env):
    return load_config(env)["port"] < 1024
'''},
"ag_perf": {"dedupe.py": '''from collections import Counter
def find_duplicates(items):
    return sorted(k for k, v in Counter(items).items() if v > 1)
'''},
"ag_vague": {"slug.py": '''import re, unicodedata
def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")
'''},
}
bad = 0
for repo in tasks_tools.REPOS:
    for fixed in (False, True):
        d = tempfile.mkdtemp()
        files = dict(repo["files"]); files.update(FIX[repo["id"]] if fixed else {})
        for p, c in files.items():
            os.makedirs(os.path.dirname(os.path.join(d, p)) or d, exist_ok=True); open(os.path.join(d, p), "w").write(c)
        ok, o = bench.repo_tests(d)
        good = ok == fixed
        print(f"{'OK ' if good else 'BAD'} {repo['id']:14s} {'fixed' if fixed else 'original'}: tests {'pass' if ok else 'fail'}" + ("" if good else " :: " + o[-400:]))
        bad += not good
        shutil.rmtree(d, ignore_errors=True)
sys.exit(1 if bad else 0)
