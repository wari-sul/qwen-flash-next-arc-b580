# Results

| Path | What |
|---|---|
| `codebench/` | Final benchmark, one JSON line per graded item. `*.regraded.jsonl` are the authoritative files (re-graded with the final code extractor); the plain `.jsonl` keep the verdicts as logged during the run |
| `codebench/summary.txt` | Output of `bench_report.py` for both models |
| `codebench/*.log` | The live run logs, with the verdicts as originally logged (before the grader fix) |
| `codebench/host-memavailable-kb.txt` | Host `MemAvailable` in kB every 30 s during both runs (Coder 03:10 to 04:58, DavidAU 04:59 to 06:54) |
| `earlier-tests/mtp/` | MTP on/off A/B: graded suite (`q-mtp-*.json`) and an ungraded speed set (`mtp-*.json`), plus the MTP tensor inventory and quantization report |
| `earlier-tests/context/` | 128K / 256K needle tests (`ctx-*.json`), graded suite at each size (`q-ctx-*.json`), engine placement log |
| `earlier-tests/reasoning/` | The 13-prompt hard reasoning set with full answers and reasoning for both models |
| `earlier-tests/graded-suite/` | Coder model on the 17-task graded suite |

Field names in the codebench files: `ok` pass/fail, `completion_tokens` from the API usage, `gen_tokens`/`gen_ms` and `drafts_accepted`/`drafts_proposed` from the Strata engine log, `wall` seconds per request, `test_s` seconds the tests took, `answer` the model's final answer, `reasoning` the last 4,000 characters of its reasoning.
