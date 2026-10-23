"""One place for the theme's names and paths: Slotted, plus the legacy art-book-slot.

Slotted's hand-written views live in theme/slotted. Until art-book-slot is retired, the shared
runtime assets (_slot/) stay in theme/art-book-slot/_slot and are copied into the Slotted package,
so the many existing tools keep their paths. Device folders are /userdata/themes/<name>.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLOTTED = 'Slotted'
LEGACY = 'art-book-slot'
DEVICE_THEMES = (SLOTTED, LEGACY)
H700_RUNTIME_LIBRARIES=('libasound.so.2','libcurl.so.4','libespeak.so.1','libfreeimage.so.3',
    'libfreetype.so.6','libmali.so.0','libpulse.so.0','libSDL2_image-2.0.so.0',
    'libSDL2_mixer-2.0.so.0','libSDL2-2.0.so.0','libudev.so.1','libvlc.so.5')

SLOTTED_SOURCE = ROOT / 'theme/slotted'
LEGACY_SOURCE = ROOT / 'theme' / LEGACY
SLOT_ASSETS = LEGACY_SOURCE / '_slot'

DEVICE_THEME_ROOT = '/userdata/themes'
THEME_SETTINGS = '/userdata/system/configs/emulationstation/themesettings'


def device_theme_dir(name=SLOTTED):
    if name not in DEVICE_THEMES:
        raise ValueError('Unknown theme set: ' + str(name))
    return DEVICE_THEME_ROOT + '/' + name


def device_assets(name=SLOTTED):
    return device_theme_dir(name) + '/_slot'


def device_layouts(name=SLOTTED):
    return device_assets(name) + '/tabletop/layouts'


def theme_settings(name=SLOTTED):
    return THEME_SETTINGS + '/' + name + '.cfg'
