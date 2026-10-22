#pragma once
#include <cstdlib>
#include <cstring>

// Process-only editor preview. Never put the test system/TV in Settings.
namespace slot {
inline const char* scenePreviewValue(const char* name, const char* const* values) {
    const char* value = std::getenv(name);
    if(value)for(;*values;++values)if(std::strcmp(value,*values)==0)return value;
    return nullptr;
}
inline const char* scenePreviewSystem() {
    static const char* const values[]={"snes","n64","nes","megadrive","psx","gb","gbc","gba","nds","psp","pico8",nullptr};
    return scenePreviewValue("SLOT_SCENE_PREVIEW_SYSTEM",values);
}
inline const char* scenePreviewTV() {
    static const char* const values[]={"panasonic","pvm","oldtv",nullptr};
    return scenePreviewValue("SLOT_SCENE_PREVIEW_TV",values);
}
inline bool scenePreviewActive(){return scenePreviewSystem() && scenePreviewTV();}
}
