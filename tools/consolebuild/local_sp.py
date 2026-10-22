"""Prepare the user-supplied NeilVFX SP for local use, never redistribution.

Blender 4.5: --disable-autoexec --python local_sp.py -- source.blend output
Processing code MIT. Input geometry retains its Editorial License (no AI).
Outputs belong under ignored build/, with the untouched full source retained.
"""
import sys, math, json, struct, hashlib
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE_URL = 'https://www.cgtrader.com/free-3d-models/electronics/other/gameboy-advance-sp'
# The supplied scene includes a separate Game Pak. The existing animated,
# ROM-labelled Game Pak replaces it; internal electronics never become a shell.
CART = {'Case_3', 'Connect.1', 'Game_Boy_Logo', 'Model_Info', 'Ninteno_Logo',
        'Platine.1', 'Sticker', 'Würfel', 'Würfel.1', 'Würfel_1', 'Würfel_2', 'Würfel_3',
        'Klon.1', 'Klon.1_1'}
LID = {'Backplate', 'Case_2', 'Glass', 'Screen', 'Rubber', 'Nintendo', 'Ebene', 'Ankle_', 'Ankle_small'}
PAINT = {'Case', 'Case_1', 'Case_2', 'Backplate', 'Ankle_', 'Ankle_small', 'Small_Plate', 'Symmetrie'}
BUTTONS = {'Cross', 'A-Button', 'B-Button', 'Select-Button', 'Start-Button', 'Light_Btton', 'L_Trigger', 'R_Trigger'}
COLOURS = {'shell': (.18, .34, .68), 'buttons': (.44, .46, .51),
           'black': (.025, .033, .045), 'metal': (.53, .56, .60),
           'green': (.22, .75, .21), 'red': (.65, .06, .035), 'ink': (.82, .84, .88)}


def material(name):
    m = bpy.data.materials.new(name); m.diffuse_color = (*COLOURS[name], 1)
    return m


def export_glb(objects, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                             export_extras=True, export_animations=False)


def main():
    source, output = [Path(s) for s in sys.argv[sys.argv.index('--')+1:]]
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    # Uniform 82 mm base width. Native units use 224/82 units per mm.
    # Locate the original source Game Pak's label on the existing animation's
    # underside plane, keeping its connector-first insertion choreography.
    q = 224 / (4.00363492965698 + 3.44072699546814)
    cx = (4.00363492965698 - 3.44072699546814) / 2
    offset_y = -26.03 * (224/82) - (-.953876376152039) * q
    offset_z = 24.45 * (224/82) + (-2.0875059068203) * q
    transform = Matrix(((q*.01, 0, 0, -cx*q*.01),
                        (0, q*.01, 0, -offset_z*.01),
                        (0, 0, q*.01, offset_y*.01), (0, 0, 0, 1)))
    mats = {name: material(name) for name in COLOURS}
    kept = []
    for o in objects:
        if o.name in CART:
            bpy.data.objects.remove(o, do_unlink=True); continue
        o.data.transform(transform @ o.matrix_world); o.matrix_world = Matrix.Identity(4)
        o['source_part'] = o.name; o['hinged'] = o.name in LID; o['paint'] = o.name in PAINT
        role = 'shell' if o.name in PAINT else 'buttons' if o.name in BUTTONS else 'black'
        if o.name.startswith('Screw') or o.name in {'Nintendo', 'Symmetrie.1'}: role = 'metal'
        if o.name == 'Green_Light': role = 'green'
        if o.name == 'Red_Light': role = 'red'
        if o.name in {'License_Sticker', 'Charging_Info.1'}: role = 'ink'
        o.data.materials.clear(); o.data.materials.append(mats[role])
        for p in o.data.polygons: p.material_index = 0
        kept.append(o)
    # Screen and Glass are continuous full lens planes in this OBJ, without
    # the original C4D shader assignments. Keep the outer black lens and put
    # an accurately sized 3:2 active panel in front of it, rather than stretch
    # metadata over its complete 77 mm width.
    screen = bpy.data.objects['Screen']
    pts = [v.co for v in screen.data.vertices]
    centre = sum(pts, Vector()) / len(pts)
    up = Vector((0, math.sin(math.radians(23)), math.cos(math.radians(23))))
    normal = Vector((0, -math.cos(math.radians(23)), math.sin(math.radians(23))))
    # Source lens sits slightly in front of the source Screen.
    glass = bpy.data.objects['Glass']
    lens_c = sum((v.co for v in glass.data.vertices), Vector()) / len(glass.data.vertices)
    centre += normal * ((lens_c-centre).dot(normal) + .0005)
    width, height = 61.2*(224/82)*.01, 40.8*(224/82)*.01
    corners = [centre + Vector((x*width/2, 0, 0)) + up*(y*height/2)
               for x, y in [(-1,1),(1,1),(1,-1),(-1,-1)]]
    mesh = bpy.data.meshes.new('Registered active LCD'); mesh.from_pydata(corners, [], [(3,2,1,0)]); mesh.update()
    lcd = bpy.data.objects.new('SP LCD glass', mesh); bpy.context.collection.objects.link(lcd)
    lcd.data.materials.append(mats['black']); lcd['hinged'] = True; lcd['paint'] = False; kept.append(lcd)
    # Barrel centre is the midpoint of the two moving cylindrical knuckles.
    hinge = Vector((0, .830711*q+offset_y, -3.40764*q+offset_z))
    # Recover the actual supplied logo into small, flat ink quads. The source
    # colour image and alpha mask together exclude the rectangular backdrop.
    # This keeps the identifying typography without inventing a replacement
    # font or adding texture sampling to the shared GLES2 mesh format.
    texture_dir = ROOT/'research/model-quality/originals/gbasp-neilvfx/Textures'
    images = [bpy.data.images.load(str(texture_dir/n), check_existing=False)
              for n in ('Gameboy_advance_SP_logo.png','Gameboy_advance_SP_logoalpha.png')]
    iw, ih = 384, 38
    for image in images: image.scale(iw, ih)
    pixels = [list(image.pixels[:]) for image in images]
    lc = centre-up*((40.8/2+3)*(224/82)*.01)+normal*.001
    lw = 44*(224/82)*.01; lh = lw*125/1280
    verts, faces = [], []
    for y in range(ih):
        x=0
        while x<iw:
            if not all(p[(y*iw+x)*4]>.7 for p in pixels): x+=1; continue
            start=x
            while x<iw and all(p[(y*iw+x)*4]>.7 for p in pixels): x+=1
            first=len(verts)
            verts += [lc+Vector(((xx/iw-.5)*lw,0,0))+up*((yy/ih-.5)*lh)
                      for xx,yy in ((start,y),(x,y),(x,y+1),(start,y+1))]
            faces.append((first,first+1,first+2,first+3))
    ink_mesh=bpy.data.meshes.new('Supplied SP logo');ink_mesh.from_pydata(verts,[],faces);ink_mesh.update()
    logo=bpy.data.objects.new('SP supplied logo',ink_mesh);bpy.context.collection.objects.link(logo)
    logo.data.materials.append(mats['ink']);logo['hinged']=True;logo['printed']=True;kept.append(logo)
    native_lcd = [(p.x*100, p.z*100, -p.y*100) for p in corners]
    pose = dict(hinge=list(hinge), open_radians=math.radians(113), lcd=native_lcd,
                source=SOURCE_URL, author='NeilVFX / nvfx', licence='Editorial License (no AI)',
                materials='Explicit local vertex-colour reconstruction; OBJ has one white default material',
                scale='Uniform 82 mm base width, no anisotropic rescaling', removed_game_pak_parts=sorted(CART))
    export_glb(kept, output/'model-master.glb')
    # Independent per-part budgets. Large smooth mouldings retain much more
    # geometry than the earlier 13k whole-console collapse; small lettering,
    # ports and controls have their own budgets. The full master stays intact.
    for o in kept:
        o.data.calc_loop_triangles(); before = len(o.data.loop_triangles)
        budget = 24000 if o.name == 'Case' else 15000 if o.name == 'Case_1' else 6000 if o.name in {'Case_2', 'Backplate'} else 2200 if o.name in LID else 1400 if o.name in BUTTONS else 300
        if o.name in {'Glass','Screen','SP LCD glass','Ebene','SP supplied logo'}: budget = before
        if before > budget:
            bpy.context.view_layer.objects.active = o
            mod = o.modifiers.new('Local animation detail', 'DECIMATE'); mod.ratio = budget / before
            bpy.ops.object.modifier_apply(modifier=mod.name)
            o.data.validate(clean_customdata=False)
        o.data.set_sharp_from_angle(angle=math.radians(35))
        for p in o.data.polygons: p.use_smooth = True
        bpy.context.view_layer.objects.active = o
        mod = o.modifiers.new('Moulded surface normals', 'WEIGHTED_NORMAL'); mod.keep_sharp = True; mod.weight = 100
        bpy.ops.object.modifier_apply(modifier=mod.name)
    vertices, indices, lookup, weights = [], [], {}, []
    door = 0
    for moving in (False, True):
        if moving: door = len(indices)
        for o in kept:
            if bool(o.get('hinged')) != moving: continue
            mesh = o.data; mesh.calc_loop_triangles()
            for tri in mesh.loop_triangles:
                if tri.normal.length_squared < .5: continue
                rgb = mesh.materials[tri.material_index].diffuse_color[:3]
                for li in tri.loops:
                    p = mesh.vertices[mesh.loops[li].vertex_index].co
                    n = mesh.corner_normals[li].vector.normalized()
                    # Quantize normals only to remove negligible OBJ/weighted
                    # normal differences. Position/silhouette remain exact.
                    ink = .25 if o.get('printed') else 1
                    values = (p.x*100,p.z*100,-p.y*100,*(round(v*ink,4) for v in (n.x,n.z,-n.y)),*rgb)
                    packed = struct.pack('<9f', *values)
                    if packed not in lookup:
                        lookup[packed] = len(vertices); vertices.append(packed); weights.append(192 if o.get('paint') else 0)
                    indices.append(lookup[packed])
    assert len(vertices) <= 65535, len(vertices)
    assert len(indices) <= 600000
    raw = b''.join(vertices)
    (output/'model.mesh').write_bytes(struct.pack('<8sIII', b'SCTOON2\0',len(vertices),len(indices),door)+raw+struct.pack('<%dH'%len(indices),*indices))
    h = 14695981039346656037
    for b in raw: h = ((h^b)*1099511628211)&0xffffffffffffffff
    geometry_hash = 14695981039346656037
    for vertex in vertices:
        for b in vertex[:24]: geometry_hash = ((geometry_hash^b)*1099511628211)&0xffffffffffffffff
    (output/'model.pose').write_bytes(b'SCLCD001'+struct.pack('<16fQ', *hinge, pose['open_radians'],
                                                       *(v for p in native_lcd for v in p), geometry_hash))
    (output/'paint.mask').write_bytes(struct.pack('<8sIQ',b'SCPAINT1',len(vertices),h)+bytes(weights))
    export_glb(kept, output/'model.glb')
    pose.update(vertices=len(vertices), triangles=len(indices)//3, door_first=door,
                mesh_sha256=hashlib.sha256((output/'model.mesh').read_bytes()).hexdigest())
    (output/'model-info.json').write_text(json.dumps(pose, indent=2)+'\n')
    (output/'CREDITS.txt').write_text('Local user-supplied asset. NOT a redistributable theme asset.\nNeilVFX / nvfx: Gameboy Advance SP\n'+SOURCE_URL+'\nEditorial License (no AI). Original geometry and UVs retained in the full source master.\nOBJ materials reconstructed explicitly; original C4D materials are not claimed.\n')
    print('LOCAL SP READY', len(vertices), 'vertices;',len(indices)//3,'triangles;', len(kept),'parts')


if __name__ == '__main__': main()
