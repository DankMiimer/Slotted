// Regression: a Panasonic preview must not hide saved PVM handheld layouts. MIT.
#include "SlotSceneProfile.h"
#include <cassert>
#include <set>
#include <cstdio>
using namespace slot_scene;
int main(){
    std::set<std::string>files={"layouts/snes-panasonic.scene","layouts/snes-pvm.scene"};
    auto exists=[&](const std::string&p){return files.count(p)!=0;};
    for(const auto*system:{"gb","gbc","gba","nds","psp"}){
        const std::string own=std::string("layouts/")+system+"-pvm.scene";files.insert(own);
        for(const auto*tv:{"panasonic","pvm","oldtv"}){
            auto selected=sceneProfileFor("layouts",system,tv,exists);
            assert(selected.path==own&&selected.system==system&&selected.tv=="pvm");
        }
    }
    files.insert("layouts/gba-panasonic.scene");
    assert(sceneProfileFor("layouts","gba","panasonic",exists).tv=="panasonic");
    assert(sceneProfileFor("layouts","gba","pvm",exists).tv=="pvm");
    files.insert("layouts/n64-panasonic.scene");
    assert(sceneProfileFor("layouts","n64","pvm",exists).system=="n64");
    assert(sceneProfileFor("layouts","nes","pvm",exists).path=="layouts/snes-pvm.scene");
    assert(sceneProfileFor("layouts","nes","oldtv",exists).path=="layouts/snes-panasonic.scene");
    files.clear();files.insert("layouts/gb-pvm.scene");
    assert(sceneProfileFor("layouts","gba","panasonic",exists).path.empty());
    std::puts("console-authored layouts precede shared fallbacks for every TV");
}
