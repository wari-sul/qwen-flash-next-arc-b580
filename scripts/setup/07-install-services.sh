#!/bin/bash
# Run inside the container from the repo root. Installs configs, the unload hook and both systemd units.
# Put your API key into both configs first (or generate one: python3 -c "import secrets;print('sk-strata-'+secrets.token_urlsafe(32))").
set -euo pipefail
install -d -m 700 /etc/strata
install -m 600 configs/strata/davidau-iq3s-256k.json configs/strata/coder-iq1m-256k.json /etc/strata/
grep -q '<API_KEY>' /etc/strata/*.json && { echo "replace <API_KEY> in /etc/strata/*.json first"; exit 1; }
install -m 755 configs/bin/strata-unload-peer /usr/local/bin/strata-unload-peer
install -m 644 configs/systemd/strata.service configs/systemd/strata-coder.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now strata strata-coder
sleep 3
for p in 8080 8081; do echo ":$p $(curl -s localhost:$p/health)"; done
