# 01. Hardware, host, and why GPU passthrough was dropped

## The machine

| Part | Details |
|---|---|
| CPU | AMD Ryzen 7 5700X, 8 cores / 16 threads |
| RAM | 64 GB DDR4 (62 GiB visible to the OS) |
| GPU | Intel Arc B580, 12 GB GDDR6 (Battlemage G21, PCI ID `8086:e20b`) |
| Hypervisor | Proxmox VE 9.2.21, kernel `7.0.14-20-pve` |
| Storage | NVMe thin pools for container root disks and model files, one HDD pool for bulk data |
| Role | General homelab host: several other LXC containers (DNS, an S3 server, a Coolify instance, an AI agent) run next to the model |

The last row matters. This is not a dedicated inference box. Every memory decision in this repo is shaped by the fact that other containers have to keep running while an 84 GB model is loaded.

## The GPU stays with the host

The host's `xe` kernel driver owns the B580 permanently:

```
$ lspci -nnk -s <gpu-bdf>
VGA compatible controller [0300]: Intel Corporation Battlemage G21 [Arc B580] [8086:e20b]
        Kernel driver in use: xe
        Kernel modules: xe
```

The container gets the card through `/dev/dri` (see [02-lxc-container.md](02-lxc-container.md)). Nothing ever unbinds or resets it.

## What went wrong first: VFIO passthrough to a VM

My first plan was the usual one: a Ubuntu VM with the B580 passed through with VFIO (the GPU function and its audio function, `hostpci0` and `hostpci1`).

It worked once, and that run is the misleading part. The VM booted, the guest saw the card with the `xe` driver, and `/dev/dri/renderD128` appeared. Earlier starts had already shown warnings (one start ended with "unexpected status"), but the host survived them.

The start that went wrong took the whole host down:

1. `qm start` triggered a VFIO reset of the B580.
2. The AMD IOMMU stalled (`AMD-Vi: Completion-Wait loop timed out`).
3. About a minute later the kernel logged that the GPU's PCIe root port was unreachable:
   `pcieport <port-bdf>: Unable to change power state from D3hot to D0, device inaccessible`
4. Host services (`pvestatd`, the firewall) stalled for tens of seconds.
5. The journal ended with no shutdown lines. The host needed a hard reset, and every container went down with it.

The host also logged a machine check entry on the next boot. A later boot logged "uncorrected error caused a data fabric sync flood event". I have not proven that these came from the GPU reset, but I am not willing to find out the hard way a second time.

### Why this happens (as far as I can tell)

The Arc cards are known to be awkward with VFIO resets. On this board, the reset path that runs at VM start leaves the card (and its upstream port) in a state the IOMMU cannot recover from. Because the host's `xe` driver claims the card on every boot, every VM start has to unbind it and reset it, so every start rolls the dice again.

There are BIOS and kernel workarounds people try (binding `vfio-pci` at boot so the host never touches the card, ACS overrides, disabling ASPM, different reset methods). Each attempt risks another full host freeze, and this host runs other services. I stopped there.

### The decision

I deleted the VM, its cloud-init template, and all passthrough configuration, and moved to an unprivileged LXC container that shares the GPU through `/dev/dri`. The host keeps the driver and the card is never reset. It has been stable through days of sustained full load since then.

Trade-off: the card is shared with the host instead of exclusive to a guest. For a single inference service that is fine.

## Thermal and power under sustained load

Measured on the host from the `xe` hwmon interface (`/sys/class/drm/card0/device/hwmon/hwmon*/`) after 45 minutes to 2.5 hours of continuous benchmark load:

| Reading | Value |
|---|---|
| GPU package | 65 to 70 C (critical limit 100 C) |
| VRAM | 64 to 70 C (critical limit 105 C) |
| Fans | two fans at 1,390 to 1,525 RPM (the third fan channel reads 0, nothing connected) |
| Card power | about 108 to 111 W |
| GPU clock | 2,850 MHz, no throttle reasons set |
| CPU (Tctl / CCD) | 65 to 67 C / 59 to 65 C |
| Host CPU busy | about 33% of 16 threads (the Strata process uses about 4.7 to 5.2 cores) |
| GPU idle | about 34 C |

The script that reads these is [scripts/monitor/hw-snapshot.sh](../scripts/monitor/hw-snapshot.sh).
