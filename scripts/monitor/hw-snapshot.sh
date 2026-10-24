#!/bin/bash
# Run on the Proxmox HOST. One snapshot of GPU (xe hwmon) and CPU state, sampled over ~9 s.
# Assumes the B580 is card0; adjust H if not.
H=$(ls -d /sys/class/drm/card0/device/hwmon/hwmon* | head -1)
F=/sys/class/drm/card0/device/tile0/gt0/freq0
date +%T
e1=$(cat $H/energy1_input); read -r _ a1 b1 c1 d1 i1 f1 g1 h1 _ < /proc/stat
for i in 1 2 3; do
  echo "gpu pkg=$(($(cat $H/temp2_input)/1000))C vram=$(($(cat $H/temp3_input)/1000))C fan1=$(cat $H/fan1_input) fan2=$(cat $H/fan2_input) freq=$(cat $F/act_freq)MHz"
  sleep 3
done
e2=$(cat $H/energy1_input); read -r _ a2 b2 c2 d2 i2 f2 g2 h2 _ < /proc/stat
echo "gpu card power ~$(( (e2-e1)/9000000 )) W   throttle_status=$(cat $F/throttle/status)"
for r in $F/throttle/reason_*; do [ "$(cat $r)" != 0 ] && echo "  throttle reason: $(basename $r)"; done
busy=$(( (a2+b2+c2+f2+g2+h2)-(a1+b1+c1+f1+g1+h1) )); idle=$(( (d2+i2)-(d1+i1) ))
echo "host cpu busy=$(( 100*busy/(busy+idle) ))%   load: $(cut -d' ' -f1-3 /proc/loadavg)"
for z in /sys/class/hwmon/hwmon*; do
  case $(cat $z/name) in k10temp|coretemp)
    for t in $z/temp*_input; do l=${t%_input}_label; echo "cpu $( [ -e $l ] && cat $l )=$(($(cat $t)/1000))C"; done;;
  esac
done
echo "host MemAvailable: $(awk '/MemAvailable/{printf "%.1f GB", $2/1048576}' /proc/meminfo)"
