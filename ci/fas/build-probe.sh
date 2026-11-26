#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:-"$root/out"}
${CC:-clang} --target=aarch64-linux-gnu -O2 -std=gnu11 -Wall -Wextra -Werror \
  -fno-builtin -fno-stack-protector -fno-pie -Wl,-no-pie -nostdlib -static \
  -nostdinc -isystem "$out/usr/include" -fuse-ld=lld -Wl,-e,_start \
  "$root/ci/fas/feature-probe.c" -o "$out/fas-feature-probe"
