#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Resource isolation for disposable Ubuntu Actions runners, never the phone.
set -euo pipefail
if [ "${GITHUB_ACTIONS:-}" != true ]; then
  echo 'This wrapper requires an Actions runner with systemd and cgroup v2.' >&2
  exit 2
fi
test "$#" -gt 0
test -f /sys/fs/cgroup/cgroup.controllers
grep -qw memory /sys/fs/cgroup/cgroup.controllers
build_user=$(id -un)
unit="fran-build-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-$$"
build_env=("PATH=$PATH")
for key in ARCH SUBARCH KBUILD_BUILD_USER KBUILD_BUILD_HOST CCACHE_DIR CCACHE_BASEDIR CCACHE_COMPILERCHECK CCACHE_MAXSIZE; do
  if [ "${!key+x}" ]; then build_env+=("$key=${!key}"); fi
done
free -h
set +e
sudo systemd-run --scope --collect --expand-environment=no --unit="$unit" \
  --property=MemoryHigh=75% --property=MemoryMax=85% \
  --property=MemorySwapMax=18G --property=CPUWeight=25 --property=IOWeight=25 \
  runuser --user "$build_user" -- env "${build_env[@]}" "$@"
result=$?
set -e
free -h
df -h .
exit "$result"
