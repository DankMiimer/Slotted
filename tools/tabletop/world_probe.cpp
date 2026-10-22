// Persistent room: fixed tables, console-follow camera and newest-request stress (MIT).
#include "SlotTabletop.h"
#include "SlotWorldLayout.h"
#include "SlotHomeProfile.h"
#define SDL_USE_BUILTIN_OPENGL_DEFINITIONS 1
#include <SDL_opengles2.h>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <string>
#include <vector>
using namespace slot_scene;
static double now(){return 1000.0*SDL_GetPerformanceCounter()/SDL_GetPerformanceFrequency();}
static void capture(SlotTabletop*s,unsigned texture,const std::string&path){
    if(getenv("SLOT_WORLD_NO_CAPTURE"))return; // timing runs (e.g. on the device) keep no BMPs
    int size[3];slot_tabletop_raster(s,size);GLuint fbo;
    glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)std::exit(3);
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
    const int height=getenv("SLOT_SCENE_ASPECT")&&std::string(getenv("SLOT_SCENE_ASPECT"))=="4:3"?540:480;
    auto*window=SDL_CreateWindow("Slotted persistent room probe",0,0,720,height,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);
    const auto owner=window?SDL_GL_CreateContext(window):nullptr;if(!owner)return 1;
    const std::string out=argv[3];
    const bool details=getenv("SLOT_WORLD_DETAILS")!=nullptr,matrix=getenv("SLOT_WORLD_MATRIX")!=nullptr;
    auto*scene=slot_tabletop_open(window,argv[1],argv[2],"home","panasonic",false,"original",720,height);
    if(!scene||!slot_tabletop_world(scene,getenv("SLOT_WORLD_PROFILE")))return 1;
    slot_tabletop_reduced_motion(scene,getenv("SLOT_WORLD_REDUCED")!=nullptr);
    std::vector<std::string> systems={"snes","n64","nes","md","psx","gb","gbc","gba","nds","psp","pico8"},ids;
    std::vector<SlotTabletopItem> home,carts;
    for(const auto&system:systems)home.push_back({system.c_str(),system.c_str(),""});
    for(int i=0;i<12;i++)ids.push_back("world-game-"+std::to_string(i));
    if(!slot_tabletop_items(scene,home.data(),int(home.size()))||!slot_tabletop_status(scene,80,false,true,"20:15")||!slot_tabletop_stream_start(scene))return 1;
    SlotTabletopFrame frame;frame.selected=-1;frame.cameraView=0;frame.automatic=false;frame.delta=1/60.f;
    std::map<std::string,std::array<float,16>> fixed;
    std::ofstream log(out+"/frames.tsv");log<<"frame\tphase\ttables\tvisible\tx\ty\tz\tms\n";
    unsigned texture=0;int frames=0,both=0;double worst=0;
    auto tick=[&](){
        const auto start=now();texture=slot_tabletop_frame(scene,frame);const double ms=now()-start;worst=std::max(worst,ms);
        if(!texture){std::fprintf(stderr,"render failed: %s\n",slot_tabletop_error(scene));std::exit(4);}
        // The accepted authored close-ups may put furniture outside the frustum,
        // including during their pan back to the TV. World ownership stays live.
        int counts[2]={};if(!slot_tabletop_world_stats(scene,counts)||counts[0]<1||counts[0]>2||(counts[1]<1&&(!matrix||frame.cameraView==0))){std::fprintf(stderr,"table disappeared at frame %d (%d/%d)\n",frames,counts[1],counts[0]);std::exit(4);}
        both+=counts[1]==2;
        for(const auto*model:{"table","wooden-table","tv-stand"}){
            std::array<float,16> pose;if(!slot_tabletop_world_table(scene,model,pose.data()))continue;
            auto old=fixed.emplace(model,pose);
            for(int i=0;i<16;i++)if(std::abs(old.first->second[i]-pose[i])>.002f){std::fprintf(stderr,"table moved: %s element %d\n",model,i);std::exit(4);}
        }
        unsigned long long stats[6];slot_tabletop_stream_stats(scene,stats);float camera[7];slot_tabletop_camera(scene,camera);
        log<<frames<<'\t'<<stats[4]<<'\t'<<counts[0]<<'\t'<<counts[1]<<'\t'<<camera[0]<<'\t'<<camera[1]<<'\t'<<camera[2]<<'\t'<<ms<<'\n';
        frame.seconds+=frame.delta;frames++;
    };
    auto settle=[&](const std::string&name){
        const auto started=now();int count=0,shot=0;
        do{
            if(now()-started>(details?120000:45000)||slot_tabletop_stream_failed(scene)){std::fprintf(stderr,"stream failed/timed out %s: %s\n",name.c_str(),slot_tabletop_error(scene));std::exit(4);}
            tick();count++;
            unsigned long long stats[6];slot_tabletop_stream_stats(scene,stats);
            if(!matrix&&(stats[4]==3||stats[4]==4)&&shot<(details?30:10)&&count%(details?6:8)==0)capture(scene,texture,out+"/"+name+"-travel-"+std::to_string(shot++)+".bmp");
        }while(!slot_tabletop_ready(scene)||count<60);
        for(int i=0;i<60;i++)tick();
        if(!matrix)capture(scene,texture,out+"/"+name+"-settled.bmp");
        const auto path=out+"/"+name+".scene";if(!slot_tabletop_export_layout(scene,path.c_str()))std::exit(4);
        SceneProfile source;
        if(name.rfind("home",0)==0){HomeProfile homeProfile;if(!readHomeProfile(path,homeProfile))std::exit(4);source.eye=homeProfile.overview.eye;source.target=homeProfile.overview.target;source.fov=homeProfile.overview.fov;source.width=homeProfile.width;source.height=homeProfile.height;}
        else if(!readSceneProfile(path,source))std::exit(4);
        if(frame.cameraView>0&&frame.cameraView<5&&source.cameras[frame.cameraView].authored){const auto&c=source.cameras[frame.cameraView];source.eye=c.eye;source.target=c.target;source.fov=c.fov;}
        Mat root;float camera[7];slot_tabletop_world_transform(scene,root.v);slot_tabletop_camera(scene,camera);
        const auto eye=transform(root,source.eye),target=transform(root,source.target);
        const float error=std::abs(eye.x-camera[0])+std::abs(eye.y-camera[1])+std::abs(eye.z-camera[2])+std::abs(target.x-camera[3])+std::abs(target.y-camera[4])+std::abs(target.z-camera[5]);
        if(error>.002f){std::fprintf(stderr,"authored camera drift: %s %.6f\n",name.c_str(),error);std::exit(4);}
        const float fov=2*std::atan(std::tan(radians(source.fov)/2)*source.width/source.height*height/720)*180/3.14159265f;
        if(std::abs(fov-camera[6])>.002f){std::fprintf(stderr,"authored FOV drift: %s\n",name.c_str());std::exit(4);}
        std::printf("%s: fixed tables, persistent world, saved camera error %.6f\n",name.c_str(),error);std::fflush(stdout);
    };
    auto request=[&](const char*system,const char*tv){
        carts.clear();for(const auto&id:ids)carts.push_back({id.c_str(),system,""});
        const bool isHome=std::string(system)=="home";
        frame.cameraView=details&&std::string(system)=="gba"?2:0;
        if(!slot_tabletop_request(scene,system,tv,"neilvfx",isHome?home.data():carts.data(),int(isHome?home.size():carts.size())))std::exit(4);
    };
    if(matrix){
        int cases=0,closeups=0;
        std::ofstream checks(out+"/matrix.tsv");checks<<"system\ttv\tfront_and_status\tanchors\tauthored_closeups\n";
        for(const char*tv:{"panasonic","pvm","oldtv"}){
            std::vector<std::string> models={"home"};models.insert(models.end(),systems.begin(),systems.end());
            for(const auto&model:models){
                // Exact overview comparisons exclude the intentional home focus lean.
                frame.selected=model=="home"?-1:0;
                const std::string tag=model+"-"+tv;request(model.c_str(),tv);settle(tag);
                int tested=0;
                if(model!="home"){
                    SceneProfile profile;if(!readSceneProfile(out+"/"+tag+".scene",profile))return 4;
                    for(int view=1;view<=3;view++)if(profile.cameras[view].authored){
                        frame.cameraView=view;settle(tag+"-camera"+std::to_string(view));tested++;closeups++;
                    }
                }
                frame.cameraView=5;frame.selected=-1;for(int i=0;i<120;i++)tick();
                for(int item:{-2,-1}){
                    float box[4];if(!slot_tabletop_bounds(scene,item,box)||box[0]<4||box[1]<4||box[0]+box[2]>716||box[1]+box[3]>height-4){
                        std::fprintf(stderr,"TV/status framing failed: %s item %d\n",tag.c_str(),item);return 4;
                    }
                }
                SlotTabletopFocus points[32];const int anchors=slot_tabletop_focus_points(scene,points,32);
                if(anchors!=(model=="home"?12:13)||glGetError()!=GL_NO_ERROR){std::fprintf(stderr,"matrix anchors/GL failed: %s (%d)\n",tag.c_str(),anchors);return 4;}
                if(model=="home")capture(scene,texture,out+"/"+tag+"-tv.bmp");
                checks<<model<<'\t'<<tv<<"\tpass\t"<<anchors<<'\t'<<tested<<'\n';checks.flush();cases++;
                frame.selected=0;
            }
        }
        std::printf("matrix: %d layouts, %d exact authored close-ups, all TV fronts/status and anchors pass at 720x%d; %d frames\n",cases,closeups,height,frames);
        slot_tabletop_close(scene);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(window);SDL_Quit();return cases==36?0:4;
    }
    settle("home-start");
    request("gba","pvm");settle("gba-cross-table");
    request("home","panasonic");settle("home-return");
    request("nes","panasonic");settle("nes-same-table");
    request("gba","pvm");settle("gba-system-switch");
    request("snes","panasonic");settle("snes-system-switch");
    for(int i=0;i<30;i++){request(i%2?"gba":"home",i%2?"pvm":"panasonic");for(int j=0;j<3;j++)tick();}
    request("home","panasonic");settle("home-after-retargets");
    if(!both||fixed.size()<2)return 4;
    std::printf("world: %d frames; %d two-table views; %zu fixed table models; max host frame %.2f ms\n",frames,both,fixed.size(),worst);
    slot_tabletop_close(scene);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(window);SDL_Quit();return 0;
}
