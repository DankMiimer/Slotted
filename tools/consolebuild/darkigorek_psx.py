"""Restore dark_igorek's complete PSX geometry/UVs/albedo (CC BY 4.0).

Blender 4.5, --factory-startup --disable-autoexec. Opens the verified original
blend with use_scripts=False. Keeps the accepted SCPH-1001 registration and
early pickup orientation; no monitor, cables, controllers or game art.
"""
import json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import textured_blender as tb
Q=1.6
URL='https://sketchfab.com/3d-models/sony-pvm-1341-sony-playstation-5f80311f1a4646ef9673f20ee6dc6245'
NAMES={'Ps1_body':'PS1 enclosure','Ps1_body_details':'PS1 controls and fittings',
    'ps1_cap':'PS1 disc lid','body_inner':'PS1 disc well','laser_disc_rotor':'PS1 spindle',
    'laser_plate':'PS1 optical pickup','ps1_plugs':'PS1 socket interiors'}


def main():
    source=Path(sys.argv[sys.argv.index('--')+1]);bpy=tb.bpy
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),use_scripts=False,load_ui=False)
    kept=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(c.name=='ps1' for c in o.users_collection)]
    assert {o.name for o in kept}==set(NAMES)
    lid=bpy.data.objects['ps1_cap'];opened=lid.rotation_euler.x
    assert abs(opened+math.radians(50))<1e-6
    lid.rotation_euler.x=0;bpy.context.view_layer.update()
    points=[o.matrix_world@v.co for o in kept for v in o.data.vertices]
    low=Vector([min(p[i] for p in points) for i in range(3)]);high=Vector([max(p[i] for p in points) for i in range(3)])
    span=high-low;scale=Vector((.270/span.x,.188/span.y,.060/span.z))
    hub=bpy.data.objects['laser_disc_rotor'];centre=(low+high)/2;centre.y=hub.matrix_world.translation.y
    transform=Matrix.Diagonal((*scale,1))@Matrix.Translation(-centre)
    anchor=transform@hub.matrix_world.translation
    def native(p):
        v=transform@p;return [v.x*1000*Q,v.z*1000*Q,-v.y*1000*Q]
    hinge=native(lid.matrix_world.translation)
    disc=hub.matrix_world.translation.copy();disc.z=max((hub.matrix_world@v.co).z for v in hub.data.vertices)+.0004
    disc_native=native(disc)
    flags={};counts={}
    for o in list(bpy.context.scene.objects):
        if o not in kept:bpy.data.objects.remove(o,do_unlink=True)
    for o in kept:
        old=o.name;o.data=o.data.copy();world=o.matrix_world.copy();o.parent=None;o.matrix_world=Matrix.Identity(4)
        o.data.transform(transform@world)
        if old in ('laser_plate','body_inner'):
            o.data.transform(Matrix.Translation(anchor)@Matrix.Rotation(math.pi/2,4,'Z')@Matrix.Translation(-anchor))
        o.name=NAMES[old];o['source_part']=old;o['hinged']=old=='ps1_cap';o.data.update();o.data.calc_loop_triangles()
        counts[o.name]=len(o.data.loop_triangles)
        if old in ('Ps1_body','Ps1_body_details','ps1_cap'):flags[o.name]=dict(role='paint')
        if old=='ps1_cap':flags[o.name]['moving']=True
    tb.to_native(kept,(0,0,0),1000,Q)
    work=tb.ROOT/'build/textured/psx';tb.write_corners(kept,work,flags)
    alpha=bpy.data.images.get('ps1_details_mat_Alpha.jpg')
    if alpha:tb.save_image(alpha,work/'images'/alpha.name)
    reg=dict(model='psx',adapter='darkigorek_psx.py',author='dark_igorek',title='Sony PVM-1341 || Sony Playstation',
        url=URL,licence='CC-BY-4.0',licence_url='https://creativecommons.org/licenses/by/4.0/',
        source_file=source.name,source_sha256=tb.sha256(source),archive_sha256='0dab2049dc14e93fffb97b4576017fe26f26df31323612457405a00326885845',
        source_console_triangles=sum(counts.values()),source_parts=counts,decimation=False,
        source_game_art='None in the seven console meshes; no disc or screen is supplied in this collection',
        native_units_per_mm=Q,closed_size_mm=[270,60,188],physical_axis_scale=list(scale),
        hinge_native=hinge,disc_centre_native=disc_native,disc_radius_mm=60,disc_thickness_mm=1.2,
        pickup_registration_degrees=90,
        uncertainty='Keep the accepted authored hinge/spindle and envelope registration; no OEM pivot metrology',
        modifications=['Keep all seven console meshes, source UVs, print and base colour; no decimation',
            'Close original 50-degree lid; accepted 270 x 60 x 188 mm envelope correction',
            'Retain early SCPH-1001 pickup registration, 90 degrees behind the spindle',
            'Exclude monitor, cables and controllers from console asset',
            'Two 4K albedos reduced to 1024px tiles in a 2048px atlas; full masters/maps preserved',
            'Native albedo/simple lighting; no normal/roughness/metallic/emission shading'])
    (work/'registration.json').write_text(json.dumps(reg,indent=2)+'\n')
    tb.export_master_glb(kept,work/'model-master.glb')
    target=tb.ROOT/'theme/art-book-slot/_slot/consoles/psx'
    provenance=dict(source_creator='dark_igorek',source_licence='CC-BY-4.0',source_url=URL)
    for name,physical in [('model.glb',False),('model-master.glb',False),('model-physical.glb',True)]:
        tb.export_geometry_glb(kept,target/name,Q,physical=physical,provenance=provenance)
    print('PSX PREPARED',sum(counts.values()),'triangles',flush=True)


if __name__=='__main__':main()
