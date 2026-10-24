# 03. Installing Strata on an Intel Arc card

[Strata](https://github.com/Niko1221/Strata) is an inference engine built for exactly this problem: running Qwen3.8-Flash-Next, a very large mixture-of-experts (MoE) model, on a consumer GPU that holds only a small fraction of its weights. It keeps the dense parts and a cache of hot experts in VRAM, mirrors the rest of the experts in pinned host RAM, and lets the GPU read missing experts over PCIe.

Version used here: **Strata 0.2.3** (terminal build 0.1.48, engine `0.1.48-linux-x86_64-sycl`). The 0.2.3.1 point release only fixed a Windows/Linux NVIDIA setup crash, so nothing here changes with it.

## Install

```
apt-get install -y locales && locale-gen en_US.UTF-8 && update-locale LANG=en_US.UTF-8
export LANG=en_US.UTF-8
F=https://github.com/Niko1221/Strata/releases/download/v0.2.3
curl -fsSL -o install.sh $F/install.sh
echo "73a3e0cbd8f2f00e1f26a304c1f8f498afdf9be3a4a9f58c83fa5ffdb6642780  install.sh" | sha256sum -c -
STRATA_FEED=$F sh install.sh
export PATH=$HOME/.local/bin:$PATH
strata --version
# strata 0.2.3 (build 0.1.48; python 3.12.15 at ~/.local/share/strata/terminal/0.1.48/python/bin/python3.12)
```

Script: [scripts/setup/03-install-strata.sh](../scripts/setup/03-install-strata.sh).

Strata needs a UTF-8 locale. Without `LANG=en_US.UTF-8` some of its tools fail on non-ASCII text in the chat template.

## What does not work out of the box on Arc

Two things surprised me:

1. **`strata launch` does not download or prepare models for Intel cards.** Its built-in downloader handles NVIDIA and AMD only and says so: "The downloader built into this Terminal sets up NVIDIA and AMD cards only (Intel Arc cards have a separate installer)". It will, however, write a run config from model files and a pack that are already on disk.
2. **The B580 is flagged as untested.** On launch Strata warns: "The Arc B580 is a B-series Arc card. It is new to Strata and we have not tested it ourselves, so pictures or long answers may fail on it." In my testing long answers (12K+ tokens) and 256K contexts worked. I ran with vision off throughout.

So the workflow on Arc is: download the GGUF yourself, build the pack yourself ([05-custom-packs.md](05-custom-packs.md)), then let `strata launch` write the run config once, and run it under systemd from then on.

## First launch (writes the run config)

```
strata launch \
  --model-path /models/qwen38-flash-next-abliterated-iq3s \
  --data-dir /models/strata-data \
  --model iq3_s --context 32k --vision off --tune skip \
  --access lan --port 8080 \
  --set vram-reserve-mib=1536 --mtp off \
  --save-preset davidau-iq3s-32k --no-tui --yes
```

- `--access lan` makes Strata create an API key, because the server is reachable beyond localhost. Show it with `strata launch --show-key --preset <name>`.
- The saved preset ends up under `~/.local/state/strata/launch/`. I copied it to `/etc/strata/` and edited it from there (next section).

## Running it as a service

`strata launch` is an interactive supervisor. For a server I use `strata serve` with the run config as a profile:

```
ExecStart=/root/.local/bin/strata serve --profile /etc/strata/davidau-iq3s-256k.json --host 0.0.0.0 --port 8080
LimitMEMLOCK=infinity
Environment=LANG=en_US.UTF-8
```

Full units: [configs/systemd/](../configs/systemd/). A transient `systemd-run` unit did not work: the server exited when the transient unit's parent went away. Dedicated unit files fixed that.

`strata profile set` refused the keys I needed (`lazy_load`, `idle_unload_s`), so I edit the JSON directly. The annotated configs are in [configs/strata/](../configs/strata/) and explained in [04-strata-config.md](04-strata-config.md).
