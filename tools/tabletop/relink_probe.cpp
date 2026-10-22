// Opens the home table twice in one process, tearing the window and GL contexts down in between
// as a game launch does, so the second open reloads the cached program binaries. Prints both
// open times and whether the two settled frames are byte-identical (MIT).
// Usage: relink_probe MODELS PREPARED TV OUTPUT_DIR
#include "SlotTabletop.h"
#define SDL_USE_BUILTIN_OPENGL_DEFINITIONS 1
#include <SDL_opengles2.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <utility>
#include <vector>
static double now(){return 1000.0*SDL_GetPerformanceCounter()/SDL_GetPerformanceFrequency();}
static std::vector<unsigned char> capture(SlotTabletop*s,unsigned texture,const std::string&path){
    int size[3];slot_tabletop_raster(s,size);GLuint fbo;
    glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
    std::vector<unsigned char> pixels(size[0]*size[1]*4);glReadPixels(0,0,size[0],size[1],GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());
    glBindFramebuffer(GL_FRAMEBUFFER,0);glDeleteFramebuffers(1,&fbo);
    const size_t row=size[0]*4;
    for(int y=0;y<size[1]/2;y++)for(size_t x=0;x<row;x++)std::swap(pixels[y*row+x],pixels[(size[1]-1-y)*row+x]);
    SDL_Surface*image=SDL_CreateRGBSurfaceWithFormatFrom(pixels.data(),size[0],size[1],32,size[0]*4,SDL_PIXELFORMAT_RGBA32);
    if(!image||SDL_SaveBMP(image,path.c_str()))std::exit(3);SDL_FreeSurface(image);
    return pixels;
}
// One open/render/close round with its own window and owner context.
static std::vector<unsigned char> round(char**argv,const char*name){
    auto*window=SDL_CreateWindow("Slotted relink probe",0,0,720,480,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);
    const auto owner=window?SDL_GL_CreateContext(window):nullptr;if(!owner)std::exit(1);
    const double start=now();
    auto*scene=slot_tabletop_open(window,argv[1],argv[2],"home",argv[3],false,"original",720,480);
    if(!scene||!slot_tabletop_world(scene,nullptr)){std::fprintf(stderr,"open failed\n");std::exit(4);}
    const double opened=now()-start;
    slot_tabletop_reduced_motion(scene,true);
    std::vector<SlotTabletopItem> home;
    for(const char*system:{"snes","n64","nes","md","psx","gb","gbc","gba","nds","psp","pico8"})home.push_back({system,system,""});
    if(!slot_tabletop_items(scene,home.data(),int(home.size()))||!slot_tabletop_status(scene,80,false,true,"20:15"))std::exit(1);
    SlotTabletopFrame frame;frame.selected=-1;frame.cameraView=0;frame.automatic=false;frame.delta=1/60.f;
    unsigned texture=0;
    for(int i=0;i<30;i++){texture=slot_tabletop_frame(scene,frame);if(!texture){std::fprintf(stderr,"render failed: %s\n",slot_tabletop_error(scene));std::exit(4);}frame.seconds+=frame.delta;}
    auto pixels=capture(scene,texture,std::string(argv[4])+"/"+name+".bmp");
    std::printf("%s: open %.0f ms\n",name,opened);
    slot_tabletop_close(scene);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(window);
    return pixels;
}
int main(int argc,char**argv){
    if(argc<5)return 2;
    if(SDL_Init(SDL_INIT_VIDEO))return 1;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    const auto first=round(argv,"compiled"),second=round(argv,"reloaded");
    std::printf("identical %s (%zu bytes)\n",first==second?"yes":"NO",first.size());
    SDL_Quit();return first==second?0:5;
}
