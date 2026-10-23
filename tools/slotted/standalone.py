"""Build a complete Slotted theme/runtime bundle from a verified public checkout.

No device access. Firmware libraries, ROMs, BIOS, settings and saves are excluded.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile

from tools.frontend.apply import PIN
from tools.frontend.prepare_build import aarch64,sha,LIBRARIES
from tools.publication.export import verify,safe_file,relative
from tools.slot_theme import H700_RUNTIME_LIBRARIES
from tools.slotted.runtime import REQUIRED,validate as validate_runtime

MARKERS=(b'SLOTTED_ROOM1:SLOTHOME1,SLOTWORLD1,SLOTWORLD2',
         b'SLOTTED_ROOM_FEATURES1:motion,crt,controller-devicepath')

def payload_files(root,manifest):
    """Approved public paths only; no broad walk of the dirty development checkout."""
    selected={}
    for name in manifest['files']:
        if name.startswith('theme/slotted/'):
            target=name[len('theme/slotted/'):]
        elif name.startswith('theme/art-book-slot/_slot/'):
            target=name[len('theme/art-book-slot/'):]
        elif name.startswith('assets/tabletop/'):
            target='_slot/tabletop/'+name[len('assets/tabletop/'):]
        elif name in ('LICENSE','CREDITS.md','LICENSE_SCOPE.md','docs/PUBLIC_ASSET_REMEDIATION.md') or name.startswith('LICENSES/'):
            target='_licenses/'+name
        else:continue
        key=PurePosixPath(target)
        if key.is_absolute() or '..' in key.parts or 'local-models' in key.parts:
            raise ValueError('Unsafe standalone asset path: '+target)
        if target in selected:raise ValueError('Conflicting runtime asset: '+target)
        selected[target]=safe_file(root,name)
    return selected

def saved_layouts(root,manifest):
    from tools.tabletop.editor import profiles,room
    result={}
    for name in sorted(manifest['files']):
        p=PurePosixPath(name)
        if len(p.parts)!=2 or p.parts[0]!='scene-layouts' or p.suffix!='.json':continue
        value=json.loads(safe_file(root,name).read_text())
        if value.get('kind') in ('room','home'):
            key=room.profile_key(value);content=room.native_text(value)
            target='_slot/tabletop/layouts/'+key+('.world' if key=='room' else '.scene')
        elif 'system' in value:
            profile=profiles.validate(value);target='_slot/tabletop/layouts/'+profile['system']+'-'+profile['tv']+'.scene'
            content=profiles.native_text(profile)
        else:continue
        data=content.encode('utf-8')
        if target in result and result[target]!=data:raise ValueError('Conflicting authored layouts: '+target)
        result[target]=data
    return result

def package(root,frontend,helper,output):
    root=Path(root).resolve();frontend=Path(frontend).resolve();helper=Path(helper).resolve();output=Path(output).absolute()
    if output.exists() or output.is_symlink():raise FileExistsError('Use a new standalone output folder')
    verified=verify(root)
    aarch64(frontend);aarch64(helper)
    data=frontend.read_bytes()
    if not all(marker in data for marker in MARKERS):raise ValueError('Frontend lacks current Slotted room capabilities')
    workspace=frontend.parent.parent
    built=json.loads((workspace/'native-build.json').read_text())
    inputs=json.loads((workspace/'build-inputs.json').read_text())
    if built['frontendSha256']!=sha(frontend) or built['sourcePin']!=PIN or built['buildInputsSha256']!=sha(workspace/'build-inputs.json'):
        raise ValueError('Frontend and prepared build receipt differ')
    helper_receipt=json.loads(helper.with_suffix(helper.suffix+'.json').read_text())
    if (helper_receipt['sha256']!=sha(helper) or helper_receipt['sourcePin']!=PIN
        or helper_receipt['buildInputsSha256']!=sha(workspace/'build-inputs.json')):
        raise ValueError('Helper and prepared build receipt differ')
    runtime={r['runtimeName']:r['sha256'] for r in inputs['inputs'] if r['kind']=='target-library'}
    if set(runtime)!=set(H700_RUNTIME_LIBRARIES):raise ValueError('Build receipt lacks required target library hashes')
    manifest=json.loads((root/'PUBLICATION_MANIFEST.json').read_text())
    selected=payload_files(root,manifest);selected['_slot/launch/slot-launch']=helper
    selected.update(saved_layouts(root,manifest))
    for relative_name,source_name in [('pugixml-MIT.txt','pugixml/LICENSE.md'),('id3v2lib-BSD.txt','id3v2lib/LICENSE'),
             ('rcheevos-MIT.txt','libcheevos/rcheevos/LICENSE'),('nanosvg-zlib.txt','nanosvg/nanosvg_license.txt')]:
        selected['_licenses/vendor/'+relative_name]=workspace/'frontend/external'/source_name
    def read(name):
        value=selected[name]
        return value if isinstance(value,bytes) else value.read_bytes()
    validate_runtime(selected,read)
    for value in selected.values():
        if not isinstance(value,bytes) and not value.is_file():raise ValueError('Missing runtime input: '+value.name)
    output.mkdir(parents=True);records={}
    with tarfile.open(output/'payload.tar','w') as archive:
        for name,path in sorted(selected.items()):
            content=path if isinstance(path,bytes) else path.read_bytes();digest=hashlib.sha256(content).hexdigest()
            mode=0o755 if path==helper or (not isinstance(path,bytes) and path.suffix in ('.sh','.py')) else 0o644
            entry=tarfile.TarInfo(name);entry.size=len(content);entry.mode=mode;entry.mtime=0
            archive.addfile(entry,io.BytesIO(content));records[name]=dict(sha256=digest,bytes=len(content),mode=mode)
    shutil.copy2(frontend,output/'frontend-candidate')
    (output/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    release=dict(schema=1,kind='slotted-standalone',state='packaged-not-installed',completeRuntime=True,
        sourcePin=PIN,publicManifestSha256=sha(root/'PUBLICATION_MANIFEST.json'),publicSourceFiles=verified['files'],
        frontendSha256=sha(output/'frontend-candidate'),helperSha256=sha(helper),payloadSha256=sha(output/'payload.tar'),
        runtimeLibraryHashes=runtime,compiler=built['compiler'],
        files=len(records),firmwareLibrariesBundled=False,
        licenses='MIT original code; separate CC/OFL/CC0 assets including NonCommercial/ShareAlike. See _licenses/.')
    (output/'release.json').write_text(json.dumps(release,indent=2)+'\n')
    inspect(output)
    return release

def inspect(bundle):
    bundle=Path(bundle).resolve();release=json.loads((bundle/'release.json').read_text());manifest=json.loads((bundle/'manifest.json').read_text())
    if release.get('kind')!='slotted-standalone' or release.get('sourcePin')!=PIN or not release.get('completeRuntime'):
        raise ValueError('Unsupported standalone bundle')
    if set(release.get('runtimeLibraryHashes',{}))!=set(H700_RUNTIME_LIBRARIES):raise ValueError('Standalone runtime dependency record is incomplete')
    if sha(bundle/'payload.tar')!=release['payloadSha256'] or sha(bundle/'frontend-candidate')!=release['frontendSha256']:
        raise ValueError('Standalone bundle checksum differs')
    aarch64(bundle/'frontend-candidate')
    if not all(m in (bundle/'frontend-candidate').read_bytes() for m in MARKERS):raise ValueError('Frontend capabilities differ')
    if not set(REQUIRED)<=set(manifest):raise ValueError('Standalone bundle lacks required runtime assets')
    seen=set()
    with tarfile.open(bundle/'payload.tar') as archive:
        for member in archive:
            name=member.name;path=PurePosixPath(name)
            relative(name)
            if (not member.isfile() or path.is_absolute() or '..' in path.parts or '\\' in name
                or 'local-models' in path.parts or name in seen or name not in manifest):
                raise ValueError('Unsafe/duplicate standalone archive path: '+name)
            seen.add(name);record=manifest[name]
            content=archive.extractfile(member).read()
            if len(content)!=record['bytes'] or hashlib.sha256(content).hexdigest()!=record['sha256'] or member.mode!=record['mode']:
                raise ValueError('Standalone member checksum/mode differs: '+name)
            if member.mode not in (0o644,0o755):raise ValueError('Unsupported standalone file mode: '+name)
            if name=='_slot/launch/slot-launch':
                if (hashlib.sha256(content).hexdigest()!=release['helperSha256'] or member.mode!=0o755
                    or content[:6]!=b'\x7fELF\x02\x01' or content[18:20]!=b'\xb7\x00'):
                    raise ValueError('Standalone helper ABI/checksum differs')
        validate_runtime(manifest,lambda name:archive.extractfile(name).read())
    if seen!=set(manifest):raise ValueError('Standalone archive and manifest differ')
    return release

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path)
    p.add_argument('--frontend',type=Path);p.add_argument('--helper',type=Path);p.add_argument('--output',type=Path)
    p.add_argument('--inspect',type=Path);a=p.parse_args()
    if a.inspect:result=inspect(a.inspect)
    else:
        if not all((a.source,a.frontend,a.helper,a.output)):p.error('Provide --source, --frontend, --helper and --output')
        result=package(a.source,a.frontend,a.helper,a.output)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
