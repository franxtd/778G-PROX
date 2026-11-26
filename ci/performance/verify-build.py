#!/usr/bin/env python3
"""Ensure phone-module ABI and native UClamp configuration are preserved."""
from pathlib import Path
import sys, hashlib, json, os, subprocess, tempfile
out = Path(sys.argv[1])
base = Path('ci/performance/Module.symvers.baseline')
def symbols(p):
    return {s[1]: s[0] for line in p.read_text().splitlines() if (s := line.split())}
a, b = symbols(base), symbols(out/'Module.symvers')
missing = sorted(a.keys()-b.keys())
changed = sorted(k for k in a.keys() & b.keys() if a[k] != b[k])
assert not missing and not changed, (missing, changed)
print(f'PASS all {len(a)} baseline exported-symbol CRCs unchanged')
c = (out/'.config').read_text().splitlines()
for name in ['SCHED_WALT','CPU_FREQ_GOV_WALT','CPU_FREQ_GOV_SCHEDUTIL',
             'UCLAMP_TASK','UCLAMP_TASK_GROUP','MEMCG','PSI','SWAP',
             'COMPACTION','KSU','NOMOUNT','KSU_SUSFS','CFI_CLANG','MODVERSIONS']:
    assert f'CONFIG_{name}=y' in c, name
print('PASS WALT enabled; native UClamp, memory, root and integrity options retained')
def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()
image = out/'arch/arm64/boot/Image'
with tempfile.TemporaryDirectory() as td:
    regenerated = Path(td)/'Image'
    subprocess.run([os.environ.get('LLVM_OBJCOPY', 'llvm-objcopy'),
                    '-O','binary','-R','.note','-R','.note.gnu.build-id',
                    '-R','.comment','-S',str(out/'vmlinux'),str(regenerated)],check=True)
    assert sha(regenerated) == sha(image), 'Image differs from final linked ELF'
assert len(list(out.rglob('*.ko'))) == 113
report = {'baseline_exports': len(a), 'changed_crcs': changed,
          'removed_exports': missing, 'compiled_modules': 113,
          'image_matches_final_elf': True, 'image_sha256': sha(image)}
Path('logs/performance-build.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS production Image matches final ELF; 113 phone modules built')
