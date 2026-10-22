"""Restore hash-verified public assets to build/research, without replacing files."""
import json
from pathlib import Path
import shutil

from tools.publication.export import ROOT, digest, permitted, relative, safe_file


def restore(root=ROOT):
    root = Path(root).resolve()
    records = json.loads(safe_file(root, 'assets/restore-map.json').read_text(encoding='utf-8'))
    planned = []
    destinations = set()
    for item in records:
        name = item['restore']
        permitted(name, asset=True)
        if relative(name).parts[0] not in ('build', 'research'):
            raise ValueError('Restore destination must be under build/research: ' + name)
        if name.casefold() in destinations:
            raise ValueError('Duplicate asset restore destination: ' + name)
        destinations.add(name.casefold())
        source = safe_file(root, item['destination'])
        if digest(source) != item['sha256']:
            raise ValueError('Public asset hash differs: ' + item['destination'])
        target = root / name
        target.resolve().relative_to(root)
        for part in (target, *target.parents):
            if part == root:
                break
            if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
                raise ValueError('Linked restore path: ' + name)
        if target.exists():
            if not target.is_file() or digest(target) != item['sha256']:
                raise ValueError('Existing asset differs; preserve it before restoring: ' + name)
        else:
            planned.append((source, target, item['sha256']))
    # All conflicts/hashes are checked before any copies. Exclusive writes never overwrite.
    for source, target, expected in planned:
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open('rb') as src, target.open('xb') as dst:
            shutil.copyfileobj(src, dst)
        if digest(target) != expected:
            raise OSError('Restored copy verification failed: ' + str(target))
    return dict(copied=len(planned), alreadyPresent=len(records)-len(planned))


if __name__ == '__main__':
    print(json.dumps(restore(), indent=2))
