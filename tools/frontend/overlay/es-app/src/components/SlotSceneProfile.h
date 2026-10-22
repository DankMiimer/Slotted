// Shared authoring format: millimetres, Euler degrees in Y-X-Z order (MIT).
#pragma once
#include "SlotSceneMath.h"
#include <array>
#include <fstream>
#include <iomanip>
#include <set>
#include <sstream>
#include <string>
namespace slot_scene {
struct Placement {Vec position={0,0,0},rotation={0,0,0};Mat matrix(float size=1)const{return product(product(translate(position),rotate(radians(rotation.x),radians(rotation.y),radians(rotation.z))),scale(size,size,size));}};
constexpr int sceneMaxCartridges=12,sceneMaxNodes=4+sceneMaxCartridges;
static const char*const sceneNodeNames[]={"table","tv","console","status","cart0","cart1","cart2","cart3","cart4","cart5","cart6","cart7","cart8","cart9","cart10","cart11"};
struct ProfileCamera {Vec eye={0,650,1000},target={0,120,0};float fov=40;bool authored=false;};
// Metadata bits: title, HUD, artwork, description, facts, page footer, video, library.
struct SceneDisplay {bool enabled=true;int layout=0;float textScale=1,padding=12;unsigned fields=255,background=0x0e191b,foreground=0xe8e9e7,accent=0x42665a;};
struct SceneProfile {
    std::array<Placement,sceneMaxNodes> nodes;Vec eye={0,650,1000},target={0,120,0};float fov=40;
    int width=720,height=480,cartridgeCount=sceneMaxCartridges;
    std::array<ProfileCamera,5> cameras;float transitionSeconds=.8f;int browseView=0;std::string tableAsset="table";Vec tableScale={1,1,1};
    SceneDisplay displays[2];bool extended=false;
    SceneProfile(){displays[1].enabled=false;}
};
struct SceneProfileChoice {std::string path,system,tv;};
// A console's authored composition takes precedence over another console's
// fallback, even when it was saved with a different television. Never rewrite
// the saved profile or its cameras when changing the displayed TV.
template<class Exists> inline SceneProfileChoice sceneProfileFor(const std::string&folder,const std::string&system,const std::string&tv,Exists exists){
    for(const auto&console:{system,std::string("snes")})
        for(const auto&cabinet:{tv,std::string("panasonic"),std::string("pvm"),std::string("oldtv")}){
            const auto path=folder+"/"+console+"-"+cabinet+".scene";
            if(exists(path))return {path,console,cabinet};
        }
    return {};
}
inline SceneProfileChoice sceneProfileFor(const std::string&folder,const std::string&system,const std::string&tv){
    return sceneProfileFor(folder,system,tv,[](const std::string&path){return bool(std::ifstream(path));});
}
static const char*const sceneViewNames[]={"all","tv","cartridge","console","inspect"};
inline bool validCamera(const ProfileCamera&c){return std::isfinite(c.fov)&&c.fov>=5&&c.fov<=110&&dot(sub(c.eye,c.target),sub(c.eye,c.target))>=100;}
inline bool validVector(Vec v){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z)&&std::abs(v.x)<=10000&&std::abs(v.y)<=10000&&std::abs(v.z)<=10000;}
inline bool readSceneProfile(const std::string&path,SceneProfile&out){
    std::ifstream f(path);std::string word;SceneProfile p;std::set<std::string>seen;
    if(!(f>>word)||word!="SLOTLAYOUT1")return false;
    while(f>>word){
        if(!seen.insert(word).second)return false;
        if(word=="viewport"){if(!(f>>p.width>>p.height)||p.width<320||p.height<240||p.width>1920||p.height>1200)return false;}
        else if(word=="camera"){if(!(f>>p.eye.x>>p.eye.y>>p.eye.z>>p.target.x>>p.target.y>>p.target.z>>p.fov)||!validVector(p.eye)||!validVector(p.target)||!std::isfinite(p.fov)||p.fov<5||p.fov>110||dot(sub(p.eye,p.target),sub(p.eye,p.target))<100)return false;}
        else if(word.rfind("view_",0)==0){int index=-1;for(int i=1;i<5;i++)if(word==std::string("view_")+sceneViewNames[i])index=i;if(index<0)return false;auto&c=p.cameras[index];if(!(f>>c.eye.x>>c.eye.y>>c.eye.z>>c.target.x>>c.target.y>>c.target.z>>c.fov)||!validVector(c.eye)||!validVector(c.target)||!validCamera(c))return false;c.authored=true;p.extended=true;}
        else if(word=="transition"){if(!(f>>p.transitionSeconds)||!std::isfinite(p.transitionSeconds)||p.transitionSeconds<.1f||p.transitionSeconds>5)return false;p.extended=true;}
        else if(word=="browse_view"){if(!(f>>p.browseView)||p.browseView<0||p.browseView>3)return false;p.extended=true;}
        else if(word=="table_asset"){if(!(f>>p.tableAsset)||(p.tableAsset!="table"&&p.tableAsset!="tv-stand"&&p.tableAsset!="wooden-table"))return false;p.extended=true;}
        else if(word=="table_scale"){auto&v=p.tableScale;if(!(f>>v.x>>v.y>>v.z)||!validVector(v)||v.x<.1f||v.y<.1f||v.z<.1f||v.x>5||v.y>5||v.z>5)return false;p.extended=true;}
        else if(word=="display_tv"||word=="display_handheld"){auto&d=p.displays[word=="display_handheld"];int enabled;if(!(f>>enabled>>d.layout>>d.textScale>>d.padding>>d.fields>>d.background>>d.foreground>>d.accent)||enabled<0||enabled>1||d.layout<0||d.layout>2||!std::isfinite(d.textScale)||d.textScale<.5f||d.textScale>2||!std::isfinite(d.padding)||d.padding<0||d.padding>40||d.fields>255||d.background>0xffffff||d.foreground>0xffffff||d.accent>0xffffff)return false;d.enabled=enabled;p.extended=true;}
        else {int index=-1;for(int i=0;i<sceneMaxNodes;i++)if(word==sceneNodeNames[i])index=i;if(index<0)return false;auto&n=p.nodes[index];if(!(f>>n.position.x>>n.position.y>>n.position.z>>n.rotation.x>>n.rotation.y>>n.rotation.z)||!validVector(n.position)||!validVector(n.rotation))return false;}
    }
    if(!seen.count("camera")||!seen.count("viewport"))return false;
    int nodes=0;for(int i=0;i<sceneMaxNodes;i++)nodes+=seen.count(sceneNodeNames[i]);
    if(nodes!=12&&nodes!=16)return false;p.cartridgeCount=nodes==12?8:sceneMaxCartridges;
    for(int i=0;i<4+p.cartridgeCount;i++)if(!seen.count(sceneNodeNames[i]))return false;
    p.cameras[0]={p.eye,p.target,p.fov,true};out=p;return true;
}
inline bool writeSceneProfile(const std::string&path,const SceneProfile&p){
    std::ofstream f(path);f<<std::setprecision(9)<<"SLOTLAYOUT1\nviewport "<<p.width<<' '<<p.height<<"\ncamera "<<p.eye.x<<' '<<p.eye.y<<' '<<p.eye.z<<' '<<p.target.x<<' '<<p.target.y<<' '<<p.target.z<<' '<<p.fov<<'\n';
    for(int i=0;i<4+p.cartridgeCount;i++){auto&n=p.nodes[i];f<<sceneNodeNames[i]<<' '<<n.position.x<<' '<<n.position.y<<' '<<n.position.z<<' '<<n.rotation.x<<' '<<n.rotation.y<<' '<<n.rotation.z<<'\n';}
    if(p.extended){
        for(int i=1;i<5;i++)if(p.cameras[i].authored){auto&c=p.cameras[i];f<<"view_"<<sceneViewNames[i]<<' '<<c.eye.x<<' '<<c.eye.y<<' '<<c.eye.z<<' '<<c.target.x<<' '<<c.target.y<<' '<<c.target.z<<' '<<c.fov<<'\n';}
        f<<"transition "<<p.transitionSeconds<<"\nbrowse_view "<<p.browseView<<"\ntable_asset "<<p.tableAsset<<"\ntable_scale "<<p.tableScale.x<<' '<<p.tableScale.y<<' '<<p.tableScale.z<<'\n';
        for(int i=0;i<2;i++){auto&d=p.displays[i];f<<(i?"display_handheld ":"display_tv ")<<d.enabled<<' '<<d.layout<<' '<<d.textScale<<' '<<d.padding<<' '<<d.fields<<' '<<d.background<<' '<<d.foreground<<' '<<d.accent<<'\n';}
    }return bool(f);
}
}
