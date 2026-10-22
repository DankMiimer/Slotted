"""Blender-side helpers for source-faithful textured models (Blender 4.5, MIT).

Imports a downloaded source with its UVs and images intact, registers it into
the native frame and writes per-corner geometry for tools/consolebuild/textured.py.
Run every adapter with --factory-startup --disable-autoexec: source scripts never run.

Native frame: x right, y up, z toward the viewer, in native units (mm * q).
Blender frame used here: native / 100 with Blender's z-up axes, so a glTF
export gives positions * 100 == native, as tools.themebuild.screens expects.
"""
import hashlib, json, math
from pathlib import Path
import bpy, numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]


def import_source(path):
    """Import a GLB/FBX/DAE; flatten parents; name meshes after their source node."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path = Path(path)
    if path.suffix.lower() == '.fbx':
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif path.suffix.lower() == '.dae':
        bpy.ops.wm.collada_import(filepath=str(path))
    else:
        bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update()
    meshes = {}
    for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
        name = o.parent.name if o.parent and o.parent.type != 'MESH' else o.name
        world = o.matrix_world.copy()
        o.parent = None
        o.data = o.data.copy()  # never edit shared source datablocks in place
        o.data.transform(world)
        o.matrix_world = Matrix.Identity(4)
        o['source_node'] = name
        meshes[name] = o
    for o in list(bpy.context.scene.objects):
        if o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    for o, name in [(o, n) for n, o in meshes.items()]:
        o.name = name
    bpy.context.view_layer.update()
    return {o.name: o for o in bpy.context.scene.objects if o.type == 'MESH'}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bounds(objects):
    points = [v.co for o in objects for v in o.data.vertices]
    return (Vector([min(p[i] for p in points) for i in range(3)]),
            Vector([max(p[i] for p in points) for i in range(3)]))


def ray(o, origin, direction):
    tree = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    hit = tree.ray_cast(Vector(origin), Vector(direction))
    return hit[0]


def to_native(objects, centre, mm_per_unit, q):
    """Uniform registration: source units -> Blender native/100 units."""
    k = mm_per_unit * q * .01
    transform = Matrix.Diagonal(Vector((k, k, k, 1))) @ Matrix.Translation(-Vector(centre))
    for o in objects:
        o.data.transform(transform)
        o.data.update()
    return k


def base_colour_image(material):
    """The image feeding Principled Base Color, with its factor (glTF importer layout)."""
    if not material or not material.use_nodes:
        return None, (1, 1, 1)
    bsdf = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf:
        return None, (1, 1, 1)
    socket = bsdf.inputs['Base Color']
    stack = [l.from_node for l in socket.links]
    while stack:
        node = stack.pop()
        if node.type == 'TEX_IMAGE' and node.image:
            return node.image, tuple(socket.default_value[:3]) if not socket.links else (1, 1, 1)
        stack += [l.from_node for s in node.inputs for l in s.links]
    return None, tuple(socket.default_value[:3])


def save_image(image, path):
    """Copy the source's original encoded image bytes; Blender never re-encodes them."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if image.packed_file:
        data = bytes(image.packed_file.data)
    else:
        data = Path(bpy.path.abspath(image.filepath)).read_bytes()
    suffix = '.png' if data[:8] == b'\x89PNG\r\n\x1a\n' else '.jpg' if data[:2] == b'\xff\xd8' else '.bin'
    target = path.with_suffix(suffix)
    target.write_bytes(data)
    return dict(name=image.name, size=list(image.size), colourspace=image.colorspace_settings.name,
                file=target.name, sha256=hashlib.sha256(data).hexdigest())


def write_corners(objects, folder, flags):
    """Per-corner native geometry + source UVs for the CPython packing stage.

    flags[name] holds 'moving' (hinged door group), 'material' override and
    'role' strings used by textured.py for blanking, swatches and paint."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    pos, nrm, uv, part, tri_part = [], [], [], [], []
    names = []
    materials = {}
    order = sorted(objects, key=lambda o: (bool(flags.get(o.name, {}).get('moving')), o.name))
    for index, o in enumerate(order):
        names.append(o.name)
        mesh = o.data
        mesh.calc_loop_triangles()
        layer = mesh.uv_layers.active
        for tri in mesh.loop_triangles:
            if tri.normal.length_squared < .5:
                continue
            material = mesh.materials[tri.material_index].name if mesh.materials else ''
            materials.setdefault(material, len(materials))
            tri_part.append((index, materials[material]))
            for li in tri.loops:
                p = mesh.vertices[mesh.loops[li].vertex_index].co
                n = mesh.corner_normals[li].vector
                if n.length_squared < .5:
                    n = tri.normal
                n = n.normalized()
                pos.append((p.x * 100, p.z * 100, -p.y * 100))
                nrm.append((n.x, n.z, -n.y))
                uv.append(tuple(layer.data[li].uv) if layer else (0., 0.))
    np.savez_compressed(folder / 'corners.npz', position=np.array(pos, np.float32),
                        normal=np.array(nrm, np.float32), uv=np.array(uv, np.float32),
                        triangle=np.array(tri_part, np.int32))
    images = {}
    for name in materials:
        material = bpy.data.materials.get(name)
        image, factor = base_colour_image(material)
        images[name] = dict(factor=list(factor),
                            image=save_image(image, folder / 'images' / image.name) if image else None)
    (folder / 'parts.json').write_text(json.dumps(dict(
        parts=[dict(name=n, **flags.get(n, {})) for n in names],
        materials=list(materials), images=images), indent=2) + '\n')
    return names


def copy_triangles(source,name,keep):
    """Copy selected source triangles, retaining material, UV and corner normals."""
    mesh=source.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active
    points=[];normals=[];texcoords=[];faces=[];materials=[]
    for tri in mesh.loop_triangles:
        if not keep(tri):continue
        first=len(points);faces.append((first,first+1,first+2));materials.append(tri.material_index)
        for li in tri.loops:
            points.append(mesh.vertices[mesh.loops[li].vertex_index].co.copy())
            normals.append(mesh.corner_normals[li].vector.copy())
            texcoords.append(uv.data[li].uv.copy() if uv else (0,0))
    data=bpy.data.meshes.new(name);data.from_pydata(points,[],faces);data.update()
    for material in mesh.materials:data.materials.append(material)
    layer=data.uv_layers.new(name='Source UVs')
    for i,value in enumerate(texcoords):layer.data[i].uv=value
    for polygon,material in zip(data.polygons,materials):polygon.material_index=material;polygon.use_smooth=True
    data.normals_split_custom_set(normals)
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    return obj


def export_geometry_glb(objects, path, q, physical=False, provenance=None):
    """Image-free GLB of the named parts: native frame (positions * 100 == native)
    for LCD/paint registration, or metres for editing. Never carries source images."""
    scene = bpy.context.scene
    scene['slotters_axes'] = 'x right, y up, z front'
    scene['slotters_native_units_per_mm'] = q
    scene['slotters_glb_to_metres'] = 1 if physical else 1 / (10 * q)
    for o in objects:
        for key, value in (provenance or {}).items():
            o[key] = value
        o['hinged'] = bool(o.get('hinged', False))
        o['printed'] = False
        o.matrix_world = Matrix.Scale(1 / (10 * q), 4) if physical else Matrix.Identity(4)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), use_selection=True, export_format='GLB',
                              export_materials='NONE', export_texcoords=False,
                              export_normals=True, export_animations=False, export_extras=True)
    for o in objects:
        o.matrix_world = Matrix.Identity(4)


def export_master_glb(objects, path):
    """Full-detail registered master with source materials, UVs and images."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), use_selection=True, export_format='GLB',
                              export_animations=False, export_extras=True)
