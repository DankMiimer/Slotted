// The system selector shares the same native scene as cartridge browsing (MIT).
#pragma once
#include "SlotTabletop.h"
#include "InputConfig.h"
#include <string>
#include <vector>
#include <map>
#include <memory>
class Window;class SystemData;class TextComponent;class Font;
namespace slot {
std::string roomModel(const std::string&system);
class Home {
public:
    explicit Home(Window*window):mWindow(window){}
    bool input(InputConfig*config,Input event,const std::vector<SystemData*>&systems);
    void render(const std::vector<SystemData*>&systems);
    void update(int ms);
    void show();
private:
    void rebuild(const std::vector<SystemData*>&systems);
    void move(int direction);
    void remember();
    void shuffle();
    Window*mWindow;SlotTabletop*mScene=nullptr;
    std::vector<SystemData*>mConsoles,mChannels;std::vector<std::string>mModels;
    std::string mSignature;int mSelected=0,mChannel=0,mCamera=0,mAxes[2]={0,0},mDirection=0,mRepeatMs=0,mRepeatAt=350;
    bool mTV=false,mControls=false,mConfirmHeld=false,mBackHeld=false,mCameraHeld=false,mRandom=false,mShuffle=true;
    std::string mRandomSystem,mRandomPath;
    // Font::get keeps weak references. Retain the rows and their font atlases
    // rather than creating/uploading the large system-card fonts every frame.
    std::map<std::pair<int,int>,std::shared_ptr<TextComponent>>mTextRows;
    std::map<std::pair<int,std::string>,std::shared_ptr<Font>>mCardFonts;
};
}
