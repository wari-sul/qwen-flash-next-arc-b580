# 12. Results: DavidAU IQ3_S vs ISTA Coder IQ1_M

Both models, same hardware, same Strata config (256K context, MTP on), same 103 graded items, run back to back on 2026-10-24. Method: [11-benchmark-method.md](11-benchmark-method.md). Raw data: [results/codebench/](../results/codebench/) (`*.regraded.jsonl` are authoritative), full report: [results/codebench/summary.txt](../results/codebench/summary.txt).

## Headline

| | Coder IQ1_M | DavidAU IQ3_S |
|---|---|---|
| **All graded items** | **96/103 (93%)** | **100/103 (97%)** |
| Proper-spec coding (48) | 45 (94%) | 46 (96%) |
| Casual-prompt coding (24) | 21 (88%) | 23 (96%) |
| xhigh reasoning, 5 hardest tasks | 4/5 | 5/5 |
| Tool calling (16) | 16/16 | 16/16 |
| Agent repos (10) | 10/10 | 10/10 |
| Generation speed, coding (engine) | 34.2 tok/s | 30.2 tok/s |
| Tokens generated, whole run | 201,485 | 201,019 |
| Total request time, whole run | 1.75 h | 1.91 h |
| Pinned host RAM | ~23 GiB | ~47 GiB |
| Host RAM available while loaded | 30.9 to 31.7 GiB | 7.9 to 8.6 GiB |

## Coding

### By phase

| | Coder | DavidAU |
|---|---|---|
| **Proper spec, low effort** (48 runs) | 45/48 | 46/48 |
| completion tokens, total / median per task | 68,581 / 1,016 | 80,680 / 994 |
| request time, total / median per task | 35.0 min / 32 s | 47.5 min / 37 s |
| generation speed | 34.2 tok/s | 30.2 tok/s |
| **Casual prompt, low effort** (24 runs) | 21/24 | 23/24 |
| completion tokens, total / median | 70,020 / 1,618 | 54,153 / 1,615 |
| request time, total / median | 34.2 min / 44 s | 27.5 min / 50 s |
| generation speed | 35.2 tok/s | 33.9 tok/s |
| **xhigh effort** (5 runs) | 4/5 | 5/5 |
| completion tokens, total / median | 46,706 / 9,680 | 54,688 / 12,315 |
| request time, total / median | 25.7 min / 5.4 min | 30.8 min / 7.1 min |
| generation speed | 30.7 tok/s | 30.1 tok/s |
| Answers cut off by the token limit | 0 | 0 |
| MTP draft acceptance | 68 to 75% | 67 to 74% |

### By category and language (all coding runs)

| | Coder | DavidAU |
|---|---|---|
| implement | 19/23 | 21/23 |
| efficiency | 9/9 | 9/9 |
| debug | 15/15 | 15/15 |
| refactor | 7/7 | 7/7 |
| decision | 13/13 | 12/13 |
| sql | 5/7 | 7/7 |
| bash | 2/3 | 3/3 |
| Python | 57/61 | 58/61 |
| JavaScript | 6/6 | 6/6 |

### Per task (c = proper-spec runs, then casual run; x = xhigh)

Only tasks where at least one run failed:

| Task | Coder | DavidAU |
|---|---|---|
| impl_ttl_lru | c ✗✗ ✓, x ✓ | c ✗✓ ✓, x ✓ |
| impl_parse_duration | c ✓✗ ✓ | c ✓✗ ✓ |
| impl_expr_eval | c ✓✓ ✓, x ✗ | c ✓✓ ✓, x ✓ |
| sql_top_earners | c ✓✓ ✗ | c ✓✓ ✓ |
| sql_monthly_cumulative | c ✓✓ ✗, x ✓ | c ✓✓ ✓, x ✓ |
| bash_largest_files | c ✓✓ ✗ | c ✓✓ ✓ |
| decide_csv_parse | c ✓✓ ✓ | c ✓✓ ✗ |

Every other task (17 of 24) passed every run on both models.

### Every failure, explained

I read each failing answer. None of these are grader problems.

**Both models made the same two mistakes:**

- **TTL + LRU cache timed out** (Coder both low-effort runs, DavidAU one). Once the cache is full, each insert scans the whole cache for expired entries, so `put` becomes O(n) instead of the required O(1) amortized, and the 500K-operation test runs out of time. In one run Coder's notes even claimed the purge was "amortized O(1) per operation (each entry is purged at most once)", which ignores the cost of scanning the entries that are not expired. Both models fixed it at xhigh effort.
- **parse_duration accepted `"1h\n"`** (one run each). Both used `re.match(r'^...$')`. In Python `$` also matches just before a trailing newline. The spec says anything else must raise `ValueError`. A classic.

**Coder only:**

- **SQL top earners, casual prompt:** put a window function in `WHERE` (`WHERE RANK() OVER (...) = 1`), which no SQL dialect allows, and stated it "works in SQLite 3.25+". A correct correlated-subquery version was only in a quoted fallback paragraph.
- **SQL monthly revenue, casual prompt:** used `generate_series`, a table-valued function that is not in standard SQLite builds.
- **Bash largest files, casual prompt:** output format did not match the spec.
- **Expression evaluator, xhigh:** after 12.8K tokens of reasoning, the parser crashed on its own bug (`UnboundLocalError` for an index variable). The same task passed in all three low-effort runs.

**DavidAU only:**

- **CSV parser, casual prompt:** `parse_csv("")` returned `[['']]` instead of `[]`. The answer documents this choice deliberately ("Produces `[['']]`: one row, one empty field"). Neither prompt spells out the empty-input case; my test follows Python's `csv` module, which returns `[]`. A fair check, but the most borderline failure in the set.

### Prompt style

- **Coder dropped from 94% to 88%** going from the structured spec to a casual paragraph. All three casual failures were SQL or Bash.
- **DavidAU stayed at 96%** either way.
- With casual prompts both models wrote longer answers (median about 1,600 tokens vs 1,000), mostly explanation around the code. Several casual answers put the solution and a separate usage example in different code blocks, which is what broke my first grader ([11](11-benchmark-method.md#grading-and-fairness)).

### Reasoning effort

On the five hardest tasks, `xhigh` used about 10x the tokens of `low` (median 9.7K to 12.3K tokens, 5 to 7 minutes per answer). It fixed the TTL cache for both models. It broke the expression evaluator for Coder, which `low` had solved three times. For day-to-day coding `low` is the better default; `xhigh` is worth it for a task that `low` keeps getting wrong.

## Tool calling

Both 16/16: single call, parallel calls (Paris and Tokyo in one turn), answering without a tool when none is needed, picking `search_files` out of five tools, a nested schema (ISO date, integer duration, enum, array of attendee objects), using a tool result, and the Anthropic `/v1/messages` call and result cases. No malformed arguments. Median time per call: 4.2 s (Coder), 5.7 s (DavidAU).

## Agent episodes

| | Coder | DavidAU |
|---|---|---|
| Passed | 10/10 | 10/10 |
| LLM turns, total (median per episode) | 52 (5) | 51 (5) |
| Tool calls | 56 | 54 |
| File writes | 11 | 11 |
| Test runs | 12 | 10 |
| Malformed or failed tool calls | 0 | 0 |
| Stopped on its own | 10 | 10 |
| Edited the tests | 0 | 0 |
| Prompt tokens / completion tokens | 48,913 / 14,868 | 45,871 / 10,147 |
| Time per episode, median (range) | 33 s (20 to 225 s) | 45 s (32 to 71 s) |
| Total time | 9.1 min | 7.4 min |

Both models behaved like a careful developer: list files, read the source and the tests, write one fix, run the tests, stop. Neither ever touched a test file. The one notable difference was the vague slug task: Coder spent 225 s and 6.9K tokens on its first attempt (94 s on the second), while DavidAU took 51 s and 71 s with 1.3K and 1.8K tokens.

## Speed and resources

- **Generation speed:** Coder is about 13% faster on coding (34.2 vs 30.2 tok/s) and about the same on tools, agents and xhigh (30 to 34 tok/s for both). That fits its model shape: half the experts, so twice the share of them fits in VRAM and fewer have to come over PCIe. I did not compare the per-request cache hit rates directly.
- **Total time:** both generated about 201K tokens over the run. Coder needed 1.75 h, DavidAU 1.91 h (9% more).
- **Memory:** this is the big difference. DavidAU leaves the host about 8 GiB; Coder leaves about 31 GiB.
- **Hardware during the run:** GPU 65 to 70 C, about 110 W, 2,850 MHz with no throttling; CPU 65 to 67 C; host never below 7.9 GiB available.

## Earlier tests (for completeness)

| Test | Coder | DavidAU |
|---|---|---|
| 17-task graded suite (MTP on) | 49/51 at 256K, 39.7 tok/s (missed a letter-reversal task in 2 of 3 runs) | 51/51 at 32K (34.1 tok/s); 34/34 at 256K (34.7 tok/s) |
| 256K needle test (5 facts in 243K tokens) | 5/5, 647 tok/s prefill, 39.0 tok/s after | 5/5, 546 tok/s prefill, 33.2 tok/s after |
| 13-prompt hard reasoning set | 12/12 applicable | 13/13 |

## Verdict

**Keep DavidAU IQ3_S as the default coding model.**

- It passed 100 of 103 items against 96. The gap is small, but it is consistent in one direction and concentrated where it matters to me: casual prompts and SQL/Bash, which is how I actually ask for code.
- Its one unique failure was a deliberate, documented choice on an edge case my prompt did not specify. Coder's unique failures were invalid SQL presented as valid, a missing SQLite function, a wrong output format and a crash in its own parser.
- Tool use and agent behaviour were identical, so there is nothing to give up there.

What it costs: about 13% slower generation and 23 GiB more locked RAM. The host has run stably at about 8 GiB available with it loaded, so that is acceptable here.

**Pick the Coder model instead if** you need the RAM for other workloads, or if you mostly write precise, structured prompts, where the two models were nearly identical (45 vs 46 of 48).

Keeping the Coder files as a fallback costs only 29.6 GB of disk, because shard 2 is shared, and the `before_load` hook switches between them automatically.

Caveats: one to three runs per item, my own task set, temperature 0.6. A 4-item difference out of 103 would not survive much re-running without more samples. Treat it as "DavidAU is at least as good and more robust to sloppy prompts", not as a precise ranking.
