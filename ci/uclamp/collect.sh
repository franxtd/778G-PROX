#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
MODDIR=${0%/*}
OUT=/data/local/tmp/fran-uclamp-sample.txt
umask 077
{
 id
 cat /proc/version
 sh "$MODDIR/profile.sh" status
 i=0
 while [ "$i" -lt 30 ]; do
  date '+%H:%M:%S'
  for base in /dev/cpuctl /sys/fs/cgroup/cpu /sys/fs/cgroup; do
   if [ -r "$base/top-app/cpu.uclamp.min" ]; then
    for f in cpu.uclamp.min cpu.uclamp.max cpu.uclamp.latency_sensitive; do
     printf '%s=' "$f"; cat "$base/top-app/$f"
    done
    break
   fi
  done
  for cpu in 0 4 7; do
   p=/sys/devices/system/cpu/cpufreq/policy$cpu
   [ -d "$p" ] || continue
   printf 'policy%s ' "$cpu"
   for f in scaling_governor scaling_min_freq scaling_max_freq scaling_cur_freq; do
    printf '%s=%s ' "$f" "$(cat "$p/$f")"
   done
   printf '\n'
  done
  while IFS= read -r package || [ -n "$package" ]; do
   case "$package" in ''|'#'*|*[!a-zA-Z0-9_.]*) continue;; esac
   for pid in $(pidof "$package" 2>/dev/null); do
    printf '%s pid=%s\n' "$package" "$pid"
    cat "/proc/$pid/cgroup"
    grep -E '^(effective )?uclamp\.' "/proc/$pid/sched" || :
   done
  done < "$MODDIR/packages.list"
  if [ -r /sys/class/kgsl/kgsl-3d0/gpuclk ]; then
   printf 'gpuclk='; cat /sys/class/kgsl/kgsl-3d0/gpuclk
  fi
  sleep 1
  i=$((i+1))
 done
 printf '\nService log:\n'
 tail -n 40 "$MODDIR/profile.log"
 printf '\nThermal snapshots (type then temperature):\n'
 for zone in /sys/class/thermal/thermal_zone*; do
  [ -r "$zone/type" ] && [ -r "$zone/temp" ] || continue
  printf '%s ' "${zone##*/}"; cat "$zone/type" "$zone/temp"
 done
} > "$OUT" 2>&1
printf 'Captured: %s\n' "$OUT"
