"""Hash-pinned tabletop frontend activation through Knulli's post-share hook. MIT.

The firmware binary stays untouched. S12populateshare calls /boot/postshare.sh
synchronously after mounting userdata and before S31 starts EmulationStation.
Only bind the retained binary here; the ordinary init script still owns launch.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

BASE = Path('/userdata/system/slot-dev/frontend')
HOOK = Path('/boot/postshare.sh')
OFFICIAL = Path('/usr/bin/emulationstation')
MOUNTS = Path('/proc/mounts')
RECEIPT = Path('/userdata/system/slot-dev/frontend-boot.json')
PIN = '4041b56a714265de81de8165b34fbd10f313a891'
BEGIN = b'# BEGIN SLOT TABLETOP FRONTEND\n'
END = b'# END SLOT TABLETOP FRONTEND\n'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.slot-tmp')
    with temporary.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(mode)
    temporary.replace(path)


def hook_bytes(previous):
    block = (BEGIN + b'if [ "$1" = start ] && [ -f /userdata/system/slot-dev/frontend/boot.py ]; then\n'
             b'    /usr/bin/python3 /userdata/system/slot-dev/frontend/boot.py boot '
             b'>> /userdata/system/slot-dev/frontend-boot.log 2>&1 || :\nfi\n' + END)
    if BEGIN in previous or END in previous:
        if previous.count(BEGIN) != 1 or previous.count(END) != 1:
            raise ValueError('Ambiguous existing Slot boot hook')
        start = previous.index(BEGIN)
        end = previous.index(END) + len(END)
        if end <= start:
            raise ValueError('Invalid existing Slot boot hook')
        return previous[:start] + block + previous[end:]
    if not previous:
        previous = b'#!/bin/sh\n'
    # Prepend after the shebang, so an existing exit cannot skip activation.
    split = previous.find(b'\n') + 1 if previous.startswith(b'#!') else 0
    if previous.startswith(b'#!') and not split:
        previous += b'\n'
        split = len(previous)
    return previous[:split] + block + previous[split:]


@contextlib.contextmanager
def writable_boot():
    mount = next((line.split() for line in MOUNTS.read_text().splitlines()
                  if line.split()[1] == '/boot'), None)
    readonly = mount is not None and 'ro' in mount[3].split(',')
    if readonly:
        subprocess.run(['mount', '-o', 'remount,rw', '/boot'], check=True)
    try:
        yield
    finally:
        if readonly:
            subprocess.run(['mount', '-o', 'remount,ro', '/boot'], check=True)


def managed_paths():
    return {'hook': HOOK, 'config': BASE / 'active.json', 'helper': BASE / 'boot.py'}


def capture(folder):
    """Retain exact previous hook/selection separately from the userdata snapshot."""
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {}
    for key, path in managed_paths().items():
        if path.is_symlink():
            raise ValueError('Refusing managed startup symlink: ' + str(path))
        entry = dict(path=str(path), exists=path.exists())
        if entry['exists']:
            if not path.is_file():
                raise ValueError('Startup path is not a file: ' + str(path))
            shutil.copy2(path, folder / key)
            entry.update(sha256=digest(path), mode=path.stat().st_mode & 0o777)
            if digest(folder / key) != entry['sha256']:
                raise RuntimeError('Startup backup checksum mismatch')
        manifest[key] = entry
    atomic(folder / 'manifest.json', json.dumps(manifest, indent=2).encode())
    return manifest


def restore(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    for key, path in managed_paths().items():
        entry = manifest[key]
        if entry['path'] != str(path) or (entry['exists'] and digest(folder / key) != entry['sha256']):
            raise ValueError('Invalid startup recovery copy')
    with writable_boot():
        for key, path in managed_paths().items():
            entry = manifest[key]
            if entry['exists']:
                atomic(path, (folder / key).read_bytes(), entry['mode'])
            elif path.exists():
                path.unlink()  # Exact three owned paths only; binaries/history stay.


def install(binary, sha256, stock_sha256):
    """Call with ES stopped, after capture() and the standard fresh snapshot."""
    if not all(re.fullmatch('[0-9a-f]{64}', value) for value in (sha256, stock_sha256)):
        raise ValueError('Invalid frontend SHA-256')
    if digest(binary) != sha256:
        raise ValueError('Frontend checksum mismatch')
    old_hook = HOOK.read_bytes() if HOOK.exists() else b''
    new_hook = hook_bytes(old_hook)
    # Preserve the actual firmware hash across later editor updates while mounted.
    config_path = BASE / 'active.json'
    if config_path.exists():
        stock_sha256 = json.loads(config_path.read_text())['stockSha256']
    target = BASE / ('emulationstation-' + sha256)
    if target.is_symlink():
        raise ValueError('Refusing frontend symlink')
    if target.exists():
        if digest(target) != sha256:
            raise ValueError('Retained frontend checksum mismatch')
    else:
        atomic(target, Path(binary).read_bytes(), 0o755)
    if digest(target) != sha256:
        raise RuntimeError('Persistent frontend copy failed verification')
    config = dict(version=1, binary=target.name, sha256=sha256,
                  stockSha256=stock_sha256, sourcePin=PIN)
    atomic(BASE / 'boot.py', Path(__file__).read_bytes())
    atomic(config_path, json.dumps(config, indent=2).encode())
    with writable_boot():
        atomic(HOOK, new_hook, HOOK.stat().st_mode & 0o777 if HOOK.exists() else 0o755)
    if HOOK.read_bytes() != new_hook:
        raise RuntimeError('Startup hook checksum mismatch')
    return dict(**config, hookSha256=digest(HOOK), helperSha256=digest(BASE / 'boot.py'),
                configSha256=digest(config_path))


def verify(expected):
    for path, sha in ((BASE / expected['binary'], expected['sha256']),
                      (HOOK, expected['hookSha256']),
                      (BASE / 'boot.py', expected['helperSha256']),
                      (BASE / 'active.json', expected['configSha256'])):
        if path.is_symlink() or digest(path) != sha:
            raise RuntimeError('Persistent startup verification failed: ' + str(path))


def firmware_sha256():
    """ES must be stopped; caller retains/rebinds the previous frontend on error."""
    if (BASE / 'active.json').is_file():
        return json.loads((BASE / 'active.json').read_text())['stockSha256']
    if any(line.split()[1] == str(OFFICIAL) for line in MOUNTS.read_text().splitlines()):
        subprocess.run(['umount', str(OFFICIAL)], check=True)
    return digest(OFFICIAL)


def activate():
    config = json.loads((BASE / 'active.json').read_text())
    sha = config['sha256']
    if (config.get('version') != 1 or not re.fullmatch('[0-9a-f]{64}', sha)
            or config['binary'] != 'emulationstation-' + sha):
        raise ValueError('Invalid persistent frontend selection')
    binary = BASE / config['binary']
    if binary.is_symlink() or digest(binary) != sha:
        raise ValueError('Persistent frontend checksum mismatch; keeping stock')
    current = digest(OFFICIAL)
    if current == sha:
        return dict(state='active', sha256=sha, alreadyActive=True)
    if current != config['stockSha256']:
        raise RuntimeError('Firmware frontend changed; keeping current firmware')
    if subprocess.run(['pidof', 'emulationstation'], capture_output=True).returncode == 0:
        raise RuntimeError('Frontend already running; activation requires a clean stop')
    if any(line.split()[1] == str(OFFICIAL) for line in MOUNTS.read_text().splitlines()):
        raise RuntimeError('Unexpected frontend mount; leaving it intact')
    subprocess.run(['mount', '--bind', str(binary), str(OFFICIAL)], check=True)
    if digest(OFFICIAL) != sha:
        subprocess.run(['umount', str(OFFICIAL)], check=True)
        raise RuntimeError('Mounted frontend checksum mismatch; reverted to stock')
    return dict(state='active', sha256=sha, alreadyActive=False)


def boot():
    """A failure must allow the ordinary firmware frontend to start."""
    import fcntl
    try:
        with (BASE.parent / 'editor-upload.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = activate()
    except Exception as error:
        result = dict(state='fallback', error=str(error))
    result['bootId'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    atomic(RECEIPT, json.dumps(result, indent=2).encode())
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] != ['boot']:
        raise SystemExit('Usage: boot.py boot')
    boot()
