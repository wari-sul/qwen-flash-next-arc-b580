# Tool-calling cases and multi-step agent repositories.

WEATHER = {"type": "function", "function": {"name": "get_weather", "description": "Current weather for a city.",
  "parameters": {"type": "object", "properties": {"city": {"type": "string"}, "unit": {"type": "string", "enum": ["c", "f"]}}, "required": ["city", "unit"]}}}
SEARCH = {"type": "function", "function": {"name": "search_files", "description": "Search file contents for a regex pattern under a directory. Returns matching lines.",
  "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern", "path"]}}}
READ = {"type": "function", "function": {"name": "read_file", "description": "Read one file.",
  "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}
RUN = {"type": "function", "function": {"name": "run_command", "description": "Run a shell command. Only use when no dedicated tool fits.",
  "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}, "timeout_s": {"type": "integer"}}, "required": ["cmd"]}}}
EVENT = {"type": "function", "function": {"name": "create_event", "description": "Create a calendar event.",
  "parameters": {"type": "object", "properties": {
     "title": {"type": "string"}, "start": {"type": "string", "description": "ISO 8601 local datetime, e.g. 2026-01-31T09:00"},
     "duration_minutes": {"type": "integer"}, "priority": {"type": "string", "enum": ["low", "normal", "high"]},
     "attendees": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "email": {"type": "string"}}, "required": ["name", "email"]}}},
   "required": ["title", "start", "duration_minutes", "priority", "attendees"]}}}
ALL = [WEATHER, SEARCH, READ, RUN, EVENT]

def _calls(msg):
    out = []
    for c in msg.get("tool_calls") or []:
        import json
        try: args = json.loads(c["function"]["arguments"])
        except Exception: args = None
        out.append((c["function"]["name"], args))
    return out

def g_single(msg):
    c = _calls(msg)
    return len(c) == 1 and c[0][0] == "get_weather" and isinstance(c[0][1], dict) and "oslo" in str(c[0][1].get("city", "")).lower() and c[0][1].get("unit") == "c"
def g_parallel(msg):
    c = _calls(msg); cities = {str((a or {}).get("city", "")).lower() for n, a in c if n == "get_weather"}
    return any("paris" in x for x in cities) and any("tokyo" in x for x in cities) and all((a or {}).get("unit") == "f" for n, a in c if n == "get_weather")
def g_none(msg):
    return not _calls(msg) and "paris" in (msg.get("content") or "").lower()
def g_choose(msg):
    c = _calls(msg)
    return len(c) >= 1 and c[0][0] == "search_files" and "todo" in str(c[0][1].get("pattern", "")).lower() and "src" in str(c[0][1].get("path", ""))
def g_args(msg):
    c = _calls(msg)
    if len(c) != 1 or c[0][0] != "create_event" or not isinstance(c[0][1], dict): return False
    a = c[0][1]; att = a.get("attendees") or []
    emails = sorted(str(x.get("email", "")).lower() for x in att if isinstance(x, dict))
    return (str(a.get("start", "")).startswith("2026-10-27T14:30") and a.get("duration_minutes") == 45 and isinstance(a.get("duration_minutes"), int)
            and a.get("priority") == "high" and emails == ["ana@x.io", "ben@x.io"] and "release review" in str(a.get("title", "")).lower())
def g_followup(msg):
    t = (msg.get("content") or "").lower()
    return not _calls(msg) and "-3" in t and "snow" in t

TOOL_CASES = [
 dict(id="tc_single", tools=[WEATHER, SEARCH], messages=[{"role": "user", "content": "What's the weather in Oslo right now? Use celsius."}], grade=g_single),
 dict(id="tc_parallel", tools=[WEATHER], messages=[{"role": "user", "content": "Compare the current weather in Paris and Tokyo, in fahrenheit."}], grade=g_parallel),
 dict(id="tc_no_tool", tools=ALL, messages=[{"role": "user", "content": "What is the capital of France? Answer in one word."}], grade=g_none),
 dict(id="tc_choose_tool", tools=ALL, messages=[{"role": "user", "content": "Find every TODO comment in the src folder."}], grade=g_choose),
 dict(id="tc_complex_args", tools=ALL, messages=[{"role": "user", "content": "Schedule 'Release review' on 2026-10-27 at 14:30 for 45 minutes, high priority, with Ana (ana@x.io) and Ben (ben@x.io)."}], grade=g_args),
 dict(id="tc_use_result", tools=[WEATHER], messages=[
    {"role": "user", "content": "What's the weather in Oslo? Celsius please."},
    {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "get_weather", "arguments": "{\"city\": \"Oslo\", \"unit\": \"c\"}"}}]},
    {"role": "tool", "tool_call_id": "call_1", "content": "{\"temp_c\": -3, \"condition\": \"light snow\", \"wind_kmh\": 12}"}], grade=g_followup),
]

ANTH_TOOLS = [{"name": "get_weather", "description": "Current weather for a city.",
               "input_schema": {"type": "object", "properties": {"city": {"type": "string"}, "unit": {"type": "string", "enum": ["c", "f"]}}, "required": ["city", "unit"]}}]
def ga_call(resp):
    b = [x for x in resp.get("content", []) if x.get("type") == "tool_use"]
    return resp.get("stop_reason") == "tool_use" and len(b) == 1 and b[0]["name"] == "get_weather" and "berlin" in str(b[0]["input"].get("city", "")).lower()
def ga_result(resp):
    t = " ".join(x.get("text", "") for x in resp.get("content", []) if x.get("type") == "text").lower()
    return not [x for x in resp.get("content", []) if x.get("type") == "tool_use"] and "21" in t and "sun" in t
ANTH_CASES = [
 dict(id="tc_anthropic_call", messages=[{"role": "user", "content": "How's the weather in Berlin? Celsius."}], grade=ga_call),
 dict(id="tc_anthropic_result", messages=[
    {"role": "user", "content": "How's the weather in Berlin? Celsius."},
    {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_1", "name": "get_weather", "input": {"city": "Berlin", "unit": "c"}}]},
    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "{\"temp_c\": 21, \"condition\": \"sunny\"}"}]}], grade=ga_result),
]

# ---------------- agent repositories ----------------
AGENT_TOOLS = [
 {"type": "function", "function": {"name": "list_files", "description": "List all files in the repository (relative paths).", "parameters": {"type": "object", "properties": {}}}},
 {"type": "function", "function": {"name": "read_file", "description": "Read a file from the repository.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
 {"type": "function", "function": {"name": "write_file", "description": "Create or overwrite a file with the full new content.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
 {"type": "function", "function": {"name": "run_tests", "description": "Run the test suite (python -m unittest) and return its output.", "parameters": {"type": "object", "properties": {}}}},
]
AGENT_SYSTEM = ("You are an autonomous coding agent working inside a small Python repository. Use the tools to inspect files, "
                "edit code and run the tests. Make correct, minimal changes in the source files; never edit test files. "
                "Run the tests to verify before you finish. When everything passes, reply with a short summary and do not call any tool.")

REPOS = []
REPOS.append(dict(id="ag_bugfix", task="The tests are failing. Fix the library so all tests pass.", files={
"textstats/__init__.py": "",
"textstats/stats.py": '''def words(text):
    return text.split(" ")


def word_count(text):
    return len(words(text))


def avg_word_length(text):
    w = words(text)
    return sum(len(x) for x in w) / len(text)
''',
"tests/__init__.py": "",
"tests/test_stats.py": '''import unittest
from textstats.stats import word_count, avg_word_length


class T(unittest.TestCase):
    def test_count(self):
        self.assertEqual(word_count("hello  world\\nfoo"), 3)
        self.assertEqual(word_count(""), 0)
        self.assertEqual(word_count("   "), 0)

    def test_avg(self):
        self.assertEqual(avg_word_length("ab cd"), 2.0)
        self.assertEqual(avg_word_length("a bcd"), 2.0)
        self.assertEqual(avg_word_length(""), 0.0)
        self.assertEqual(avg_word_length("  x  "), 1.0)
'''}))

REPOS.append(dict(id="ag_feature", task=("Feature request for todo.py: items get an optional due date (datetime.date) and a priority 1-3 (1 = most urgent, default 2). "
 "add(title, due=None, priority=2) must reject other priorities with ValueError. pending() returns titles sorted by priority, then due date (no due date last), "
 "then insertion order. Add overdue(today) returning pending titles whose due date is before today, in the same order. Tests in test_todo.py describe the behaviour."), files={
"todo.py": '''class TodoList:
    def __init__(self):
        self._items = []
        self._next = 1

    def add(self, title):
        item = {"id": self._next, "title": title, "done": False}
        self._items.append(item)
        self._next += 1
        return item["id"]

    def complete(self, item_id):
        for it in self._items:
            if it["id"] == item_id:
                it["done"] = True
                return
        raise KeyError(item_id)

    def pending(self):
        return [it["title"] for it in self._items if not it["done"]]
''',
"test_todo.py": '''import unittest
from datetime import date
from todo import TodoList


class T(unittest.TestCase):
    def test_backwards_compatible(self):
        t = TodoList(); a = t.add("a"); t.add("b"); t.complete(a)
        self.assertEqual(t.pending(), ["b"])
        with self.assertRaises(KeyError):
            t.complete(99)

    def test_ordering(self):
        t = TodoList()
        t.add("no-due-p2")
        t.add("late-p2", due=date(2026, 5, 1))
        t.add("early-p2", due=date(2026, 1, 1))
        t.add("p1", priority=1)
        t.add("p3", due=date(2020, 1, 1), priority=3)
        t.add("early-p2-b", due=date(2026, 1, 1))
        self.assertEqual(t.pending(), ["p1", "early-p2", "early-p2-b", "late-p2", "no-due-p2", "p3"])

    def test_overdue(self):
        t = TodoList()
        x = t.add("x", due=date(2026, 1, 1)); t.add("y", due=date(2026, 3, 1), priority=1); t.add("z")
        t.add("today", due=date(2026, 3, 10))
        self.assertEqual(t.overdue(date(2026, 3, 10)), ["y", "x"])
        t.complete(x)
        self.assertEqual(t.overdue(date(2026, 3, 10)), ["y"])

    def test_bad_priority(self):
        t = TodoList()
        for p in (0, 4, "1"):
            with self.assertRaises(ValueError):
                t.add("bad", priority=p)
'''}))

REPOS.append(dict(id="ag_crossfile", task="test_app.py fails. Fix the code. Note that values coming from the environment are strings.", files={
"config.py": '''def load_config(env):
    return {
        "host": env.get("APP_HOST", "127.0.0.1"),
        "port": env.get("APP_PORT", 8080),
    }
''',
"app.py": '''from config import load_config


def server_address(env):
    cfg = load_config(env)
    return f"http://{cfg.host}:{cfg.port}"


def is_privileged(env):
    return load_config(env)["port"] < 1024
''',
"test_app.py": '''import unittest
from app import server_address, is_privileged
from config import load_config


class T(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(server_address({}), "http://127.0.0.1:8080")
        self.assertEqual(load_config({})["port"], 8080)

    def test_env(self):
        env = {"APP_HOST": "0.0.0.0", "APP_PORT": "80"}
        self.assertEqual(server_address(env), "http://0.0.0.0:80")
        self.assertTrue(is_privileged(env))
        self.assertFalse(is_privileged({"APP_PORT": "8443"}))
        self.assertEqual(load_config(env)["port"], 80)

    def test_invalid_port(self):
        for bad in ("abc", "0", "70000", "-1", ""):
            with self.assertRaises(ValueError):
                load_config({"APP_PORT": bad})
'''}))

REPOS.append(dict(id="ag_perf", task="test_dedupe.py fails on the large input because find_duplicates is far too slow. Make it fast without changing its results.", files={
"dedupe.py": '''def find_duplicates(items):
    """Return a sorted list of the distinct items that appear more than once."""
    dups = []
    for i, x in enumerate(items):
        if x in items[i + 1:] and x not in dups:
            dups.append(x)
    return sorted(dups)
''',
"test_dedupe.py": '''import random
import time
import unittest
from dedupe import find_duplicates


class T(unittest.TestCase):
    def test_small(self):
        self.assertEqual(find_duplicates([3, 1, 3, 2, 1, 3]), [1, 3])
        self.assertEqual(find_duplicates([]), [])
        self.assertEqual(find_duplicates(["b", "a", "b"]), ["b"])
        self.assertEqual(find_duplicates([1, 2, 3]), [])

    def test_large(self):
        r = random.Random(1)
        items = [r.randint(0, 40000) for _ in range(60000)]
        t = time.time()
        got = find_duplicates(items)
        self.assertLess(time.time() - t, 1.0)
        from collections import Counter
        self.assertEqual(got, sorted(k for k, v in Counter(items).items() if v > 1))
'''}))

REPOS.append(dict(id="ag_vague", task=("Slugs on our blog look broken for titles like 'Crème Brûlée: A Guide!' or '  Hello -- World  '. "
 "Please make slugify produce clean URL slugs. There are tests in test_slug.py."), files={
"slug.py": '''def slugify(s):
    return s.lower().replace(" ", "-")
''',
"test_slug.py": '''import unittest
from slug import slugify


class T(unittest.TestCase):
    def test_cases(self):
        cases = {
            "Crème Brûlée: A Guide!": "creme-brulee-a-guide",
            "  Hello -- World  ": "hello-world",
            "Ünïcödé": "unicode",
            "100% Pure_Data": "100-pure-data",
            "already-clean": "already-clean",
            "": "",
            "!!!": "",
            "Ångström Ærø": "angstrom-r",
        }
        for src, want in cases.items():
            self.assertEqual(slugify(src), want, src)
'''}))
