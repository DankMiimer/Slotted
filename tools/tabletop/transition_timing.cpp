// Paced (60 Hz) system-switch timing study against the public tabletop API (MIT).
// transition-timing MODELS PREPARED OUTPUT FACES STEP... ; STEP is system:tv[:idle seconds[:p]]
// (`p` prefetches that step's destination while idling before it, as the frontend
// prefetches neighbours). Writes OUTPUT/frames.tsv; SLOT_SCENE_STREAMLOG adds events.
#include "SlotTabletop.h"
#define SDL_USE_BUILTIN_OPENGL_DEFINITIONS 1
#include <SDL_opengles2.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>
static double now(){return 1000.0*SDL_GetPerformanceCounter()/SDL_GetPerformanceFrequency();}
int main(int argc,char**argv){
    if(argc<6){std::fprintf(stderr,"transition-timing MODELS PREPARED OUTPUT FACES STEP...\n");return 2;}
    if(SDL_Init(SDL_INIT_VIDEO))return 1;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    SDL_Window*w=SDL_CreateWindow("Switch timing",0,0,720,480,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);auto owner=w?SDL_GL_CreateContext(w):nullptr;if(!owner)return 1;
    auto*s=slot_tabletop_open(w,argv[1],argv[2],"snes","panasonic",false,"original",720,480);if(!s)return 1;
    SlotTabletopItem items[12];std::string ids[12],faces[12];std::string model;
    auto bind=[&](const std::string&system){model=system;for(int i=0;i<12;i++){ids[i]=system+"-"+std::to_string(i);faces[i]=std::string(argv[4])+"/"+system+"/"+std::to_string(i)+".png";if(!std::ifstream(faces[i]))faces[i].clear();items[i]={ids[i].c_str(),model.c_str(),faces[i].c_str()};}};
    bind("snes");if(!slot_tabletop_items(s,items,12)||!slot_tabletop_status(s,100,true,true,"18:08")||!slot_tabletop_stream_start(s))return 1;
    std::ofstream out(std::string(argv[3])+"/frames.tsv");out<<"step\tsystem\tframe\tticks\tsince_request_ms\tinterval_ms\tframe_ms\tphase\twanted\tactive\tuploads\n";
    SlotTabletopFrame f;f.selected=0;f.cameraView=-1;f.seconds=0;
    double previous=now(),next=previous;
    // One vsync-paced frame: the frontend's delta, then wait for the next 60 Hz tick.
    auto frame=[&](int step,const std::string&system,double request,long index){
        const double start=now();f.delta=(float)std::min(.1,std::max(.001,(start-previous)/1000));f.seconds+=f.delta;
        const double interval=start-previous;previous=start;
        unsigned texture=slot_tabletop_frame(s,f);const double took=now()-start;if(!texture)std::exit(1);
        unsigned long long v[6];slot_tabletop_stream_stats(s,v);
        out<<step<<'\t'<<system<<'\t'<<index<<'\t'<<SDL_GetTicks()<<'\t'<<(request>0?start-request:-1)<<'\t'<<interval<<'\t'<<took<<'\t'<<v[4]<<'\t'<<v[0]<<'\t'<<v[1]<<'\t'<<v[5]<<'\n';
        next+=1000/60.;if(now()>next)next=now();else while(now()<next)SDL_Delay(next-now()>2?1:0);
    };
    for(long k=0;k<240;k++)frame(-1,"snes",-1,k);
    for(int a=5;a<argc;a++){
        std::string step=argv[a],system=step.substr(0,step.find(':')),rest=step.substr(step.find(':')+1),tv=rest.substr(0,rest.find(':'));
        float idle=1;bool prefetch=false;if(rest.find(':')!=std::string::npos){const std::string tail=rest.substr(rest.find(':')+1);idle=std::atof(tail.c_str());prefetch=tail.find(":p")!=std::string::npos;}
        if(prefetch)slot_tabletop_prefetch(s,system.c_str(),tv.c_str(),"neilvfx");
        for(long k=0;k<(long)(idle*60);k++)frame(a-5,"idle",-1,k);
        bind(system);const double request=now();if(!slot_tabletop_request(s,system.c_str(),tv.c_str(),"neilvfx",items,12))return 1;
        long k=0;while(!slot_tabletop_ready(s)){if(now()-request>30000||slot_tabletop_stream_failed(s)){std::fprintf(stderr,"timeout/failure at %s\n",step.c_str());return 1;}frame(a-5,system,request,k++);}
        std::printf("%s settled_ms=%.0f frames=%ld\n",step.c_str(),now()-request,k);std::fflush(stdout);
        for(int j=0;j<30;j++)frame(a-5,system,request,k++);
    }
    slot_tabletop_close(s);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(w);SDL_Quit();return 0;
}
