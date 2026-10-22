"""Replay the patched view's actual input method with Knulli's InputConfig.

Usage: python3 tools/frontend/tests/input.py /path/to/pinned/patched/frontend
No SDL window/device is needed. The list double models held repeat velocity.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

source=Path(sys.argv[1]).resolve()
repo=Path(__file__).resolve().parents[3]
view=(source/'es-app/src/views/gamelist/CarouselGameListView.cpp').read_text(errors='surrogateescape')
def method(signature):
    start=view.index(signature)
    brace=view.index('{',start);depth=1;end=brace+1
    while depth:
        depth+=(view[end]=='{')-(view[end]=='}');end+=1
    return view[start:end]
production=method('bool CarouselGameListView::input(')+'\n'+method('void CarouselGameListView::moveSlotCursor(')
harness=r'''
#include "InputConfig.h"
#include <cassert>
#include <iostream>
#include "SlotState.h"
#include "SlotSpatialNavigation.h"
namespace slot {bool roomReturn(const std::string&){return false;}}
struct Root {Root*getSystem(){return this;}std::string getName(){return "snes";}};
enum {GAME=1};
struct FileData {std::string path;int getType(){return GAME;}FileData* getSourceFileData(){return this;}const std::string& getPath(){return path;}};
struct List {
    int velocity=0,cursor=0,count=25;
    int size(){return count;}int getCursorIndex(){return cursor;}
    void setCursorIndex(int n){assert(n>=0&&n<count);cursor=n;}
    void resetSlotIdle() {}
    void stopScrolling(){velocity=0;}
    bool input(InputConfig* c,Input i) {
        if(!i.value){velocity=0;return true;}
        if(c->isMappedLike("left",i)){velocity=-1;cursor--;return true;}
        if(c->isMappedLike("right",i)){velocity=1;cursor++;return true;}
        return false;
    }
    void advance(){cursor+=velocity*10;}
};
struct Presentation {
    int inserted=0,ejected=0,pages=0,orbiting=0,cameraCycles=0;
    bool room=false,tv=false,controls=false;int next=slot_navigation::noTarget,entry=0,lastDirection=0,entryCount=0;
    bool roomControls(){return room;}bool tvSelected(){return tv;}bool tvControls(){return controls;}
    void controlTV(bool on){controls=on;}
    bool navigationReady(){return ready&&!open&&!state.launching();}
    int spatialSelection(int d){lastDirection=d;if(next==-2)tv=true;return next;}
    int spatialEdgeEntry(int,int count){entryCount=count;return std::min(entry,count-1);}
    void cycleCamera(){cameraCycles++;}
    bool table=false,ready=true;slot::State state;
    bool tableReady(){return ready;}
    void orbit(int direction){orbiting=direction;}
    bool open=false;int spinH=0,spinV=0,inspections=0;
    bool inspect(bool on){open=on;inspections+=on;return true;}
    bool inspecting(){return open;}
    bool inspectionOpen(){return open;}
    void spin(int h,int v){spinH=h;spinV=v;}
    bool hasTabletop(){return table;}
    bool hasScene(){return true;}
    void insert(FileData* g){inserted++;state.insert(g->getPath());} void eject(){ejected++;state.eject();}
    void page(int n){pages+=n;}
};
struct ISimpleGameListView {
    List mList;
    int backs=0;
    bool input(InputConfig* c,Input i){if(i.value&&c->isMappedTo(BUTTON_BACK,i))backs++;return mList.input(c,i);}
};
struct CarouselGameListView:ISimpleGameListView {
    Root root;Root*mRoot=&root;
    bool mSlotEnabled=true;int mSlotDirectionHeld=0,mSlotSpin[2]={0,0};Presentation mSlot;
    void updateHelpPrompts(){}
    bool mSlotFullCarousel=false,mSlotConfirmHeld=false,mSlotCarouselHeld=false;
    bool mSlotSelectHeld=false,mSlotSelectUsed=false;int mSlotSelectMs=0;
    bool mSlotBackHeld=false;int mSlotHeldAxes[2]={0,0},mSlotNavMs=0,mSlotNavRepeat=350;
    void toggleFavoritesFilter(){}
    int validatedLaunches=0;FileData current;
    FileData* getCursor(){current.path=std::to_string(mList.cursor);return &current;}
    void launchSelectedGame(){validatedLaunches++;mSlot.state.play(getCursor()->getPath());}
    bool input(InputConfig*,Input);
    void moveSlotCursor(int direction);
};
// PRODUCTION_INPUT
int main(){
    for(auto type:{TYPE_HAT,TYPE_AXIS,TYPE_KEY}) {
        InputConfig c(0,0,"test","test",10,1,2);
        const char* names[]={"left","right","up","down"};
        int hats[]={SDL_HAT_LEFT,SDL_HAT_RIGHT,SDL_HAT_UP,SDL_HAT_DOWN};
        for(int i=0;i<4;i++)c.mapInput(names[i],Input(0,type,type==TYPE_HAT?0:type==TYPE_AXIS?i/2:i,type==TYPE_HAT?hats[i]:type==TYPE_AXIS?(i%2?1:-1):1,true));
        c.mapInput("pageup",Input(0,TYPE_BUTTON,4,1,true));
        c.mapInput("pagedown",Input(0,TYPE_BUTTON,5,1,true));
        auto input=[&](int n,int value){return Input(0,type,type==TYPE_HAT?0:type==TYPE_AXIS?n/2:n,value?type==TYPE_HAT?hats[n]:type==TYPE_AXIS?(n%2?1:-1):1:0,true);};
        CarouselGameListView v;
        v.input(&c,input(1,1));assert(v.mList.velocity==1);
        v.input(&c,input(1,0));const int cursor=v.mList.cursor;
        v.mList.advance();assert(v.mList.cursor==cursor && v.mList.velocity==0);
        v.input(&c,input(0,1));v.input(&c,input(0,0));
        const int left=v.mList.cursor;v.mList.advance();assert(v.mList.cursor==left);
        v.input(&c,input(1,1));v.input(&c,input(3,1));
        assert(v.mList.velocity==0 && v.mSlot.inserted==1);
        v.input(&c,input(3,1));assert(v.mSlot.inserted==1);
        v.input(&c,input(3,0));v.input(&c,input(3,1));assert(v.mSlot.inserted==2);
        v.input(&c,input(3,0));v.input(&c,input(2,1));assert(v.mSlot.ejected==1);
        v.input(&c,input(2,0));
        v.input(&c,Input(0,TYPE_BUTTON,5,1,true));assert(v.mSlot.pages==1);
    }
    {
        InputConfig c(0,0,"tabletop","test",10,1,2);BUTTON_OK=(char*)"a";BUTTON_BACK=(char*)"b";
        c.mapInput("select",Input(0,TYPE_BUTTON,8,1,true));
        c.mapInput("a",Input(0,TYPE_BUTTON,0,1,true));c.mapInput("b",Input(0,TYPE_BUTTON,1,1,true));c.mapInput("r3",Input(0,TYPE_BUTTON,9,1,true));
        CarouselGameListView v;v.mSlot.table=true;
        v.mSlot.ready=false;
        v.input(&c,Input(0,TYPE_BUTTON,0,1,true));v.input(&c,Input(0,TYPE_BUTTON,0,0,true));
        assert(v.mSlot.inserted==0&&v.validatedLaunches==0);v.mSlot.ready=true;
        auto button=[&](int id,int value){v.input(&c,Input(0,TYPE_BUTTON,id,value,true));};
        button(8,1);button(9,1);button(9,1);assert(v.mSlot.cameraCycles==1&&!v.mSlotFullCarousel);button(9,0);button(8,0);
        assert(!v.mSlotSelectHeld&&v.mSlotSelectUsed);button(9,1);assert(v.mSlotFullCarousel);button(9,0);button(1,1);button(1,0);
        button(0,1);button(0,1);assert(v.mSlot.inserted==1&&v.validatedLaunches==0);button(0,0);
        for(int i=0;i<40;i++)v.mSlot.state.update(.05f);
        const auto loaded=v.mSlot.state.inserted();assert(loaded=="0");
        button(9,1);button(9,1);assert(v.mSlotFullCarousel&&v.mSlot.state.inserted()==loaded);button(9,0);
        button(1,1);assert(!v.mSlotFullCarousel&&v.mSlot.state.inserted()==loaded);button(1,0);
        v.mList.cursor=1;button(0,1);button(0,0);assert(v.mSlot.inserted==2&&v.validatedLaunches==0);
        for(int i=0;i<50;i++)v.mSlot.state.update(.05f);
        assert(v.mSlot.state.inserted()=="1");button(0,1);button(0,1);button(0,0);assert(v.validatedLaunches==1);
        v.mSlot.state.presentationDurations(.2f,.3f);assert(v.mSlot.state.takeLaunch().empty());assert(v.mSlot.state.preparing());
        button(1,1);button(1,0);assert(!v.mSlot.state.launching()&&v.mSlot.state.inserted()=="1"&&v.mSlot.state.takeLaunch().empty());
        // Right stick X orbits (left -1, right +1, neutral returns) without moving the list.
        c.mapInput("joystick2left",Input(0,TYPE_AXIS,2,-1,true));const int list=v.mList.cursor;
        v.input(&c,Input(0,TYPE_AXIS,2,1,true));assert(v.mSlot.orbiting==1);
        v.input(&c,Input(0,TYPE_AXIS,2,-1,true));assert(v.mSlot.orbiting==-1);
        v.input(&c,Input(0,TYPE_AXIS,2,0,true));assert(v.mSlot.orbiting==0&&v.mList.cursor==list);
        // L3 opens inspection; the hat turns the cart (both axes per event, neutral stops)
        // without browsing, inserting or ejecting; A is ignored; B puts it back.
        c.mapInput("l3",Input(0,TYPE_BUTTON,10,1,true));
        const char* dirs[]={"left","right","up","down"};int hats[]={SDL_HAT_LEFT,SDL_HAT_RIGHT,SDL_HAT_UP,SDL_HAT_DOWN};
        for(int i=0;i<4;i++)c.mapInput(dirs[i],Input(0,TYPE_HAT,0,hats[i],true));
        const int inserted=v.mSlot.inserted,ejected=v.mSlot.ejected,launches=v.validatedLaunches;
        button(10,1);button(10,0);assert(v.mSlot.open&&v.mSlot.inspections==1);
        v.input(&c,Input(0,TYPE_HAT,0,SDL_HAT_LEFT|SDL_HAT_UP,true));assert(v.mSlot.spinH==-1&&v.mSlot.spinV==-1);
        v.input(&c,Input(0,TYPE_HAT,0,SDL_HAT_RIGHT,true));assert(v.mSlot.spinH==1&&v.mSlot.spinV==0);
        v.input(&c,Input(0,TYPE_HAT,0,0,true));assert(v.mSlot.spinH==0&&v.mSlot.spinV==0);
        v.input(&c,Input(0,TYPE_HAT,0,SDL_HAT_DOWN,true));v.input(&c,Input(0,TYPE_HAT,0,0,true));
        button(0,1);button(0,0);
        assert(v.mList.cursor==list&&v.mSlot.inserted==inserted&&v.mSlot.ejected==ejected&&v.validatedLaunches==launches);
        button(1,1);button(1,0);assert(!v.mSlot.open);
        button(10,1);button(10,0);assert(v.mSlot.open);button(10,1);button(10,0);assert(!v.mSlot.open&&v.mSlot.inspections==2);
    }
    for(auto type:{TYPE_HAT,TYPE_AXIS,TYPE_KEY}) {
        InputConfig c(0,0,"room","test",10,1,2);BUTTON_OK=(char*)"a";BUTTON_BACK=(char*)"b";
        const char* names[]={"left","right","up","down"};int hats[]={SDL_HAT_LEFT,SDL_HAT_RIGHT,SDL_HAT_UP,SDL_HAT_DOWN};
        for(int i=0;i<4;i++)c.mapInput(names[i],Input(0,type,type==TYPE_HAT?0:type==TYPE_AXIS?i/2:i,type==TYPE_HAT?hats[i]:type==TYPE_AXIS?(i%2?1:-1):1,true));
        c.mapInput("a",Input(0,TYPE_BUTTON,0,1,true));c.mapInput("b",Input(0,TYPE_BUTTON,1,1,true));c.mapInput("r3",Input(0,TYPE_BUTTON,9,1,true));
        auto direction=[&](int n,int value){return Input(0,type,type==TYPE_HAT?0:type==TYPE_AXIS?n/2:n,value?type==TYPE_HAT?hats[n]:type==TYPE_AXIS?(n%2?1:-1):1:0,true);};
        CarouselGameListView v;v.mSlot.room=v.mSlot.table=true;v.mSlot.next=4;
        auto button=[&](int id,int value){v.input(&c,Input(0,TYPE_BUTTON,id,value,true));};
        const int directions[]={-1,1,-2,2};
        for(int n=0;n<4;n++){
            v.input(&c,direction(n,1));assert(v.mSlot.lastDirection==directions[n]&&v.mList.cursor==4);
            assert(v.mSlot.inserted==0&&v.mSlot.ejected==0&&v.mList.velocity==0);
            v.input(&c,direction(n,0));assert(v.mSlotDirectionHeld==0);
        }
        if(type!=TYPE_HAT){
            v.input(&c,direction(1,1));v.input(&c,direction(3,1));v.input(&c,direction(3,0));
            assert(v.mSlotDirectionHeld==1&&v.mSlotHeldAxes[0]==1);v.input(&c,direction(1,0));
        }
        // Final partial window enters a real slot; edge wrap returns to first window.
        v.mSlot.next=slot_navigation::noTarget;v.mSlot.entry=11;v.mList.cursor=23;
        v.input(&c,direction(1,1));v.input(&c,direction(1,0));assert(v.mList.cursor==24&&v.mSlot.entryCount==1);
        v.mSlot.entry=0;v.input(&c,direction(1,1));v.input(&c,direction(1,0));assert(v.mList.cursor==0);
        button(0,1);button(0,1);assert(v.mSlot.inserted==1&&v.validatedLaunches==0);button(0,0);
        for(int n=0;n<40;n++)v.mSlot.state.update(.05f);
        const auto loaded=v.mSlot.state.inserted();assert(loaded=="0");
        v.mSlot.next=-2;v.input(&c,direction(2,1));v.input(&c,direction(2,0));assert(v.mSlot.tvSelected());
        button(0,1);button(0,1);button(0,0);assert(v.mSlot.controls&&v.mSlot.state.inserted()==loaded&&v.validatedLaunches==0);
        button(1,1);button(1,1);assert(!v.mSlot.controls&&v.mSlot.ejected==0&&v.backs==0);button(1,0);
        button(9,1);button(9,1);button(9,0);assert(v.mSlot.cameraCycles==1&&!v.mSlotFullCarousel);
        v.mSlot.open=true;button(1,1);button(1,1);assert(!v.mSlot.open&&v.mSlot.ejected==0);button(1,0);
        button(1,1);button(1,1);button(1,0);assert(v.mSlot.ejected==1&&v.backs==0);
        for(int n=0;n<40;n++)v.mSlot.state.update(.05f);
        button(1,1);button(1,1);button(1,0);assert(v.backs==1);
        // A separate press on the loaded cartridge is still validated exactly once.
        v.mSlot.tv=false;button(0,1);button(0,0);for(int n=0;n<40;n++)v.mSlot.state.update(.05f);
        button(0,1);button(0,1);button(0,0);assert(v.validatedLaunches==1);
    }
    std::cout<<"Input: production view + Knulli hat/axis/key; legacy and room A/B/R3, spatial edges, TV focus and held buttons pass.\n";
}
'''.replace('// PRODUCTION_INPUT',production)
with tempfile.TemporaryDirectory(prefix='slot-input-') as temporary:
    test=Path(temporary)/'input.cpp';test.write_text(harness)
    executable=Path(temporary)/'input'
    subprocess.run(['g++','-std=c++14','-ffunction-sections','-fdata-sections',
        '-I'+str(source/'es-core/src'),'-I'+str(source/'es-app/src/components'),'-I'+str(source/'external'),
        '-I'+str(repo/'build/native/SDL-release-2.32.8/include'),
        str(test),str(source/'es-core/src/InputConfig.cpp'),str(source/'es-core/src/utils/StringUtil.cpp'),
        '-Wl,--gc-sections','-o',str(executable)],check=True)
    subprocess.run([str(executable)],check=True)
