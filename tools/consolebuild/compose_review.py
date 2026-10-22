"""Compose local blank-media review captures; no handheld access (MIT)."""
import json
import struct
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/exemplars'
FONT=ImageFont.truetype(str(ROOT/'third_party/open-sans/OpenSans-SemiBold.ttf'),20)


def sheet(system,rows,destination,before_path=None,before_label=None):
    before_label=before_label or ('Before - 65ceb24' if system in ('gbc','gba') else 'Before - fba7ffe')
    image=Image.new('RGB',(1440,len(rows)*512+36),(26,28,32));draw=ImageDraw.Draw(image)
    draw.text((16,4),before_label,font=FONT,fill='white')
    draw.text((736,4),'After - Slotters exemplars',font=FONT,fill='white')
    for y,(label,file) in enumerate(rows):
        for x,version in enumerate(('before','after')):
            folder=before_path if version=='before' and before_path else OUT/version/system
            source=Image.open(folder/file).convert('RGBA')
            image.paste(source,(x*720,36+y*512),source)
        draw.text((16,36+y*512+480),label,font=FONT,fill='white')
    image.save(OUT/destination)


def sequence(system,mode,timed=False):
    frames=[]
    for i in range(61):
        frame=Image.new('RGB',(1440,480))
        for x,version in enumerate(('before','after')):
            part='-scene' if timed else ''
            frame.paste(Image.open(OUT/version/system/f'{mode}{part}-{i:02d}.png'),(x*720,0))
        frames.append(frame)
    motion=(1150 if system=='gba' else 1850) if mode=='insert' else 1750;hold=100 if mode=='insert' else 350
    durations=[motion/60]*60+[hold]
    suffix='-timed' if timed else ''
    frames[0].save(OUT/f'{system}-{mode}{suffix}.gif',save_all=True,append_images=frames[1:],
                   duration=durations,loop=0,optimize=False)


def main():
    report={}
    systems=os.environ.get('SLOT_REVIEW_SYSTEMS','gb psp').split()
    for system in systems:
        sheet(system,[(v,v+'.png') for v in ('front','rear','side','top')],f'{system}-neutral-comparison.png')
        sheet(system,[('Matched neutral front','front.png')],f'{system}-front-comparison.png')
        sheet(system,[(v+' media envelope (before: reconstructed slab)', 'media-'+v+'.png') for v in ('front','rear','side','top')],f'{system}-media-comparison.png')
        rows=[('Insert first mechanical pose','insert-00.png'),('Front presentation','insert-18.png'),
              ('Rear/door alignment','insert-39.png'),('Media seating','insert-46.png'),
              ('Insert last mechanical pose / eject first','insert-60.png'),('Eject last mechanical pose','eject-60.png')]
        sheet(system,rows,f'{system}-pose-sheet.png')
        sheet(system,[(f'{mode} {end} displayed frame (production fade)',f'{mode}-scene-{i:02d}.png')
                      for mode in ('insert','eject') for end,i in (('first',0),('last',60))],f'{system}-timed-endpoints.png')
        media=Image.new('RGB',(1440,1024),(26,28,32));draw=ImageDraw.Draw(media)
        for i,view in enumerate(('front','rear','side','top')):
            im=Image.open(OUT/'after'/system/('media-'+view+'.png')).convert('RGBA')
            media.paste(im,((i%2)*720,(i//2)*512),im)
            draw.text(((i%2)*720+16,(i//2)*512+480),view,font=FONT,fill='white')
        media.save(OUT/f'{system}-media-neutral.png')
        for mode in ('insert','eject'):
            sequence(system,mode);sequence(system,mode,True)
        report[system]={version:json.loads((base/system/'mesh-info.json').read_text()) for version,base in (
            ('before',OUT/'before/theme/art-book-slot/_slot/consoles'),('after',ROOT/'theme/art-book-slot/_slot/consoles'))}
    if not set(systems)&{'gb','psp'}:
        (OUT/'handheld-review-report.json').write_text(json.dumps(report,indent=2)+'\n')
        return
    # Positive open-cover control avoids accepting an absent/black media face.
    def bright(mode,i):
        im=np.array(Image.open(OUT/'after/psp'/f'{mode}-{i:02d}.png').convert('RGB'))
        return int((im[180:420,200:500].min(axis=2)>175).sum())
    closed={str(i):bright('insert',i) for i in range(54,61)}
    eject_closed={str(i):bright('eject',i) for i in range(7)}
    assert min(bright('insert',46),bright('eject',14))>300, 'Open UMD positive control is missing'
    assert max((*closed.values(),*eject_closed.values()))==0, 'Seated UMD leaks through the closed door'
    report['psp_cover']={'roi_xyxy':[200,180,500,420],
                         'open_frame_46_bright_pixels':bright('insert',46),
                         'eject_open_frame_14_bright_pixels':bright('eject',14),
                         'closed_bright_pixels':closed,'eject_closed_bright_pixels':eject_closed}
    report['media']={}
    for system,q in (('gb',168/90),('psp',480/169.4)):
        base=ROOT/'theme/art-book-slot/_slot/consoles'/system
        info=json.loads((base/'media-info.json').read_text());raw=(base/'media.mesh').read_bytes()
        points=np.frombuffer(raw,'<f4',struct.unpack_from('<I',raw,8)[0]*9,20).reshape(-1,9)[:,:3]/q
        info['complete_bounds_mm']=[round(float(v),4) for v in np.ptp(points,axis=0)]
        report['media'][system]=info
    def physical_bounds(system,part,stem='model'):
        raw=(ROOT/'theme/art-book-slot/_slot/consoles'/system/(stem+'.glb')).read_bytes()
        length=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+length])
        node=next(n for n in g['nodes'] if n.get('name')==part)
        a=g['accessors'][g['meshes'][node['mesh']]['primitives'][0]['attributes']['POSITION']]
        q=168/90 if system=='gb' else 480/169.4
        return np.array(a['min'])*100/q,np.array(a['max'])*100/q
    case_low,case_high=physical_bounds('psp','UMD original ECMA case','media')
    door_low,door_high=physical_bounds('psp','UMD door shell')
    report['sampled_clearance_mm']={'dmg_front_wall_x0_y40':.3459,'dmg_rear_wall_x0_y40':.169,
                                  'umd_side_to_rails_each':.9,
                                  'umd_top_to_door_envelope':float(door_high[1]-case_high[1]),
                                  'umd_bottom_to_door_envelope':float(case_low[1]-door_low[1]),
                                  'umd_label_to_door_inner_surface':8.4026-23/(480/169.4)}
    previous=OUT/'rear-correction/before/gb'
    if previous.exists():
        sheet('gb',[('Rear structure, unloaded','rear.png'),('Front silhouette','front.png'),
                    ('Native alignment','insert-46.png'),('Native seated cartridge','insert-60.png')],
              'gb-rear-correction.png',previous,'Previous exemplar - c57edab')
    diagnostic=OUT/'diagnostic/gb/clip-check.json'
    if diagnostic.exists():report['dmg_clip']=json.loads(diagnostic.read_text())
    (OUT/'review-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
