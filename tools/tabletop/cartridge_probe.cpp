// Real renderer validation: twelve carts, both aspects, insertion/ejection and GPU timings (MIT).
// Does not launch games or write the theme/layouts. OUTPUT must be a private directory.
#include "SlotTabletop.h"
#define SDL_USE_BUILTIN_OPENGL_DEFINITIONS 1
#include <SDL_opengles2.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

static bool capture(SlotTabletop*s,GLuint texture,const std::string&path){
    int raster[3]={};if(!slot_tabletop_raster(s,raster))return false;
    GLuint fbo;glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)return false;
    SDL_Surface*p=SDL_CreateRGBSurfaceWithFormat(0,raster[0],raster[1],32,SDL_PIXELFORMAT_RGBA32);
    if(!p)return false;glReadPixels(0,0,raster[0],raster[1],GL_RGBA,GL_UNSIGNED_BYTE,p->pixels);
    std::vector<unsigned char>row(p->pitch);
    for(int y=0;y<p->h/2;y++){
        auto*a=(unsigned char*)p->pixels+y*p->pitch,*b=(unsigned char*)p->pixels+(p->h-1-y)*p->pitch;
        std::memcpy(row.data(),a,p->pitch);std::memcpy(a,b,p->pitch);std::memcpy(b,row.data(),p->pitch);
    }
    bool ok=SDL_SaveBMP(p,path.c_str())==0;SDL_FreeSurface(p);glBindFramebuffer(GL_FRAMEBUFFER,0);glDeleteFramebuffers(1,&fbo);
    return ok;
}

int main(int argc,char**argv){
    if(argc<7){std::fprintf(stderr,"usage: cartridge-probe MODELS PREPARED OUTPUT MODEL TV FACE [benchmark]\n");return 2;}
    if(SDL_Init(SDL_INIT_VIDEO))return 1;
    const int width=720,height=getenv("SLOT_SCENE_ASPECT")&&std::strcmp(getenv("SLOT_SCENE_ASPECT"),"4:3")==0?540:480;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    SDL_Window*w=SDL_CreateWindow("Cartridge validation",0,0,width,height,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);
    SDL_GLContext context=w?SDL_GL_CreateContext(w):nullptr;if(!context)return 1;
    std::printf("renderer=%s\n",glGetString(GL_RENDERER));
    SlotTabletop*s=slot_tabletop_open(w,argv[1],argv[2],argv[4],argv[5],false,"original",width,height);if(!s)return 1;
    SlotTabletopItem items[12];char names[12][20];std::string faces[12],faceArg=argv[6];
    for(int i=0;i<12;i++){std::snprintf(names[i],sizeof(names[i]),"fixture-%d",i);
        faces[i]=faceArg.back()=='/'?faceArg+std::to_string(i)+".png":faceArg;
        items[i]={names[i],argv[4],faces[i].c_str()};}
    if(!slot_tabletop_items(s,items,12)||!slot_tabletop_status(s,84,false,true,"12:34"))return 1;
    SlotTabletopFrame f;f.selected=0;f.cameraView=0;f.automatic=false;f.delta=.1f;
    float seconds=0;GLuint texture=0;
    auto render=[&](int count){for(int i=0;i<count;i++){f.seconds=seconds;seconds+=f.delta;texture=slot_tabletop_frame(s,f);if(!texture)return false;}glFinish();return true;};
    auto shot=[&](const char*name){
        if(!render(12)||!capture(s,texture,std::string(argv[3])+"/"+name+".bmp"))return false;
        float bounds[4],display[8];slot_tabletop_display(s,display);
        std::printf("shot=%s near_mm=%.3f tv=",name,slot_tabletop_near(s));slot_tabletop_bounds(s,-2,bounds);for(float v:bounds)std::printf("%.3f,",v);
        std::printf(" status=");slot_tabletop_bounds(s,-1,bounds);for(float v:bounds)std::printf("%.3f,",v);
        std::printf(" screen=");for(float v:display)std::printf("%.3f,",v);std::printf("\n");std::fflush(stdout);
        return glGetError()==GL_NO_ERROR;
    };
    bool timingOnly=argc>7&&std::string(argv[7])=="timing";
    if(!timingOnly){
    if(!shot("overview"))return 1;
    f.cameraView=4;f.inspection=1;if(!shot("front"))return 1;
    f.inspectYaw=180;if(!shot("rear"))return 1;
    f.inspectYaw=25;f.inspectPitch=-20;if(!shot("quarter"))return 1;
    f.inspection=0;f.inspectYaw=0;f.inspectPitch=0;f.cameraView=3;
    if(!slot_tabletop_resident(s,&items[0],0))return 1;
    f.phase=1;
    for(float p:{0.f,.55f,.7f,.8f,.9f,1.f}){
        f.progress=p;char name[40];std::snprintf(name,sizeof(name),"insert-%03d",(int)(p*100+.5f));if(!shot(name))return 1;
    }
    f.phase=2;
    for(float p:{0.f,.2f,.3f,.45f,1.f}){
        f.progress=p;char name[40];std::snprintf(name,sizeof(name),"eject-%03d",(int)(p*100+.5f));if(!shot(name))return 1;
    }
    }
    if(argc>7&&(std::string(argv[7])=="benchmark"||timingOnly)){
        if(timingOnly&&!slot_tabletop_resident(s,&items[0],0))return 1;
        f.cameraView=0;f.phase=1;f.delta=.016f;
        std::vector<double>timing;
        for(int i=-20;i<180;i++){
            f.progress=.7f+.3f*(i+20)/200.f;f.seconds=seconds;seconds+=f.delta;
            Uint64 start=SDL_GetPerformanceCounter();texture=slot_tabletop_frame(s,f);if(!texture)return 1;
            // Include actual GPU completion; submitting cached/static frames is not a frame-rate benchmark.
            glFinish();double ms=1000.0*(SDL_GetPerformanceCounter()-start)/SDL_GetPerformanceFrequency();
            if(i>=0)timing.push_back(ms);
        }
        std::sort(timing.begin(),timing.end());long cache[2];slot_tabletop_cache(s,cache);
        std::printf("gpu_scene_ms n=%zu p50=%.4f p95=%.4f max=%.4f cache_rendered=%ld reused=%ld\n",timing.size(),timing[timing.size()/2],timing[timing.size()*95/100],timing.back(),cache[0],cache[1]);
    }
    int raster[3];slot_tabletop_raster(s,raster);GLenum error=glGetError();std::printf("raster=%dx%d msaa=%d triangles=%d labels=%d GL_error=%u\n",raster[0],raster[1],raster[2],slot_tabletop_triangles(s),slot_tabletop_label_count(s),error);
    slot_tabletop_close(s);SDL_GL_DeleteContext(context);SDL_DestroyWindow(w);SDL_Quit();return error?1:0;
}
