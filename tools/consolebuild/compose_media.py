"""Compose review sheets/GIFs for the physical media slice (MIT). Pillow only."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'build/media'
VARIANTS = ('snes', 'snes-us', 'nes', 'n64', 'md', 'md-jp', 'md-ea', 'nds', 'pico8')


def sheet(rows, columns, cell, path):
    w, h = cell
    image = Image.new('RGB', (w*len(columns), h*len(rows)+18), (14, 15, 18))
    draw = ImageDraw.Draw(image)
    for c, (label, _) in enumerate(columns):
        draw.text((c*w+4, 3), label, fill=(220, 220, 220))
    for r, row in enumerate(rows):
        for c, (_, source) in enumerate(columns):
            file = source(row)
            if file.exists():
                image.paste(Image.open(file).convert('RGB').resize(cell), (c*w, 18+r*h))
        draw.text((4, 22+r*h), row, fill=(255, 220, 60))
    image.save(path)


def main():
    frames = (0, 15, 30, 45, 60)
    sheet(VARIANTS, [('before %02d' % f, lambda v, f=f: OUT/'before'/v/('insert-%02d.png' % f)) for f in (0, 30, 60)] +
          [('after %02d' % f, lambda v, f=f: OUT/'after'/v/('insert-%02d.png' % f)) for f in (0, 30, 60)],
          (240, 160), OUT/'before-after.png')
    sheet(VARIANTS, [('insert %02d' % f, lambda v, f=f: OUT/'after'/v/('insert-%02d.png' % f)) for f in frames] +
          [('eject %02d' % f, lambda v, f=f: OUT/'after'/v/('eject-%02d.png' % f)) for f in frames],
          (192, 128), OUT/'poses.png')
    views = ('front', 'rear', 'side', 'top', 'bottom', 'three-quarter', 'seated')
    sheet(VARIANTS, [(view, lambda v, view=view: OUT/'media-review'/v/(view+'.png')) for view in views],
          (180, 120), OUT/'neutral.png')
    for v in VARIANTS:
        for mode in ('insert', 'eject'):
            pictures = [Image.open(OUT/'after'/v/('%s-scene-%02d.png' % (mode, i))).convert('RGB').resize((360, 240))
                        for i in range(61) if (OUT/'after'/v/('%s-scene-%02d.png' % (mode, i))).exists()]
            if pictures:
                pictures[0].save(OUT/'after'/v/(mode+'.gif'), save_all=True, append_images=pictures[1:],
                                 duration=30, loop=0)
    print('wrote', OUT/'before-after.png', OUT/'poses.png', OUT/'neutral.png')


if __name__ == '__main__':
    main()
