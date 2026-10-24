#include "SlotRoomHost.h"
#include "SlotThemeRoot.h"
#include "SlotPresentation.h"
#include "SlotHome.h"
#include "views/SystemView.h"
#include "views/ViewController.h"
#include "SystemData.h"
#include "ThemeData.h"
#include "Window.h"
#include "renderers/Renderer.h"
#include "Log.h"
#include "PowerSaver.h"
#include "SlotRoomTiming.h"
#include "components/TextComponent.h"
#include "components/VideoVlcComponent.h"
#include "math/Transform4x4f.h"
#include "watchers/WatchersManager.h"
#include "watchers/BatteryLevelWatcher.h"
#include "watchers/NetworkStateWatcher.h"
#include <GLES2/gl2.h>
#include <algorithm>
#include <atomic>
#include <set>
#include <cstdio>
#include <execinfo.h>
#include <fcntl.h>
#include <pthread.h>
#include <signal.h>
#include <thread>
#include <unistd.h>
#ifdef SLOT_ROOM_TEST_DRIVER
#include "room_driver.inc"
#endif

namespace slot {
namespace {
struct Host {
    SlotTabletop* scene=nullptr;SlotTabletopFrame frame;
    unsigned texture=0,fbo=0;bool queued=false,ui=false,picture=false,powerPaused=false;Uint32 last=0;float clock=0;
} host;
int executing=0;
// SLOT_SCENE_ROOMLOG only (evidence): when room frames stop for over a second while the
// room is live, a watchdog samples the main thread's stack every ~0.5 s into
// <log>.stalls.txt, so freezes outside every measured stage can be attributed. Frames are
// module offsets; symbolise them offline with addr2line against the unstripped candidate.
struct StallSampler {
    std::atomic<Uint32> beat{0};std::atomic<bool> armed{false},sampled{false};pthread_t main{};int fd=-1;
    static void sample(int){
        void*frames[48];const int n=backtrace(frames,48);
        if(stalls().fd>=0)backtrace_symbols_fd(frames,n,stalls().fd);
        stalls().sampled=true;
    }
    static StallSampler&stalls(){static StallSampler s;return s;}
    void start(const std::string&path){
        fd=open(path.c_str(),O_WRONLY|O_CREAT|O_APPEND|O_CLOEXEC,0644);if(fd<0)return;
        void*warm[2];backtrace(warm,2); // loads the unwinder outside the signal handler
        main=pthread_self();struct sigaction action{};action.sa_handler=sample;action.sa_flags=SA_RESTART;sigemptyset(&action.sa_mask);sigaction(SIGRTMIN+3,&action,nullptr);
        std::thread([this]{
            Uint32 last=0;int samples=0,total=0;
            for(;;){
                SDL_Delay(100);const Uint32 frame=beat;const Uint32 now=SDL_GetTicks();
                if(!armed||now-frame<1000){if(now-frame<1000)samples=0;continue;}
                if(samples>=8||total>=80||now-last<500)continue;
                dprintf(fd,"== tick %u: no room frame for %u ms\n",now,now-frame);
                sampled=false;pthread_kill(main,SIGRTMIN+3);for(int i=0;i<20&&!sampled;i++)SDL_Delay(5);
                last=now;samples++;total++;
            }
        }).detach();
    }
};
struct RoomTiming {
    FILE*file=nullptr;bool opened=false;Uint64 last=0;unsigned pending=0;double ui=0,scene=0,output=0;
    // Time inside Window::input/update and Home::render since the previous row,
    // so stalls outside ui/scene/output can be split into stock and room work.
    double stages[SlotRoomStage::Count]={};
    float native[3]={}; // slot_tabletop_frame_timing: owner wait, CPU, own GPU finish
    ~RoomTiming(){if(file)std::fclose(file);}
    void tick(SlotTabletop*scene,int gui){
        if(!opened){opened=true;if(const char*path=getenv("SLOT_SCENE_ROOMLOG")){file=std::fopen(path,"a");if(file){std::fprintf(file,"ticks\tphase\ttv\tframe_ms\tui_ms\tscene_call_ms\toutput_ms\tgui\tinput_ms\tupdate_ms\thome_ms\tnative_wait_ms\tnative_cpu_ms\tnative_finish_ms\n");StallSampler::stalls().start(std::string(path)+".stalls.txt");}}}
        if(!file)return;const Uint64 now=SDL_GetPerformanceCounter();StallSampler::stalls().beat=SDL_GetTicks();StallSampler::stalls().armed=true;
        if(last&&scene){unsigned long long stats[6]={};slot_tabletop_stream_stats(scene,stats);std::fprintf(file,"%u\t%llu\t%s\t%.6f\t%.6f\t%.6f\t%.6f\t%d\t%.6f\t%.6f\t%.6f\t%.3f\t%.3f\t%.3f\n",SDL_GetTicks(),stats[4],slot_tabletop_television(scene),1000.0*(now-last)/SDL_GetPerformanceFrequency(),ui,this->scene,output,gui,stages[SlotRoomStage::Input],stages[SlotRoomStage::Update],stages[SlotRoomStage::Home],native[0],native[1],native[2]);if(++pending%64==0)std::fflush(file);}
        last=now;for(auto&stage:stages)stage=0;
    }
    double elapsed(Uint64 start)const{return 1000.0*(SDL_GetPerformanceCounter()-start)/SDL_GetPerformanceFrequency();}
} timing;
// WatchersManager::GetComponent takes the lock its thread holds while every due
// check runs, including the ~0.2 s knulli-padsinfo script every ~15 s, so a
// per-frame lookup froze the room for that long. Change notifications arrive on
// the watcher thread with the values current; frames read these copies.
struct StatusFeed:IWatcherNotify {
    std::atomic<int> battery{-1};std::atomic<bool> charging{false},connected{false};
    void read(IWatcher*component){
        if(auto*b=dynamic_cast<BatteryLevelWatcher*>(component)){const auto info=b->getBatteryInfo();battery=info.hasBattery?info.level:-1;charging=info.isCharging;}
        else if(auto*n=dynamic_cast<NetworkStateWatcher*>(component))connected=n->isConnected();
    }
    void OnWatcherChanged(IWatcher*component)override{read(component);}
};
void quad(unsigned texture,float width,float height){
    Renderer::setMatrix(Transform4x4f::Identity());Renderer::bindTexture(texture);
    Renderer::Vertex vertices[4]={{{0,0},{0,1},0xFFFFFFFF},{{0,height},{0,0},0xFFFFFFFF},
        {{width,0},{1,1},0xFFFFFFFF},{{width,height},{1,0},0xFFFFFFFF}};
    Renderer::drawTriangleStrips(vertices,4);Renderer::bindTexture(0);
}
}
}
SlotRoomStage::SlotRoomStage(Kind kind):kind(kind),started(slot::timing.file?SDL_GetPerformanceCounter():0){}
SlotRoomStage::~SlotRoomStage(){if(started)slot::timing.stages[kind]+=slot::timing.elapsed(started);}
static FILE*slotProbeFile(){
    static FILE*file=[]()->FILE*{
        const char*path=getenv("SLOT_SCENE_ROOMLOG");if(!path)return nullptr;
        FILE*f=std::fopen((std::string(path)+".probes.tsv").c_str(),"a");if(f)std::fprintf(f,"ticks\tlabel\tms\n");return f;
    }();
    return file;
}
SlotRoomProbe::SlotRoomProbe(const char*label):label(label),started(slotProbeFile()?SDL_GetPerformanceCounter():0){}
SlotRoomProbe::~SlotRoomProbe(){
    if(!started)return;const double ms=slot::timing.elapsed(started);
    if(ms>=10){std::fprintf(slotProbeFile(),"%u\t%s\t%.3f\n",SDL_GetTicks(),label,ms);std::fflush(slotProbeFile());}
}
namespace slot {
RoomStatus roomStatus(){
    static StatusFeed*feed=[]{
        // Process lifetime like the watchers (stopped only at exit). roomStartup()
        // runs right after main() creates them, before their first checks, so
        // the seed lookup does not wait; later values arrive as notifications.
        auto*f=new StatusFeed();WatchersManager::RegisterNotify(f);
        f->read(WatchersManager::GetComponent<BatteryLevelWatcher>());f->read(WatchersManager::GetComponent<NetworkStateWatcher>());
        return f;
    }();
    return {feed->battery,feed->charging,feed->connected};
}
void roomStartup(){
    roomStatus();
    // The first VideoVlcComponent runs libvlc_new (~0.2 s on the RG34XXSP),
    // which otherwise froze the first console opened from the home table.
    if(roomControls())VideoVlcComponent::init();
}
void roomGameEnded(){
    // The table reopens synchronously on the first room frame after a game, bounded by
    // decoding its 4K textures; start that now, while the frontend re-initialises.
    if(roomControls())slot_tabletop_predecode_remembered();
}
RoomExecution::RoomExecution():active(roomControls()){if(active)executing++;}
RoomExecution::~RoomExecution(){if(active)executing--;}
bool roomSplash(Window*,bool swap){
    if(!roomControls())return false;
    // The ordinary launch owner releases GL memory for actual game/app execution.
    if(executing||!Renderer::getSDLWindow())return true;
    if(!host.scene){host.scene=SlotPresentation::homeTable({});SlotPresentation::preloadType();}
    if(!host.scene)return true;
    auto frame=host.frame;const Uint32 now=SDL_GetTicks();
    frame.delta=host.last?std::min(.1f,(now-host.last)/1000.f):.016f;host.last=now;
#ifdef SLOT_ROOM_TEST_FIXED_STATUS
    frame.delta=1.f/60.f;  // host screenshot fixture: a deterministic animation clock
#endif
    host.clock+=frame.delta;frame.seconds=host.clock;
    frame.selected=-1;frame.automatic=false;
    slot_tabletop_reduced_motion(host.scene,Settings::getInstance()->getString("subset.slotted-motion")=="reduced");
    slot_tabletop_crt(host.scene,Settings::getInstance()->getString("subset.slotted-crt")!="off");
    const auto texture=slot_tabletop_frame(host.scene,frame);
    if(texture){RenderTarget output(Renderer::getWindowWidth(),Renderer::slotOutputHeight());quad(texture,Renderer::getWindowWidth(),Renderer::slotOutputHeight());}
#ifdef SLOT_ROOM_TEST_DRIVER
    roomTestBootstrap(Renderer::getWindowWidth(),Renderer::slotOutputHeight());
#endif
    if(swap)Renderer::swapBuffers();return true;
}
void roomQueue(SlotTabletop*scene,const SlotTabletopFrame&frame,bool ui,bool picture){host.scene=scene;host.frame=frame;host.queued=true;host.ui=ui;host.picture=picture;}
void roomForget(SlotTabletop*scene){
    if(host.scene==scene){host.scene=nullptr;host.queued=false;}
    timing.last=0;StallSampler::stalls().armed=false;if(timing.file)std::fflush(timing.file);
    if(host.powerPaused){PowerSaver::resume();host.powerPaused=false;}
    if(host.fbo){glDeleteFramebuffers(1,&host.fbo);host.fbo=0;}
    if(host.texture){Renderer::destroyTexture(host.texture);host.texture=0;}
}
void roomMenuTheme(){
    if(!roomControls())return;
    const auto&menu=ThemeData::getMenuTheme();if(!menu)return;
    static std::shared_ptr<ThemeData::ThemeMenu>owner;static std::unique_ptr<ThemeData::ThemeMenu>base;static std::string previous;
    if(owner!=menu){owner=menu;base.reset(new ThemeData::ThemeMenu(*menu));previous.clear();}
    const std::string tv=host.scene?slot_tabletop_television(host.scene):Settings::getInstance()->getString("subset.slot-tv-model");
    if(tv==previous)return;previous=tv;*menu=*base;
    // Use the actual cabinet selected by the saved scene, which may differ
    // from the home TV preference. Existing menu logic/widgets remain intact.
    unsigned bg=0x0B1A7AFF,text=0xF2F4FFFF,dim=0x9DB0FFFF,hi=0xFFE14AFF,sel=0xFFE14AFF,selText=0x0B1A7AFF;
    if(tv=="pvm"){bg=0x050806FF;text=0xD9E4D6FF;dim=0x7E9A82FF;hi=0x45FF7AFF;sel=0x1E6B34FF;selText=0xE8FFE9FF;}
    else if(tv=="oldtv"||tv=="retro"){bg=0x000000FF;text=0xFFFFFFFF;dim=0x00FFFFFF;hi=0xFFFF00FF;sel=0x0000D0FF;selText=0xFFFF00FF;}
    menu->Background.color=menu->Background.centerColor=bg;menu->Title.color=hi;
    for(auto*element:{&menu->Text,&menu->TextSmall,&menu->Footer}){element->color=text;element->selectedColor=selText;element->selectorColor=element->selectorGradientColor=sel;element->separatorColor=dim;}
    menu->Group.color=hi;menu->Group.backgroundColor=bg;menu->Group.separatorColor=dim;
}
bool roomRenderWindow(Window*window){
    if(!roomControls()){if(host.powerPaused){PowerSaver::resume();host.powerPaused=false;}return false;}
    timing.tick(host.scene,int(window->getGuiStackSize()));
    const Uint64 uiStarted=SDL_GetPerformanceCounter();
    // The live room animates even on the system/home view. The ordinary idle
    // event wait adds 40 ms per frame there; pause it with paired ownership,
    // preserving the user's configured power-saving mode for other themes/apps.
    if(!host.powerPaused){PowerSaver::pause();host.powerPaused=true;}
    const int outputWidth=Renderer::getWindowWidth(),outputHeight=Renderer::slotOutputHeight();
    GLint previous=0;glGetIntegerv(GL_FRAMEBUFFER_BINDING,&previous);
    if(!host.texture){
        host.texture=Renderer::createTexture(Renderer::Texture::RGBA,true,false,640,480,nullptr);
        glGenFramebuffers(1,&host.fbo);glBindFramebuffer(GL_FRAMEBUFFER,host.fbo);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,host.texture,0);
        if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE){
            LOG(LogError)<<"Slotted TV framebuffer is incomplete";glBindFramebuffer(GL_FRAMEBUFFER,previous);return true;
        }
    }
    host.queued=false;
    roomMenuTheme();
    glBindFramebuffer(GL_FRAMEBUFFER,host.fbo);
    {
        RenderTarget target(640,480);Renderer::bindTexture(0);glClearColor(.025f,.03f,.04f,1);glClear(GL_COLOR_BUFFER_BIT);
        window->renderContents();
        if(host.scene&&slot_tabletop_stream_failed(host.scene)){
            const auto skin=ThemeData::getMenuTheme();
            Renderer::setMatrix(Transform4x4f::Identity());Renderer::drawRect(0,0,640,480,skin->Background.centerColor);
            auto text=[&](const std::string&value,float y){TextComponent row(window,value,skin->Text.font,skin->Text.color);row.setPosition(28,y);row.setSize(584,110);row.render(Transform4x4f::Identity());};
            text("COULD NOT OPEN LAYOUT",28);text(slot_tabletop_error(host.scene),150);text("B  RETURN   /   L2 R2  ANOTHER SYSTEM",340);host.ui=true;
        }
    }
    glBindFramebuffer(GL_FRAMEBUFFER,previous);
    timing.ui=timing.elapsed(uiStarted);
    if(!host.scene||(!host.queued&&window->getGuiStackSize()==1)){
        // Games/apps release native GL memory through the ordinary launch owner.
        // A TV-only list belongs to the original home table, including after
        // returning from a modelled collection game. Console menus keep their
        // current furniture/arrangement instead.
        const auto systems=ViewController::get()->getSystemListView()->getObjects();
        std::vector<SystemData*>consoles;std::vector<std::string>models;std::set<std::string>seen;
        for(auto*system:systems){const auto model=system->isCollection()?"":roomModel(system->getName());if(!model.empty()&&seen.insert(model).second){consoles.push_back(system);models.push_back(model);}}
        std::vector<SlotTabletopItem>items;for(size_t i=0;i<consoles.size();i++)items.push_back({consoles[i]->getName().c_str(),models[i].c_str(),""});
        host.scene=SlotPresentation::homeTable(items);host.frame=SlotTabletopFrame();host.ui=true;
    }
    if(!host.scene)return true;
    const Uint32 now=SDL_GetTicks();float dt=host.last?std::min(.1f,(now-host.last)/1000.f):.016f;host.last=now;
#ifdef SLOT_ROOM_TEST_FIXED_STATUS
    dt=1.f/60.f;  // host screenshot fixture: a deterministic animation clock
#endif
    host.clock+=dt;
    auto frame=host.frame;frame.seconds=host.clock;frame.delta=dt;
    if(host.picture){frame.screen=host.texture;frame.screenU=frame.screenV=1;frame.screenTopDown=false;frame.screenLeft=0;}
    if(window->getGuiStackSize()>1||!host.queued||host.ui){
        frame.screen=host.texture;frame.screenU=frame.screenV=1;frame.screenTopDown=false;frame.screenLeft=0;
        frame.cameraView=5;frame.automatic=false;frame.selected=-1;frame.inspection=0;frame.yaw=frame.elevation=0;
        // Menus do not change retained media or queue a game launch.
        frame.zoom=frame.power=0;
    }
    slot_tabletop_reduced_motion(host.scene,Settings::getInstance()->getString("subset.slotted-motion")=="reduced");
    slot_tabletop_crt(host.scene,Settings::getInstance()->getString("subset.slotted-crt")!="off");
    const Uint64 sceneStarted=SDL_GetPerformanceCounter();const auto scene=slot_tabletop_frame(host.scene,frame);timing.scene=timing.elapsed(sceneStarted);
    slot_tabletop_frame_timing(host.scene,timing.native);
    const Uint64 outputStarted=SDL_GetPerformanceCounter();
    if(scene){RenderTarget output(outputWidth,outputHeight);quad(scene,float(outputWidth),float(outputHeight));}
    timing.output=timing.elapsed(outputStarted);
    // Stock menu/notification closures can resume idle polling independently
    // of the room's paired pause. Keep the live frame loop active without
    // adding pause counters; roomForget still restores ordinary ownership.
    PowerSaver::lock(false);
#ifdef SLOT_ROOM_TEST_DRIVER
    roomTestFrame(window,host.scene,frame,host.fbo,outputWidth,outputHeight);
#endif
    return true;
}
}
bool slotRoomRenderWindow(Window*window){return slot::roomRenderWindow(window);}
bool slotRoomSplash(Window*window,bool swap){return slot::roomSplash(window,swap);}
