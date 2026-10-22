"""Read-only report of a downloaded source: parts, materials, maps and UV ranges.

Blender 4.5: blender -b --factory-startup --disable-autoexec --python source_report.py -- SOURCE.glb|.fbx REPORT.json
Never executes source scripts; the archive must already be inspected/extracted.
Processing code MIT. The source keeps its own licence.
"""
import bpy, json, sys
from pathlib import Path


def linked_image(socket, seen=None):
    """First image texture feeding a socket, through mix/multiply/normal nodes."""
    seen = seen or set()
    for link in socket.links:
        node = link.from_node
        if node in seen:
            continue
        seen.add(node)
        if node.type == 'TEX_IMAGE' and node.image:
            return node
        for s in node.inputs:
            found = linked_image(s, seen)
            if found:
                return found
    return None


def main():
    source, report_path = [Path(p) for p in sys.argv[sys.argv.index('--')+1:]]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if source.suffix.lower() == '.fbx':
        bpy.ops.import_scene.fbx(filepath=str(source))
    else:
        bpy.ops.import_scene.gltf(filepath=str(source))
    bpy.context.view_layer.update()
    parts = []
    for o in bpy.context.scene.objects:
        if o.type != 'MESH':
            continue
        world = o.matrix_world
        points = [world @ v.co for v in o.data.vertices]
        o.data.calc_loop_triangles()
        uv = o.data.uv_layers.active
        ranges = {}
        if uv:
            for tri in o.data.loop_triangles:
                name = o.data.materials[tri.material_index].name if o.data.materials else ''
                r = ranges.setdefault(name, [1e9, 1e9, -1e9, -1e9, 0])
                for li in tri.loops:
                    u, v = uv.data[li].uv
                    r[0] = min(r[0], u); r[1] = min(r[1], v); r[2] = max(r[2], u); r[3] = max(r[3], v)
                r[4] += 1
        parts.append(dict(name=o.name, parent=o.parent.name if o.parent else None,
                          low=[min(p[i] for p in points) for i in range(3)],
                          high=[max(p[i] for p in points) for i in range(3)],
                          vertices=len(o.data.vertices), triangles=len(o.data.loop_triangles),
                          uv_layers=[l.name for l in o.data.uv_layers],
                          colour_attributes=[a.name for a in o.data.color_attributes],
                          uv_ranges_by_material=ranges))
    materials = []
    for m in bpy.data.materials:
        entry = dict(name=m.name, users=m.users, blend=getattr(m, 'blend_method', ''))
        bsdf = next((n for n in (m.node_tree.nodes if m.use_nodes else []) if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf:
            for key in ('Base Color', 'Metallic', 'Roughness', 'Normal', 'Alpha', 'Emission Color'):
                socket = bsdf.inputs.get(key)
                if not socket:
                    continue
                node = linked_image(socket)
                value = socket.default_value
                entry[key] = dict(image=node.image.name if node else None,
                                  size=list(node.image.size) if node else None,
                                  default=list(value) if hasattr(value, '__len__') else value)
        materials.append(entry)
    images = [dict(name=i.name, size=list(i.size), colourspace=i.colorspace_settings.name,
                   packed=bool(i.packed_file)) for i in bpy.data.images if i.type == 'IMAGE']
    actions = [a.name for a in bpy.data.actions]
    report = dict(source=source.name, parts=parts, materials=materials, images=images, actions=actions)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print('REPORT', len(parts), 'parts', len(materials), 'materials', len(images), 'images')


if __name__ == '__main__':
    main()
