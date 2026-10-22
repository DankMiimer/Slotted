"""Prepare the six exact user-selected sources; preserve originals and full detail.

Blender 4.5 --factory-startup --disable-autoexec --python-exit-code 1 -t 1.
Writes only build/selected-cartridges, never current runtime assets. MIT processing.
"""
import json
import math
import sys
from pathlib import Path
import numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import textured_blender as tb

SPECS = {
    'nds': dict(width=33, q=2.75, angle=math.pi, nodes=['Cartouche_Ds.003'],
                blank=[.070, .525, .480, .960]),
    'nes': dict(width=120, q=196/120, angle=-math.pi/2, label='sticker_3'),
    'gb': dict(width=57, q=1.8666667, angle=0, blank=[.510, .510, .850, .833]),
    'gba': dict(width=60, q=224/82, angle=0, blank=[.105, .372, .524, .594]),
    'gbc': dict(width=57, q=2.1538462, angle=math.pi, blank=[.396,.123,.456,.492]),
    'md': dict(width=109, q=224/109, nodes=['Object_3', 'Object_14', 'Object_42', 'Object_45'],
               label='Object_14'),
}


def clip(poly, axis, edge, sign):
    result = []
    for i, a in enumerate(poly):
        b = poly[(i+1) % len(poly)]
        da, db = (a[axis]-edge)*sign, (b[axis]-edge)*sign
        if da >= -1e-7: result.append(a)
        if (da >= 0) != (db >= 0): result.append(a+(b-a)*da/(da-db))
    return result


def original_box(name, low, high, colour):
    """New, explicitly original concealed GBC geometry; dimensions in mm."""
    bpy = tb.bpy
    bpy.ops.mesh.primitive_cube_add(size=1, location=((low[0]+high[0])/2,
        -(low[2]+high[2])/2, (low[1]+high[1])/2))
    o = bpy.context.object
    o.name = name
    o.dimensions = (high[0]-low[0], high[2]-low[2], high[1]-low[1])
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mat = bpy.data.materials.new(name+' material')
    mat.use_nodes = True
    mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (*colour, 1)
    o.data.materials.append(mat)
    return o


def gbc_complete(objects):
    # In the unchanged full source the cartridge is the separate upper/back
    # Plastic island. No console triangles meet these bounds.
    src = objects['Plastic']
    card = tb.copy_triangles(src, 'Wikiti authored exposed cartridge', lambda t: all(
        src.data.vertices[i].co.z > .449 and src.data.vertices[i].co.y > .009
        and abs(src.data.vertices[i].co.x) < .405 for i in t.vertices))
    assert len(card.data.polygons) > 300
    for o in list(objects.values()): tb.bpy.data.objects.remove(o, do_unlink=True)
    return [card]


def subtract_box(objects, name, low, high):
    tool = original_box(name, low, high, (.03,.03,.03))
    for obj in objects:
        tb.bpy.context.view_layer.objects.active = obj
        mod = obj.modifiers.new(name, 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.solver = 'EXACT'
        mod.object = tool
        tb.bpy.ops.object.modifier_apply(modifier=mod.name)
    tb.bpy.data.objects.remove(tool, do_unlink=True)


def run(key):
    cfg = SPECS[key]
    source = tb.ROOT/'research/selected-cartridges-20261019'/key/'full.glb'
    metadata = json.loads(source.with_name('metadata.json').read_text())
    objects = tb.import_source(source)
    if key == 'gbc':
        selected = gbc_complete(objects)
    else:
        selected = [objects[n] for n in cfg.get('nodes', objects)]
        for o in list(objects.values()):
            if o not in selected: tb.bpy.data.objects.remove(o, do_unlink=True)
    if key == 'md':
        label = next(o for o in selected if o.name == cfg['label'])
        label.data.calc_loop_triangles()
        front = Vector((0,0,0))
        for t in label.data.loop_triangles:
            if abs(t.normal.z) < .5: front += t.normal*t.area
        front.z = 0
        front.normalize()
        angle = math.atan2(-front.x, -front.y)
    else:
        angle = cfg['angle']
    for o in selected:
        o.data.transform(Matrix.Rotation(angle, 4, 'Z'))
        o.data.update()
    lo, hi = tb.bounds(selected)
    mm = cfg['width']/(hi.x-lo.x)
    size = [(hi[i]-lo[i])*mm for i in (0,2,1)]
    centre = (hi+lo)/2
    additions = []
    if key == 'gbc':
        # Keep the original exposed top unchanged, at the top of a 65.5-mm card.
        # Work in mm before adding the missing lower/back shell and contacts.
        centre.z = hi.z-65.5/(2*mm)
        tb.to_native(selected, centre, mm, 100)  # mm in Blender coordinates
        lower_top = 32.75-size[1]+.08
        lower = original_box('Original concealed CGB lower shell', (-28.5,-32.75,-3.989),
            (28.5,lower_top,3.989), (.027,.027,.029))
        additions.append(lower)
        tb.bpy.context.view_layer.objects.active = lower
        bevel = lower.modifiers.new('Original moulded lower edges', 'BEVEL')
        bevel.width = .45
        bevel.segments = 4
        tb.bpy.ops.object.modifier_apply(modifier=bevel.name)
        # Continue the partial source's actual label recess down the new shell.
        # The old filled lower strip would otherwise hide the live game label.
        subtract_box(selected+[lower], 'Complete CGB label well',
            (-21.572,-24,3.432),(21.083,14.985,5))
        subtract_box([lower], 'Original rear connector opening',
            (-25.5,-33,-4.5),(25.5,-25.5,1))
        additions += [original_box('Original CGB connector board',(-25.5,-32.6,-.95),(25.5,-25.5,.15),(.06,.19,.10))]
        for i in range(32):
            x = -24.8+i*1.6
            additions.append(original_box('Original CGB contact %02d'%i,(x,-32.7,-1.01),(x+.95,-26.2,-.96),(.55,.36,.07)))
        for o in selected+additions:
            o.data.transform(Matrix.Scale(cfg['q']*.01,4))
            o.data.update()
        selected += additions
    else:
        tb.to_native(selected, centre, mm, cfg['q'])
    out = tb.ROOT/'build/selected-cartridges'/key
    out.mkdir(parents=True, exist_ok=True)
    flags = {o.name:dict(role='paint') for o in selected}
    if key == 'md':
        flags['Object_45']['role'] = 'fixed'
    for o in additions:
        if 'contact' in o.name or 'board' in o.name: flags[o.name]['role']='fixed'
    tb.write_corners(selected, out, flags)
    data = np.load(out/'corners.npz')
    parts = json.loads((out/'parts.json').read_text())
    names = [p['name'] for p in parts['parts']]
    pos = data['position'].reshape(-1,3,3)
    normal = data['normal'].reshape(-1,3,3)
    uv = data['uv'].reshape(-1,3,2)
    candidates = normal[:,:,2].mean(1) > .5
    # Flat sources often carry softened corner normals: actual face normals
    # decide which side is the front, while output retains their source normals.
    geo = np.cross(pos[:,1]-pos[:,0], pos[:,2]-pos[:,0])
    candidates &= geo[:,2] > 0
    label_projection = None
    if cfg.get('label'):
        label_part = data['triangle'][:,0] == names.index(cfg['label'])
        front = candidates & label_part
        # The NES and MD stickers wrap over their top edge. Keep every source
        # sticker triangle and its continuous UV layout, oriented from the front.
        label_projection = np.linalg.lstsq(np.c_[uv[front].reshape(-1,2),
            np.ones(front.sum()*3)],pos[front,:,:2].reshape(-1,2),rcond=None)[0]
        candidates = label_part
    label = []
    if key == 'gbc':
        # Explicit original surface; the partial source has no complete front label.
        q=cfg['q']; x0,x1,y0,y1,z=-21.2,20.7,-23.6,14.8,3.47
        for triangle in [[(x0,y0,z),(x1,y0,z),(x1,y1,z)],[(x0,y0,z),(x1,y1,z),(x0,y1,z)]]:
            label.append([np.array((*p,0,0,1,0,0))*np.array((q,q,q,1,1,1,1,1)) for p in triangle])
    else:
        for p,n,t in zip(pos[candidates],normal[candidates],uv[candidates]):
            poly=[np.concatenate((p[i],n[i],t[i])) for i in range(3)]
            if cfg.get('blank'):
                u0,v0,u1,v1=cfg['blank']
                for axis,edge,sign in [(6,u0,1),(6,u1,-1),(7,v0,1),(7,v1,-1)]:
                    if poly: poly=clip(poly,axis,edge,sign)
            for i in range(1,len(poly)-1): label.append([poly[0],poly[i],poly[i+1]])
    label=np.array(label,dtype=np.float32)
    if len(label)<2: raise RuntimeError(key+': empty label')
    p,n=label[:,:,:3],label[:,:,3:6]
    p+=n*(.035*cfg['q'])
    a,b=p.min((0,1))/cfg['q'],p.max((0,1))/cfg['q']
    if label_projection is not None:
        flat = label[:,:,6:8].reshape(-1,2)
        virtual = (np.c_[flat,np.ones(len(flat))] @ label_projection).reshape(-1,3,2)
        t = (virtual-virtual.min((0,1)))/(virtual.max((0,1))-virtual.min((0,1)))
    else:
        t=np.stack(((p[:,:,0]/cfg['q']-a[0])/(b[0]-a[0]),(p[:,:,1]/cfg['q']-a[1])/(b[1]-a[1])),axis=-1)
    np.savez_compressed(out/'label.npz',position=p.reshape(-1,3),normal=n.reshape(-1,3),uv=t.reshape(-1,2))
    lo,hi=tb.bounds(selected)
    size=[(hi[i]-lo[i])*100/cfg['q'] for i in (0,2,1)]
    reg=dict(adapter=Path(__file__).name, key=key, creator=metadata['user']['displayName'],
        licence='CC-BY-4.0',licence_url='https://creativecommons.org/licenses/by/4.0/',
        url=metadata['viewerUrl'], uid=metadata['uid'],source_file=str(source.relative_to(tb.ROOT)),
        source_sha256=tb.sha256(source),source_nodes=cfg.get('nodes',[o.name for o in selected if o not in additions]),
        q=cfg['q'],size_mm=size,label_mm=[float((a[0]+b[0])/2),float((a[1]+b[1])/2),float((b[0]-a[0])/2),float((b[1]-a[1])/2),float(b[2])],
        label_triangles=len(p),decimation=False,depth_scale=1,
        blank_uv=cfg.get('blank'),excluded_materials=[parts['materials'][i] for i in range(len(parts['materials'])) if cfg.get('label') and cfg['label'] in names and i in set(data['triangle'][data['triangle'][:,0]==names.index(cfg['label']),1])],
        modifications=['One card isolated from source scene; uniform width registration; no decimation',
            'Fixed game label blanked; independent per-game label surface',
            'Source UVs/normals retained; native renderer uses albedo only, full PBR originals retained in research'],
        original_additions=[o.name for o in additions],
        source_quality_limitation='GBC hidden lower shell and connector are original additions; partial source label well extended through its filled lower strip; dimensions are presentation estimates' if additions else '')
    (out/'registration.json').write_text(json.dumps(reg,indent=2)+'\n')
    tb.export_master_glb(selected,out/'registered-full-detail.glb')
    for suffix,physical in [('-master',False),('-physical',True),('',False)]:
        tb.export_geometry_glb(selected,out/('media'+suffix+'.glb'),cfg['q'],physical=physical,
            provenance={'creator':reg['creator'],'licence':reg['licence'],'source':reg['url']})
    print('PREPARED',key,json.dumps(reg),flush=True)


if __name__=='__main__':
    for key in sys.argv[sys.argv.index('--')+1:]: run(key)
