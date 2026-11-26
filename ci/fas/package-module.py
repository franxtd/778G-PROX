#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep the release daemon unchanged; replace only the compatibility scripts."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
import hashlib, json, sys

here=Path(__file__).resolve().parent
upstream,probe,output=map(Path,sys.argv[1:])
manifest=json.loads((here/'UPSTREAM.json').read_text())['fas_rs']
assert hashlib.sha256(upstream.read_bytes()).hexdigest()==manifest['release_sha256']
replacements={n:(here/n).read_bytes() for n in ['customize.sh','service.sh','uninstall.sh','module.prop']}
with ZipFile(upstream) as src, ZipFile(output,'w',ZIP_DEFLATED,compresslevel=9) as dst:
    daemon=src.read('fas-rs')
    assert hashlib.sha256(daemon).hexdigest()==manifest['binary_sha256']
    for item in src.infolist():
        dst.writestr(item,replacements.get(item.filename,src.read(item)),compress_type=ZIP_DEFLATED,compresslevel=9)
    for name,data in [('fas-feature-probe',probe.read_bytes()),('ram-profile.sh',(here/'ram-profile.sh').read_bytes()),
                      ('FRAN-COMPAT.md',(here/'README.md').read_bytes()),('LICENSE',(here/'LICENSE').read_bytes()),
                      ('UPSTREAM.json',(here/'UPSTREAM.json').read_bytes())]:
        info=ZipInfo(name,(2026,11,26,0,0,0));info.create_system=3
        info.external_attr=((0o100755 if name in ['fas-feature-probe','ram-profile.sh'] else 0o100644)<<16)
        dst.writestr(info,data,compress_type=ZIP_DEFLATED,compresslevel=9)
with ZipFile(output) as z:
    assert z.testzip() is None
    assert z.read('fas-rs')==daemon
print(output,hashlib.sha256(output.read_bytes()).hexdigest())
