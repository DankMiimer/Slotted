"""Report welded physical islands in Wikiti's full source; never alter the input."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import textured_blender as tb

objects = tb.import_source(tb.ROOT / 'research/selected-cartridges-20261019/gbc/full.glb')
result = []
for name, obj in objects.items():
    mesh = obj.data
    parent = list(range(len(mesh.vertices)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(a, b):
        parent[find(a)] = find(b)
    coords = {}
    for v in mesh.vertices:
        key = tuple(round(x, 5) for x in v.co)
        if key in coords: union(v.index, coords[key])
        coords[key] = v.index
    for e in mesh.edges: union(*e.vertices)
    groups = {}
    for v in mesh.vertices: groups.setdefault(find(v.index), []).append(v.index)
    for indices in groups.values():
        if len(indices) < 8: continue
        lo = [min(mesh.vertices[i].co[a] for i in indices) for a in range(3)]
        hi = [max(mesh.vertices[i].co[a] for i in indices) for a in range(3)]
        result.append(dict(object=name, root=find(indices[0]), vertices=len(indices), low=lo, high=hi))
out = tb.ROOT / 'build/cartridge-implementation-20261019/inspection/gbc/components.json'
out.write_text(json.dumps(result, indent=2) + '\n')
print('COMPONENTS', json.dumps(result), flush=True)
