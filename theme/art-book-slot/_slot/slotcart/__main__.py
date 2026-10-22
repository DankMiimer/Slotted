"""Bakes cartridge, PS1 disc and PSP UMD images for the Art Book Slot shelves.

    cd /userdata/themes/art-book-slot/_slot && python3 -m slotcart [options]

Each game gets <rom dir>/media/slotcarts/<rom name>.png, which the shelf shows instead of the
generic shell. Reruns only redo carts whose inputs changed (.slotcart.json next to them).

  --roms DIR       ROM root (default /userdata/roms)
  --systems LIST   comma-separated ES system folders (default: supported systems and hack folders)
  --labels DIR     a Slot-style Labels folder (<DIR>/GBA/<rom name>.png, ...) to prefer
  --only TEXT      only games whose file name contains TEXT
  --force          redo every cart
  --offline        use only what is already cached
  --jobs N         render processes (default: CPU count)
  --dry-run        show what would be done
"""
import argparse
import json
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

from PIL import Image

from . import discs, labels, pico8, render, shells, states, surfaces
from .library import SYSTEMS, CrcCache, scan
from .launchbox import LaunchBox

SLOT_DIR = Path(__file__).resolve().parents[1]
MANIFEST = '.slotcart.json'

_shapes = {}


def load_shapes():
    _shapes.update({p.name: render.Shape(p) for p in (SLOT_DIR / 'shapes').iterdir() if p.is_dir()})


# Console cartridge labels from ScreenScraper (Skraper's support texture) are the
# whole printed sticker, licence strips and seals included. Like LaunchBox scans
# they are fitted whole; beyond 15% ratio difference an image is cropped instead.
COMPLETE_LABEL_SHAPES = {'snes', 'snes-us', 'snes-tzakol', 'nes', 'n64', 'md', 'md-jp', 'md-ea', 'nds'}


def complete_label(outline, size, well):
    ratio = (size[0] / size[1]) / (well[0] / well[1])
    return outline in COMPLETE_LABEL_SHAPES and 1 / 1.15 <= ratio <= 1.15


def bake(job):
    """Runs in a worker: render one cart and write it atomically."""
    out, outline, colour, finish, kind, source, paper = job
    try:
        shape = _shapes[outline]
        shell = shells.Shell(tuple(colour), finish)
        if kind=='pico-cart':
            img=pico8.cartridge(shape,source,shell)
            tmp=out+'.part';img.save(tmp,'PNG',compress_level=6);os.replace(tmp,out)
            return out,None
        if kind=='pico-label':label=pico8.text_label(source)
        elif kind=='pico-browser':label=pico8.browser_label(shape.well_size)
        elif (shape.disc or shape.umd) and kind in ('text','logo'):
            label=discs.fallback(kind,source,tuple(paper),discs.number(Path(out).stem),shape.name)
        elif kind == 'text':
            label = labels.text_label(shape.well_size, source, tuple(paper))
        elif kind == 'logo':
            label = labels.logo_label(shape.well_size, source, tuple(paper))
        else:
            label = Image.open(source)
            if kind == 'cart-scan' or (kind == 'own' and complete_label(outline, label.size, shape.well_size)):
                # Keep the complete printed layout, including the small branding
                # at either edge; fitting a slightly different scan ratio clips it.
                label = label.resize(shape.well_size, Image.Resampling.LANCZOS)
        if shape.disc or shape.umd:
            flat=render.umd_texture(shape,label) if shape.umd else render.disc_texture(shape,label)
            raw=str(Path(out).with_suffix('.disc.png'));flat.save(raw+'.part','PNG');os.replace(raw+'.part',raw)
            native=str(Path(out).with_suffix('.disc.tga'))
            flat.resize((512,512),Image.Resampling.LANCZOS).save(native+'.part','TGA');os.replace(native+'.part',native)
            img=render.disc_poster(shape,flat)
        else:
            if shape.pico_sticker_crop:
                label=pico8.sticker(label,Path(source).stem if kind=='pico-label' else 'SPLORE' if kind=='pico-browser' else source if kind=='text' else Path(out).stem)
            img = render.face(shape, shell, label)
        tmp = out + '.part'
        img.save(tmp, 'PNG', compress_level=6)
        os.replace(tmp, out)
        return out, None
    except Exception as ex:  # one bad label must not stop the run
        return out, repr(ex)


@lru_cache(maxsize=None)
def shape_revision(outline):
    spec = json.loads((SLOT_DIR/'shapes'/outline/'shape.json').read_text())
    return spec.get('revision')


def key_for(outline, shell, plan):
    kind, source, paper = plan
    stamp = None
    if kind in ('own','pico-cart','pico-label'):
        st = os.stat(source)
        stamp = [st.st_size, st.st_mtime_ns if kind.startswith('pico-') else int(st.st_mtime)]
    revision = shape_revision(outline)
    version = [render.VERSION, revision] if revision else render.VERSION
    paper_key = paper if isinstance(paper, dict) else list(paper) if paper else None
    return json.dumps([version, outline, list(shell.colour), shell.finish, kind,
                       source, paper_key, stamp])


def load_manifest(folder):
    try:
        return json.loads((folder / MANIFEST).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def main(argv=None):
    ap = argparse.ArgumentParser(prog='slotcart', description=__doc__.splitlines()[0])
    ap.add_argument('--roms', default='/userdata/roms')
    ap.add_argument('--systems', default=','.join(SYSTEMS))
    ap.add_argument('--labels')
    ap.add_argument('--only')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--offline', action='store_true')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    ap.add_argument('--cache', default=os.path.expanduser('~/.cache/slotcart'))
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(line_buffering=True)  # progress shows up live when logged to a file

    started = time.time()
    systems = [s for s in args.systems.split(',') if s in SYSTEMS]
    cache = CrcCache(args.cache)
    games = scan(args.roms, systems, cache)
    cache.save()
    if args.only:
        games = [g for g in games if args.only.lower() in g.path.name.lower()]
    print('%d games in %s (%.0fs)' % (len(games), ', '.join(systems), time.time() - started))
    if not args.dry_run:
        print('%d save-state photos ready' % states.refresh_many(games, roms=Path(args.roms)))

    art = labels.ArtSet(args.cache, args.offline)
    carts = {kind: LaunchBox(args.cache, args.offline, platform=kind)
             for kind in sorted({g.kind for g in games} & {'snes', 'nes', 'n64', 'md', 'psx', 'dreamcast', 'psp', 'nds'})}
    overrides = {}
    for system in systems:
        for ini in (Path(args.roms) / system / 'media' / 'labels' / 'cart_shell.ini',
                    Path(args.labels or '/nonexistent') / 'cart_shell.ini'):
            if ini.exists():
                overrides.update(shells.parse_overrides(ini.read_text(encoding='utf-8', errors='replace')))

    faces = {}
    priority = {'own': 0, 'pico-cart':0,'pico-label':0,'pico-browser':0,
                'cart-scan': 1, 'disc-scan': 1, 'scan': 1, 'logo': 2, 'text': 3}
    def quality(plans):
        return priority[plans[0][0]], not any(p[0] == 'logo' for p in plans)
    for g in games:
        outline, shell = shells.choose(g.header, g.stem, overrides)
        embedded=pico8.plan(g) if g.kind=='pico8' else None
        plans = labels.candidates(g, art, args.labels, carts)
        if embedded:
            plans=[p for p in plans if p[0]=='own']+[embedded]+[p for p in plans if p[0]!='own']
        out_dir = g.dir / 'media' / 'slotcarts'
        out = out_dir / (g.stem + '.png')
        # Different dump formats share one shelf image. Select the richest plan
        # before checking freshness, so a cached logo cannot be replaced by text.
        previous = faces.get(out)
        if previous is None or quality(plans) < quality(previous[3]):
            faces[out] = (g, outline, shell, plans, out)
        if outline in ('snes','snes-us'):
            alternate=out.with_name(g.stem+'.tzakol.png')
            previous=faces.get(alternate)
            if previous is None or quality(plans)<quality(previous[3]):
                faces[alternate]=(g,'snes-tzakol',shell,plans,alternate)

    manifests, todo = {}, []
    for g, outline, shell, plans, out in faces.values():
        out_dir = out.parent
        manifest = manifests.setdefault(out_dir, load_manifest(out_dir))
        if not args.dry_run:
            surfaces.write_variant(out,outline)
            backing = out.with_suffix('.back.png')
            pixels = (SLOT_DIR / 'backings' / (outline + '.png')).read_bytes()
            if not backing.exists() or backing.read_bytes() != pixels:
                out_dir.mkdir(parents=True, exist_ok=True)
                backing.write_bytes(pixels)
        complete=out.exists() and (outline not in ('psx','dreamcast','psp') or (out.with_suffix('.disc.png').exists() and out.with_suffix('.disc.tga').exists()))
        if not args.force and complete and manifest.get(out.stem) == key_for(outline, shell, plans[0]):
            continue
        todo.append((g, outline, shell, plans, out))

    if len(faces) < len(games):
        print('%d unique cart faces (%d ROMs share existing stems)' % (len(faces),len(games)-len(faces)))
    elif len(faces)>len(games):print('%d cartridge faces including selectable styles'%len(faces))
    print('%d carts to bake, %d up to date' % (len(todo), len(faces) - len(todo)))
    if args.dry_run:
        for kind, n in Counter(t[3][0][0] for t in todo).most_common():
            print('  %-5s %d' % (kind, n))
        return 0
    if not todo:
        return 0

    def resolve(item):
        """Downloads what the first workable label plan needs (threads; network-bound)."""
        g, outline, shell, plans, out = item
        for plan in plans:
            kind, source, paper = plan
            if kind in ('cart-scan','disc-scan'):
                path = carts[g.kind].fetch(paper)
                if not path:
                    continue
                return item, plan, (kind, str(path), None)
            if kind in ('scan', 'logo') and not Path(source).is_absolute():
                path = art.fetch(source)
                if not path:
                    continue
                return item, plan, (kind, str(path), paper)
            return item, plan, plan
        return item, plans[-1], plans[-1]

    jobs, chosen = [], {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for n, (item, plan, local) in enumerate(pool.map(resolve, todo), 1):
            g, outline, shell, plans, out = item
            out.parent.mkdir(parents=True, exist_ok=True)
            chosen[str(out)] = (g, key_for(outline, shell, plan), plan[0])
            jobs.append((str(out), outline, shell.colour, shell.finish, local[0], local[1], local[2]))
            if n % 100 == 0:
                print('  labels %d/%d' % (n, len(todo)))

    kinds, failed = Counter(), []
    with Pool(args.jobs, initializer=load_shapes) as pool:
        for n, (out, error) in enumerate(pool.imap_unordered(bake, jobs, chunksize=4), 1):
            g, key, kind = chosen[out]
            if error:
                failed.append((g.path.name, error))
                continue
            kinds[kind] += 1
            manifests[Path(out).parent][Path(out).stem] = key
            if n % 100 == 0:
                print('  baked %d/%d' % (n, len(jobs)))

    for out_dir, manifest in manifests.items():
        if out_dir.exists():
            (out_dir / MANIFEST).write_text(json.dumps(manifest, indent=0, ensure_ascii=False), encoding='utf-8')

    print('baked %d carts in %.0fs: %s' % (sum(kinds.values()), time.time() - started,
                                         ', '.join('%s %d' % kv for kv in kinds.most_common())))
    for name, error in failed[:20]:
        print('  failed:', name, error)
    if kinds:
        print('Restart EmulationStation (or reload the theme) to see the new carts.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
