"""Builds the generated parts of the theme.

    python -m tools.themebuild [theme dir]      (default: theme/art-book-slot)

Hand-written files (theme.xml, splash.xml, _slot/shelf-common.xml, ...) are left alone; this
writes the art, icons, sounds, fonts, shelf views and per-system theme.xml files around them.
"""
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

from . import band, consoles, icons, shells, shelves, stage
from .geometry import OPEN_SANS, RASTER_FORGE, ROOT, SHAPES, SLOT_MIT, SLOT2_MIT


def sounds(out):
    out.mkdir(parents=True, exist_ok=True)
    for name in ('insert', 'eject'):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', '48000', '-ac', '1',
                        '-i', str(SLOT_MIT / f'{name}.pcm'), '-ac', '2', str(out / f'{name}.wav')],
                       check=True)


def fonts(out):
    out.mkdir(parents=True, exist_ok=True)
    for name in ('OpenSans-Regular.ttf', 'OpenSans-SemiBold.ttf', 'OFL.txt'):
        shutil.copy2(OPEN_SANS / name, out / name)
    shutil.copy2(RASTER_FORGE / 'RasterForge-ES.ttf', out / 'RasterForge.ttf')
    shutil.copy2(RASTER_FORGE / 'LICENSE-CC0.txt', out / 'RasterForge-LICENSE-CC0.txt')


def main(theme_dir):
    slot = theme_dir / '_slot'
    slot.mkdir(parents=True, exist_ok=True)
    band.build(slot)
    consoles.build(slot)
    stage.build(slot)
    shells.build(slot, SHAPES)
    icons.build(slot)
    Image.new('RGBA', (1, 1), (255, 255, 255, 255)).save(slot / 'px.png')
    sounds(slot / 'sounds')
    fonts(slot / 'fonts')
    shelves.build(theme_dir, SHAPES)
    shutil.copy2(SLOT_MIT / 'LICENSE', slot / 'LICENSE-slot-mit.txt')
    shutil.copy2(SLOT2_MIT / 'LICENSE', slot / 'LICENSE-slot2-mit.txt')
    shutil.copy2(ROOT / 'LICENSE', theme_dir / 'LICENSE')
    print('built', theme_dir)


if __name__ == '__main__':
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'theme' / 'art-book-slot')
