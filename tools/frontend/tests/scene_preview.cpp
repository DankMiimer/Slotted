#include "SlotScenePreview.h"
#include <cassert>
#include <cstdlib>
#include <cstring>

int main(){
    unsetenv("SLOT_SCENE_PREVIEW_SYSTEM");unsetenv("SLOT_SCENE_PREVIEW_TV");
    assert(!slot::scenePreviewActive());
    setenv("SLOT_SCENE_PREVIEW_SYSTEM","gba",1);
    assert(!slot::scenePreviewActive());
    setenv("SLOT_SCENE_PREVIEW_TV","pvm",1);
    assert(slot::scenePreviewActive());
    assert(std::strcmp(slot::scenePreviewSystem(),"gba")==0);
    setenv("SLOT_SCENE_PREVIEW_TV","../../other",1);
    assert(!slot::scenePreviewActive());
    setenv("SLOT_SCENE_PREVIEW_TV","oldtv",1);
    setenv("SLOT_SCENE_PREVIEW_SYSTEM","gba; launch",1);
    assert(!slot::scenePreviewActive());
    setenv("SLOT_SCENE_PREVIEW_SYSTEM","megadrive",1);
    assert(slot::scenePreviewActive());
    unsetenv("SLOT_SCENE_PREVIEW_SYSTEM");unsetenv("SLOT_SCENE_PREVIEW_TV");
    assert(!slot::scenePreviewActive());
}
