#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the actual ARM64 kernel and static BPF probe, without a device image."""
from pathlib import Path
import gzip, os, re, subprocess, sys, tempfile

def entry(name, mode, data=b'', major=0, minor=0):
    name = name.encode()+b'\0'
    fields = [1, mode, 0, 0, 1, 0, len(data), 0, 0, major, minor, len(name), 0]
    h = b'070701'+b''.join(f'{v:08x}'.encode() for v in fields)
    a = h+name
    a += b'\0'*(-len(a)%4)
    a += data
    return a+b'\0'*(-len(data)%4)

image, probe, module, log = map(Path, sys.argv[1:])
# Qualcomm's early firmware call cannot run on QEMU's generic ARM platform.
# Use the linked CFI names as well; never modify the distributed kernel Image.
system_map = image.parents[3]/'System.map'
blocked = [line.split()[-1] for line in system_map.read_text().splitlines()
           if re.fullmatch(r'(?:scm_mem_protection_init|remoteqdss_init)(?:\.[\w.]+)?', line.split()[-1])]
assert blocked, 'Cannot locate the Qualcomm-only initcall'
cmdline = ('earlycon=pl011,0x9000000 console=ttyAMA0 ignore_loglevel rdinit=/init '
           'panic=-1 nokaslr initcall_blacklist='+','.join(blocked))
with tempfile.TemporaryDirectory() as td:
    initrd = Path(td)/'init.cpio.gz'
    archive = b''.join(entry(n, 0o040755) for n in ['dev','proc','sys'])
    archive += entry('dev/console', 0o020600, major=5, minor=1)
    archive += entry('init', 0o100755, probe.read_bytes())
    archive += entry('fran_qemu_cpufreq.ko', 0o100600, module.read_bytes())
    archive += entry('compat-probe', 0o100755, (probe.parent/'compat-probe').read_bytes())
    archive += entry('TRAILER!!!', 0)
    initrd.write_bytes(gzip.compress(archive, mtime=0))
    command = [os.environ.get('QEMU_BINARY','qemu-system-aarch64'), '-M','virt',
               '-cpu','cortex-a76','-m','1024','-smp','2','-nodefaults','-nographic','-serial','stdio','-monitor','none',
               '-no-reboot','-kernel',str(image),'-initrd',str(initrd),
               '-append',cmdline]
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('wb') as f:
        try:
            result = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, timeout=300)
        except subprocess.TimeoutExpired:
            raise SystemExit('QEMU timed out; inspect '+str(log))
    text = log.read_text(errors='replace')
    checks = [s for s in text.splitlines() if 'PASS' in s or 'FAIL' in s or 'Kernel panic' in s]
    print('\n'.join(checks))
    if result.returncode or 'PERFORMANCE_PROBE: PASS' not in text or 'FAIL:' in text:
        raise SystemExit('QEMU memory/governor test failed: '+str(log))
