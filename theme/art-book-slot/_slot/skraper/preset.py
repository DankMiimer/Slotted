"""What Art Book Slot needs from ScreenScraper, expressed as Skraper media entries.

Skraper 1.x stores media as numbers (SkraperLibrary2.Configuration.System.Media):
MediaType 0 Image, 4 NormalizedVideo; ImageType 9 SupportTexture, 10 Wheel.
"""
SHELF_SYSTEMS = ('gb', 'gbc', 'gba', 'snes', 'nes', 'n64', 'megadrive', 'genesis',
                 'psx', 'psp', 'nds')

IMAGE, NORMALIZED_VIDEO = 0, 4
SUPPORT_TEXTURE, WHEEL = 9, 10

# Folders below each ROM folder, where the theme's baker and preview linker look.
# Only the video is linked into the gamelist: a label or wheel linked there would
# replace the user's own <image>/<marquee> choice.
TARGETS = (
    (IMAGE, SUPPORT_TEXTURE, 'media\\labels', False),     # flat label/disc scan
    (IMAGE, WHEEL, 'media\\wheels', False),               # logo for logo labels
    (NORMALIZED_VIDEO, 0, 'media\\videos', True),         # shelf preview
)


def media_entries(root='%ROMROOTFOLDER%'):
    return [{'Type': kind, 'Image': image, 'Title': None, 'InternalMix': 0, 'LocalMixFile': '',
             'OutputFolder': root + '\\' + folder, 'EmptyOutputFolder': False,
             # Full resolution: the baker crops and scales labels itself.
             'ResizeWidth': False, 'ResizeHeight': False, 'KeepRatio': True,
             'ResizeWidthValue': 800, 'ResizeHeightValue': 600,
             'LinkToNode': link, 'Optimize': False}
            for kind, image, folder, link in TARGETS]


def is_theme_entry(entry):
    return any(entry.get('Type') == kind and (kind != IMAGE or entry.get('Image') == image)
               for kind, image, _, _ in TARGETS)
