# Part 2: debugging, refactoring, implementation decisions from user requests, concurrency.
T = []

T.append(dict(id="debug_find_first", cat="debug", lang="python", hard=False, timeout=30, forbid=[".index("],
given='''def find_first(arr, x):
    """Return the index of the FIRST occurrence of x in the sorted list arr, or -1."""
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] < x:
            lo = mid
        else:
            hi = mid - 1
    return lo if arr[lo] == x else -1
''',
spec="""## Bug report
Users report three problems with `find_first` (code below): some calls never return, some return the wrong index for lists with duplicates, and `find_first([], 3)` raises `IndexError`.

## Task
Fix `find_first` so it returns the index of the first occurrence of `x` in the ascending-sorted list `arr`, or `-1` if absent.
Keep the same signature and keep it O(log n) (it is called 200,000 times on a 1,000,000-element list). Do not use `list.index`.""",
casual="this find_first function is broken, sometimes it hangs, sometimes it gives the wrong index when there are duplicates, and find_first([], 3) throws IndexError. it should return the index of the first occurrence of x in the sorted list or -1. keep the same signature, keep it O(log n) since we call it 200k times on a list of a million items, and don't use list.index. can you fix it?",
tests=r'''
import random, time, bisect
from solution import find_first as f
assert f([], 3) == -1
assert f([3], 3) == 0 and f([3], 4) == -1 and f([3], 2) == -1
assert f([1,2,2,2,3], 2) == 1
assert f([2,2,2], 2) == 0
assert f([1,1,2], 3) == -1 and f([1,1,2], 0) == -1
r = random.Random(2)
for _ in range(300):
    a = sorted(r.randint(0, 9) for _ in range(r.randint(0, 25))); x = r.randint(-1, 10)
    i = bisect.bisect_left(a, x); exp = i if i < len(a) and a[i] == x else -1
    assert f(a, x) == exp, (a, x)
big = sorted(r.randint(0, 500000) for _ in range(1000000))
qs = [r.randint(0, 500000) for _ in range(200000)]
t0 = time.time(); res = [f(big, q) for q in qs]; el = time.time() - t0
assert el < 3.0, f"too slow {el:.2f}s"
for q, g in list(zip(qs, res))[:2000]:
    i = bisect.bisect_left(big, q); assert g == (i if i < len(big) and big[i] == q else -1)
print("PASS")
''',
ref='''
def find_first(arr, x):
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] < x: lo = mid + 1
        else: hi = mid
    return lo if lo < len(arr) and arr[lo] == x else -1
'''))

T.append(dict(id="debug_shared_state", cat="debug", lang="python", hard=False, timeout=20,
given='''class Article:
    def __init__(self, title, tags=[]):
        self.title = title
        self.tags = tags

    def add_tag(self, tag):
        if tag not in self.tags:
            self.tags.append(tag)


def clone(article):
    """Return an independent copy of the article."""
    return Article(article.title, article.tags)
''',
spec="""## Bug report
"I tagged one article and suddenly other articles had the same tags. Also editing a cloned article changes the original."

## Task
Fix `Article` and `clone` (code below). An `Article` must own its tags:
- Articles created without tags never share a list.
- Mutating the list that was passed to the constructor afterwards must not change the article.
- `clone(a)` returns an independent copy (same title and tags, separate list).
- `add_tag` keeps its current behaviour (ignore exact duplicates, keep insertion order).""",
casual="weird bug: when i tag one article, other articles get the same tags, and editing a cloned article changes the original too. code is below. an article should own its tags: articles made without tags must not share a list, changing the list i passed into the constructor later shouldn't affect the article, clone(a) should give an independent copy with the same title and tags, and add_tag should keep working like now (skip exact duplicates, keep order). please fix it.",
tests=r'''
from solution import Article, clone
a = Article("a"); b = Article("b"); a.add_tag("x")
assert a.tags == ["x"] and b.tags == []
src = ["p"]; c = Article("c", src); src.append("q"); assert c.tags == ["p"]
c.add_tag("p"); c.add_tag("r"); assert c.tags == ["p", "r"]
d = clone(c); d.add_tag("s"); assert c.tags == ["p", "r"] and d.tags == ["p", "r", "s"] and d.title == "c"
e = Article("e"); e.add_tag("y"); f = Article("f"); assert f.tags == []
print("PASS")
''',
ref='''
class Article:
    def __init__(self, title, tags=None):
        self.title = title
        self.tags = list(tags) if tags is not None else []
    def add_tag(self, tag):
        if tag not in self.tags: self.tags.append(tag)
def clone(article):
    return Article(article.title, article.tags)
'''))

T.append(dict(id="debug_monthly_totals", cat="debug", lang="python", hard=False, timeout=20,
given='''def monthly_totals(records):
    """records: list of {"date": "YYYY-MM-DD", "amount": float}.
    Return {"YYYY-MM": total_amount} ordered by month."""
    totals = {}
    for r in records:
        y, m, d = r["date"].split("-")
        key = f"{y}-{int(m) - 1:02d}"
        totals.setdefault(key, 0)
        totals[key] =+ r["amount"]
    return dict(sorted(totals.items()))
''',
spec="""## Failing test output
```
>>> monthly_totals([{"date": "2026-01-15", "amount": 10.0}, {"date": "2026-01-20", "amount": 5.5}, {"date": "2026-12-01", "amount": 1.0}])
{'2026-00': 5.5, '2026-11': 1.0}
expected: {'2026-01': 15.5, '2026-12': 1.0}
```

## Task
Fix `monthly_totals` (code below) so it groups by the record's real month and sums correctly. Totals are floats; ordering by month ascending must be kept.""",
casual="monthly_totals (below) gives {'2026-00': 5.5, '2026-11': 1.0} for records on 2026-01-15 (10.0), 2026-01-20 (5.5) and 2026-12-01 (1.0), but it should give {'2026-01': 15.5, '2026-12': 1.0}. fix it so it groups by the real month and sums properly, totals as floats, still ordered by month.",
tests=r'''
from solution import monthly_totals as f
got = f([{"date": "2026-01-15", "amount": 10.0}, {"date": "2026-01-20", "amount": 5.5}, {"date": "2026-12-01", "amount": 1.0}])
assert got == {"2026-01": 15.5, "2026-12": 1.0}, got
assert list(got) == ["2026-01", "2026-12"]
g2 = f([{"date": "2025-12-31", "amount": 2.0}, {"date": "2025-02-01", "amount": 1.25}, {"date": "2025-12-01", "amount": 3.0}])
assert list(g2) == ["2025-02", "2025-12"] and g2["2025-12"] == 5.0 and g2["2025-02"] == 1.25
assert f([]) == {}
print("PASS")
''',
ref='''
def monthly_totals(records):
    totals = {}
    for r in records:
        key = r["date"][:7]
        totals[key] = totals.get(key, 0.0) + r["amount"]
    return dict(sorted(totals.items()))
'''))

T.append(dict(id="debug_js_async", cat="debug", lang="js", hard=True, timeout=30,
given='''async function totalStock(ids, fetchStock) {
  let total = 0;
  ids.forEach(async (id) => {
    const n = await fetchStock(id);
    total += n;
  });
  return total;
}
module.exports = { totalStock };
''',
spec="""## Bug report
`totalStock` (Node.js, code below) always resolves to `0`.

## Task
Fix it. Requirements:
- Resolve to the sum of `await fetchStock(id)` for every id (`fetchStock` returns a Promise of a number).
- Start all fetches concurrently (not one after another) — there can be hundreds of ids and each fetch takes ~100 ms.
- If any fetch rejects, the returned promise must reject with that error.
- Empty `ids` resolves to `0`.
- Keep the CommonJS export `module.exports = { totalStock };`.""",
casual="this node function totalStock always returns 0 (code below). it should resolve to the sum of fetchStock(id) for all ids (fetchStock returns a promise of a number). fetch them all at the same time, not one by one, there can be hundreds of ids and each takes ~100ms. if any fetch fails the whole thing should reject with that error, empty ids gives 0, and keep the module.exports = { totalStock } export.",
tests=r'''
const { totalStock } = require('./solution.js');
const assert = require('assert');
(async () => {
  let inflight = 0, maxIn = 0;
  const fetch = (id) => new Promise(res => { inflight++; maxIn = Math.max(maxIn, inflight); setTimeout(() => { inflight--; res(id * 2); }, 100); });
  const ids = Array.from({length: 200}, (_, i) => i + 1);
  const t0 = Date.now(); const s = await totalStock(ids, fetch); const el = Date.now() - t0;
  assert.strictEqual(s, ids.reduce((a, b) => a + b * 2, 0));
  assert.ok(maxIn >= 150, 'not concurrent: max in flight ' + maxIn);
  assert.ok(el < 1000, 'too slow ' + el);
  assert.strictEqual(await totalStock([], fetch), 0);
  const bad = (id) => id === 3 ? Promise.reject(new Error('boom')) : Promise.resolve(1);
  await assert.rejects(totalStock([1, 2, 3, 4], bad), /boom/);
  console.log('PASS');
})().catch(e => { console.error(e); process.exit(1); });
''',
ref='''
async function totalStock(ids, fetchStock) {
  const vals = await Promise.all(ids.map(id => fetchStock(id)));
  return vals.reduce((a, b) => a + b, 0);
}
module.exports = { totalStock };
'''))

T.append(dict(id="refactor_invoice", cat="refactor", lang="python", hard=True, timeout=20,
given='''def invoice_total(items, country):
    total = 0
    for it in items:
        total += it["price"] * it["qty"]
    if country == "DE":
        total = total * 1.19
    elif country == "FR":
        total = total * 1.20
    elif country == "US":
        total = total
    return round(total, 2)
''',
spec="""## Change request
Extend `invoice_total` (code below). New signature: `invoice_total(items, country, code=None) -> float`.

1. Existing behaviour for DE (19% VAT), FR (20%) and US (0%) must stay the same.
2. Add GB with 20% VAT.
3. An unknown country must raise `ValueError` (today it silently applies no tax).
4. Discount codes, applied to the pre-tax subtotal before VAT:
   - `"SAVE10"`: 10% off.
   - `"FLAT5"`: 5.00 off, but the subtotal never goes below 0.
   - Any other non-None code raises `ValueError`.
5. Money must be exact: compute with `decimal.Decimal` from the given numbers (`Decimal(str(x))`) and round the final total to cents with ROUND_HALF_UP; return it as a float.
   Example: one item price 1.005, qty 1, country US -> 1.01 (not 1.0).""",
casual="please extend invoice_total (below) to invoice_total(items, country, code=None). DE 19%, FR 20% and US 0% must keep working the same. add GB at 20%. an unknown country should raise ValueError instead of silently using no tax. discount codes apply to the pre-tax subtotal before VAT: SAVE10 is 10% off, FLAT5 is 5.00 off but never below 0, any other code (that isn't None) raises ValueError. money has to be exact: use Decimal built with Decimal(str(x)) and round the final total to cents half-up, return a float. e.g. price 1.005 qty 1 in the US must give 1.01, not 1.0.",
tests=r'''
from solution import invoice_total as f
items = [{"price": 10.0, "qty": 2}, {"price": 2.5, "qty": 4}]
assert f(items, "DE") == 35.7
assert f(items, "FR") == 36.0
assert f(items, "US") == 30.0
assert f(items, "GB") == 36.0
assert f(items, "DE", "SAVE10") == 32.13
assert f(items, "US", "FLAT5") == 25.0
assert f([{"price": 3.0, "qty": 1}], "FR", "FLAT5") == 0.0
assert f([{"price": 1.005, "qty": 1}], "US") == 1.01
assert f([{"price": 0.1, "qty": 3}], "US") == 0.3
assert f([], "DE") == 0.0
assert isinstance(f(items, "DE"), float)
for bad in [("XX", None), ("de", None), ("DE", "SAVE20")]:
    try: f(items, *bad)
    except ValueError: continue
    raise AssertionError(f"no ValueError for {bad}")
print("PASS")
''',
ref='''
from decimal import Decimal, ROUND_HALF_UP
VAT = {"DE": Decimal("0.19"), "FR": Decimal("0.20"), "US": Decimal("0"), "GB": Decimal("0.20")}
def invoice_total(items, country, code=None):
    if country not in VAT: raise ValueError(country)
    sub = sum((Decimal(str(i["price"])) * Decimal(str(i["qty"])) for i in items), Decimal("0"))
    if code is None: pass
    elif code == "SAVE10": sub *= Decimal("0.9")
    elif code == "FLAT5": sub = max(sub - Decimal("5"), Decimal("0"))
    else: raise ValueError(code)
    return float((sub * (1 + VAT[country])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
'''))

T.append(dict(id="refactor_flatten_iterative", cat="refactor", lang="python", hard=False, timeout=20,
given='''def flatten(x):
    out = []
    for e in x:
        if isinstance(e, list):
            out.extend(flatten(e))
        else:
            out.append(e)
    return out
''',
spec="""## Problem
`flatten` (code below) crashes with `RecursionError` on deeply nested input (we see nesting depth 100,000) and is slow on big inputs because of repeated list copying.

## Task
Rewrite `flatten(x)` so that it:
- produces exactly the same output order as today;
- flattens only `list` instances (tuples, strings, dicts stay as single elements);
- handles any nesting depth;
- runs in O(total number of elements).""",
casual="flatten (below) dies with RecursionError when lists are nested really deep (we've seen 100k levels) and it's slow on big inputs because it keeps copying lists. rewrite it so the output order stays exactly the same, only lists get flattened (tuples, strings, dicts stay as they are), any depth works, and it's linear in the number of elements.",
tests=r'''
import time
from solution import flatten as f
assert f([]) == []
assert f([1, [2, [3, [4]], 5], [], [[6]]]) == [1, 2, 3, 4, 5, 6]
assert f([(1, [2]), "ab", {"k": [1]}, [[None]]]) == [(1, [2]), "ab", {"k": [1]}, None]
deep = [7]
for i in range(100000): deep = [i, deep]
out = f(deep); assert len(out) == 100001 and out[0] == 99999 and out[-1] == 7
wide = [[i, [i, i]] for i in range(300000)]
t = time.time(); assert len(f(wide)) == 900000; assert time.time() - t < 2.0
print("PASS")
''',
ref='''
def flatten(x):
    out, stack = [], [iter(x)]
    while stack:
        for e in stack[-1]:
            if isinstance(e, list):
                stack.append(iter(e)); break
            out.append(e)
        else:
            stack.pop()
    return out
'''))

T.append(dict(id="decide_rate_limiter", cat="decision", lang="python", hard=True, timeout=20,
spec="""## User request
"Our API lets each user make at most 5 requests in any 10-second window. Right now people burst 10 requests around the minute boundary and we get hammered. Write the limiter."

## Interface
`RateLimiter()` with `allow(user_id: str, now: float) -> bool` (`now` is seconds, non-decreasing).

## Precise rule
A request at time `now` is allowed if fewer than 5 ALLOWED requests of that user happened in the half-open interval `(now - 10, now]`. Denied requests do not count. Users are independent. Memory per user must stay bounded (do not keep timestamps forever).""",
casual="our api is supposed to let each user make at most 5 requests in any 10-second window, but people burst like 10 requests around the minute boundary and hammer us. write a RateLimiter class with allow(user_id, now) -> bool where now is seconds and never goes backwards. a request at time now is allowed if fewer than 5 allowed requests from that user happened in (now-10, now]; denied requests don't count, users are independent, and don't keep old timestamps forever.",
tests=r'''
from solution import RateLimiter
r = RateLimiter()
assert all(r.allow("u", t) for t in [0, 1, 2, 3, 4])
assert not r.allow("u", 9.9)
assert r.allow("v", 9.9)
assert r.allow("u", 10.0)          # request at 0 left the window (10-10, 10]
assert not r.allow("u", 10.5)
# boundary burst: fixed windows would allow 10 within ~1 second
b = RateLimiter()
assert all(b.allow("x", 9.5 + i * 0.05) for i in range(5))
assert not any(b.allow("x", 10.1 + i * 0.05) for i in range(5)), "fixed-window behaviour"
# denied requests do not count
d = RateLimiter()
for t in range(5): assert d.allow("z", t)
for t in [5, 6, 7, 8, 9]: assert not d.allow("z", t)
assert d.allow("z", 10.0) and d.allow("z", 11.0)
# bounded memory: many old requests
m = RateLimiter()
for i in range(200000): m.allow("w", i * 3.0)
import sys
sizes = [len(v) for v in vars(m).values() if hasattr(v, "__len__")]
inner = []
for v in vars(m).values():
    if isinstance(v, dict):
        for x in v.values():
            if hasattr(x, "__len__"): inner.append(len(x))
assert all(s <= 10 for s in inner), f"unbounded per-user state: {max(inner)}"
print("PASS")
''',
ref='''
from collections import deque, defaultdict
class RateLimiter:
    def __init__(self, limit=5, window=10.0):
        self.limit, self.window = limit, window
        self.hits = defaultdict(deque)
    def allow(self, user_id, now):
        q = self.hits[user_id]
        while q and q[0] <= now - self.window: q.popleft()
        if len(q) < self.limit:
            q.append(now); return True
        return False
'''))

T.append(dict(id="decide_money_sum", cat="decision", lang="python", hard=False, timeout=30,
spec="""## User request
"We sum invoice amounts and sometimes the report shows 0.30000000000000004 or is off by a cent on big totals. Amounts come in as strings like '19.99', '-5', '0.1' (at most 2 decimal places, can be up to 15 digits before the point). Give me `add_amounts(amounts: list[str]) -> str` that returns the exact total formatted with exactly 2 decimals, e.g. '0.30'. Lists can have a million entries."

## Notes
- Negative totals format as e.g. `'-1.50'`; zero is `'0.00'`.
- Must run in under 2 seconds for 1,000,000 amounts.""",
casual="we sum invoice amounts and the report sometimes shows 0.30000000000000004 or is a cent off on big totals. amounts are strings like '19.99', '-5', '0.1', max 2 decimals and up to 15 digits before the point. write add_amounts(amounts) that returns the exact total as a string with exactly 2 decimals, like '0.30'. negative totals look like '-1.50' and zero is '0.00'. lists can be a million items and it should take under 2 seconds.",
tests=r'''
import time
from solution import add_amounts as f
assert f(["0.1", "0.2"]) == "0.30"
assert f([]) == "0.00"
assert f(["-5", "3.5"]) == "-1.50"
assert f(["19.99", "0.01"]) == "20.00"
assert f(["999999999999999.99", "0.01"]) == "1000000000000000.00"
assert f(["0.10", "-0.1"]) == "0.00"
big = ["0.01"] * 1000000
t = time.time(); assert f(big) == "10000.00"; assert time.time() - t < 2.0
assert f(["1234567890123.45"] * 3) == "3703703670370.35"
print("PASS")
''',
ref='''
from decimal import Decimal
def add_amounts(amounts):
    s = sum(map(Decimal, amounts), Decimal(0))
    r = s.quantize(Decimal("0.01"))
    return "0.00" if r == 0 else f"{r:.2f}"
'''))

T.append(dict(id="decide_csv_parse", cat="decision", lang="python", hard=False, timeout=20,
spec="""## User request
"Customers upload CSV exports and our split(',') parser breaks: some fields are quoted and contain commas, line breaks, or doubled quotes. Write `parse_csv(text: str) -> list[list[str]]`."

## Rules (RFC 4180)
- Comma separator; records end with `\\n` or `\\r\\n`.
- A field may be wrapped in double quotes; inside quotes, commas and line breaks are literal and `""` means one `"`.
- A final line break does not create an extra empty record. Empty fields are `''`.
- Return all fields as strings exactly as written (no stripping, no type conversion).""",
casual="customers upload csv files and our split(',') parser breaks because some fields are quoted and contain commas, line breaks or doubled quotes. write parse_csv(text) that returns a list of rows (lists of strings). normal rfc 4180 rules: comma separated, rows end with \\n or \\r\\n, quoted fields can contain commas and newlines, \"\" inside quotes means one quote, a trailing newline doesn't make an extra empty row, empty fields are '' and keep fields exactly as written (no stripping or converting).",
tests=r'''
from solution import parse_csv as f
assert f("a,b\n1,2\n") == [["a","b"],["1","2"]]
assert f('a,"b,c",d\n"x""y","multi\nline",z\r\n') == [["a","b,c","d"],['x"y',"multi\nline","z"]]
assert f("a,,b\n,\n") == [["a","","b"],["",""]]
assert f(' a , b \n') == [[" a "," b "]]
assert f("x,y") == [["x","y"]]
assert f('"",""\r\n1,2') == [["",""],["1","2"]]
assert f("") == []
print("PASS")
''',
ref='''
import csv, io
def parse_csv(text):
    return [row for row in csv.reader(io.StringIO(text, newline=""))]
'''))

T.append(dict(id="decide_dedupe_records", cat="decision", lang="python", hard=True, timeout=30,
spec="""## User request
"Our import gets the same record many times. Write `unique_records(records: list[dict]) -> list[dict]` that drops duplicates and keeps the first occurrence in the original order. Two records are duplicates if they have the same keys and values, regardless of key order. Values can be str, int, float, bool, None, or nested lists/dicts of those. Imports have ~200k records."

## Notes
- Must run in under 2 seconds for 200,000 records.
- Return the original dict objects (no copies needed).""",
casual="our import gets the same record many times. write unique_records(records) that drops duplicate dicts keeping the first one, in the original order. duplicates = same keys and values, key order doesn't matter, and values can be str/int/float/bool/None or nested lists and dicts of those. imports are ~200k records and should take under 2 seconds. just return the original dicts.",
tests=r'''
import random, time
from solution import unique_records as f
a = {"id": 1, "tags": ["x", "y"], "meta": {"k": [1, {"z": None}]}}
b = {"meta": {"k": [1, {"z": None}]}, "tags": ["x", "y"], "id": 1}
c = {"id": 1, "tags": ["y", "x"], "meta": {"k": [1, {"z": None}]}}
out = f([a, b, c, a])
assert len(out) == 2 and out[0] is a and out[1] is c
assert f([]) == []
assert len(f([{"x": 1.5}, {"x": 1.5}, {"x": "1.5"}])) == 2
r = random.Random(8)
recs = [{"id": r.randint(0, 50000), "v": [r.randint(0, 3)], "m": {"a": r.choice([None, True, "s"])}} for _ in range(200000)]
t = time.time(); got = f(recs); el = time.time() - t
assert el < 2.0, f"too slow {el:.2f}s"
import json
seen, exp = set(), []
for x in recs:
    k = json.dumps(x, sort_keys=True)
    if k not in seen: seen.add(k); exp.append(x)
assert len(got) == len(exp) and all(g is e for g, e in zip(got, exp))
print("PASS")
''',
ref='''
def _freeze(v):
    if isinstance(v, dict): return ("d", tuple(sorted((k, _freeze(x)) for k, x in v.items())))
    if isinstance(v, list): return ("l", tuple(_freeze(x) for x in v))
    return (type(v).__name__, v)
def unique_records(records):
    seen, out = set(), []
    for r in records:
        k = _freeze(r)
        if k not in seen: seen.add(k); out.append(r)
    return out
'''))

T.append(dict(id="concurrency_counter", cat="debug", lang="python", hard=False, timeout=60,
given='''import time

class Counter:
    def __init__(self):
        self.counts = {}

    def incr(self, key, n=1):
        cur = self.counts.get(key, 0)
        time.sleep(0)          # simulates other work between read and write
        self.counts[key] = cur + n

    def snapshot(self):
        return dict(self.counts)
''',
spec="""## Bug report
Under load (many threads calling `incr`) totals come out too low.

## Task
Make `Counter` (code below) thread-safe:
- `incr` from any number of threads must never lose updates (keep the `time.sleep(0)` line, it stands in for real work).
- `snapshot()` returns a consistent copy.
- Keep the same public interface.""",
casual="our Counter class (below) loses counts when lots of threads call incr at once. make it thread safe without losing updates (keep the time.sleep(0) line, that's standing in for real work), snapshot() should return a consistent copy, and keep the same interface.",
tests=r'''
import threading
from solution import Counter
src = open("solution.py").read(); assert "sleep(0)" in src, "removed the simulated work"
c = Counter()
def work(k):
    for _ in range(3000): c.incr(k); c.incr("all", 2)
ts = [threading.Thread(target=work, args=(f"k{i%4}",)) for i in range(16)]
[t.start() for t in ts]; [t.join() for t in ts]
s = c.snapshot()
assert s["all"] == 16 * 3000 * 2, s["all"]
assert all(s[f"k{i}"] == 4 * 3000 for i in range(4)), s
s["all"] = 0; assert c.snapshot()["all"] == 96000
print("PASS")
''',
ref='''
import time, threading
class Counter:
    def __init__(self):
        self.counts = {}; self._lock = threading.Lock()
    def incr(self, key, n=1):
        with self._lock:
            cur = self.counts.get(key, 0)
            time.sleep(0)
            self.counts[key] = cur + n
    def snapshot(self):
        with self._lock: return dict(self.counts)
'''))
