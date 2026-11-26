#!/usr/bin/env python3
from pathlib import Path
import subprocess
base = '00cf9162657ed37fc3a460523ec84b3aa6bed9a2'
# The reviewed native scheduler/UClamp code must be exactly the known-boot base.
# Blob hashes let this check work in a depth-one Actions checkout.
expected = {
 'kernel/sched/core.c': '30930250bcca19e6fec9b83a2ed749c1a9fad04e',
 'kernel/sched/cpufreq_schedutil.c': '9de29b93c046eb6a3fab27f1d35fd0da206b6a6a',
 'kernel/sched/debug.c': '562ccde36c15055b10588cc20256ffa8315f9050',
 'kernel/sched/sched.h': 'b5ac1d91cb4551b1bccec2ee45f5af00d9eeb609',
}
for p, sha in expected.items():
    assert subprocess.check_output(['git','hash-object',p],text=True).strip()==sha,p
assert not Path('ci/uclamp').exists()
gpu=Path('drivers/gpu/msm/kgsl_pwrscale.c').read_text()
assert '__WQ_LEGACY | WQ_FREEZABLE | WQ_UNBOUND | WQ_MEM_RECLAIM |\n\t\tWQ_HIGHPRI, 1)' in gpu
assert 'SYSCALL_DEFINE5(process_madvise, int, pidfd,' in Path('mm/madvise.c').read_text()
print('PASS extra UClamp changes removed; original native scheduler restored')
print('PASS GPU workqueue retains freeze/reclaim/order flags and adds priority')
