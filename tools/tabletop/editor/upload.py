"""Host-side scene upload jobs; immutable payloads, narrow manifests, retained evidence.

One upload job is one device transaction for one or more saved layouts: one snapshot,
one combined (deduplicated) manifest of only the files whose device hash differs, one
tar, one frontend restart, verification of every file and one audit. Any failure
rolls every file back together (device_upload.py).

    python -m tools.tabletop.editor.upload --layout snes-panasonic --layout gba-pvm --open normal
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import threading
import time
import uuid
import zlib

from tools.tabletop.device_probe import Remote
from tools.slot_theme import LEGACY, SLOTTED, DEVICE_THEMES
from tools.tabletop.editor import room as room_profiles

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BUILD = ROOT / 'build/tabletop'
RUNTIME_SUFFIXES = {'.mesh', '.texture', '.mask', '.pose', '.control', '.txt', '.json', '.png'}
# Local models remain in the retained shared asset tree. Each transaction targets
# the supported theme actually selected on the device, and rechecks it before stopping ES.
THEME_NAME = LEGACY
DEVICE_THEME = '/userdata/themes/' + THEME_NAME
DEVICE_LAYOUTS = DEVICE_THEME + '/_slot/tabletop/layouts'
DEVICE_JOBS = '/userdata/system/slot-dev/editor-uploads'
# Device worker tools sent with every job (name on the device, source on the host).
TOOLS = (('device_upload.py', 'tools/tabletop/editor/device_upload.py'), ('session_data.py', 'tools/dev/session_data.py'),
         ('esdev.py', 'tools/dev/esdev.py'), ('apply_increment.py', 'tools/dev/apply_increment.py'),
         ('frontend_persistence.py', 'tools/frontend/persistence.py'), ('slot_theme.py', 'tools/slot_theme.py'))
FAIL_POINTS = ('installed', 'started')
ROOM_MARKER = b'SLOTTED_ROOM1:SLOTHOME1,SLOTWORLD1'
SURFACES_MARKER = b'SLOTTED_ROOM1:SLOTHOME1,SLOTWORLD1,SLOTWORLD2'  # room surfaces, 22 Oct frontend


def digest(data):
    return hashlib.sha256(data).hexdigest()


def theme_slot():
    return ROOT / 'theme' / THEME_NAME / '_slot'


def layout_file(system, tv):
    return '_slot/tabletop/layouts/' + system + '-' + tv + '.scene'


def entry_key(entry):
    p=entry['profile']
    return room_profiles.profile_key(p) if p.get('kind') in ('room','home') else entry['system']+'-'+entry['tv']


def native_file(entry):
    key=entry_key(entry)
    return '_slot/tabletop/layouts/'+key+('.world' if key=='room' else '.scene')


def room_frontend(profiles, theme, spec, binary):
    """New scene formats must never reach the legacy theme or an old frontend."""
    formats={('SLOTWORLD1' if p['kind']=='room' else 'SLOTHOME1') for p in profiles if p.get('kind') in ('room','home')}
    if formats and (theme!=SLOTTED or not formats<=set(spec.get('roomFormats',[])) or ROOM_MARKER not in binary):
        raise ValueError('Room/home scenes require Slotted and its verified room frontend. No device files were changed.')
    if any(p.get('kind')=='room' and p.get('surfaces') for p in profiles):
        formats.add('SLOTWORLD2')
        if 'SLOTWORLD2' not in spec.get('roomFormats',[]) or SURFACES_MARKER not in binary:
            raise ValueError('Room surfaces need the newer Slotted frontend; see the editor README. No device files were changed.')
    return sorted(formats)


def dependencies(profile):
    """Only current runtime derivatives for the selected models, never source GLBs."""
    kind=profile.get('kind');system=profile.get('system');tv=profile.get('tv')
    prepared = set(profile['tables']) if kind=='room' else {'table', tv, profile.get('table', {}).get('model', 'table')}
    variants = set(profile['consoles']) if kind=='home' else set() if kind=='room' else {system}
    if 'snes' in variants:variants.add('snes-us')
    if 'md' in variants:variants.add('md-jp')
    prepared |= {key for key in variants if (BUILD / 'assets' / key).is_dir()}
    result = {}
    folders = [(BUILD / 'assets' / key, '_slot/tabletop/' + key) for key in sorted(prepared)]
    folders += [(theme_slot() / 'consoles' / key, '_slot/consoles/' + key) for key in sorted(variants)]
    local = theme_slot() / 'local-models/consoles/gba'
    if 'gba' in variants and local.is_dir():
        folders.append((local, '_slot/local-models/consoles/gba'))
    for folder, prefix in folders:
        if not folder.is_dir():
            raise ValueError('Missing prepared runtime model: ' + str(folder))
        for path in sorted(folder.rglob('*')):
            if path.is_file() and path.suffix in RUNTIME_SUFFIXES:
                result[prefix + '/' + path.relative_to(folder).as_posix()] = path
    extras=['MODEL_CREDITS.txt']+(['stage/tv/'+tv+'.png'] if tv else [])+['shells/'+key+'.png' for key in sorted(variants)]
    for name in extras:
        path = theme_slot() / name
        if path.is_file():
            result['_slot/' + name] = path
    if kind=='room':
        for name in room_profiles.textures(profile):
            result['_slot/tabletop/surfaces/' + name + '.png'] = room_profiles.texture_path(ROOT, name)
    return result


def combined_dependencies(profiles):
    """Every layout's runtime files, each listed once (TVs, tables and consoles are shared)."""
    result = {}
    for profile in profiles:
        for key, path in dependencies(profile).items():
            if result.setdefault(key, path) != path:
                raise ValueError('Two sources for one runtime file: ' + key)
    return result


def plan(hashes, device):
    """Split the needed files into those to send (device hash differs or missing) and
    those already identical on the device. Every needed file is verified afterwards."""
    changed = [key for key in hashes if device.get(key) != hashes[key]]
    return changed, [key for key in hashes if key not in changed]


class Uploads:
    def __init__(self):
        self.lock = threading.Lock()
        self.current = dict(state='idle', message='Save and upload the current layout to test it on your device.')
        self.directory = None

    def restore_status(self):
        candidates = sorted((BUILD / 'editor-uploads').glob('*/status.json'))
        if not candidates:
            return
        try:
            value = json.loads(candidates[-1].read_text(encoding='utf-8'))
            self.directory, self.current = candidates[-1].parent, value
            if value['state'] == 'running':
                if value.get('remoteJob'):
                    threading.Thread(target=self.resume, args=(value['remoteJob'],), daemon=True).start()
                else:
                    self.update(state='failed', message='Previous upload stopped before the device transaction started. Your saved layout is retained.')
        except (ValueError, OSError, KeyError):
            self.directory = None

    def resume(self, remote_job):
        try:
            self.poll(Remote(), remote_job)
        except BaseException as error:
            self.update(state='failed', message='Cannot read device upload status: ' + str(error), remoteJob=remote_job)

    def poll(self, remote, remote_job, timeout=600):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = json.loads(remote.python("from pathlib import Path\nimport json\np=Path(" + repr(remote_job + '/status.json') + ")\nprint(p.read_text() if p.is_file() else json.dumps(dict(state='running',message='Starting device snapshot…')))"))
            value.pop('system', None)
            value.pop('tv', None)
            self.progress(value.pop('progress', None) or {})
            self.update(**value, remoteJob=remote_job)
            if value['state'] in ('complete', 'failed'):
                return
            time.sleep(1)
        raise TimeoutError('Device upload is still running. Check its retained status: ' + remote_job + '/status.json')

    def status(self):
        with self.lock:
            return json.loads(json.dumps(self.current))

    def update(self, **values):
        with self.lock:
            self.current.update(values)
            if self.directory:
                path = self.directory / 'status.json'
                temporary = path.with_suffix('.tmp')
                temporary.write_text(json.dumps(self.current, indent=2), encoding='utf-8')
                temporary.replace(path)

    def progress(self, states):
        """Per-file progress, {theme-relative name: state}, merged into the status list."""
        with self.lock:
            for item in self.current.get('progress', []):
                item['state'] = states.get(item['name'], item['state'])

    def start(self, profile, native, save):
        """The quick "Upload to device": save the current layout, upload it and open it."""
        def prepare():
            saved = save(profile)
            source = Path(saved['json']).read_bytes()
            return [dict(system=profile['system'], tv=profile['tv'], profile=profile, native=native, source=source, saved=saved)]
        return self.start_batch(prepare, (profile.get('system'), profile.get('tv')))

    def start_batch(self, prepare, open_target=None, fail_at=None, background=True):
        """prepare() runs under the upload lock, after the running check, and returns the
        layouts as dicts (system, tv, profile, native, source); a rejected upload never
        saves. open_target is (system, tv) to open afterwards, or None for normal startup."""
        if fail_at not in (None,) + FAIL_POINTS:
            raise ValueError('Unknown forced failure point')
        with self.lock:
            if self.current['state'] == 'running':
                raise ValueError('An upload is already running; wait for it to finish.')
            entries = prepare()
            keys = [entry_key(entry) for entry in entries]
            if not keys:
                raise ValueError('Choose at least one saved layout to upload.')
            if len(set(keys)) != len(keys):
                raise ValueError('A layout is listed twice')
            session = 'editor-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
            self.directory = BUILD / 'editor-uploads' / session
            (self.directory / 'layouts').mkdir(parents=True, exist_ok=False)
            for key, entry in zip(keys, entries):
                (self.directory / 'layouts' / (key + '.json')).write_bytes(entry['source'])
                (self.directory / 'layouts' / Path(native_file(entry)).name).write_bytes(entry['native'].encode('utf-8'))
            if len(entries) == 1:
                (self.directory / 'profile.json').write_bytes(entries[0]['source'])
            system, tv = open_target or (None, None)
            self.current = dict(state='running', message='Connecting to your device…', session=session,
                                system=system, tv=tv, layouts=keys, progress=[], evidence=str(self.directory),
                                sources={key: digest(entry['source']) for key, entry in zip(keys, entries)})
            if len(entries) == 1:
                self.current.update(sourceSha256=digest(entries[0]['source']), saved=entries[0].get('saved'))
            if fail_at:
                self.current['failAt'] = fail_at
            result = dict(self.current)
            directory = self.directory
        if background:
            threading.Thread(target=self.worker, args=(entries, open_target, session, directory, fail_at), daemon=True).start()
        else:
            self.worker(entries, open_target, session, directory, fail_at)
        return result

    def worker(self, entries, open_target, session, directory, fail_at=None):
        remote_job = DEVICE_JOBS + '/' + session
        try:
            remote = Remote()
            sources = combined_dependencies([entry['profile'] for entry in entries])
            natives = {native_file(entry): entry['native'].encode('utf-8') for entry in entries}
            if natives.keys() & sources.keys():
                raise ValueError('A layout file is also a model dependency')
            hashes = {key: digest(path.read_bytes()) for key, path in sources.items()}
            hashes.update({key: digest(data) for key, data in natives.items()})
            sizes = {key: path.stat().st_size for key, path in sources.items()}
            sizes.update({key: len(data) for key, data in natives.items()})
            self.update(message='Checking ' + str(len(hashes)) + ' files on your device…',
                        progress=[dict(name=key, bytes=sizes[key], state='checking') for key in sorted(hashes)])
            # Connection/readiness checks happen before any device mutation.
            # Full home scenes reference hundreds of files. Compress this read-only
            # request so Windows/OpenSSH command-line limits cannot truncate it.
            request = base64.b64encode(zlib.compress(json.dumps(list(hashes)).encode())).decode()
            state = json.loads(remote.python("""import sys,json,hashlib,base64,zlib
from pathlib import Path
sys.path.insert(0,'/userdata/system/slot-dev')
import esdev
if not esdev.es_pid() or json.loads(esdev.api('/runningGame'))!={'msg':'NO GAME RUNNING'}:
    raise RuntimeError('Close the running game and return to the frontend before uploading.')
theme=esdev.get('ThemeSet')
if theme not in THEMES:raise RuntimeError('Select Slotted or art-book-slot on the device first.')
base=Path('/userdata/themes')/theme
keys=json.loads(zlib.decompress(base64.b64decode(KEYS)))
files={key:hashlib.sha256((base/key).read_bytes()).hexdigest() if (base/key).is_file() else None for key in keys}
print(json.dumps(dict(theme=theme,files=files)))
""".replace('THEMES', repr(DEVICE_THEMES)).replace('KEYS', repr(request))))
            theme = state['theme']
            self.update(theme=theme)
            record = 'frontend-Slotted.json' if theme == SLOTTED else 'frontend.json'
            frontend_spec = json.loads((BUILD / 'editor-device' / record).read_text(encoding='utf-8'))
            if theme == SLOTTED and frontend_spec.get('themeRoot') != 'active-theme-v1':
                raise ValueError('Slotted needs a frontend with active-theme asset resolution.')
            frontend = ROOT / frontend_spec['path']
            binary=frontend.read_bytes()
            if digest(binary) != frontend_spec['sha256']:
                raise ValueError('The editor preview frontend needs rebuilding; see the editor README.')
            formats=room_frontend([entry['profile'] for entry in entries],theme,frontend_spec,binary)
            changed, same = plan(hashes, state['files'])
            self.progress({**dict.fromkeys(changed, 'queued'), **dict.fromkeys(same, 'same')})
            manifest = {}
            with tarfile.open(directory / 'payload.tar', 'w') as archive:
                for key in changed:
                    data = natives[key] if key in natives else sources[key].read_bytes()
                    if digest(data) != hashes[key]:
                        raise ValueError('Runtime model changed while packaging: ' + key)
                    info = tarfile.TarInfo(key)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
                    manifest[key] = dict(sha256=hashes[key], bytes=len(data))
            (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            config = dict(session=session, theme=theme, layouts=[entry_key(entry) for entry in entries],
                          preview=open_target is not None, files=manifest, verify=hashes, frontendSha256=frontend_spec['sha256'],
                          sources={entry_key(entry): digest(entry['source']) for entry in entries})
            if formats:config['roomFormats']=formats
            if open_target:
                config.update(system='megadrive' if open_target[0] == 'md' else open_target[0], tv=open_target[1])
            if len(entries) == 1:
                config['sourceSha256'] = digest(entries[0]['source'])
            if fail_at:
                config['failAt'] = fail_at
            (directory / 'request.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
            megabytes = sum(entry['bytes'] for entry in manifest.values()) / 2 ** 20
            self.update(message='Sending %d changed file%s (%.1f MiB; %d already on the device) and the preview frontend…'
                        % (len(manifest), '' if len(manifest) == 1 else 's', megabytes, len(same)),
                        target=remote.target, manifest=manifest)
            remote.run(['mkdir', '-p', remote_job])
            copies = [(directory / name, name) for name in ('manifest.json', 'payload.tar', 'request.json')]
            copies += [(ROOT / source, name) for name, source in TOOLS] + [(frontend, 'frontend')]
            for path, name in copies:
                remote.copy(path, remote_job + '/' + name)
            self.progress(dict.fromkeys(changed, 'sent'))
            self.update(remoteJob=remote_job)
            remote.python("""import subprocess,sys
from pathlib import Path
p=Path(JOB)
with (p/'worker.log').open('wb') as log:
    subprocess.Popen([sys.executable,str(p/'device_upload.py'),str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
""".replace('JOB', repr(remote_job)))
            self.poll(remote, remote_job)
        except BaseException as error:
            detail = error.stderr.decode('utf-8', 'replace').strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
            self.update(state='failed', message=detail, remoteJob=remote_job)


UPLOADS = Uploads()


def main():
    """Command-line batch of saved layouts (device tests); the editor uses the same job."""
    from tools.tabletop.editor import server
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--layout', action='append', required=True, help='saved SYSTEM-TV layout, repeatable')
    parser.add_argument('--open', default='normal', help='SYSTEM-TV to open afterwards, or normal')
    parser.add_argument('--fail-at', choices=FAIL_POINTS, help='test only: fail there and roll everything back')
    args = parser.parse_args()
    jobs = Uploads()
    open_target = None if args.open == 'normal' else server.layout_pair(args.open)
    result = jobs.start_batch(lambda: [server.scene_entry(key) for key in args.layout],
                              open_target, args.fail_at)
    shown = None
    while (final := jobs.status())['state'] == 'running':
        counts = {}
        for item in final.get('progress', []):
            counts[item['state']] = counts.get(item['state'], 0) + 1
        line = final['message'] + ' ' + json.dumps(counts, sort_keys=True)
        if line != shown:
            print(time.strftime('%H:%M:%S'), line, flush=True)
            shown = line
        time.sleep(0.5)
    print(json.dumps(dict(session=result['session'], state=final['state'], message=final['message'],
                          evidence=result['evidence'], recovery=final.get('recovery')), indent=2))
    raise SystemExit(0 if final['state'] == 'complete' else 1)


if __name__ == '__main__':
    main()
