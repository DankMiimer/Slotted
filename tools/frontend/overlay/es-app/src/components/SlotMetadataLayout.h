// Metadata spacing for the measured glass area. Original processing, MIT.
#pragma once
#include <algorithm>
struct SlotMetadataLayout {
    float type,margin,top,hudGap,hudHeight,ruleGap,bodyGap,footerReserve,footerOffset,footerHeight;
    bool shortGlass;
    float bodyTop(float header,bool ds) const {return ds?34:header+bodyGap;}
    float bodyHeight(float height,float header,bool ds) const {
        return std::max(shortGlass?0.f:24.f,height-bodyTop(header,ds)-footerReserve);
    }
};
inline SlotMetadataLayout slotMetadataLayout(float width,float height,bool handheld) {
    if(!handheld&&height<125)return {.70f,8,4,5,15,21,24,19,17,15,true};
    return {!handheld&&width<200?.84f:1.f,12,6,7,22,31,34,28,23,21,false};
}
