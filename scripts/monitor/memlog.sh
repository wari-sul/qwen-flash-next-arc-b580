#!/bin/bash
# Run on the Proxmox HOST. Logs host MemAvailable (kB) every 30 s.
# This is the number that matters: Strata's pinned expert memory does not show up in the container's cgroup.
# usage: nohup ./memlog.sh /root/memlog.txt &
OUT=${1:-/root/memlog.txt}
while true; do
  echo "$(date +%T) $(awk '/MemAvailable/{print $2}' /proc/meminfo)" >> "$OUT"
  sleep 30
done
