"""Preview links add only <video>, keep play data, never replace working videos, and undo."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'theme/art-book-slot/_slot'))
from slotcart import previews

GAMELIST = """<?xml version="1.0"?>
<gameList>
\t<game>
\t\t<path>./Listed (Europe).sfc</path>
\t\t<name>Listed</name>
\t\t<playcount>7</playcount>
\t\t<favorite>true</favorite>
\t</game>
\t<game>
\t\t<path>./Has Video (USA).sfc</path>
\t\t<video>./videos/Has Video (USA)-video.mp4</video>
\t</game>
</gameList>
"""


class PreviewLinks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.roms = Path(self.temp.name) / 'roms'
        snes = self.roms / 'snes'
        (snes / 'media/videos').mkdir(parents=True)
        (snes / 'videos').mkdir()
        for name in ('Listed (Europe)', 'Has Video (USA)', 'Unlisted (Japan)'):
            (snes / (name + '.sfc')).write_bytes(b'rom')
            (snes / 'media/videos' / (name + '.mp4')).write_bytes(b'clip')
        (snes / 'videos/Has Video (USA)-video.mp4').write_bytes(b'old clip')
        (snes / 'gamelist.xml').write_text(GAMELIST)
        psx = self.roms / 'psx'
        (psx / 'media/videos').mkdir(parents=True)
        for suffix in ('.cue', '.bin'):
            (psx / ('Disc Game' + suffix)).write_bytes(b'disc')
        (psx / 'media/videos/Disc Game.mp4').write_bytes(b'clip')
        self.journals = Path(self.temp.name) / 'journals'
        patcher = patch.object(previews, 'JOURNALS', self.journals)
        patcher.start()
        self.addCleanup(patcher.stop)

    def games(self, system):
        root = ET.parse(self.roms / system / 'gamelist.xml').getroot()
        return {g.findtext('path'): g for g in root.iter('game')}

    def test_link_adds_only_missing_videos_and_keeps_play_data(self):
        self.assertEqual(previews.link(['snes'], roms=self.roms), 2)
        games = self.games('snes')
        listed = games['./Listed (Europe).sfc']
        self.assertEqual(listed.findtext('video'), './media/videos/Listed (Europe).mp4')
        self.assertEqual((listed.findtext('playcount'), listed.findtext('favorite')), ('7', 'true'))
        self.assertEqual(games['./Has Video (USA).sfc'].findtext('video'),
                         './videos/Has Video (USA)-video.mp4')
        unlisted = games['./Unlisted (Japan).sfc']
        self.assertEqual([child.tag for child in unlisted], ['path', 'video'])

    def test_disc_images_get_one_entry(self):
        self.assertEqual(previews.link(['psx'], roms=self.roms), 1)
        self.assertEqual(list(self.games('psx')), ['./Disc Game.cue'])

    def test_restore_removes_only_our_links(self):
        previews.link(['snes'], roms=self.roms)
        journal = next(self.journals.glob('*/journal.json'))
        previews.restore(journal)
        games = self.games('snes')
        self.assertIsNone(games['./Listed (Europe).sfc'].find('video'))
        self.assertEqual(games['./Listed (Europe).sfc'].findtext('playcount'), '7')
        self.assertNotIn('./Unlisted (Japan).sfc', games)
        self.assertEqual(games['./Has Video (USA).sfc'].findtext('video'),
                         './videos/Has Video (USA)-video.mp4')

    def test_dry_run_changes_nothing(self):
        before = (self.roms / 'snes/gamelist.xml').read_bytes()
        previews.link(['snes'], dry_run=True, roms=self.roms)
        self.assertEqual((self.roms / 'snes/gamelist.xml').read_bytes(), before)
        self.assertFalse(self.journals.exists())


if __name__ == '__main__':
    unittest.main()
