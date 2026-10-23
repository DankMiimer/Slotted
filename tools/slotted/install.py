"""Install Slotted on the device next to art-book-slot (one snapshot-protected transaction).

    python -m tools.slotted.install --package-only        (build the package and manifest only)
    python -m tools.slotted.install [--activate] [--resync-slot]
    python -m tools.slotted.install --standalone BUNDLE --activate

--activate selects Slotted as the theme. Without it, the theme is installed but not selected.
--resync-slot copies _slot/ from art-book-slot again instead of keeping Slotted's own copy.
Theme-only updates preserve the frontend. --standalone is a fresh install of the
complete runtime and matching frontend; it refuses an existing Slotted theme.
Evidence is kept in build/slotted/installs/SESSION.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import time
import uuid

from tools.slot_theme import ROOT, SLOTTED_SOURCE

BUILD = ROOT / 'build/slotted/installs'
REMOTE = '/userdata/system/slot-dev/slotted-installs/'


def files(source=SLOTTED_SOURCE):
    """Slotted's own files: everything in theme/slotted. _slot comes from the device."""
    result = {}
    for path in sorted(source.rglob('*')):
        relative = path.relative_to(source).as_posix()
        if path.is_file() and '__pycache__' not in relative and not relative.startswith('_slot/'):
            result[relative] = path
    return result


def package(directory, source=SLOTTED_SOURCE):
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {}
    with tarfile.open(directory / 'payload.tar', 'w') as archive:
        for name, path in files(source).items():
            data = path.read_bytes()
            manifest[name] = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o644, int(path.stat().st_mtime)
            archive.addfile(info, io.BytesIO(data))
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def install(activate, resync, standalone=None):
    from tools.tabletop.device_probe import Remote
    session = 'slotted-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    directory = BUILD / session
    if standalone:
        if resync:raise ValueError('A standalone bundle cannot resync assets from another theme')
        from tools.slotted.standalone import inspect
        import shutil
        release=inspect(standalone)
        directory.mkdir(parents=True)
        for source,name in [('payload.tar','payload.tar'),('manifest.json','manifest.json'),('frontend-candidate','frontend')]:
            shutil.copy2(Path(standalone)/source,directory/name)
        manifest=json.loads((directory/'manifest.json').read_text())
    else:manifest = package(directory)
    request = dict(session=session, activate=activate, resyncSlot=resync)
    if standalone:request.update(completeRuntime=True,frontendSha256=release['frontendSha256'],
                                 sourcePin=release['sourcePin'],runtimeLibraryHashes=release['runtimeLibraryHashes'])
    (directory / 'request.json').write_text(json.dumps(request, indent=2), encoding='utf-8')
    remote = Remote()
    job = REMOTE + session
    remote.run(['mkdir', '-p', job])
    copies = [(directory / n, n) for n in ('payload.tar', 'manifest.json', 'request.json')]
    copies += [(ROOT / 'tools/slotted/device_install.py', 'device_install.py'),
               (ROOT / 'tools/slot_theme.py', 'slot_theme.py'),
               (ROOT / 'tools/dev/session_data.py', 'session_data.py'), (ROOT / 'tools/dev/esdev.py', 'esdev.py')]
    if standalone:
        copies += [(directory/'frontend','frontend'),(ROOT/'tools/frontend/persistence.py','frontend_persistence.py'),
                   (ROOT/'tools/slotted/runtime.py','standalone_runtime.py'),
                   (ROOT/'tools/tabletop/editor/device_upload.py','device_upload.py')]
    for path, name in copies:
        remote.copy(path, job + '/' + name)
    remote.python("""import subprocess,sys
from pathlib import Path
p=Path(JOB)
with (p/'worker.log').open('wb') as log:
    subprocess.Popen([sys.executable,str(p/'device_install.py'),str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
""".replace('JOB', repr(job)))
    deadline = time.monotonic() + 900
    last = None
    while time.monotonic() < deadline:
        time.sleep(3)
        try:
            text = remote.python("from pathlib import Path\np=Path(" + repr(job + '/status.json') + ")\nprint(p.read_text() if p.is_file() else '{}')").decode()
        except Exception as error:  # the frontend restart can briefly slow SSH
            print('waiting:', error)
            continue
        value = json.loads(text or '{}')
        if value.get('message') != last and value.get('message'):
            last = value['message']
            print(value.get('state'), '-', last, flush=True)
        if value.get('state') in ('complete', 'failed'):
            (directory / 'status.json').write_text(json.dumps(value, indent=2), encoding='utf-8')
            return value
    raise TimeoutError('Install still running; read ' + job + '/status.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--package-only', action='store_true')
    parser.add_argument('--activate', action='store_true')
    parser.add_argument('--resync-slot', action='store_true')
    parser.add_argument('--standalone',type=Path,help='Fresh complete bundle; refuses an existing Slotted installation')
    args = parser.parse_args()
    if args.package_only and args.standalone:parser.error('Use tools.slotted.standalone to create/inspect complete bundles')
    if args.package_only:
        manifest = package(ROOT / 'build/slotted/package')
        print('packaged', len(manifest), 'files in build/slotted/package')
        return
    result = install(args.activate, args.resync_slot,args.standalone)
    print(json.dumps({k: result.get(k) for k in ('state', 'message', 'settings', 'themeSet', 'recovery')}, indent=2))
    if result.get('state') != 'complete':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
