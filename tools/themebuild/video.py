"""Video surface parameters derived from the same assets as the baked media."""
import json
from PIL import Image
from .geometry import ROOT, W, H, SHAPES

VARIANTS = ('snes-us','md-jp','md-ea')


def label_viewport(shape):
    spec = json.loads((ROOT/'theme/art-book-slot/_slot/shapes'/shape.name/'shape.json').read_text())
    w,h = shape.size
    if spec['size'] != [w,h]:
        raise ValueError('Label and shelf dimensions disagree: '+shape.name)
    x0,y0,x1,y1 = spec['well']
    return ((W/2-w/2+(x0+x1)/2)/W,(shape.top+(y0+y1)/2)/H),((x1-x0)/W,(y1-y0)/H)


def variants(shape):
    return ('snes-us',) if shape.name=='snes' else ('md-jp','md-ea') if shape.name=='md' else ()


def surface_binding(shape):
    # Scarab binds FLOAT properties, but neither COLOR nor vec4 shader values.
    # Use its existing saturation scalar as a surface selector in this custom
    # shader. Source RGB is preserved; alpha/fade and one-player behavior stay
    # native. The default 1.0 selects the ordinary shell, .75/.5 its variants.
    names = variants(shape)
    if not names:
        return ''
    expression = '1'
    for index,name in reversed(list(enumerate(names,1))):
        marker = 'directory({game:path}) + "/media/slotcarts/" + stem({game:path}) + ".slot-profile-'+name+'"'
        expression = 'exists('+marker+') ? %.2f : ' % (1-index/4) +expression
    return '         <saturation>'+expression+'</saturation>\n'


def build_variants(slot):
    catalogue = {name:index for family in ('snes','md')
                 for index,name in enumerate(variants(SHAPES[family]),1)}
    (slot/'video-profiles.json').write_text(json.dumps(catalogue,indent=2)+'\n',encoding='utf-8')


def disc_map(name):
    folder = ROOT / 'theme/art-book-slot/_slot/shapes' / name
    spec = json.loads((folder / 'shape.json').read_text())
    with Image.open(folder / 'edge.png') as image:
        width, height = image.size
    with Image.open(folder / 'print-mask.png') as image:
        source_width, source_height = image.size
    a, b, c, d, e, f, g, h = spec['projection']
    return ((a*width/source_width, b*height/source_width, c/source_width, 0),
            (d*width/source_height, e*height/source_height, f/source_height, 0),
            (g*width, h*height, 1, 0))


def shader_xml(shape):
    values = dict(mediaMode=0,mediaSize=' '.join(str(number) for number in shape.size))
    if shape.name not in ('psx','dreamcast','psp'):
        for index,name in enumerate((shape.name,)+variants(shape)):
            item = SHAPES[name]
            spec=json.loads((ROOT/'theme/art-book-slot/_slot/shapes'/name/'shape.json').read_text())
            x0,y0,x1,y1 = spec['well']
            w,h = item.size
            values['mediaWell%d'%index]=' '.join('%.9g'%number for number in
                                                  (x0/w,y0/h,(x1-x0)/w,(y1-y0)/h))
            values['mediaCorner%d'%index]=spec.get('wellRadius',0)
    if shape.name == 'nds':
        # Normalized DS clips stack both screens (320x480). Crop within the top
        # screen, stopping just short of the seam between them.
        values['mediaSource'] = '0 0 1 0.49'
    if shape.name in ('psx', 'dreamcast', 'psp'):
        folder = ROOT / 'theme/art-book-slot/_slot/shapes' / shape.name
        preview = json.loads((folder / 'shape.json').read_text())['preview']
        with Image.open(folder / 'print-mask.png') as image:
            source_width, source_height = image.size
        if source_width != source_height or preview['centre'] != [source_width/2, source_height/2]:
            raise ValueError('Disc preview requires a centered square art surface')
        values = dict(mediaMode=1, mediaOuter=preview.get('videoOuter',preview['outer'])/source_width,
                      mediaInner=preview.get('videoInner',preview['inner'])/source_width)
        # UMD video fills the art window's square, not the surrounding shell.
        values['mediaCanvas'] = ' '.join('%.9g' % (number/source_width)
                                         for number in preview['canvas'])
        for index, row in enumerate(disc_map(shape.name)):
            values['mediaMap%d' % index] = ' '.join('%.9g' % number for number in row)
    # Scarab treats nested shader properties as strings, including path. Resolve
    # the include's directory explicitly, just like the art's bound image paths.
    lines = ['         <shader>', '            <path>${currentPath}/shaders/media.glsl</path>']
    lines += ['            <%s>%s</%s>' % (key, value, key) for key, value in values.items()]
    lines.append('         </shader>')
    return '\n'.join(lines) + '\n'
