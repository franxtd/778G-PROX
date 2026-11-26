#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
# Game-scoped hints for the CPU cgroup selected by Android task profiles.
MODDIR=${0%/*}
STATE=/dev/.fran-uclamp-profile
log() { printf 'FranUClamp: %s\n' "$*"; }

percent_units() {
 v=$1
 [ "$v" != max ] || { units=10000; return 0; }
 case "$v" in *.*) whole=${v%%.*}; fraction=${v#*.};; *) whole=$v; fraction=0;; esac
 case "$whole" in ''|*[!0-9]*) return 1;; esac
 case "$fraction" in ''|*[!0-9]*|???) return 1;; esac
 [ "${#whole}" -le 3 ] && [ "${#fraction}" -le 2 ] || return 1
 [ "${#fraction}" -ne 1 ] || fraction=${fraction}0
 while [ "${whole#0}" != "$whole" ]; do whole=${whole#0}; done
 while [ "${fraction#0}" != "$fraction" ]; do fraction=${fraction#0}; done
 units=$((${whole:-0} * 100 + ${fraction:-0}))
 [ "$units" -le 10000 ]
}
read_units() { value=$(cat "$1") && percent_units "$value"; }
format_units() { printf '%d.%02d\n' "$(( $1 / 100 ))" "$(( $1 % 100 ))"; }

restore_profile() {
 [ -f "$STATE/applied" ] || return 0
 group=$(cat "$STATE/group") || return 1
 # Only restore the exact nodes this service owns, and only while values match.
 if read_units "$group/cpu.uclamp.min" && [ "$units" = "$(cat "$STATE/ours-min")" ]; then
  cat "$STATE/old-min" > "$group/cpu.uclamp.min" || return 1
 else
  log 'minimum changed externally; retaining external value'
 fi
 current_ls=$(cat "$group/cpu.uclamp.latency_sensitive") || return 1
 if [ "$current_ls" = 1 ]; then
  cat "$STATE/old-ls" > "$group/cpu.uclamp.latency_sensitive" || return 1
 else
  log 'latency hint changed externally; retaining external value'
 fi
 rm -f "$STATE/applied" "$STATE/old-min" "$STATE/old-ls" "$STATE/ours-min" "$STATE/group" "$STATE/active"
 log 'profile released'
}
cleanup() {
 if ! restore_profile; then log 'restore failed; recovery state retained'; return; fi
 rm -f "$STATE/pid" "$STATE/pids" "$STATE/stop" "$STATE/active" "$STATE/old-min" "$STATE/old-ls" "$STATE/ours-min" "$STATE/group"
 rmdir "$STATE" 2>/dev/null || :
}

load_settings() {
 MIN_PERCENT=25
 while IFS='=' read -r key value || [ -n "$key" ]; do
  case "$key" in ''|'#'*) continue;; MIN_PERCENT) MIN_PERCENT=$value;; *) log "unknown setting: $key"; return 1;; esac
 done < "$MODDIR/settings.conf"
 case "$MIN_PERCENT" in ''|*[!0-9]*) log 'MIN_PERCENT must be an integer from 0 to 100'; return 1;; esac
 percent_units "$MIN_PERCENT" || return 1
 target_units=$units
}

detect_group() {
 group=
 for base in /dev/cpuctl /sys/fs/cgroup/cpu /sys/fs/cgroup; do
  candidate=$base/top-app
  if [ -r "$candidate/cpu.uclamp.min" ] && [ -w "$candidate/cpu.uclamp.min" ] &&
     [ -r "$candidate/cpu.uclamp.latency_sensitive" ] && [ -w "$candidate/cpu.uclamp.latency_sensitive" ]; then
   group=$candidate; return 0
  fi
 done
 log 'top-app uclamp nodes missing or not writable'; return 1
}

pid_start() {
 IFS= read -r proc_stat < "/proc/$1/stat" || return 1
 # Fields after the final ') ' start with state (field 3); starttime is field 22.
 proc_stat=${proc_stat##*) }
 set -- $proc_stat
 [ "$#" -ge 20 ] || return 1
 shift 19
 start_time=$1
 case "$start_time" in ''|*[!0-9]*) return 1;; esac
}
refresh_pids() {
 : > "$STATE/pids" || return 1
 while IFS= read -r package || [ -n "$package" ]; do
  case "$package" in ''|'#'*) continue;; *[!a-zA-Z0-9_.]*) log 'invalid package in packages.list'; return 1;; esac
  for pid in $(pidof "$package" 2>/dev/null); do
   case "$pid" in ''|*[!0-9]*) continue;; esac
   pid_start "$pid" || continue
   printf '%s %s %s\n' "$package" "$pid" "$start_time" >> "$STATE/pids" || return 1
  done
 done < "$MODDIR/packages.list"
}
active_game() {
 while read -r package pid saved_start; do
  pid_start "$pid" || continue
  [ "$start_time" = "$saved_start" ] || continue
  while IFS=: read -r hierarchy controllers membership; do
   case ",$controllers," in *,cpu,*) ;; *) [ "$hierarchy" = 0 ] && [ -z "$controllers" ] || continue;; esac
   if [ "$membership" = /top-app ]; then
    active_package=$package; active_pid=$pid; return 0
   fi
  done < "/proc/$pid/cgroup"
 done < "$STATE/pids"
 return 1
}
apply_profile() {
 detect_group || return 1
 read_units "$group/cpu.uclamp.min" || return 1
 original_min=$value
 desired=$target_units
 [ "$units" -le "$desired" ] || desired=$units
 original_ls=$(cat "$group/cpu.uclamp.latency_sensitive") || return 1
 case "$original_ls" in 0|1) ;; *) return 1;; esac
 printf '%s\n' "$group" > "$STATE/group" || return 1
 printf '%s\n' "$original_min" > "$STATE/old-min" || return 1
 printf '%s\n' "$original_ls" > "$STATE/old-ls" || return 1
 printf '%s\n' "$desired" > "$STATE/ours-min" || return 1
 : > "$STATE/applied" || return 1
 format_units "$desired" > "$group/cpu.uclamp.min" || { restore_profile; return 1; }
 printf '1\n' > "$group/cpu.uclamp.latency_sensitive" || { restore_profile; return 1; }
 if ! read_units "$group/cpu.uclamp.min" || [ "$units" != "$desired" ] ||
    [ "$(cat "$group/cpu.uclamp.latency_sensitive")" != 1 ]; then
  log 'profile readback mismatch'; restore_profile; return 1
 fi
 printf '%s pid=%s\n' "$active_package" "$active_pid" > "$STATE/active"
 log "active $active_package pid=$active_pid min=$(format_units "$desired")% latency_sensitive=1"
}
still_owned() {
 group=$(cat "$STATE/group") || return 1
 read_units "$group/cpu.uclamp.min" && [ "$units" = "$(cat "$STATE/ours-min")" ] &&
 [ "$(cat "$group/cpu.uclamp.latency_sensitive")" = 1 ]
}

case "${1:-status}" in
 status)
  if [ -f "$STATE/pid" ]; then
   printf 'service_pid='; cat "$STATE/pid"
  else log 'service not running'; fi
  [ ! -f "$STATE/active" ] || cat "$STATE/active"
  if detect_group; then
   for node in cpu.uclamp.min cpu.uclamp.max cpu.uclamp.latency_sensitive; do
    printf '%s=' "$node"; cat "$group/$node"
   done
  fi
  ;;
 stop|restore)
  if [ -f "$STATE/pid" ] && kill -0 "$(cat "$STATE/pid")" 2>/dev/null; then
   : > "$STATE/stop" || exit 1
   i=0
   while [ -f "$STATE/pid" ] && [ "$i" -lt 8 ]; do sleep 1; i=$((i+1)); done
   [ ! -f "$STATE/pid" ] || { log 'service did not stop; recovery state retained'; exit 1; }
  else
   cleanup
  fi
  ;;
 run)
  load_settings || exit 1
  umask 077
  if ! mkdir "$STATE" 2>/dev/null; then
   if [ -f "$STATE/pid" ] && kill -0 "$(cat "$STATE/pid")" 2>/dev/null; then log 'already running'; exit 0; fi
   cleanup
   mkdir "$STATE" || exit 1
  fi
  printf '%s\n' "$$" > "$STATE/pid" || exit 1
  trap cleanup EXIT
  trap 'exit 0' INT TERM HUP
  detect_group || exit 1
  log "ready: min=${MIN_PERCENT}% for packages.list while Android assigns them to top-app"
  iteration=0
  blocked=0
  previous_game=
  while [ ! -f "$STATE/stop" ] && [ ! -f "$MODDIR/disable" ] && [ ! -f "$MODDIR/remove" ]; do
   if [ "$iteration" = 0 ]; then refresh_pids || exit 1; fi
   iteration=$(( (iteration+1) % 5 ))
   if active_game; then
    if [ -f "$STATE/applied" ] && ! still_owned; then
     log 'external controller changed hints; suspending until this game leaves top-app'
     restore_profile || exit 1
     blocked=1
    fi
    if [ "$previous_game" != "$active_pid" ]; then
     restore_profile || exit 1
     blocked=0
     previous_game=$active_pid
    fi
    if [ ! -f "$STATE/applied" ] && [ "$blocked" = 0 ]; then apply_profile || exit 1; fi
   else
    restore_profile || exit 1
    blocked=0
    previous_game=
   fi
   sleep 1
  done
  ;;
 *) log 'usage: profile.sh [run|status|stop|restore]'; exit 2;;
esac
