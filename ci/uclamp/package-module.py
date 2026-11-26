#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED,ZipInfo
import hashlib,json,sys
here=Path(__file__).resolve().parent
upstream,output=map(Path,sys.argv[1:])
assert hashlib.sha256(upstream.read_bytes()).hexdigest()=='0157de34da9792a29283af76a2d62cca21fdc73f7420c834c361481d0474338b'
with ZipFile(upstream) as src, ZipFile(output,'w',ZIP_DEFLATED,compresslevel=9) as z:
 for n in ['META-INF/com/google/android/update-binary','META-INF/com/google/android/updater-script']:
  info=src.getinfo(n);z.writestr(info,src.read(n),compress_type=ZIP_DEFLATED)
 for n in ['module.prop','customize.sh','service.sh','uninstall.sh','profile.sh','settings.conf','packages.list','README.md','collect.sh']:
  item=ZipInfo(n,(2026,11,26,0,0,0));item.create_system=3;item.external_attr=((0o100755 if n.endswith('.sh') else 0o100644)<<16)
  z.writestr(item,(here/n).read_bytes(),compress_type=ZIP_DEFLATED)
 z.writestr('INSTALLER-LICENSE-GPL3', (here.parent/'fas/LICENSE').read_bytes())
 z.writestr('PROFILE-LICENSE-GPL2', (here.parents[1]/'LICENSES/preferred/GPL-2.0').read_bytes())
with ZipFile(output) as z:assert z.testzip() is None
print(output,hashlib.sha256(output.read_bytes()).hexdigest())
