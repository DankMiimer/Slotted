// Home table with full motion and one console selected, so its idle hover keeps moving:
// renders a fixed 1/60 s sequence and saves frames for byte comparison between
// SLOT_SCENE_PARTIAL=0 (whole re-render) and the default region re-render (MIT).
// Usage: hover_probe MODELS PREPARED OUTPUT_DIR
#include "SlotTabletop.h"
#define SDL_USE_BUILTIN_OPENGL_DEFINITIONS 1
#include <SDL_opengles2.h>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <utility>
#include <vector>
static double now(){return 1000.0*SDL_GetPerformanceCounter()/SDL_GetPerformanceFrequency();}
static void capture(SlotTabletop*s,unsigned texture,const std::string&path){
    int size[3];slot_tabletop_raster(s,size);GLuint fbo;
    glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
    std::vector<unsigned char> pixels(size[0]*size[1]*4);glReadPixels(0,0,size[0],size[1],GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());
    glBindFramebuffer(GL_FRAMEBUFFER,0);glDeleteFramebuffers(1,&fbo);
    const size_t row=size[0]*4;
    for(int y=0;y<size[1]/2;y++)for(size_t x=0;x<row;x++)std::swap(pixels[y*row+x],pixels[(size[1]-1-y)*row+x]);
    SDL_Surface*image=SDL_CreateRGBSurfaceWithFormatFrom(pixels.data(),size[0],size[1],32,size[0]*4,SDL_PIXELFORMAT_RGBA32);
    if(!image||SDL_SaveBMP(image,path.c_str()))std::exit(3);SDL_FreeSurface(image);
}
int main(int argc,char**argv){
    if(argc<4)return 2;
    if(SDL_Init(SDL_INIT_VIDEO))return 1;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    auto*window=SDL_CreateWindow("Slotted hover probe",0,0,720,480,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);
    const auto owner=window?SDL_GL_CreateContext(window):nullptr;if(!owner)return 1;
    const std::string out=argv[3];
    auto*scene=slot_tabletop_open(window,argv[1],argv[2],"home","panasonic",false,"original",720,480);
    if(!scene||!slot_tabletop_world(scene,nullptr))return 1;
    slot_tabletop_reduced_motion(scene,false);
    std::vector<SlotTabletopItem> home;
    for(const char*system:{"snes","n64","nes","md","psx","gb","gbc","gba","nds","psp","pico8"})home.push_back({system,system,""});
    if(!slot_tabletop_items(scene,home.data(),int(home.size()))||!slot_tabletop_status(scene,80,false,true,"20:15"))return 1;
    SlotTabletopFrame frame;frame.selected=-1;frame.cameraView=0;frame.automatic=false;frame.delta=1/60.f;
    double worst=0,total=0;int frames=0;
    for(int i=0;i<720;i++){
        if(i==60)frame.selected=4; // a console in the middle row: neighbours overlap its box
        const double start=now();const unsigned texture=slot_tabletop_frame(scene,frame);const double ms=now()-start;
        if(!texture){std::fprintf(stderr,"render failed: %s\n",slot_tabletop_error(scene));return 4;}
        if(i>=60){worst=std::max(worst,ms);total+=ms;frames++;}
        if(i%40==0)capture(scene,texture,out+"/hover-"+std::to_string(i)+".bmp");
        frame.seconds+=frame.delta;
    }
    long counts[2];slot_tabletop_cache(scene,counts);
    std::printf("hover: %d frames, mean %.2f ms, worst %.2f ms, rendered %ld, reused %ld\n",frames,total/frames,worst,counts[0],counts[1]);
    slot_tabletop_close(scene);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(window);SDL_Quit();return 0;
}
