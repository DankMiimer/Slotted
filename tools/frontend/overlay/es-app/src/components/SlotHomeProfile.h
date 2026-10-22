// Slotted's home table (system selection): every console on one table with the TV (MIT).
// Its own file type, home-<tv>.scene, so binaries that only read SLOTLAYOUT1 never meet it.
// Millimetres and Euler degrees (Y-X-Z) exactly as the console rooms' SceneProfile.
#pragma once
#include "SlotSceneProfile.h"
#include <vector>

namespace slot_scene {
// Tabletop console models the home table may show (regional variants included).
static const char*const homeModels[]={"snes","snes-us","n64","nes","md","md-jp","psx","gb","gbc","gba","nds","psp","pico8"};
inline bool homeModel(const std::string&m){for(auto*k:homeModels)if(m==k)return true;return false;}
// The room a model belongs to (its saved layout's console).
inline std::string homeSystem(const std::string&model){return model=="snes-us"?"snes":model=="md-jp"?"md":model;}
struct HomeConsole {std::string model;Placement at;};
struct HomeProfile {
    int width=720,height=480;
    ProfileCamera overview,screen;      // screen: zoomed into the TV for 2D lists (derived when not authored)
    Placement table,tv,status;std::string tableAsset="table";Vec tableScale={1,1,1};
    float transitionSeconds=.8f;
    float follow=.2f;                   // how far the overview camera leans toward the highlighted console
    std::vector<HomeConsole> consoles;
};
constexpr int homeMaxConsoles=16;
inline bool readHomeProfile(const std::string&path,HomeProfile&out){
    std::ifstream f(path);std::string word;HomeProfile p;std::set<std::string> seen,models;
    if(!(f>>word)||word!="SLOTHOME1")return false;
    auto camera=[&](ProfileCamera&c){if(!(f>>c.eye.x>>c.eye.y>>c.eye.z>>c.target.x>>c.target.y>>c.target.z>>c.fov)||!validVector(c.eye)||!validVector(c.target)||!validCamera(c))return false;c.authored=true;return true;};
    auto placement=[&](Placement&n){return bool(f>>n.position.x>>n.position.y>>n.position.z>>n.rotation.x>>n.rotation.y>>n.rotation.z)&&validVector(n.position)&&validVector(n.rotation);};
    while(f>>word){
        if(word=="console"){
            HomeConsole c;if(!(f>>c.model)||!homeModel(c.model)||!placement(c.at))return false;
            if(!models.insert(homeSystem(c.model)).second||(int)p.consoles.size()>=homeMaxConsoles)return false; // one console per room
            p.consoles.push_back(c);continue;
        }
        if(!seen.insert(word).second)return false;
        if(word=="viewport"){if(!(f>>p.width>>p.height)||p.width<320||p.height<240||p.width>1920||p.height>1200)return false;}
        else if(word=="camera"){if(!camera(p.overview))return false;}
        else if(word=="view_screen"){if(!camera(p.screen))return false;}
        else if(word=="table"){if(!placement(p.table))return false;}
        else if(word=="tv"){if(!placement(p.tv))return false;}
        else if(word=="status"){if(!placement(p.status))return false;}
        else if(word=="table_asset"){if(!(f>>p.tableAsset)||(p.tableAsset!="table"&&p.tableAsset!="tv-stand"&&p.tableAsset!="wooden-table"))return false;}
        else if(word=="table_scale"){auto&v=p.tableScale;if(!(f>>v.x>>v.y>>v.z)||!validVector(v)||v.x<.1f||v.y<.1f||v.z<.1f||v.x>5||v.y>5||v.z>5)return false;}
        else if(word=="transition"){if(!(f>>p.transitionSeconds)||!std::isfinite(p.transitionSeconds)||p.transitionSeconds<.1f||p.transitionSeconds>5)return false;}
        else if(word=="follow"){if(!(f>>p.follow)||!std::isfinite(p.follow)||p.follow<0||p.follow>1)return false;}
        else return false;
    }
    for(const char*required:{"viewport","camera","table","tv","status"})if(!seen.count(required))return false;
    out=p;return true;
}
inline bool writeHomeProfile(const std::string&path,const HomeProfile&p){
    std::ofstream f(path);f<<std::setprecision(9);
    auto camera=[&](const char*name,const ProfileCamera&c){f<<name<<' '<<c.eye.x<<' '<<c.eye.y<<' '<<c.eye.z<<' '<<c.target.x<<' '<<c.target.y<<' '<<c.target.z<<' '<<c.fov<<'\n';};
    auto placement=[&](const std::string&name,const Placement&n){f<<name<<' '<<n.position.x<<' '<<n.position.y<<' '<<n.position.z<<' '<<n.rotation.x<<' '<<n.rotation.y<<' '<<n.rotation.z<<'\n';};
    f<<"SLOTHOME1\nviewport "<<p.width<<' '<<p.height<<'\n';camera("camera",p.overview);if(p.screen.authored)camera("view_screen",p.screen);
    placement("table",p.table);placement("tv",p.tv);placement("status",p.status);
    f<<"table_asset "<<p.tableAsset<<"\ntable_scale "<<p.tableScale.x<<' '<<p.tableScale.y<<' '<<p.tableScale.z<<"\ntransition "<<p.transitionSeconds<<"\nfollow "<<p.follow<<'\n';
    for(const auto&c:p.consoles)placement("console "+c.model,c.at);
    return bool(f);
}
// The home table shown with `tv`: its own authored layout, else one saved with another TV.
template<class Exists> inline std::string homeProfileFor(const std::string&folder,const std::string&tv,Exists exists){
    for(const auto&cabinet:{tv,std::string("panasonic"),std::string("pvm"),std::string("oldtv")}){
        const auto path=folder+"/home-"+cabinet+".scene";if(exists(path))return path;
    }
    return {};
}
// A starting arrangement when nothing is authored: the room default TV pose, consoles in two
// staggered rows on its left. It is only a fallback; an authored home table always wins.
inline HomeProfile defaultHomeProfile(const std::vector<std::string>&models){
    HomeProfile p;p.tv={{340,0,440},{0,-12,0}};p.status={{0,0,0},{0,0,0}};
    p.overview={{-120,900,1500},{-60,60,240},40,true};
    for(size_t i=0;i<models.size()&&(int)i<homeMaxConsoles;i++){
        const float column=float(i/2),row=float(i%2);
        p.consoles.push_back({models[i],{{-60-170*column+40*row,0,360-260*row},{0,14,0}}});
    }
    return p;
}
}
