# 04. The Strata run config, flag by flag

This is the final config for the DavidAU model (`/etc/strata/davidau-iq3s-256k.json`, key removed). The Coder config is identical apart from the paths, port, log file and expert profile.

```json
{
  "exe": "component:strata-engine",
  "args": [
    "--pack", "/models/strata-data/packs/iq3_s",
    "--native", "/models/qwen38-flash-next-abliterated-iq3s/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_S-00001-of-00002.gguf",
    "--ple-gguf", "/models/qwen38-flash-next-abliterated-iq3s/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_S-00002-of-00002.gguf",
    "--expert-profile", "/root/.local/share/strata/terminal/0.1.48/data/expert-profile.bin",
    "--expert-cache", "auto",
    "--prefill", "4096",
    "--spec", "4",
    "--max-context", "262144",
    "--kv", "int8",
    "--stream-experts",
    "--vram-reserve-mib", "2048",
    "--mtp", "/models/strata-data/mtp/rt",
    "--spec-min-p", "0.5",
    "--kv-resident", "32768"
  ],
  "tokenizer": "/models/strata-data/packs/iq3_s/tokenizer",
  "model_name": "qwen3.8-flash-next-iq3_s",
  "log": "/var/log/strata-engine.log",
  "port": 8080,
  "backend": "sycl",
  "host": "0.0.0.0",
  "api_key": "<API_KEY>",
  "mtp": true,
  "lazy_load": true,
  "idle_unload_s": 1200,
  "before_load": ["/usr/local/bin/strata-unload-peer", "8081", "/etc/strata/coder-iq1m-256k.json"],
  "before_load_timeout_s": 330,
  "before_load_strict": true
}
```

## Engine arguments

| Flag | Value | What it does here |
|---|---|---|
| `--pack` | pack dir | The hand-built pack: dense tensors, index, tokenizer ([05](05-custom-packs.md)) |
| `--native` | shard 1 | GGUF the experts are read from in place (IQ3_S / IQ1_M blocks, no conversion) |
| `--ple-gguf` | shard 2 | The second shard, which holds the large per-layer lookup tables. It is byte-identical between the two models, so one copy is hard-linked into both model folders |
| `--expert-profile` | `.bin` | Which experts are hot, used to seed the VRAM cache. Strata ships `expert-profile.bin` (full model) and `expert-profile-coder.bin` (the 256-expert Coder) |
| `--expert-cache auto` | | Fill the VRAM left after everything else with expert slots |
| `--stream-experts` | | Experts missing from VRAM are read by the GPU from pinned host memory over PCIe |
| `--vram-reserve-mib` | 2048 | VRAM kept free. 1536 also worked; 2048 leaves headroom for long prompts |
| `--prefill` | 4096 | Prompt chunk size |
| `--max-context` | 262144 | 256K, the model's native trained context ([08](08-context-scaling.md)) |
| `--kv int8` | | 8-bit KV cache |
| `--kv-resident` | 32768 | Only 32K KV cells per attention layer live in VRAM; the full 256K KV sits in pinned RAM (3.09 GiB) and streams in. Freed VRAM goes to experts |
| `--mtp` | rt dir | The multi-token prediction draft layer ([07](07-mtp.md)) |
| `--spec` | 4 | Draft up to 4 tokens per step |
| `--spec-min-p` | 0.5 | Only keep a drafted token if the draft model is at least this confident |

## Server keys (read by `strata serve`, not the engine)

| Key | Value | Notes |
|---|---|---|
| `lazy_load` | true | Start the HTTP server without loading the model. The first request loads it |
| `idle_unload_s` | 1200 | Unload after 20 minutes without requests, which gives the ~47 GB of pinned RAM back to the host |
| `before_load` | command | Runs before every load. Used to unload the other model first ([09](09-on-demand-loading.md)) |
| `before_load_strict` | true | If the hook fails, do not load (prevents both models being pinned at once) |
| `api_key` | | Bearer key for `/v1/*`. Keep the file `chmod 600` |

## What the engine reports at load (256K, DavidAU)

```
KV streaming: 32768 of 262144 cells per QSA layer in VRAM, the K/V in 3.09 GiB of pinned RAM
expert cache 1742 slots, 3.35 GiB of VRAM
23008 of 22834 experts missing from VRAM (+ 174 in the prompt loan's slots) mirrored in pinned host memory (43.82 GiB, 12.9 s); the GPU reads them over PCIe
2221 MiB of VRAM free with everything loaded
```

The model has 48 MoE layers with 512 experts each, 24,576 experts in total. About 7% of them fit in VRAM. The rest are read over PCIe on demand, and the hit rate on the VRAM cache is what makes this usable.

For the Coder model (256 experts per layer, 12,288 total) 1,896 experts fit in VRAM, about 15%, with about 20.1 GiB pinned in host RAM.
