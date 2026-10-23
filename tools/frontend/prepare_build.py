"""Prepare a fresh pinned H700 build workspace; never installs packages or deploys."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import re
import struct
import subprocess
import sys
import tarfile
import urllib.request

from tools.frontend.apply import PIN, apply

ROOT=Path(__file__).resolve().parents[2]
REPOSITORY='https://github.com/knulli-cfw/batocera-emulationstation.git'
LIBRARIES=('libasound.so.2','libcurl.so.4','libespeak.so.1','libfreeimage.so.3',
           'libfreetype.so.6','libmali.so','libpulse.so.0','libSDL2_image-2.0.so.0',
           'libSDL2_mixer-2.0.so.0','libSDL2-2.0.so.0','libudev.so.1','libvlc.so.5')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def aarch64(path):
    with Path(path).open('rb') as stream:data=stream.read(20)
    if len(data)!=20 or data[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',data,18)[0]!=183:
        raise ValueError('Expected an AArch64 ELF library: '+Path(path).name)

def verify_workspace(work):
    work=Path(work).resolve();record=json.loads((work/'build-inputs.json').read_text())
    if record['sourcePin']!=PIN:raise ValueError('Unsupported prepared frontend source pin')
    for entry in record['inputs']:
        path=Path(record['libraries'])/entry['name'] if entry['kind'] in ('target-library','linker-script') else work/'packages'/entry['filename']
        if sha(path)!=entry['sha256']:raise ValueError('Prepared build input changed: '+path.name)
        if entry['kind']=='target-library':aarch64(path)
    for kind,base in [('headerHashes',work/'headers'),('sdlHeaderHashes',Path(record['sdlHeaders']))]:
        for name,expected in record[kind].items():
            if sha(base/name)!=expected:raise ValueError('Prepared API header changed: '+name)
    if record['sourcePrepared']:
        source=work/'frontend'
        if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=PIN:
            raise ValueError('Prepared source revision changed')
        modules=subprocess.check_output(['git','-C',str(source),'submodule','status','--recursive'],text=True).splitlines()
        if modules!=record['submodules']:raise ValueError('Prepared source submodules changed')
        owned=json.loads((source/'.git/slot-presentation-output.json').read_text())
        for name,expected in owned.items():
            if sha(source/name)!=expected:raise ValueError('Patched frontend source changed: '+name)
    return dict(state='verified-build-inputs',sourcePin=PIN,inputs=len(record['inputs']))

def record_build(work):
    work=Path(work).resolve();result=verify_workspace(work);binary=work/'frontend/emulationstation';aarch64(binary)
    result.update(state='built-not-installed',frontendSha256=sha(binary),buildInputsSha256=sha(work/'build-inputs.json'),
                  compiler=subprocess.check_output(['aarch64-linux-gnu-g++','--version'],text=True).splitlines()[0])
    (work/'native-build.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def checked_download(url,path,expected):
    if not url.startswith('https://'):raise ValueError('Use HTTPS for build inputs')
    if not path.exists():
        with urllib.request.urlopen(url,timeout=60) as source,path.open('xb') as target:
            shutil.copyfileobj(source,target)
    if sha(path)!=expected:raise ValueError('Build input SHA-256 differs: '+path.name)

def sdl_headers(archive,work,version):
    prefix='SDL-release-'+version
    with tarfile.open(archive) as tar:
        for member in tar:
            name=PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or '\\' in member.name:
                raise ValueError('Unsafe SDL archive path')
            if not (member.name.startswith(prefix+'/include/') or member.name==prefix+'/LICENSE.txt'):
                continue
            if member.isdir():continue
            if not member.isfile():raise ValueError('Linked SDL header is not supported')
            target=work.joinpath(*name.parts);target.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(member) as source,target.open('xb') as output:shutil.copyfileobj(source,output)
    include=work/prefix/'include'
    if not (include/'SDL.h').is_file():raise ValueError('SDL archive lacks public headers')
    shutil.copy2(include/'SDL_config_minimal.h',include/'SDL_config.h')
    return include

def prepare(output,libraries,packages=None,download=False,clone=True,lock=None):
    output=Path(output).absolute();libraries=Path(libraries).resolve()
    if output.exists() or output.is_symlink():raise FileExistsError('Use a new build workspace: '+str(output))
    if output.resolve()==ROOT or ROOT.is_relative_to(output.resolve()):raise ValueError('Build workspace may not contain the project')
    if packages is None and not download:raise ValueError('Choose --packages or --download-headers')
    config=json.loads(Path(lock or ROOT/'release/frontend-headers.json').read_text())
    # Preflight target libraries and supplied packages before creating anything.
    for name in LIBRARIES:aarch64(libraries/name)
    if packages:
        packages=Path(packages).resolve()
        for record in config['packages']:
            if sha(packages/record['filename'])!=record['sha256']:
                raise ValueError('Header package SHA-256 differs: '+record['filename'])
    for tool in ('git','cmake','pkg-config','dpkg-deb','aarch64-linux-gnu-gcc','aarch64-linux-gnu-g++','aarch64-linux-gnu-readelf'):
        if not shutil.which(tool):raise ValueError('Missing build tool: '+tool)
    output.mkdir(parents=True);cache=output/'packages';cache.mkdir();headers=output/'headers';headers.mkdir()
    lib=output/'lib';lib.mkdir();inputs=[]
    for name in LIBRARIES:
        shutil.copy2(libraries/name,lib/name)
        if sha(libraries/name)!=sha(lib/name):raise OSError('Target library copy differs: '+name)
        dynamic=subprocess.check_output(['aarch64-linux-gnu-readelf','-d',str(lib/name)],text=True)
        soname=re.search(r'\(SONAME\).*?\[([^\]]+)\]',dynamic)
        if not soname:raise ValueError('Target library has no SONAME: '+name)
        inputs.append(dict(kind='target-library',name=name,runtimeName=soname[1],sha256=sha(lib/name)))
    # The firmware's Mali library provides both GLES and EGL. Satisfy upstream's
    # -lEGL without redistributing a firmware wrapper or another driver library.
    egl=lib/'libEGL.so';egl.write_text('INPUT ( -l:libmali.so )\n')
    inputs.append(dict(kind='linker-script',name='libEGL.so',sha256=sha(egl)))
    for record in config['packages']:
        target=cache/record['filename']
        if packages:shutil.copy2(packages/record['filename'],target)
        else:checked_download(record['url'],target,record['sha256'])
        subprocess.run(['dpkg-deb','--extract',str(target),str(headers)],check=True)
        inputs.append(dict(kind='header-package',**record))
    sdl=config['sdl'];archive=cache/'SDL-headers.tar.gz'
    checked_download(sdl['url'],archive,sdl['sha256'])
    include=sdl_headers(archive,output,sdl['version'])
    shutil.copy2(include/'SDL_config_minimal.h',headers/'usr/include/SDL2/SDL_config.h')
    (headers/'usr/include/KHR').mkdir(exist_ok=True)
    shutil.copy2(include/'SDL_opengles2_khrplatform.h',headers/'usr/include/KHR/khrplatform.h')
    frontend=output/'frontend'
    if clone:
        subprocess.run(['git','init','--quiet',str(frontend)],check=True)
        subprocess.run(['git','-C',str(frontend),'remote','add','origin',REPOSITORY],check=True)
        subprocess.run(['git','-C',str(frontend),'fetch','--depth=1','origin',PIN],check=True)
        subprocess.run(['git','-C',str(frontend),'checkout','--detach','FETCH_HEAD'],check=True)
        subprocess.run(['git','-C',str(frontend),'submodule','update','--init','--recursive','--depth=1'],check=True)
        apply(frontend)
    receipt=dict(schema=1,sourcePin=PIN,repository=REPOSITORY,sourcePrepared=clone,
                 headerLockSha256=sha(lock or ROOT/'release/frontend-headers.json'),sdl=sdl,
                 inputs=inputs,headers=str(headers/'usr/include'),libraries=str(lib),sdlHeaders=str(include),
                 state='prepared-not-built',firmwareLibraries='User-supplied; not redistributed by this tool')
    if clone:
        receipt['submodules']=subprocess.check_output(['git','-C',str(frontend),'submodule','status','--recursive'],text=True).splitlines()
    receipt['headerHashes']={p.relative_to(headers).as_posix():sha(p) for p in sorted((headers/'usr/include').rglob('*')) if p.is_file()}
    receipt['sdlHeaderHashes']={p.relative_to(include).as_posix():sha(p) for p in sorted(include.rglob('*')) if p.is_file()}
    (output/'build-inputs.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path);p.add_argument('--libraries',type=Path)
    group=p.add_mutually_exclusive_group();group.add_argument('--packages',type=Path);group.add_argument('--download-headers',action='store_true')
    p.add_argument('--verify',type=Path);p.add_argument('--record-build',type=Path)
    p.add_argument('--no-clone',action='store_true');args=p.parse_args()
    if args.verify:result=verify_workspace(args.verify)
    elif args.record_build:result=record_build(args.record_build)
    else:
        if not args.output or not args.libraries or not (args.packages or args.download_headers):p.error('Provide --output, --libraries and --packages or --download-headers')
        result=prepare(args.output,args.libraries,args.packages,args.download_headers,not args.no_clone)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
