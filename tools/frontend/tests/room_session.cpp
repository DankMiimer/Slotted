#include "SlotRoomSession.h"
#include "SlotWorldProfile.h"
#include <cassert>
#include <cstdio>
#include <iostream>

static void finish(slot::State&s){for(int i=0;i<100&&s.busy();i++)s.update(.05f);}
int main(int argc,char**argv){
    slot::RoomSession session;
    auto&nes=session.console("nes").media;
    nes.insert("/nes/A.nes");finish(nes);
    session.leave("nes","/nes/B.nes",7);
    auto&gba=session.console("gba").media;gba.insert("/gba/C.gba");finish(gba);
    assert(nes.inserted()=="/nes/A.nes"&&gba.inserted()=="/gba/C.gba");
    assert(&session.console("nes").media==&nes&&session.console("nes").loadedHome==7);
    // A swap underway when its view disappears finishes logically, never launches.
    nes.insert("/nes/B.nes");session.leave("nes","/nes/B.nes",3);
    assert(nes.inserted()=="/nes/B.nes"&&nes.takeLaunch().empty()&&!nes.busy());
    nes.play("/nes/B.nes");session.leave("nes","/nes/B.nes",3);
    assert(nes.takeLaunch().empty());
    // An actual handoff retains exactly-once launch state through graphics teardown.
    nes.play("/nes/B.nes");assert(nes.takeLaunch()=="/nes/B.nes");nes.running();
    session.leave("nes","/nes/B.nes",3);assert(nes.launching());
    nes.returned();assert(nes.inserted()=="/nes/B.nes"&&nes.takeLaunch().empty());
    nes.eject();session.leave("nes","/nes/B.nes",3);assert(nes.inserted().empty());
    assert(gba.inserted()=="/gba/C.gba");
    session.invalidate("/gba/C.gba");assert(gba.inserted().empty());
    session.homeConsole("nes");session.homeChannel("recent");
    assert(session.homeChannels()&&session.homeConsole()=="nes"&&session.homeChannel()=="recent");
    session.homeConsole("gba");assert(!session.homeChannels()&&session.homeChannel()=="recent");

    using namespace slot_scene;
    WorldProfile world;world.tables["wooden-table"].position.y=417;
    world.paths.push_back({"table","wooden-table",1.2f,{0,100,50},{0,200,-50}});
    assert(validWorld(world));
    const auto forward=worldPath(world,"table","wooden-table"),reverse=worldPath(world,"wooden-table","table");
    const Vec a={0,900,200},b={4200,700,-300};
    for(int i=0;i<=100;i++){
        const float t=i/100.f;
        const Vec x=worldFlight(a,b,forward,t),y=worldFlight(b,a,reverse,1-t);
        assert(dot(sub(x,y),sub(x,y))<.0001f);
    }
    assert(worldFlight(a,b,forward,0).x==a.x&&worldFlight(a,b,forward,1).x==b.x);
    auto invalid=world;invalid.tables["table"].rotation.x=1;assert(!validWorld(invalid));
    invalid=world;invalid.paths.push_back(forward);assert(!validWorld(invalid));
    invalid=world;invalid.paths[0].seconds=0;assert(!validWorld(invalid));
    if(argc==2){
        assert(writeWorldProfile(argv[1],world));WorldProfile loaded;
        assert(readWorldProfile(argv[1],loaded)&&loaded.authored&&loaded.tables.size()==3&&loaded.paths.size()==1);
        assert(loaded.tables.at("wooden-table").position.y==417);
        {std::ofstream bad(argv[1]);bad<<"SLOTWORLD1\nroom 0 -8000 8000 -6000 6000 3600\ntable table 0 805 0 0 0 0\nunknown 1\n";}
        const auto old=loaded;assert(!readWorldProfile(argv[1],loaded));
        assert(loaded.paths.size()==old.paths.size()&&loaded.tables.size()==old.tables.size());
    }
    std::cout<<"Room session: media survives view/graphics changes; explicit eject; exactly-once handoff; world paths and strict profile round-trip pass.\n";
}
