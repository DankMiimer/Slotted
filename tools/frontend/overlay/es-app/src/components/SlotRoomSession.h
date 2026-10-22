// Logical room ownership outlives gamelist views and native graphics (MIT).
#pragma once
#include "SlotState.h"
#include <map>
#include <string>

namespace slot {
struct RoomConsole {
    State media;
    std::string selected;
    int loadedHome=0;
};
class RoomSession {
public:
    // Map nodes are never erased while views hold references to their media.
    RoomConsole& console(const std::string&system){return mConsoles[system];}
    void leave(const std::string&system,const std::string&selected,int home){
        auto&c=console(system);c.media.park();c.selected=selected;
        if(home>=0&&home<12)c.loadedHome=home;
    }
    void invalidate(std::string game){for(auto&entry:mConsoles)entry.second.media.invalidate(game);}
    void homeConsole(const std::string&system){mHomeConsole=system;mHomeChannels=false;}
    void homeChannel(const std::string&channel){mHomeChannel=channel;mHomeChannels=true;}
    const std::string& homeConsole()const{return mHomeConsole;}
    const std::string& homeChannel()const{return mHomeChannel;}
    bool homeChannels()const{return mHomeChannels;}
    void origin(const std::string&system,const std::string&game,const std::string&target){mOriginSystem=system;mOriginGame=game;mOriginTarget=target;}
    void clearOrigin(){mOriginSystem.clear();mOriginGame.clear();mOriginTarget.clear();}
    const std::string& originSystem()const{return mOriginSystem;}
    const std::string& originGame()const{return mOriginGame;}
    const std::string& originTarget()const{return mOriginTarget;}
private:
    std::map<std::string,RoomConsole> mConsoles;
    std::string mHomeConsole,mHomeChannel;bool mHomeChannels=false;
    std::string mOriginSystem,mOriginGame,mOriginTarget;
};
inline RoomSession& roomSession(){static RoomSession session;return session;}
}
