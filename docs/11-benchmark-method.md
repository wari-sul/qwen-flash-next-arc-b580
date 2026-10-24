# 11. Benchmark methodology

The goal was a practical decision: which of the two models should stay deployed as my coding model. So the benchmark tests what I actually use it for, and every result is decided by running code, never by asking a model to grade.

Everything is in [benchmark/codebench/](../benchmark/codebench/). Run it yourself with:

```
python3 bench.py validate                                   # reference solutions vs graders, no model needed
python3 validate_agents.py                                  # agent repos: original fails, fixed passes
python3 bench.py run <label> /etc/strata/<config>.json <port>
python3 regrade.py results/<label>.jsonl                     # re-grade stored answers with the current grader
python3 bench_report.py results/a.regraded.jsonl results/b.regraded.jsonl
```

## What is tested (103 graded items per model)

### 1. Code tasks: 24 tasks in 4 languages

| Category | Tasks | What it checks |
|---|---|---|
| implement | merge intervals, top-k words, TTL+LRU cache, duration parser, Dijkstra with path, expression evaluator, JS deepEqual | Writing correct code from a precise spec, including edge cases |
| efficiency | count pairs, running median, log statistics | Picking the right algorithm: every test includes a large input with a time limit (e.g. 200K items in under 1 to 2 s) |
| debug | binary search bug, shared mutable default, wrong month key, JS async `forEach`, thread-safety race | Finding and fixing real bugs in given code. The original buggy code is checked to fail the tests |
| refactor | invoice with VAT/discounts in `Decimal`, recursive flatten to iterative | Changing working code without breaking existing behaviour |
| decision | sliding-window rate limiter, exact money sums, RFC 4180 CSV, dedupe nested records | Turning a user's request into the right design choice. The tests encode the subtle part (fixed vs sliding window, float vs decimal, `split(',')` vs a real CSV parser, key-order-insensitive dedupe) |
| sql | top earners with ties, monthly revenue with all 12 months and a running total | SQLite, window functions and recursive CTEs |
| bash | 3 largest files | Paths with spaces, sorting, error handling and exit codes |

Languages: 19 Python, 2 JavaScript (Node 22), 2 SQL (SQLite 3.46), 1 Bash.

### 2. Prompt styles

Each code task is asked in two ways with identical information:

- **Proper**: a system prompt with engineering rules ("one fenced code block, standard library only, consider edge cases and input sizes") and a structured spec with headings for requirements, constraints and errors.
- **Casual**: one paragraph, written the way I would type it into a chat, no system prompt.

Proper prompts run twice (48 runs), casual once (24 runs).

### 3. Reasoning effort

Proper prompts run at `reasoning_effort: low`. The 5 hardest tasks (expression evaluator, TTL cache, rate limiter, invoice refactor, monthly SQL) also run once at `xhigh` with a 16K token budget, to see whether thinking longer helps.

### 4. Tool calling: 8 cases x 2 runs

Single call, two parallel calls, knowing when *not* to call a tool, choosing the right tool out of five, filling a nested argument schema (date, integer duration, enum, array of objects), using a tool result in the final answer, plus a call and a result-handling case through the Anthropic `/v1/messages` endpoint.

### 5. Agent tasks: 5 repos x 2 runs

A minimal agent loop gives the model four tools (`list_files`, `read_file`, `write_file`, `run_tests`) and a small repository with failing tests:

| Repo | Task |
|---|---|
| ag_bugfix | Two bugs in a text-statistics module |
| ag_feature | Add due dates, priorities and an `overdue()` query to a todo list without breaking the old API |
| ag_crossfile | A config value read as a string from the environment, used as an attribute in another file |
| ag_perf | An O(n^2) duplicate finder that must become fast without changing results |
| ag_vague | "Slugs look broken for titles like 'Creme Brulee: A Guide!'": Unicode normalization and cleanup |

An episode passes only if the tests pass at the end, the model stopped on its own (no tool call in its last turn, max 16 turns), and the test files are byte-identical to the originals (editing tests to pass is a fail).

## Grading and fairness

- Every task has a reference solution. `bench.py validate` runs the reference through the grader (must pass) and the buggy starting code (must fail) before any model time is spent. This caught one bug of mine: my first TTL cache reference was too slow for its own test.
- Model code runs as an unprivileged `bench` user in a temporary directory with a timeout.
- **Code extraction:** the grader takes the fenced code blocks from the answer, language-tagged ones first, longest first, and tries up to 4 until one passes. I added this mid-run after finding that casual answers often put a usage example in its own block, which my first grader picked instead of the solution. All stored answers for both models were re-graded with the final grader. The re-grade flipped exactly 4 Coder answers from fail to pass and none the other way; DavidAU ran with the final grader from the start. Raw logs keep the original verdicts.
- Sampling: `temperature 0.6, top_p 0.95, top_k 20, min_p 0` for both models.
- Both models run with the same Strata config apart from model paths: 256K context, MTP on, same VRAM reserve.
- One model is loaded at a time, back to back on the same hardware.

## What is measured

Per item: pass/fail, completion tokens, wall time, engine generation speed (from the Strata engine log), MTP draft acceptance, code size, finish reason (to catch answers cut off by the token limit) and the test's own run time. For agent episodes also: turns, tool calls, file writes, test runs, malformed tool calls, prompt tokens and whether tests were tampered with.

Hardware state was logged alongside: host available RAM every 30 s, plus GPU temperature, fan, power and clock snapshots.

## Limits of this benchmark

- One run (or two) per item. Pass rates on small task counts move by several points with one flip.
- The tasks are mine. They reflect my use (Python-heavy, practical) and not a standard leaderboard.
- Temperature 0.6 means re-running will not reproduce the exact answers.
