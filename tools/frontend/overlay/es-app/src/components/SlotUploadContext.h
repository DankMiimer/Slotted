// A persistent shared EGL context with its own pbuffer. No SDL window surface
// is ever made current on two threads (MIT). The caller joins before destruction.
#pragma once
#include <SDL.h>
struct SlotUploadContext {
    void*library=nullptr,*display=nullptr,*context=nullptr,*surface=nullptr;
    unsigned (*makeCurrent)(void*,void*,void*,void*)=nullptr;
    unsigned (*destroyContext)(void*,void*)=nullptr;
    unsigned (*destroySurface)(void*,void*)=nullptr;
    bool create(){
        library=SDL_LoadObject("libEGL.so.1");if(!library)library=SDL_LoadObject("libmali.so");if(!library)return false;
        auto at=[&](const char*n){return SDL_LoadFunction(library,n);};
        auto getDisplay=(void*(*)())at("eglGetCurrentDisplay"),getContext=(void*(*)())at("eglGetCurrentContext");
        auto query=(unsigned(*)(void*,void*,int,int*))at("eglQueryContext");
        auto choose=(unsigned(*)(void*,const int*,void**,int,int*))at("eglChooseConfig");
        auto createSurface=(void*(*)(void*,void*,const int*))at("eglCreatePbufferSurface");
        auto createContext=(void*(*)(void*,void*,void*,const int*))at("eglCreateContext");
        makeCurrent=(unsigned(*)(void*,void*,void*,void*))at("eglMakeCurrent");
        destroyContext=(unsigned(*)(void*,void*))at("eglDestroyContext");destroySurface=(unsigned(*)(void*,void*))at("eglDestroySurface");
        if(!getDisplay||!getContext||!query||!choose||!createSurface||!createContext||!makeCurrent||!destroyContext||!destroySurface)return false;
        display=getDisplay();void*share=getContext(),*config=nullptr;int id=0,count=0;
        if(!display||!share||!query(display,share,0x3028,&id))return false;
        const int attributes[]={0x3028,id,0x3038},size[]={0x3057,1,0x3056,1,0x3038},version[]={0x3098,2,0x3038};
        if(!choose(display,attributes,&config,1,&count)||count!=1)return false;
        surface=createSurface(display,config,size);if(surface)context=createContext(display,config,share,version);return surface&&context;
    }
    bool bind(){return context&&makeCurrent(display,surface,surface,context);}
    void unbind(){if(makeCurrent&&display)makeCurrent(display,nullptr,nullptr,nullptr);}
    ~SlotUploadContext(){if(context)destroyContext(display,context);if(surface)destroySurface(display,surface);if(library)SDL_UnloadObject(library);}
};
