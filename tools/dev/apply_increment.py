#!/usr/bin/env python3
"""Device side: apply one owned theme increment and optionally bind a dev frontend.

    apply_increment.py TAR MANIFEST.json [--frontend BINARY SHA256]

EmulationStation must be stopped. Archive members must be relative theme paths;
every extracted file is hash-checked against the manifest. The official
/usr/bin/emulationstation is never written: a dev binary is bind-mounted over it
(reboot restores stock). Snapshot first with session_data.py backup NAME.
"""
import argparse, hashlib, json, subprocess, sys, tarfile
from pathlib import Path

THEME = Path('/userdata/themes/art-book-slot')
OFFICIAL = Path('/usr/bin/emulationstation')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--frontend', nargs=2, metavar=('BINARY', 'SHA256'))
    parser.add_argument('--theme', choices=('art-book-slot', 'Slotted'), default='art-book-slot')
    args = parser.parse_args()
    theme = THEME.parent / args.theme
    if subprocess.run(['pidof', 'emulationstation'], capture_output=True).returncode == 0:
        sys.exit('Stop EmulationStation first')
    expected = json.loads(args.manifest.read_text())
    with tarfile.open(args.archive) as archive:
        members = archive.getmembers()
        for m in members:
            target = (theme / m.name).resolve()
            if not m.isfile() or m.name.startswith('/') or '..' in Path(m.name).parts or not target.is_relative_to(theme.resolve()):
                sys.exit('Refusing archive member: ' + m.name)
            if m.name not in expected:
                sys.exit('Member not in manifest: ' + m.name)
        archive.extractall(theme, members=members, filter='data') if sys.version_info >= (3, 12) else archive.extractall(theme, members=members)
    bad = [name for name, entry in expected.items() if digest(theme / name) != entry['sha256']]
    if bad:
        sys.exit('Hash mismatch after extraction: ' + ', '.join(bad))
    report = dict(applied=len(expected))
    if args.frontend:
        binary, sha = Path(args.frontend[0]), args.frontend[1]
        if digest(binary) != sha:
            sys.exit('Frontend hash mismatch')
        mounts = Path('/proc/mounts').read_text()
        if f' {OFFICIAL} ' in mounts:
            subprocess.run(['umount', str(OFFICIAL)], check=True)
        binary.chmod(0o755)
        subprocess.run(['mount', '--bind', str(binary), str(OFFICIAL)], check=True)
        report['frontend'] = dict(binary=str(binary), sha256=digest(OFFICIAL))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
