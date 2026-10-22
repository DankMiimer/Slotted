"""Optional scene controls. Legacy version-one profiles retain their exact values."""
import math
import re

VIEWS = ('all', 'tv', 'cartridge', 'console', 'inspect')
TABLES = {'table': 'Wooden table · lena-wachs', 'tv-stand': 'TV stand · Qu3st10n',
          'wooden-table': 'Wooden table · AndreyUEDev'}
TVS = ('panasonic', 'pvm', 'oldtv')
FIELDS = ('title', 'hud', 'artwork', 'description', 'facts', 'footer', 'video', 'library')


def number(value, low, high):
    if type(value) not in (float, int) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'Expected a finite number from {low} to {high}')
    return float(value)


def camera(value, vector):
    eye, target = vector(value['position']), vector(value['target'])
    if sum((a-b)**2 for a, b in zip(eye, target)) < 100:
        raise ValueError('Camera must be at least 10 mm from its target')
    return dict(position=eye, target=target, fov=number(value['fov'], 5, 110))


def display(value):
    result = {}
    if set(value) != {'enabled', 'layout', 'textScale', 'padding', 'background', 'foreground', 'accent', 'fields'}:
        raise ValueError('Invalid display settings')
    if type(value['enabled']) is not bool or value['layout'] not in ('split', 'text', 'artwork'):
        raise ValueError('Invalid display mode')
    result.update(enabled=value['enabled'], layout=value['layout'],
                  textScale=number(value['textScale'], .5, 2), padding=number(value['padding'], 0, 40))
    for key in ('background', 'foreground', 'accent'):
        if not isinstance(value[key], str) or not re.fullmatch('#[0-9a-fA-F]{6}', value[key]):
            raise ValueError('Use six-digit display colours')
        result[key] = value[key].lower()
    if set(value['fields']) != set(FIELDS) or any(type(v) is not bool for v in value['fields'].values()):
        raise ValueError('Invalid metadata fields')
    result['fields'] = {key: value['fields'][key] for key in FIELDS}
    return result


def validate_extras(value, vector):
    result = {}
    if 'browseView' in value:
        if value['browseView'] not in VIEWS[:4]:
            raise ValueError('Invalid default browse view')
        result['browseView'] = value['browseView']
    if 'cameras' in value:
        if not set(value['cameras']).issubset(VIEWS):
            raise ValueError('Unknown camera view')
        result['cameras'] = {key: camera(cam, vector) for key, cam in value['cameras'].items()}
        if 'all' in result['cameras'] and result['cameras']['all'] != camera(value['camera'], vector):
            raise ValueError('Overview camera and all view must agree')
    if 'transitionSeconds' in value:
        result['transitionSeconds'] = number(value['transitionSeconds'], .1, 5)
    if 'table' in value:
        table = value['table']
        if set(table) != {'model', 'scale'} or table['model'] not in TABLES:
            raise ValueError('Invalid table model')
        if not isinstance(table['scale'], list) or len(table['scale']) != 3:
            raise ValueError('Table scale requires XYZ')
        result['table'] = dict(model=table['model'], scale=[number(v, .1, 5) for v in table['scale']])
    if 'displays' in value:
        if set(value['displays']) != {'tv', 'handheld'}:
            raise ValueError('Use TV and handheld display settings')
        result['displays'] = {key: display(v) for key, v in value['displays'].items()}
    return result


def native_extras(profile):
    def nums(values):
        return ' '.join(format(v, '.9g') for v in values)
    lines = []
    if 'browseView' in profile:
        lines.append('browse_view ' + str(VIEWS.index(profile['browseView'])))
    for key, cam in profile.get('cameras', {}).items():
        if key != 'all':
            lines.append('view_' + key + ' ' + nums(cam['position'] + cam['target'] + [cam['fov']]))
    if 'transitionSeconds' in profile:
        lines.append('transition ' + nums([profile['transitionSeconds']]))
    if 'table' in profile:
        lines.append('table_asset ' + profile['table']['model'])
        lines.append('table_scale ' + nums(profile['table']['scale']))
    for key, spec in profile.get('displays', {}).items():
        mask = sum(int(spec['fields'][field]) << i for i, field in enumerate(FIELDS))
        lines.append('display_' + key + ' ' + nums([int(spec['enabled']), ('split', 'text', 'artwork').index(spec['layout']),
                     spec['textScale'], spec['padding'], mask] + [int(spec[c][1:], 16) for c in ('background', 'foreground', 'accent')]))
    return lines
