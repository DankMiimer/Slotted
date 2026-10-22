"""Prepare real TV/table meshes for the tabletop GLES prototype, without decimation.

Blender 4.5 --background --factory-startup --disable-autoexec --python-exit-code 1
  --python tools/tabletop/prepare_assets.py -- OUTPUT_DIR [KEY ...]
Outputs are separate from the existing selected runtime models. Optional KEYs (e.g. oldtv)
prepare only those sources and keep the other prepared folders as they are.
"""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
SOURCES = {
    'panasonic': ROOT / 'third_party/models/damiantoons-panasonic/model.glb',
    'retro': ROOT / 'third_party/models/denys-retro-tv/model.glb',
    'pvm': ROOT / 'third_party/models/darkigorek-pvm/model.glb',
    'oldtv': ROOT / 'third_party/models/pibanezl-old-tv/model.glb',
    'table': ROOT / 'research/table-lena-wachs/wooden_table.glb',
    'tv-stand': ROOT / 'research/tv-stand-qu3st10n/tv_stand.glb',
    'wooden-table': ROOT / 'research/table-andrey/wooden_table_low_poly.glb',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_for(material):
    if not material or not material.use_nodes:
        return None
    bsdf = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf:
        return None
    links = bsdf.inputs['Base Color'].links
    if links and links[0].from_node.type == 'TEX_IMAGE':
        return links[0].from_node.image
    return None


def prepare(key, source):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in objects:
        world = o.matrix_world.copy()
        o.parent = None
        o.data.transform(world)
        o.matrix_world.identity()
        o.data.update()
    points = [v.co.copy() for o in objects for v in o.data.vertices]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    # Blender coordinates are x right / z up / -y forward. Convert once to
    # native x right / y up / z forward, in millimetres and with base at y=0.
    scale = 450 / (high.z - low.z) if key == 'retro' else 1000
    if key in ('table', 'tv-stand', 'wooden-table'):
        scale = 1500 / (high.x - low.x)
    center = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
    # The table mesh retains its top and rails; legs below the selected top slab
    # are excluded geometrically, not replaced with a procedural wood plane.
    table_cut = high.z - (high.z - low.z) * .12
    if key in ('table', 'tv-stand', 'wooden-table'):
        center.z = high.z

    def position(p):
        p = (p - center) * scale
        return (p.x, p.z, -p.y)

    folder = OUT / key
    folder.mkdir(parents=True, exist_ok=True)
    groups = []
    glass_points = []
    glass_source = [position(v.co) for o in objects
                    if o.name.startswith('Blank live CRT glass') or any(
                        m and 'Blank live CRT glass' in m.name for m in o.data.materials)
                    for v in o.data.vertices]
    gx0 = min((p[0] for p in glass_source), default=0)
    gx1 = max((p[0] for p in glass_source), default=1)
    gy0 = min((p[1] for p in glass_source), default=0)
    gy1 = max((p[1] for p in glass_source), default=1)
    totals = dict(source_triangles=0, retained_triangles=0)
    exported_images = {}
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        normals = mesh.corner_normals
        uv = mesh.uv_layers.active
        for material_index in sorted({t.material_index for t in mesh.loop_triangles}):
            material = mesh.materials[material_index] if material_index < len(mesh.materials) else None
            name = material.name if material else 'Default'
            glass = 'Blank live CRT glass' in name or obj.name.startswith('Blank live CRT glass')
            color = material.diffuse_color[:3] if material else (.6, .6, .6)
            hidden = False
            if material and material.use_nodes:
                shader = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if shader:
                    color = shader.inputs['Base Color'].default_value[:3]
                    hidden = shader.inputs['Alpha'].default_value == 0 and not shader.inputs['Alpha'].links
            color = tuple(min(1, max(0, c)) ** (1 / 2.2) for c in color)
            image = None if glass else image_for(material)
            texture = ''
            if image:
                if image.name not in exported_images:
                    texture = 'albedo-%02d.png' % len(exported_images)
                    image.filepath_raw = str(folder / texture)
                    image.file_format = 'PNG'
                    image.save()
                    exported_images[image.name] = texture
                texture = exported_images[image.name]
            corners = []
            for tri in mesh.loop_triangles:
                if tri.material_index != material_index:
                    continue
                totals['source_triangles'] += 1
                coords = [mesh.vertices[i].co for i in tri.vertices]
                if key == 'table' and min(p.z for p in coords) < table_cut:
                    continue
                totals['retained_triangles'] += 1
                for vi, li in zip(tri.vertices, tri.loops):
                    p = position(mesh.vertices[vi].co)
                    n = normals[li].vector
                    tex = uv.data[li].uv if uv else (0, 0)
                    tex = ((p[0]-gx0)/(gx1-gx0), (gy1-p[1])/(gy1-gy0)) if glass else (tex[0], 1-tex[1])
                    corners.append((*p, n.x, n.z, -n.y, *color, *tex))
                    if glass:
                        glass_points.append(p)
            # Compact exact corner tuples, chunked below GLES2's 16-bit limit.
            for first in range(0, len(corners), 60000):
                batch = corners[first:first + 60000]
                vertices, indices, lookup = [], [], {}
                for corner in batch:
                    packed = struct.pack('<11f', *corner)
                    if packed not in lookup:
                        lookup[packed] = len(vertices)
                        vertices.append(packed)
                    indices.append(lookup[packed])
                if not indices:
                    continue
                stem = 'part-%03d' % len(groups)
                path = folder / (stem + '.mesh')
                path.write_bytes(struct.pack('<8sIII', b'SCTABL1\0', len(vertices), len(indices), int(glass))
                                 + b''.join(vertices) + struct.pack('<%dH' % len(indices), *indices))
                groups.append(dict(file=path.name, texture=texture, glass=glass, hidden=hidden,
                                   object=obj.name, material=name, triangles=len(indices) // 3,
                                   vertices=len(vertices), sha256=sha(path)))
    bounds = [position(p) for p in points]
    registration = dict(
        id=key, source_sha256=sha(source), units='mm', groups=groups, **totals,
        bounds=[[min(p[i] for p in bounds) for i in range(3)],
                [max(p[i] for p in bounds) for i in range(3)]],
        source_objects=[dict(name=o.name, triangles=len(o.data.loop_triangles)) for o in objects],
        changes=['World transforms applied', 'X right / Y up / Z forward millimetres',
                 'Original geometry, UVs and base-color textures retained; no decimation',
                 'Source PBR maps retained in original GLB; runtime uses simple lighting'])
    if key == 'table':
        registration['changes'].append('Source tabletop/upper trim only; lower legs excluded')
    if glass_points:
        lo = [min(p[i] for p in glass_points) for i in range(3)]
        hi = [max(p[i] for p in glass_points) for i in range(3)]
        registration['glass'] = [lo, hi]
    (folder / 'scene.json').write_text(json.dumps(registration, indent=2) + '\n')
    glass = registration.get('glass', [[0,0,0],[0,0,0]])
    lines = ['SCTABLETOP1 ' + str(len(groups)),
             ' '.join(map(str, registration['bounds'][0] + registration['bounds'][1])),
             ' '.join(map(str, glass[0] + glass[1]))]
    lines += [g['file'] + ' ' + (g['texture'] or '-') + ' ' + str(int(g['glass']) | (2 if g['hidden'] else 0)) for g in groups]
    (folder / 'scene.txt').write_text('\n'.join(lines) + '\n')
    print('TABLETOP', key, len(groups), totals, 'bounds', registration['bounds'], flush=True)
    return registration


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    keys = sys.argv[sys.argv.index('--') + 2:] or list(SOURCES)
    registry = {key: prepare(key, SOURCES[key]) for key in keys}
    listed = OUT / 'sources.json'
    sources = json.loads(listed.read_text()) if listed.exists() and len(keys) < len(SOURCES) else {}
    sources.update({k:dict(path=str(SOURCES[k].relative_to(ROOT)), sha256=v['source_sha256']) for k,v in registry.items()})
    listed.write_text(json.dumps({k: sources[k] for k in SOURCES if k in sources}, indent=2) + '\n')
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from prepare_controls import prepare
    prepare(OUT)
