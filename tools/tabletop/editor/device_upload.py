"""Device-side transaction for a scene-editor upload (launched detached over SSH).

One job installs every file of one or more layouts together: one snapshot, one
apply, every needed file verified, one frontend restart, one audit. Any failure
restores every file from that snapshot. status.json reports progress per file.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import time

from session_data import Snapshot, digest
import esdev
try:
    from slot_theme import LEGACY, DEVICE_THEMES
except ModuleNotFoundError:
    from tools.slot_theme import LEGACY, DEVICE_THEMES
try:
    import frontend_persistence
except ModuleNotFoundError:
    from tools.frontend import persistence as frontend_persistence

THEME_NAME = LEGACY
THEME = Path('/userdata/themes') / THEME_NAME
OFFICIAL = Path('/usr/bin/emulationstation')
SYSTEMS = ('snes', 'n64', 'nes', 'megadrive', 'psx', 'gb', 'gbc', 'gba', 'nds', 'psp', 'pico8')
TVS = ('panasonic', 'pvm', 'oldtv')
LAYOUT = re.compile(r'(snes|n64|nes|md|psx|gb|gbc|gba|nds|psp|pico8)-(panasonic|pvm|oldtv)')
ROOM_LAYOUT = re.compile(r'room|home-(panasonic|pvm|oldtv)')
ROOM_MARKER = b'SLOTTED_ROOM1:SLOTHOME1,SLOTWORLD1'
SURFACES_MARKER = b'SLOTTED_ROOM1:SLOTHOME1,SLOTWORLD1,SLOTWORLD2'
FAIL_POINTS = ('installed', 'started')


def checked_members(archive, expected, theme=None):
    theme = THEME if theme is None else theme
    members = archive.getmembers()
    names = [m.name for m in members]
    if len(set(names)) != len(names) or set(names) != set(expected):
        raise ValueError('Archive and owned manifest differ')
    for member in members:
        key = PurePosixPath(member.name)
        if (not member.isfile() or key.is_absolute() or '..' in key.parts or '\\' in member.name
                or not member.name.startswith('_slot/')
                or not (theme / member.name).resolve().is_relative_to(theme.resolve())):
            raise ValueError('Unsafe upload member: ' + member.name)
        data = archive.extractfile(member).read()
        entry = expected[member.name]
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Upload checksum mismatch: ' + member.name)
    return members


def check_audit(report, expected, theme_name=LEGACY):
    if report['data']['changed'] or report['data']['new']:
        raise RuntimeError('User data changed during upload; snapshot retained')
    changes = {name.replace('\\', '/') for name in report['runtime']['changed'] + report['runtime']['new']}
    owned = {'themes/' + theme_name + '/' + name for name in expected}
    if not changes <= owned:
        raise RuntimeError('Unexpected runtime changes: ' + ', '.join(sorted(changes - owned)))


def check_request(config):
    """Everything about the request that can be refused before the device is touched."""
    if config.get('theme', THEME_NAME) not in DEVICE_THEMES:
        raise ValueError('Unsupported device theme')
    preview = config.get('preview', True)
    if preview and (config.get('system') not in SYSTEMS or config.get('tv') not in TVS):
        raise ValueError('Unsupported preview selection')
    layouts=config.get('layouts', [])
    if not all(LAYOUT.fullmatch(key) or ROOM_LAYOUT.fullmatch(key) for key in layouts):
        raise ValueError('Unsupported layout name')
    formats={('SLOTWORLD1' if key=='room' else 'SLOTHOME1') for key in layouts if ROOM_LAYOUT.fullmatch(key)}
    if formats and (config.get('theme')!='Slotted' or not formats<=set(config.get('roomFormats',[]))):
        raise ValueError('Room/home layouts require the Slotted room frontend')
    for name in config['files']:
        if name.endswith('/room.world') or re.search(r'/home-[^/]+\.scene$',name):
            key=Path(name).stem
            if key not in layouts or not ROOM_LAYOUT.fullmatch(key):raise ValueError('Undeclared room/home scene')
    if config.get('failAt') not in (None,) + FAIL_POINTS:
        raise ValueError('Unknown forced failure point')
    files = config['files']
    verify = config.get('verify') or {name: entry['sha256'] for name, entry in files.items()}
    for name in verify:
        key = PurePosixPath(name)
        if key.is_absolute() or '..' in key.parts or '\\' in name or not name.startswith('_slot/'):
            raise ValueError('Unsafe verification path: ' + name)
    if any(verify.get(name) != entry['sha256'] for name, entry in files.items()):
        raise ValueError('Verification list does not cover the manifest')
    return verify


def verify_files(verify, mark, theme=None):
    """Hash every file the layouts need, as installed; mark() reports each one."""
    theme = THEME if theme is None else theme
    for name, sha256 in verify.items():
        path = theme / name
        if not path.is_file() or digest(path) != sha256:
            mark(name, 'mismatch')
            raise RuntimeError('Verification failed: ' + name)
        mark(name, 'verified')


def rollback_states(snapshot, names, theme=None):
    """After restoring the snapshot, each sent file must be its snapshot copy again, or
    gone when the snapshot did not have it."""
    theme = THEME if theme is None else theme
    prefix = theme.resolve().relative_to(snapshot.root).as_posix() + '/'
    before = {key.replace('\\', '/'): value for key, value in snapshot.manifest()['runtime'].items()}
    result = {}
    for name in names:
        path, original = theme / name, before.get(prefix + name)
        if original is None:
            result[name] = 'removed' if not path.exists() else 'rollback failed'
        else:
            result[name] = 'restored' if path.is_file() and digest(path) == original else 'rollback failed'
    return result


def bind(binary):
    if ' /usr/bin/emulationstation ' in Path('/proc/mounts').read_text():
        subprocess.run(['umount', str(OFFICIAL)], check=True)
    binary.chmod(0o755)
    subprocess.run(['mount', '--bind', str(binary), str(OFFICIAL)], check=True)


def start(environment):
    subprocess.Popen(['setsid', esdev.INIT, 'start'], env=environment,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def process_environment(pid):
    return Path('/proc/' + pid + '/environ').read_bytes().split(b'\0')


def run(job):
    config = json.loads((job / 'request.json').read_text())
    theme_name = config.get('theme', LEGACY)
    theme = THEME.parent / theme_name
    snapshot = Snapshot('/userdata', config['session'])
    stopped = backed_up = installed = rebound = False
    startup_backup = None
    prior_env = os.environ.copy()
    layouts = config.get('layouts', [])
    progress = {}
    current = ['Starting device transaction…']
    def status(state, message, **extra):
        current[0] = message
        result = dict(state=state, message=message, session=config['session'],
                      system=config.get('system'), tv=config.get('tv'), layouts=layouts, progress=progress, **extra)
        temporary = job / 'status.tmp'
        temporary.write_text(json.dumps(result, indent=2))
        temporary.replace(job / 'status.json')
    def mark(name, state):
        progress[name] = state
        status('running', current[0])
    lock = open('/userdata/system/slot-dev/editor-upload.lock', 'a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        status('failed', 'Another device upload is running. Wait for it to finish.')
        lock.close()
        return
    try:
        verify = check_request(config)
        frontend = job / 'frontend'
        if digest(frontend) != config['frontendSha256']:
            raise ValueError('Frontend checksum mismatch')
        if config.get('roomFormats') and ROOM_MARKER not in frontend.read_bytes():
            raise ValueError('Frontend does not support room/home formats')
        if 'SLOTWORLD2' in config.get('roomFormats', []) and SURFACES_MARKER not in frontend.read_bytes():
            raise ValueError('Frontend does not support room surfaces')
        expected = config['files']
        with tarfile.open(job / 'payload.tar') as archive:
            checked_members(archive, expected, theme)
        progress.update(dict.fromkeys(verify, 'same'))
        progress.update(dict.fromkeys(expected, 'received'))
        pid = esdev.es_pid()
        if not pid or json.loads(esdev.api('/runningGame')) != {'msg': 'NO GAME RUNNING'}:
            raise RuntimeError('Return to the frontend and close any running game before uploading.')
        if esdev.get('ThemeSet') != theme_name:
            raise RuntimeError('Select the ' + theme_name + ' theme on the device first.')
        for entry in process_environment(pid):
            name, _, value = entry.partition(b'=')
            if name.decode(errors='replace').startswith(('SLOT_', 'SDL_')):
                prior_env[name.decode()] = value.decode()
        shutil.copy2(OFFICIAL, job / 'previous-frontend')
        previous_sha = digest(job / 'previous-frontend')
        status('running', 'Stopping frontend and taking a verified snapshot…')
        if json.loads(esdev.api('/runningGame')) != {'msg': 'NO GAME RUNNING'}:
            raise RuntimeError('A game started; return to the frontend before uploading.')
        stopped = True
        esdev.stop()
        if esdev.es_pid():
            raise RuntimeError('Frontend did not stop')
        counts = snapshot.backup()
        backed_up = True
        startup_backup = job / 'startup-backup'
        frontend_persistence.capture(startup_backup)
        status('running', 'Installing %d changed file%s for %s…' % (len(expected), '' if len(expected) == 1 else 's',
                                                                 ', '.join(layouts) or 'the frontend'), backup=counts)
        installed = True
        subprocess.run([sys.executable, str(job / 'apply_increment.py'), str(job / 'payload.tar'),
                        str(job / 'manifest.json'), '--theme', theme_name], check=True, capture_output=True)
        progress.update(dict.fromkeys(expected, 'installed'))
        status('running', 'Verifying all %d files…' % len(verify), backup=counts)
        verify_files(verify, mark, theme)
        if config.get('failAt') == 'installed':
            raise RuntimeError('Forced test failure after installing and verifying every file')
        rebound = True
        persistent = frontend_persistence.install(frontend, config['frontendSha256'],
                                                 frontend_persistence.firmware_sha256())
        bind(frontend_persistence.BASE / persistent['binary'])
        if digest(OFFICIAL) != config['frontendSha256']:
            raise RuntimeError('Mounted frontend checksum mismatch')
        audit = snapshot.audit(True)
        check_audit(audit, expected, theme_name)
        # Reuse the standard restore/audit process, retaining every changed file.
        restore = snapshot.restore()
        check_audit(snapshot.audit(True), expected, theme_name)
        environment = prior_env.copy()
        for name in tuple(environment):
            if name.startswith(('SLOT_SCENE_PREVIEW_', 'SLOT_TABLETOP_')):
                environment.pop(name)
        preview = config.get('preview', True)
        if preview:
            environment['SLOT_SCENE_PREVIEW_SYSTEM'] = config['system']
            environment['SLOT_SCENE_PREVIEW_TV'] = config['tv']
        opening = config['system'].upper() + ' / ' + config['tv'].upper() if preview else 'normal startup'
        status('running', 'Opening ' + opening + ' on the device…')
        start(environment)
        esdev.wait(45)
        actual = process_environment(esdev.es_pid())
        for name in ('SLOT_SCENE_PREVIEW_SYSTEM', 'SLOT_SCENE_PREVIEW_TV') if preview else ():
            if (name + '=' + environment[name]).encode() not in actual:
                raise RuntimeError('Preview environment was not inherited')
        # API readiness precedes the first full-detail 3D frame.
        time.sleep(10)
        if not esdev.es_pid() or json.loads(esdev.api('/runningGame')) != {'msg': 'NO GAME RUNNING'}:
            raise RuntimeError('Frontend preview did not stay ready')
        if config.get('failAt') == 'started':
            raise RuntimeError('Forced test failure after the frontend restarted with the new files')
        final_audit = snapshot.audit(True)
        check_audit(final_audit, expected, theme_name)
        verify_files(verify, mark, theme)
        frontend_persistence.verify(persistent)
        done = ('Uploaded %s (%d changed, %d verified). ' % (layouts[0].upper() if len(layouts) == 1 else '%d layouts' % len(layouts),
                                                              len(expected), len(verify)) if layouts else 'Installed. ')
        status('complete', done + opening[0].upper() + opening[1:] + ' is ready on the device.',
               backup=counts, audit=final_audit, restore=restore, frontendSha256=digest(OFFICIAL),
               previousFrontendSha256=previous_sha, files=expected, sourceSha256=config.get('sourceSha256'),
               sources=config.get('sources'), persistence=persistent,
               recovery=str(snapshot.directory), settings='Normal startup, TV and model preferences preserved.')
    except BaseException as error:
        recovery = {}
        message = str(error).rstrip('.')
        try:
            if stopped:
                esdev.stop()
                if esdev.es_pid():
                    raise RuntimeError('Cannot roll back while frontend is running')
                if backed_up:
                    recovery['restore'] = snapshot.restore(runtime=installed)
                    recovery['audit'] = snapshot.audit(runtime=installed)
                    if installed:
                        recovery['files'] = rollback_states(snapshot, config['files'], theme)
                        progress.update(recovery['files'])
                        clean = not any(group['changed'] or group['new'] for group in recovery['audit'].values())
                        good = all(state != 'rollback failed' for state in recovery['files'].values())
                        message += ('. Rolled back all %d changed files together; audit %s'
                                    % (len(recovery['files']), 'clean' if clean and good else 'NOT clean'))
                if startup_backup and (startup_backup / 'manifest.json').is_file():
                    frontend_persistence.restore(startup_backup)
                    recovery['startupRestored'] = True
                if rebound:
                    bind(job / 'previous-frontend')
                start(prior_env)
                esdev.wait(45)
        except BaseException as rollback_error:
            recovery['error'] = str(rollback_error)
        status('failed', message + '.', recovery=recovery, snapshot=str(snapshot.directory))
    finally:
        lock.close()


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve())
