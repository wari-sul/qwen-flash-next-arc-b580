# 13. Troubleshooting

Every problem I actually hit, in the order I hit it.

| Symptom | Cause | Fix |
|---|---|---|
| Host freezes about a minute after starting a VM with the B580 passed through; journal ends with `AMD-Vi: Completion-Wait loop timed out` and `Unable to change power state from D3hot to D0` | VFIO reset of the Arc card stalls the IOMMU on this platform | Do not use VFIO for this card here. Share `/dev/dri` with an LXC and let the host keep the `xe` driver ([01](01-hardware-and-host.md)) |
| `clinfo` shows no devices in the container | Device nodes not passed in, or wrong group | `dev0: /dev/dri/renderD128,gid=<render gid>`; check `getent group render` inside the CT ([02](02-lxc-container.md)) |
| Engine fails allocating the expert mirror | memlock limit | `lxc.prlimit.memlock: unlimited` in the CT config and `LimitMEMLOCK=infinity` in the unit |
| Strata tools fail on the chat template | No UTF-8 locale | `locale-gen en_US.UTF-8`, `LANG=en_US.UTF-8` everywhere, including the unit |
| `strata launch` will not download or prepare the model on Arc | Its downloader only handles NVIDIA/AMD | Download the GGUF yourself, build the pack yourself, then `launch` writes the run config ([03](03-strata-install.md)) |
| `ArenaExpertSource: the pack's native_experts.txt does not match the model` | Pack built for a different GGUF build | Rebuild with `tools/iq_pack.py` and `tools/strata_tokenizer.py` against your shard 1 ([05](05-custom-packs.md)) |
| Server started with `systemd-run` exits by itself | Transient unit lifetime | Use a real unit file ([configs/systemd/](../configs/systemd/)) |
| `strata profile set` rejects `lazy_load` / `idle_unload_s` | Not exposed through `profile set` in 0.2.3 | Edit the JSON config directly |
| Container shows 2 GB used but the host is out of RAM | Pinned GPU host allocations are not charged to the CT cgroup | Watch host `MemAvailable`, never the CT's numbers ([02](02-lxc-container.md)) |
| Another container OOM-killed during a 512K test | Host pressure lands on the tightest cgroup elsewhere | Stay at 256K native on a 64 GB host with this model; check `journalctl -k` after memory-heavy tests ([08](08-context-scaling.md)) |
| Both models loaded at once would exceed RAM | Two independent servers | `before_load` hook that unloads the peer, with `before_load_strict` ([09](09-on-demand-loading.md)) |
| First request after a while is slow | Lazy load after idle unload | Expected: about a minute to load. Raise `idle_unload_s` if it bothers you |
| B580 shown as "untested" by Strata | B-series is new to Strata | Works for text with vision off in my testing |
| Benchmark grader marked correct answers wrong | My extractor picked a usage-example code block | Try every fenced block (fixed in `bench.py`, `regrade.py` re-grades stored answers) |

## Useful commands

```
# host: memory and GPU
grep MemAvailable /proc/meminfo
journalctl -k | grep -E "Memory cgroup out of memory|AMD-Vi|xe 0000"
cat /sys/class/drm/card0/device/hwmon/hwmon*/temp2_input            # GPU package, millidegrees
cat /sys/class/drm/card0/device/tile0/gt0/freq0/throttle/status      # 0 = not throttling

# container: Strata
systemctl status strata strata-coder
curl -s localhost:8080/health
grep -aE "expert cache|mirrored|VRAM free|KV streaming|hit rate" /var/log/strata-engine.log | tail
```

The engine log is the best source of truth. Per request it prints prompt tokens reused vs read, generation speed, draft acceptance, the VRAM expert-cache hit rate (about 47 to 61% in coding work here) and how much was read over PCIe.
