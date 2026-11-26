#!/system/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
MODDIR=${0%/*}
umask 077
until [ "$(getprop sys.boot_completed)" = 1 ]; do sleep 2; done
exec sh "$MODDIR/profile.sh" run > "$MODDIR/profile.log" 2>&1
