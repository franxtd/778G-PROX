#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
from pathlib import Path
import json,subprocess,sys
here=Path(__file__).resolve().parent
out=Path(sys.argv[1] if len(sys.argv)>1 else 'out')
def read(path):return {s[1]:s[0] for l in path.read_text().splitlines() if len(s:=l.split())>=2}
old=read(here/'exported-symbols-00cf9162.tsv');new=read(out/'Module.symvers')
changed={n:{'before':old[n],'after':new[n]} for n in old.keys()&new.keys() if old[n]!=new[n]}
removed=sorted(old.keys()-new.keys())
report={'baseline_source_commit':'00cf9162657ed37fc3a460523ec84b3aa6bed9a2','baseline_ci_run':45769079532,'baseline_artifact':15094547646,'baseline_exports':len(old),'new_exports':len(new),'changed_crcs':changed,'removed_exports':removed,'added_exports':sorted(new.keys()-old.keys())}
print(json.dumps(report,indent=2))
assert len(old)==14436 and not changed and not removed, 'Exported ABI changed'
