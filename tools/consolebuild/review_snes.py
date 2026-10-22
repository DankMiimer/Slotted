"""Independent neutral before/after and loaded views of exported SNES meshes."""
import os,sys
from pathlib import Path
import bpy
from mathutils import Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from review_media import add,clear,render,VIEWS
from snes import SPECS
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/snes'

def main():
    for version in os.environ.get('SLOT_REVIEW_VERSIONS','before after').split():
        assets=OUT/'before/theme/art-book-slot/_slot' if version=='before' else ROOT/'theme/art-book-slot/_slot'
        for name,s in SPECS.items():
            target=OUT/'neutral'/version/name;target.mkdir(parents=True,exist_ok=True)
            for view,direction in VIEWS.items():
                clear();add(assets/'consoles'/name/'model.glb')
                render(target/(view+'.png'),direction,6.9)
            if version=='after':
                for view,direction in (('loaded-front',(.25,-1,.7)),('loaded-side',(1,0,.1)),('loaded-rear',(.25,1,.5))):
                    clear();add(assets/'consoles'/name/'model.glb')
                    media=add(assets/'consoles'/name/'media.glb')
                    q=s['scale'];centre=(s['media'][1]/2+s['entry']-s['seat_depth'])*q
                    for o in media:o.matrix_world=Matrix.Translation((0,-s['slot']*q*.01,centre*.01))@o.matrix_world
                    render(target/(view+'.png'),direction,6.9)

if __name__=='__main__':main()
