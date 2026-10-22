"""Binary-only install using the editor's verified snapshot/persistence transaction."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
import tarfile
import time
import uuid
from tools.tabletop.device_probe import Remote, ROOT
from tools.slot_theme import DEVICE_THEMES

BASE = ROOT/os.environ.get('SLOT_TRANSITION_BUILD', 'build/system-switch-implementation-20261020')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    remote = Remote()
    if args.fetch:
        saved = json.loads((BASE/'install-job.json').read_text())
        value = remote.python('from pathlib import Path\nprint((Path('+repr(saved['job'])+")/'status.json').read_text())")
        (BASE/saved['session']/'status.json').write_bytes(value)
        print(value.decode())
        return
    session = os.environ.get('SLOT_TRANSITION_VERSION', 'transition-n17')+'-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    job = '/userdata/system/slot-dev/editor-uploads/'+session
    local = BASE/session
    local.mkdir()
    with tarfile.open(local/'payload.tar', 'w'):
        pass  # Empty, explicit ownership: no models, layouts, labels or settings.
    (local/'manifest.json').write_text('{}\n')
    binary = (BASE/'frontend-candidate' if (BASE/'frontend-candidate').is_file() else BASE/'frontend-n17-candidate')
    sha = hashlib.sha256(binary.read_bytes()).hexdigest()
    config = dict(session=session, system='nes', tv='panasonic', preview=False, files={},
                  frontendSha256=sha, sourceSha256=hashlib.sha256((BASE/'owned-source.json').read_bytes()).hexdigest())
    # Binary-only installation also supports Slotted; the device worker rechecks
    # this active theme immediately before stopping the frontend.
    state=json.loads(remote.python("""import json,sys
sys.path.insert(0,'/userdata/system/slot-dev');import esdev
assert esdev.es_pid(),'Return to the frontend first'
assert json.loads(esdev.api('/runningGame'))=={'msg':'NO GAME RUNNING'},'Close the running game first'
print(json.dumps(dict(theme=esdev.get('ThemeSet'))))
"""))
    if state['theme'] not in DEVICE_THEMES:raise ValueError('Select Slotted or art-book-slot first')
    config['theme']=state['theme']
    (local/'request.json').write_text(json.dumps(config, indent=2)+'\n')
    files = {name:local/name for name in ('payload.tar', 'manifest.json', 'request.json')}
    files.update(frontend=binary, device_upload=ROOT/'tools/tabletop/editor/device_upload.py')
    files['device_upload.py'] = files.pop('device_upload')
    for name in ('session_data.py', 'esdev.py', 'apply_increment.py'):
        files[name] = ROOT/'tools/dev'/name
    files['frontend_persistence.py'] = ROOT/'tools/frontend/persistence.py'
    files['slot_theme.py'] = ROOT/'tools/slot_theme.py'
    remote.python('from pathlib import Path\nPath('+repr(job)+').mkdir(parents=True,exist_ok=False)')
    for name, path in files.items():
        remote.copy(path, job+'/'+name)
    remote.python('import subprocess,sys\nfrom pathlib import Path\np=Path('+repr(job)+")\nwith (p/'worker.log').open('wb') as out:subprocess.Popen([sys.executable,str(p/'device_upload.py'),str(p)],stdin=subprocess.DEVNULL,stdout=out,stderr=out,start_new_session=True)")
    (BASE/'install-job.json').write_text(json.dumps(dict(session=session, job=job), indent=2)+'\n')
    print('Started binary-only transaction:', session, sha)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr.decode('utf8', 'replace') if error.stderr else 'Device command failed') from None
