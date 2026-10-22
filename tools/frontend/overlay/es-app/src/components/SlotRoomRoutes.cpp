#include "SlotRoomRoutes.h"
#include "SlotThemeRoot.h"
#include "SlotHome.h"
#include "SlotRoomSession.h"
#include "SystemData.h"
#include "FileData.h"
#include "views/ViewController.h"
#include "views/gamelist/IGameListView.h"
namespace slot {
namespace {int directLaunches=0;}
bool roomDirectLaunch(){return directLaunches>0;}
RoomDirectLaunch::RoomDirectLaunch(){directLaunches++;}
RoomDirectLaunch::~RoomDirectLaunch(){directLaunches--;}

bool roomCollection(SystemData*collection,FileData*game){
    return collection&&collection->isCollection()&&roomOpenGame(collection,game);
}
bool roomOpenGame(SystemData*origin,FileData*game){
    if(!roomControls()||!game||game->getType()!=GAME)return false;
    auto*source=game->getSourceFileData();auto*system=source->getSystem();
    if(roomModel(system->getName()).empty())return false;
    if(origin&&origin->isCollection())roomSession().origin(origin->getName(),source->getPath(),system->getName());
    else roomSession().clearOrigin();
    auto view=ViewController::get()->getGameListView(system);view->setCursor(source);
    ViewController::get()->goToGameList(system,true);return true;
}
bool roomReturn(const std::string&system){
    auto&session=roomSession();if(!roomControls()||session.originTarget()!=system||session.originSystem().empty())return false;
    auto*collection=SystemData::getSystem(session.originSystem());
    if(!collection){session.clearOrigin();return false;}
    auto view=ViewController::get()->getGameListView(collection);
    if(auto*game=collection->getRootFolder()->FindByPath(session.originGame()))view->setCursor(game);
    session.clearOrigin();ViewController::get()->goToGameList(collection,true);return true;
}
}
