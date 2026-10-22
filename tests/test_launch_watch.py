"""The early launch signal must be a complete ROM export, never stale/partial XML."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

SOURCE = Path(__file__).resolve().parents[1] / 'theme/art-book-slot/_slot/launch/watch.py'
spec = importlib.util.spec_from_file_location('slot_launch_watch', SOURCE)
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


class LaunchExportTests(unittest.TestCase):
    def test_xml_entities_and_rom_path_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'game.xml'
            rom = '/userdata/roms/nes/Snow Bros & Friends (Europe).nes'
            root = ET.Element('gameList')
            ET.SubElement(ET.SubElement(root, 'game'), 'path').text = rom
            ET.ElementTree(root).write(path, encoding='utf-8')
            self.assertEqual(watch.launch_rom(path), rom)

    def test_partial_missing_and_non_rom_exports_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'game.xml'
            self.assertIsNone(watch.launch_rom(path))
            for xml in ('<gameList><game>', '<gameList/>',
                        '<gameList><game><path>/etc/passwd</path></game></gameList>'):
                path.write_text(xml)
                self.assertIsNone(watch.launch_rom(path))
