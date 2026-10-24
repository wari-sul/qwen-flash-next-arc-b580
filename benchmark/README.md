# Benchmark code

| Folder | What |
|---|---|
| [codebench/](codebench/) | The final coding benchmark: 103 graded items per model (code tasks, prompt styles, reasoning effort, tool calling, agent repos). Method: [docs/11-benchmark-method.md](../docs/11-benchmark-method.md) |
| [earlier/](earlier/) | The smaller test scripts used along the way: MTP A/B, context scaling with a needle test, the 13-prompt reasoning set, prompt-cache check |

## codebench files

| File | Purpose |
|---|---|
| `bench.py` | Runner. `validate` checks every grader against its reference solution and the buggy starting code. `run <label> <config> <port> [phases]` runs a model and appends one JSON line per item to `results/<label>.jsonl` |
| `tasks_py1.py` | Implement-from-spec and efficiency tasks (Python) |
| `tasks_py2.py` | Debug, refactor, decision and concurrency tasks |
| `tasks_other.py` | SQL (SQLite), Bash, JavaScript tasks |
| `tasks_tools.py` | Tool-calling cases (OpenAI and Anthropic styles) and the 5 agent repositories |
| `validate_agents.py` | Checks each agent repo: original code fails its tests, a reference fix passes |
| `regrade.py` | Re-grades stored answers with the current grader, writes `<label>.regraded.jsonl` |
| `bench_report.py` | Side-by-side tables from one or more result files |

## Requirements

- Python 3.10+ (standard library only), Node.js 18+ for the JS tasks, `sqlite3` module (bundled with Python), bash with GNU coreutils/findutils.
- A Strata run config (the runner reads `api_key` and `log` from it; the engine log is parsed for tokens/s and draft acceptance).
- Optional but recommended: an unprivileged user called `bench`. When the runner is root it executes model code as that user (`useradd -r -M -s /usr/sbin/nologin bench`).

## Safety

The runner executes code written by a model. Run it in a disposable container or VM, never on a machine with data you care about. Each test runs in a fresh temporary directory, as the `bench` user, with a timeout and a minimal environment.
