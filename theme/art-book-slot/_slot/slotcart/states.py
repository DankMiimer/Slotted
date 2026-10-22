"""Cache the newest save-state screenshot as a small shelf photo. Never edits saves."""
import argparse
import json
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .library import EXTENSIONS, SKIP_DIRS, SYSTEMS

FONT = Path(__file__).resolve().parents[1] / 'fonts' / 'OpenSans-SemiBold.ttf'


def refresh(rom, saves=Path('/userdata/saves'), roms=Path('/userdata/roms')):
    rom, saves, roms = Path(rom), Path(saves), Path(roms)
    relative = rom.relative_to(roms)
    folders = {saves / relative.parent, saves / relative.parts[0]}
    candidates = [p for folder in folders if folder.is_dir() for p in folder.iterdir()
                  if p.is_file() and p.name.startswith(rom.stem)
                  and re.fullmatch(r'\.state(?:\d+|\.auto)?\.png', p.name[len(rom.stem):], re.I)]
    folder = rom.parent / 'media' / 'slotstates'
    output = folder / (rom.stem + '.png')
    manifest = folder / (rom.stem + '.json')
    if not candidates:
        output.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        return False
    source = max(candidates, key=lambda p: (p.stat().st_mtime_ns, str(p)))
    stat = source.stat()
    key = [str(source), stat.st_size, stat.st_mtime_ns, 1]
    try:
        if output.exists() and json.loads(manifest.read_text()) == key:
            return True
    except (OSError, ValueError):
        pass
    with Image.open(source) as image:
        picture = ImageOps.contain(image.convert('RGB'), (136, 104), Image.Resampling.LANCZOS)
    paper = Image.new('RGBA', (148, 134), '#eee9df')
    draw = ImageDraw.Draw(paper)
    draw.rectangle((6, 6, 141, 109), fill='#18181c')
    paper.paste(picture, (6 + (136-picture.width)//2, 6 + (104-picture.height)//2))
    draw.text((74, 120), 'SAVE STATE', fill='#514d48', font=ImageFont.truetype(str(FONT), 9), anchor='mm')
    tilted = paper.rotate(-3, resample=Image.Resampling.BICUBIC, expand=True)
    photo = Image.new('RGBA', (160, 148))
    photo.alpha_composite(tilted, ((160-tilted.width)//2, (148-tilted.height)//2))
    folder.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp.png')
    photo.save(temporary)
    temporary.replace(output)
    manifest.write_text(json.dumps(key), encoding='utf-8')
    return True


def refresh_many(games, saves=Path('/userdata/saves'), roms=Path('/userdata/roms')):
    count = 0
    for game in games:
        try:
            count += refresh(game.path, saves, roms)
        except (OSError, ValueError) as error:
            print('  save-state photo:', game.path.name, error)
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roms', type=Path, default=Path('/userdata/roms'))
    parser.add_argument('--saves', type=Path, default=Path('/userdata/saves'))
    parser.add_argument('--systems', nargs='+', default=list(SYSTEMS))
    parser.add_argument('--rom', type=Path)
    args = parser.parse_args()
    if args.rom:
        refresh(args.rom, args.saves, args.roms)
    else:
        count = 0
        for system in args.systems:
            if system not in SYSTEMS:
                parser.error('unsupported system: ' + system)
            for parent, dirs, files in os.walk(args.roms / system):
                dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and not d.startswith('.')]
                for name in files:
                    if name.lower().endswith(EXTENSIONS[SYSTEMS[system]] + ('.zip',)):
                        try:
                            count += refresh(Path(parent) / name, args.saves, args.roms)
                        except (OSError, ValueError) as error:
                            print('  save-state photo:', name, error)
        print('%d save-state photos ready' % count)


if __name__ == '__main__':
    main()
