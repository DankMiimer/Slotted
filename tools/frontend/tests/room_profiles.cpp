#include "SlotWorldProfile.h"
#include "SlotHomeProfile.h"
#include <cassert>
#include <iostream>
int main(int argc,char**argv){
    assert(argc==3);slot_scene::WorldProfile world;slot_scene::HomeProfile home;
    assert(slot_scene::readWorldProfile(argv[1],world));assert(world.tables.size()==3&&world.paths.size()==2);
    assert(slot_scene::readHomeProfile(argv[2],home));assert(home.consoles.size()==11&&home.screen.authored);
    assert(home.screen.eye.y==800&&home.overview.authored);
    std::cout<<"Native room/home parsers accept editor output with all 11 current models and separate TV camera.\n";
}
