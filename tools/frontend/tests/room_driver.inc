// Host test build only: scripted SDL inputs/captures, never compiled by build.sh.
#include "components/SlotRoomSession.h"
#include "components/SlotHome.h"
#include "components/SlotSpatialNavigation.h"
#include "views/ViewController.h"
#include "SystemData.h"
#include <fstream>
#include <sstream>
#include <map>
#include <vector>
#include <cstring>
static void roomTestBootstrap(int width,int height){
    static bool saved=false;const char*out=getenv("SLOT_ROOM_TEST_OUTPUT");if(saved||!out)return;saved=true;
    SDL_Surface*image=SDL_CreateRGBSurfaceWithFormat(0,width,height,32,SDL_PIXELFORMAT_RGBA32);glPixelStorei(GL_PACK_ALIGNMENT,1);glReadPixels(0,0,width,height,GL_RGBA,GL_UNSIGNED_BYTE,image->pixels);
    std::vector<unsigned char>row(image->pitch);for(int y=0;y<height/2;y++){auto*a=(unsigned char*)image->pixels+y*image->pitch;auto*b=(unsigned char*)image->pixels+(height-1-y)*image->pitch;std::memcpy(row.data(),a,image->pitch);std::memcpy(a,b,image->pitch);std::memcpy(b,row.data(),image->pitch);}
    SDL_SaveBMP(image,(std::string(out)+"/bootstrap-room.bmp").c_str());SDL_FreeSurface(image);
}
static void roomTestFrame(Window*window,SlotTabletop*scene,const SlotTabletopFrame&frame,unsigned uiFbo,int width,int height){
    struct Action {int at;std::string kind,arg;};
    struct Driver {
        int number=0;std::string out;std::vector<Action>actions;std::vector<std::pair<SDL_Keycode,int>> releases;std::ofstream log;
        Driver(){
            const char*script=getenv("SLOT_ROOM_TEST_SCRIPT"),*output=getenv("SLOT_ROOM_TEST_OUTPUT");if(!script||!output)return;
            out=output;std::ifstream in(script);std::string line;
            while(std::getline(in,line)){std::istringstream row(line);Action a;if(row>>a.at>>a.kind>>a.arg)actions.push_back(a);}
            log.open(out+"/frames.tsv");log<<"frame\tsystem\tview\tgui\tselected\tcamera\tphase\ttables\tvisible\tinserted\tglerror\n";
        }
    };static Driver driver;if(driver.out.empty())return;
    auto key=[](SDL_Keycode key,bool down){SDL_Event e={};e.type=down?SDL_KEYDOWN:SDL_KEYUP;e.key.state=down?SDL_PRESSED:SDL_RELEASED;e.key.keysym.sym=key;e.key.keysym.scancode=SDL_GetScancodeFromKey(key);SDL_PushEvent(&e);};
    for(auto i=driver.releases.begin();i!=driver.releases.end();)if(i->second<=driver.number){key(i->first,false);i=driver.releases.erase(i);}else ++i;
    auto save=[&](unsigned fbo,int w,int h,const std::string&name){
        GLint old=0;glGetIntegerv(GL_FRAMEBUFFER_BINDING,&old);glBindFramebuffer(GL_FRAMEBUFFER,fbo);
        SDL_Surface*image=SDL_CreateRGBSurfaceWithFormat(0,w,h,32,SDL_PIXELFORMAT_RGBA32);glPixelStorei(GL_PACK_ALIGNMENT,1);glReadPixels(0,0,w,h,GL_RGBA,GL_UNSIGNED_BYTE,image->pixels);
        std::vector<unsigned char>row(image->pitch);for(int y=0;y<h/2;y++){auto*a=(unsigned char*)image->pixels+y*image->pitch;auto*b=(unsigned char*)image->pixels+(h-1-y)*image->pitch;std::memcpy(row.data(),a,image->pitch);std::memcpy(a,b,image->pitch);std::memcpy(b,row.data(),image->pitch);}
        SDL_SaveBMP(image,(driver.out+"/"+name+".bmp").c_str());SDL_FreeSurface(image);glBindFramebuffer(GL_FRAMEBUFFER,old);
    };
    const bool ready=slot_tabletop_ready(scene)||slot_tabletop_stream_failed(scene);
    bool seeking=false;
    for(const auto&action:driver.actions)if(ready&&action.at==driver.number){
        if(action.kind=="key"){
            static const std::map<std::string,SDL_Keycode>keys={{"ok",SDLK_RETURN},{"back",SDLK_ESCAPE},{"up",SDLK_UP},{"down",SDLK_DOWN},{"left",SDLK_LEFT},{"right",SDLK_RIGHT},{"start",SDLK_F1},{"select",SDLK_F2},{"r3",SDLK_F9},{"l3",SDLK_F10},{"r2",SDLK_F8},{"l2",SDLK_F7}};
            auto i=keys.find(action.arg);if(i!=keys.end()){key(i->second,true);driver.releases.push_back({i->second,driver.number+3});}
        }else if(action.kind=="seek"){
            int target=-2;
            if(action.arg!="tv"){
                int index=0;std::set<std::string>models;
                for(auto*system:ViewController::get()->getSystemListView()->getObjects()){
                    const auto model=system->isCollection()?"":slot::roomModel(system->getName());if(model.empty()||!models.insert(model).second)continue;
                    if(model==action.arg){target=index;break;}index++;
                }
            }
            if(frame.selected==target)continue;
            SlotTabletopFocus anchors[16];const int count=slot_tabletop_focus_points(scene,anchors,16,frame.cameraView);
            std::vector<slot_navigation::Point>points;for(int i=0;i<count;i++)points.push_back({anchors[i].item,anchors[i].x,anchors[i].y,true});
            struct Node{int id;SDL_Keycode first;};std::vector<Node>queue={{frame.selected,0}};std::set<int>seen={frame.selected};
            const slot_navigation::Direction directions[]={slot_navigation::Direction::Left,slot_navigation::Direction::Right,slot_navigation::Direction::Up,slot_navigation::Direction::Down};
            const SDL_Keycode keys[]={SDLK_LEFT,SDLK_RIGHT,SDLK_UP,SDLK_DOWN};
            for(size_t i=0;i<queue.size();i++){
                if(queue[i].id==target){key(queue[i].first,true);key(queue[i].first,false);break;}
                for(int d=0;d<4;d++){const int next=slot_navigation::neighbor(points,queue[i].id,directions[d]);if(next!=slot_navigation::noTarget&&seen.insert(next).second)queue.push_back({next,queue[i].first?queue[i].first:keys[d]});}
            }
            seeking=true;
        }else if(action.kind=="shot"){
            save(0,width,height,action.arg+"-room");save(uiFbo,640,480,action.arg+"-ui");slot_tabletop_export_layout(scene,(driver.out+"/"+action.arg+".scene").c_str());
        }else if(action.kind=="quit"){SDL_Event e={};e.type=SDL_QUIT;SDL_PushEvent(&e);}
    }
    const auto state=ViewController::get()->getState();auto*system=state.getSystem();int counts[2]={};slot_tabletop_world_stats(scene,counts);unsigned long long stats[6]={};slot_tabletop_stream_stats(scene,stats);
    const auto inserted=system?slot::roomSession().console(slot::roomModel(system->getName())).media.inserted():"";
    driver.log<<driver.number<<'\t'<<(system?system->getName():"")<<'\t'<<int(state.viewing)<<'\t'<<window->getGuiStackSize()<<'\t'<<frame.selected<<'\t'<<frame.cameraView<<'\t'<<stats[4]<<'\t'<<counts[0]<<'\t'<<counts[1]<<'\t'<<inserted<<'\t'<<glGetError()<<'\n';driver.log.flush();
    if(ready&&!seeking)driver.number++;SDL_Delay(16);
}
