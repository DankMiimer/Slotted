"""Owned theme files that differ from the device, for one deploy increment.

    python -m tools.frontend.deploy_set DEVICE_HASHES OUTPUT.tar [--family NAME ...]

DEVICE_HASHES is `sha256sum` output from /userdata/themes/art-book-slot. Only
owned runtime paths are considered: the presentation package (stage, XML,
credits, launch gate), the standalone helper, appearance derivatives, console
specs/bands and the named console families; `--tabletop` adds the prepared
tabletop scene from build/tabletop/assets. Unrelated local workspace changes
(scrapers, video, local-models) are never included. Does not deploy.
"""
import argparse, hashlib, json, tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEME = ROOT / 'theme/art-book-slot'
FIXED = ('theme.xml', '_slot/shelf-common.xml', '_slot/slot-interaction.xml', '_slot/status.xml',
         '_slot/MODEL_CREDITS.txt', '_slot/launch/common.sh', '_slot/launch/frontend-owned.sh',
         '_slot/launch/slot-launch', '_slot/consoles/specs.json')


TABLETOP = ROOT / 'build/tabletop/assets'


def tabletop():
    """Prepared tabletop runtime files keyed by their `_slot/tabletop/` theme path.

    TVs with an authored layout, plus the small TVs that borrow the Panasonic's.
    """
    tvs = sorted({p.stem.split('-', 1)[1] for p in (TABLETOP / 'layouts').glob('*.scene')} | {'pvm', 'oldtv'})
    folders = ['table', 'tv-stand', 'wooden-table', 'snes', 'snes-us', 'n64', 'nes', 'md', 'md-jp', 'layouts'] + tvs
    return {'_slot/tabletop/' + p.relative_to(TABLETOP).as_posix(): p
            for folder in folders if (TABLETOP / folder).is_dir()
            for p in sorted((TABLETOP / folder).iterdir()) if p.is_file()}


def owned(families, baker=False):
    paths = [THEME / p for p in FIXED]
    paths += sorted((THEME/'_slot/cartridges').glob('*.xml'))
    paths += sorted(p for p in (THEME / '_slot/stage').rglob('*') if p.is_file() and p.suffix in ('.png', '.json', '.xml'))
    paths += [THEME / '_slot/appearance/manifest.json']
    if baker:
        paths += [THEME / '_slot/slotcart' / (name+'.py') for name in
                  ('__main__','discs','labels','launchbox','library','previews','shells','render','pico8')]
    for family in families:
        paths += sorted((THEME / '_slot/appearance').glob(f'*/*/band-console-{family}.png'))
        paths += sorted((THEME / '_slot/appearance').glob(f'*/*/consoles/{family}/*'))
    for family in families:
        paths.append(THEME / '_slot' / f'band-console-{family}.png')
        paths += [THEME / family / 'theme.xml', THEME / (family+'h') / 'theme.xml', THEME / '_slot' / f'shelf-{family}.xml',
                  THEME / '_slot/shells' / f'{family}.png', THEME / '_slot/shells' / f'{family}.disc.png',
                  THEME / '_slot/shells' / f'{family}.disc.tga', THEME / '_slot/backings' / f'{family}.png']
        paths += sorted(p for p in (THEME / '_slot/shapes' / family).glob('*') if p.is_file())
        # Editing masters (*-master/*-physical, media GLBs) are not runtime files.
        folder=THEME/'_slot/consoles'/family
        if folder.exists():
            paths += sorted(p for p in folder.iterdir() if p.is_file()
                            and not p.name.endswith(('-master.glb', '-physical.glb'))
                            and not (p.suffix=='.glb' and p.name.startswith('media')))
    return sorted(set(p for p in paths if p.is_file()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('hashes', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--family', action='append', default=[])
    parser.add_argument('--baker', action='store_true', help='include reviewed media-baker runtime changes')
    parser.add_argument('--tabletop', action='store_true', help='include prepared tabletop scene assets')
    args = parser.parse_args()
    device = {}
    for line in args.hashes.read_text().splitlines():
        digest, path = line.split(None, 1)
        device[path.strip()[2:] if path.strip().startswith('./') else path.strip()] = digest
    sources = {path.relative_to(THEME).as_posix(): path for path in owned(args.family, args.baker)}
    if args.tabletop:
        sources.update(tabletop())
    changed = {}
    for relative, path in sources.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if device.get(relative) != digest:
            changed[relative] = dict(sha256=digest, device=device.get(relative))
    with tarfile.open(args.output, 'w') as archive:
        for relative in sorted(changed):
            path = sources[relative]
            info = archive.gettarinfo(str(path), arcname=relative)
            info.uid = info.gid = 0; info.uname = info.gname = 'root'
            info.mode = 0o755 if path.suffix == '.sh' or path.name == 'slot-launch' else 0o644
            with path.open('rb') as stream:
                archive.addfile(info, stream)
    args.output.with_suffix('.json').write_text(json.dumps(changed, indent=2) + '\n', newline='\n')
    for relative in sorted(changed):
        print(('new ' if changed[relative]['device'] is None else 'chg ') + relative)
    print(len(changed), 'files ->', args.output)


if __name__ == '__main__':
    main()
