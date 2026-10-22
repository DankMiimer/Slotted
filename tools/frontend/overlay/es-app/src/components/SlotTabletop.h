// Real shared-depth tabletop renderer. Separate from the accepted legacy scene (MIT).
#pragma once
#include <SDL.h>
#include "SlotSceneProfile.h"
struct SlotTabletop;
struct SlotTabletopItem {const char* id;const char* model;const char* face;};
struct SlotTabletopFrame {
    float seconds=0,delta=.016f,yaw=0,elevation=0,zoom=0,inspection=0,inspectYaw=0,inspectPitch=0;
    int selected=0,loaded=-1,moving=-1,phase=0; // phase: 0 browse, 1 insert, 2 eject
    float progress=0,power=0;
    float lid=-1; // optical lid opening 0..1 set by the presentation (prelaunch close); -1 automatic
    unsigned screen=0;float screenU=1,screenV=1;bool screenTopDown=false;
    float screenLeft=0; // TV picture: texture u where it starts (a 4:3 picture inside a wider target)
    unsigned handheldScreen=0;
    int cameraView=-1; // -1 profile default, 0 overview, 1 TV, 2 cartridge, 3 console, 4 inspection,
                       // 5 the whole TV front plus top status UI (Slotted lists and menus)
    // No camera picked by hand (Select+R3): a seated selected game pans to the overview. Launches
    // (lid >= 0, power or zoom) always pan to the console (handheld screen) or TV, then zoom in.
    bool automatic=true;
    float pageMs=0,videoBindMs=0; // the frontend's metadata-page drawing / video frame fetch, SLOT_SCENE_FRAMELOG only
    float pageSteps[5]={0,0,0,0,0}; // this frame's page redraws: both, TV page, LCD page, TV video, LCD video (log only)
};
// model "home" opens Slotted's home table (every console with the TV); items then list the
// systems that have games, model = their console. slot_tabletop_request accepts "home" too.
SlotTabletop* slot_tabletop_open(SDL_Window* window,const char* models,const char* prepared,
                                const char* model,const char* tv,bool cel=false,const char* paint="original",
                                int logicalWidth=720,int logicalHeight=480,bool bootstrapHome=false);
bool slot_tabletop_items(SlotTabletop*,const SlotTabletopItem*,int count);
// Opt in before starting the stream. nullptr uses starter positions; a supplied
// SLOTWORLD1 file must be valid. Legacy tabletop rendering remains unchanged.
bool slot_tabletop_world(SlotTabletop*,const char* worldProfile=nullptr);
// Calmer object motion: no idle sway, rocking or landing bounce. Authored
// cameras, room paths, insert/launch ownership and fixed furniture stay exact.
void slot_tabletop_reduced_motion(SlotTabletop*,bool enabled);
// Optional fixed CRT scanlines/vignette on live glass only; model materials stay intact.
void slot_tabletop_crt(SlotTabletop*,bool enabled);
// Last drawn fixed table model matrix; counts {table instances, tables in view}.
bool slot_tabletop_world_table(SlotTabletop*,const char* model,float matrix[16]);
bool slot_tabletop_world_transform(SlotTabletop*,float matrix[16]);
bool slot_tabletop_world_stats(SlotTabletop*,int counts[2]);
// Independent resident media retains its table home when the visible window moves.
// phase 1/2 animates this one node; phase 0 seats it. nullptr clears it.
bool slot_tabletop_resident(SlotTabletop*,const SlotTabletopItem*,int homeIndex);
// Rebuilds geometry only when values change. Clock is the frontend's formatted HH:MM.
bool slot_tabletop_status(SlotTabletop*,int battery,bool charging,bool connected,const char* clock);
unsigned slot_tabletop_frame(SlotTabletop*,const SlotTabletopFrame&);
void slot_tabletop_close(SlotTabletop*);
const char* slot_tabletop_error(SlotTabletop*);
// World-space display corners projected into the logical viewport, independent of raster resolution.
bool slot_tabletop_display(SlotTabletop*,float xy[8]);
// After frame: projected x/y/width/height for item 0..11, status -1, or TV front -2.
bool slot_tabletop_bounds(SlotTabletop*,int item,float xywh[4]);
// Stable spatial-selection anchors, independent of hover, insertion and camera
// pan progress. item is the current window index, or -2 for the selectable TV.
// Uses an authored reference view (0 overview by default), not the animated pose.
// Main thread, no GL work; writes at most capacity, returns 0 while not ready.
struct SlotTabletopFocus {int item;float x,y;};
int slot_tabletop_focus_points(SlotTabletop*,SlotTabletopFocus*,int capacity,int referenceView=0,bool emptySlots=false);
bool slot_tabletop_appearance(SlotTabletop*,bool cel,const char* paint);
const char* slot_tabletop_television(SlotTabletop*);
// Last frame's dust-flap angles in degrees (N64); returns how many the console has.
int slot_tabletop_flaps(SlotTabletop*,float degrees[4]);
// Permitted browse orbit in degrees {left, right} of an authored camera, after its first frame.
bool slot_tabletop_orbit_limits(SlotTabletop*,float limits[2]);
// Last frame's near plane in mm (fitted to the closest geometry in view, 10..150), and the
// number of draws issued {drawn, skipped outside the view}.
float slot_tabletop_near(SlotTabletop*);
// Frames so far that {rendered the 3D scene, reused the cached scene} (only screens redrawn).
bool slot_tabletop_cache(SlotTabletop*,long counts[2]);
// Last frame's milliseconds: waiting for the owner's GPU work, this renderer's CPU work,
// waiting for this renderer's GPU work (the two glFinish synchronisation points).
bool slot_tabletop_frame_timing(SlotTabletop*,float ms[3]);
// Before a game closes the table: remember its current table and TV. After the game exits:
// start decoding their textures on worker threads (main thread), so the first room frame's
// synchronous reopen overlaps the frontend's own re-initialisation. Pixels are unchanged.
void slot_tabletop_remember_assets(SlotTabletop*);
void slot_tabletop_predecode_remembered();
// Scene texture size {width, height} and MSAA samples (0: 2x supersampled raster).
bool slot_tabletop_raster(SlotTabletop*,int size[3]);
bool slot_tabletop_draws(SlotTabletop*,int counts[2]);
int slot_tabletop_label_count(SlotTabletop*);
int slot_tabletop_triangles(SlotTabletop*);
bool slot_tabletop_export_layout(SlotTabletop*,const char* path);
const slot_scene::SceneDisplay* slot_tabletop_display_settings(SlotTabletop*,int display);
int slot_tabletop_default_view(SlotTabletop*);
// The authored camera pan time in seconds (the launch waits for its pan to finish).
float slot_tabletop_pan_seconds(SlotTabletop*);
bool slot_tabletop_camera(SlotTabletop*,float values[7]);
// One persistent session, bounded shared room/core cache, and a single shared
// upload context. Requests copy all strings; only the latest generation commits.
bool slot_tabletop_stream_start(SlotTabletop*);
bool slot_tabletop_request(SlotTabletop*,const char* system,const char* tv,const char* gbaChoice,
                          const SlotTabletopItem*,int count);
void slot_tabletop_prefetch(SlotTabletop*,const char* system,const char* tv,const char* gbaChoice);
bool slot_tabletop_ready(SlotTabletop*);
bool slot_tabletop_stream_failed(SlotTabletop*);
// Generation/resource telemetry for native/frontend validation: wanted and active
// generation, loads, tracked GPU bytes, choreography phase, completed GPU uploads.
bool slot_tabletop_stream_stats(SlotTabletop*,unsigned long long values[6]);
