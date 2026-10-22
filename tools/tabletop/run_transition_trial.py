"""Stage or retrieve a temporary frontend trial. No persistent installation."""
import argparse
import hashlib
import io
import json
import os
import subprocess
from pathlib import Path
import tarfile
import time
import uuid
from tools.tabletop.device_probe import Remote, ROOT

BASE = ROOT/os.environ.get('SLOT_TRANSITION_BUILD', 'build/system-switch-implementation-20261020')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    remote = Remote()
    if args.fetch:
        saved = json.loads((BASE/'trial-job.json').read_text())
        job = saved['job']
        status = json.loads(remote.python('from pathlib import Path\nprint((Path('+repr(job)+")/'status.json').read_text())"))
        print(json.dumps({k:status[k] for k in ('state', 'message')}))
        code = '''import sys,tarfile
from pathlib import Path
p=Path(JOB)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
    for f in sorted(p.rglob('*')):
        if f.is_file() and f.suffix in ('.json','.tsv','.log','.png'):t.add(f,arcname=f.relative_to(p).as_posix(),recursive=False)
'''.replace('JOB', repr(job))
        output = BASE/saved['session']
        with tarfile.open(fileobj=io.BytesIO(remote.python(code, 90))) as archive:
            for member in archive:
                target = output/member.name
                if not member.isfile() or not target.resolve().is_relative_to(output.resolve()):
                    raise ValueError('Unsafe trial result member')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
        print('Fetched:', output)
        return
    session = 'transition-ui-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    job = '/userdata/system/slot-dev/transition-trials/'+session
    files = {'frontend': (BASE/'frontend-candidate' if (BASE/'frontend-candidate').is_file() else BASE/'frontend-n17-candidate'),
             'transition_frontend_trial.py': ROOT/'tools/tabletop/transition_frontend_trial.py'}
    config = dict(session=session, files={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()})
    local = BASE/session
    local.mkdir(parents=True)
    (local/'request.json').write_text(json.dumps(config, indent=2)+'\n')
    remote.python('from pathlib import Path\nPath('+repr(job)+').mkdir(parents=True,exist_ok=False)')
    for name,path in files.items():
        remote.copy(path, job+'/'+name)
    remote.copy(local/'request.json', job+'/request.json')
    remote.python('import subprocess\nfrom pathlib import Path\np=Path('+repr(job)+")\nwith (p/'worker.log').open('wb') as out:subprocess.Popen(['python3',str(p/'transition_frontend_trial.py'),str(p)],stdin=subprocess.DEVNULL,stdout=out,stderr=out,start_new_session=True)")
    (BASE/'trial-job.json').write_text(json.dumps(dict(session=session, job=job), indent=2)+'\n')
    print('Started:', session)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr.decode('utf8', 'replace') if error.stderr else 'Device command failed') from None
