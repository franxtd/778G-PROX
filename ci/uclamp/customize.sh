#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
[ "$ARCH" = arm64 ] || abort 'This build targets arm64 Dubai.'
[ "$API" -ge 31 ] || abort 'Android 12 or newer is required.'
case "$(getprop ro.product.device)" in dubai) ;; *) abort 'This profile is configured for Motorola dubai.';; esac
found=0
for base in /dev/cpuctl /sys/fs/cgroup/cpu /sys/fs/cgroup; do
 if [ -w "$base/top-app/cpu.uclamp.min" ] && [ -w "$base/top-app/cpu.uclamp.latency_sensitive" ]; then found=1; fi
done
[ "$found" = 1 ] || abort 'Kernel/ROM top-app uclamp interfaces are unavailable or inaccessible.'
set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/profile.sh" 0 0 0755
set_perm "$MODPATH/service.sh" 0 0 0755
ui_print 'Starling task profile: uclamp minimum 25%, latency_sensitive=1 while in top-app.'
ui_print 'CPU frequency limits, GPU clocks and thermal protection remain controlled by the ROM/fas-rs.'
