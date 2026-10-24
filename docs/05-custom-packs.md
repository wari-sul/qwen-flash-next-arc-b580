# 05. Building the Strata pack by hand

## The error

The first start with the DavidAU GGUF failed with:

```
ArenaExpertSource: the pack's native_experts.txt does not match the model
```

A Strata "pack" is a folder that describes the model to the engine: a `dense.bin` with the non-expert tensors, an `index.txt` mapping every tensor to its location, `native_experts.txt` listing the expert tensors read straight from the GGUF, and a `tokenizer/` folder. Strata's catalogued packs match specific upstream files. DavidAU's file is a different build of the same quant (it ships a much larger chat template, about 222K characters, among other changes), so offsets in a stock pack do not line up.

On NVIDIA and AMD the installer would build the pack for you. On Intel it refuses: "the prepared pack ... is missing (this installer cannot prepare it for this graphics card)". The tools it would have run are in the install, though.

## The fix

Run Strata's own pack tools with its bundled Python against shard 1:

```
T=~/.local/share/strata/terminal/0.1.48
PY=$T/python/bin/python3.12
G=/models/qwen38-flash-next-abliterated-iq3s/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_S-00001-of-00002.gguf
P=/models/strata-data/packs/iq3_s
cd $T
$PY tools/iq_pack.py        --gguf $G --out $P
$PY tools/strata_tokenizer.py --gguf $G --out $P
```

Output:

```
tokenizer/: vocab 248320, merges 247587, pre qwen35, specials {eos 248046, padding 248044, bos 248044}
model shards: ...-00001-of-00002.gguf, ...-00002-of-00002.gguf
index.txt: 1079 tensors, 302 served natively, 0 in extra.bin, arena 1.43 GiB
real 0m2.691s
```

It takes seconds, because it only writes the dense tensors (about 1.5 GB) and an index. The experts stay in the GGUF and are read in place.

Resulting pack:

```
conversions.json       330 B
dense.bin              1.5 GB
index.txt              94 KB
native_experts.txt     3.3 KB
tokenizer/             chat_template.jinja, merges.txt, token_type.json, tokenizer.json, vocab.json
```

The Coder pack is built the same way ([scripts/setup/05-build-packs.sh](../scripts/setup/05-build-packs.sh)) and comes out at 1.4 GB.

## When you need to rebuild

Rebuild the pack whenever the GGUF changes: a new upload of the same repo, a different quant, a re-split. The pack records shard names and sizes in `conversions.json`, so a mismatch is easy to spot.
