// Native profile compatibility: preserve authored eight/twelve-cart layouts (MIT).
#include "SlotSceneProfile.h"
#include "SlotSceneCamera.h"
#include <cassert>
#include <cstdio>
using namespace slot_scene;
int main(int argc,char**argv){
    assert(argc==2);std::string path=argv[1];SceneProfile original,loaded;
    original.eye={-161.50935f,715.5572f,1566.8765f};original.target={218.6796f,-509.6783f,213.6335f};
    for(int i=0;i<sceneMaxNodes;i++)original.nodes[i]={{float(i*19),10,float(i*31)},{-90,float(i*7),0}};
    for(int count:{8,12}){
        original.cartridgeCount=count;assert(writeSceneProfile(path,original));assert(readSceneProfile(path,loaded));
        assert(loaded.cartridgeCount==count);assert(loaded.eye.x==original.eye.x&&loaded.target.y==original.target.y);
        for(int i=0;i<4+count;i++)assert(loaded.nodes[i].position.z==original.nodes[i].position.z&&loaded.nodes[i].rotation.y==original.nodes[i].rotation.y);
    }
    // Missing middle cart cannot masquerade as a valid shorter profile.
    original.cartridgeCount=12;assert(writeSceneProfile(path,original));
    std::ifstream in(path);std::string text,line;while(std::getline(in,line))if(line.rfind("cart7 ",0)!=0)text+=line+'\n';in.close();
    {std::ofstream out(path);out<<text;}assert(!readSceneProfile(path,loaded));
    // Reject partial sets and duplicate records.
    for(int count:{9,10,11}){original.cartridgeCount=count;assert(writeSceneProfile(path,original));assert(!readSceneProfile(path,loaded));}
    original.cartridgeCount=12;assert(writeSceneProfile(path,original));{std::ofstream out(path,std::ios::app);out<<"cart11 0 0 0 0 0 0\n";}assert(!readSceneProfile(path,loaded));
    original.extended=true;original.tableAsset="tv-stand";original.tableScale={1.2f,.8f,1.4f};original.browseView=2;original.transitionSeconds=1.2f;
    original.cameras[1]={{0,220,1200},{0,220,0},35,true};original.displays[1].enabled=true;original.displays[1].fields=9;original.displays[1].textScale=.8f;
    assert(writeSceneProfile(path,original)&&readSceneProfile(path,loaded));
    assert(loaded.browseView==2&&loaded.tableAsset=="tv-stand"&&loaded.tableScale.z==1.4f&&loaded.transitionSeconds==1.2f);
    assert(loaded.cameras[1].authored&&loaded.cameras[1].eye.y==220&&loaded.displays[1].fields==9&&loaded.displays[1].enabled);
    for(const auto&bad:{"table_scale 0 1 1", "view_tv 0 0 0 0 0 0 40", "transition 0", "browse_view 4", "table_asset ../bad", "display_tv 2 0 1 12 255 0 0 0"}){
        original.extended=false;assert(writeSceneProfile(path,original));{std::ofstream out(path,std::ios::app);out<<bad<<'\n';}assert(!readSceneProfile(path,loaded));
    }
    ProfileCamera a={{0,100,1000},{0,100,0},40,true},b={{1000,300,0},{1000,300,-1000},60,true};
    auto first=blendCamera(a,b,0),mid=blendCamera(a,b,.5f),last=blendCamera(a,b,1);
    assert(first.eye.z==1000&&mid.eye.x==500&&mid.fov==50&&last.eye.x==1000&&last.fov==60);
    auto interrupted=blendCamera(mid,a,0);assert(interrupted.eye.x==mid.eye.x);
    a.eye={-161.50935f,715.5572f,1566.8765f};b.eye={314.1f,257.1000001f,891.3f};
    b.target={293.1f,127.2f,329.2000001f};b.fov=37.16253f;
    last=blendCamera(a,b,1);assert(last.eye.x==b.eye.x&&last.eye.y==b.eye.y&&last.eye.z==b.eye.z);
    assert(last.target.x==b.target.x&&last.target.y==b.target.y&&last.target.z==b.target.z&&last.fov==b.fov);
    std::remove(path.c_str());std::puts("native scene profile compatibility passed");
}
