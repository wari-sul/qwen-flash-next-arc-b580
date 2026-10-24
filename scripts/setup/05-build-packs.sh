#!/bin/bash
# Run inside the container. Builds the Strata packs (dense tensors + index + tokenizer) for both GGUFs.
# Needed on Intel Arc: the installer will not prepare packs for this card, and the DavidAU file does not match a stock pack.
set -euo pipefail
export LANG=en_US.UTF-8
T=/root/.local/share/strata/terminal/0.1.48; PY=$T/python/bin/python3.12; cd $T
build() {  # build <shard1.gguf> <pack dir>
  $PY tools/iq_pack.py --gguf "$1" --out "$2"
  $PY tools/strata_tokenizer.py --gguf "$1" --out "$2"
  ls -la "$2"; du -sh "$2"
}
mkdir -p /models/strata-data/packs
build /models/qwen38-flash-next-abliterated-iq3s/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_S-00001-of-00002.gguf /models/strata-data/packs/iq3_s
build /models/qwen38-flash-next-coder-iq1m/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf /models/strata-data/packs/coder-iq1m
