"""Soft floor glow and contact-shadow textures for the home-console scene (MIT, generated).

The console and its TV stand on one floor line; the frontend draws `stage/floor.png` along it and
`stage/shadow.png` under each footprint. Both are plain radial alpha gradients: no artwork.
"""
import numpy as np
from PIL import Image
from .geometry import ROOT
from .stage import save_changed


def radial(width, height, colour, peak, power):
    y, x = np.mgrid[0:height, 0:width]
    r = np.hypot((x + .5 - width / 2) / (width / 2), (y + .5 - height / 2) / (height / 2))
    alpha = np.clip(1 - r, 0, 1) ** power * peak
    image = np.zeros((height, width, 4), np.uint8)
    image[..., :3] = colour
    image[..., 3] = np.round(alpha * 255).astype(np.uint8)
    return Image.fromarray(image, 'RGBA')


def build(slot=None):
    out = (slot or ROOT / 'theme/art-book-slot/_slot') / 'stage'
    out.mkdir(parents=True, exist_ok=True)
    save_changed(radial(256, 128, (6, 7, 9), .62, 1.5), out / 'shadow.png')
    save_changed(radial(512, 128, (150, 162, 180), .22, 2.0), out / 'floor.png')
    return out


if __name__ == '__main__':
    print('Floor textures:', build())
