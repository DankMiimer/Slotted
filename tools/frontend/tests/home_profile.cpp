// SLOTHOME1 round trip and rejection rules (MIT).
#include "SlotHomeProfile.h"
#include <cassert>
#include <cstdio>
using namespace slot_scene;
int main(int argc,char**argv){
    assert(argc==2);const std::string path=argv[1];HomeProfile p,loaded;
    p.overview={{-161.5f,715.5f,1566.8f},{218.6f,-50.6f,213.6f},38.5f,true};
    p.table={{0,-760,0},{0,90,0}};p.tv={{340,0,440},{0,-12,0}};p.status={{0,402,180},{0,0,0}};
    p.tableAsset="wooden-table";p.tableScale={.7f,.7f,.7f};p.transitionSeconds=1.1f;p.follow=.35f;
    for(const char*m:{"snes","n64","md-jp","gba","psp"})p.consoles.push_back({m,{{float(p.consoles.size()*100),3,-20},{0,float(p.consoles.size()*7),0}}});
    assert(writeHomeProfile(path,p)&&readHomeProfile(path,loaded));
    assert(loaded.consoles.size()==5&&loaded.consoles[2].model=="md-jp"&&loaded.consoles[4].at.rotation.y==28);
    assert(loaded.overview.eye.x==p.overview.eye.x&&loaded.overview.fov==p.overview.fov&&loaded.overview.authored&&!loaded.screen.authored);
    assert(loaded.tableAsset=="wooden-table"&&loaded.tableScale.y==.7f&&loaded.follow==.35f&&loaded.transitionSeconds==1.1f);
    // An authored screen camera round-trips.
    p.screen={{340,240,700},{340,240,440},30,true};assert(writeHomeProfile(path,p)&&readHomeProfile(path,loaded)&&loaded.screen.authored&&loaded.screen.eye.z==700);
    // Rejections: unknown model, two consoles of one room, duplicates, bad values, unknown record, wrong header.
    for(const char*bad:{"console dreamcast 0 0 0 0 0 0","console snes-us 0 0 0 0 0 0","tv 0 0 0 0 0 0","follow 2","transition 0",
                        "table_asset ../x","view_screen 0 0 0 0 0 0 40","banana 1"}){
        assert(writeHomeProfile(path,p));{std::ofstream out(path,std::ios::app);out<<bad<<'\n';}assert(!readHomeProfile(path,loaded));
    }
    {std::ofstream out(path);out<<"SLOTLAYOUT1\nviewport 720 480\n";}assert(!readHomeProfile(path,loaded));
    // Required records.
    assert(writeHomeProfile(path,p));std::ifstream in(path);std::string text,line;while(std::getline(in,line))if(line.rfind("status ",0)!=0)text+=line+'\n';in.close();
    {std::ofstream out(path);out<<text;}assert(!readHomeProfile(path,loaded));
    // Lookup prefers the requested TV, then the fixed order.
    auto exists=[](const std::string&p){return p.find("home-pvm")!=std::string::npos||p.find("home-oldtv")!=std::string::npos;};
    assert(homeProfileFor("L","oldtv",exists)=="L/home-oldtv.scene");assert(homeProfileFor("L","panasonic",exists)=="L/home-pvm.scene");
    assert(homeProfileFor("L","panasonic",[](const std::string&){return false;}).empty());
    auto fallback=defaultHomeProfile({"snes","gba","psp"});assert(fallback.consoles.size()==3&&fallback.consoles[1].at.position.z<fallback.consoles[0].at.position.z);
    std::remove(path.c_str());std::puts("home profile passed");
}
