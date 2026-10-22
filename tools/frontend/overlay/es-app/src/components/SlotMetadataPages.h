// Independently filtered TV/LCD metadata pages share one reversible navigation cycle (MIT).
#pragma once
#include "SlotSceneProfile.h"
#include <string>
inline bool slotMetadataPageVisible(const std::string&label,bool overview,const slot_scene::SceneDisplay&d){
    auto field=[&](int bit){return (d.fields&(1u<<bit))!=0;};
    const bool text=d.layout!=2,art=d.layout!=1;
    return overview||(label=="Game details"?text&&field(4):label=="Your library"?text&&field(7):label=="Video"?art&&field(6):art&&field(2));
}
inline int slotMetadataPageCycle(int tv,int handheld){
    tv=std::max(1,tv);handheld=std::max(1,handheld);int a=tv,b=handheld;
    while(b){int remainder=a%b;a=b;b=remainder;}return tv/a*handheld;
}
