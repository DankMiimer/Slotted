// Separate room positions and travel paths; never rewrites a console layout (MIT).
#pragma once
#include "SlotWorldLayout.h"
#include <array>
#include <map>
#include <vector>

namespace slot_scene {
inline bool worldTableModel(const std::string&name){return name=="table"||name=="wooden-table"||name=="tv-stand";}
// Optional room surfaces (SLOTWORLD2 `surface` records): a plain colour, or a texture
// (_slot/tabletop/surfaces/NAME.png) repeated every `tile` mm and multiplied by `color`.
// Unset floor/walls keep the original plain box; the ceiling is drawn only when set.
struct WorldSurface {bool set=false;Vec color={1,1,1};float tile=1000;std::string texture;};
enum WorldSurfaceKind {SurfaceFloor,SurfaceWall,SurfaceCeiling,SurfaceCount};
inline const char*worldSurfaceName(int kind){static const char*names[SurfaceCount]={"floor","wall","ceiling"};return names[kind];}
inline bool worldTextureName(const std::string&name){
    if(name.empty()||name.size()>48)return false;
    for(char c:name)if(!((c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='-'))return false;
    return name.front()!='-';
}
struct WorldPath {
    std::string from,to;
    float seconds=1.4f;
    Vec first={0,180,0},second={0,180,0}; // offsets from the straight path's 1/3 and 2/3 points
};
struct WorldProfile {
    std::map<std::string,Placement> tables={
        {"table",{{0,0,0},{0,0,0}}},
        {"wooden-table",{{4200,0,0},{0,90,0}}},
        {"tv-stand",{{-4200,0,0},{0,0,0}}},
    };
    std::vector<WorldPath> paths;
    float floor=0,left=-8000,right=8000,back=-6000,front=6000,height=3600;
    std::array<WorldSurface,SurfaceCount> surfaces;
    bool authored=false;
};
inline bool worldHasSurfaces(const WorldProfile&p){for(const auto&s:p.surfaces)if(s.set)return true;return false;}
inline bool validWorld(const WorldProfile&p){
    if(p.tables.empty()||p.tables.size()>3||p.paths.size()>6)return false;
    for(float x:{p.floor,p.left,p.right,p.back,p.front,p.height})if(!std::isfinite(x)||std::abs(x)>30000)return false;
    for(const auto&s:p.surfaces){
        if(!s.set)continue;
        for(float c:{s.color.x,s.color.y,s.color.z})if(!std::isfinite(c)||c<0||c>1)return false;
        if(!std::isfinite(s.tile)||s.tile<100||s.tile>20000||(!s.texture.empty()&&!worldTextureName(s.texture)))return false;
    }
    if(p.right-p.left<2000||p.front-p.back<2000||p.height<1500||p.height>10000)return false;
    for(const auto&entry:p.tables){
        const auto&at=entry.second;
        if(!worldTableModel(entry.first)||!validVector(at.position)||!validVector(at.rotation))return false;
        if(at.position.x<=p.left||at.position.x>=p.right||at.position.z<=p.back||at.position.z>=p.front)return false;
        // World furniture stands on the floor. Layout-local rotations remain intact
        // inside the common root, including all authored console/camera orientations.
        if(at.rotation.x!=0||at.rotation.z!=0)return false;
    }
    std::set<std::pair<std::string,std::string>> paths;
    for(const auto&path:p.paths){
        if(!p.tables.count(path.from)||!p.tables.count(path.to)||path.from==path.to||!paths.emplace(path.from,path.to).second)return false;
        if(!validVector(path.first)||!validVector(path.second)||!std::isfinite(path.seconds)||path.seconds<.2f||path.seconds>8)return false;
    }
    return true;
}
inline bool readWorldProfile(const std::string&path,WorldProfile&out){
    std::ifstream file(path);std::string record;WorldProfile p;p.tables.clear();p.authored=true;
    if(!(file>>record)||(record!="SLOTWORLD1"&&record!="SLOTWORLD2"))return false;
    const bool surfaces=record=="SLOTWORLD2";
    bool room=false;
    while(file>>record){
        if(record=="room"){
            if(room||!(file>>p.floor>>p.left>>p.right>>p.back>>p.front>>p.height))return false;
            room=true;
        }else if(record=="surface"&&surfaces){
            // surface floor|wall|ceiling R G B TILE TEXTURE|-
            std::string name,texture;WorldSurface s;s.set=true;
            if(!(file>>name>>s.color.x>>s.color.y>>s.color.z>>s.tile>>texture))return false;
            int kind=0;while(kind<SurfaceCount&&name!=worldSurfaceName(kind))kind++;
            if(kind==SurfaceCount||p.surfaces[kind].set)return false;
            s.texture=texture=="-"?std::string():texture;p.surfaces[kind]=s;
        }else if(record=="table"){
            std::string model;Placement at;
            if(!(file>>model>>at.position.x>>at.position.y>>at.position.z>>at.rotation.x>>at.rotation.y>>at.rotation.z)||!p.tables.emplace(model,at).second)return false;
        }else if(record=="path"){
            WorldPath v;
            if(!(file>>v.from>>v.to>>v.seconds>>v.first.x>>v.first.y>>v.first.z>>v.second.x>>v.second.y>>v.second.z))return false;
            p.paths.push_back(v);
        }else return false;
    }
    if(!room||!validWorld(p))return false;
    out=std::move(p);return true;
}
inline bool writeWorldProfile(const std::string&path,const WorldProfile&p){
    if(!validWorld(p))return false;
    std::ofstream file(path);file<<std::setprecision(9)<<(worldHasSurfaces(p)?"SLOTWORLD2":"SLOTWORLD1")<<"\nroom "<<p.floor<<' '<<p.left<<' '<<p.right<<' '<<p.back<<' '<<p.front<<' '<<p.height<<'\n';
    for(int kind=0;kind<SurfaceCount;kind++){const auto&s=p.surfaces[kind];if(s.set)file<<"surface "<<worldSurfaceName(kind)<<' '<<s.color.x<<' '<<s.color.y<<' '<<s.color.z<<' '<<s.tile<<' '<<(s.texture.empty()?std::string("-"):s.texture)<<'\n';}
    for(const auto&entry:p.tables){const auto&at=entry.second;file<<"table "<<entry.first<<' '<<at.position.x<<' '<<at.position.y<<' '<<at.position.z<<' '<<at.rotation.x<<' '<<at.rotation.y<<' '<<at.rotation.z<<'\n';}
    for(const auto&v:p.paths)file<<"path "<<v.from<<' '<<v.to<<' '<<v.seconds<<' '<<v.first.x<<' '<<v.first.y<<' '<<v.first.z<<' '<<v.second.x<<' '<<v.second.y<<' '<<v.second.z<<'\n';
    return bool(file);
}
inline WorldPath worldPath(const WorldProfile&p,const std::string&from,const std::string&to){
    for(const auto&path:p.paths)if(path.from==from&&path.to==to)return path;
    for(const auto&path:p.paths)if(path.from==to&&path.to==from){auto reverse=path;reverse.from=from;reverse.to=to;std::swap(reverse.first,reverse.second);return reverse;}
    WorldPath result;result.from=from;result.to=to;
    if(from==to){result.seconds=.5f;result.first=result.second={0,80,0};}
    return result;
}
inline Vec worldFlight(Vec from,Vec to,const WorldPath&path,float t){
    t=std::max(0.f,std::min(1.f,t));if(t==0)return from;if(t==1)return to;
    const auto delta=sub(to,from),a=add(add(from,mul(delta,1.f/3)),path.first),b=add(add(from,mul(delta,2.f/3)),path.second);
    const float u=1-t;return add(add(mul(from,u*u*u),mul(a,3*u*u*t)),add(mul(b,3*u*t*t),mul(to,t*t*t)));
}
}
