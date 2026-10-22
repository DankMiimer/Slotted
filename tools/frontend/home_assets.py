"""Refresh home-console fallback sprites from the production 2x browse cache (MIT).

Run render_quality.py --all-finishes first. Handheld bodies and derivatives are
left untouched; the packaged GBA browse cache must also be current when present.
"""
import hashlib,json
from pathlib import Path
from PIL import Image
from tools.themebuild.appearance import STYLES,COLORS
from tools.themebuild.stage import save_changed,build as build_stage
from tools.themebuild.consoles import build as build_consoles

ROOT=Path(__file__).resolve().parents[2]
SLOT=ROOT/'theme/art-book-slot/_slot'
HOMES=('snes','snes-us','nes','n64','md','md-jp','pico8','psx','dreamcast')

def cached(style,colour,model):
    path=ROOT/'build/model-quality/browse'/style/colour/(model+'.png')
    metadata=json.loads(path.with_suffix('.json').read_text())
    if metadata['renderer_sha256']!=hashlib.sha256((ROOT/'tools/frontend/overlay/es-app/src/components/SlotNative.c').read_bytes()).hexdigest():
        raise ValueError('Stale renderer cache: '+str(path))
    if metadata['mesh_sha256']!=hashlib.sha256((SLOT/'consoles'/model/'model.mesh').read_bytes()).hexdigest():
        raise ValueError('Stale mesh cache: '+str(path))
    with Image.open(path) as im:
        if im.size!=(1440,960):raise ValueError('Expected native 2x browse raster')
        return im.convert('RGBA').resize((720,480),Image.Resampling.LANCZOS)

def main():
    for model in HOMES:
        save_changed(cached('realistic','original',model),SLOT/'consoles'/model/'body.png')
    build_consoles(SLOT,only=set(HOMES))
    specs=json.loads((SLOT/'consoles/specs.json').read_text())
    for style in STYLES:
        for colour in COLORS:
            dest=SLOT/'appearance'/style/colour
            for model in HOMES:
                spec=specs[model];full=cached(style,colour,model)
                band=Image.new('RGBA',(720,480),(0,0,0,255))
                band.alpha_composite(full,(0,spec['idle']-240))
                save_changed(band.crop((0,422,720,480)),dest/('band-console-'+model+'.png'))
                x,y,w,h=spec['sprite']
                save_changed(full.crop((x,y,x+w,y+h)),dest/'consoles'/model/'body.png')
    build_stage(SLOT,only=set(HOMES))
    print('Refreshed nine home consoles, 16 finishes each; handheld sprites preserved')

if __name__=='__main__':main()
