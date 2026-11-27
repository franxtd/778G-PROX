> Nota da revisão Full LTO/AutoFDO: este documento registra a integração FAS
> anterior. O workflow atual não gera ZIP de módulo fas-rs. O kernel usa
> Full LTO por padrão, preserva CFI e mantém os testes BPF. Consulte
> `autofdo/README.md` e `performance/AOSPA-REVIEW.md` para o estado atual.

# Dubai 5.4.286: gaming/FAS compatibility build

Base: `afef2f1aaf50ef70583e86ba100837eb6e751b96` (working NoMount integration).
Device: Motorola Edge 30 / dubai, LOS 21 Android 14, December 2024 ROM.
BakaSU v4.1.0, SUSFS 2.4.0 and NoMount v2.3.1 remain built in.

## CPU and memory

`CONFIG_CPU_FREQ_GOV_ONDEMAND=y` and `CONFIG_CPU_FREQ_GOV_USERSPACE=y` add two
selectable governors. Existing performance, powersave, conservative and schedutil
remain available. The ROM's original default remains performance; no frequency
or voltage tables, boost limits or thermal protection have been changed.
fas-rs adjusts cpufreq min/max limits in userspace and needs no special governor.

The companion module has a reversible zRAM readahead profile: `vm.page-cluster=0`
only when all active swap devices are zRAM. It saves the old value for this boot
and supports restore/opt-out. This avoids speculative decompression of adjacent
swap pages, trading sequential-swap throughput for individual fault latency.
No extra memory is created and no measured FPS gain is claimed.

Existing PSI, memory cgroups, compaction, LZ4/ZSTD and zRAM support are retained.
The ROM's zRAM remains a module; this boot-only ZIP does not replace ROM modules.
The profile therefore changes a runtime VM control instead of relying on a new
zRAM module that the installer would not actually install. No live swap reset,
cache dropping, arbitrary swappiness/LMKD changes or memory-layout backports.

## eBPF backport

The upstream fas-rs 4.9.1 release embeds frame-analyzer-ebpf, which uses map type
27 (ringbuf), helper 131 (reserve) and 132 (submit), plus uprobes and mmap/poll.
The original 5.4 tree has tracing/JIT/uprobes but lacks this ringbuf ABI.

The backport is derived from upstream commit
`457f44363a8894135c85b7a9afd2bd8196db24ab` and ringbuf.c from Linux stable 5.10
commit `3a323bc22b881a5bdc1646080f93f5ecb22850bf`. The implementation includes the
pending-position reservation fix and irq_work synchronization before freeing.
Pin information and official release hashes are in `fas/UPSTREAM.json`.

Adaptations for 5.4:

- Map type 26 and helper IDs 126..129 retain their upstream numeric slots but
  are unsupported. No fake implementation is provided for them. Helpers 130..134
  (output/reserve/submit/discard/query) are available to tracing programs.
- Extend verifier allocation bounds, nullable-pointer and reference tracking.
  Release requires the start of a live reservation; derived and spilled pointers
  carry the allocation's reference identity.
- Use existing bpf_map memlock accounting and require CAP_SYS_ADMIN for creation.
- Dispatch ringbuf-only mmap/poll from bpf_map_fops, preserving bpf_map_ops layout.
  Writable mappings are restricted to the consumer page; freeze is unsupported
  for ringbuf. Other maps retain their existing behavior.
- New enum constants are appended, with existing ordinals and enum widths
  preserved. mem_size aliases an existing union with an unsigned-long member.
  These additive definitions are hidden from genksyms so unchanged old layouts
  retain their original type hashes. CRC values are generated normally, never
  hardcoded or overwritten.

The companion module retains the official v4.9.1 daemon byte-for-byte and replaces
its >=5.8 version gate with a real feature test. It fails closed on missing BPF
features or permissions. Build/use instructions are in `fas/README.md`.

## Validation

The exact final ARM64 Image was booted under QEMU cortex-a76 / generic virt.
Two Qualcomm-only initcalls, scm_mem_protection_init and remoteqdss_init, were
blacklisted through the test command line because QEMU has no Qualcomm secure
firmware. The linked kernel Image was not modified. This is not a phone boot test.

The static probe loaded the official release's eBPF instructions, attached a real
self-uprobe, verified 400 timestamp/token records via mmap/poll and wrapped the
4096-byte ring buffer. It checked rejection of reservation leaks, out-of-bounds
stores, shifted/double releases, use after release, arithmetic before a null test,
and writable producer mappings. The probe's installed binary performs these same
checks on the phone before launching fas-rs.

All 113 kernel modules compile. Original 14,434 exported symbols retain their
CRCs; the two additional exports belong to the existing ondemand governor code.
CFI and ThinLTO remain enabled. Image/ELF correspondence, config delta, module
inventory/vermagic, patch application, RAM profile skip/restore behavior and ZIP
integrity are checked in the accompanying validation report.

Device boot, Android SELinux/game attachment, actual governor transitions, gaming
FPS/frame pacing, heat and battery life still require testing on the phone.

## Build

Use the pinned AOSP Clang/BakaSU versions in `.github/workflows/build-dubai.yml`:

```sh
make O=out ARCH=arm64 LLVM=1 LLVM_IAS=1 vendor/franbakasu_susfs_defconfig
make -j8 O=out ARCH=arm64 LLVM=1 LLVM_IAS=1 Image dtbs modules
make O=out ARCH=arm64 LLVM=1 LLVM_IAS=1 headers_install
CC=clang ci/fas/build-probe.sh out
python3 ci/fas/test-ram-profile.py
python3 ci/fas/run-qemu.py out/arch/arm64/boot/Image out/fas-feature-probe qemu.log
```

Use one make invocation for Image/dtbs/modules so the packaged Image corresponds
to the final linked ELF. See the workflow for full tool flags and packaging.
