"""Private device feasibility probes, with snapshot/restore and no frontend install.

python tools/tabletop/device_probe.py boot --mode show --frames 450
python tools/tabletop/device_probe.py scene --tv panasonic
"""
import argparse
import io
import json
import os
import re
from pathlib import Path
import shlex
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
DEVICE = '/userdata/system/slot-dev/tabletop-20261018'
SNAPSHOT = 'tabletop-20261018a'


class Remote:
    def __init__(self):
        self.target = os.environ.get('SLOT_DEVICE') or (ROOT / 'tools/dev/device.txt').read_text().strip()

    def run(self, args, timeout=90):
        return subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', self.target,
                               shlex.join(map(str, args))], check=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout).stdout

    def python(self, source, timeout=90):
        return self.run(['python3', '-c', source], timeout)

    def copy(self, source, target):
        subprocess.run(['scp', '-o', 'BatchMode=yes', '-q', str(source), self.target + ':' + target], check=True, timeout=90)


def fetch(remote, folder, output):
    source = '''import tarfile,sys
from pathlib import Path
p=Path(FOLDER)
t=tarfile.open(fileobj=sys.stdout.buffer,mode='w|')
for f in sorted(p.iterdir()):
    if f.is_file() and f.suffix in ('.ppm','.json','.tsv','.s16le','.bmp','.log'):
        t.add(f,arcname=f.name,recursive=False)
t.close()
'''.replace('FOLDER', repr(folder))
    data = remote.python(source)
    output.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for entry in archive:
            if not entry.isfile() or '/' in entry.name or '\\' in entry.name or entry.name in ('.', '..'):
                raise ValueError('Invalid probe result')
            (output / entry.name).write_bytes(archive.extractfile(entry).read())


def boot(remote, args):
    remote.copy(ROOT / 'build/tabletop/slot-boot', DEVICE + '/slot-boot')
    tag = args.tag or args.mode
    work = DEVICE + '/boot-' + tag
    source = '''import json,hashlib,shutil,subprocess,os
from pathlib import Path
work=Path(WORK)
work.mkdir(exist_ok=False)
for name in ('bios','saves','output'):(work/name).mkdir()
bios={}
for p in sorted(Path('/userdata/bios').glob('scph*.bin')):
    shutil.copy2(p,work/'bios'/p.name)
    bios[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
content=next(iter(sorted(Path('/userdata/roms/psx').glob('*.chd'))))
binary=Path(BINARY);binary.chmod(0o755)
command=[str(binary),'/usr/lib/libretro/pcsx_rearmed_libretro.so',str(work/'bios'),str(work/'saves'),str(content),str(work/'output'),str(FRAMES),MODE]
result=subprocess.run(command,cwd=work,env=dict(os.environ,HOME=str(work),XDG_DATA_HOME=str(work/'data'),XDG_CONFIG_HOME=str(work/'config')),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=75)
(work/'output/probe.log').write_bytes(result.stdout)
after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/userdata/bios').glob('scph*.bin')}
assert after==bios,'User firmware changed'
(work/'output/isolation.json').write_text(json.dumps(dict(firmware_unchanged=True,private_save_directory=True,content=str(content),core_sha256=hashlib.sha256(Path('/usr/lib/libretro/pcsx_rearmed_libretro.so').read_bytes()).hexdigest(),returncode=result.returncode)))
print(json.dumps(dict(returncode=result.returncode,firmware_unchanged=True)))
'''
    for key, value in dict(WORK=repr(work), BINARY=repr(DEVICE + '/slot-boot'), FRAMES=str(args.frames), MODE=repr(args.mode)).items():
        source = source.replace(key, value)
    print(remote.python(source).decode().strip())
    output = ROOT / 'build/tabletop' / ('boot-' + tag)
    fetch(remote, work + '/output', output)
    report = json.loads((output / 'isolation.json').read_text())
    if report['returncode']:
        print((output / 'probe.log').read_text(errors='replace')[-1800:])
        raise RuntimeError('Boot capture failed; device restored by finally block')
    print((output / 'capture.json').read_text().strip())


def scene(remote, args):
    remote.copy(ROOT / 'build/tabletop/probe-arm64', DEVICE + '/scene-probe')
    archive = ROOT / 'build/tabletop/prepared.tar'
    with tarfile.open(archive, 'w') as tar:
        for path in (ROOT / 'build/tabletop/assets').rglob('*'):
            if path.is_file():
                tar.add(path, arcname=path.relative_to(ROOT / 'build/tabletop/assets').as_posix())
    remote.copy(archive, DEVICE + '/prepared.tar')
    tag = args.tag or args.tv
    work = DEVICE + '/scene-' + tag
    source = '''import json,tarfile,subprocess,os
from pathlib import Path
base=Path(BASE);work=Path(WORK);work.mkdir(exist_ok=False)
assets=base/'assets';assets.mkdir(exist_ok=True)
with tarfile.open(base/'prepared.tar') as archive:
    for m in archive:
        target=assets/m.name
        assert m.isfile() and target.resolve().is_relative_to(assets.resolve())
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.extractfile(m).read())
binary=base/'scene-probe';binary.chmod(0o755)
faces=[str(f) for f in sorted(Path('/userdata/roms/snes/media/slotcarts').glob('*.png')) if not f.name.endswith(('.tzakol.png','.back.png'))][:COUNT]
env=dict(os.environ,SLOT_BENCH='1',SLOT_SCENE_CARTRIDGES=str(COUNT))
if ALLOW_CLIP:env['SLOT_SCENE_ALLOW_CLIP']='1'
result=subprocess.run([str(binary),'/userdata/themes/art-book-slot/_slot',str(assets),str(work/'scene.bmp'),'snes',TV]+faces,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
(work/'probe.log').write_bytes(result.stdout)
print(json.dumps(dict(returncode=result.returncode)))
'''
    for key, value in dict(BASE=repr(DEVICE), WORK=repr(work), TV=repr(args.tv), COUNT=str(args.cartridges), ALLOW_CLIP=repr(args.allow_clip)).items():
        source = source.replace(key, value)
    result = json.loads(remote.python(source).decode())
    output = ROOT / 'build/tabletop/device' / tag
    fetch(remote, work, output)
    print((output / 'probe.log').read_text(errors='replace')[-1600:])
    if result['returncode']:
        raise RuntimeError('Scene probe failed; device restored by finally block')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', choices=('boot', 'scene'))
    parser.add_argument('--mode', choices=('show', 'skip'), default='show')
    parser.add_argument('--tv', choices=('panasonic', 'retro', 'pvm'), default='panasonic')
    parser.add_argument('--frames', type=int, default=450)
    parser.add_argument('--cartridges', type=int, choices=(8,12), default=8)
    parser.add_argument('--allow-clip', action='store_true', help='Report intentional authored crops without changing the camera')
    parser.add_argument('--tag', help='Unique private result name for a repeated boot or scene experiment')
    args = parser.parse_args()
    if not 1 <= args.frames <= 900:
        parser.error('Use 1..900 frames for the isolated feasibility probe')
    if args.tag and not re.fullmatch('[a-z0-9-]{1,32}', args.tag):
        parser.error('Tag must be 1..32 lowercase letters/digits/hyphens')
    remote = Remote()
    status = remote.run(['python3', '/userdata/system/slot-dev/esdev.py', 'status']).decode()
    if 'NO GAME RUNNING' not in status:
        raise RuntimeError('A game may be running; refusing to interrupt it')
    remote.run(['python3', '/userdata/system/slot-dev/esdev.py', 'stop'])
    try:
        exists = remote.python("from pathlib import Path;print(int(Path('/userdata/system/slot-dev/sessions/" + SNAPSHOT + "').exists()))").strip() == b'1'
        if not exists:
            print(remote.run(['python3', '/userdata/system/slot-dev/session_data.py', 'backup', SNAPSHOT]).decode().strip())
        remote.run(['mkdir', '-p', DEVICE])
        {'boot': boot, 'scene': scene}[args.probe](remote, args)
    finally:
        # Probes write only their private dev directory. Avoid rewriting 231 MB
        # of unchanged user/runtime files when the hash audit is already clean.
        try:
            try:
                print(remote.run(['python3', '/userdata/system/slot-dev/session_data.py', 'audit', SNAPSHOT, '--runtime']).decode().strip())
            except subprocess.CalledProcessError:
                print(remote.run(['python3', '/userdata/system/slot-dev/session_data.py', 'restore', SNAPSHOT, '--runtime']).decode().strip())
                print(remote.run(['python3', '/userdata/system/slot-dev/session_data.py', 'audit', SNAPSHOT, '--runtime']).decode().strip())
        finally:
            remote.run(['python3', '/userdata/system/slot-dev/esdev.py', 'start'])


if __name__ == '__main__':
    main()
