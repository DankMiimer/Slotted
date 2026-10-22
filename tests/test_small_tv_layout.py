"""Exercise actual layout arithmetic: small glass must leave a readable body above the footer."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class SmallTVLayout(unittest.TestCase):
    @unittest.skipUnless(os.name=='posix','host C++ compiler')
    def test_one_and_two_line_titles_leave_body_clear_of_footer_on_all_tvs(self):
        header=ROOT/'tools/frontend/overlay/es-app/src/components/SlotMetadataLayout.h'
        source='''#include "'''+str(header)+'''"
#include <cassert>
#include <cmath>
int main(){
    const float glass[][2]={{155,108},{184,143},{222,159}};
    for(auto& area:glass)for(int lines=1;lines<=2;lines++){
        auto layout=slotMetadataLayout(area[0],area[1],false);
        float title=std::ceil(21*layout.type*1.4f*1.05f*lines)+1;
        float y=layout.bodyTop(title,false),h=layout.bodyHeight(area[1],title,false);
        assert(h>=20);assert(y+h<=area[1]-layout.footerOffset-1);
        assert(title+layout.hudGap+layout.hudHeight<=y);
    }
    auto handheld=slotMetadataLayout(155,108,true);assert(handheld.type==1);
}'''
        with tempfile.TemporaryDirectory() as tmp:
            cpp=Path(tmp)/'layout.cpp';cpp.write_text(source);binary=Path(tmp)/'layout'
            subprocess.run(['g++','-std=c++11',str(cpp),'-o',str(binary)],check=True,capture_output=True)
            subprocess.run([str(binary)],check=True,capture_output=True)

    def test_pvm_is_licensed_blank_glass_without_loose_power_geometry(self):
        profile=json.loads((ROOT/'theme/art-book-slot/_slot/stage/tv/pvm.json').read_text())
        self.assertEqual(profile['license'],'CC BY 4.0')
        self.assertEqual(len(profile['removed_power_islands']),6)
        self.assertLess(profile['source_size_metres'][0],.4)
        self.assertEqual(profile['glass_polygons'],320)
        self.assertLessEqual(profile['display'][1],352)
