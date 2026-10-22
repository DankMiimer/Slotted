"""Create/verify an exact-path public source export. Never deploys or changes Git."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'PUBLICATION_MANIFEST.json'
UPLOAD_LIST = 'UPLOAD_PATHS.txt'
MAX_BYTES = 100 * 1024 * 1024
PRESERVE_BYTES = {'assets', 'theme', 'third_party', 'scene-layouts'}
PRESERVE_SUFFIXES = {'.png', '.wav', '.pcm', '.ttf', '.glb', '.mesh', '.texture', '.mask', '.tga', '.ico'}
BLOCKED_PARTS = {'.git', '.ssh', '__pycache__', '.venv', 'local-models', 'cache'}
BLOCKED_SUFFIXES = {'.pyc', '.pem', '.key', '.iso', '.rom', '.sav', '.srm', '.state', '.bios',
                    '.nes', '.sfc', '.smc', '.z64', '.n64', '.v64', '.nds', '.gba', '.gb', '.gbc',
                    '.cso', '.pbp', '.chd'}
PATTERNS = {
    'private key': re.compile(rb'-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----'),
    'GitHub token': re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})'),
    'OpenAI key': re.compile(rb'sk-(?:proj-)?[A-Za-z0-9_-]{40,}'),
    'private SSH target': re.compile(rb'\b[a-z_][a-z0-9_-]*@(?:10\.|192\.168\.|172\.(?:1[6-9]|2[0-9]|3[01])\.)[0-9.]+', re.I),
}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def json_write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def checkout_bytes(name, data):
    """Match committed checkout conventions without altering protected asset bytes."""
    path = PurePosixPath(name)
    if path.parts[0] in PRESERVE_BYTES or path.suffix in PRESERVE_SUFFIXES or b'\0' in data:
        return data
    data = data.replace(b'\r\n', b'\n')
    return data.replace(b'\n', b'\r\n') if name.endswith('.ps1') else data


def relative(value):
    """Portable path only; no traversal, shell pathspecs or Windows aliases."""
    path = PurePosixPath(value)
    if (not value or not path.parts or path.is_absolute() or path.as_posix() != value
            or any(p in ('', '.', '..') or any(c in p for c in ':\\\n\r*?[]') for p in path.parts)):
        raise ValueError('Invalid publication path: ' + repr(value))
    return path


def safe_file(root, name):
    path = root.joinpath(*relative(name).parts)
    path.resolve().relative_to(root.resolve())
    for item in (path, *path.parents):
        if item == root:
            break
        if item.is_symlink() or getattr(item, 'is_junction', lambda: False)():
            raise ValueError('Linked publication input: ' + name)
    if not path.is_file():
        raise ValueError('Missing publication file: ' + name)
    return path


def permitted(name, asset=False):
    path = relative(name)
    if (set(p.lower() for p in path.parts) & BLOCKED_PARTS
            or path.suffix.lower() in BLOCKED_SUFFIXES
            or any(p.lower().startswith('.env') and p != '.env.example' for p in path.parts)
            or name == 'tools/dev/device.txt'
            or name == 'theme/art-book-slot/_slot/launch/slot-launch'
            or (not asset and path.parts[0] in ('build', 'research', 'slot-v1.4.0'))):
        raise ValueError('Forbidden publication path: ' + name)


def inspect_file(path, name):
    if path.stat().st_size >= MAX_BYTES:
        raise ValueError('File reaches GitHub 100 MiB ceiling: ' + name)
    # Binary assets are hash-verified separately. Never print a matching secret.
    data = path.read_bytes()
    if b'\0' not in data[:8192]:
        for label, pattern in PATTERNS.items():
            if pattern.search(data):
                raise ValueError(label + ' detected in ' + name)


def inputs(root):
    config = json.loads((root / 'release/publication.json').read_text(encoding='utf-8'))
    names = [s for s in (root / 'release/public-files.txt').read_text(encoding='utf-8').splitlines()
             if s and not s.startswith('#')]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate publication allowlist entry')
    result = {}
    for name in names:
        permitted(name)
        result[name] = (safe_file(root, name), None)
    restores = set()
    for record in config['assets']:
        name = record['destination']
        permitted(name)
        if not name.startswith('assets/') or name in result:
            raise ValueError('Invalid/duplicate asset destination: ' + name)
        permitted(record['source'], asset=True)
        permitted(record['restore'], asset=True)
        if PurePosixPath(record['restore']).parts[0] not in ('build', 'research'):
            raise ValueError('Restore may only target build/research')
        if record['restore'].casefold() in restores:
            raise ValueError('Duplicate asset restore destination')
        restores.add(record['restore'].casefold())
        # Public clones have the durable assets, development checkouts have build inputs.
        source_name = name if (root / name).exists() else record['source']
        source = safe_file(root, source_name)
        if digest(source) != record['sha256']:
            raise ValueError('Protected asset hash differs: ' + source_name)
        result[name] = (source, record)
    from .derivatives import select
    result, config = select(root, result, config, safe_file, digest)
    folded = [name.casefold() for name in result]
    if len(folded) != len(set(folded)):
        raise ValueError('Case-colliding export paths')
    if MANIFEST in result or UPLOAD_LIST in result or 'assets/restore-map.json' in result:
        raise ValueError('Generated export files cannot be allowlisted as inputs')
    for name, (path, _) in result.items():
        inspect_file(path, name)
    return result, config


def verify(directory):
    root = Path(directory).resolve()
    state = json.loads(safe_file(root, MANIFEST).read_text(encoding='utf-8'))
    expected = set(state['files']) | {MANIFEST}
    actual = set()
    for path in root.rglob('*'):
        name = path.relative_to(root).as_posix()
        parts = path.relative_to(root).parts
        if parts[0] in ('.git', 'build', 'research', '.venv') or '__pycache__' in parts:
            continue
        if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise ValueError('Linked file in export: ' + name)
        if path.is_file():
            actual.add(name)
    if actual != expected:
        raise ValueError('Export file set differs; missing=%r extra=%r' % (sorted(expected-actual), sorted(actual-expected)))
    total = 0
    for name, record in state['files'].items():
        permitted(name)
        path = safe_file(root, name)
        inspect_file(path, name)
        if path.stat().st_size != record['bytes'] or digest(path) != record['sha256']:
            raise ValueError('Export checksum differs: ' + name)
        total += record['bytes']
    # Cross-check pinned build assets even when a snapshot manifest has been regenerated.
    config = json.loads((root / 'release/publication.json').read_text(encoding='utf-8'))
    restore = json.loads((root / 'assets/restore-map.json').read_text(encoding='utf-8'))
    if restore != config['assets']:
        raise ValueError('Asset restore map differs from publication config')
    for asset in restore:
        if digest(safe_file(root, asset['destination'])) != asset['sha256']:
            raise ValueError('Asset pin differs: ' + asset['destination'])
    from .derivatives import load
    seen = set()
    for derivative in load(root):
        name = derivative['destination']
        if name in seen or name not in state['files']:
            raise ValueError('Duplicate/unlisted derivative destination: ' + name)
        seen.add(name)
        if digest(safe_file(root, name)) != derivative['sha256']:
            raise ValueError('Public derivative pin differs: ' + name)
    return dict(files=len(expected), bytes=total, state='verified-source-export')


def export(output, root=ROOT):
    root = Path(root).resolve()
    output = Path(output).absolute()
    # Refuse existing paths (including dangling symlinks), never remove previous exports.
    if output.exists() or output.is_symlink():
        raise ValueError('Output already exists; choose a new empty path: ' + str(output))
    resolved = output.resolve()
    if resolved == root or root.is_relative_to(resolved):
        raise ValueError('Output must not contain the source checkout')
    if resolved.is_relative_to(root) and resolved.relative_to(root).parts[0] != 'build':
        raise ValueError('In-checkout exports must be under build/')
    report = output.parent / (output.name + '-audit.json')
    if report.exists() or report.is_symlink():
        raise ValueError('Audit report already exists: ' + str(report))
    selected, config = inputs(root)  # Preflight every input before creating output.
    output.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, (source, asset) in sorted(selected.items()):
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        source_hash = digest(source)
        if digest(destination) != source_hash:
            raise OSError('Copy verification failed: ' + name)
        if asset and source_hash != asset['sha256']:
            raise OSError('Asset changed during copy: ' + name)
        if not asset:
            data = destination.read_bytes()
            canonical = checkout_bytes(name, data)
            if name == 'release/publication.json' and json.loads(data) != config:
                canonical = (json.dumps(config, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
            if canonical != data:
                destination.write_bytes(canonical)
        records[name] = dict(bytes=destination.stat().st_size, sha256=digest(destination),
                             licenseContext=asset['license'] if asset else 'LICENSE_SCOPE.md; CREDITS.md')
    restore = output / 'assets/restore-map.json'
    restore.parent.mkdir(parents=True, exist_ok=True)
    json_write(restore, config['assets'])
    records['assets/restore-map.json'] = dict(bytes=restore.stat().st_size, sha256=digest(restore))
    upload = output / UPLOAD_LIST
    upload.write_text('\n'.join(sorted(set(records) | {MANIFEST, UPLOAD_LIST})) + '\n', encoding='utf-8', newline='\n')
    records[UPLOAD_LIST] = dict(bytes=upload.stat().st_size, sha256=digest(upload))
    json_write(output / MANIFEST, dict(schema=1, createdUTC=datetime.now(timezone.utc).isoformat(),
        edition='MIT original code; separately licensed assets including NonCommercial/ShareAlike',
        status='Development source snapshot; no binary; no device installation performed',
        files=records))
    result = verify(output)
    json_write(report, dict(**result, output=str(output),
        manifestSha256=digest(output / MANIFEST),
        filesAbove50MiB=[n for n, r in records.items() if r['bytes'] > 50*1024*1024],
        exclusions=['Git history/private handoffs', 'editorial/local-models', 'device settings/saves/snapshots',
                    'ROMs/BIOS/scraped game artwork', 'unreviewed research/build inputs']))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.verify) if args.verify else export(args.output)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
