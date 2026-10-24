#!/bin/bash
# Run inside the container. Installs the Intel compute runtime (Level Zero + OpenCL) from the Ubuntu 26.04 repo.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y intel-opencl-icd libze1 libze-intel-gpu1 clinfo curl python3 locales
locale-gen en_US.UTF-8 && update-locale LANG=en_US.UTF-8
clinfo -l
# Expected:
# Platform #0: Intel(R) OpenCL Graphics
#  `-- Device #0: Intel(R) Arc(TM) B580 Graphics
