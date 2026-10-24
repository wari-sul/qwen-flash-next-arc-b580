# 08. Context scaling: 32K to 512K

Goal: find the largest context that is stable and usable on this host. I started at 32K, then doubled: 128K, 256K, 512K.

## Method

For each size:

1. Set `--max-context`, keep `--kv-resident 32768` (only 32K KV cells per layer in VRAM, the rest streamed from pinned RAM), `--vram-reserve-mib 2048`, `--prefill 4096`.
2. Restart, load, record what the engine places where and how much host RAM is left.
3. **Needle test:** fill about 92% of the window with filler text containing 5 hidden facts (a code word and a 6-digit number each) at different depths, then ask for all 5.
4. Re-run the 17-task graded suite (2 runs) to catch any quality change.

Scripts: [benchmark/earlier/ctxtest.py](../benchmark/earlier/ctxtest.py), [benchmark/earlier/run-ctx.sh](../benchmark/earlier/run-ctx.sh).

## Results (DavidAU IQ3_S, MTP on)

| | 32K | 128K | 256K (native max) | 512K (YaRN x2) |
|---|---|---|---|---|
| Experts in VRAM | 1,426 | 1,856 | 1,742 | 1,509 |
| Pinned RAM (experts + KV) | 44.1 GiB | 43.6 + 1.55 GiB | 43.8 + 3.09 GiB | 44.2 + 6.19 GiB |
| VRAM free when loaded | 2,288 MiB | 2,222 MiB | 2,221 MiB | 2,219 MiB |
| Host RAM available when loaded | ~11.9 GB | ~9.8 GB | ~7.4 GB | ~4.5 GB |
| Needle prompt | n/a | 121,165 tok (92%) | 243,050 tok (93%) | 487,230 tok, stopped at 50% |
| Needles found | n/a | 5/5 | 5/5 | not reached |
| Prompt processing | n/a | 654 tok/s (3.1 min) | 546 tok/s (7.4 min) | ~530 tok/s |
| Generation after the long prompt | n/a | 35.6 tok/s | 33.2 tok/s | not reached |
| Graded suite | 51/51, 34.1 tok/s | 33/34*, 35.7 tok/s | 34/34, 34.7 tok/s | not run |

\* The one miss at 128K was my grader's fault: the model correctly said a paper title "appears to be fabricated" and my regex expected different words.

The Coder model at 256K: 5/5 needles at 243,050 tokens, 647 tok/s prompt processing (6.3 min), 39.0 tok/s generation afterwards.

Why does 128K/256K have *more* experts in VRAM than 32K? Because the 32K config kept the whole KV cache in VRAM. With `--kv-resident 32768` the KV lives in pinned RAM and streams in, and the freed VRAM goes to expert slots.

## What happened at 512K

512K is past the native window, so it needs YaRN rope scaling (`--rope-scaling yarn --rope-scale 2`). The engine accepted it, but filling the pinned memory took 41 s instead of 13 s and left the host with about 4.5 GB available.

That was not enough. The kernel started pushing other containers into swap. My Coolify container, with its own 6 GB limit, 512 MB of swap already full and about 3.8 GB of shared memory it could not drop, hit its limit, and its OOM killer ended dockerd, containerd, postgres, redis, php-fpm and traefik. The container stopped itself. My watchdog did not trip because it only fired below 2.5 GB host-wide.

I stopped the test, restarted the container (all its services came back healthy) and checked the kernel log: it was the only OOM event in the previous 14 days.

Lessons:

- The pinned memory is invisible to the model container's cgroup ([02](02-lxc-container.md)), so the pressure lands on *other* containers.
- A host-wide "available RAM" threshold is not a sufficient guard. Also check `journalctl -k | grep "Memory cgroup out of memory"` and `pct list` after every memory-heavy step.
- 384K would have left only about 1.4 GB more than the failed run. Lower-precision KV (`--kv q4_0`) would roughly halve the KV cost and might make it fit, but YaRN also changes behaviour on every request, short ones included. I did not need more than 256K, so I stopped.

## Decision

**256K native** (`--max-context 262144`) is the daily setting. It passed every test, needs no rope scaling, and leaves about 7.4 to 8.7 GB for the rest of the host with the larger model loaded. Raw data: [results/earlier-tests/context/](../results/earlier-tests/context/).
