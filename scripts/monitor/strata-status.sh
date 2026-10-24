#!/bin/bash
# Run inside the container. What is loaded, and the engine's most recent placement and per-request stats.
for p in 8080 8081; do echo ":$p $(curl -s -m 3 localhost:$p/health)"; done
for L in /var/log/strata-engine.log /var/log/strata-coder-engine.log; do
  [ -f $L ] || continue
  echo "== $L"
  grep -aE "expert cache [0-9]+ slots|mirrored in pinned|VRAM free with|KV streaming: [0-9]+ of" $L | tail -4 | cut -c1-200
  grep -aE "serve: prompt|hit rate" $L | tail -4 | cut -c1-220
done
