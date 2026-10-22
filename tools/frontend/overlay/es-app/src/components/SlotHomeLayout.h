// Home-console scene placement in logical 720 x 480 pixels (MIT).
#pragma once
#include <algorithm>
#include <cstring>

// Native geometry units per mm: authored enclosure anchors, or the procedural
// console's existing physical-media scale (NES/MD/PICO-8). PICO-8 is fictional.
inline float slotHomeUnitsPerMM(const char* model) {
    if(!std::strcmp(model,"snes"))return 1.6f;
    if(!std::strcmp(model,"snes-us"))return 1.55f;
    if(!std::strcmp(model,"n64"))return 1.5f;
    if(!std::strcmp(model,"psx"))return 1.6f;
    if(!std::strcmp(model,"dreamcast"))return 1.3f;
    if(!std::strcmp(model,"nes"))return 1.63333333f;
    if(!std::strcmp(model,"md")||!std::strcmp(model,"md-jp"))return 2.05504587f;
    if(!std::strcmp(model,"pico8"))return 2.2f;
    return 1.f;
}

struct SlotHomeLayout {float scale,rect[4],tv[2],frontY;};
inline SlotHomeLayout slotHomeLayout(const char* model,const float bounds[4],const float contact[2],
                                     const float display[2],const float tvContact[2],float tvUnitsPerMM) {
    SlotHomeLayout out={};
    out.scale=tvUnitsPerMM/slotHomeUnitsPerMM(model);
    // Fixed cabinet size retains readable metadata. If an unusually large console must fit,
    // constrain it at the scene edges while preserving its complete open-lid silhouette.
    out.frontY=std::min(478.f-(display[1]-tvContact[1]),124.f+tvContact[1]);
    const float above=std::max(1.f,contact[1]-bounds[1]);
    const float below=std::max(1.f,bounds[1]+bounds[3]-contact[1]);
    out.scale=std::min(out.scale,std::min(326.f/bounds[2],std::min((out.frontY-124)/above,(478-out.frontY)/below)));
    out.tv[0]=716-display[0];out.tv[1]=out.frontY-tvContact[1];
    // Centre the console in the free area, with a visible gap to the cabinet.
    const float centreX=(12+out.tv[0]-16)/2;
    out.rect[0]=centreX-(bounds[0]+bounds[2]/2)*out.scale;
    out.rect[1]=out.frontY-contact[1]*out.scale;
    out.rect[2]=720*out.scale;out.rect[3]=480*out.scale;
    return out;
}
