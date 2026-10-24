# 02. The LXC container

## Sizing

| Setting | Value | Why |
|---|---|---|
| OS | Ubuntu 26.04 LTS (Proxmox template `ubuntu-26.04-standard_26.04-1_amd64.tar.zst`) | Recent Mesa/Level Zero packages in the distro repo |
| Type | Unprivileged, `nesting=1` | No need for a privileged container to use `/dev/dri` |
| Cores | 8 | Strata uses about 5 cores during decode |
| Memory limit | 52 GiB, swap 0 | See the warning below: this limit does not cover the pinned expert memory |
| Root disk | 32 GB on an NVMe thin pool | OS, Strata, Python, logs |
| Model disk | 150 GB mount point at `/models` on a second NVMe thin pool, `backup=0` | Two models plus packs use 111 GB |
| Network | Bridge, DHCP with a router reservation | Static address without editing the container |
| Start at boot | Yes | Safe because Strata loads the model on demand (see [09](09-on-demand-loading.md)) |

The full config is in [configs/proxmox/ct-strata.conf](../configs/proxmox/ct-strata.conf).

## GPU access

Two device nodes are passed in, with the group IDs the container expects:

```
dev0: /dev/dri/renderD128,gid=991
dev1: /dev/dri/card0,gid=44
lxc.prlimit.memlock: unlimited
```

- `renderD128` is what compute APIs (Level Zero, OpenCL) open. GID 991 is the `render` group inside the Ubuntu 26.04 container.
- `card0` is optional for compute but some tools probe it. GID 44 is `video`.
- Check the GIDs in your own container with `getent group render video` before copying these numbers.
- `lxc.prlimit.memlock: unlimited` is required. Strata pins (page-locks) tens of GB of host memory so the GPU can read experts over PCIe with DMA. With the default memlock limit the engine fails to allocate its expert mirror.

The systemd units also set `LimitMEMLOCK=infinity`, because systemd applies its own limit to services.

## The memory warning you must read

The pinned expert memory is allocated through the GPU driver (SYCL / Level Zero host allocations). On this setup it is **not charged to the container's memory cgroup**.

With the 84 GB model loaded:

- Inside the container, `free` and the cgroup counters show about 2 GB used.
- On the host, `MemAvailable` drops by about 47 GB and the memory shows up as locked.

The container's `memory: 53248` limit therefore does not cap the model. The only number that tells the truth is the host's `MemAvailable`. I learned this the hard way when a 512K context test pushed the host to about 4.5 GB available and the kernel killed processes in a *different* container (details in [08-context-scaling.md](08-context-scaling.md)).

Watch it with:

```
watch -n 5 "grep MemAvailable /proc/meminfo"          # on the host
journalctl -k | grep "Memory cgroup out of memory"     # after any memory-heavy test
```

[scripts/monitor/memlog.sh](../scripts/monitor/memlog.sh) logs it every 30 seconds.

## Verifying the GPU inside the container

```
apt-get install -y intel-opencl-icd libze1 libze-intel-gpu1 clinfo
clinfo -l
# Platform #0: Intel(R) OpenCL Graphics
#  `-- Device #0: Intel(R) Arc(TM) B580 Graphics
```

Versions that worked here (Ubuntu 26.04 repo): `intel-opencl-icd 26.05.37020.3`, `libze-intel-gpu1 26.05.37020.3`, `libze1 1.28.2`.

Full steps: [scripts/setup/02-ct-gpu-runtime.sh](../scripts/setup/02-ct-gpu-runtime.sh).
