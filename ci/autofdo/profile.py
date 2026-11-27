#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""AutoFDO provenance, profile validation and ETM conversion for this 5.4 tree."""
from pathlib import Path
import argparse, hashlib, json, re, struct, subprocess, tempfile

ROOT = Path(__file__).resolve().parents[2]
TOOLCHAIN_REVISION = '16fae8ef5b856b1d3e02a55274e4327c5842bb34'
BAKASU_REVISION = '57b2db6076f439cfd489f14576444e8f0f2f0a25'

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def run(args, **kwargs):
    return subprocess.check_output([str(x) for x in args], text=True, **kwargs)

def source_id():
    # Profile/CI/doc updates can change the commit without changing kernel code.
    lines = run(['git','ls-files','-s'], cwd=ROOT).splitlines()
    selected = [s for s in lines if not s.split('\t',1)[1].startswith(
        ('ci/','.github/','Documentation/'))]
    return hashlib.sha256(('\n'.join(selected)+'\n').encode()).hexdigest()

def elf_notes(path):
    with Path(path).open('rb') as f:
        header=f.read(64)
        if len(header)!=64 or header[:6]!=b'\x7fELF\x02\x01':
            raise ValueError('Expected ELF64 little-endian vmlinux')
        offset=struct.unpack_from('<Q',header,40)[0]
        size,count,names=struct.unpack_from('<HHH',header,58)
        if size<64 or not 0 < count < 65535 or names>=count:
            raise ValueError('Unsupported ELF section table')
        f.seek(offset);raw=f.read(size*count)
        sections=[struct.unpack_from('<IIQQQQIIQQ',raw,i*size) for i in range(count)]
        name_section=sections[names];f.seek(name_section[4]);strings=f.read(name_section[5])
        for s in sections:
            end=strings.find(b'\0',s[0])
            if strings[s[0]:end]==b'.notes':
                f.seek(s[4]);note=f.read(s[5])
                if len(note)!=s[5]:raise ValueError('Truncated notes')
                return note
    raise ValueError('Missing .notes section')

def reader(profile, profdata='llvm-profdata'):
    p = Path(profile)
    if not p.is_file() or not 0 < p.stat().st_size <= 64*1024*1024:
        raise ValueError('Profile missing, empty, or larger than 64 MiB')
    with tempfile.TemporaryDirectory() as td:
        text = Path(td)/'profile.txt'
        subprocess.run([profdata,'merge','--sample','--text',str(p),'-o',str(text)],check=True)
        headers = [re.fullmatch(r'(\S.*):([0-9]+):([0-9]+)',s)
                   for s in text.read_text().splitlines() if s and not s[0].isspace()]
        counts = [int(m[2]) for m in headers if m]
        if not counts or sum(counts) == 0:
            raise ValueError('Profile contains no nonzero top-level function samples')
        return {'functions':len(counts),'samples':sum(counts)}

def bundle(out, dest, mode='collect', profile=None):
    out, dest = Path(out).resolve(), Path(dest).resolve()
    dest.mkdir(parents=True,exist_ok=True)
    elf=out/'vmlinux'; config=out/'.config'
    actual_su=run(['git','rev-parse','HEAD'],cwd=ROOT/'KernelSU').strip()
    if actual_su!=BAKASU_REVISION:
        raise ValueError('Unexpected external BakaSU source revision')
    (dest/'kernel.notes').write_bytes(elf_notes(elf))
    note = run(['llvm-readelf','-n',elf])
    m=re.search(r'Build ID: ([0-9a-fA-F]+)',note)
    if not m: raise ValueError('No GNU build ID in vmlinux')
    for name,src in [('vmlinux',elf),('kernel.config',config),('kernel.release',out/'include/config/kernel.release')]:
        import shutil
        shutil.copyfile(src,dest/name)
    manifest={'schema':1,'mode':{'collect':'collection','profile':'optimized','off':'off'}[mode],'source_id':source_id(),
              'source_commit':run(['git','rev-parse','HEAD'],cwd=ROOT).strip(),
              'config_sha256':sha(config),'vmlinux_sha256':sha(elf),
              'image_sha256':sha(out/'arch/arm64/boot/Image'),
              'kernel_notes_sha256':sha(dest/'kernel.notes'),'build_id':m[1].lower(),
              'toolchain_revision':TOOLCHAIN_REVISION,
              'bakasu_revision':actual_su,
              'profile_applied':mode=='profile','device_trace_collected':mode=='profile'}
    if mode=='profile':
        if not profile:raise ValueError('Profile required for optimized mode')
        manifest['applied_profile']=validate(profile,config)
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

def convert(trace, symbols, output):
    trace, symbols, output=map(lambda p:Path(p).resolve(),[trace,symbols,output])
    m=json.loads((symbols/'manifest.json').read_text())
    if sha(trace/'kernel.notes')!=m['kernel_notes_sha256']:
        raise ValueError('Device trace and symbol bundle have different kernel build IDs')
    if sha(symbols/'vmlinux')!=m['vmlinux_sha256']:
        raise ValueError('Symbol ELF hash mismatch')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        raw=Path(td)/'kernel.autofdo'; afdo=Path(td)/'kernel.afdo'
        subprocess.run(['simpleperf','inject','-i',str(trace/'branch.data'),
            '--binary','kernel.kallsyms','--symdir',str(symbols),'-o',str(raw)],check=True)
        if not raw.is_file() or not raw.stat().st_size:
            raise ValueError('No kernel branch ranges found')
        subprocess.run(['create_llvm_prof','--profiler=text',f'--binary={symbols / "vmlinux"}',
                        f'--profile={raw}',f'--out={afdo}','--format=extbinary'],check=True)
        stats=reader(afdo)
        import shutil
        shutil.copyfile(afdo,output)
    m.update({'mode':'device-profile','profile_applied':False,'device_trace_collected':True,
              'trace_sha256':sha(trace/'branch.data'),'profile_sha256':sha(output),**stats})
    output.with_suffix(output.suffix+'.json').write_text(json.dumps(m,indent=2)+'\n')
    return m

def validate(profile, config):
    profile=Path(profile).resolve()
    m=json.loads(profile.with_suffix(profile.suffix+'.json').read_text())
    if m.get('mode')!='device-profile' or m.get('device_trace_collected') is not True:
        raise ValueError('A real device-profile manifest is required')
    for key,expected in [('profile_sha256',sha(profile)),('source_id',source_id()),
                         ('config_sha256',sha(config)),('toolchain_revision',TOOLCHAIN_REVISION),
                         ('bakasu_revision',BAKASU_REVISION)]:
        if m.get(key)!=expected:raise ValueError(f'Profile provenance mismatch: {key}')
    return {**reader(profile),'sha256':sha(profile),'source_id':m['source_id']}

def main():
    a=argparse.ArgumentParser();s=a.add_subparsers(dest='command',required=True)
    p=s.add_parser('bundle');p.add_argument('out');p.add_argument('destination');p.add_argument('--mode',choices=['collect','profile','off'],default='collect');p.add_argument('--profile')
    p=s.add_parser('convert');p.add_argument('trace');p.add_argument('symbols');p.add_argument('output')
    p=s.add_parser('validate');p.add_argument('profile');p.add_argument('config')
    args=a.parse_args()
    if args.command=='bundle':r=bundle(args.out,args.destination,args.mode,args.profile)
    elif args.command=='convert':r=convert(args.trace,args.symbols,args.output)
    else:r=validate(args.profile,args.config)
    print(json.dumps(r,indent=2))
if __name__=='__main__':main()
