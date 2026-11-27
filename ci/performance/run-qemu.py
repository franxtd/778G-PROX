#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Run the production Image with CI-only CPUfreq hardware and ABI probes."""
from pathlib import Path
import gzip, os, re, subprocess, sys, tempfile

def entry(name, mode, data=b'', major=0, minor=0):
    name = name.encode()+b'\0'
    fields = [1, mode, 0, 0, 1, 0, len(data), 0, 0, major, minor, len(name), 0]
    a = b'070701'+b''.join(f'{v:08x}'.encode() for v in fields)+name
    a += b'\0'*(-len(a)%4)
    return a+data+b'\0'*(-len(data)%4)

image, probe, module, log = map(Path, sys.argv[1:])
symbols = [line.split()[-1] for line in (image.parents[3]/'System.map').read_text().splitlines()]
base_blocked = [s for s in symbols if re.fullmatch(r'(?:scm_mem_protection_init|remoteqdss_init)(?:\.[\w.]+)?',s)]
walt_blocked = [s for s in symbols if re.fullmatch(r'register_walt_callback(?:\.[\w.]+)?',s)]
assert base_blocked and walt_blocked, 'Missing linked initcall names'
all_logs = []
for mode in ['normal','fast']:
    # On hardware qcom-cpufreq-hw registers its cycle counter and removes this
    # transition notifier. QEMU has no Qualcomm counter. For fast-path coverage
    # only, skip that notifier initcall in the guest command line. This boot
    # tests governor/limit code; it cannot validate WALT cycle/load accuracy.
    blocked = base_blocked + (walt_blocked if mode == 'fast' else [])
    cmdline = ('earlycon=pl011,0x9000000 console=ttyAMA0 ignore_loglevel rdinit=/init '
               'panic=-1 nokaslr initcall_blacklist='+','.join(blocked))
    with tempfile.TemporaryDirectory() as td:
        initrd = Path(td)/'init.cpio.gz'
        archive = b''.join(entry(n,0o040755) for n in ['dev','proc','sys'])
        archive += entry('dev/console',0o020600,major=5,minor=1)
        for n,p in [('init',probe),('compat-probe',probe.parent/'compat-probe'),('fran_qemu_cpufreq.ko',module)]:
            archive += entry(n,0o100755,p.read_bytes())
        archive += entry('zram.ko',0o100600,(probe.parent/'drivers/block/zram/zram.ko').read_bytes())
        archive += entry('qemu-mode',0o100444,mode.encode())+entry('TRAILER!!!',0)
        initrd.write_bytes(gzip.compress(archive,mtime=0))
        command = [os.environ.get('QEMU_BINARY','qemu-system-aarch64'),'-M','virt',
                   '-cpu','cortex-a76','-m','1024','-smp','2','-nodefaults',
                   '-nographic','-serial','stdio','-monitor','none','-no-reboot',
                   '-kernel',str(image),'-initrd',str(initrd),'-append',cmdline]
        per_log = log.with_name(log.stem+'-'+mode+log.suffix)
        per_log.parent.mkdir(parents=True,exist_ok=True)
        with per_log.open('wb') as f:
            try:
                result = subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=300)
            except subprocess.TimeoutExpired:
                raise SystemExit('QEMU timed out; inspect '+str(per_log))
        text = per_log.read_text(errors='replace');all_logs.append(text)
        print('\n'.join(s for s in text.splitlines() if 'PASS' in s or 'FAIL' in s or 'Kernel panic' in s))
        if result.returncode or 'PERFORMANCE_PROBE: PASS' not in text or 'FAIL:' in text or 'Kernel panic' in text:
            raise SystemExit('QEMU memory/governor test failed: '+str(per_log))
        if mode == 'fast':
            assert 'PASS hardware fast-switch callback actually executed' in text
log.write_text('\n'.join(all_logs))
