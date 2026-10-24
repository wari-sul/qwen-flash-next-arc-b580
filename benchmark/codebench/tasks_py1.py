# Coding benchmark tasks, part 1: implement-from-spec + efficiency (Python).
# Each task: id, cat, lang, spec (structured prompt body), casual (same information, casual one-paragraph phrasing),
# tests (python test file importing from `solution`), timeout (s), forbid (substrings that fail the task), ref (reference solution).
T = []

T.append(dict(id="impl_merge_intervals", cat="implement", lang="python", hard=False, timeout=20,
spec="""## Task
Implement `merge_intervals(intervals: list[list[int]]) -> list[list[int]]`.

## Requirements
- Merge intervals that overlap OR touch: `[1,3]` and `[3,5]` become `[1,5]`.
- Input may be unsorted and may be empty.
- Return a new list sorted by start; do NOT mutate the input list or its inner lists.

## Constraints
- Up to 200,000 intervals; must run well under 2 seconds.""",
casual="hey can you write me a python function merge_intervals(intervals) that merges overlapping intervals? intervals that just touch like [1,3] and [3,5] should merge too. the input can be unsorted or empty, return them sorted by start, and please don't modify the list i pass in. it gets called with up to 200k intervals so it needs to be fast.",
tests=r'''
import random, time, bisect, copy
from solution import merge_intervals as f
assert f([]) == []
assert f([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]
assert f([[1,4],[4,5]]) == [[1,5]]
assert f([[5,6],[1,2]]) == [[1,2],[5,6]]
assert f([[1,10],[2,3],[4,5]]) == [[1,10]]
assert f([[1,1]]) == [[1,1]]
x = [[3,4],[1,2],[2,3]]; y = copy.deepcopy(x); f(x); assert x == y, "input mutated"
r = random.Random(7)
big = []
for _ in range(200000):
    a = r.randint(0, 10**9); big.append([a, a + r.randint(0, 3000)])
t = time.time(); out = f(big); el = time.time() - t
assert el < 2.0, f"too slow {el:.2f}s"
for i in range(len(out) - 1):
    assert out[i][0] <= out[i][1] and out[i][1] < out[i+1][0]
starts = [o[0] for o in out]
for a, b in big[:20000]:
    i = bisect.bisect_right(starts, a) - 1
    assert i >= 0 and out[i][0] <= a and b <= out[i][1]
print("PASS")
''',
ref='''
def merge_intervals(intervals):
    out = []
    for a, b in sorted(intervals):
        if out and a <= out[-1][1]:
            if b > out[-1][1]: out[-1][1] = b
        else:
            out.append([a, b])
    return out
'''))

T.append(dict(id="impl_top_k_words", cat="implement", lang="python", hard=False, timeout=30,
spec="""## Task
Implement `top_k_words(text: str, k: int) -> list[tuple[str, int]]`.

## Requirements
- A word is a maximal run of ASCII letters `a-z` / `A-Z`; everything else separates words.
- Counting is case-insensitive; report words in lowercase.
- Return `(word, count)` pairs sorted by count descending, ties broken alphabetically ascending.
- Return at most `k` pairs (fewer if there are fewer distinct words). `k` may be 0.

## Constraints
- `text` can be 5 MB; must run well under 2 seconds.""",
casual="need a python function top_k_words(text, k) that returns the k most common words as (word, count) tuples. words are just runs of ascii letters, anything else splits them, case insensitive and return them lowercase. sort by count high to low and alphabetically when counts tie. if there are fewer than k distinct words just return what there is, and k can be 0. text can be like 5MB so keep it quick.",
tests=r'''
import random, time
from solution import top_k_words as f
assert f("", 3) == []
assert f("a b a", 0) == []
assert f("The the THE cat. Cat! dog", 2) == [("the", 3), ("cat", 2)]
assert f("b a c b a", 5) == [("a", 2), ("b", 2), ("c", 1)]
assert f("don't stop-me now2day", 10) == [("day",1),("don",1),("me",1),("now",1),("stop",1),("t",1)]
r = random.Random(3)
words = ["".join(r.choice("abcdefghij") for _ in range(r.randint(1,6))) for _ in range(3000)]
text = " ".join(r.choice(words).upper() if r.random()<0.3 else r.choice(words) for _ in range(900000))
t = time.time(); out = f(text, 50); el = time.time() - t
assert el < 2.0, f"too slow {el:.2f}s"
from collections import Counter
import re
c = Counter(re.findall("[a-z]+", text.lower()))
exp = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:50]
assert out == exp
print("PASS")
''',
ref='''
import re
from collections import Counter
def top_k_words(text, k):
    c = Counter(re.findall(r"[a-z]+", text.lower()))
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
'''))

T.append(dict(id="impl_ttl_lru", cat="implement", lang="python", hard=True, timeout=30,
spec="""## Task
Implement class `TTLCache(capacity: int, ttl: float, clock=time.monotonic)`.

## Interface
- `get(key)` -> the value, or `None` if the key is missing or expired. A successful `get` makes the key most-recently-used but does NOT extend its expiry.
- `put(key, value)` -> stores/overwrites; sets the key's expiry to `clock() + ttl` and makes it most-recently-used.
- `len(cache)` -> number of non-expired entries.

## Requirements
- An entry is expired when `clock() >= its expiry`.
- When `put` adds a NEW key and the cache would exceed `capacity`: first drop all expired entries; if still over capacity, evict the least-recently-used entry.
- `clock` is injectable (tests pass a fake clock).

## Constraints
- `get`/`put` must be O(1) amortized; up to 1,000,000 operations.""",
casual="can you write a python class TTLCache(capacity, ttl, clock=time.monotonic) — an LRU cache where entries also expire. get(key) returns the value or None if missing/expired, and a hit makes it most recently used but doesn't extend the expiry. put(key, value) stores or overwrites, sets expiry to clock()+ttl and makes it most recently used. len(cache) should count only non-expired entries. an entry is expired once clock() >= its expiry. when put adds a new key and we'd go over capacity, first throw away expired entries and if still too many evict the least recently used one. the clock is injectable because our tests use a fake clock. get/put need to be O(1) amortized, we do about a million ops.",
tests=r'''
import time
from solution import TTLCache
class Clock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t
c = Clock(); x = TTLCache(2, 10, clock=c)
x.put("a", 1); x.put("b", 2)
assert x.get("a") == 1
x.put("c", 3)                      # evicts LRU = b
assert x.get("b") is None and x.get("a") == 1 and x.get("c") == 3
c.t = 5; x.put("a", 11)            # refresh a expiry -> 15
c.t = 10                           # c expired (put at 0)
assert x.get("c") is None
assert len(x) == 1
x.put("d", 4); x.put("e", 5)       # over capacity: expired already gone; evict LRU among a,d -> a
assert x.get("a") is None and x.get("d") == 4 and x.get("e") == 5
c.t = 19.999; assert x.get("d") == 4
c.t = 20.0; assert x.get("d") is None    # expiry boundary: expired when clock >= expiry
# get must not extend expiry
c2 = Clock(); y = TTLCache(5, 10, clock=c2); y.put("k", 1); c2.t = 9; assert y.get("k") == 1; c2.t = 10; assert y.get("k") is None
# expired entries purged before LRU eviction
c3 = Clock(); z = TTLCache(2, 10, clock=c3); z.put("old", 1); c3.t = 5; z.put("new", 2); c3.t = 11
z.put("x", 3)
assert z.get("new") == 2 and z.get("x") == 3 and len(z) == 2
# overwrite does not grow
w = TTLCache(1, 100, clock=Clock()); w.put("k", 1); w.put("k", 2); assert w.get("k") == 2 and len(w) == 1
# performance
c4 = Clock(); p = TTLCache(50000, 1000.0, clock=c4)
t = time.time()
for i in range(500000):
    c4.t += 0.001; p.put(i, i); p.get(i // 2)
el = time.time() - t
assert el < 6.0, f"too slow {el:.2f}s"
print("PASS")
''',
ref='''
import time
from collections import OrderedDict, deque
class TTLCache:
    def __init__(self, capacity, ttl, clock=time.monotonic):
        self.cap, self.ttl, self.clock = capacity, ttl, clock
        self.d = OrderedDict()      # key -> (value, expiry), in recency order
        self.q = deque()            # (expiry, key) in expiry order (ttl is constant, clock non-decreasing)
    def _purge(self):
        now = self.clock()
        while self.q and self.q[0][0] <= now:
            exp, k = self.q.popleft()
            it = self.d.get(k)
            if it is not None and it[1] == exp: del self.d[k]
    def get(self, key):
        it = self.d.get(key)
        if it is None: return None
        if self.clock() >= it[1]:
            del self.d[key]; return None
        self.d.move_to_end(key); return it[0]
    def put(self, key, value):
        new = key not in self.d
        exp = self.clock() + self.ttl
        self.d[key] = (value, exp); self.d.move_to_end(key); self.q.append((exp, key))
        if new and len(self.d) > self.cap:
            self._purge()
            while len(self.d) > self.cap: self.d.popitem(last=False)
        if len(self.q) > 4 * max(self.cap, 1) + 16:
            self.q = deque((e, k) for e, k in self.q if k in self.d and self.d[k][1] == e)
    def __len__(self):
        self._purge(); return len(self.d)
'''))

T.append(dict(id="impl_parse_duration", cat="implement", lang="python", hard=False, timeout=20,
spec="""## Task
Implement `parse_duration(s: str) -> int` returning total seconds.

## Format
- One or more `<integer><unit>` parts, units `d` (86400 s), `h`, `m`, `s`.
- Units must appear in that order (d, h, m, s), each at most once. Integers are non-negative decimal digits (leading zeros allowed). No spaces, no signs, lowercase only.
- Examples: `"1h30m"` -> 5400, `"45s"` -> 45, `"2d4s"` -> 172804, `"0s"` -> 0.

## Errors
- Anything else raises `ValueError` (e.g. `""`, `"1h1h"`, `"30m1h"`, `"1.5h"`, `"h"`, `"-1s"`, `"1H"`, `"10"`, `" 1h"`).""",
casual="write parse_duration(s) in python, it turns strings like \"1h30m\" into seconds (5400). parts are a number followed by d, h, m or s (d is a day). units must come in the order d h m s and each at most once, numbers are plain digits (leading zeros are ok), no spaces, no signs, lowercase only. \"45s\" is 45, \"2d4s\" is 172804, \"0s\" is 0. anything else should raise ValueError, e.g. empty string, \"1h1h\", \"30m1h\", \"1.5h\", \"h\", \"-1s\", \"1H\", \"10\", \" 1h\".",
tests=r'''
from solution import parse_duration as f
ok = {"1h30m":5400,"45s":45,"2d4s":172804,"0s":0,"01m":60,"1d2h3m4s":93784,"100h":360000,"0d0h0m0s":0}
for s, v in ok.items(): assert f(s) == v, (s, f(s))
for s in ["", "1h1h", "30m1h", "1.5h", "h", "-1s", "1H", "10", " 1h", "1h ", "1hm", "1s1d", "1x", "+1s", "1h\n", "1 h", "dhms"]:
    try:
        f(s)
    except ValueError:
        continue
    raise AssertionError(f"no ValueError for {s!r}")
print("PASS")
''',
ref='''
import re
_R = re.compile(r"(?:(\\d+)d)?(?:(\\d+)h)?(?:(\\d+)m)?(?:(\\d+)s)?")
def parse_duration(s):
    m = _R.fullmatch(s)
    if not s or not m or not any(m.groups()): raise ValueError(s)
    d, h, mi, se = (int(g) if g else 0 for g in m.groups())
    return d*86400 + h*3600 + mi*60 + se
'''))

T.append(dict(id="impl_dijkstra_path", cat="implement", lang="python", hard=True, timeout=40,
spec="""## Task
Implement `shortest_path(n: int, edges: list[tuple[int, int, int]], src: int, dst: int) -> tuple[int | None, list[int]]`.

## Requirements
- Directed graph with nodes `0..n-1`; each edge `(u, v, w)` has non-negative integer weight `w`. Parallel edges and self-loops may exist.
- Return `(distance, path)` where `path` is the list of nodes from `src` to `dst` inclusive along one shortest route.
- If `dst` is unreachable return `(None, [])`. If `src == dst` return `(0, [src])`.

## Constraints
- n up to 100,000, up to 300,000 edges; must run well under 3 seconds.""",
casual="i need shortest_path(n, edges, src, dst) in python. directed graph, nodes 0..n-1, edges are (u, v, w) tuples with non-negative int weights, there can be parallel edges and self loops. return (distance, path) where path is the list of nodes from src to dst inclusive on a shortest route. if dst can't be reached return (None, []), and if src == dst return (0, [src]). graphs have up to 100k nodes and 300k edges so it has to be quick (under 3 sec easily).",
tests=r'''
import random, time, heapq
from solution import shortest_path as f
def ref(n, edges, s):
    g = [[] for _ in range(n)]
    for u, v, w in edges: g[u].append((v, w))
    d = [None]*n; d[s] = 0; pq = [(0, s)]
    while pq:
        du, u = heapq.heappop(pq)
        if du > d[u]: continue
        for v, w in g[u]:
            nd = du + w
            if d[v] is None or nd < d[v]: d[v] = nd; heapq.heappush(pq, (nd, v))
    return d
def check(n, edges, s, t, res):
    d = ref(n, edges, s)[t]
    dist, path = res
    if d is None: assert res == (None, []), res; return
    assert dist == d, (dist, d)
    assert path[0] == s and path[-1] == t
    best = {}
    for u, v, w in edges:
        if (u, v) not in best or w < best[(u, v)]: best[(u, v)] = w
    tot = 0
    for a, b in zip(path, path[1:]):
        assert (a, b) in best, ("not an edge", a, b); tot += best[(a, b)]
    assert tot == d
assert f(3, [], 1, 1) == (0, [1])
assert f(3, [(0,1,5)], 1, 0) == (None, [])
assert f(4, [(0,1,1),(1,2,1),(0,2,5),(2,3,1),(0,3,10)], 0, 3) == (3, [0,1,2,3])
check(3, [(0,0,0),(0,1,2),(0,1,1),(1,2,0)], 0, 2, f(3, [(0,0,0),(0,1,2),(0,1,1),(1,2,0)], 0, 2))
r = random.Random(11)
for _ in range(40):
    n = r.randint(1, 30); e = [(r.randrange(n), r.randrange(n), r.randint(0, 9)) for _ in range(r.randint(0, 80))]
    s, t = r.randrange(n), r.randrange(n); check(n, e, s, t, f(n, e, s, t))
n = 100000; e = [(r.randrange(n), r.randrange(n), r.randint(0, 1000)) for _ in range(300000)]
t0 = time.time(); res = f(n, e, 0, n - 1); el = time.time() - t0
assert el < 3.0, f"too slow {el:.2f}s"
check(n, e, 0, n - 1, res)
print("PASS")
''',
ref='''
import heapq
def shortest_path(n, edges, src, dst):
    g = [[] for _ in range(n)]
    for u, v, w in edges: g[u].append((v, w))
    dist = [None]*n; prev = [-1]*n; dist[src] = 0; pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]: continue
        if u == dst: break
        for v, w in g[u]:
            nd = d + w
            if dist[v] is None or nd < dist[v]:
                dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
    if dist[dst] is None: return (None, [])
    p = [dst]
    while p[-1] != src: p.append(prev[p[-1]])
    return (dist[dst], p[::-1])
'''))

T.append(dict(id="impl_expr_eval", cat="implement", lang="python", hard=True, timeout=30, forbid=["eval(", "exec(", "compile(", "import ast", "from ast"],
spec="""## Task
Implement `eval_expr(s: str) -> float` — a calculator for arithmetic expressions.

## Requirements
- Supports `+ - * /`, parentheses, unary `+`/`-` (also stacked, e.g. `--2`, `2*-3`), integer and decimal literals (`3`, `3.5`, `.5`), arbitrary whitespace.
- Usual precedence (`* /` above `+ -`), left associative (`8/4/2` = 1, `1-2-3` = -4). Result is a float.
- Division by zero raises `ZeroDivisionError`. Any malformed input raises `ValueError`.
- Do NOT use `eval`, `exec`, `compile` or the `ast` module.

## Constraints
- Expressions up to 200,000 characters (flat) and nesting depth up to 200; must finish in under 2 seconds.""",
casual="write me a python calculator function eval_expr(s) that returns a float. it needs + - * / with normal precedence and left associativity (8/4/2 is 1, 1-2-3 is -4), parentheses, unary plus/minus which can stack like --2 or 2*-3, numbers like 3, 3.5 or .5, and any whitespace. divide by zero should raise ZeroDivisionError and garbage input should raise ValueError. don't use eval, exec, compile or the ast module. expressions can be 200k characters long and nested about 200 deep, should take under 2 seconds.",
tests=r'''
import time
from solution import eval_expr as f
cases = {"2+3*4":14, "(2+3)*4":20, "2*-3":-6, "--2":2, "-(2+3)":-5, "8/4/2":1, "1 - 2 - 3":-4, "3.5*2":7, ".5+.5":1,
         " 7 ":7, "+3":3, "2*(3+(4-1))*2":24, "10/4":2.5, "-2*-2":4, "1+2*3-4/2":5, "((((1))))":1}
for s, v in cases.items():
    got = f(s); assert isinstance(got, float), (s, type(got)); assert abs(got - v) < 1e-9, (s, got)
for s in ["2+", "(1", "1)", "abc", "", "1 2", "*3", "2**3", "()", "1..2", "3+(4*)", "1/(2-"]:
    try: f(s)
    except ValueError: continue
    except Exception as e: raise AssertionError(f"{s!r} raised {type(e).__name__}, want ValueError")
    raise AssertionError(f"no ValueError for {s!r}")
for s in ["1/0", "5/(2-2)"]:
    try: f(s)
    except ZeroDivisionError: continue
    raise AssertionError(f"no ZeroDivisionError for {s!r}")
big = "+".join(["1"]*100000)
t = time.time(); assert abs(f(big) - 100000) < 1e-6; deep = "(" * 200 + "2" + ")" * 200; assert f(deep) == 2
assert abs(f("-".join(["1"]*50001)) - (1 - 50000)) < 1e-6
assert time.time() - t < 2.0, "too slow"
print("PASS")
''',
ref='''
import re
_TOK = re.compile(r"\\s*(?:(\\d+\\.\\d*|\\.\\d+|\\d+)|(.))")
def eval_expr(s):
    toks = []
    for num, op in _TOK.findall(s):
        if num: toks.append(("n", float(num)))
        elif op.strip():
            if op not in "+-*/()": raise ValueError(op)
            toks.append(("o", op))
    if re.search(r"\\d\\.\\d*\\.", s) or re.search(r"\\.\\.", s): raise ValueError(s)
    pos = 0
    def peek():
        return toks[pos] if pos < len(toks) else (None, None)
    def expr():
        nonlocal pos
        v = term()
        while peek()[1] in ("+", "-") and peek()[0] == "o":
            op = toks[pos][1]; pos += 1; r = term(); v = v + r if op == "+" else v - r
        return v
    def term():
        nonlocal pos
        v = unary()
        while peek()[0] == "o" and peek()[1] in ("*", "/"):
            op = toks[pos][1]; pos += 1; r = unary()
            if op == "*": v *= r
            else:
                if r == 0: raise ZeroDivisionError("division by zero")
                v /= r
        return v
    def unary():
        nonlocal pos
        sign = 1
        while peek()[0] == "o" and peek()[1] in ("+", "-"):
            if toks[pos][1] == "-": sign = -sign
            pos += 1
        return sign * atom()
    def atom():
        nonlocal pos
        k, v = peek()
        if k == "n": pos += 1; return v
        if k == "o" and v == "(":
            pos += 1; r = expr()
            if peek() != ("o", ")"): raise ValueError("missing )")
            pos += 1; return r
        raise ValueError("unexpected token")
    if not toks: raise ValueError("empty")
    r = expr()
    if pos != len(toks): raise ValueError("trailing")
    return float(r)
'''))

T.append(dict(id="eff_count_pairs", cat="efficiency", lang="python", hard=False, timeout=20,
spec="""## Task
Implement `count_pairs(nums: list[int], target: int) -> int`: the number of index pairs `i < j` with `nums[i] + nums[j] == target`.

## Requirements
- Values may repeat and may be negative.

## Constraints
- `len(nums)` up to 200,000; must run well under 1 second.""",
casual="python function count_pairs(nums, target): how many index pairs i<j have nums[i]+nums[j]==target. numbers can repeat and be negative. list can have 200k numbers, needs to be fast (well under a second).",
tests=r'''
import random, time
from solution import count_pairs as f
def brute(a, t): return sum(1 for i in range(len(a)) for j in range(i+1, len(a)) if a[i]+a[j]==t)
assert f([], 5) == 0 and f([5], 10) == 0
assert f([1,1,1,1], 2) == 6
assert f([3,3,3], 6) == 3
assert f([-1, 1, 0, 2, -2], 0) == 2
r = random.Random(5)
for _ in range(200):
    a = [r.randint(-6, 6) for _ in range(r.randint(0, 40))]; t = r.randint(-8, 8)
    assert f(a, t) == brute(a, t)
big = [r.randint(-1000, 1000) for _ in range(200000)]
t0 = time.time(); got = f(big, 17); el = time.time() - t0
from collections import Counter
c = Counter(big); exp = sum(c[x]*c[17-x] for x in c if x < 17-x) + (c[17/2]*(c[17/2]-1)//2 if 17 % 2 == 0 else 0)
assert got == exp and el < 1.0, (got, exp, el)
print("PASS")
''',
ref='''
from collections import defaultdict
def count_pairs(nums, target):
    seen = defaultdict(int); n = 0
    for x in nums:
        n += seen[target - x]; seen[x] += 1
    return n
'''))

T.append(dict(id="eff_running_median", cat="efficiency", lang="python", hard=True, timeout=30,
spec="""## Task
Implement `running_median(nums: list[int]) -> list[float]`: element `i` of the result is the median of `nums[0..i]`.

## Requirements
- Odd count: the middle value; even count: the mean of the two middle values. Always return floats.
- Empty input returns `[]`.

## Constraints
- Up to 200,000 numbers; must run in under 2 seconds (an O(n log n) approach is expected).""",
casual="write running_median(nums) in python, returns a list where item i is the median of nums[0..i] as a float (average of the two middle ones when the count is even). empty input gives []. it needs to handle 200k numbers in under 2 seconds.",
tests=r'''
import random, time, heapq, statistics
from solution import running_median as f
assert f([]) == []
assert f([5]) == [5.0]
assert f([1, 3]) == [1.0, 2.0]
assert f([5, 15, 1, 3]) == [5.0, 10.0, 5.0, 4.0]
r = random.Random(9)
for _ in range(50):
    a = [r.randint(-50, 50) for _ in range(r.randint(1, 60))]
    got = f(a); assert len(got) == len(a)
    for i in range(len(a)): assert abs(got[i] - statistics.median(a[:i+1])) < 1e-9
    assert all(isinstance(x, float) for x in got)
big = [r.randint(-10**6, 10**6) for _ in range(200000)]
t0 = time.time(); got = f(big); el = time.time() - t0
assert el < 2.0, f"too slow {el:.2f}s"
lo, hi = [], []; exp = []
for x in big:
    if lo and x > -lo[0]: heapq.heappush(hi, x)
    else: heapq.heappush(lo, -x)
    if len(lo) > len(hi) + 1: heapq.heappush(hi, -heapq.heappop(lo))
    elif len(hi) > len(lo): heapq.heappush(lo, -heapq.heappop(hi))
    exp.append(float(-lo[0]) if len(lo) > len(hi) else (-lo[0] + hi[0]) / 2.0)
assert got == exp
print("PASS")
''',
ref='''
import heapq
def running_median(nums):
    lo, hi, out = [], [], []
    for x in nums:
        if lo and x > -lo[0]: heapq.heappush(hi, x)
        else: heapq.heappush(lo, -x)
        if len(lo) > len(hi) + 1: heapq.heappush(hi, -heapq.heappop(lo))
        elif len(hi) > len(lo): heapq.heappush(lo, -heapq.heappop(hi))
        out.append(float(-lo[0]) if len(lo) > len(hi) else (-lo[0] + hi[0]) / 2.0)
    return out
'''))

T.append(dict(id="eff_log_stats", cat="efficiency", lang="python", hard=True, timeout=40,
spec="""## Task
Implement `top_ips(lines: list[str]) -> list[tuple[str, int, int]]`.

## Input
Each line looks like `2026-10-23T12:00:01Z 203.0.113.7 GET /api/items 200 37ms`
(timestamp, client IP, method, path, status, latency in integer milliseconds followed by `ms`). Fields are separated by single spaces. Lines that do not match this shape (wrong field count, latency not `<digits>ms`, status not 3 digits) must be skipped.

## Output
- For the 10 IPs with the most valid requests: `(ip, request_count, p95_latency_ms)`.
- p95 uses the nearest-rank method: sort that IP's latencies ascending and take the value at 1-based rank `ceil(0.95 * count)`.
- Sort by count descending, then IP string ascending. Fewer than 10 IPs -> return all.

## Constraints
- Up to 1,000,000 lines; must run in under 3 seconds.""",
casual="i have access log lines like '2026-10-23T12:00:01Z 203.0.113.7 GET /api/items 200 37ms' (timestamp, ip, method, path, status, latency in ms with an ms suffix, single spaces). write top_ips(lines) that returns the top 10 ips by number of valid requests as (ip, count, p95_latency) tuples. skip lines that don't fit that shape (wrong number of fields, latency not digits+ms, status not 3 digits). p95 is nearest-rank: sort the ip's latencies and take the one at 1-based rank ceil(0.95*count). sort by count descending then ip ascending, and if there are fewer than 10 ips return them all. could be a million lines, should take under 3 seconds.",
tests=r'''
import random, time, math
from solution import top_ips as f
L = ["2026-10-23T12:00:01Z 10.0.0.1 GET /a 200 10ms",
     "2026-10-23T12:00:02Z 10.0.0.1 GET /a 500 30ms",
     "2026-10-23T12:00:03Z 10.0.0.2 POST /b 201 5ms",
     "garbage line",
     "2026-10-23T12:00:04Z 10.0.0.2 GET /c 200 fastms",
     "2026-10-23T12:00:05Z 10.0.0.3 GET /c 20 7ms",
     "2026-10-23T12:00:06Z 10.0.0.3 GET /c 200 7",
     "2026-10-23T12:00:07Z 10.0.0.1 GET /a 200 20ms extra"]
assert f(L) == [("10.0.0.1", 2, 30), ("10.0.0.2", 1, 5)], f(L)
assert f([]) == []
r = random.Random(4)
ips = [f"192.168.{r.randint(0,3)}.{r.randint(0,40)}" for _ in range(60)]
lines = []
for i in range(1000000):
    if i % 997 == 0: lines.append("broken"); continue
    lines.append(f"2026-10-23T12:00:00Z {r.choice(ips)} GET /x {r.choice((200,404,500))} {r.randint(1,2000)}ms")
t0 = time.time(); got = f(lines); el = time.time() - t0
assert el < 3.0, f"too slow {el:.2f}s"
d = {}
for ln in lines:
    p = ln.split(" ")
    if len(p) == 6 and p[5].endswith("ms") and p[5][:-2].isdigit() and len(p[4]) == 3 and p[4].isdigit():
        d.setdefault(p[1], []).append(int(p[5][:-2]))
exp = []
for ip, v in d.items():
    v.sort(); exp.append((ip, len(v), v[math.ceil(0.95*len(v))-1]))
exp.sort(key=lambda x: (-x[1], x[0]))
assert got == exp[:10], (got[:3], exp[:3])
print("PASS")
''',
ref='''
import math
def top_ips(lines):
    d = {}
    for ln in lines:
        p = ln.split(" ")
        if len(p) != 6: continue
        lat, st = p[5], p[4]
        if not (lat.endswith("ms") and lat[:-2].isdigit() and len(st) == 3 and st.isdigit()): continue
        d.setdefault(p[1], []).append(int(lat[:-2]))
    out = []
    for ip, v in d.items():
        v.sort(); out.append((ip, len(v), v[math.ceil(0.95*len(v)) - 1]))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out[:10]
'''))
