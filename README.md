# Qwen3.8-Flash-Next on an Intel Arc B580 (12 GB) in a Proxmox LXC

Run an **84 GB mixture-of-experts model on a 12 GB GPU** at about 30 to 35 tokens per second with a **256K context**, inside an unprivileged Proxmox container, using [Strata](https://github.com/Niko1221/Strata). Plus a 103-item coding benchmark comparing two quantized builds of the model.

Companion blog post: *An 84 GB Model on a 12 GB GPU: Running Qwen3.8-Flash-Next on an Intel Arc B580 in Proxmox*.

## Results at a glance

| | ISTA-DASLab Coder IQ1_M | DavidAU IQ3_S (abliterated) |
|---|---|---|
| Benchmark, all 103 graded items | 96 (93%) | **100 (97%)** |
| Coding, structured spec / casual prompt | 45/48, 21/24 | 46/48, 23/24 |
| Hardest tasks at xhigh reasoning | 4/5 | 5/5 |
| Tool calling / agent repos | 16/16, 10/10 | 16/16, 10/10 |
| Generation speed (coding) | **34.2 tok/s** | 30.2 tok/s |
| 256K needle test (5 facts in 243K tokens) | 5/5 | 5/5 |
| Experts in VRAM | 1,896 of 12,288 (15%) | 1,742 of 24,576 (7%) |
| Pinned host RAM | ~23 GiB | ~47 GiB |
| Host RAM left (64 GB host) | ~31 GiB | ~8 GiB |

Verdict: DavidAU IQ3_S is the default, because it is more robust to casual prompts and to SQL/Bash work. The Coder build is the better choice if you need the RAM. Full analysis: [docs/12-results.md](docs/12-results.md).

Other measured results:

- **MTP speculative decoding:** 24.1 to 34.1 tok/s (1.41x) with 51/51 graded answers unchanged ([docs/07-mtp.md](docs/07-mtp.md))
- **Context:** 128K and 256K are stable, with all 5 needles found at both. 512K (YaRN) ran the host out of memory ([docs/08-context-scaling.md](docs/08-context-scaling.md))
- **Prompt cache:** a 3.4K-token prefix went from 6.0 s cold to 0.49 s warm ([docs/10-api-usage.md](docs/10-api-usage.md))
- **Thermals under hours of load:** GPU 65 to 70 C, about 110 W, no throttling ([docs/01-hardware-and-host.md](docs/01-hardware-and-host.md))

## The setup

```
Proxmox VE 9.2 host (Ryzen 7 5700X, 64 GB RAM, Arc B580 12 GB, xe driver stays on the host)
└── unprivileged LXC, Ubuntu 26.04, 8 cores, /dev/dri/renderD128 + card0 passed in, memlock unlimited
    ├── strata.service        :8080  DavidAU IQ3_S   256K ctx, MTP, lazy load, 20 min idle unload
    └── strata-coder.service  :8081  Coder IQ1_M     256K ctx, MTP, lazy load, 20 min idle unload
        (a before_load hook unloads the other model first, so only one is ever on the GPU)
```

How it fits: Strata keeps the dense weights and a cache of hot experts in VRAM, mirrors every other expert in pinned host RAM, and the GPU reads missing experts over PCIe. The KV cache for long contexts also lives in pinned RAM (`--kv-resident`), which leaves more VRAM for experts.

## Documentation

| | |
|---|---|
| [01. Hardware, host, and why GPU passthrough was dropped](docs/01-hardware-and-host.md) | The VFIO reset that froze the whole host, and thermals |
| [02. The LXC container](docs/02-lxc-container.md) | Sizing, `/dev/dri` passthrough, and the memory accounting trap |
| [03. Installing Strata on Arc](docs/03-strata-install.md) | What the installer does not do on Intel, and how to run it as a service |
| [04. The run config, flag by flag](docs/04-strata-config.md) | Every engine argument and server key explained |
| [05. Building the pack by hand](docs/05-custom-packs.md) | Fixing `native_experts.txt does not match the model` |
| [06. The two models](docs/06-models.md) | GSQ-RCO explained, file sizes, the shared shard |
| [07. MTP speculative decoding](docs/07-mtp.md) | Fetching the draft layer by hand, and an A/B quality test |
| [08. Context scaling 32K to 512K](docs/08-context-scaling.md) | Needle tests, memory math, and the OOM incident |
| [09. On-demand loading, two models one GPU](docs/09-on-demand-loading.md) | `lazy_load`, `idle_unload_s`, and the unload hook |
| [10. Using the API](docs/10-api-usage.md) | OpenAI Chat/Responses, Anthropic Messages, prompt caching |
| [11. Benchmark methodology](docs/11-benchmark-method.md) | 103 items, code-graded, with fairness checks |
| [12. Results](docs/12-results.md) | Every number and every failure explained |
| [13. Troubleshooting](docs/13-troubleshooting.md) | Every error hit, with its fix |
| [14. Lessons learned](docs/14-lessons-learned.md) | |

## Quick start

These steps assume a Proxmox host with an Arc card on the `xe` driver and at least 64 GB of RAM. Read [docs/02](docs/02-lxc-container.md) and [docs/08](docs/08-context-scaling.md) before you load anything: the model's pinned memory is not limited by the container.

```
# on the Proxmox host (edit CTID, storage names and GIDs first)
scripts/setup/01-create-ct.sh

# inside the container
scripts/setup/02-ct-gpu-runtime.sh     # Level Zero + OpenCL, check clinfo sees the B580
scripts/setup/03-install-strata.sh     # Strata 0.2.3
scripts/setup/04-download-models.sh    # ~114 GB, pinned revisions, sha256-checked
scripts/setup/05-build-packs.sh        # seconds
scripts/setup/06-mtp-draft.sh          # ~5.2 GB download, MTP draft layer
# put your API key into configs/strata/*.json, then:
scripts/setup/07-install-services.sh
```

Then:

```
curl http://<ct-ip>:8080/v1/chat/completions -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"model":"x","messages":[{"role":"user","content":"hello"}],"reasoning_effort":"low"}'
```

The first request loads the model, which takes about a minute.

## Repository layout

```
docs/          the write-ups above
configs/       proxmox CT config, Strata run configs (key removed), systemd units, unload hook
scripts/       setup/ (numbered, in order) and monitor/ (host RAM, GPU/CPU, Strata status)
benchmark/     codebench/ (the 103-item suite) and earlier/ (MTP, context, reasoning tests)
results/       codebench/ raw JSONL + summary, earlier-tests/ raw JSON
```

## Versions

Proxmox VE 9.2.21 (kernel 7.0.14), Ubuntu 26.04.1 in the container, Strata 0.2.3 (engine 0.1.48 SYCL), intel-opencl-icd / libze-intel-gpu1 26.05.37020.3, libze1 1.28.2, Node 22 and Python 3.14 for the benchmark.

## Credits

- [Strata](https://github.com/Niko1221/Strata) by Niko1221: the engine that makes this possible
- [ISTA-DASLab](https://huggingface.co/ISTA-DASLab): the GSQ-RCO quantizations and the expert-pruned Coder build
- [DavidAU](https://huggingface.co/DavidAU) and SC117: the abliterated IQ3_S build
- Qwen team: Qwen3.8-Flash-Next

## License

Code (`benchmark/`, `scripts/`, `configs/`) is MIT. Docs and results are CC BY 4.0. See [LICENSE](LICENSE). Model weights and Strata are under their own licenses and are not included.
