"""Device-side Slotted install (launched detached over SSH by tools/slotted/install.py).

Installs /userdata/themes/Slotted next to art-book-slot, never replacing it:
  1. stop the frontend and take a verified snapshot (session_data.py);
  2. stage Slotted: copy the runtime assets (_slot/) from the existing Slotted install, or from
     art-book-slot on first install / resync, so authored layouts and local-only models carry over;
     then add Slotted's own files from payload.tar and verify every one against the manifest;
  3. swap the staged folder in (the previous Slotted is kept in the job folder);
  4. create themesettings/Slotted.cfg from art-book-slot.cfg (only the slot-* theme options), once;
  5. optionally select Slotted as the theme, start the frontend and audit.
Any failure restores the snapshot, puts the previous Slotted back and restarts the frontend.
"""
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import time

try:
    from slot_theme import SLOTTED, LEGACY, H700_RUNTIME_LIBRARIES
except ModuleNotFoundError:
    from tools.slot_theme import SLOTTED, LEGACY, H700_RUNTIME_LIBRARIES
DEVICE_LOCK = Path('/userdata/system/slot-dev/editor-upload.lock')
MIGRATED = ('slot-tv-model', 'slot-model-style', 'slot-console-color', 'slot-snes-cartridge-model',
            'slot-gba-sp-model', 'slot-video', 'slot-wallpaper', 'slot-state')

def validate_runtime(names,read):
    # Historical theme-only trial jobs do not need the fresh-runtime module.
    try:from standalone_runtime import validate
    except ModuleNotFoundError:from tools.slotted.runtime import validate
    return validate(names,read)


class Layout:
    def __init__(self, root='/userdata'):
        self.root = Path(root)
        self.themes = self.root / 'themes'
        self.target = self.themes / SLOTTED
        self.legacy = self.themes / LEGACY
        self.settings = self.root / 'system/configs/emulationstation/themesettings'


def checked_members(archive, manifest, staging, complete_runtime=False):
    members = archive.getmembers()
    names = [m.name for m in members]
    if len(set(names)) != len(names) or set(names) != set(manifest):
        raise ValueError('Archive and manifest differ')
    for member in members:
        key = PurePosixPath(member.name)
        if (not member.isfile() or not key.parts or key.as_posix()!=member.name or ':' in member.name or key.is_absolute() or '..' in key.parts or '\\' in member.name
                or (key.parts[0] == '_slot' and not complete_runtime) or not (staging / member.name).resolve().is_relative_to(staging.resolve())):
            raise ValueError('Unsafe package member: ' + member.name)
        import hashlib
        data=archive.extractfile(member).read();entry=manifest[member.name]
        if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
            raise RuntimeError('Payload checksum differs: '+member.name)
        if complete_runtime and entry.get('mode') not in (0o644,0o755):raise ValueError('Unsupported standalone file mode')
    return members


def digest(path):
    import hashlib
    value = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''):
            value.update(block)
    return value.hexdigest()

def check_standalone(config,frontend,libraries):
    if config.get('sourcePin')!='4041b56a714265de81de8165b34fbd10f313a891' or digest(frontend)!=config['frontendSha256']:
        raise ValueError('Standalone frontend source pin/checksum differs')
    data=Path(frontend).read_bytes()
    if data[:6]!=b'\x7fELF\x02\x01' or data[18:20]!=b'\xb7\x00' or b'SLOTTED_ROOM1:SLOTHOME1,SLOTWORLD1,SLOTWORLD2' not in data:
        raise ValueError('Standalone frontend ABI/capabilities differ')
    hashes=config.get('runtimeLibraryHashes',{})
    if set(hashes)!=set(H700_RUNTIME_LIBRARIES):raise ValueError('Standalone runtime dependency record is incomplete')
    for name,expected in hashes.items():
        if digest(Path(libraries)/name)!=expected:raise ValueError('Firmware library differs from the build inputs: '+name)


def stage(layout, payload, manifest, session, resync=False, complete_runtime=False,on_created=None):
    """Builds the complete new Slotted folder beside the live one; returns its path."""
    staging = layout.themes / ('.Slotted-' + session)
    if staging.exists():
        raise FileExistsError('Staging folder already exists: ' + str(staging))
    if complete_runtime and layout.target.exists():
        raise ValueError('Fresh standalone install refuses an existing Slotted theme; preserve its authored runtime.')
    source = None if complete_runtime else layout.target / '_slot' if (layout.target / '_slot').is_dir() and not resync else layout.legacy / '_slot'
    if source is not None and not source.is_dir():
        raise FileNotFoundError('No runtime assets to copy: ' + str(source))
    with tarfile.open(payload) as archive:
        checked_members(archive,manifest,staging,complete_runtime)
        if complete_runtime:validate_runtime(manifest,lambda name:archive.extractfile(name).read())
    staging.mkdir(parents=True)
    if on_created:on_created(staging)
    if source is not None:shutil.copytree(source, staging / '_slot', symlinks=True)
    with tarfile.open(payload) as archive:
        for member in checked_members(archive, manifest, staging, complete_runtime):
            target = staging / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
            if complete_runtime:
                mode=manifest[member.name].get('mode',0o644)
                if mode not in (0o644,0o755):raise ValueError('Unsupported standalone file mode')
                target.chmod(mode)
    for name, entry in manifest.items():
        if digest(staging / name) != entry['sha256']:
            raise RuntimeError('Staged file does not match the manifest: ' + name)
    return staging, source


def swap(layout, staging, keep):
    """Moves the live Slotted (if any) to keep, then the staged folder into place."""
    previous = None
    if layout.target.exists():
        previous = keep
        layout.target.rename(previous)
    try:staging.rename(layout.target)
    except BaseException:
        if previous is not None:previous.rename(layout.target)
        raise
    return previous


def retain_failed(layout, path, keep):
    """Keep a failed derivative intact outside the theme search path; never delete assets."""
    if path.is_symlink() or path.resolve().parent != layout.themes.resolve():
        raise ValueError('Unexpected theme recovery path: ' + str(path))
    if keep.exists():
        raise FileExistsError('Keep the existing recovery copy: ' + str(keep))
    path.rename(keep)
    return keep


def undo_swap(layout, previous, keep=None):
    retained = None
    if layout.target.exists():
        keep = keep or ((previous.parent if previous else layout.root) / ('failed-Slotted-' + str(time.time_ns())))
        retained = retain_failed(layout, layout.target, keep)
    if previous and previous.exists():
        previous.rename(layout.target)
    return retained


def migrate_settings(layout):
    """Creates Slotted.cfg from art-book-slot.cfg once; ES records are name=value separated by CR."""
    target = layout.settings / (SLOTTED + '.cfg')
    if target.exists():
        return 'kept'
    source = layout.settings / (LEGACY + '.cfg')
    if not source.is_file():
        return 'none'
    records = source.read_bytes().decode('utf-8', 'replace').replace('\n', '\r').split('\r')
    keep = [r for r in records if any(r.startswith('subset.' + name + '=') for name in MIGRATED)]
    if not keep:
        return 'none'
    layout.settings.mkdir(parents=True, exist_ok=True)
    target.write_bytes(('\r'.join(keep) + '\r').encode('utf-8'))
    return 'created'


def check_audit(report, activate, migrated):
    allowed_data = set()
    if migrated == 'created':
        allowed_data.add('system/configs/emulationstation/themesettings/' + SLOTTED + '.cfg')
    if activate:
        allowed_data.add('system/configs/emulationstation/es_settings.cfg')
    data = {n.replace('\\', '/') for n in report['data']['changed'] + report['data']['new']}
    if not data <= allowed_data:
        raise RuntimeError('Unexpected user data changes: ' + ', '.join(sorted(data - allowed_data)))
    runtime = {n.replace('\\', '/') for n in report['runtime']['changed'] + report['runtime']['new']}
    stray = sorted(n for n in runtime if not n.startswith('themes/' + SLOTTED + '/'))
    if stray:
        raise RuntimeError('Unexpected runtime changes: ' + ', '.join(stray[:8]))


def _run(job):
    sys.path.insert(0, str(job))
    from session_data import Snapshot
    import esdev
    config = json.loads((job / 'request.json').read_text())
    manifest = json.loads((job / 'manifest.json').read_text())
    layout = Layout()
    snapshot = Snapshot('/userdata', config['session'])
    activate, resync = bool(config.get('activate')), bool(config.get('resyncSlot'))
    complete=config.get('completeRuntime') is True
    state = dict(stopped=False, backed_up=False, swapped=False, previous=None, staging=None)
    startup_backup=None;persistent=None;rebound=False;prior_env=None

    def status(kind, message, **extra):
        value = dict(state=kind, message=message, session=config['session'], **extra)
        (job / 'status.tmp').write_text(json.dumps(value, indent=2))
        (job / 'status.tmp').replace(job / 'status.json')

    try:
        if complete:
            if layout.target.exists():raise RuntimeError('Fresh standalone install refuses the existing Slotted theme; use the preserving update path.')
            import frontend_persistence
            from device_upload import bind,process_environment,start,OFFICIAL
            frontend=job/'frontend'
            check_standalone(config,frontend,'/usr/lib')
        elif not (layout.target/'_slot').is_dir() and not (layout.legacy/'_slot').is_dir():
            raise RuntimeError('No installed shared runtime; use a complete standalone bundle for a fresh install.')
        with tarfile.open(job/'payload.tar') as archive:
            checked_members(archive,manifest,layout.themes/('.Slotted-'+config['session']),complete)
            if complete:validate_runtime(manifest,lambda name:archive.extractfile(name).read())
        if not esdev.es_pid() or json.loads(esdev.api('/runningGame')) != {'msg': 'NO GAME RUNNING'}:
            raise RuntimeError('Return to the frontend and close any running game first.')
        previous_theme = esdev.get('ThemeSet')
        if complete:
            prior_env=os.environ.copy()
            for entry in process_environment(esdev.es_pid()):
                name,_,value=entry.partition(b'=')
                if name.decode(errors='replace').startswith(('SLOT_','SDL_')):prior_env[name.decode()]=value.decode()
            shutil.copy2(OFFICIAL,job/'previous-frontend')
        status('running', 'Stopping the frontend and taking a verified snapshot…')
        if json.loads(esdev.api('/runningGame'))!={'msg':'NO GAME RUNNING'}:raise RuntimeError('A game started; return to the frontend first.')
        state['stopped'] = True
        esdev.stop()
        if esdev.es_pid():
            raise RuntimeError('Frontend did not stop')
        counts = snapshot.backup()
        state['backed_up'] = True
        if complete:
            startup_backup=job/'startup-backup';frontend_persistence.capture(startup_backup)
        status('running', 'Copying the tabletop assets and Slotted files…', backup=counts)
        staging, source = stage(layout, job / 'payload.tar', manifest, config['session'], resync,complete,
                                on_created=lambda path:state.update(staging=path))
        state['staging'] = staging
        state['previous'] = swap(layout, staging, job / 'previous-Slotted')
        state['swapped'] = True
        state['staging'] = None
        migrated = migrate_settings(layout)
        if activate:
            esdev.set_('ThemeSet', SLOTTED)
        if complete:
            persistent=frontend_persistence.install(frontend,config['frontendSha256'],frontend_persistence.firmware_sha256())
            rebound=True;bind(frontend_persistence.BASE/persistent['binary'])
            if digest(OFFICIAL)!=config['frontendSha256']:raise RuntimeError('Standalone frontend mount checksum differs')
        audit = snapshot.audit(True)
        check_audit(audit, activate, migrated)
        status('running', 'Starting the frontend…')
        if complete:start(prior_env)
        else:esdev.start()
        esdev.wait(60)
        time.sleep(8)
        if not esdev.es_pid():
            raise RuntimeError('Frontend did not stay running')
        final = snapshot.audit(True)
        check_audit(final, activate, migrated)
        if complete:frontend_persistence.verify(persistent)
        status('complete', 'Slotted installed%s. art-book-slot is unchanged.' % (' and selected' if activate else ''),
               backup=counts, audit=final, settings=migrated, assetsFrom=str(source),
               previousTheme=previous_theme, themeSet=esdev.get('ThemeSet'), files=len(manifest),
               frontendSha256=digest(OFFICIAL) if complete else None,
               persistence=persistent,completeRuntime=complete,
               previousSlotted=str(state['previous']) if state['previous'] else None,
               recovery=str(snapshot.directory))
    except BaseException as error:
        recovery = {}
        try:
            if state['stopped']:
                esdev.stop()
                if state['staging'] and Path(state['staging']).exists():
                    retain_failed(layout, Path(state['staging']), job / 'failed-staging')
                if state['swapped']:
                    recovery['retained'] = str(undo_swap(layout, state['previous'], job / 'failed-Slotted'))
                    recovery['slotted'] = 'previous restored' if state['previous'] else 'removed'
                if state['backed_up']:
                    recovery['restore'] = snapshot.restore(runtime=True)
                    recovery['audit'] = snapshot.audit(runtime=True)
                if complete:
                    if startup_backup and (startup_backup/'manifest.json').is_file():frontend_persistence.restore(startup_backup)
                    if rebound:bind(job/'previous-frontend')
                    start(prior_env or os.environ.copy())
                else:esdev.start()
                esdev.wait(60)
        except BaseException as rollback_error:
            recovery['error'] = str(rollback_error)
        status('failed', str(error).rstrip('.') + '.', recovery=recovery, snapshot=str(snapshot.directory))


def run(job):
    import fcntl
    with DEVICE_LOCK.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            (job / 'status.json').write_text(json.dumps(dict(state='failed', message='Another device transaction is running.')))
            return
        _run(job)


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve())
