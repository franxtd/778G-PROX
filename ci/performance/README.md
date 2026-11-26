# FranBakaSU WALT / Memory ABI / GPU — Dubai LOS21

Target: Motorola Edge 30 (dubai), LineageOS 21 Android 14,
5.4.286. Experimental until physically booted and measured on that phone.

## Changes

* Reverts the complete acb885d5 UClamp patch set. The native scheduler,
  schedutil, scheduler debug and UClamp structures are byte-for-byte the
  known-boot 00cf9162 source. Pre-existing CONFIG_UCLAMP_TASK and
  CONFIG_UCLAMP_TASK_GROUP remain enabled for Android compatibility.
* Backports Qualcomm's real WALT governor from the pinned 5.10 source
  in UPSTREAM.json, using this 5.4 scheduler's update-util hooks and clocks.
  The governor is named `walt`, with per-policy rate limits, hispeed,
  related-thread-group and predictive-load tunables. Both hardware fast
  switching and deferred switching are supported. Hard frequency limits
  take effect independently of rate limiting. Existing governors remain.
* Corrects syscall 440 process_madvise from the obsolete six-argument draft
  to Android's five-argument pidfd ABI. Implements native and compat iovecs,
  partial byte-count returns, READ_FSCREDS and CAP_SYS_NICE authorization.
  This repairs an interface used by Android process compaction; it does
  not force the ROM to enable compaction or prove a measured RAM saving.
* Gives the KGSL GPU DVFS workqueue WQ_HIGHPRI while preserving its
  single-active ordering, freezer, unbound and reclaim flags. No OPP,
  voltage, thermal, GPU-governor or idle-timer changes.
* Preserves BakaSU, SUSFS, NoMount, FAS BPF backports, zRAM module,
  SELinux, CFI and the existing phone driver/module configuration.

## Remove the previous optional UClamp module

If `FranBakaSU UClamp Task Profiles` is installed, first stop its service
and disable it in BakaSU. The new kernel cannot remove an Android module
already installed under /data/adb/modules.

```sh
su -c 'if [ -f /data/adb/modules/fran_uclamp_profiles/profile.sh ]; then sh /data/adb/modules/fran_uclamp_profiles/profile.sh stop; fi'
```

Disable/uninstall `fran_uclamp_profiles` in the root manager and reboot with
the new kernel. Keep the working boot backup and recovery method.

## Select WALT after boot

The kernel keeps the original default governor. Android's Power HAL may
select schedutil at boot or overwrite a manual selection. Check all policies:

```sh
su -c '
cat /proc/version
for p in /sys/devices/system/cpu/cpufreq/policy*; do
  echo "$p"
  cat "$p/scaling_available_governors"
  echo walt > "$p/scaling_governor" || exit 1
  cat "$p/scaling_governor"
done
'
```

To roll back the runtime governor selection, replace `echo walt` above
with `echo schedutil`. This does not require reflashing. The selection is
temporary; no persistent tuning daemon is installed by this ZIP. Do not
reuse tuning modules that constantly overwrite FAS frequency limits.

## Verification

CI builds the complete ARM64 Image, device trees and original modules with
the pinned AOSP Clang and checks every baseline exported-symbol CRC. QEMU
runs the real Image with a CI-only virtual cpufreq driver: governor switch
lifecycle and forced limits through both fast and deferred paths. It tests
process_madvise native/AArch32 vector import, data preservation, byte counts, partial completion and
permission/error paths, then runs the original 400-uprobe FAS feature test.
The virtual driver is never included in the flashable ZIP and refuses real
phone platforms. Qualcomm-only early firmware initcalls are skipped only in
QEMU's boot command line; the distributed Image is not modified.

QEMU cannot verify the physical GPU, phone boot, thermals, ROM compaction
policy or FPS improvement. On-device comparison should use the same game,
scene, graphics settings, battery level and initial temperature, measuring
frame-time outliers and sustained performance rather than peak frequency.

The boot-only AnyKernel3 package preserves the installed ramdisk and does
not flash modules, DTB, DTBO or vendor_boot. ABI checks reduce one source
of risk; they do not establish a boot guarantee for an untested ROM.
