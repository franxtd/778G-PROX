#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:-"$root/out"}
python3 - "$root" "$out" <<'PY'
from pathlib import Path
import sys
root,out=map(Path,sys.argv[1:])
s=(root/'ci/fas/feature-probe.c').read_text()
assert s.count('int result=test();')==1
s=s.replace('void start_c(unsigned long *sp)',(root/'ci/uclamp/uclamp-probe.inc').read_text()+'\nvoid start_c(unsigned long *sp)')
s=s.replace('int result=test();','int result=test(); if (!result) result=test_uclamp();')
(out/'uclamp-feature-probe.c').write_text(s)
PY
${CC:-clang} --target=aarch64-linux-gnu -O2 -std=gnu11 -Wall -Wextra -Werror \
 -fno-builtin -fno-stack-protector -fno-pie -Wl,-no-pie -nostdlib -static \
 -nostdinc -isystem "$out/usr/include" -fuse-ld=lld -Wl,-e,_start \
 "$out/uclamp-feature-probe.c" -o "$out/uclamp-feature-probe"
