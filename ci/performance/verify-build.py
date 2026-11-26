#!/usr/bin/env python3
"""Ensure phone-module ABI and native UClamp configuration are preserved."""
from pathlib import Path
import sys
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
