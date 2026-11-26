#!/system/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Limit compressed-swap readahead without changing zRAM capacity or algorithm.
MODDIR=${0%/*}
STATE=/dev/.franbakasu-ram
KNOB=/proc/sys/vm/page-cluster
say() { echo "FranBakaSU RAM: $*"; }
case "${1:-apply}" in
 apply)
  [ ! -f "$MODDIR/disable-ram-profile" ] || { say disabled; exit 0; }
  [ -r /proc/swaps ] && [ -w "$KNOB" ] || { say 'swap/knob unavailable'; exit 0; }
  count=0
  while read -r device type size used priority; do
   [ "$device" != Filename ] || continue
   [ -n "$device" ] || continue
   case "$device" in
    /dev/block/zram[0-9]*|/dev/zram[0-9]*) count=$((count+1));;
    *) say 'physical or unknown swap present; unchanged'; exit 0;;
   esac
  done < /proc/swaps
  [ "$count" -gt 0 ] || { say 'no active zRAM; unchanged'; exit 0; }
  [ ! -d "$STATE" ] || { say 'already applied this boot'; exit 0; }
  old=$(cat "$KNOB") || exit 1
  case "$old" in ''|*[!0-9]*) say 'invalid original value'; exit 1;; esac
  [ "$old" != 0 ] || { say 'page-cluster already 0'; exit 0; }
  umask 077
  mkdir "$STATE" || exit 1
  printf '%s\n' "$old" > "$STATE/page-cluster" || { rmdir "$STATE"; exit 1; }
  if printf '0\n' > "$KNOB"; then
   say "page-cluster $old -> 0 (zRAM only)"
  else
   rm -f "$STATE/page-cluster"; rmdir "$STATE"; exit 1
  fi
  ;;
 restore)
  [ -f "$STATE/page-cluster" ] || { say 'nothing to restore'; exit 0; }
  old=$(cat "$STATE/page-cluster") || exit 1
  case "$old" in ''|*[!0-9]*) say 'invalid saved value'; exit 1;; esac
  current=$(cat "$KNOB") || exit 1
  if [ "$current" = 0 ]; then
   printf '%s\n' "$old" > "$KNOB" || exit 1
   say "page-cluster restored to $old"
  else
   say 'value changed by another service; retained'
  fi
  rm -f "$STATE/page-cluster"; rmdir "$STATE"
  ;;
 *) say 'usage: ram-profile.sh [apply|restore]'; exit 2;;
esac
