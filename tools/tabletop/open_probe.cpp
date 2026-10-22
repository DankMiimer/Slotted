// Opens one tabletop scene synchronously and exits: the startup/post-game open path,
// for crash and timing checks (MIT). Usage: open_probe MODELS PREPARED SYSTEM TV [bootstrap]
#include "SlotTabletop.h"
#define SDL_USE_BUILTIN_OPENGL_DEFINITIONS 1
#include <SDL_opengles2.h>
#include <cstdio>
#include <cstring>
static double now(){return 1000.0*SDL_GetPerformanceCounter()/SDL_GetPerformanceFrequency();}
// Lists the EGL/GL sync extensions of the current context (EGL resolved at run time).
static void syncExtensions(){
    using Display=void*(*)();using Query=const char*(*)(void*,int);
    auto display=(Display)SDL_GL_GetProcAddress("eglGetCurrentDisplay");auto query=(Query)SDL_GL_GetProcAddress("eglQueryString");
    const char*egl=display&&query?query(display(),0x3055/*EGL_EXTENSIONS*/):nullptr;const char*gl=(const char*)glGetString(GL_EXTENSIONS);
    for(const char*name:{"EGL_KHR_fence_sync","EGL_KHR_wait_sync","EGL_KHR_reusable_sync","EGL_ANDROID_native_fence_sync"})std::printf("%s %s\n",name,egl&&std::strstr(egl,name)?"yes":"no");
    for(const char*name:{"GL_OES_EGL_sync","GL_APPLE_sync","GL_EXT_disjoint_timer_query"})std::printf("%s %s\n",name,gl&&std::strstr(gl,name)?"yes":"no");
}
int main(int argc,char**argv){
    if(argc<5)return 2;
    if(SDL_Init(SDL_INIT_VIDEO))return 1;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    auto*window=SDL_CreateWindow("Slotted open probe",0,0,720,480,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);
    const auto owner=window?SDL_GL_CreateContext(window):nullptr;if(!owner)return 1;
    syncExtensions();
    const bool bootstrap=argc>5&&std::strcmp(argv[5],"bootstrap")==0;
    const double start=now();
    auto*scene=slot_tabletop_open(window,argv[1],argv[2],argv[3],argv[4],false,"original",720,480,bootstrap);
    if(!scene){std::fprintf(stderr,"open failed\n");return 4;}
    std::printf("open %s %s%s: %.0f ms\n",argv[3],argv[4],bootstrap?" bootstrap":"",now()-start);
    slot_tabletop_close(scene);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(window);SDL_Quit();return 0;
}
