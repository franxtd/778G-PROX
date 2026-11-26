#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise reversible writes and skip behavior against isolated fake proc files."""
from pathlib import Path
import subprocess, tempfile
source=Path(__file__).with_name('ram-profile.sh').read_text()
with tempfile.TemporaryDirectory() as t:
    root=Path(t); knob=root/'page-cluster'; swaps=root/'swaps'; state=root/'state'; script=root/'ram-profile.sh'
    script.write_text(source.replace('/proc/sys/vm/page-cluster',str(knob)).replace('/proc/swaps',str(swaps)).replace('/dev/.franbakasu-ram',str(state)))
    def run(arg='apply'):
        return subprocess.run(['sh',str(script),arg],check=True,text=True,capture_output=True).stdout
    header='Filename Type Size Used Priority\n'
    knob.write_text('3\n');swaps.write_text(header);run();assert knob.read_text()=='3\n' and not state.exists()
    swaps.write_text(header+'/dev/block/zram0 partition 4096 100 1\n/dev/block/sda swap 4096 0 0\n')
    run();assert knob.read_text()=='3\n' and not state.exists()
    swaps.write_text(header+'/dev/block/zram0 partition 4096 100 1\n')
    run();assert knob.read_text()=='0\n' and (state/'page-cluster').read_text()=='3\n'
    run();assert (state/'page-cluster').read_text()=='3\n'
    run('restore');assert knob.read_text()=='3\n' and not state.exists()
    run();knob.write_text('1\n');run('restore');assert knob.read_text()=='1\n' and not state.exists()
    (root/'disable-ram-profile').touch();run();assert knob.read_text()=='1\n' and not state.exists()
print('PASS RAM profile: zRAM-only apply, empty/mixed swap skip, idempotence, restore, external changes, opt-out')
