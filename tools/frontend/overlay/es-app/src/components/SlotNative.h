// Embed the approved renderer without a second window, input loop or present.
#pragma once
#ifdef __cplusplus
extern "C" {
#endif
struct SDL_Window;
typedef struct SlotNative SlotNative;
SlotNative* slot_native_open(struct SDL_Window*,const char* assets,const char* rom,
                             const char* model,const char* face,const char* style,const char* colour);
unsigned slot_native_frame(SlotNative*,float progress,int inserting);
unsigned slot_native_present(SlotNative*,float progress);
void slot_native_optical_close(SlotNative*,float closed);
unsigned slot_native_browse(SlotNative*);
int slot_native_bounds(SlotNative*,float bounds[4]);
float slot_native_origin(SlotNative*);
void slot_native_project(SlotNative*,const float point[3],int lid,float result[2]);
int slot_native_lcd(SlotNative*,int screen,int corner,float result[2]);
// Home consoles: projected floor centre and footprint extent (native raster pixels); 0 if unavailable.
int slot_native_ground(SlotNative*,float centre[2],float extent[2]);
// Visible front base edge, including any housing overhang ahead of the feet.
int slot_native_contact(SlotNative*,float front[2]);
void slot_native_raster_size(int *width,int *height);
void slot_native_close(SlotNative*);
float slot_native_duration(const char* model,int inserting);
// Decode a textured model's albedo on a worker thread before its first scene.
// 1 ready, 0 pending (call again later), -1 untextured. Never blocks.
int slot_native_prefetch(const char* assets,const char* model);
#ifdef __cplusplus
}
#endif
