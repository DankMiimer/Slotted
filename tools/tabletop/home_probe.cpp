// Slotted home-table probe: overview, highlight, channels, TV screen, home -> room -> home (MIT).
// home-probe MODELS PREPARED OUTPUT [TV=panasonic ROOM=snes]
#include "SlotTabletop.h"
#include "SlotSpatialNavigation.h"
#define SDL_USE_BUILTIN_OPENGL_DEFINITIONS 1
#include <SDL_opengles2.h>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <set>
static long memory(const char*key){std::ifstream in("/proc/self/status");std::string line;while(std::getline(in,line))if(line.rfind(std::string(key)+":",0)==0){long kb=0;std::istringstream(line.substr(std::string(key).size()+1))>>kb;return kb;}return -1;}
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
static bool empty(SlotTabletop*s,unsigned texture){auto p=pixels(s,texture);size_t lit=0;for(size_t i=0;i<p.size();i+=4)lit+=p[i]+p[i+1]+p[i+2]>45;return lit<p.size()/4/20;}
// A 720x480 picture standing in for the 2D list: colour bars in the 4:3 middle, grey sides.
static GLuint picture(){
    std::vector<unsigned char> p(720*480*4);const unsigned char bars[7][3]={{192,192,192},{192,192,0},{0,192,192},{0,192,0},{192,0,192},{192,0,0},{0,0,192}};
    for(int y=0;y<480;y++)for(int x=0;x<720;x++){unsigned char*o=&p[(y*720+x)*4];o[3]=255;
        if(x<40||x>=680){o[0]=o[1]=o[2]=60;continue;}const int b=(x-40)*7/640;
        const bool frame=x<44||x>=676||y<4||y>=476;for(int k=0;k<3;k++)o[k]=frame?255:y<300?bars[b][k]:(unsigned char)((x-40)*255/640);}
    GLuint t;glGenTextures(1,&t);glBindTexture(GL_TEXTURE_2D,t);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,720,480,0,GL_RGBA,GL_UNSIGNED_BYTE,p.data());
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);return t;
}
int main(int argc,char**argv){
    if(argc<4){std::fprintf(stderr,"home-probe MODELS PREPARED OUTPUT [TV ROOM]\n");return 2;}
    if(SDL_Init(SDL_INIT_VIDEO))return 1;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    const int height=getenv("SLOT_SCENE_ASPECT")&&std::string(getenv("SLOT_SCENE_ASPECT"))=="4:3"?540:480;
    SDL_Window*w=SDL_CreateWindow("Slotted home probe",0,0,720,height,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);auto owner=w?SDL_GL_CreateContext(w):nullptr;if(!owner)return 1;
    const std::string out=argv[3],tv=argc>4?argv[4]:"panasonic",room=argc>5?argv[5]:"snes";
    const std::vector<std::string> systems={"snes","n64","nes","md","psx","gb","gbc","gba","nds","psp","pico8"};
    std::vector<SlotTabletopItem> home;for(auto&m:systems)home.push_back({m.c_str(),m.c_str(),""});
    auto*s=slot_tabletop_open(w,argv[1],argv[2],"home",tv.c_str(),false,"original",720,height);if(!s){std::fprintf(stderr,"open failed\n");return 1;}
    if(getenv("SLOT_HOME_WORLD")&&!slot_tabletop_world(s))return 1;
    if(const char*path=getenv("SLOT_HOME_PROFILE_EXPORT")){
        const bool ok=slot_tabletop_export_layout(s,path);slot_tabletop_close(s);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(w);SDL_Quit();return ok?0:1;
    }
    if(!slot_tabletop_items(s,home.data(),(int)home.size())||!slot_tabletop_status(s,80,false,true,"20:15")||!slot_tabletop_stream_start(s)){std::fprintf(stderr,"setup: %s\n",slot_tabletop_error(s));return 1;}
    const GLuint tvPicture=picture();
    SlotTabletopFrame f;f.selected=-1;f.cameraView=0;f.delta=1/60.f;unsigned texture=0;std::vector<double> times;
    std::ofstream metrics(out+"/stages.tsv");metrics<<"stage\tframes\tp50_ms\tp95_ms\tmax_ms\tsettled_p95_ms\ttriangles\tdraws\ttracked_gpu_bytes\trss_kb\tpeak_rss_kb\n";
    auto run=[&](int frames,const char*name){std::vector<double> stage,settled;for(int k=0;k<frames;k++){double t=now();texture=slot_tabletop_frame(s,f);const double took=now()-t;times.push_back(took);stage.push_back(took);if(k>=60)settled.push_back(took);f.seconds+=f.delta;if(!texture){std::fprintf(stderr,"frame failed: %s\n",slot_tabletop_error(s));std::exit(1);}}
        if(name){capture(s,texture,out+"/"+name+".bmp");std::sort(stage.begin(),stage.end());std::sort(settled.begin(),settled.end());unsigned long long stats[6]={};slot_tabletop_stream_stats(s,stats);int draws[2]={};slot_tabletop_draws(s,draws);
            metrics<<name<<'\t'<<frames<<'\t'<<stage[stage.size()/2]<<'\t'<<stage[stage.size()*95/100]<<'\t'<<stage.back()<<'\t'<<(settled.empty()?-1:settled[settled.size()*95/100])<<'\t'<<slot_tabletop_triangles(s)<<'\t'<<draws[0]<<'\t'<<stats[3]<<'\t'<<memory("VmRSS")<<'\t'<<memory("VmHWM")<<'\n';metrics.flush();}};
    f.screen=tvPicture;f.screenU=1;f.screenV=1;
    run(120,"home-overview");
    if(getenv("SLOT_HOME_CRT_ONLY")){
        f.cameraView=5;f.selected=-1;run(120,"crt-off");const auto off=pixels(s,texture);
        float corners[8];if(!slot_tabletop_display(s,corners))return 6;
        float left=1e9f,top=1e9f,right=-1e9f,bottom=-1e9f;
        for(int i=0;i<4;i++){left=std::min(left,corners[2*i]);right=std::max(right,corners[2*i]);top=std::min(top,corners[2*i+1]);bottom=std::max(bottom,corners[2*i+1]);}
        slot_tabletop_crt(s,true);run(2,"crt-on");const auto on=pixels(s,texture);
        slot_tabletop_crt(s,false);run(2,"crt-off-again");const auto again=pixels(s,texture);
        if(off!=again){std::fprintf(stderr,"CRT off did not restore exact pixels\n");return 6;}
        int size[3];slot_tabletop_raster(s,size);size_t changed=0,outside=0;
        for(size_t i=0;i<off.size();i+=4)if(off[i]!=on[i]||off[i+1]!=on[i+1]||off[i+2]!=on[i+2]){
            changed++;const size_t pixel=i/4;const float x=float(pixel%size[0])*720/size[0],y=(size[1]-1-float(pixel/size[0]))*height/size[1];
            outside+=x<left-2||x>right+2||y<top-2||y>bottom+2;
        }
        if(changed<100||outside||glGetError()!=GL_NO_ERROR){std::fprintf(stderr,"CRT isolation failed: %zu changed, %zu outside glass\n",changed,outside);return 6;}
        std::printf("CRT %s %dx%d: %zu changed pixels, none outside glass; off restores exact frame\n",tv.c_str(),720,height,changed);
        slot_tabletop_close(s);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(w);SDL_Quit();return 0;
    }
    auto focusPoints=[&](){
        SlotTabletopFocus focus[32];const int count=slot_tabletop_focus_points(s,focus,32);
        std::vector<slot_navigation::Point> points;
        for(int i=0;i<count;i++)points.push_back({focus[i].item,focus[i].x,focus[i].y});
        return points;
    };
    auto navigation=[&](const char*tag){
        const auto points=focusPoints();
        if(points.size()<2){std::fprintf(stderr,"no stable navigation anchors: %s\n",tag);std::exit(5);}
        std::ofstream file(out+"/"+tag+"-navigation.tsv");file<<"item\tx\ty\tleft\tright\tup\tdown\n";
        for(const auto&start:points){
            std::set<int> visited={start.id};std::vector<int> pending={start.id};
            file<<start.id<<'\t'<<start.x<<'\t'<<start.y;
            for(auto direction:{slot_navigation::Direction::Left,slot_navigation::Direction::Right,slot_navigation::Direction::Up,slot_navigation::Direction::Down})
                file<<'\t'<<slot_navigation::neighbor(points,start.id,direction);
            file<<'\n';
            for(size_t i=0;i<pending.size();i++)for(auto direction:{slot_navigation::Direction::Left,slot_navigation::Direction::Right,slot_navigation::Direction::Up,slot_navigation::Direction::Down}){
                const int next=slot_navigation::neighbor(points,pending[i],direction);
                if(next!=slot_navigation::noTarget&&visited.insert(next).second)pending.push_back(next);
            }
            if(visited.size()!=points.size()){std::fprintf(stderr,"unreachable focus from %d (%s)\n",start.id,tag);std::exit(5);}
        }
        std::printf("%s: %zu stable anchors, all reachable from every start\n",tag,points.size());
    };
    if(getenv("SLOT_HOME_NAV_ONLY")){
        navigation("home");const auto initial=focusPoints();
        f.selected=7;run(90,"home-highlight-gba");
        f.selected=0;run(90,"home-highlight-snes");
        const auto after=focusPoints();
        if(after.size()!=initial.size())return 5;
        for(size_t i=0;i<initial.size();i++)if(initial[i].id!=after[i].id||std::abs(initial[i].x-after[i].x)>.001f||std::abs(initial[i].y-after[i].y)>.001f)return 5;
        navigation("home-after-hover");
        std::printf("hover/camera-follow leave the reference navigation anchors unchanged\n");
        auto tvFraming=[&](const char*tag){
            f.cameraView=5;f.selected=-1;run(90,tag);
            for(int item:{-2,-1}){
                float box[4];if(!slot_tabletop_bounds(s,item,box))std::exit(6);
                if(box[0]<4||box[1]<4||box[0]+box[2]>716||box[1]+box[3]>height-4){
                    std::fprintf(stderr,"TV/status clipped (%s item %d): %.2f %.2f %.2f %.2f\n",tag,item,box[0],box[1],box[2],box[3]);std::exit(6);
                }
            }
            std::printf("%s: whole TV front and status fit %dx%d\n",tag,720,height);
        };
        tvFraming("home-tv-ui");
        std::vector<std::string> ids;std::vector<SlotTabletopItem> carts;
        for(int i=0;i<12;i++)ids.push_back("navigation-game-"+std::to_string(i));
        for(int i=0;i<12;i++)carts.push_back({ids[i].c_str(),room.c_str(),""});
        if(!slot_tabletop_request(s,room.c_str(),tv.c_str(),"neilvfx",carts.data(),int(carts.size())))return 5;
        f.selected=0;f.cameraView=0;const double started=now();
        while(!slot_tabletop_ready(s)){
            if(now()-started>45000||slot_tabletop_stream_failed(s))return 5;
            texture=slot_tabletop_frame(s,f);f.seconds+=f.delta;if(!texture)return 5;
        }
        run(30,"console-overview");navigation("console");const auto loose=focusPoints();
        if(!slot_tabletop_resident(s,&carts[0],0))return 5;
        f.selected=3;f.cameraView=2;run(90,"console-loaded-camera");
        const auto loaded=focusPoints();
        if(loaded.size()!=loose.size())return 5;
        for(size_t i=0;i<loose.size();i++)if(loose[i].id!=loaded[i].id||std::abs(loose[i].x-loaded[i].x)>.001f||std::abs(loose[i].y-loaded[i].y)>.001f)return 5;
        navigation("console-after-insertion");
        std::printf("insertion and a close camera leave cartridge/TV home anchors unchanged\n");
        tvFraming("console-tv-ui");
        slot_tabletop_close(s);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(w);SDL_Quit();return 0;
    }
    if(getenv("SLOT_HOME_STATIC")){slot_tabletop_close(s);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(w);SDL_Quit();return 0;}
    f.selected=7;run(90,"home-highlight-gba");
    f.selected=0;run(90,"home-highlight-snes");
    f.cameraView=1;f.selected=-1;run(90,"home-channels");
    f.cameraView=5;run(90,"home-screen");
    f.screenLeft=40.f/720;f.screenU=640.f/720;run(30,"home-screen-43");f.screenLeft=0;f.screenU=1;
    f.zoom=1;run(30,"home-launch-zoom");f.zoom=0;
    f.cameraView=0;f.selected=0;run(60,nullptr);
    // Home -> room: the others leave, the SNES glides to its saved pose, the carts land.
    auto transition=[&](const char*system,const std::vector<SlotTabletopItem>&items,const char*tag){
        if(!slot_tabletop_request(s,system,tv.c_str(),"neilvfx",items.data(),(int)items.size())){std::fprintf(stderr,"request failed\n");std::exit(1);}
        double start=now();int frame=0;float age=0;int shot=0;
        while(!slot_tabletop_ready(s)||frame<30){
            if(now()-start>45000||slot_tabletop_stream_failed(s)){std::fprintf(stderr,"stream timeout/failure: %s\n",slot_tabletop_error(s));std::exit(1);}
            double t=now();texture=slot_tabletop_frame(s,f);times.push_back(now()-t);age+=f.delta;f.seconds+=f.delta;
            unsigned long long v[6];slot_tabletop_stream_stats(s,v);
            if(v[4]>=2&&v[4]<=4&&age>=shot*.08f&&shot<16){capture(s,texture,out+"/"+tag+"-"+std::to_string(shot)+"-phase"+std::to_string(v[4])+".bmp");shot++;}
            if((v[4]==2||v[4]==3)&&frame%3==0&&empty(s,texture)){std::fprintf(stderr,"empty transition frame (%s)\n",tag);std::exit(1);}
            frame++;
        }
        run(30,(std::string(tag)+"-settled").c_str());
        std::printf("%s: settled after %.0f ms, %d frames\n",tag,now()-start,frame);
    };
    std::vector<SlotTabletopItem> carts;std::vector<std::string> ids;for(int i=0;i<12;i++)ids.push_back("game-"+std::to_string(i));
    for(int i=0;i<12;i++)carts.push_back({ids[i].c_str(),room.c_str(),""});
    f.selected=0;f.cameraView=-1;transition(room.c_str(),carts,"to-room");
    f.selected=0;f.cameraView=0;transition("home",home,"to-home");
    std::sort(times.begin(),times.end());
    std::printf("frames=%zu median=%.2fms p95=%.2fms max=%.2fms gl=%s\n",times.size(),times[times.size()/2],times[times.size()*95/100],times.back(),slot_tabletop_error(s));
    slot_tabletop_close(s);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(w);SDL_Quit();return 0;
}
