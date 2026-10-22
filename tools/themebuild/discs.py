"""Original PS1 model assets shared with the approved motion study.

Only prepared masks, textures and a homography go to the Pillow-only handheld baker.
The native helper projects the same world geometry during launch and eject.
"""
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from tools.discpreview import preview as model


def export(folder):
    folder.mkdir(parents=True, exist_ok=True)
    n=648
    y,x=np.mgrid[:n,:n]; r=np.hypot(x+.5-n/2,y+.5-n/2)
    mask=Image.fromarray(np.where((r<n/2)&(r>n/16),255,0).astype('uint8'))
    mask.save(folder/'print-mask.png')
    hub=Image.new('RGBA',(n,n));d=ImageDraw.Draw(hub)
    for radius,col in ((45,(107,112,113)),(43,(191,194,188)),(30,(115,118,120)),
                       (28,(202,206,200)),(22,(225,227,217)),(20.25,(0,0,0,0))):
        d.ellipse(((162-radius)*2,(162-radius)*2,(162+radius)*2,(162+radius)*2),fill=col)
    hub.save(folder/'hub.png')
    # A physical dark rim, independent of scanned label/background colours.
    # Its narrow highlight follows the shared upper-left scene lighting.
    light=np.clip((-(x+.5-n/2)-(y+.5-n/2))/(n/2*1.4142),0,1)
    tone=np.where(r>n/2-1,48+38*light,12+14*light)
    rim=np.zeros((n,n,4),dtype='uint8')
    for channel in range(3):rim[:,:,channel]=tone+channel
    # Extend the neutral underlay beneath the video's antialias fringe too, so
    # cropped scan colours cannot leave a blue (or other artwork-coloured) halo.
    rim[:,:,3]=np.where((r>=n/2-10)&(r<n/2),255,0)
    Image.fromarray(rim).save(folder/'disc-rim.png')
    centre=np.array((0,156,0)); u,v=model.disc_basis(model.PHI,np.radians(10),np.radians(-3))
    q=model.project([centre+u*a+v*b for a,b in ((-150,-150),(150,-150),(150,150),(-150,150))])*2
    q-=np.array((192,43))*2
    matrix,rhs=[],[]
    for (a,b),(tx,ty) in zip(q,((0,0),(n,0),(n,n),(0,n))):
        matrix.extend(((a,b,1,0,0,0,-tx*a,-tx*b),(0,0,0,a,b,1,-ty*a,-ty*b)));rhs.extend((tx,ty))
    projection=np.linalg.solve(matrix,rhs).tolist()
    empty=Image.new('RGBA',(n,n)); full=Image.new('RGBA',(n,n),'white');full.putalpha(mask)
    crop=(384,86,1056,758)
    edge=Image.new('RGBA',(1440,960))
    model.ring(edge,empty,empty,centre,u,v,150,2.2,350,inner=18.75)
    edge.crop(crop).save(folder/'edge.png')
    silhouette=Image.new('RGBA',(1440,960))
    model.ring(silhouette,full,full,centre,u,v,150,2.2,350,inner=18.75)
    silhouette.crop(crop).getchannel('A').resize((336,336),Image.Resampling.LANCZOS).save(folder/'mask.png')
    model.BACK.save(folder/'underside.png');model.LID.save(folder/'lid.png');model.UNDER.save(folder/'lid-inside.png')
    deck=Image.new('RGBA',(1440,960))
    old=model.project
    try:
        model.project=lambda points,origin=0:np.array([(360+p[0],240+p[2]) for p in points])
        model.deck(deck,0)
    finally:model.project=old
    deck.crop((264,180,1176,780)).save(folder/'deck.png')
    shadow=Image.new('RGBA',(512,512));d=ImageDraw.Draw(shadow)
    d.ellipse((24,24,488,488),fill=(0,0,0,105))
    shadow.filter(ImageFilter.GaussianBlur(12)).save(folder/'shadow.png')
    # Uncompressed small runtime textures avoid PNG decoding after display handoff.
    for name in ('underside','lid','lid-inside','deck','shadow'):
        with Image.open(folder/(name+'.png')) as im:
            im.resize((im.width//2,im.height//2),Image.Resampling.LANCZOS).save(folder/(name+'.tga'))
    spec=dict(size=[336,336],well=[90,38,246,108],disc=True,projection=projection)
    fingerprint=hashlib.sha256(json.dumps(spec,sort_keys=True).encode())
    for p in sorted(folder.glob('*.png')):fingerprint.update(p.read_bytes())
    spec['revision']='disc-1-'+fingerprint.hexdigest()[:16]
    # Describes the very same flat art surface for live video. Adding consumer
    # metadata does not invalidate unchanged baked posters or motion textures.
    spec['preview']=dict(canvas=[0,0,n,n],centre=[n/2,n/2],outer=n/2,inner=n/16)
    # Leave the original metallic hub and narrow outer rim visible beneath the
    # live video. Their pixels already travel with the baked carousel artwork.
    hub_y,hub_x=np.nonzero(np.asarray(hub.getchannel('A')))
    spec['preview']['videoInner']=float(np.hypot(hub_x+.5-n/2,hub_y+.5-n/2).max()+1.5)
    spec['preview']['videoOuter']=n/2-6-1.5
    (folder/'shape.json').write_text(json.dumps(spec),encoding='utf8')
    band=Image.new('RGBA',(1440,960),(35,35,41,255))
    model.deck(band,527);model.draw_lid(band,527,0)
    if folder.name == 'psx':
        band.resize((720,480),Image.Resampling.LANCZOS).crop((0,422,720,480)).save(folder.parents[1]/'band-psx.png')
