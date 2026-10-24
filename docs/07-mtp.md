# 07. MTP speculative decoding

Qwen3.8-Flash-Next has a multi-token prediction (MTP) block: one extra transformer layer, trained alongside the model, that predicts the next token from the main model's hidden state. Strata uses it as a draft model. It proposes up to 4 tokens, the main model verifies them in one pass, and accepted tokens are free.

## Getting the draft layer onto an Intel install

The quantized GGUFs do not contain the MTP block. Strata's setup normally fetches it from the original BF16 checkpoint, but on Intel the setup does not run, so I did the same steps by hand ([scripts/setup/06-mtp-draft.sh](../scripts/setup/06-mtp-draft.sh)):

```
T=~/.local/share/strata/terminal/0.1.48; PY=$T/python/bin/python3.12; cd $T
C=$(grep -oP '^LLAMA_CPP_COMMIT\s*=\s*"\K[0-9a-f]+' setup.py)     # the llama.cpp commit Strata pins
# fetch that llama.cpp revision for its gguf-py, then:
export STRATA_GGUF_PY=/root/third_party/llama.cpp-$C/gguf-py STRATA_SOURCE=huggingface
M=/models/strata-data/mtp
$PY tools/mtp_fetch.py fetch  --out $M        # range-reads only the 31 MTP tensors (5.2 GB) out of the BF16 shards
$PY tools/mtp_fetch.py verify --out $M        # sha256 per tensor
$PY tools/mtp_pack.py --src $M --experts q2_0 --out $M/mtp-q2_0.gguf
$PY tools/mtp_rt.py   --gguf $M/mtp-q2_0.gguf --out $M/rt
cp $T/data/draft_vocab_en.bin $M/rt/draft_vocab.bin      # English/code draft vocabulary
```

- The MTP block is 31 tensors, 5.21 GB in BF16, spread over 28 of the checkpoint's 131 shards. `mtp_fetch.py` reads byte ranges, so only those 5.2 GB are downloaded, not the whole checkpoint.
- `mtp_pack.py` quantizes the draft layer's 512 experts to Q2_0 (about 0.89 GB total). The engine reported about 839 MiB of VRAM for it.
- The draft vocabulary restricts drafting to a subset of tokens (English and code here). Strata also ships French and Cyrillic subsets.
- After `rt/` is built, the raw tensors can be deleted (I freed 4.9 GB).

Then add to the run config:

```
"--mtp", "/models/strata-data/mtp/rt", "--spec-min-p", "0.5"     (and "mtp": true)
```

## Does it help? Does it hurt quality?

Graded suite: 17 tasks (arithmetic, logic, code with unit tests, bash, JSON, formatting, word puzzles, a trick question, an honesty check), 3 runs each, graded by code. Same model, same prompts, 32K context, only MTP toggled.

| | MTP off | MTP on |
|---|---|---|
| Passed | 51/51 | 51/51 |
| Generation speed | 24.1 tok/s | 34.1 tok/s (1.41x) |
| Total wall time | 432 s | 319 s |
| Draft acceptance | 1,377 / 2,049 (67%) | 4,541 / 5,718 (79%) |

A second, ungraded set of 8 prompts (greedy and sampled) averaged 22.8 tok/s off and 29.9 tok/s on (1.31x). Code and JSON benefit most, up to about 42 tok/s; free-form prose benefits least.

Notes:

- With MTP off the engine still reported some draft activity (the "off" column). That is Strata's non-MTP speculative path. I did not investigate it further.
- Under greedy decoding, 5 of 8 answers were byte-identical with MTP on and off; the other 3 (longer code, bash and explanation answers) differed in wording. In theory verification is exact; in practice batched verification changes floating-point order slightly. All graded answers were correct either way.
- Cost: about 839 MiB of VRAM, which would otherwise hold roughly 400 more experts. The speedup is worth far more than those experts.

Verdict: keep MTP on. Raw data: [results/earlier-tests/mtp/](../results/earlier-tests/mtp/).
