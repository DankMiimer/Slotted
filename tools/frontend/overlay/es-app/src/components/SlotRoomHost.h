// One physical room outside the frontend's TV-sized GUI render target (MIT).
#pragma once
#include "SlotTabletop.h"
class Window;
namespace Renderer {
void slotPushTarget(int width,int height);
void slotPopTarget();
int slotOutputHeight();
}
namespace slot {
struct RenderTarget {
    RenderTarget(int width,int height){Renderer::slotPushTarget(width,height);}
    ~RenderTarget(){Renderer::slotPopTarget();}
    RenderTarget(const RenderTarget&)=delete;
};
void roomQueue(SlotTabletop* scene,const SlotTabletopFrame&frame,bool televisionUI=false,bool picture=false);
void roomForget(SlotTabletop* scene);
void roomMenuTheme();
// TV status values for per-frame rendering; never waits on the watcher thread.
struct RoomStatus {int battery;bool charging,connected;};
RoomStatus roomStatus();
// Called once from main() during startup, so one-time costs never land on a
// room interaction: the status subscription and, under Slotted, libVLC init.
void roomStartup();
// Called from FileData::launchGame as soon as the game process exits.
void roomGameEnded();
bool roomRenderWindow(Window* window);
bool roomSplash(Window* window,bool swap);
struct RoomExecution {
    bool active;
    RoomExecution();
    ~RoomExecution();
};
}
