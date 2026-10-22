import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from tools.slotted import install,package_candidate

class CandidatePackage(unittest.TestCase):
    def test_rejects_old_capabilities_or_wrong_architecture_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);candidate=root/'binary';output=root/'release'
            header=b'\x7fELF\x02\x01'+bytes(12)+b'\xb7\x00'
            for data in [b'host '+b''.join(package_candidate.MARKERS),header+b'old room',header.replace(b'\xb7\x00',b'\x3e\x00')+b''.join(package_candidate.MARKERS)]:
                candidate.write_bytes(data)
                with self.assertRaises(ValueError):package_candidate.build(candidate,output)
                self.assertFalse(output.exists())

    def test_owned_package_has_verified_source_and_leaves_models_profiles_alone(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);theme=root/'theme/slotted';theme.mkdir(parents=True)
            (theme/'theme.xml').write_bytes(b'<theme/>');(theme/'_slot').mkdir();(theme/'_slot/model.mesh').write_bytes(b'valuable current full model')
            profile=root/'scene-layouts/gba-pvm.json';profile.parent.mkdir();profile.write_bytes(b'authored camera bytes')
            names=['tools/frontend/apply.py','tools/frontend/SlotState.h','tools/slot_theme.py','tools/tabletop/install_transition_frontend.py','tools/frontend/persistence.py','docs/SLOTTED_THEME_PLAN.md','docs/TABLETOP_HANDOFF.md','CREDITS.md','LICENSE']
            for name in names:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(name.encode())
            binary=root/'candidate';binary.write_bytes(b'\x7fELF\x02\x01'+bytes(12)+b'\xb7\x00'+b''.join(package_candidate.MARKERS))
            with patch.object(package_candidate,'ROOT',root),patch.object(package_candidate,'package',side_effect=lambda out:install.package(out,theme)):
                output,receipt=package_candidate.build(binary,root/'release')
                with self.assertRaises(FileExistsError):package_candidate.build(binary,output)
            self.assertEqual(receipt['state'],'candidate-not-installed')
            self.assertEqual((output/'frontend-candidate').read_bytes(),binary.read_bytes())
            for name,sha in json.loads((output/'owned-source.json').read_text()).items():
                self.assertEqual(hashlib.sha256((output/'source'/name).read_bytes()).hexdigest(),sha)
            with tarfile.open(output/'payload.tar') as archive:self.assertEqual(archive.getnames(),['theme.xml'])
            self.assertEqual(profile.read_bytes(),b'authored camera bytes')
            self.assertEqual((theme/'_slot/model.mesh').read_bytes(),b'valuable current full model')
            self.assertFalse((output/'source/scene-layouts').exists())

if __name__=='__main__':unittest.main()
