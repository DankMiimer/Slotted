"""Built-in room surface textures for Slotted's floor, walls and ceiling (original, MIT).

    python tools/tabletop/make_surfaces.py [OUTPUT]   (default build/tabletop/assets/surfaces)

Writes seamless 1024 px PNGs and library.json (name, label, tile in mm, suggested surfaces).
Everything is generated here from seeded noise; no photographs or downloaded images. Noise is
white noise low-passed in frequency space, so every texture repeats exactly at its edges.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

N = 1024
ROOT = Path(__file__).resolve().parents[2]


def noise(cutoff, seed, stretch=(1.0, 1.0)):
    """Periodic smooth noise in [0, 1]; `cutoff` in cycles per tile, `stretch` (x, y) > 1
    smooths that axis (wood grain runs along x with a large x stretch)."""
    white = np.random.default_rng(seed).standard_normal((N, N))
    fy, fx = np.fft.fftfreq(N)[:, None] * N, np.fft.fftfreq(N)[None, :] * N
    radius = np.hypot(fx * stretch[0], fy * stretch[1])
    out = np.real(np.fft.ifft2(np.fft.fft2(white) * np.exp(-(radius / cutoff) ** 2)))
    return (out - out.min()) / (out.max() - out.min())


def fbm(seed, cutoffs=(4, 16, 64, 256), weights=(.45, .3, .17, .08)):
    return sum(w * noise(c, seed + i) for i, (c, w) in enumerate(zip(cutoffs, weights)))


def colour(rgb, shade):
    """rgb (3,) scaled by a (N, N) shade map."""
    return np.asarray(rgb, float)[None, None, :] * shade[..., None]


def planks(light, dark, seed, boards=8, joints=2):
    """Boards along x, `boards` across the tile, staggered butt joints; seamless both ways."""
    rng = np.random.default_rng(seed)
    grain = .55 * noise(220, seed, (14, 1)) + .3 * noise(60, seed + 1, (10, 1)) + .15 * noise(8, seed + 2)
    figure = .5 + .5 * np.sin(2 * np.pi * (np.arange(N)[:, None] / N * boards * 6 + 4 * noise(12, seed + 3, (6, 1))))
    image = np.zeros((N, N, 3))
    height = N // boards
    for b in range(boards):
        rows = slice(b * height, (b + 1) * height)
        tint = rng.uniform(.88, 1.1)
        shift = rng.integers(0, N)
        g = np.roll(grain[rows], shift, axis=1)
        f = np.roll(figure[rows], shift, axis=1)
        mix = np.clip(.55 * g + .45 * f, 0, 1)
        image[rows] = (np.asarray(light) * (1 - mix[..., None]) + np.asarray(dark) * mix[..., None]) * tint
        for x in (rng.integers(0, N) + np.arange(joints) * N // joints) % N:
            image[rows, x:x + 2] *= .45
        image[rows][:2] *= .5  # gap above each board
        image[b * height:b * height + 2] *= .5
    return image


def tiles(cells, base, grout, seed, grout_px=8, variation=.08, checker=None):
    rng = np.random.default_rng(seed)
    size = N // cells
    shade = .9 + .1 * fbm(seed)
    image = np.zeros((N, N, 3))
    for i in range(cells):
        for j in range(cells):
            rgb = np.asarray(checker[(i + j) % 2] if checker else base, float) * rng.uniform(1 - variation, 1 + variation)
            image[i * size:(i + 1) * size, j * size:(j + 1) * size] = rgb
    image *= shade[..., None]
    lines = np.zeros(N, bool)
    for k in range(cells):
        edge = k * size
        lines[[(edge + d) % N for d in range(-grout_px // 2, grout_px - grout_px // 2)]] = True
    mask = lines[:, None] | lines[None, :]
    image[mask] = colour(grout, .85 + .15 * noise(200, seed + 9))[mask]
    return image


def bricks(seed, courses=12, across=4, mortar=8):
    rng = np.random.default_rng(seed)
    height, width = N // courses, N // across
    texture = .82 + .18 * (.6 * noise(180, seed) + .4 * noise(30, seed + 1))
    image = np.zeros((N, N, 3))
    mask = np.zeros((N, N), bool)
    for c in range(courses):
        offset = (width // 2) * (c % 2)
        rows = slice(c * height, (c + 1) * height)
        mask[c * height:c * height + mortar] = True
        for k in range(across):
            x0 = (k * width + offset) % N
            rgb = np.asarray((.56, .24, .17)) * rng.uniform(.8, 1.12) + rng.uniform(-.03, .03, 3)
            columns = (x0 + np.arange(width)) % N
            image[rows][:, columns] = rgb
            mask[rows, (x0 + np.arange(-mortar // 2, mortar - mortar // 2)) % N] = True
    image *= texture[..., None]
    image[mask] = colour((.68, .66, .62), .8 + .2 * noise(220, seed + 5))[mask]
    return image


def paper(rgb, seed, mottle=.05, grain=.03):
    shade = 1 - mottle + mottle * noise(5, seed) + grain * (noise(320, seed + 1) - .5)
    return colour(rgb, shade)


def stripes(a, b, seed, period=128):
    x = np.arange(N) % period
    blend = np.clip((np.abs(x - period / 2) - period / 4) / 3 + .5, 0, 1)[None, :]
    image = np.asarray(a)[None, None, :] * blend[..., None] + np.asarray(b)[None, None, :] * (1 - blend[..., None])
    return image * (.97 + .03 * noise(300, seed))[..., None]


def carpet(rgb, seed):
    return colour(rgb, .78 + .14 * noise(380, seed) + .08 * noise(10, seed + 1))


def concrete(seed):
    rng = np.random.default_rng(seed)
    shade = .74 + .2 * fbm(seed)
    image = colour((.62, .62, .6), shade)
    for value in (.55, 1.25):
        spots = rng.random((N, N)) < .004
        image[spots] *= value
    return image


def ceiling_tiles(seed, cells=2):
    rng = np.random.default_rng(seed)
    image = colour((.86, .86, .83), .93 + .05 * noise(40, seed) + .02 * noise(400, seed + 1))
    image[rng.random((N, N)) < .03] *= .82
    size = N // cells
    for k in range(cells):
        edge = k * size
        for d in range(-3, 3):
            image[(edge + d) % N, :] *= .7
            image[:, (edge + d) % N] *= .7
    return image


LIBRARY = [
    # name, label, tile mm (the whole texture), suggested surfaces, generator
    ('oak-planks', 'Oak planks', 1600, ['floor'], lambda: planks((.70, .52, .33), (.46, .31, .18), 11)),
    ('walnut-planks', 'Walnut planks', 1600, ['floor'], lambda: planks((.42, .28, .18), (.22, .13, .08), 12)),
    ('grey-carpet', 'Grey carpet', 1000, ['floor'], lambda: carpet((.48, .48, .5), 13)),
    ('checker-tiles', 'Checkerboard tiles', 1200, ['floor'], lambda: tiles(4, None, (.55, .55, .52), 14, 6, .03, ((.9, .89, .86), (.12, .12, .13)))),
    ('stone-tiles', 'Stone tiles', 1600, ['floor'], lambda: tiles(4, (.6, .58, .54), (.42, .41, .39), 15, 8, .1)),
    ('terracotta-tiles', 'Terracotta tiles', 1200, ['floor'], lambda: tiles(4, (.66, .36, .24), (.62, .58, .52), 16, 8, .09)),
    ('concrete', 'Concrete', 2400, ['floor', 'wall'], lambda: concrete(17)),
    ('white-plaster', 'White plaster', 2000, ['wall', 'ceiling'], lambda: paper((.86, .85, .82), 18)),
    ('warm-plaster', 'Warm plaster', 2000, ['wall'], lambda: paper((.82, .74, .62), 19)),
    ('blue-paint', 'Blue paint', 2000, ['wall'], lambda: paper((.34, .45, .6), 20, .04)),
    ('green-paint', 'Green paint', 2000, ['wall'], lambda: paper((.42, .55, .44), 21, .04)),
    ('red-brick', 'Red brick', 900, ['wall'], lambda: bricks(22)),
    ('wood-panels', 'Wood panels', 1600, ['wall', 'ceiling'], lambda: planks((.66, .47, .3), (.45, .3, .19), 23).transpose(1, 0, 2)),
    ('striped-wallpaper', 'Striped wallpaper', 1000, ['wall'], lambda: stripes((.86, .82, .7), (.58, .66, .56), 24)),
    ('ceiling-tiles', 'Ceiling tiles', 1200, ['ceiling'], lambda: ceiling_tiles(25)),
]


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'build/tabletop/assets/surfaces'
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, label, tile, surfaces, make in LIBRARY:
        pixels = np.clip(make() * 255 + .5, 0, 255).astype(np.uint8)
        Image.fromarray(pixels, 'RGB').save(out / (name + '.png'), optimize=True)
        entries.append(dict(name=name, label=label, tile=tile, surfaces=surfaces))
        print(name)
    (out / 'library.json').write_text(json.dumps(dict(version=1, textures=entries), indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
