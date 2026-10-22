"""Register live LCD surfaces to the approved front/open handheld renders.

Read the actual named LCD geometry, not hand-tuned rectangles. Coordinates are
normalized to the cropped render, retaining the model's perspective and aspect.
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

from .appearance import glb_positions
from .geometry import ROOT

PARTS = {'gb': ['LCD screen'], 'gbc': ['CGB LCD glass'],
         'gba': ['SP LCD glass'], 'nds': ['Top LCD', 'Bottom LCD'],
         'psp': ['PSP LCD glass']}


def project(points, lean):
    points = np.array(points, dtype=float).copy()
    y, z = points[:, 1].copy(), points[:, 2].copy()
    points[:, 1] = y*math.cos(lean)-z*math.sin(lean)
    points[:, 2] = y*math.sin(lean)+z*math.cos(lean)
    phi = math.radians(35)
    k = 1200/(1200-points[:, 1]*math.sin(phi)-points[:, 2]*math.cos(phi))
    return np.column_stack((360+points[:, 0]*k,
                            240+(points[:, 2]*math.sin(phi)-points[:, 1]*math.cos(phi))*k))


def corners(points, lean):
    centre = points.mean(axis=0)
    _, _, basis = np.linalg.svd(points-centre, full_matrices=False)
    # Every authored LCD uses the console's horizontal X axis.
    u = np.array([1., 0., 0.])
    v = basis[1].copy()  # width, height, then the thin glass thickness
    v = v-u*np.dot(u, v)
    v /= np.linalg.norm(v)
    if project([centre+v], lean)[0, 1] > project([centre], lean)[0, 1]:
        v = -v
    normal = np.cross(u, v)
    camera = np.array([0., math.sin(math.radians(35)+lean), math.cos(math.radians(35)+lean)])
    if np.dot(normal, camera) < 0:
        normal = -normal
    a, b, c = points@u, points@v, points@normal
    return np.array([u*x+v*y+normal*c.max()
                     for x, y in [(a.min(), b.max()), (a.max(), b.max()),
                                  (a.max(), b.min()), (a.min(), b.min())]])


def build(slot):
    slot = Path(slot)
    result = {}
    for model, names in PARTS.items():
        source = slot/'stage/front'/(model+'-front.png')
        with Image.open(source) as image:
            bounds = image.getchannel('A').getbbox()
            if not bounds or bounds[0] == 0 or bounds[1] == 0 or bounds[2] == image.width or bounds[3] == image.height:
                raise ValueError('Clipped front render: '+model)
            # Keep identical pixels byte-for-byte across Pillow encoders.
            from .stage import save_changed
            save_changed(image.crop(bounds), source.with_name(model+'.png'))
        parts = dict(glb_positions(slot/'consoles'/model/'model.glb'))
        lean = -math.radians(35) if model in ('gb', 'gbc', 'psp') else 0
        quads,physical = [],[]
        for name in names:
            points=corners(parts[name], lean)
            physical.append(points.round(7).tolist())
            quad = project(points, lean)
            quad -= np.array(bounds[:2])
            quad /= np.array([bounds[2]-bounds[0], bounds[3]-bounds[1]])
            if not np.all((quad >= 0) & (quad <= 1)):
                raise ValueError('LCD leaves housing: '+model)
            quads.append(quad.round(7).tolist())
        result[model] = dict(bounds=list(bounds[:2]), size=[bounds[2]-bounds[0], bounds[3]-bounds[1]], quads=quads,points=physical)
    (slot/'stage/screens.json').write_text(json.dumps(result, indent=2)+'\n')
    header = ['// Generated from approved LCD geometry by tools.themebuild.screens. MIT.',
              '#pragma once', 'typedef struct { const char* name; int count; float bounds[4]; float quad[2][8]; float points[2][12]; } SlotScreenSpec;',
              'static const SlotScreenSpec slotScreens[] = {']
    for model, entry in result.items():
        quads = ['{'+','.join(str(v)+'f' for point in q for v in point)+'}' for q in entry['quads']]
        if len(quads) == 1:
            quads.append('{}')
        bounds=','.join(str(v)+'.f' for v in entry['bounds']+entry['size'])
        points=['{'+','.join(str(v)+'f' for point in p for v in point)+'}' for p in entry['points']]
        if len(points)==1:points.append('{}')
        header.append('    {"'+model+'",'+str(len(entry['quads']))+',{'+bounds+'},{'+','.join(quads)+'},{'+','.join(points)+'}},')
    header += ['};', '']
    target = ROOT/'tools/frontend/overlay/es-app/src/components/SlotScreens.h'
    target.write_text('\n'.join(header))
    return result


if __name__ == '__main__':
    print('Registered LCDs:', ', '.join(build(ROOT/'theme/art-book-slot/_slot')))
