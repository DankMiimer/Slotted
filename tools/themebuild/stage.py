"""Recognizable browse-stage renders from the approved model appearance assets.

Keeps full model silhouettes, transparent wallpaper and uniform scale. Does not
rebake ROMs, change model geometry or replace the native launch endpoint.
"""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFilter

from .geometry import ROOT

WIDTH, HEIGHT, TOP = 720, 240, 240
# Twice the initial slotted-view prototype's 108 x 120 housing envelope.
MODEL_HEIGHT, MODEL_WIDTH = 228, 552


def compose(body):
    body = body.convert('RGBA')
    bounds = body.getchannel('A').getbbox()
    if bounds is None:
        raise ValueError('Console render has no visible pixels')
    crop = body.crop(bounds)
    scale = min(MODEL_WIDTH / crop.width, MODEL_HEIGHT / crop.height)
    size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
    model = crop.resize(size, Image.Resampling.LANCZOS)
    stage = Image.new('RGBA', (WIDTH, HEIGHT))
    shadow = Image.new('RGBA', stage.size)
    draw = ImageDraw.Draw(shadow)
    shadow_width = min(230, size[0])
    draw.ellipse((360-shadow_width/2, HEIGHT-16, 360+shadow_width/2, HEIGHT-4), fill=(0, 0, 0, 100))
    stage.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(3)))
    x, y = (WIDTH-size[0])//2, HEIGHT-4-size[1]
    stage.alpha_composite(model, (x, y))
    return stage, dict(source_bounds=list(bounds), scale=scale, bounds=[x,y,*size])


def save_changed(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with Image.open(path) as previous:
            if previous.mode == image.mode and previous.size == image.size and previous.tobytes() == image.tobytes():
                return
    image.save(path)


def build(slot,only=None):
    slot = Path(slot)
    source = slot / 'appearance'
    shelf = ET.parse(source/'shelf.xml')
    view = shelf.getroot().find('view')
    appearance = view.find('image')
    appearance.set('name', 'slot-browse-console')
    appearance.find('pos').text = '0 0.5'
    appearance.find('size').text = '1 0.5'
    appearance.find('zIndex').text = '10'
    # The native component supplies the regional profile. Knulli's expression
    # parser cannot reliably concatenate the old deeply nested ternary path.
    appearance.find('path').text = ''
    # The capable frontend hides inherited bands at runtime. Keep XML fallback
    # intact: after a reboot the official binary must still show its console.
    report = dict(version=1, size=[WIDTH,HEIGHT], top=TOP,
                  model_source='cd6ca96', default_style='realistic', renders={})
    manifest=slot/'stage/manifest.json'
    if only and manifest.exists():report=json.loads(manifest.read_text())
    for path in sorted(source.glob('*/*/consoles/*/body.png')):
        style, color, _, model, _ = path.relative_to(source).parts
        if only and model not in only:continue
        # Prefer the native 2x pose cache when it matches this exact mesh.
        # Never read local editorial profiles into distributable stage assets.
        cached=ROOT/'build/model-quality/browse'/style/color/(model+'.png')
        metadata=cached.with_suffix('.json')
        quality=None
        if cached.exists() and metadata.exists():
            candidate=json.loads(metadata.read_text())
            mesh=slot/'consoles'/model/'model.mesh'
            renderer=ROOT/'tools/frontend/overlay/es-app/src/components/SlotNative.c'
            if (candidate.get('mesh_sha256')==hashlib.sha256(mesh.read_bytes()).hexdigest()
                and candidate.get('renderer_sha256')==hashlib.sha256(renderer.read_bytes()).hexdigest()):
                quality=candidate;path=cached
        with Image.open(path) as body:
            image, entry = compose(body)
            crop = body.crop(body.getchannel('A').getbbox())
        output = slot/'stage'/style/color/('browse-console-'+model+'.png')
        save_changed(image, output)
        save_changed(crop, output.with_name('console-'+model+'.png'))
        entry['source_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        if quality:entry.update(raster=quality['raster'],renderer='SlotNative 2x',mesh_sha256=quality['mesh_sha256'])
        report['renders']['/'.join((style,color,model))] = entry
    if not report['renders']:
        raise ValueError('No current model appearance assets; integrate/build them first')
    target=slot/'stage'
    target.mkdir(parents=True,exist_ok=True)
    ET.indent(shelf, space='   ')
    shelf.write(target/'shelf.xml',encoding='UTF-8',xml_declaration=True)
    (target/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__ == '__main__':
    report=build(ROOT/'theme/art-book-slot/_slot')
    print('Built',len(report['renders']),'full-silhouette browse-stage renders')
