#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Test real Kbuild flag routing and the LLVM reader/compiler/linker path."""
from pathlib import Path
import argparse, subprocess, tempfile
from profile import reader

root=Path(__file__).resolve().parents[2]
fixture='''CONFIG_AUTOFDO_CLANG := y
CONFIG_DEBUG_INFO := y
CONFIG_THINLTO := y
srctree := .
obj := afdo-test
src := afdo-test
obj-y := builtin.o excluded.o
obj-m := module.o
AUTOFDO_PROFILE_excluded.o := n
basetarget = $(notdir $(basename $@))
include scripts/Kbuild.include
include scripts/Makefile.autofdo
include scripts/Makefile.lib
.PHONY: afdo-test/builtin.o afdo-test/module.o afdo-test/excluded.o
afdo-test/builtin.o afdo-test/module.o afdo-test/excluded.o:
	@echo $(_c_flags)
'''
with tempfile.TemporaryDirectory() as td:
    td=Path(td);mk=td/'Makefile';mk.write_text(fixture)
    def flags(target,extra=()):
        return subprocess.check_output(['make','--no-print-directory','-s','-f',str(mk),target,*extra],cwd=root,text=True).strip()
    assert '-fdebug-info-for-profiling' in flags('afdo-test/builtin.o')
    assert '-fdebug-info-for-profiling' not in flags('afdo-test/module.o')
    assert '-fdebug-info-for-profiling' not in flags('afdo-test/excluded.o')
    assert '-fdebug-info-for-profiling' not in flags('afdo-test/builtin.o',['CONFIG_AUTOFDO_CLANG=n'])
    r=subprocess.run(['make','-s','-f',str(mk),'afdo-test/builtin.o',f'CLANG_AUTOFDO_PROFILE={td}/missing.afdo'],cwd=root,capture_output=True)
    assert r.returncode and b'does not exist' in r.stderr
    print('PASS Kbuild: built-in profiling, module/file exclusion, off mode and missing-profile rejection')
    p=argparse.ArgumentParser();p.add_argument('--llvm',action='store_true');a=p.parse_args()
    if a.llvm:
        # Synthetic compiler fixture only. Never supplied to a kernel build.
        sample=td/'SYNTHETIC-TEST-ONLY.afdo'
        sample.write_text('afdo_smoke:1000:100\n 1: 1000\n 2: 900\n 3: 100\n')
        assert reader(sample)['samples']==1000
        empty=td/'empty.afdo';empty.write_bytes(b'')
        try:reader(empty)
        except ValueError:pass
        else:raise AssertionError('Empty profile accepted')
        source=td/'smoke.c';source.write_text('__attribute__((noinline)) int afdo_smoke(int x) {\n if (x) return x+1;\n return 0;\n}\nint entry(void) { return afdo_smoke(1); }\n')
        f=flags('afdo-test/builtin.o',[f'CLANG_AUTOFDO_PROFILE={sample}']).split()
        subprocess.run(['clang','--target=aarch64-linux-gnu','-O2','-g','-flto=thin',*f,
            '-S','-emit-llvm',str(source),'-o',str(td/'smoke.ll')],check=True)
        ir=(td/'smoke.ll').read_text()
        assert 'function_entry_count' in ir and '!prof' in ir
        subprocess.run(['clang','--target=aarch64-linux-gnu','-O2','-g','-flto=thin',
            '-fsanitize=cfi','-fvisibility=hidden',*f,'-fuse-ld=lld','-nostdlib',
            f'-Wl,--lto-sample-profile={sample}','-Wl,--mllvm=-enable-fs-discriminator=true',
            '-Wl,--mllvm=-improved-fs-discriminator=true','-Wl,-e,entry',str(source),'-o',str(td/'smoke')],check=True)
        print('PASS LLVM: sample reader, nonzero samples, IR profile metadata and ARM64 ThinLTO/CFI link')
        print('Synthetic profile was used only for this tiny compiler fixture; no device performance claim.')
