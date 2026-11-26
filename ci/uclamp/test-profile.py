#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the actual shell service against isolated proc/cgroup fixtures."""
from pathlib import Path
import os,subprocess,tempfile,time
source=Path(__file__).with_name('profile.sh').read_text()
with tempfile.TemporaryDirectory() as td:
 root=Path(td); group=root/'ctl/top-app';group.mkdir(parents=True)
 proc=root/'proc/123';proc.mkdir(parents=True)
 (proc/'stat').write_text('123 (a name with spaces) R '+' '.join(['0']*18+['100']+['0']*10)+'\n')
 (proc/'cgroup').write_text('2:cpu,cpuacct:/background\n')
 for n,v in [('cpu.uclamp.min','0.00\n'),('cpu.uclamp.max','80.00\n'),('cpu.uclamp.latency_sensitive','0\n')]: (group/n).write_text(v)
 for name,value in [('settings.conf','MIN_PERCENT=25\n'),('packages.list','io.github.juanluci.starling.preview\n')]: (root/name).write_text(value)
 binary=root/'bin';binary.mkdir();pidof=binary/'pidof'
 pidof.write_text('#!/bin/sh\n[ -f "'+str(root/'no-pid')+'" ] || echo 123\n');pidof.chmod(0o755)
 script=root/'profile.sh'
 code=source.replace('/dev/.fran-uclamp-profile',str(root/'state')).replace('/dev/cpuctl',str(root/'ctl')).replace('/sys/fs/cgroup/cpu',str(root/'unused1')).replace('/sys/fs/cgroup',str(root/'unused2')).replace('/proc/',str(root/'proc')+'/')
 script.write_text(code)
 env=os.environ.copy();env['PATH']=str(binary)+':'+env['PATH']
 def wait(condition):
  deadline=time.monotonic()+8
  while time.monotonic()<deadline:
   if condition():return
   time.sleep(.03)
  raise AssertionError('Timed out: '+(root/'run.log').read_text())
 def value(n):return (group/n).read_text().strip()
 def change_group(path):
  p=proc/'new-cgroup';p.write_text('2:cpu,cpuacct:'+path+'\n');p.replace(proc/'cgroup')
 log=(root/'run.log').open('w')
 p=subprocess.Popen(['sh',str(script),'run'],env=env,stdout=log,stderr=log)
 try:
  wait(lambda:(root/'state/pids').exists())
  assert value('cpu.uclamp.min')=='0.00'
  change_group('/top-app')
  wait(lambda:value('cpu.uclamp.min')=='25.00' and value('cpu.uclamp.latency_sensitive')=='1')
  assert value('cpu.uclamp.max')=='80.00'
  change_group('/background')
  wait(lambda:value('cpu.uclamp.min')=='0.00' and value('cpu.uclamp.latency_sensitive')=='0')
  (group/'cpu.uclamp.min').write_text('40.00\n');change_group('/top-app')
  wait(lambda:value('cpu.uclamp.latency_sensitive')=='1')
  assert value('cpu.uclamp.min')=='40.00'
  change_group('/background');wait(lambda:value('cpu.uclamp.latency_sensitive')=='0')
  (group/'cpu.uclamp.min').write_text('0.00\n');change_group('/top-app')
  wait(lambda:value('cpu.uclamp.min')=='25.00')
  (group/'cpu.uclamp.min').write_text('10.00\n')
  wait(lambda:value('cpu.uclamp.latency_sensitive')=='0')
  time.sleep(1.1);assert value('cpu.uclamp.min')=='10.00'
  (root/'disable').touch();p.wait(timeout=8);assert p.returncode==0
  assert value('cpu.uclamp.max')=='80.00' and not (root/'state').exists()
 finally:
  if p.poll() is None:p.terminate();p.wait(timeout=8)
  log.close()
 (root/'disable').unlink();(group/'cpu.uclamp.min').write_text('0.00\n')
 with (root/'run.log').open('a') as log:
  p=subprocess.Popen(['sh',str(script),'run'],env=env,stdout=log,stderr=log)
  wait(lambda:value('cpu.uclamp.min')=='25.00')
  p.kill();p.wait()
  subprocess.run(['sh',str(script),'restore'],env=env,check=True,capture_output=True)
  assert value('cpu.uclamp.min')=='0.00' and value('cpu.uclamp.latency_sensitive')=='0'
 # Source function definitions for parsing and reused-PID checks, without a daemon.
 functions=root/'functions.sh';functions.write_text(code[:code.index('case "${1:-status}" in')])
 for raw,expected in [('0',0),('25.00',2500),('2.5',250),('max',10000),('001.05',105)]:
  result=subprocess.run(['sh','-c','. "$1"; percent_units "$2" && printf "%s" "$units"','test',str(functions),raw],capture_output=True,text=True,check=True)
  assert result.stdout==str(expected),(raw,result.stdout)
 for raw in ['','-1','101','1.234','1.2.3','a','$(id)']:
  result=subprocess.run(['sh','-c','. "$1"; percent_units "$2"','test',str(functions),raw],capture_output=True)
  assert result.returncode!=0,raw
 print('PASS task profile: foreground gating, restore, existing higher floor, unchanged max, external writer, disable and crash recovery')
 print('PASS bounded percentage parsing and PID starttime fixture')
