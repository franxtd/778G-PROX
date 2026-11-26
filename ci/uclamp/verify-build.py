#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile
out=Path(sys.argv[1] if len(sys.argv)>1 else 'out')
image=out/'arch/arm64/boot/Image'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
with image.open('rb') as f:assert f.read(64)[56:60]==b'ARM\x64'
with (out/'vmlinux').open('rb') as f:assert f.read(20)[18:20]==b'\xb7\x00'
with tempfile.TemporaryDirectory() as td:
 regenerated=Path(td)/'Image'
 subprocess.run([os.environ.get('LLVM_OBJCOPY','llvm-objcopy'),'-O','binary','-R','.note','-R','.note.gnu.build-id','-R','.comment','-S',str(out/'vmlinux'),str(regenerated)],check=True)
 assert sha(regenerated)==sha(image),'Image does not match final ELF'
cfg=(out/'.config').read_text().splitlines()
for key in ['SCHED_WALT','UCLAMP_TASK','UCLAMP_TASK_GROUP','CPU_FREQ_GOV_SCHEDUTIL','KSU','KSU_SUSFS','NOMOUNT','CFI_CLANG','THINLTO','MODVERSIONS','BPF_SYSCALL','BPF_EVENTS','UPROBE_EVENTS','SCHED_DEBUG']:
 assert 'CONFIG_'+key+'=y' in cfg,key
assert len(list(out.rglob('*.ko')))==113
print(json.dumps({'image_sha256':sha(image),'image_matches_final_elf':True,'compiled_modules':113,'uclamp_task_and_group_enabled':True,'walt_schedutil_enabled':True,'bakasu_susfs_nomount_preserved':True,'cfi_thinlto_preserved':True},indent=2))
