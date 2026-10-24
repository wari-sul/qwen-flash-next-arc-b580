#!/bin/bash
# Run on the Proxmox host. Creates the Strata container. Adjust CTID, storage names and GIDs first.
set -euo pipefail
CTID=${CTID:-200}
ROOT_STORE=${ROOT_STORE:-local-nvme}       # thin pool for the 32G root disk
MODEL_STORE=${MODEL_STORE:-models-nvme}    # thin pool for the 150G /models disk
TEMPLATE=${TEMPLATE:-local:vztmpl/ubuntu-26.04-standard_26.04-1_amd64.tar.zst}

pveam update && pveam download local ubuntu-26.04-standard_26.04-1_amd64.tar.zst || true

pct create "$CTID" "$TEMPLATE" \
  --hostname strata-arc --ostype ubuntu --unprivileged 1 --features nesting=1 \
  --cores 8 --memory 53248 --swap 0 \
  --rootfs "$ROOT_STORE:32" \
  --mp0 "$MODEL_STORE:150,mp=/models,backup=0" \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --onboot 1

# GPU device nodes (check the gids inside the CT with: getent group render video)
pct set "$CTID" --dev0 /dev/dri/renderD128,gid=991 --dev1 /dev/dri/card0,gid=44
echo "lxc.prlimit.memlock: unlimited" >> /etc/pve/lxc/$CTID.conf

pct start "$CTID"
pct exec "$CTID" -- ls -la /dev/dri
