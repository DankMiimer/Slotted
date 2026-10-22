"""Register the chosen model's existing power-slider (and N64 dust-flap) triangles; no source edits."""
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[2]
# Source power-control nodes and their travel when switched on (console mm, +Z =
# front); optional power-indicator nodes are registered separately (led.control).
CONTROLS = {'snes': (('PAL power slider',), [0, 0, -6], ()), 'snes-us': (('US power slider',), [0, 0, -6], ()),
            'n64': (('N64 power slider',), [0, 0, 7], ()),
            # The first front button is POWER (models.py); its printed label moves with it.
            'nes': (('Front control button', 'POWER'), [0, 0, -2], ('Power LED',)),
            # The slider sits mid-recess; ON is the left end (models.py: 12 units, 2.055/mm).
            'md': (('Power slider',), [-12 / (224 / 109), 0, 0], ('Power indicator window',)),
            'md-jp': (('Power slider',), [-12 / (224 / 109), 0, 0], ('Power indicator window',))}


def flap_data(fnv, count, power):
    """Text registration of the two N64 dust flaps from the generated n64-data.h."""
    text = (ROOT / 'tools/slotlaunch/n64-data.h').read_text()
    def numbers(name):
        found = re.search(r'\b' + name + r'\b[^=]*=\s*(\{.*?\}|[^;{]+);', text, re.S)
        assert found, 'Missing ' + name
        return [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?(?:e-?\d+)?', found.group(1))]
    lines = ['SCFLAPS1 %d %r %r 2' % (fnv, numbers('n64_flap_clearance')[0], numbers('n64_cart_slot')[0])]
    for i in range(2):
        first, length = map(int, numbers('n64_flap_range_%d' % i))
        assert first % 3 == 0 and length % 3 == 0 and first + length <= count, 'Flap range outside the mesh'
        assert not set(range(first // 3, (first + length) // 3)) & set(power), 'Flap overlaps the power slider'
        hinge, profile = numbers('n64_flap_hinge_%d' % i), numbers('n64_flap_profile_%d' % i)
        # n64_flaps_draw: flap 0 opens on the -Z side of the slot, flap 1 on +Z.
        lines.append(' '.join(map(repr, [first, length, hinge[0], hinge[1], 1 if i else -1, len(profile) // 2] + profile)))
    return '\n'.join(lines) + '\n'


def prepare(output, model='snes'):
    folder = ROOT / 'theme/art-book-slot/_slot/consoles' / model
    raw = (folder / 'model.glb').read_bytes()
    length = struct.unpack_from('<I', raw, 12)[0]
    gltf = json.loads(raw[20:20 + length])
    binary = raw[28 + length:]
    def accessor(index):
        a = gltf['accessors'][index]; v = gltf['bufferViews'][a['bufferView']]
        code = {5126: 'f', 5123: 'H', 5125: 'I'}[a['componentType']]
        size = {'SCALAR': 1, 'VEC3': 3}[a['type']]
        start = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = v.get('byteStride', struct.calcsize(code) * size)
        return [struct.unpack_from('<' + code * size, binary, start + i * stride) for i in range(a['count'])]
    names, travel, indicator = CONTROLS[model]
    mesh = (folder / 'model.mesh').read_bytes(); vertices, count = struct.unpack_from('<II', mesh, 8)
    points = [struct.unpack_from('<3f', mesh, 20 + i * 36) for i in range(vertices)]
    indices = struct.unpack_from('<' + str(count) + 'H', mesh, 20 + vertices * 36)
    # Runtime triangles bucketed by centroid; a source triangle matches when each of
    # its vertices lies within 0.01 units of the runtime triangle's (float rounding).
    def centroid(tri):
        return tuple(sum(p[k] for p in tri) / 3 for k in range(3))
    def close(a, b):
        return all(any(sum((p[k] - q[k]) ** 2 for k in range(3)) < 1e-4 for q in b) for p in a)
    def degenerate(tri):
        # Zero-area source triangles are invisible and absent from runtime exports.
        u, v = ([tri[i][k] - tri[0][k] for k in range(3)] for i in (1, 2))
        return sum(c * c for c in (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])) < 1e-12
    cells = {}
    for t in range(count // 3):
        tri = [points[k] for k in indices[3 * t:3 * t + 3]]
        cells.setdefault(tuple(round(c) for c in centroid(tri)), []).append((t, tri))
    def register(nodes):
        selected = set()
        for name in nodes:
            node = next(n for n in gltf['nodes'] if n.get('name') == name)
            assert not any(k in node for k in ('matrix', 'translation', 'rotation', 'scale')), 'Bake source transform before registering'
            for primitive in gltf['meshes'][node['mesh']]['primitives']:
                vertex = accessor(primitive['attributes']['POSITION']); faces = [v[0] for v in accessor(primitive['indices'])]
                for i in range(0, len(faces), 3):
                    tri = [[c * 100 for c in vertex[index]] for index in faces[i:i + 3]]
                    if degenerate(tri):
                        continue
                    x, y, z = (round(c) for c in centroid(tri))
                    found = [t for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
                             for t, other in cells.get((x + dx, y + dy, z + dz), ()) if close(tri, other) and close(other, tri)]
                    assert found, 'Every source control triangle must match a runtime triangle: ' + name
                    selected.update(found)
        return sorted(selected)
    selected = register(names)
    fnv = 14695981039346656037
    for byte in mesh:
        fnv = ((fnv ^ byte) * 1099511628211) & ((1 << 64) - 1)
    target = Path(output) / model; target.mkdir(parents=True, exist_ok=True)
    def write(path, triangles):
        path.write_bytes(struct.pack('<8sQI', b'SCSWCH1\0', fnv, len(triangles)) + struct.pack('<' + str(len(triangles)) + 'I', *triangles))
    write(target / 'power.control', selected)
    report = dict(source_mesh_sha256=hashlib.sha256(mesh).hexdigest(), source_glb_sha256=hashlib.sha256(raw).hexdigest(),
                  node=' + '.join(names), triangles=len(selected), travel_mm=travel)
    if indicator:
        lit = register(indicator)
        assert not set(lit) & set(selected), 'Indicator overlaps the power control'
        write(target / 'led.control', lit)
        report['indicator'] = dict(node=' + '.join(indicator), triangles=len(lit))
    if model == 'n64':
        (target / 'flaps.control').write_text(flap_data(fnv, count, selected), newline='\n')
        report['flaps'] = 'tools/slotlaunch/n64-data.h front/rear dust flap ranges, hinges and profiles'
    (target / 'controls.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
    print(model, ' + '.join(names), len(selected), 'original triangles registered; sources unchanged')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/tabletop/assets')
    parser.add_argument('--model', choices=tuple(CONTROLS), default='snes')
    args = parser.parse_args()
    prepare(args.output, args.model)
