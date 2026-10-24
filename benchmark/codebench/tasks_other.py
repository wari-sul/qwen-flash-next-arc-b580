# Part 3: other languages (SQL via sqlite3, bash, JavaScript).
T = []

_SCHEMA = """CREATE TABLE departments(id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE employees(id INTEGER PRIMARY KEY, name TEXT NOT NULL, dept_id INTEGER REFERENCES departments(id), salary INTEGER NOT NULL, hired TEXT NOT NULL);"""

_SQL_HARNESS = r'''
import sqlite3, random, sys
sql = open("solution.sql").read()
def build(seed):
    db = sqlite3.connect(":memory:")
    db.executescript(SCHEMA)
    r = random.Random(seed)
    depts = ["Ops", "Eng", "Sales", "Legal", "Empty"]
    for i, d in enumerate(depts, 1): db.execute("INSERT INTO departments VALUES(?,?)", (i, d))
    names = ["Ana","Ben","Cy","Dee","Eve","Fay","Gus","Hal","Ivy","Jo","Kai","Lu"]
    for i in range(1, 41):
        db.execute("INSERT INTO employees VALUES(?,?,?,?,?)", (i, r.choice(names) + str(i), r.randint(1, 4) if i % 13 else None,
                   r.choice([50000, 60000, 70000, 70000, 90000]), f"20{r.randint(18,26)}-0{r.randint(1,9)}-1{r.randint(0,9)}"))
    return db
'''

T.append(dict(id="sql_top_earners", cat="sql", lang="sql", hard=False, timeout=20,
spec=f"""## Task
Write ONE SQLite query (SQLite 3.46) for this schema:
```sql
{_SCHEMA}
```
For each department, return its highest-paid employee(s). If several employees tie for the top salary in a department, return all of them. Employees with no department (`dept_id` NULL) and departments without employees produce no rows.

## Output
Columns, in order: `dept_name`, `employee_name`, `salary`. Order by `dept_name`, then `employee_name`.""",
casual=f"sqlite question. schema:\n{_SCHEMA}\nwrite one query that gives the top-paid employee(s) of every department — if there's a tie for the top salary in a department return all of them. employees with no department and departments with nobody shouldn't show up. columns dept_name, employee_name, salary, ordered by dept_name then employee_name.",
tests=f"SCHEMA = {_SCHEMA!r}\n" + _SQL_HARNESS + r'''
REF = """SELECT d.name AS dept_name, e.name AS employee_name, e.salary FROM employees e JOIN departments d ON d.id = e.dept_id
WHERE e.salary = (SELECT MAX(salary) FROM employees x WHERE x.dept_id = e.dept_id) ORDER BY dept_name, employee_name"""
for seed in range(6):
    db = build(seed)
    exp = db.execute(REF).fetchall(); got = db.execute(sql).fetchall()
    assert got == exp, (seed, got[:4], exp[:4])
    assert [c[0] for c in db.execute(sql).description] == ["dept_name", "employee_name", "salary"]
print("PASS")
''',
ref="""SELECT d.name AS dept_name, e.name AS employee_name, e.salary
FROM employees e JOIN departments d ON d.id = e.dept_id
WHERE e.salary = (SELECT MAX(salary) FROM employees x WHERE x.dept_id = e.dept_id)
ORDER BY dept_name, employee_name;"""))

_OSCHEMA = "CREATE TABLE orders(id INTEGER PRIMARY KEY, order_date TEXT NOT NULL, amount REAL NOT NULL, status TEXT NOT NULL);"
T.append(dict(id="sql_monthly_cumulative", cat="sql", lang="sql", hard=True, timeout=20,
spec=f"""## Task
Write ONE SQLite query (SQLite 3.46, window functions and recursive CTEs are available) for:
```sql
{_OSCHEMA}
```
`order_date` is `YYYY-MM-DD`. Only orders with `status = 'paid'` count.

Return one row for EVERY month of 2025 (January..December, 12 rows, including months with no paid orders) with:
`month` (text `'YYYY-MM'`), `revenue` (sum of paid amounts that month, 0 when none, rounded to 2 decimals), `cumulative` (running total of revenue from January through that month, rounded to 2 decimals). Order by `month`.""",
casual=f"sqlite (3.46) query please, table:\n{_OSCHEMA}\norder_date is YYYY-MM-DD and only status='paid' orders count. i need one row for every month of 2025, all 12 even if a month has no paid orders, with month as 'YYYY-MM', revenue = sum of paid amounts that month (0 if none, rounded to 2 decimals) and cumulative = running total from january to that month (also rounded to 2 decimals). order by month.",
tests=f"SCHEMA = {_OSCHEMA!r}\n" + r'''
import sqlite3, random
sql = open("solution.sql").read()
for seed in range(5):
    db = sqlite3.connect(":memory:"); db.executescript(SCHEMA); r = random.Random(seed)
    rows = []
    for i in range(300):
        y = r.choice([2024, 2025, 2025, 2025, 2026]); m = r.choice([1, 2, 3, 5, 6, 8, 9, 11, 12])
        rows.append((i, f"{y}-{m:02d}-{r.randint(1,28):02d}", round(r.uniform(1, 500), 2), r.choice(["paid", "paid", "refunded", "pending"])))
    db.executemany("INSERT INTO orders VALUES(?,?,?,?)", rows)
    exp, cum = [], 0.0
    for m in range(1, 13):
        rev = sum(a for _, d, a, s in rows if s == "paid" and d.startswith(f"2025-{m:02d}"))
        cum += rev; exp.append((f"2025-{m:02d}", round(rev, 2), round(cum, 2)))
    got = db.execute(sql).fetchall()
    assert len(got) == 12, len(got)
    for g, e in zip(got, exp):
        assert g[0] == e[0] and abs(g[1] - e[1]) < 0.011 and abs(g[2] - e[2]) < 0.011, (g, e)
    assert [c[0] for c in db.execute(sql).description] == ["month", "revenue", "cumulative"]
print("PASS")
''',
ref="""WITH RECURSIVE months(m) AS (SELECT 1 UNION ALL SELECT m + 1 FROM months WHERE m < 12),
rev AS (SELECT substr(order_date, 1, 7) AS month, SUM(amount) AS total FROM orders
        WHERE status = 'paid' AND order_date LIKE '2025-%' GROUP BY 1)
SELECT printf('2025-%02d', months.m) AS month, ROUND(COALESCE(rev.total, 0), 2) AS revenue,
       ROUND(SUM(COALESCE(rev.total, 0)) OVER (ORDER BY months.m), 2) AS cumulative
FROM months LEFT JOIN rev ON rev.month = printf('2025-%02d', months.m) ORDER BY month;"""))

T.append(dict(id="bash_largest_files", cat="bash", lang="bash", hard=False, timeout=30,
spec="""## Task
Write a bash script (GNU coreutils/findutils available) that takes a directory as its first argument and prints the 3 largest regular files under it, recursively.

## Output
- One line per file: `<size_in_bytes> <path>`, where `<path>` is exactly what `find "$1" -type f` prints for that file.
- Sorted by size descending; equal sizes sorted by path ascending (byte order, `LC_ALL=C`).
- Fewer than 3 files -> print all of them. File and directory names may contain spaces.
- Exit with status 2 and print an error to stderr if the argument is missing or not a directory.""",
casual="need a bash script: first argument is a directory, print the 3 biggest regular files under it (recursively) as '<size in bytes> <path>' lines, where path is exactly what find \"$1\" -type f prints. biggest first, same size sorted by path (plain byte order, LC_ALL=C). if there are fewer than 3 files print them all. names can have spaces. if the argument is missing or not a directory print an error to stderr and exit 2. gnu tools are available.",
tests=r'''
import os, subprocess, tempfile
def run(*args):
    return subprocess.run(["bash", "solution.sh", *args], capture_output=True, text=True, timeout=20)
d = tempfile.mkdtemp()
os.makedirs(os.path.join(d, "sub dir", "deep"))
files = {"a.txt": 100, "sub dir/b c.bin": 5000, "sub dir/deep/x y z": 5000, "c": 10, "sub dir/deep/d": 70000, ".hidden": 6000}
for p, n in files.items():
    with open(os.path.join(d, p), "wb") as fh: fh.write(b"x" * n)
os.symlink(os.path.join(d, "sub dir/deep/d"), os.path.join(d, "link"))
r = run(d); assert r.returncode == 0, r.stderr
exp = [f"70000 {d}/sub dir/deep/d", f"6000 {d}/.hidden", f"5000 {d}/sub dir/b c.bin"]
assert r.stdout.strip().split("\n") == exp, r.stdout
e = tempfile.mkdtemp(); open(os.path.join(e, "only one"), "w").write("hi")
r = run(e); assert r.stdout.strip() == f"2 {e}/only one", r.stdout
assert run().returncode == 2 and run("/nonexistent/x").returncode == 2
r = run("/nonexistent/x"); assert r.stderr.strip() and not r.stdout.strip()
print("PASS")
''',
ref='''#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 1 ] || [ ! -d "$1" ]; then echo "usage: $0 DIR" >&2; exit 2; fi
find "$1" -type f -printf '%s %p\\0' | LC_ALL=C sort -z -k1,1nr -k2 | head -z -n 3 | tr '\\0' '\\n'
'''))

T.append(dict(id="js_deep_equal", cat="implement", lang="js", hard=False, timeout=20,
spec="""## Task
Implement `deepEqual(a, b)` in Node.js (CommonJS, export with `module.exports = { deepEqual };`).

## Rules
- Primitives compare with `===`, except `NaN` equals `NaN`. `null` only equals `null`; `undefined` only equals `undefined`.
- Arrays are equal if same length and elements are deepEqual in order. An array never equals a plain object.
- Plain objects are equal if they have the same own enumerable keys (any order) and deepEqual values. `{a: undefined}` is NOT equal to `{}`.
- `Date` objects are equal if their `getTime()` values are equal.
- Must handle nesting of a few thousand levels without blowing the stack is NOT required; ordinary depth (< 500) is enough.""",
casual="write deepEqual(a, b) in node (commonjs, module.exports = { deepEqual }). primitives use === except NaN equals NaN, null only equals null and undefined only undefined. arrays equal if same length and elements deepEqual in order, and an array never equals an object. plain objects equal if they have the same own keys in any order with deepEqual values, but {a: undefined} is not equal to {}. Dates are equal if getTime() matches. normal nesting depth only.",
tests=r'''
const { deepEqual: e } = require('./solution.js');
const assert = require('assert');
const T = (a, b) => assert.strictEqual(e(a, b), true, JSON.stringify([a, b]));
const F = (a, b) => assert.strictEqual(e(a, b), false, JSON.stringify([a, b]));
T(1, 1); F(1, "1"); T(NaN, NaN); T(null, null); F(null, undefined); F(null, {}); T(undefined, undefined); F(0, null);
T([1, [2, {a: 3}]], [1, [2, {a: 3}]]); F([1, 2], [2, 1]); F([1], [1, 1]); F([], {}); F({}, []); F({0: 1, length: 1}, [1]);
T({a: 1, b: {c: [1, 2]}}, {b: {c: [1, 2]}, a: 1}); F({a: 1}, {a: 1, b: 2}); F({a: undefined}, {}); F({}, {a: undefined});
T(new Date(5), new Date(5)); F(new Date(5), new Date(6)); F(new Date(5), {}); F({}, new Date(5));
T({d: [new Date(1), NaN]}, {d: [new Date(1), NaN]}); F("abc", ["a", "b", "c"]); T("", "");
let deep1 = {}, deep2 = {}; let p1 = deep1, p2 = deep2;
for (let i = 0; i < 300; i++) { p1.x = {}; p2.x = {}; p1 = p1.x; p2 = p2.x; } p1.v = 1; p2.v = 1; T(deep1, deep2); p2.v = 2; F(deep1, deep2);
console.log('PASS');
''',
ref='''
function deepEqual(a, b) {
  if (a === b) return true;
  if (typeof a === 'number' && typeof b === 'number') return Number.isNaN(a) && Number.isNaN(b);
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') return false;
  if (a instanceof Date || b instanceof Date) return a instanceof Date && b instanceof Date && a.getTime() === b.getTime();
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a)) return a.length === b.length && a.every((x, i) => deepEqual(x, b[i]));
  const ka = Object.keys(a), kb = Object.keys(b);
  if (ka.length !== kb.length) return false;
  return ka.every(k => Object.prototype.hasOwnProperty.call(b, k) && deepEqual(a[k], b[k]));
}
module.exports = { deepEqual };
'''))
