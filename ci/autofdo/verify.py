#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
from pathlib import Path
import json,sys
out=Path(sys.argv[1]);mode=sys.argv[2];lto=sys.argv[3]
enabled='CONFIG_AUTOFDO_CLANG=y' in (out/'.config').read_text().splitlines()
assert enabled==(mode!='off')
for p in ['kernel/sched/.cpufreq_walt.o.cmd','mm/.vmscan.o.cmd']:
    command=(out/p).read_text()
    assert ('-flto=thin' in command)==(lto=='thin'),p
    if lto=='full':assert '-flto ' in command,p
    assert ('-fdebug-info-for-profiling' in command)==enabled,p
    assert ('-gline-tables-only' in command)==enabled,p
    assert ('-fprofile-sample-use=' in command)==(mode=='profile'),p
module=out/'drivers/block/zram/.zram_drv.o.cmd'
assert '-fdebug-info-for-profiling' not in module.read_text()
assert '-fprofile-sample-use=' not in module.read_text()
assert '# CONFIG_CORESIGHT_SOURCE_ETM4X is not set' in (out/'.config').read_text()
report={'mode':mode,'lto_mode':lto,'collection_metadata_enabled':enabled,'profile_applied':mode=='profile',
        'profiling_debug_info':'line-tables-only' if enabled else 'baseline',
        'module_profile_flags_applied':False,'etm_hardware_configuration_changed':False,
        'device_profile_collected':mode=='profile','performance_gain_measured':False}
Path('logs/autofdo-build.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
