"""Read-only mesh/raster provenance audit; writes evidence under ignored build/."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from zipfile import ZipFile
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def glb(path):
    with path.open('rb') as stream:
        header=stream.read(20)
        if header[:4]!=b'glTF':raise ValueError(str(path))
        model=json.loads(stream.read(struct.unpack_from('<I',header,12)[0]))
    triangles=sum((model['accessors'][p['indices']]['count'] if 'indices' in p else
                   model['accessors'][p['attributes']['POSITION']]['count'])//3
                  for m in model['meshes'] for p in m['primitives'] if p.get('mode',4)==4)
    return dict(triangles=triangles,images=len(model.get('images',[])),
                materials=len(model.get('materials',[])))


def audit(gba_source):
    slot=ROOT/'theme/art-book-slot/_slot'
    # Retired checkout hashes are evidence, not a dependency on a second tree.
    record=ROOT/'build/storage-cleanup-20261018/previous-runtime-hashes.json'
    previous=json.loads(record.read_text()) if record.exists() else {}
    stage=json.loads((slot/'stage/manifest.json').read_text())
    report=dict(models={},original_sources={},selected_gba={})
    for folder in sorted((slot/'consoles').iterdir()):
        model=folder/'model.glb'
        if not model.exists():continue
        master=folder/'model-master.glb'
        image=slot/'appearance/realistic/original/consoles'/folder.name/'body.png'
        entry=dict(runtime=glb(model),runtime_sha256=digest(model),
                   prepared_master=glb(master) if master.exists() else None,
                   same_mesh_as_previous_checkout=digest(model)==previous.get(folder.name) if folder.name in previous else None)
        if image.exists():
            with Image.open(image) as pixels:entry['browse_input_pixels']=list(pixels.size)
            entry['browse_raster_scale']=stage['renders']['realistic/original/'+folder.name]['scale']
        report['models'][folder.name]=entry
    sources={
        'gb':('verheyen-dmg',ROOT/'research/model-options-20261016/gb/gameboy_classic.glb'),
        'gb-cart':('letsdo3d-dmg',ROOT/'research/model-quality/originals/dmg/source/Skectfab gameboy.blend'),
        'gbc':('bpoole-cgb',ROOT/'research/model-options-20261016/gbc.glb'),
        'psp':('ostrovsky-psp',ROOT/'research/model-options-20261016/psp/sony_psp.glb'),
        'gba_cc':('graphicsgeek-ags-textured',ROOT/'research/gba/gameboy_advance_sp.glb'),
        'nds':('cianon-ds-lite',ROOT/'research/model-options-20261016/dslite/nintendo_ds_lite.glb'),
        'dreamcast':('zerescas-dreamcast',ROOT/'research/model-options-20261016/dreamcast.glb'),
        'n64':('josephrohm-n64',ROOT/'research/n64/rohm/extracted/source/N64_with_controller.fbx'),
        'psx':('darkigorek-psx-textured',ROOT/'research/model-options-20261016/sony-pvm-psx/source.blend'),
        'snes':('quick-loop-snes',ROOT/'research/snes/quick-loop/source/model/model/model.dae'),
        'snes-us':('ibbqcats-snes',ROOT/'research/snes/ibbqcats/source/Super Nintendo Console Mesh/Super Nintendo Console Mesh.stl'),
    }
    for name,(profile,path) in sources.items():
        provenance=json.loads((ROOT/'third_party/models'/profile/'source.json').read_text())
        report['original_sources'][name]=dict(path=str(path.resolve()),sha256=digest(path),
            matches_recorded_original=digest(path)==provenance.get('source_file_sha256',provenance.get('source_sha256')),
            creator=provenance['author'],url=provenance['url'])
    native=ROOT/'build/slotted-presentation/native-probes-final.log'
    if native.exists():
        for name,numbers in re.findall(r'^lcd (\w+) (.+)$',native.read_text(),re.M):
            values=list(map(float,numbers.split()));xs=values[::2];ys=values[1::2]
            factor=min(660/(max(xs)-min(xs)),328/(max(ys)-min(ys)))*(.5 if name!='nds' else 1)
            report['models'][name]['live_raster_scale']=factor
            report['models'][name]['first_lcd_source_pixels']=[abs(xs[1]-xs[0]),abs(ys[3]-ys[0])]
    report['selected_gba']=dict(directory=str(gba_source.resolve()),creator='nvfx / NeilVFX',
        url='https://www.cgtrader.com/free-3d-models/electronics/other/gameboy-advance-sp',
        licence='Editorial License (no AI), as listed 2026-10-16; local research assets, not CC/MIT',
        originals={p.name:dict(bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(gba_source.iterdir()) if p.is_file()},
        imported_full_geometry_glb=str(ROOT/'build/model-quality/gbasp-neilvfx/gbasp-full-geometry.glb'),
        imported_full_geometry=glb(ROOT/'build/model-quality/gbasp-neilvfx/gbasp-full-geometry.glb'),
        notes='OBJ retains geometry and UVs, but its MTL has only one white default material. Original C4D and texture files remain intact.')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gba-source',type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.gba_source)
    out=ROOT/'build/model-quality/audit.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n')
    assert all(e['matches_recorded_original'] for e in result['original_sources'].values()),'Original provenance mismatch'
    print('Recovered and verified',len(result['original_sources']),'original sources; wrote',out)
