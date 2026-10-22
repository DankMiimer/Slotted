"""Freeze and dispatch the selected cartridge-only device transaction. MIT.

Run after the private device validation. Does not export editor profiles or
deploy a frontend; all recovery records and the immutable payload are retained.
"""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import time
from .selected_cartridges import ROOT, SLOT, KEYS
from tools.tabletop.device_probe import Remote

NAMES = ('media.mesh', 'media.texture', 'media.albedo.png', 'media-label.mesh',
         'media-label.texture', 'media-label.albedo.png', 'media-info.json', 'media-registration.json')


def main():
    validation = json.loads((ROOT/'build/cartridge-validation-20261019/device-report.json').read_text())
    if not validation.get('frontend_ready') or len(validation.get('results', [])) != 24 or any(r['exit'] for r in validation['results']):
        raise ValueError('Complete private device validation required')
    if any(v['changed'] or v['new'] for v in validation['audit'].values()):
        raise ValueError('Validation audit was not clean')
    session = 'cartridges-'+time.strftime('%Y%m%d-%H%M%S')
    out = ROOT/'build/cartridge-installation-20261019'/session
    out.mkdir(parents=True, exist_ok=False)
    remote = '/userdata/system/slot-dev/cartridge-installation/'+session
    payload = {'_slot/consoles/'+key+'/'+name:(SLOT/'consoles'/key/name).read_bytes() for key in KEYS for name in NAMES}
    payload['_slot/MODEL_CREDITS.txt'] = (SLOT/'MODEL_CREDITS.txt').read_bytes()
    manifest = {name:dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)) for name, data in payload.items()}
    r = Remote()
    # Capture the precise stale sidecar; the device worker proves its fresh
    # snapshot copy before removing it. Full-detail originals remain untouched.
    stale = '_slot/consoles/gba/media.paint.mask'
    state = json.loads(r.python('import json,hashlib\nfrom pathlib import Path\np=Path('+repr('/userdata/themes/art-book-slot/'+stale)+')\nprint(json.dumps(dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None)))'))
    config = dict(session=session, files=manifest, frontendSha256=validation['frontend_sha256'],
                  remove={stale:state['sha256']} if state['sha256'] else {}, remote=remote)
    for name, obj in (('request.json', config), ('manifest.json', manifest)):
        (out/name).write_text(json.dumps(obj, indent=2)+'\n')
    with tarfile.open(out/'payload.tar', 'w') as archive:
        for name, data in payload.items():
            member = tarfile.TarInfo(name); member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    r.run(['mkdir', '-p', remote])
    for p, name in ((out/'request.json', 'request.json'), (out/'payload.tar', 'payload.tar'),
                    (ROOT/'tools/tabletop/cartridge_device_install.py', 'worker.py')):
        r.copy(p, remote+'/'+name)
    r.python('import subprocess,sys\nfrom pathlib import Path\np=Path('+repr(remote)+')\nwith (p/"worker.log").open("wb") as log:\n subprocess.Popen([sys.executable,str(p/"worker.py"),str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)')
    print(json.dumps(dict(session=session, local=str(out), remote=remote, files=len(manifest))))


if __name__ == '__main__':
    main()
