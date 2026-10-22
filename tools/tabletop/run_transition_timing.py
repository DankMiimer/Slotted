"""Dispatch/fetch the private paced switch-timing study (n19 baseline vs candidates)."""
import argparse
import hashlib
import io
import json
import os
import subprocess
import tarfile
import time
import uuid
from tools.tabletop.device_probe import Remote, ROOT

BASE = ROOT/os.environ.get('SLOT_TRANSITION_BUILD', 'build/system-switch-implementation-20261020')
# Prefetched neighbours with a pause (normal browsing), then cold destinations in quicker succession.
PREFETCHED = [s+':1.2:p' for s in ('nes:panasonic', 'gb:pvm', 'gba:pvm', 'n64:panasonic', 'psx:panasonic',
                                    'gbc:pvm', 'nds:pvm', 'snes:panasonic', 'psp:pvm', 'nes:panasonic')]
COLD = [s+':0.5' for s in ('gb:pvm', 'n64:panasonic', 'gba:pvm', 'psx:panasonic', 'nds:pvm',
                           'nes:panasonic', 'gbc:pvm', 'snes:panasonic', 'psp:pvm', 'n64:panasonic')]
RUNS = [dict(name='n19-1', binary='timing-n19-arm64'), dict(name='new-1', binary='timing-new-arm64'),
        dict(name='n19-2', binary='timing-n19-arm64'), dict(name='new-2', binary='timing-new-arm64')]
# A/B evidence: the candidate with GPU uploads also allowed while the hardware lifts.
LIFT_UPLOADS = dict(name='lift-uploads-1', binary='timing-new-arm64', env={'SLOT_SCENE_LIFT_UPLOADS': '1'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--lift-uploads', action='store_true', help='also time uploads during the lift (A/B)')
    parser.add_argument('--baseline', default='n19', help='baseline label: runs timing-LABEL-arm64 as LABEL-1/LABEL-2')
    args = parser.parse_args()
    remote = Remote()
    if args.fetch:
        saved = json.loads((BASE/'timing-job.json').read_text())
        job = saved['job']
        status = json.loads(remote.python('from pathlib import Path\nprint((Path('+repr(job)+")/'status.json').read_text())"))
        print(json.dumps(status))
        if status['state'] not in ('complete', 'failed'):
            return
        code = '''import sys,tarfile
from pathlib import Path
p=Path(JOB)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
    for f in sorted(p.rglob('*')):
        if f.is_file() and not f.is_symlink() and f.suffix in ('.json','.tsv','.log'):t.add(f,arcname=f.relative_to(p).as_posix(),recursive=False)
'''.replace('JOB', repr(job))
        output = BASE/saved['session']
        with tarfile.open(fileobj=io.BytesIO(remote.python(code, 90))) as archive:
            for member in archive:
                target = output/member.name
                if not member.isfile() or not target.resolve().is_relative_to(output.resolve()):
                    raise ValueError('Unsafe result member')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
        print('Fetched:', output)
        return
    session = 'transition-timing-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    job = '/userdata/system/slot-dev/transition-timing/'+session
    baseline = 'timing-'+args.baseline+'-arm64'
    files = {baseline: BASE/baseline, 'timing-new-arm64': BASE/'timing-new-arm64',
             'transition_timing_study.py': ROOT/'tools/tabletop/transition_timing_study.py'}
    chosen = [dict(run, name=run['name'].replace('n19', args.baseline), binary=run['binary'].replace('n19', args.baseline))
              for run in RUNS[:2]+([LIFT_UPLOADS] if args.lift_uploads else [])+RUNS[2:]]
    runs = [dict(run, steps=PREFETCHED+COLD) for run in chosen]
    config = dict(session=session, runs=runs, files={name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()})
    local = BASE/session
    local.mkdir(parents=True)
    (local/'request.json').write_text(json.dumps(config, indent=2)+'\n')
    remote.python('from pathlib import Path\nPath('+repr(job)+').mkdir(parents=True,exist_ok=False)')
    for name, path in files.items():
        remote.copy(path, job+'/'+name)
    remote.copy(local/'request.json', job+'/request.json')
    remote.python('import subprocess\nfrom pathlib import Path\np=Path('+repr(job)+")\nwith (p/'worker.log').open('wb') as log:subprocess.Popen(['python3',str(p/'transition_timing_study.py'),str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)")
    (BASE/'timing-job.json').write_text(json.dumps(dict(session=session, job=job), indent=2)+'\n')
    print('Started:', session)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr.decode('utf8', 'replace') if error.stderr else 'Device command failed') from None
