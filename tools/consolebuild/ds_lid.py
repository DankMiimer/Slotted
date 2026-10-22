"""Fit and register the existing original DS Lite lid for closure (MIT).

Coordinates below are native units: the original 404-wide lower housing anchors
133 mm. Hinge and 145-degree pose are reconstruction parameters, not OEM drawings.
"""
import math
HINGE=(0,-34,-103)
OPEN_DEGREES=145
HOUSING_UNITS_PER_MM=404/133
# Closed outer top = base screw bottom (-87.5) + Nintendo's 21.5-mm height.
# The old lid spans z=-118.3..-96. Register its inner plane at -102 so it
# clears the existing keys; fit its outer skin to that closed-height anchor.
CLOSED_TOP=-87.5+21.5*HOUSING_UNITS_PER_MM
SKIN_DEPTH_FACTOR=((-103-(CLOSED_TOP+34))-(-102))/(-118.3-(-96))
PREFIXES=('DS display lid','Upper shell seam','Lid inner fascia','DS lid hinge neck',
          'Upper LCD gasket','Upper LCD frame','Top LCD','DS speaker perforation',
          'Lid rubber bumper','Embossed DS emblem')


def prepare(m):
    from mathutils import Matrix,Vector
    bpy=m.bpy;h=Vector(m.xyz(*HINGE))
    open_pose=Matrix.Translation(h)@Matrix.Rotation(math.radians(-55),4,'X')@Matrix.Translation(-h)
    # The microphone is part of the upper bezel/neck, as the physical repair
    # assembly shows. It must move with that neck rather than stay on the deck.
    for name in ('Microphone opening','MIC.'):
        bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    mic=m.cylinder('DS lid microphone',(0,-25,-98.1),1.7,.35,m.M['darkink'],'front',16)
    word=m.text('MIC.',(0,-19,-98.1),3.8,m.M['ink'],True)
    bpy.context.view_layer.update()
    for o in (mic,word):o.matrix_world=open_pose@o.matrix_world
    bpy.context.view_layer.update()
    # Existing fixed end barrels retain their centres. Give the rotating middle
    # barrel actual radial clearance through the rear edge of the control deck.
    deck=bpy.data.objects['DS control deck']
    bore=m.cylinder('DS hinge clearance cutter',HINGE,9.55,315.5,m.M['black'],'side',48)
    bpy.context.view_layer.objects.active=deck
    for mod in list(deck.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=deck.modifiers.new('Registered hinge clearance','BOOLEAN')
    mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=bore
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(bore,do_unlink=True)
    deck['ds_hinge_clearance']=True
    parts=[o for o in bpy.context.scene.objects if o.name.startswith(PREFIXES) or o in (mic,word)]
    for o in parts:
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
        bpy.ops.object.convert(target='MESH');o=bpy.context.object
        # Evaluate bevels before this correction, so the thin skin's corners
        # follow its actual surface rather than retaining an oversized radius.
        for v in o.data.vertices:
            p=open_pose.inverted()@(o.matrix_world@v.co)
            z=-p.y/m.SCALE;p.y=-(-102+(z+96)*SKIN_DEPTH_FACTOR)*m.SCALE
            v.co=open_pose@p
        o.matrix_world=Matrix.Identity(4);o.data.update()
        m.panel_normals(m,o)
        o['hinged']=True;o['hinge_native']=list(HINGE)
    barrel=bpy.data.objects['DS rotating lid knuckle']
    barrel['hinged']=True;barrel['hinge_native']=list(HINGE)
    # Preserve the established 4:3 screen placement, using Nintendo's stated
    # 61.4 x 46.1-mm active dimensions at the existing housing register.
    for name in ('Bottom LCD','Top LCD'):
        o=bpy.data.objects[name]
        # Top LCD has already been baked into its open pose; handle its local
        # width/height in the unrotated lid plane to keep the hinge unchanged.
        transform=open_pose.inverted() if name=='Top LCD' else o.matrix_world
        back=open_pose if name=='Top LCD' else o.matrix_world.inverted()
        points=[transform@v.co for v in o.data.vertices]
        centre=sum(points,Vector())/len(points)
        for p,v in zip(points,o.data.vertices):
            p.x=centre.x+(p.x-centre.x)*(61.4*HOUSING_UNITS_PER_MM/191)
            axis=2 if name=='Top LCD' else 1
            p[axis]=centre[axis]+(p[axis]-centre[axis])*(46.1*HOUSING_UNITS_PER_MM/143)
            v.co=back@p
