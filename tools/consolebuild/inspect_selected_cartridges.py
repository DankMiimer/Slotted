"""Inspect the preserved October 2026 cartridge sources, without writing assets."""
import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import textured_blender as tb


def inspect(key):
    source = tb.ROOT / 'research/selected-cartridges-20261019' / key / 'full.glb'
    objects = tb.import_source(source)
    report = []
    out = tb.ROOT / 'build/cartridge-implementation-20261019/inspection' / key
    out.mkdir(parents=True, exist_ok=True)
    for name, obj in objects.items():
        mesh = obj.data
        mesh.calc_loop_triangles()
        lo, hi = tb.bounds([obj])
        materials = []
        for mat in mesh.materials:
            image, factor = tb.base_colour_image(mat)
            materials.append(dict(name=mat.name, factor=list(factor),
                image=tb.save_image(image, out / 'images' / image.name) if image else None))
        report.append(dict(name=name, low=list(lo), high=list(hi),
            triangles=len(mesh.loop_triangles), materials=materials))
    tb.write_corners(list(objects.values()), out, {})
    (out / 'inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    print('INSPECTED', key, json.dumps(report), flush=True)


if __name__ == '__main__':
    for key in sys.argv[sys.argv.index('--') + 1:]:
        inspect(key)
