"""Bake browse poses from the 2x shared native renderer, without upscaling.

Run under Linux with the native probe's SDL/GLES library environment. Local
editorial profiles stay under ignored local-models; packaged profiles use the
existing theme stage paths. No ROM data or cartridge labels are modified.
"""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.themebuild.stage import compose,save_changed,build
from tools.themebuild.appearance import STYLES,COLORS,STYLE_MODELS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe',type=Path,required=True)
    parser.add_argument('--slot',type=Path,default=ROOT/'theme/art-book-slot/_slot')
    parser.add_argument('--models',nargs='+',default=list(STYLE_MODELS))
    parser.add_argument('--all-finishes',action='store_true')
    parser.add_argument('--packaged',nargs='*',default=[],metavar='MODEL',
                        help='bake the packaged model even if a local-models profile exists (gba: SLOT_GBA_SP=graphicsgeek)')
    args=parser.parse_args()
    output=ROOT/'build/model-quality/browse';output.mkdir(parents=True,exist_ok=True)
    report=json.loads((output/'report.json').read_text()) if (output/'report.json').exists() else {}
    finishes=[(s,c) for s in STYLES for c in COLORS] if args.all_finishes else [('realistic','original')]
    for style,colour in finishes:
        env=dict(os.environ,SLOT_MODEL_STYLE=style,SLOT_CONSOLE_COLOR=colour)
        for model in args.models:
            raw=output/(model+'.bmp')
            packaged=model in args.packaged
            run=subprocess.run([str(args.probe),str(args.slot),str(raw),model,'browse'],env=dict(env,SLOT_GBA_SP='graphicsgeek') if packaged else env,text=True,capture_output=True)
            if run.returncode:raise RuntimeError(run.stdout+run.stderr)
            with Image.open(raw) as image:
                stage,entry=compose(image)
                if entry['scale']>1.001:raise ValueError('Browse still enlarges a small raster: '+model)
                local=(args.slot/'local-models/consoles'/model/'model.pose').exists() and not packaged
                if not local:
                    cached=output/style/colour/(model+'.png');save_changed(image,cached)
                    metadata=dict(mesh_sha256=hashlib.sha256((args.slot/'consoles'/model/'model.mesh').read_bytes()).hexdigest(),
                                  renderer_sha256=hashlib.sha256((ROOT/'tools/frontend/overlay/es-app/src/components/SlotNative.c').read_bytes()).hexdigest(),
                                  raster=list(image.size))
                    cached.with_suffix('.json').write_text(json.dumps(metadata,indent=2)+'\n')
            path=(args.slot/'local-models/consoles'/model/style/colour/'browse.png') if local else (args.slot/'stage'/style/colour/('browse-console-'+model+'.png'))
            save_changed(stage,path)
            report['/'.join((style,colour,model))]=dict(entry,local=local,raster=[1440,960])
        print('Rendered browse',style,colour,flush=True)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    build(args.slot,only=set(args.models))


if __name__=='__main__':main()
