"""Read twelve existing device cartridge faces for private scene review; no device writes."""
import argparse
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]


def fetch(system, output):
    if system not in ('snes', 'gb', 'gbc', 'gba', 'n64', 'nes', 'nds', 'pico8', 'megadrive', 'psx', 'psp'):
        raise ValueError('Unsupported review system')
    target = os.environ.get('SLOT_DEVICE') or (ROOT / 'tools/dev/device.txt').read_text().strip()
    # PlayStation discs carry their circular disc print; cartridges their front face.
    script = '''import tarfile,sys,json,io
from pathlib import Path
p=Path('/userdata/roms/SYSTEM/media/slotcarts')
files=[f for f in sorted(p.glob('*.disc.png'))][:12] if 'SYSTEM'=='psx' else [f for f in sorted(p.glob('*.png')) if not f.name.endswith(('.tzakol.png','.back.png','.disc.png'))][:12]
t=tarfile.open(fileobj=sys.stdout.buffer,mode='w|')
for i,f in enumerate(files):
    t.add(f,arcname=str(i)+'.png',recursive=False)
raw=json.dumps([f.stem for f in files]).encode()
info=tarfile.TarInfo('names.json');info.size=len(raw)
t.addfile(info,io.BytesIO(raw));t.close()
'''.replace('SYSTEM', system)
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
                             target, 'python3 -c ' + shlex.quote(script)], check=True, stdout=subprocess.PIPE)
    output.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
        for item in archive.getmembers():
            if not item.isfile() or '/' in item.name or '\\' in item.name or item.name not in tuple(str(i)+'.png' for i in range(12))+('names.json',):
                raise ValueError('Unexpected review input')
            (output / item.name).write_bytes(archive.extractfile(item).read())
    print('Fetched', len(json.loads((output / 'names.json').read_text())), 'private cartridge faces')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--system', default='snes')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/tabletop/faces')
    args = parser.parse_args()
    fetch(args.system, args.output)
