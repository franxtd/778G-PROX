# fas-rs 4.9.1 / FranBakaSU 5.4 compatibility

Historical module sources and current kernel feature tests. The module ZIP
generator has been removed from the current build workflow. Instructions below
for installing a module refer to the previously delivered compatibility ZIP.

Target: Motorola Edge 30 (dubai), LOS 21 / Android 14, Linux 5.4.286.
This is a compatibility package, maintained separately from upstream fas-rs.
The official v4.9.1 daemon is included unchanged; its SHA-256 and source tag are
recorded in UPSTREAM.json. Original licenses and attribution are retained.

## Changes

- The installer uses a real root BPF feature test instead of the upstream >=5.8
  version gate. A kernel without the necessary backport or permissions is rejected.
- The same test runs before the daemon starts after a reboot.
- The probe loads the official release's frame-analyzer program, creates a ringbuf
  map, attaches a self-uprobe and checks 400 timestamp/token events with mmap/poll.
  It also checks that unsafe reservation programs are rejected by the verifier.
- The optional RAM adjustment sets vm.page-cluster=0 only if active swap devices
  are exclusively zRAM. Capacity, compression algorithm, swappiness, LMKD, thermal
  controls and frequency limits remain under the ROM's control.
- The upstream update URL is omitted because an ordinary upstream module update
  would restore its kernel version restriction and remove this compatibility test.

## Use

1. Boot the matching FranBakaSU gaming/FAS kernel first.
2. Install this ZIP through BakaSU and reboot. Use one instance of fas-rs only.
3. Configure your actual game package names and target frame rates in
   `/sdcard/Android/fas-rs/games.toml`; the original upstream template is included.
   No game list or target FPS has been invented for this device.
4. Check `/sdcard/Android/fas-rs/feature-probe.log`, `fas_log.txt` and
   `ram-profile.log`. A feature-test failure prevents daemon startup.

Manual probe (root):

```sh
/data/adb/modules/fas_rs/fas-feature-probe
cat /sys/devices/system/cpu/cpufreq/policy*/scaling_available_governors
cat /proc/sys/vm/page-cluster
```

To disable the RAM adjustment and restore its original value this boot:

```sh
touch /data/adb/modules/fas_rs/disable-ram-profile
sh /data/adb/modules/fas_rs/ram-profile.sh restore
```

Removing `disable-ram-profile` enables it on the next reboot. Disabling the whole
module stops its service at the next boot. Runtime settings reset on reboot.

`ondemand` and `userspace` are selectable governors; this package does not switch
them automatically. fas-rs controls cpufreq min/max limits and requires no new
special governor. Running multiple frequency-control modules may conflict.

## Kernel feature test (module ZIP generation removed)

With the pinned BakaSU source present and the kernel UAPI headers installed:

```sh
CC=clang ci/fas/build-probe.sh out
python3 ci/fas/run-qemu.py out/arch/arm64/boot/Image out/fas-feature-probe qemu.log
```

The current kernel workflow no longer downloads or builds a fas-rs module ZIP.
The already installed module is independent of this removal.
The static probe needs no Android libc or Rust toolchain. Full fas-rs source is at
https://github.com/shadow3aaa/fas-rs/tree/eb883c534e92107f536ae8ebc343c99243f5ee4d
and is licensed GPL-3.0-or-later. The embedded BPF program is GPL-3.0-or-later.
The compatibility scripts and probe source accompany this package in the kernel
repository's `ci/fas` directory and the separate source/config/log archive.

QEMU uses the distributed kernel Image with two Qualcomm-only firmware initcalls
blacklisted through its test command line; see `../GAMING.md`.

The BPF self-test verifies the kernel path, not Android SurfaceFlinger symbol
availability, SELinux policy for each game or measured game performance. Device
boot, GPU behavior, sustained FPS and battery consumption need device testing.
