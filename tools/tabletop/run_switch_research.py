"""Stage a unique private load probe and retrieve compact results over SSH."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import time
import uuid

from tools.tabletop.device_probe import Remote, ROOT

BASE = ROOT / 'build/system-switch-research-20261020'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--images', action='store_true')
    parser.add_argument('--stream-only', action='store_true')
    args = parser.parse_args()
    remote = Remote()
    if args.fetch:
        saved = json.loads((BASE / 'active-job.json').read_text())
        job = saved['job']
        result = json.loads(remote.python('from pathlib import Path\nprint((Path(' + repr(job) + ")/'status.json').read_text())"))
        print(json.dumps(result))
        if result['state'] not in ('complete', 'failed'):
            return
        code = '''import io,sys,tarfile
from pathlib import Path
root=Path(JOB)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
    for p in sorted(root.rglob('*')):
        if p.is_file() and (p.suffix in ('.json','.tsv','.log') or IMAGES and p.suffix=='.bmp'):
            t.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
'''.replace('JOB', repr(job)).replace('IMAGES', repr(args.images))
        data = remote.python(code, 120)
        output = BASE / saved['session']
        output.mkdir(exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            for member in archive:
                dest = output / member.name
                if not member.isfile() or not dest.resolve().is_relative_to(output.resolve()):
                    raise ValueError('Invalid result path')
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.extractfile(member).read())
        print('Fetched results:', output)
        return
    session = 'switch-study-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    job = '/userdata/system/slot-dev/switch-research/' + session
    files = {name: path for name, path in (
        ('switch-probe-arm64', BASE / 'switch-probe-arm64'),
        ('switch_device_probe.py', ROOT / 'tools/tabletop/switch_device_probe.py'))}
    config = dict(session=session, streamOnly=args.stream_only, files={name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()})
    local = BASE / session
    local.mkdir(parents=True)
    (local / 'request.json').write_text(json.dumps(config, indent=2) + '\n')
    remote.python('from pathlib import Path\nPath(' + repr(job) + ').mkdir(parents=True,exist_ok=False)')
    for name, path in files.items():
        remote.copy(path, job + '/' + name)
    remote.copy(local / 'request.json', job + '/request.json')
    remote.python('import subprocess\nfrom pathlib import Path\np=Path(' + repr(job) + ")\nwith (p/'worker.log').open('wb') as out: subprocess.Popen(['python3',str(p/'switch_device_probe.py'),str(p)],stdin=subprocess.DEVNULL,stdout=out,stderr=out,start_new_session=True)")
    (BASE / 'active-job.json').write_text(json.dumps(dict(job=job, session=session), indent=2) + '\n')
    print('Started private device job:', session)


if __name__ == '__main__':
    main()
