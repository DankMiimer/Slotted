// Public-API integration probe for persistent scene ownership and streaming (MIT).
#include "SlotTabletop.h"
#define SDL_USE_BUILTIN_OPENGL_DEFINITIONS 1
#include <SDL_opengles2.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <fstream>
#include <chrono>
#include <set>
static double now(){return 1000.0*SDL_GetPerformanceCounter()/SDL_GetPerformanceFrequency();}
static std::vector<unsigned char> pixels(SlotTabletop*s,unsigned texture){
    int raster[3];slot_tabletop_raster(s,raster);GLuint fbo;glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)std::exit(3);
    std::vector<unsigned char> p(raster[0]*raster[1]*4);glReadPixels(0,0,raster[0],raster[1],GL_RGBA,GL_UNSIGNED_BYTE,p.data());glBindFramebuffer(GL_FRAMEBUFFER,0);glDeleteFramebuffers(1,&fbo);return p;
}
static void capture(SlotTabletop*s,unsigned texture,const std::string&path){
    auto p=pixels(s,texture);int size[3];slot_tabletop_raster(s,size);const size_t row=size[0]*4;
    for(int y=0;y<size[1]/2;y++)for(size_t x=0;x<row;x++)std::swap(p[y*row+x],p[(size[1]-1-y)*row+x]);
    SDL_Surface*surface=SDL_CreateRGBSurfaceWithFormatFrom(p.data(),size[0],size[1],32,size[0]*4,SDL_PIXELFORMAT_RGBA32);
    if(!surface||SDL_SaveBMP(surface,path.c_str()))std::exit(4);SDL_FreeSurface(surface);
}
int main(int argc,char**argv){
    if(argc<4){std::fprintf(stderr,"transition-probe MODELS PREPARED OUTPUT [TARGET=gba TV=pvm]\n");return 2;}
    if(SDL_Init(SDL_INIT_VIDEO))return 1;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    int height=getenv("SLOT_SCENE_ASPECT")&&std::string(getenv("SLOT_SCENE_ASPECT"))=="4:3"?540:480;
    SDL_Window*w=SDL_CreateWindow("Persistent scene validation",0,0,720,height,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);auto owner=w?SDL_GL_CreateContext(w):nullptr;if(!owner)return 1;
    auto*s=slot_tabletop_open(w,argv[1],argv[2],"snes","panasonic",false,"original",720,height);if(!s)return 1;
    SlotTabletopItem items[12];std::string ids[12],faces[12];
    auto bind=[&](const std::string&model){for(int i=0;i<12;i++){faces[i]=argc>6?std::string(argv[6])+"/"+model+"/"+std::to_string(i)+".png":"";if(!faces[i].empty()&&!std::ifstream(faces[i]))faces[i].clear();items[i]={ids[i].c_str(),model.c_str(),faces[i].c_str()};}};
    for(int i=0;i<12;i++)ids[i]="game-"+std::to_string(i);const std::string snes="snes";bind(snes);
    if(!slot_tabletop_items(s,items,12)||!slot_tabletop_status(s,100,true,true,"18:08")||!slot_tabletop_stream_start(s))return 1;
    SlotTabletopFrame f;f.selected=0;f.cameraView=-1;f.delta=1/60.f;unsigned texture=0;
    for(int k=0;k<160;k++)texture=slot_tabletop_frame(s,f);
    const std::string system=argc>4?argv[4]:"gba",tv=argc>5?argv[5]:"pvm";
    // Prepare expected neighbors while the current room is present. Main calls
    // continue during load; no join or full-scene reopen occurs here.
    slot_tabletop_prefetch(s,"nes","panasonic","neilvfx");slot_tabletop_prefetch(s,system.c_str(),tv.c_str(),"neilvfx");
    bind(system);
    const auto before=pixels(s,texture);
    if(!slot_tabletop_request(s,system.c_str(),tv.c_str(),"neilvfx",items,12))return 1;
    std::ofstream timeline(std::string(argv[3])+"/frames.tsv");timeline<<"frame\tms\twanted\tactive\tloads\tgpu_bytes\tphase\tuploads\n";
    // Input acknowledgement: animation time until the room visibly moves (the lift
    // starts on the request frame, before the destination is prepared).
    float animation=0,visible=-1;
    slot_scene::SceneProfile profile;const auto choice=slot_scene::sceneProfileFor(std::string(argv[2])+"/layouts",system,tv);
    if(!slot_scene::readSceneProfile(choice.path,profile))return 1;
    bool sawOverview=false,sawSavedPan=false;float lastArrivalError=1000;
    std::set<std::pair<int,int>> captures;int previousPhase=-1;float phaseAge=0;
    std::vector<double> times;unsigned frames=0;double start=now(),previous=start;
    while(!slot_tabletop_ready(s)||frames<60){
        if(now()-start>45000||slot_tabletop_stream_failed(s)){std::fprintf(stderr,"stream timeout/failure: %s\n",slot_tabletop_error(s));return 1;}
        // 60 Hz animation steps while the acknowledgement is measured, then real time.
        double t=now();f.delta=std::min(.05,(t-previous)/1000);if(f.delta<.001)f.delta=.001;if(visible<0&&animation<.25f)f.delta=1/60.f;previous=t;
        texture=slot_tabletop_frame(s,f);double ms=now()-t;if(!texture)return 1;times.push_back(ms);animation+=f.delta;
        unsigned long long v[6];slot_tabletop_stream_stats(s,v);timeline<<frames<<'\t'<<ms;for(int k=0;k<6;k++)timeline<<'\t'<<v[k];timeline<<'\n';
        if(visible<0&&animation<.25f){
            auto p=pixels(s,texture);size_t moved=0;for(size_t i=0;i<p.size();i+=4)moved+=std::abs(p[i]-before[i])+std::abs(p[i+1]-before[i+1])+std::abs(p[i+2]-before[i+2])>24;
            if(moved>=200)visible=animation;
        }
        float camera[7];slot_tabletop_camera(s,camera);
        if(v[4]==3){
            float error=0;const float expected[]={profile.eye.x,profile.eye.y,profile.eye.z,profile.target.x,profile.target.y,profile.target.z,
                2*std::atan(std::tan(slot_scene::radians(profile.fov)/2)*profile.width/profile.height*height/720.f)*180/3.14159265358979323846f};
            for(int k=0;k<7;k++)error=std::max(error,std::abs(camera[k]-expected[k]));
            lastArrivalError=error;if(error<.001f)sawOverview=true;
        }
        if(v[4]==4)sawSavedPan=true;
        if((int)v[4]!=previousPhase){phaseAge=0;previousPhase=v[4];}else phaseAge+=f.delta;
        if(v[4]>=2&&v[4]<=4)for(int mark=1;mark<=6;mark++)if(phaseAge>=mark*.10f&&captures.emplace(v[4],mark).second)
            capture(s,texture,std::string(argv[3])+"/phase-"+std::to_string(v[4])+"-"+std::to_string(mark)+".bmp");
        // Departure/arrival (incl. a table slide) never shows an empty screen.
        if(frames%30==0||((v[4]==2||v[4]==3)&&frames%2==0)){auto p=pixels(s,texture);size_t foreground=0;for(size_t i=0;i<p.size();i+=4)foreground+=p[i]+p[i+1]+p[i+2]>45;if(foreground<p.size()/4/20){std::fprintf(stderr,"Black/empty transition frame\n");return 1;}}
        frames++;SDL_Delay(1);
    }
    if(!sawOverview||lastArrivalError>.001f||!sawSavedPan){std::fprintf(stderr,"Overview-before-saved-camera failed %d %g %d\n",sawOverview,lastArrivalError,sawSavedPan);return 1;}
    // Visible within three 60 Hz frames of the request.
    if(visible<0||visible>.051f){std::fprintf(stderr,"No visible motion within three frames of the request (%g s)\n",visible);return 1;}
    float readyCamera[7];slot_tabletop_camera(s,readyCamera);
    f.delta=1/60.f;for(int i=0;i<160;i++)texture=slot_tabletop_frame(s,f);auto destination=pixels(s,texture);float destinationCamera[7];slot_tabletop_camera(s,destinationCamera);
    // Ready means settled: the saved camera is already exact on that frame.
    for(int k=0;k<7;k++)if(readyCamera[k]!=destinationCamera[k]){std::fprintf(stderr,"Camera still moving after ready\n");return 1;}
    // A retarget back to this room while the hardware is still lifting lowers it
    // again: no commit, and the same pixels as before.
    {
        const std::string other=system=="nes"?"n64":"nes";bind(other);
        if(!slot_tabletop_request(s,other.c_str(),"panasonic","neilvfx",items,12))return 1;
        for(int k=0;k<4;k++){f.delta=1/60.f;texture=slot_tabletop_frame(s,f);SDL_Delay(1);}
        unsigned long long v[6];slot_tabletop_stream_stats(s,v);if(v[4]!=2){std::fprintf(stderr,"Request did not start lifting at once\n");return 1;}
        bind(system);if(!slot_tabletop_request(s,system.c_str(),tv.c_str(),"neilvfx",items,12))return 1;
        start=now();while(!slot_tabletop_ready(s)){
            if(now()-start>30000||slot_tabletop_stream_failed(s))return 1;
            f.delta=1/60.f;texture=slot_tabletop_frame(s,f);if(!texture)return 1;slot_tabletop_stream_stats(s,v);
            if(v[4]==3){std::fprintf(stderr,"Return to the current room flew the hardware away\n");return 1;}SDL_Delay(1);
        }
        for(int i=0;i<60;i++)texture=slot_tabletop_frame(s,f);
        if(pixels(s,texture)!=destination){std::fprintf(stderr,"Return to the current room did not restore the scene\n");return 1;}
    }
    // Thirty rapid changes, interleaved with actual drawing/preparation.
    const std::string targets[]={"nes","n64","snes"};
    for(int change=0;change<30;change++){
        const auto&target=targets[change%3];bind(target);
        if(!slot_tabletop_request(s,target.c_str(),"panasonic","neilvfx",items,12))return 1;
        for(int k=0;k<3;k++){texture=slot_tabletop_frame(s,f);if(!texture)return 1;SDL_Delay(1);}
    }
    start=now();while(!slot_tabletop_ready(s)){
        if(now()-start>30000||slot_tabletop_stream_failed(s))return 1;
        f.delta=1/60.f;texture=slot_tabletop_frame(s,f);if(!texture)return 1;SDL_Delay(1);
    }
    unsigned long long stats[6];slot_tabletop_stream_stats(s,stats);if(stats[0]!=stats[1])return 1;
    // Settled source matrices and complete source geometry must match a normal
    // fresh renderer. Close before the reference so device RAM never doubles.
    for(int i=0;i<120;i++)texture=slot_tabletop_frame(s,f);auto final=pixels(s,texture);float camera[7];slot_tabletop_camera(s,camera);
    slot_tabletop_close(s);s=slot_tabletop_open(w,argv[1],argv[2],system.c_str(),tv.c_str(),false,"original",720,height);if(!s)return 1;bind(system);
    if(!slot_tabletop_items(s,items,12)||!slot_tabletop_status(s,100,true,true,"18:08"))return 1;
    for(int i=0;i<160;i++)texture=slot_tabletop_frame(s,f);auto expectedDestination=pixels(s,texture);float dc[7];slot_tabletop_camera(s,dc);float destinationError=0;for(int i=0;i<7;i++)destinationError=std::max(destinationError,std::abs(dc[i]-destinationCamera[i]));
    bool sameDestination=destination==expectedDestination;
    slot_tabletop_close(s);s=slot_tabletop_open(w,argv[1],argv[2],"snes","panasonic",false,"original",720,height);if(!s)return 1;bind(snes);
    if(!slot_tabletop_items(s,items,12)||!slot_tabletop_status(s,100,true,true,"18:08"))return 1;
    for(int i=0;i<120;i++)texture=slot_tabletop_frame(s,f);auto expected=pixels(s,texture);float ref[7];slot_tabletop_camera(s,ref);
    bool same=final==expected;float error=0;for(int i=0;i<7;i++)error=std::max(error,std::abs(camera[i]-ref[i]));
    GLenum gl=glGetError();if(!slot_tabletop_stream_start(s))return 1;slot_tabletop_prefetch(s,"gba","pvm","neilvfx");for(int i=0;i<8;i++){slot_tabletop_frame(s,f);SDL_Delay(3);}slot_tabletop_close(s);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(w);SDL_Quit();
    std::sort(times.begin(),times.end());std::printf("frames=%u p50_ms=%.3f p95_ms=%.3f max_ms=%.3f wanted=%llu active=%llu loads=%llu resources_bytes=%llu same_landing=%d camera_error=%g same_destination=%d destination_camera_error=%g gl_error=%u overview_before_saved=%d visible_motion_s=%.4f\n",frames,times[times.size()/2],times[times.size()*95/100],times.back(),stats[0],stats[1],stats[2],stats[3],same,error,sameDestination,destinationError,gl,sawOverview&&sawSavedPan,visible);
    return same&&error==0&&sameDestination&&destinationError==0&&!gl?0:1;
}
