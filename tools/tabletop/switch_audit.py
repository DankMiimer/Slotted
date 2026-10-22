"""Read-only baseline for seamless system-switch research; never stops ES."""
import hashlib
import json
from pathlib import Path

from tools.tabletop.device_probe import Remote, ROOT

OUTPUT = ROOT / 'build/system-switch-research-20261020'


def host_inventory():
    paths = set()
    for folder in ('scene-layouts', 'third_party/models', 'research/selected-cartridges-20261019',
                   'theme/art-book-slot/_slot/consoles', 'theme/art-book-slot/_slot/local-models'):
        paths.update(p for p in (ROOT / folder).rglob('*') if p.is_file())
    paths.update(p for p in (ROOT / 'tools/frontend').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


DEVICE_AUDIT = r'''
import hashlib, json, pathlib, subprocess, urllib.request
p=pathlib.Path
pid=subprocess.run(['pidof','emulationstation'],capture_output=True,text=True).stdout.strip().split()
pid=pid[0] if pid else None
root=p('/userdata/themes/art-book-slot/_slot')
layouts={f.name:dict(sha256=hashlib.sha256(f.read_bytes()).hexdigest(),text=f.read_text()) for f in sorted((root/'tabletop/layouts').glob('*.scene'))}
def entries(folder):
    return {str(f.relative_to(root)):f.stat().st_size for f in folder.rglob('*') if f.is_file() and f.suffix in ('.mesh','.png','.texture','.control','.pose','.txt')}
with urllib.request.urlopen('http://127.0.0.1:1234/runningGame',timeout=3) as r: game=json.load(r)
print(json.dumps(dict(pid=pid,runningGame=game,meminfo=p('/proc/meminfo').read_text(),
    status=p('/proc/'+pid+'/status').read_text() if pid else '',
    frontendSha256=hashlib.sha256(p('/usr/bin/emulationstation').read_bytes()).hexdigest(),
    layouts=layouts,prepared=entries(root/'tabletop'),consoles=entries(root/'consoles'),
    glEnvironment=[x.decode(errors='replace') for x in p('/proc/'+pid+'/environ').read_bytes().split(b'\0') if x.startswith((b'SLOT_',b'SDL_'))] if pid else [])))
'''


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    before = OUTPUT / 'protected-host-before.json'
    if not before.exists():
        before.write_text(json.dumps(host_inventory(), indent=2)+'\n')
    result = json.loads(Remote().python(DEVICE_AUDIT, 45))
    (OUTPUT / 'read-only-device-audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(pid=result['pid'], runningGame=result['runningGame'],
        frontendSha256=result['frontendSha256'],layouts=len(result['layouts']),
        memory=[x for x in result['meminfo'].splitlines() if x.startswith(('MemTotal','MemAvailable','SwapTotal','SwapFree'))],
        process=[x for x in result['status'].splitlines() if x.startswith(('VmRSS','VmHWM','Threads'))],
        protectedHostFiles=len(json.loads(before.read_text()))),indent=2))


if __name__ == '__main__':
    main()
