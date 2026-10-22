// Real shared-context scene probe; host or ARM64 device, no game launch (MIT).
#include "SlotTabletop.h"
#define SDL_USE_BUILTIN_OPENGL_DEFINITIONS 1
#include <SDL_opengles2.h>
extern "C" SDL_Surface* IMG_Load(const char*);
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
int main(int argc,char**argv){
    if(argc<4){std::fprintf(stderr,"usage: probe MODELS PREPARED OUTPUT.bmp [MODEL TV [FACE...]]\n");return 2;}
    if(SDL_Init(SDL_INIT_VIDEO)){std::fprintf(stderr,"%s\n",SDL_GetError());return 1;}
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    int width=720,height=getenv("SLOT_SCENE_ASPECT")&&std::strcmp(getenv("SLOT_SCENE_ASPECT"),"4:3")==0?540:480;
    SDL_Window*w=SDL_CreateWindow("Slot tabletop probe",0,0,width,height,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);SDL_GLContext owner=w?SDL_GL_CreateContext(w):nullptr;
    if(!owner){std::fprintf(stderr,"%s\n",SDL_GetError());return 1;}
    std::printf("renderer=%s\n",glGetString(GL_RENDERER));
    const char*model=argc>4?argv[4]:"snes",*tv=argc>5?argv[5]:"panasonic";
    SlotTabletop*s=slot_tabletop_open(w,argv[1],argv[2],model,tv,false,"original",width,height);if(!s)return 1;
    const int count=getenv("SLOT_SCENE_CARTRIDGES")?std::atoi(getenv("SLOT_SCENE_CARTRIDGES")):8;
    if(count<1||count>12)return 1;
    // SLOT_SCENE_ITEM_MODEL renders other media (e.g. snes-us) beside the chosen console.
    const char*media=getenv("SLOT_SCENE_ITEM_MODEL")?getenv("SLOT_SCENE_ITEM_MODEL"):model;
    SlotTabletopItem items[12];char names[12][20];for(int i=0;i<count;i++){std::snprintf(names[i],sizeof(names[i]),"game-%d",i);items[i]={names[i],media,argc>6+i?argv[6+i]:""};}
    if(!slot_tabletop_items(s,items,count)){std::fprintf(stderr,"%s\n",slot_tabletop_error(s));return 1;}
    int battery=getenv("SLOT_SCENE_BATTERY")?std::atoi(getenv("SLOT_SCENE_BATTERY")):84;
    if(!slot_tabletop_status(s,battery,getenv("SLOT_SCENE_CHARGING")!=nullptr,getenv("SLOT_SCENE_OFFLINE")==nullptr,getenv("SLOT_SCENE_CLOCK")?getenv("SLOT_SCENE_CLOCK"):"21:48"))return 1;
    SlotTabletopFrame frame;frame.selected=getenv("SLOT_SCENE_SELECTED")?std::atoi(getenv("SLOT_SCENE_SELECTED")):3;if(getenv("SLOT_SCENE_YAW"))frame.yaw=std::atof(getenv("SLOT_SCENE_YAW"));if(getenv("SLOT_SCENE_PITCH"))frame.elevation=std::atof(getenv("SLOT_SCENE_PITCH"));
    if(getenv("SLOT_SCENE_RESIDENT")){int resident=std::atoi(getenv("SLOT_SCENE_RESIDENT"));if(resident<0||resident>=count||!slot_tabletop_resident(s,&items[resident],resident))return 1;}
    if(getenv("SLOT_SCENE_PHASE"))frame.phase=std::atoi(getenv("SLOT_SCENE_PHASE"));
    if(getenv("SLOT_SCENE_PROGRESS"))frame.progress=std::atof(getenv("SLOT_SCENE_PROGRESS"));
    if(getenv("SLOT_SCENE_POWER"))frame.power=std::atof(getenv("SLOT_SCENE_POWER"));
    if(getenv("SLOT_SCENE_ZOOM"))frame.zoom=std::atof(getenv("SLOT_SCENE_ZOOM"));
    if(getenv("SLOT_SCENE_LID"))frame.lid=std::atof(getenv("SLOT_SCENE_LID"));
    if(getenv("SLOT_SCENE_INSPECT"))frame.inspection=std::atof(getenv("SLOT_SCENE_INSPECT"));
    if(getenv("SLOT_SCENE_INSPECT_YAW"))frame.inspectYaw=std::atof(getenv("SLOT_SCENE_INSPECT_YAW"));
    if(getenv("SLOT_SCENE_INSPECT_PITCH"))frame.inspectPitch=std::atof(getenv("SLOT_SCENE_INSPECT_PITCH"));
    if(getenv("SLOT_SCENE_CAMERA"))frame.cameraView=std::atoi(getenv("SLOT_SCENE_CAMERA"));
    if(getenv("SLOT_SCENE_SCREEN")){
        SDL_Surface*raw=IMG_Load(getenv("SLOT_SCENE_SCREEN"));SDL_Surface*image=raw?SDL_ConvertSurfaceFormat(raw,SDL_PIXELFORMAT_RGBA32,0):nullptr;if(raw)SDL_FreeSurface(raw);
        if(!image){std::fprintf(stderr,"missing screen image\n");return 1;}
        glGenTextures(1,&frame.screen);glBindTexture(GL_TEXTURE_2D,frame.screen);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,image->w,image->h,0,GL_RGBA,GL_UNSIGNED_BYTE,image->pixels);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);SDL_FreeSurface(image);frame.screenTopDown=true;
        if(getenv("SLOT_SCENE_HANDHELD_SCREEN"))frame.handheldScreen=frame.screen;
    }
    std::vector<double>samples;GLuint result=0;int frames=getenv("SLOT_BENCH")?120:24;
    int destination=frame.cameraView;
    if(getenv("SLOT_SCENE_CAMERA_FROM"))frame.cameraView=std::atoi(getenv("SLOT_SCENE_CAMERA_FROM"));
    for(int i=-12;i<frames;i++){if(i==0)frame.cameraView=destination;Uint64 start=SDL_GetPerformanceCounter();frame.seconds=i*.016f;result=slot_tabletop_frame(s,frame);if(!result){std::fprintf(stderr,"%s\n",slot_tabletop_error(s));return 1;}if(i>=0)samples.push_back(1000.0*(SDL_GetPerformanceCounter()-start)/SDL_GetPerformanceFrequency());}
    std::sort(samples.begin(),samples.end());std::printf("scene_ms n=%zu p50=%.3f p95=%.3f max=%.3f unique_geometry_triangles=%d\n",samples.size(),samples[samples.size()/2],samples[samples.size()*95/100],samples.back(),slot_tabletop_triangles(s));
    float orbit[2];if(slot_tabletop_orbit_limits(s,orbit))std::printf("orbit_limits left=%.1f right=%.1f\n",orbit[0],orbit[1]);
    float flaps[4];int flapCount=slot_tabletop_flaps(s,flaps);for(int i=0;i<flapCount;i++)std::printf("flap%d_degrees=%.2f\n",i,flaps[i]);
    for(int i=-2;i<count;i++){float bounds[4]={};if(!slot_tabletop_bounds(s,i,bounds))return 1;if(bounds[0]<0||bounds[1]<0||bounds[0]+bounds[2]>width||bounds[1]+bounds[3]>height){std::fprintf(stderr,"Clipped item %d: %.2f %.2f %.2f %.2f\n",i,bounds[0],bounds[1],bounds[2],bounds[3]);if(!getenv("SLOT_SCENE_ALLOW_CLIP"))return 1;}}
    if(slot_tabletop_label_count(s)>13)return 1;
    float xy[8];slot_tabletop_display(s,xy);std::printf("display_quad");for(float v:xy)std::printf(" %.2f",v);std::printf("\n");
    float camera[7];if(slot_tabletop_camera(s,camera)){std::printf("camera");for(float v:camera)std::printf(" %.5f",v);std::printf("\n");}
    int draws[2];if(slot_tabletop_draws(s,draws))std::printf("near_mm=%.2f draws=%d culled=%d\n",slot_tabletop_near(s),draws[0],draws[1]);
    long cache[2];if(slot_tabletop_cache(s,cache))std::printf("scene_cache rendered=%ld reused=%ld\n",cache[0],cache[1]);
    int raster[3]={width*2,height*2,0};slot_tabletop_raster(s,raster);std::printf("raster=%dx%d msaa=%d\n",raster[0],raster[1],raster[2]);
    if(getenv("SLOT_SCENE_EXPORT")&&!slot_tabletop_export_layout(s,getenv("SLOT_SCENE_EXPORT")))return 1;
    GLuint fbo;glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,result,0);if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)return 1;
    SDL_Surface*image=SDL_CreateRGBSurfaceWithFormat(0,raster[0],raster[1],32,SDL_PIXELFORMAT_RGBA32);glReadPixels(0,0,raster[0],raster[1],GL_RGBA,GL_UNSIGNED_BYTE,image->pixels);
    unsigned foreground=0;for(int y=0;y<image->h;y++)for(int x=0;x<image->w;x++){auto*p=(unsigned char*)image->pixels+y*image->pitch+x*4;foreground+=p[0]+p[1]+p[2]>45;}std::printf("foreground_pixels=%u\n",foreground);
    if(foreground*14u<(unsigned)(raster[0]*raster[1])){std::fprintf(stderr,"Scene contains no substantial geometry\n");return 1;}
    std::vector<unsigned char>row(image->pitch);for(int y=0;y<image->h/2;y++){auto*a=(unsigned char*)image->pixels+y*image->pitch,*b=(unsigned char*)image->pixels+(image->h-1-y)*image->pitch;std::memcpy(row.data(),a,image->pitch);std::memcpy(a,b,image->pitch);std::memcpy(b,row.data(),image->pitch);}SDL_SaveBMP(image,argv[3]);SDL_FreeSurface(image);glBindFramebuffer(GL_FRAMEBUFFER,0);glDeleteFramebuffers(1,&fbo);
    GLenum error=glGetError();std::printf("GL error=%u; %s\n",error,slot_tabletop_error(s));slot_tabletop_close(s);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(w);SDL_Quit();return error?1:0;
}
