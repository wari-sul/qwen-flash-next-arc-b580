#!/bin/bash
# Run inside the container. Fetches the MTP draft layer from the original BF16 checkpoint (only its 31 tensors, ~5.2 GB),
# verifies it, quantizes its experts to Q2_0 and builds the runtime folder, the same steps Strata's setup runs elsewhere.
set -eu
export LANG=en_US.UTF-8
T=/root/.local/share/strata/terminal/0.1.48; PY=$T/python/bin/python3.12; cd $T
C=$(grep -oP '^LLAMA_CPP_COMMIT\s*=\s*"\K[0-9a-f]+' setup.py)     # the llama.cpp revision Strata pins
mkdir -p /root/third_party; cd /root/third_party
[ -d llama.cpp-$C/gguf-py ] || { curl -fsSL -o l.zip https://github.com/ggml-org/llama.cpp/archive/$C.zip; python3 -c "import zipfile;zipfile.ZipFile('l.zip').extractall('.')"; rm l.zip; }
export STRATA_GGUF_PY=/root/third_party/llama.cpp-$C/gguf-py STRATA_SOURCE=huggingface
cd $T
M=/models/strata-data/mtp
for n in 1 2 3; do $PY tools/mtp_fetch.py fetch --out $M && break; sleep 5; done
$PY tools/mtp_fetch.py verify --out $M
$PY tools/mtp_pack.py --src $M --experts q2_0 --out $M/mtp-q2_0.gguf
$PY tools/mtp_rt.py --gguf $M/mtp-q2_0.gguf --out $M/rt
cp $T/data/draft_vocab_en.bin $M/rt/draft_vocab.bin             # English/code draft vocabulary
ls -la $M/rt; du -sh $M
# Optional: the raw BF16 tensors are no longer needed once rt/ exists (about 4.9 GB)
