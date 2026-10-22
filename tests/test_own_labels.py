"""Own labels, including the JPEG scans Skraper keeps, take priority over every fallback."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'theme/art-book-slot/_slot'))
from slotcart import labels
from slotcart.library import CrcCache, scan


class NoArt:
    def entry(self, crc):
        return {}


class OwnLabels(unittest.TestCase):
    def games(self, root):
        folder = root/'nes'
        folder.mkdir()
        (folder/'Game (Europe).nes').write_bytes(b'NES\x1a' + bytes(16 + 16384))
        return scan(root, ['nes'], CrcCache(root/'cache')), folder

    def test_jpeg_label_from_skraper_is_used_first(self):
        with tempfile.TemporaryDirectory() as directory:
            games, folder = self.games(Path(directory))
            (folder/'media/labels').mkdir(parents=True)
            label = folder/'media/labels/Game (Europe).jpg'
            label.write_bytes(b'jpeg')
            plans = labels.candidates(games[0], NoArt())
            self.assertEqual(plans[0], ('own', str(label), None))

    def test_png_wins_over_jpeg_and_text_is_last(self):
        with tempfile.TemporaryDirectory() as directory:
            games, folder = self.games(Path(directory))
            (folder/'media/labels').mkdir(parents=True)
            for suffix in ('.jpg', '.png'):
                (folder/('media/labels/Game (Europe)' + suffix)).write_bytes(b'image')
            plans = labels.candidates(games[0], NoArt())
            self.assertEqual(Path(plans[0][1]).suffix, '.png')
            self.assertEqual(plans[-1][0], 'text')


if __name__ == '__main__':
    unittest.main()
