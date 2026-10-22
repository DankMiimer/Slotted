"""Reproducible console finish/paint derivatives from the native renderer (MIT)."""
import json,subprocess
from pathlib import Path
from PIL import Image
from tools.themebuild.appearance import build,COLORS,STYLES,STYLE_MODELS

ROOT=Path(__file__).resolve().parents[2]
SLOT=ROOT/'theme/art-book-slot/_slot'

def main():
    build(SLOT)
    specs=json.loads((SLOT/'consoles/specs.json').read_text())
    for style in STYLES:
        for color in COLORS:
            dest=SLOT/'appearance'/style/color
            dest.mkdir(parents=True,exist_ok=True)
            render=ROOT/'build/appearance/renders'/style/color;render.mkdir(parents=True,exist_ok=True)
            subprocess.run([str(ROOT/'build/appearance/preview'),str(SLOT),str(render),style,color],check=True)
            for name in STYLE_MODELS:
                spec=specs[name]
                full=Image.open(render/(name+'.png')).convert('RGBA')
                band=Image.new('RGBA',(720,480),(0,0,0,255))
                band.alpha_composite(full,(0,spec['idle']-240))
                band.crop((0,422,720,480)).save(dest/('band-console-'+name+'.png'))
                target=dest/'consoles'/name;target.mkdir(parents=True,exist_ok=True)
                x,y,w,h=spec['sprite'];full.crop((x,y,x+w,y+h)).save(target/'body.png')
    print(f'Rendered {len(STYLES)} finishes x {len(COLORS)} colours x {len(STYLE_MODELS)} models')

if __name__=='__main__':main()
