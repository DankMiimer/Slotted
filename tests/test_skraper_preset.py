"""The Skraper preset adds the theme's media without disturbing a user's setup."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'theme/art-book-slot/_slot/skraper'))
import apply_preset
from preset import NORMALIZED_VIDEO, SUPPORT_TEXTURE, WHEEL

BOX = {'Type': 0, 'Image': 3, 'OutputFolder': '%ROMROOTFOLDER%\\images', 'LinkToNode': True}


def system(folder, medias=None):
    return {'Overriden': 8 if medias is not None else 2, 'SystemId': 1,
            'GamesAndRoms': {'Path': '\\\\HOST\\share\\roms\\' + folder},
            'Medias': medias or []}


def config(*systems):
    return {'ScreenScraperAccount': {'Login': 'x', 'Password': 'y'},
            'AllSystems': {'Medias': [BOX]}, 'Systems': list(systems)}


class SkraperPreset(unittest.TestCase):
    def test_keeps_existing_media_and_adds_theme_media_once(self):
        data = config(system('snes'), system('3do'))
        original = copy.deepcopy(data)
        self.assertEqual(apply_preset.apply(data), ['snes'])
        self.assertEqual(apply_preset.apply(data), ['snes'])  # repeatable
        snes = data['Systems'][0]
        kinds = [(m['Type'], m.get('Image')) for m in snes['Medias']]
        self.assertEqual(kinds, [(0, 3), (0, SUPPORT_TEXTURE), (0, WHEEL), (NORMALIZED_VIDEO, 0)])
        self.assertTrue(snes['Overriden'] & 8)
        self.assertEqual(data['Systems'][1], original['Systems'][1])
        self.assertEqual(data['ScreenScraperAccount'], original['ScreenScraperAccount'])
        self.assertEqual(data['AllSystems'], original['AllSystems'])

    def test_labels_never_take_over_gamelist_images(self):
        data = config(system('gb'))
        apply_preset.apply(data)
        linked = {(m['Type'], m.get('Image')): m['LinkToNode'] for m in data['Systems'][0]['Medias']}
        self.assertFalse(linked[(0, SUPPORT_TEXTURE)])
        self.assertFalse(linked[(0, WHEEL)])
        self.assertTrue(linked[(NORMALIZED_VIDEO, 0)])

    def test_an_existing_video_entry_is_kept_instead_of_adding_one(self):
        theirs = {'Type': 3, 'Image': 0, 'OutputFolder': '%ROMROOTFOLDER%\\videos', 'LinkToNode': True}
        data = config(system('psx', [BOX, theirs]))
        apply_preset.apply(data)
        medias = data['Systems'][0]['Medias']
        self.assertIn(theirs, medias)
        self.assertEqual([m for m in medias if m['Type'] in (3, NORMALIZED_VIDEO)], [theirs])


if __name__ == '__main__':
    unittest.main()
