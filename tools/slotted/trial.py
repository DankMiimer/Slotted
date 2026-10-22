"""Dispatch/fetch the temporary Slotted GUI trial, compatible with transition_ui_checks.

python -m tools.slotted.trial
SLOT_TRANSITION_BUILD=build/slotted-phase2 python -m tools.tabletop.transition_ui_checks smoke
python -m tools.slotted.trial --fetch
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import time
import uuid
from tools.tabletop.device_probe import Remote, ROOT
from tools.slotted.install import package

BASE = ROOT / 'build/slotted-phase2'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--build', type=Path, default=BASE, help='Candidate/evidence directory; must contain frontend-candidate')
    parser.add_argument('--startup', choices=('console','home'), default='console')
    parser.add_argument('--motion',choices=('full','reduced'),help='Temporary Slotted object-motion preference; snapshot restores it')
    parser.add_argument('--tv',choices=('panasonic','pvm','oldtv','retro'),help='Temporary home TV preference; snapshot restores it')
    parser.add_argument('--all-models',action='store_true',help='Temporarily show hidden modelled systems for coverage; snapshot restores visibility')
    parser.add_argument('--index-batch',type=int,choices=(0,3072,12288),help='Temporary rendering experiment; 0 is the monolithic reference')
    parser.add_argument('--screensaver',type=int,metavar='MS',help='Temporary screensaver delay (5000-120000 ms) for the checker\'s idle/wake step; snapshot restores it')
    parser.add_argument('--style',choices=('realistic','cel'),help='Temporary console model style; snapshot restores it')
    parser.add_argument('--color',choices=('original','black','white','red','blue','purple','green','yellow'),help='Temporary console colour; snapshot restores it')
    parser.add_argument('--recover-channels-from', help='Prior completed trial session with verified extra channel baselines')
    parser.add_argument('--upload-gate', action='store_true', help='Permit editor upload tests; restore startup activation as well as theme/data afterward')
    args = parser.parse_args()
    base=args.build.resolve()
    remote = Remote()
    if args.fetch:
        saved = json.loads((base / 'trial-job.json').read_text())
        job = saved['job']
        state = json.loads(remote.python('from pathlib import Path; print((Path(' + repr(job) + ")/'status.json').read_text())"))
        print(json.dumps({k: state[k] for k in ('state', 'message')}, indent=2))
        source = """import sys,tarfile
from pathlib import Path
p=Path(JOB)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz',dereference=True) as archive:
    for f in sorted(p.rglob('*')):
        rel=f.relative_to(p)
        if rel.parts[0] in ('trial-Slotted','previous-Slotted'):continue
        if f.is_file() and f.suffix in ('.json','.log','.tsv','.png','.txt'):archive.add(f,arcname=rel.as_posix(),recursive=False)
""".replace('JOB', repr(job))
        output = base / saved['session']
        with tarfile.open(fileobj=io.BytesIO(remote.python(source, 120)), mode='r:gz') as archive:
            for member in archive:
                target = output / member.name
                if not member.isfile() or not target.resolve().is_relative_to(output.resolve()):
                    raise ValueError('Unsafe trial result')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
        print('Fetched:', output)
        return
    session = 'slotted-ui-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    local = base / session
    package(local)
    files = {'frontend': base / 'frontend-candidate', 'device_trial.py': ROOT / 'tools/slotted/device_trial.py',
             'device_install.py': ROOT / 'tools/slotted/device_install.py',
             'slot_theme.py': ROOT / 'tools/slot_theme.py',
             'transition_frontend_trial.py': ROOT / 'tools/tabletop/transition_frontend_trial.py',
             'esdev.py': ROOT / 'tools/dev/esdev.py', 'session_data.py': ROOT / 'tools/dev/session_data.py',
             'frontend_persistence.py': ROOT / 'tools/frontend/persistence.py',
             'payload.tar': local / 'payload.tar', 'manifest.json': local / 'manifest.json'}
    request = dict(session=session, startup=args.startup, files={name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()})
    if args.recover_channels_from:request['recoverChannelsFrom']=args.recover_channels_from
    if args.upload_gate:request['uploadGate']=True
    if args.motion:request['motion']=args.motion
    if args.tv:request['tv']=args.tv
    if args.all_models:request['allModels']=True
    if args.index_batch is not None:request['indexBatch']=args.index_batch
    if args.screensaver is not None:request['screensaverMs']=args.screensaver
    if args.style:request['style']=args.style
    if args.color:request['color']=args.color
    (local / 'request.json').write_text(json.dumps(request, indent=2))
    files['request.json'] = local / 'request.json'
    job = '/userdata/system/slot-dev/slotted-trials/' + session
    remote.run(['mkdir', '-p', job])
    for name, path in files.items():
        remote.copy(path, job + '/' + name)
    remote.python("""import subprocess
from pathlib import Path
p=Path(JOB)
with (p/'worker.log').open('wb') as log:
    subprocess.Popen(['python3',str(p/'device_trial.py'),str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
""".replace('JOB', repr(job)))
    (base / 'trial-job.json').write_text(json.dumps(dict(session=session, job=job), indent=2))
    print('Started:', session)


if __name__ == '__main__':
    main()
