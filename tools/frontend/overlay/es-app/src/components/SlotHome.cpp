#include "SlotHome.h"
#include "SlotPresentation.h"
#include "SlotRoomHost.h"
#include "SlotRoomTiming.h"
#include "SlotRoomSession.h"
#include "SlotSpatialNavigation.h"
#include "SystemData.h"
#include "FileData.h"
#include "Window.h"
#include "views/ViewController.h"
#include "views/gamelist/IGameListView.h"
#include "guis/GuiMenu.h"
#include "components/TextComponent.h"
#include "resources/Font.h"
#include "renderers/Renderer.h"
#include "Settings.h"
#include "ThemeData.h"
#include <set>
#include <algorithm>
#include <ctime>
#include "utils/StringUtil.h"

namespace slot {
std::string roomModel(const std::string&system){
    const auto key=system=="megadrive"||system=="genesis"?"md":system;
    static const std::set<std::string>models={"snes","n64","nes","md","psx","gb","gbc","gba","nds","psp","pico8"};
    return models.count(key)?key:"";
}
void Home::rebuild(const std::vector<SystemData*>&systems){
    std::string signature;for(auto*s:systems)signature+=s->getName()+"|";if(signature==mSignature)return;
    mSignature=signature;mConsoles.clear();mChannels.clear();mModels.clear();std::set<std::string>models;
    for(auto*s:systems){
        const auto model=s->isCollection()?"":roomModel(s->getName());
        if(model.empty())mChannels.push_back(s);
        else if(models.insert(model).second){mConsoles.push_back(s);mModels.push_back(model);}
    }
    const auto remembered=Settings::getInstance()->getString("SlottedHomeConsole");
    for(size_t i=0;i<mConsoles.size();i++)if(mConsoles[i]->getName()==remembered)mSelected=int(i);
    const auto channel=Settings::getInstance()->getString("SlottedHomeChannel");
    for(size_t i=0;i<mChannels.size();i++)if(mChannels[i]->getName()==channel)mChannel=int(i);
    mSelected=std::min(mSelected,std::max(0,int(mConsoles.size())-1));mChannel=std::min(mChannel,int(mChannels.size()));
    mTV=mConsoles.empty()||Settings::getInstance()->getString("SlottedHomeFocus")=="tv";
}
void Home::remember(){
    if(!mConsoles.empty()){roomSession().homeConsole(mConsoles[mSelected]->getName());Settings::getInstance()->setString("SlottedHomeConsole",mConsoles[mSelected]->getName());}
    if(mChannel<int(mChannels.size())){roomSession().homeChannel(mChannels[mChannel]->getName());Settings::getInstance()->setString("SlottedHomeChannel",mChannels[mChannel]->getName());}
    Settings::getInstance()->setString("SlottedHomeFocus",mTV?"tv":"console");Settings::getInstance()->saveFile();
}
void Home::show(){mScene=nullptr;mConfirmHeld=mBackHeld=mCameraHeld=false;mDirection=mAxes[0]=mAxes[1]=0;}
void Home::shuffle(){
    std::vector<SystemData*>games=mConsoles;for(auto*s:mChannels)if(!s->isCollection())games.push_back(s);
    mRandomSystem.clear();mRandomPath.clear();if(games.empty())return;
    // The engine chooses only games allowed by its current filters.
    const auto start=SDL_GetTicks()%games.size();
    for(size_t i=0;i<games.size();i++)if(auto*g=games[(start+i)%games.size()]->getRandomGame()){
        auto*source=g->getSourceFileData();mRandomSystem=source->getSystem()->getName();mRandomPath=source->getPath();break;
    }
}
void Home::move(int direction){
    if(!mScene||!slot_tabletop_ready(mScene))return;
    if(mControls){
        if(mRandom){mShuffle=direction<0;return;}
        if(direction==-2||direction==2)mChannel=(mChannel+(direction<0?-1:1)+int(mChannels.size())+1)%(int(mChannels.size())+1);
        return;
    }
    SlotTabletopFocus anchors[16];const int count=slot_tabletop_focus_points(mScene,anchors,16,mCamera);
    std::vector<slot_navigation::Point>points;for(int i=0;i<count;i++)points.push_back({anchors[i].item,anchors[i].x,anchors[i].y,true});
    const auto d=direction==-1?slot_navigation::Direction::Left:direction==1?slot_navigation::Direction::Right:direction==-2?slot_navigation::Direction::Up:slot_navigation::Direction::Down;
    const int next=slot_navigation::neighbor(points,mTV?-2:mSelected,d);
    if(next==-2)mTV=true;else if(next>=0&&next<int(mConsoles.size())){mTV=false;mSelected=next;}
}
void Home::update(int ms){
    if(!mDirection)return;mRepeatMs+=std::max(0,std::min(ms,100));
    if(mRepeatMs>=mRepeatAt){mRepeatMs=0;mRepeatAt=140;move(mDirection);}
}
bool Home::input(InputConfig*config,Input event,const std::vector<SystemData*>&systems){
    SlotRoomProbe probe("home-input");
    rebuild(systems);
    if(config->isMappedTo(BUTTON_OK,event)){
        if(!event.value)mConfirmHeld=false;
        else if(!mConfirmHeld){
            mConfirmHeld=true;if(!mScene||!slot_tabletop_ready(mScene))return true;
            if(!mControls){if(mTV)mControls=true;else if(!mConsoles.empty()){remember();roomSession().clearOrigin();ViewController::get()->goToGameList(mConsoles[mSelected],true);}}
            else if(mRandom){
                if(mShuffle)shuffle();else if(auto*system=SystemData::getSystem(mRandomSystem))if(auto*game=system->getRootFolder()->FindByPath(mRandomPath)){
                    roomSession().clearOrigin();auto view=ViewController::get()->getGameListView(system);view->setCursor(game);ViewController::get()->goToGameList(system,true);
                }
            }else if(mChannel==int(mChannels.size())){mRandom=true;mShuffle=true;shuffle();}
            else{remember();ViewController::get()->goToGameList(mChannels[mChannel],true);}
        }return true;
    }
    if(config->isMappedTo(BUTTON_BACK,event)){
        if(!event.value)mBackHeld=false;
        else if(!mBackHeld){mBackHeld=true;if(mRandom)mRandom=false;else mControls=false;mDirection=mAxes[0]=mAxes[1]=0;remember();}return true;
    }
    if(config->isMappedTo("r3",event)){
        if(!event.value)mCameraHeld=false;else if(!mCameraHeld){mCameraHeld=true;if(mScene&&slot_tabletop_ready(mScene)){mCamera=(mCamera+1)%4;mControls=mRandom=false;}}return true;
    }
    const bool left=config->isMappedLike("left",event),right=config->isMappedLike("right",event),up=config->isMappedLike("up",event),down=config->isMappedLike("down",event);
    if(left||right||up||down){
        if(event.type==TYPE_HAT){mAxes[0]=!event.value?0:left?-1:right?1:0;mAxes[1]=!event.value?0:up?-2:down?2:0;}
        else{if(left||right)mAxes[0]=!event.value?0:left?-1:1;if(up||down)mAxes[1]=!event.value?0:up?-2:2;}
        const int direction=event.value?(left||right?mAxes[0]:mAxes[1]):mAxes[0]?mAxes[0]:mAxes[1];
        if(direction!=mDirection){mDirection=direction;mRepeatMs=0;mRepeatAt=350;if(direction)move(direction);}return true;
    }
    if(config->isMappedTo("select",event)){if(event.value)GuiMenu::openQuitMenu_static(mWindow,true);return true;}
    return true;
}
void Home::render(const std::vector<SystemData*>&systems){
    rebuild(systems);std::vector<SlotTabletopItem>items;
    for(size_t i=0;i<mConsoles.size();i++)items.push_back({mConsoles[i]->getName().c_str(),mModels[i].c_str(),""});
    mScene=SlotPresentation::homeTable(items);if(!mScene)return;
    char clock[6]="--:--";std::time_t now=std::time(nullptr);if(auto*local=std::localtime(&now))std::strftime(clock,sizeof(clock),"%H:%M",local);
    const auto status=roomStatus();slot_tabletop_status(mScene,status.battery,status.charging,status.connected,clock);
    SlotTabletopFrame frame;frame.selected=mTV?-2:mSelected;frame.cameraView=mControls?5:mCamera;frame.automatic=false;roomQueue(mScene,frame,mControls,true);
    const auto skin=ThemeData::getMenuTheme();
    auto drawRow=[&](int kind,const std::string&value,float y,float height,const std::shared_ptr<Font>&font,unsigned color){
        auto&row=mTextRows[{kind,int(y)}];
        if(!row)row=std::make_shared<TextComponent>(mWindow,value,font,color);
        row->setFont(font);row->setColor(color);row->setText(value);row->setPosition(28,y);
        if(row->getSize()!=Vector2f(584,height))row->setSize(584,height);
        row->render(Transform4x4f::Identity());
    };
    auto text=[&](const std::string&label,float y,bool selected=false){
        if(selected){Renderer::setMatrix(Transform4x4f::Identity());Renderer::drawRect(22,y,596,38,skin->Text.selectorColor);}
        drawRow(1,label,y,40,skin->Text.font?skin->Text.font:Font::get(FONT_SIZE_MEDIUM),selected?skin->Text.selectedColor:skin->Text.color);
    };
    Renderer::setMatrix(Transform4x4f::Identity());Renderer::drawRect(0,0,640,480,skin->Background.centerColor);
    if(!mControls){
        auto card=[&](const std::string&value,float y,int size,float height){
            const auto path=skin->Text.font?skin->Text.font->getPath():Font::getDefaultPath();
            auto&font=mCardFonts[{size,path}];if(!font)font=Font::get(size,path);
            drawRow(size,value,y,height,font,skin->Text.color);
        };
        if(mTV){card("TV",42,96,115);card("A  CHANNELS",330,32,60);}
        else if(!mConsoles.empty()){
            auto*system=mConsoles[mSelected];card(Utils::String::toUpper(mModels[mSelected]),36,80,115);
            card(system->getFullName(),160,24,75);card(std::to_string(system->getGameCount())+" GAMES",250,44,70);card("A  OPEN CONSOLE",368,28,60);
        }
        return;
    }
    text(mRandom?"RANDOM":"CHANNELS",24);
    if(mRandom){
        auto*system=SystemData::getSystem(mRandomSystem);auto*game=system?system->getRootFolder()->FindByPath(mRandomPath):nullptr;
        text(game?game->getName():"No games available",112);text(mShuffle?"> SHUFFLE":"  SHUFFLE",250,mShuffle);text(!mShuffle?"> OPEN":"  OPEN",310,!mShuffle);
    }else{
        const int first=std::max(0,mChannel-6);
        for(int row=0;row<8&&row+first<=int(mChannels.size());row++){const int i=row+first;text((i==mChannel?"> ":"  ")+(i==int(mChannels.size())?std::string("Random"):mChannels[i]->getFullName()),88+row*40,i==mChannel);}
    }
}
}
