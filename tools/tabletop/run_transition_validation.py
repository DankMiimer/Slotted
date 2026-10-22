"""Dispatch/fetch immutable private native-transition validation."""
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
        saved = json.loads((BASE/'native-job.json').read_text())
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
        if f.is_file() and f.suffix in ('.json','.tsv','.log','.bmp'):t.add(f,arcname=f.relative_to(p).as_posix(),recursive=False)
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
    session = 'transition-native-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    job = '/userdata/system/slot-dev/transition-validation/'+session
    files = {'transition-probe-arm64': BASE/'transition-probe-arm64',
             'transition_device_validation.py': ROOT/'tools/tabletop/transition_device_validation.py'}
    config = dict(session=session, files={name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()})
    local = BASE/session
    local.mkdir(parents=True)
    (local/'request.json').write_text(json.dumps(config, indent=2)+'\n')
    remote.python('from pathlib import Path\nPath('+repr(job)+').mkdir(parents=True,exist_ok=False)')
    for name, path in files.items():
        remote.copy(path, job+'/'+name)
    remote.copy(local/'request.json', job+'/request.json')
    remote.python('import subprocess\nfrom pathlib import Path\np=Path('+repr(job)+")\nwith (p/'worker.log').open('wb') as log:subprocess.Popen(['python3',str(p/'transition_device_validation.py'),str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)")
    (BASE/'native-job.json').write_text(json.dumps(dict(session=session, job=job), indent=2)+'\n')
    print('Started:', session)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr.decode('utf8', 'replace') if error.stderr else 'Device command failed') from None
