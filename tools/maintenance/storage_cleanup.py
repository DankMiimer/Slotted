"""Audited 2026-10-18 consolidation of the two retired Slot model worktrees.

`prepare` records current-model hashes, source checkpoints, copies needed source
inputs and writes a narrowly allowlisted generated-file removal manifest.
`prune` verifies the protected hashes and exact candidates before unlinking.
Git worktree removal is deliberately a separate explicit git command.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PARENT = ROOT.parent
REPORT = ROOT / 'build/storage-cleanup-20261018'
OLD = (PARENT / 'Slot_ESDE-models', PARENT / 'Slot_ESDE-next-models')
PROTECTED = (
    ROOT / 'theme', ROOT / 'third_party', ROOT / 'research',
    ROOT / 'build/textured', ROOT / 'build/model-quality/gbasp-neilvfx',
    ROOT / 'build/model-quality/local-models', ROOT / 'build/model-quality/browse',
    PARENT / 'Slotters/Research/gbasp3d',
)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


UNREADABLE = []


def files(root, tolerate_unreadable=False):
    if not root.exists():
        return
    for base, dirs, names in os.walk(root, followlinks=False):
        for name in list(dirs):
            if (Path(base) / name).is_symlink():
                if tolerate_unreadable:
                    UNREADABLE.append(str(Path(base) / name))
                    dirs.remove(name)
                    continue
                raise ValueError('Unexpected directory link: ' + str(Path(base) / name))
        for name in names:
            path = Path(base) / name
            if path.is_symlink():
                if tolerate_unreadable:
                    UNREADABLE.append(str(path))
                    continue
                raise ValueError('Unexpected file link: ' + str(path))
            try:
                path.stat()
            except OSError:
                if not tolerate_unreadable:
                    raise
                UNREADABLE.append(str(path))
                continue
            yield path


def save(name, value):
    (REPORT / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def verify():
    protected = json.loads((REPORT / 'protected-models.json').read_text())
    mismatches = [rel for rel, value in protected.items()
                  if '__pycache__' not in Path(rel).parts and Path(rel).suffix != '.pyc'
                  if not (PARENT / rel).is_file() or sha(PARENT / rel) != value['sha256']]
    if mismatches:
        raise ValueError('Protected asset changed or missing: ' + repr(mismatches[:8]))
    print('Protected files verified:', len(protected), flush=True)


def copy_verified(source, target):
    if target.exists():
        if sha(source) != sha(target):
            raise ValueError('Consolidation collision: ' + str(target))
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    digest = sha(source)
    if sha(target) != digest:
        raise ValueError('Copy verification failed: ' + str(target))
    return dict(source=str(source), target=str(target), bytes=target.stat().st_size, sha256=digest)


def candidate(path):
    """Only obsolete generated captures/payloads, never models or scraper work."""
    rel = path.relative_to(ROOT).parts
    if len(rel) < 3 or rel[0] != 'build':
        return False
    area = rel[1]
    # This closed set cannot overlap any protected prefix. Avoid resolving
    # 50,000 downloaded build-tool files against every protected asset root.
    if area not in ('shots', 'queued-models', 'queued-cartridges', 'phase-e', 'slotted-presentation'):
        return False
    if area == 'shots':
        # Retain root-level images and compact image summaries; raw sequences
        # beneath these old capture directories account for several GiB.
        return len(rel) > 3 and path.suffix.lower() in ('.bmp', '.png', '.tga') and not any(
            word in path.stem.lower() for word in ('grid', 'montage', 'comparison', 'contact'))
    if area in ('queued-models', 'queued-cartridges', 'phase-e'):
        return rel[2].startswith('frames-') and path.suffix.lower() in ('.bmp', '.png', '.tga')
    if area == 'slotted-presentation' and len(rel) == 3:
        return path.name.startswith(('prototype-payload-', 'emulationstation-')) or path.name == 'model-baseline.patch'
    return False


def prepare():
    if (REPORT / 'protected-models.json').exists():
        raise ValueError('Audit exists; use verify/prune instead of replacing it')
    REPORT.mkdir(parents=True, exist_ok=True)
    worktrees = subprocess.check_output(['git', '-C', str(ROOT), 'worktree', 'list', '--porcelain'], text=True)
    save('worktrees.json', dict(porcelain=worktrees))
    inventory = {}
    for root in (ROOT,) + OLD:
        inventory[root.name] = {p.relative_to(root).as_posix(): p.stat().st_size
                                for p in files(root, True) if '.git' not in p.relative_to(root).parts}
    save('inventory-before.json', inventory)
    save('unreadable-library-links.json', UNREADABLE)
    print('Inventoried files:', sum(map(len, inventory.values())), flush=True)

    # Preserve every tracked/untracked non-ignored source file in retired trees,
    # plus the active code/docs/tests (not the large current runtime assets).
    with zipfile.ZipFile(REPORT / 'source-checkpoint.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for root in (ROOT,) + OLD:
            listed = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-co', '--exclude-standard', '-z'])
            for raw in sorted(set(listed.decode('utf-8').split('\0')) - {''}):
                p = root / raw
                if root == ROOT and raw.split('/')[0] not in ('tools', 'docs', 'tests') and '/' in raw:
                    continue
                if p.is_file():
                    archive.write(p, root.name + '/' + raw)

    previous = {}
    for p in (OLD[1] / 'theme/art-book-slot/_slot/consoles').glob('*/model.glb'):
        previous[p.parent.name] = sha(p)
    save('previous-runtime-hashes.json', previous)

    copies = []
    # These are still the selected SNES/N64 sources and selectable GBA source.
    # Keep source archives, maps, registrations and original input paths together.
    for relative in ('research/snes', 'research/n64', 'research/gba',
                     'research/hardware-review/downloads'):
        for source in files(OLD[1] / relative):
            copies.append(copy_verified(source, ROOT / source.relative_to(OLD[1])))
    # Import the licence required by the retained CAD reference adapter.
    source = OLD[1] / 'research/hardware-review/independent/BOSL-LICENSE.txt'
    if source.exists():
        copies.append(copy_verified(source, ROOT / source.relative_to(OLD[1])))

    # Keep compact original evidence and scripts from ignored old build trees;
    # exclude obsolete mesh derivatives, payloads, raw captures and scan trials.
    for root in OLD:
        for source in files(root / 'build', True):
            if source.suffix.lower() in ('.py', '.sh', '.ps1', '.json', '.log', '.txt'):
                if source.stat().st_size < 2 * 1024 * 1024 and 'native' not in source.relative_to(root / 'build').parts:
                    copies.append(copy_verified(source, REPORT / 'historical-evidence' / root.name / source.relative_to(root / 'build')))
    save('verified-copies.json', copies)
    protected = {p.relative_to(PARENT).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p))
                 for folder in PROTECTED for p in files(folder)}
    save('protected-models.json', protected)
    finish()


def finish():
    if (REPORT / 'generated-removals.json').exists():
        raise ValueError('Removal manifest already exists')
    protected = json.loads((REPORT / 'protected-models.json').read_text())
    copies = json.loads((REPORT / 'verified-copies.json').read_text())
    removals = {p.relative_to(ROOT).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p))
                for area in ('shots', 'queued-models', 'queued-cartridges', 'phase-e', 'slotted-presentation')
                for p in files(ROOT / 'build' / area, True) if candidate(p)}
    save('generated-removals.json', removals)
    print(json.dumps(dict(protected_files=len(protected), consolidated_files=len(copies),
                         generated_removals=len(removals), reclaim_bytes=sum(x['bytes'] for x in removals.values()))), flush=True)


def prune():
    verify()
    removals = json.loads((REPORT / 'generated-removals.json').read_text())
    # Validate the whole transaction before the first deletion.
    paths = []
    for rel, value in removals.items():
        path = ROOT / rel
        resolved = path.resolve()
        if not resolved.is_relative_to((ROOT / 'build').resolve()) or not candidate(path):
            raise ValueError('Removal escapes explicit generated-file allowlist: ' + rel)
        if not path.is_file() or path.is_symlink() or path.stat().st_size != value['bytes'] or sha(path) != value['sha256']:
            raise ValueError('Removal candidate changed since audit: ' + rel)
        paths.append(path)
    for path in paths:
        path.unlink()
    verify()
    save('generated-removal-result.json', dict(files=len(paths), bytes=sum(x['bytes'] for x in removals.values())))
    print('Removed generated bytes:', sum(x['bytes'] for x in removals.values()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'finish', 'verify', 'prune'))
    {'prepare': prepare, 'finish': finish, 'verify': verify, 'prune': prune}[parser.parse_args().action]()
