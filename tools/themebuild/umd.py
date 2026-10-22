"""Original UMD textures and legacy flat PSP previews. No reference pixels ship.

Prepared textures and a poster homography keep the device baker Pillow-only.
The current full cel-shaded PSP-3000 is built by tools/consolebuild/models.py.
"""
import hashlib
import json
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from tools.discpreview import preview as camera
from .geometry import OPEN_SANS

S=2


def shell():
    im=Image.new('RGBA',(648,648));d=ImageDraw.Draw(im)
    # Circular crown, vertical flanks and shallow curved base: the complete shell.
    path=[(162+157*math.cos(a),161+157*math.sin(a))
          for a in np.linspace(math.pi,2*math.pi,80)]
    path += [(319,274),(314,286)]
    path += [(314*(1-t)**2+324*t*(1-t)+10*t*t,
              286*(1-t)**2+704*t*(1-t)+286*t*t) for t in np.linspace(0,1,50)]
    path += [(5,274)]
    path=[(x*S,y*S) for x,y in path]
    d.polygon(path,fill=(220,221,213));d.line(path+[path[0]],fill=(123,128,123),width=2*S)
    d.arc((7*S,6*S,317*S,316*S),160,358,fill=(254,254,248),width=3*S)
    # Recessed clear window has an opaque smoked ground, never wallpaper.
    d.ellipse((23*S,23*S,301*S,301*S),fill=(85,90,88),outline=(176,180,172),width=2*S)
    d.ellipse((25*S,25*S,299*S,299*S),fill=(199,203,194))
    f=ImageFont.truetype(str(OPEN_SANS/'OpenSans-Regular.ttf'),13*S)
    d.text((31*S,283*S),'PSP',font=f,fill=(161,166,160),anchor='mm')
    d.rounded_rectangle((283*S,271*S,304*S,283*S),radius=3*S,fill=(161,166,160))
    d.rectangle((287*S,273*S,289*S,281*S),fill=(232,234,224))
    d.rectangle((284*S,276*S,292*S,278*S),fill=(232,234,224))
    d.ellipse((298*S,275*S,300*S,277*S),fill=(232,234,224))
    return im


def rear(inside=False,door=False):
    im=Image.new('RGBA',(1080,448) if not door else (448,368));d=ImageDraw.Draw(im)
    w,h=im.size
    d.rounded_rectangle((2,2,w-3,h-3),radius=70 if not door else 44,
                        fill=(25,26,29) if inside else (38,39,43),outline=(87,89,93),width=3)
    d.rounded_rectangle((9,9,w-10,h-10),radius=64 if not door else 38,
                        outline=(12,13,16),width=2)
    d.arc((9,9,w-10,h-10),190,300,fill=(119,122,124),width=2)
    if door:
        if inside:
            d.rounded_rectangle((27,20,w-27,h-20),radius=39,fill=(13,14,17),outline=(65,67,72),width=3)
            for x in (31,w-45): d.rounded_rectangle((x,66,x+14,h-54),radius=5,fill=(136,141,146))
            d.rounded_rectangle((74,h-35,w-74,h-20),radius=5,fill=(120,125,130))
        else:
            d.ellipse((85,47,w-85,h-47),outline=(145,149,150),width=6)
            f=ImageFont.truetype(str(OPEN_SANS/'OpenSans-SemiBold.ttf'),58)
            d.text((w/2,h/2),'PSP',font=f,fill=(165,167,168),anchor='mm')
    else:
        # Rear drive recess, battery seams, shoulder keys and fastening screws.
        d.rounded_rectangle((w/2-215,18,w/2+215,h-22),radius=44,fill=(9,10,13),outline=(82,83,87),width=4)
        d.ellipse((w/2-137,h/2-137,w/2+137,h/2+137),fill=(21,23,26),outline=(65,67,72),width=4)
        d.ellipse((w/2-17,h/2-17,w/2+17,h/2+17),fill=(138,141,144))
        d.rounded_rectangle((w/2+68,h/2+40,w/2+107,h/2+68),radius=4,fill=(74,83,89))
        for x in (183,w-187): d.line((x,38,x,h-38),fill=(12,13,15),width=4)
        for x in (46,w-85):
            d.rounded_rectangle((x,3,x+40,24),radius=7,fill=(157,162,166),outline=(221,224,225),width=2)
        for x in (62,w-62):
            for y in (h-48,48):
                d.ellipse((x-7,y-7,x+7,y+7),fill=(14,15,18),outline=(90,92,96),width=2)
                d.line((x-3,y,x+3,y),fill=(113,115,118),width=2)
        f=ImageFont.truetype(str(OPEN_SANS/'OpenSans-Regular.ttf'),17)
        d.text((98,h-54),'SONY',font=f,fill=(150,153,156))
    return im


def underside():
    """Original recorded-side shell: exposed hub and pickup window, no label."""
    im=shell();d=ImageDraw.Draw(im)
    d.ellipse((23*S,23*S,301*S,301*S),fill=(227,230,220),outline=(170,178,167),width=2*S)
    d.ellipse((135*S,134*S,189*S,188*S),fill=(102,113,117),outline=(175,183,177),width=2*S)
    d.ellipse((144*S,143*S,180*S,179*S),fill=(194,202,202),outline=(101,113,111),width=S)
    d.ellipse((155*S,154*S,169*S,168*S),fill=(99,109,105))
    d.rectangle((235*S,113*S,298*S,207*S),fill=(142,160,166),outline=(119,132,128),width=2*S)
    d.line((239*S,116*S,293*S,199*S),fill=(184,203,209),width=5*S)
    for x,y in ((47,37),(275,38),(30,263),(298,258)):
        d.ellipse(((x-3)*S,(y-3)*S,(x+3)*S,(y+3)*S),fill=(129,141,132))
    return im


def draw_plane(im,texture,centre,u,v,rx,ry,origin):
    # Reuse the camera homography with a non-square source plane.
    square=texture.resize((texture.width,texture.width),Image.Resampling.BICUBIC)
    camera.plane(im,square,centre,u,np.asarray(v)*ry/rx,rx,origin)


def model(im,origin,opening=0):
    u=np.array((1,0,0));v=np.array((0,-math.cos(camera.PHI),math.sin(camera.PHI)))
    normal=np.array((0,math.sin(camera.PHI),math.cos(camera.PHI)))
    draw_plane(im,rear(),(0,0,0),u,v,270,112,origin)
    a=math.radians(42)*opening
    dv=v*math.cos(a)-normal*math.sin(a)
    centre=v*82-dv*82+normal*3
    draw_plane(im,rear(door=True),centre,u,dv,112,92,origin)


def export(folder):
    folder.mkdir(parents=True,exist_ok=True)
    flat=shell();flat.save(folder/'shell.png')
    alpha=Image.new('L',(648,648));d=ImageDraw.Draw(alpha)
    d.ellipse((26*S,26*S,298*S,298*S),fill=255)
    alpha.save(folder/'print-mask.png')
    # The UMD label covers its hub. Preserve the scan's printed centre.
    hub=Image.new('RGBA',(648,648));d=ImageDraw.Draw(hub)
    hub.save(folder/'hub.png')
    centre=np.array((0,156,0));u,v=camera.disc_basis(camera.PHI,math.radians(10),math.radians(-3))
    q=camera.project([centre+u*a+v*b for a,b in ((-150,-150),(150,-150),(150,150),(-150,150))])*S
    q-=np.array((192,43))*S
    matrix,rhs=[],[]
    for (a,b),(tx,ty) in zip(q,((0,0),(648,0),(648,648),(0,648))):
        matrix.extend(((a,b,1,0,0,0,-tx*a,-tx*b),(0,0,0,a,b,1,-ty*a,-ty*b)));rhs.extend((tx,ty))
    projection=np.linalg.solve(matrix,rhs).tolist()
    # Subtle 3-pixel depth, sharing the front silhouette rather than a CD ring.
    face=flat.transform((672,672),Image.Transform.PERSPECTIVE,projection,Image.Resampling.BICUBIC)
    edge=Image.new('RGBA',(672,672));shade=Image.new('RGBA',face.size,(141,149,139));shade.putalpha(face.getchannel('A'))
    edge.alpha_composite(shade,(0,4));edge.save(folder/'edge.png')
    Image.alpha_composite(edge,face).getchannel('A').resize((336,336),Image.Resampling.LANCZOS).save(folder/'mask.png')
    for name,im in (('underside',underside()),('deck',rear()),('lid',rear(door=True)),('lid-inside',rear(inside=True,door=True))):
        im.save(folder/(name+'.png'))
        im.resize((im.width//2,im.height//2),Image.Resampling.LANCZOS).save(folder/(name+'.tga'))
    spec=dict(size=[336,336],well=[70,72,266,133],umd=True,projection=projection)
    fingerprint=hashlib.sha256(json.dumps(spec,sort_keys=True).encode())
    for p in sorted(folder.glob('*.png')):fingerprint.update(p.read_bytes())
    spec['revision']='umd-1-'+fingerprint.hexdigest()[:16]
    spec['preview']=dict(canvas=[26*S,26*S,272*S,272*S],
                         centre=[162*S,162*S],outer=136*S,inner=0)
    (folder/'shape.json').write_text(json.dumps(spec),encoding='utf8')
    band=Image.new('RGBA',(1440,960),(35,35,41,255));model(band,548)
    band.resize((720,480),Image.Resampling.LANCZOS).crop((0,422,720,480)).save(folder.parents[1]/'band-psp.png')
