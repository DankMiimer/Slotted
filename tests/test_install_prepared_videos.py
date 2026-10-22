"""A preview migration must preserve originals and undo only its own metadata."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import xml.etree.ElementTree as E

from tools.dev.install_prepared_videos import install, restore


class PreparedVideoInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'roms'
        self.system=self.root/'gba'
        self.source=self.system/'videos/game.mp4'
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b'original anamorphic clip')
        self.target=self.source.parent/'.slot-square-pixels/game-corrected.mp4'
        self.gamelist=self.system/'gamelist.xml'
        self.gamelist.write_text('<gameList><!--keep--><game><path>./game.gba</path>'
                                '<video>./videos/game.mp4</video><playcount>7</playcount>'
                                '<name>My Game</name></game></gameList>')
        self.original_metadata=self.gamelist.read_bytes()
        self.plan=Path(self.temp.name)/'plan.json'
        self.archive=Path(self.temp.name)/'clips.tar'
        self.journal=Path(self.temp.name)/'journal'
        self.clip=b'prepared square pixel clip'
        self.entry=dict(path=str(self.source),target=str(self.target),
                        archive='0123456789abcdef.mp4',
                        original_sha256=hashlib.sha256(self.source.read_bytes()).hexdigest(),
                        preview_sha256=hashlib.sha256(self.clip).hexdigest())
        self.write_plan()
        self.write_archive(self.clip)

    def write_plan(self):
        self.plan.write_text(json.dumps([self.entry]))

    def write_archive(self,clip):
        with tarfile.open(self.archive,'w') as archive:
            member=tarfile.TarInfo(self.entry['archive'])
            member.size=len(clip)
            archive.addfile(member,io.BytesIO(clip))

    def install(self):
        return install(self.root,self.plan,self.archive,self.journal)

    def test_install_and_restore_preserve_originals_and_later_play_counts(self):
        report=self.install()
        self.assertEqual((report['copies'],report['links'],report['gamelists']),(1,1,1))
        self.assertEqual(self.target.read_bytes(),self.clip)
        self.assertEqual(self.source.read_bytes(),b'original anamorphic clip')
        self.assertEqual((self.journal/'gba-gamelist.xml').read_bytes(),self.original_metadata)
        self.assertIn(b'<!--keep-->',self.gamelist.read_bytes())
        tree=E.parse(self.gamelist)
        self.assertEqual(tree.findtext('.//video'),'./videos/.slot-square-pixels/game-corrected.mp4')
        tree.find('.//playcount').text='8'
        tree.write(self.gamelist)
        self.assertEqual(restore(self.journal),dict(restored=1,skipped=0))
        tree=E.parse(self.gamelist)
        self.assertEqual(tree.findtext('.//video'),'./videos/game.mp4')
        self.assertEqual(tree.findtext('.//playcount'),'8')
        self.assertEqual(restore(self.journal),dict(restored=0,skipped=1))
        with self.assertRaises(FileExistsError):self.install()

    def test_restore_keeps_a_new_user_selected_video(self):
        self.install()
        tree=E.parse(self.gamelist)
        tree.find('.//video').text='./videos/user-replacement.mp4'
        tree.write(self.gamelist)
        before=self.gamelist.read_bytes()
        self.assertEqual(restore(self.journal),dict(restored=0,skipped=1))
        self.assertEqual(self.gamelist.read_bytes(),before)

    def test_bad_archive_keeps_metadata_and_cleans_staging_file(self):
        self.write_archive(b'corrupt prepared clip')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.install()
        self.assertEqual(self.gamelist.read_bytes(),self.original_metadata)
        self.assertFalse(self.target.exists())
        self.assertEqual(list(self.target.parent.glob('.preparing-*')),[])
        self.assertEqual(restore(self.journal),dict(restored=0,skipped=1))

    def test_foreign_path_and_changed_source_rejected_before_any_edits(self):
        self.entry['target']=str(Path(self.temp.name)/'outside/game.mp4')
        self.write_plan()
        with self.assertRaisesRegex(ValueError,'escapes'):self.install()
        self.assertFalse(self.journal.exists())
        self.entry['target']=str(self.target)
        self.write_plan()
        self.source.write_bytes(b'user changed original')
        with self.assertRaisesRegex(ValueError,'Original clip changed'):self.install()
        self.assertFalse(self.journal.exists())
        self.assertEqual(self.gamelist.read_bytes(),self.original_metadata)


if __name__=='__main__':
    unittest.main()
