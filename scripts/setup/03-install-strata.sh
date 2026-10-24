#!/bin/bash
# Run inside the container. Installs Strata v0.2.3 from the signed release feed.
set -euo pipefail
export LANG=en_US.UTF-8
cd /root
F=https://github.com/Niko1221/Strata/releases/download/v0.2.3
curl -fsSL -o install.sh $F/install.sh
echo "73a3e0cbd8f2f00e1f26a304c1f8f498afdf9be3a4a9f58c83fa5ffdb6642780  install.sh" | sha256sum -c -
STRATA_FEED=$F sh install.sh
grep -q '.local/bin' /root/.profile || echo 'export PATH="$HOME/.local/bin:$PATH"' >> /root/.profile
export PATH=$HOME/.local/bin:$PATH
strata --version
