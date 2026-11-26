#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:-"$root/out"}
${CC:-clang} --target=aarch64-linux-gnu -O2 -std=gnu11 -Wall -Wextra -Werror \
  -fno-builtin -fno-stack-protector -fno-pie -Wl,-no-pie -nostdlib -static \
  -nostdinc -isystem "$out/usr/include" -fuse-ld=lld -Wl,-e,_start \
  "$root/ci/performance/probe.c" -o "$out/performance-probe"
${CC:-clang} --target=armv7a-linux-gnueabi -marm -mfloat-abi=soft -O2 \
  -std=gnu11 -Wall -Wextra -Werror -fomit-frame-pointer -fno-builtin \
  -fno-stack-protector -fno-pie -Wl,-no-pie -nostdlib -static \
  -fuse-ld=lld -Wl,-e,_start \
  "$root/ci/performance/compat-probe.c" -o "$out/compat-probe"
