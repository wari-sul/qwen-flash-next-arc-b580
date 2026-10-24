#!/bin/bash
# Run inside the container. Downloads both models at pinned revisions and verifies SHA-256.
# Shard 2 is byte-identical in both repos: it is downloaded once and hard-linked.
set -u
dl() {  # dl <url> <file>
  for try in 1 2 3 4 5; do curl -fL --retry 5 --retry-delay 10 -C - -o "$2" "$1" && return 0; echo "retry $try for $2"; sleep 20; done; return 1
}

# --- Model A: DavidAU IQ3_S abliterated
R=DavidAU/Qwen3.8-Flash-Next-Abliterated-Uncensored-Turbo-Brilliance-50x-Reasoning-Instruct-GSQ-RCO-GGUF
REV=b1b82c36770c826c41e1874f250228048cdb3f5c
A=/models/qwen38-flash-next-abliterated-iq3s; mkdir -p $A; cd $A
S1=Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_S-00001-of-00002.gguf
S2=Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_S-00002-of-00002.gguf
dl "https://huggingface.co/$R/resolve/$REV/$S1" $S1
dl "https://huggingface.co/$R/resolve/$REV/$S2" $S2
cat > SHA256SUMS <<SUMS
78706315c2fe912777c006b4ae18be1024c9f4353bd25d33b8a306c9c55f9e34  $S1
316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113  $S2
SUMS
sha256sum -c SHA256SUMS

# --- Model B: ISTA-DASLab Coder IQ1_M
REV=bba88856f8c3c0c9e40e45f82d05e228b814ac43
B=/models/qwen38-flash-next-coder-iq1m; mkdir -p $B; cd $B
F=Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf
cat > SHA256SUMS <<SUMS
bfa3644db4adfff072fc946c20994f2909d2cf89879d83f80a4c811d4016c211  Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf
316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113  Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf
SUMS
[ -e Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf ] || ln $A/$S2 Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf
dl "https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF/resolve/$REV/IQ1_M/$F" $F
sha256sum -c SHA256SUMS
