# 06. The two models

Both are builds of **Qwen3.8-Flash-Next**, a mixture-of-experts model with 48 MoE layers of 512 experts each (plus a shared expert per layer), a 248K-token vocabulary and a native 256K context. Both use the same quantization family from ISTA-DASLab, GSQ-RCO.

## What GSQ-RCO means

- **GSQ, Gumbel-Softmax Quantization:** instead of rounding each weight to the nearest grid point, the rounding decision (and the scales) are learned. The Gumbel-Softmax trick makes the discrete "round up or round down" choice differentiable, so it can be optimized against the model's real outputs.
- **RCO, Riemannian Constrained Optimization:** a global bit-budget optimizer. It decides how many bits each tensor gets so the total stays within a size budget, rather than giving every tensor the same precision.

The result is stored in standard llama.cpp quant types (IQ3_S, IQ1_M, etc.), so any GGUF reader can load it, but the values inside are better than a plain quantize of the same type.

## Model A: DavidAU IQ3_S (abliterated)

| | |
|---|---|
| Repo | [DavidAU/Qwen3.8-Flash-Next-Abliterated-Uncensored-Turbo-Brilliance-50x-Reasoning-Instruct-GSQ-RCO-GGUF](https://huggingface.co/DavidAU/Qwen3.8-Flash-Next-Abliterated-Uncensored-Turbo-Brilliance-50x-Reasoning-Instruct-GSQ-RCO-GGUF) |
| Pinned revision | `b1b82c36770c826c41e1874f250228048cdb3f5c` |
| Lineage | ISTA-DASLab GSQ-RCO IQ3_S, abliterated by SC117, packaged by DavidAU with his "Turbo Brilliance" reasoning/instruct prompt system |
| Files | shard 1: 55.06 GB, shard 2: 28.80 GB (83.86 GB total), plus a 0.91 GB BF16 vision projector (unused, vision off) |
| Experts | all 512 per layer, 24,576 total |
| In VRAM at 256K | 1,742 experts (about 7%), 3.35 GiB |
| Pinned host RAM | 43.8 GiB experts + 3.1 GiB KV at 256K |
| Host RAM left with it loaded | about 7.4 to 8.7 GB of 62 GiB |

"Abliterated" means the refusal direction was removed from the weights, so the model does not refuse requests. That is a property to be aware of, not a feature I benchmarked.

The DavidAU file ships a much larger chat template than the upstream quant (about 222K characters), which is one reason a stock Strata pack does not match it ([05](05-custom-packs.md)).

## Model B: ISTA-DASLab Coder IQ1_M

| | |
|---|---|
| Repo | [ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF), folder `IQ1_M` |
| Pinned revision | `bba88856f8c3c0c9e40e45f82d05e228b814ac43` |
| What it is | Expert-pruned for code: 256 of 512 experts kept in every layer (12,288 total), then quantized with GSQ-RCO |
| Files | shard 1: 29.61 GB, shard 2: 28.80 GB (58.4 GB listed on Hugging Face) |
| In VRAM at 256K | 1,896 experts (about 15%) |
| Pinned host RAM | about 20.1 GiB experts + 3.1 GiB KV at 256K |
| Host RAM left with it loaded | about 32 to 33 GB |

Despite the `IQ1_M` folder name, shard 1 is roughly what you would expect for half the experts at about the same bit width as the IQ3_S file. The quality results bear that out.

## The shared shard

Shard 2 of both models is the same file (SHA-256 `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`). It holds the large per-layer lookup tables that Strata loads with `--ple-gguf`, and it is identical even between DavidAU's abliterated build and the Coder build. I downloaded it once and hard-linked it into the second model folder, saving 28.8 GB of disk:

```
ln /models/qwen38-flash-next-abliterated-iq3s/...IQ3_S-00002-of-00002.gguf \
   /models/qwen38-flash-next-coder-iq1m/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf
```

Both downloads are pinned to a commit and verified with `sha256sum -c` ([scripts/setup/04-download-models.sh](../scripts/setup/04-download-models.sh)).

## Disk use

```
/models  147G size, 111G used
  qwen38-flash-next-abliterated-iq3s   84.8 GB (incl. vision projector)
  qwen38-flash-next-coder-iq1m         29.6 GB (+ the hard-linked shard)
  strata-data/packs                    2.9 GB (two packs)
  strata-data/mtp                      0.9 GB (draft layer runtime)
```
