#include "SlotPresentation.h"
#include "SlotScreens.h"
#include "SlotTelevision.h"
#include "SlotMetadataLayout.h"
#include "SlotMetadataPages.h"
#include "SlotScenePreview.h"
#include "SlotHomeLayout.h"
#include "SlotThemeRoot.h"
#include "SlotRoomSession.h"
#include "SlotRoomHost.h"
#include "SlotRoomTiming.h"
#include "FileData.h"
#include "SystemData.h"
#include "Settings.h"
#include "Sound.h"
#include "Log.h"
#include "resources/Font.h"
#include "renderers/Renderer.h"
#include "utils/FileSystemUtil.h"
#include "utils/StringUtil.h"
#include <GLES2/gl2.h>
#include <cmath>
#include <set>
#include <sstream>
#include <ctime>

namespace {
SlotTabletop* sharedTable=nullptr;std::string sharedTableRoot,sharedSceneKey;bool sharedRoom=false;
// A TV option whose prepared 3D cabinet is not installed (the Retro TV's CC BY-NC model is
// kept local) uses the Panasonic, as unknown TV values already do, instead of failing to
// open the room on every frame. Checked once per root and TV.
std::string installedTelevision(const std::string&root,const std::string&tv){
    static std::map<std::string,bool> installed;
    auto found=installed.find(root+"|"+tv);
    if(found==installed.end()){
        found=installed.emplace(root+"|"+tv,Utils::FileSystem::exists(root+"/"+tv+"/scene.txt")).first;
        if(!found->second)LOG(LogWarning)<<"Slotted: no 3D model for TV '"<<tv<<"' in "<<root<<"; using panasonic";
    }
    return found->second||tv=="panasonic"?tv:std::string("panasonic");
}
std::string first(const std::vector<std::string>& paths) {
    for(const auto& path:paths)if(!path.empty() && Utils::FileSystem::exists(path))return path;
    return {};
}
std::string modelFor(const std::string& system,const std::string& path) {
    std::string model=system;
    if(model=="genesis" || model=="megadrive")model="md";
    if(model=="gbh" || model=="gbch" || model=="gbah" || model=="snesh" || model=="nesh" || model=="n64h")model.pop_back();
    const auto upper=Utils::String::toUpper(path);
    if(model=="snes" && (upper.find("(USA")!=std::string::npos || upper.find("(CANADA")!=std::string::npos))return "snes-us";
    if(model=="md" && upper.find("JAPAN")!=std::string::npos && upper.find("USA")==std::string::npos && upper.find("EUROPE")==std::string::npos)return "md-jp";
    return model;
}
std::string style() {return !slot::scenePreviewActive() && Settings::getInstance()->getString("subset.slot-model-style")=="cel"?"cel":"realistic";}
std::string cartridgeChoice(){return !slot::scenePreviewActive() && Settings::getInstance()->getString("subset.slot-snes-cartridge-model")=="tzakol"?"tzakol":"regional";}
// Theme setting "slot-gba-sp-model": NeilVFX (local file, default) or the packaged thegraphicsgeek SP.
std::string gbaSpChoice(){return !slot::scenePreviewActive() && Settings::getInstance()->getString("subset.slot-gba-sp-model")=="graphicsgeek"?"graphicsgeek":"neilvfx";}
std::string cartridgeFace(const std::string& path,const std::string& model){
    const auto stem=Utils::FileSystem::getStem(path),directory=Utils::FileSystem::getParent(path);
    if((model=="snes"||model=="snes-us")&&cartridgeChoice()=="tzakol")
        return first({directory+"/media/slotcarts/"+stem+".tzakol.png",slot::assetRoot()+"shells/snes-tzakol.png"});
    return first({directory+"/media/slotcarts/"+stem+".png",slot::assetRoot()+"shells/"+model+".png"});
}
std::string colour() {
    if(slot::scenePreviewActive())return "original";
    const auto value=Settings::getInstance()->getString("subset.slot-console-color");
    const std::set<std::string> allowed={"black","white","red","blue","purple","green","yellow"};
    return allowed.count(value)?value:"original";
}
// Theme setting "slot-tv-model"; the first profile is the default/fallback.
const SlotTelevisionProfile* televisionProfile() {
    const std::string value=slot::scenePreviewActive()?slot::scenePreviewTV():Settings::getInstance()->getString("subset.slot-tv-model");
    for(const auto& tv:slotTelevisions)if(value==tv.id && Utils::FileSystem::exists(slot::assetRoot()+tv.image))return &tv;
    return &slotTelevisions[0];
}
const SlotScreenSpec* screenFor(const std::string& model) {
    for(const auto& screen:slotScreens)if(model==screen.name)return &screen;
    return nullptr;
}
std::string titleLines(Font* font,const std::string& text,float width) {
    // At most two lines, each guaranteed to fit: a greedy word wrap whose limit is a few pixels inside the
    // text box (so TextComponent never wraps it again), an over-long line ellipsised at a whole character.
    const float limit=width-4;
    auto fits=[&](const std::string& line){return font->sizeText(line).x()<=limit;};
    auto clip=[&](std::string line){
        if(fits(line))return line;
        while(!line.empty()){
            do line.pop_back();while(!line.empty() && (static_cast<unsigned char>(line.back())&0xC0)==0x80);
            if(!line.empty() && line.back()==' ')continue;
            if(fits(line+"…"))return line+"…";
        }
        return std::string("…");
    };
    std::vector<std::string> lines;std::string current;
    std::istringstream words(text);std::string word;
    while(words>>word) {
        const std::string trial=current.empty()?word:current+" "+word;
        if(current.empty() || fits(trial))current=trial;
        else{lines.push_back(current);current=word;}
    }
    if(!current.empty())lines.push_back(current);
    if(lines.empty())return {};
    if(lines.size()>2) {
        std::string rest;for(size_t i=1;i<lines.size();i++)rest+=(i>1?" ":"")+lines[i];
        lines.resize(2);lines[1]=rest+"…";
    }
    std::string header=clip(lines[0]);
    if(lines.size()>1)header+="\n"+clip(lines[1]);
    return header;
}
void texture(unsigned id,float x,float y,float w,float h,float u=1,float v=1,bool invert=false,unsigned alpha=255) {
    if(!id || w<=0 || h<=0)return;
    const unsigned c=Renderer::convertColor(0xFFFFFF00|alpha);
    const float top=invert?1:0,bottom=invert?1-v:v;
    Renderer::Vertex q[]={{{x,y},{0,top},c},{{x,y+h},{0,bottom},c},{{x+w,y},{u,top},c},{{x+w,y+h},{u,bottom},c}};
    Renderer::bindTexture(id);Renderer::drawTriangleStrips(q,4);
}
void lcd(unsigned id,const float* q,const Vector3f& position,const Vector2f& size,float u,float v) {
    if(!id)return;
    auto point=[&](float a,float b) {
        return Vector2f(position.x()+size.x()*((1-b)*((1-a)*q[0]+a*q[2])+b*((1-a)*q[6]+a*q[4])),
                        position.y()+size.y()*((1-b)*((1-a)*q[1]+a*q[3])+b*((1-a)*q[7]+a*q[5])));
    };
    Renderer::bindTexture(id);
    for(int row=0;row<12;row++) {
        std::vector<Renderer::Vertex> strip;
        for(int x=0;x<=12;x++)for(int dy=0;dy<2;dy++) {
            float a=x/12.f,b=(row+dy)/12.f;
            strip.emplace_back(point(a,b),Vector2f(a*u,1-b*v),0xFFFFFFFF);
        }
        Renderer::drawTriangleStrips(strip.data(),strip.size());
    }
}
std::string timePlayed(const std::string& raw) {
    long seconds=0;try {seconds=std::stol(raw);}catch(...){}
    if(seconds<60)return std::to_string(std::max(0L,seconds))+" sec";
    if(seconds<3600)return std::to_string(seconds/60)+" min";
    return std::to_string(seconds/3600)+" hr "+std::to_string((seconds%3600)/60)+" min";
}
}

SlotPresentation::SlotPresentation(Window* window,const std::string& system):GuiComponent(window),
    mRoomControls(slot::roomControls()),mRoomSystem(modelFor(system,"")),mRoomSourceSystem(system),
    state(mRoomControls?slot::roomSession().console(mRoomSystem).media:mLocalState),mArtwork(window,true),mConsole(window,true),mTelevision(window,true),
    mShadow(window,true),mFloorGlow(window,true),mVideo(window),mTitle(window),mText(window),mHud(window),mFooter(window) {
    SlotRoomProbe probe("pres-construct");
    setSize(720,mRoomControls?Renderer::slotOutputHeight():480);setDefaultZIndex(15);setZIndex(15);
    for(auto* text:{&mText,&mHud,&mFooter}) {text->setColor(0xE5E1D5FF);text->setVerticalAlignment(ALIGN_TOP);text->setLineSpacing(1.12f);}
    {SlotRoomProbe typeProbe("pres-ctor-type");applyType(1);}
    mHud.setColor(0xAAD8BCFF);
    mTitle.setColor(0xF6F4EFFF);mTitle.setVerticalAlignment(ALIGN_TOP);mTitle.setLineSpacing(1.05f);
    mTitle.setMultiLine(TextComponent::MULTILINE);
    mConsole.setPosition(20,206);mConsole.setMaxSize(300,264);
    mTelevision.setAllowFading(false);{SlotRoomProbe tvProbe("pres-ctor-tv");applyTelevision();}
    for(auto* image:{&mShadow,&mFloorGlow}){image->setAllowFading(false);image->setOrigin(.5,.5);}
    if(!mRoomControls){SlotRoomProbe stageProbe("pres-ctor-stage");loadStage();}
    mArtwork.setOrigin(.5,.5);mArtwork.setAllowFading(false);
    mVideo.setOrigin(.5,.5);mVideo.setPlayAudio(false);mVideo.setStartDelay(0);mVideo.setEffect(VideoVlcFlags::NONE);
    addChild(&mVideo);mVideo.onHide();
}
SlotPresentation::~SlotPresentation(){releaseGraphics();}

// Type sizes for the metadata surface; a TV glass much smaller than the Panasonic's uses a compact set.
void SlotPresentation::preloadType() {
    // Font::get keeps weak references, so these stay held for the process.
    static std::vector<std::shared_ptr<Font>> held;if(!held.empty())return;
    const float scale=1,fonts=Renderer::ScreenSettings::fontScale();
    held={Font::get(20*scale/fonts,slot::assetRoot()+"fonts/OpenSans-Regular.ttf"),Font::get(18*scale/fonts,slot::assetRoot()+"fonts/OpenSans-SemiBold.ttf"),
          Font::get(16*scale/fonts,slot::assetRoot()+"fonts/OpenSans-Regular.ttf"),Font::get(21*scale/fonts,slot::assetRoot()+"fonts/OpenSans-SemiBold.ttf")};
}
void SlotPresentation::applyType(float scale) {
    const float fonts=Renderer::ScreenSettings::fontScale();
    mTypeScale=scale;
    mFont=Font::get(20*scale/fonts,slot::assetRoot()+"fonts/OpenSans-Regular.ttf");
    mText.setFont(mFont);
    mHud.setFont(Font::get(18*scale/fonts,slot::assetRoot()+"fonts/OpenSans-SemiBold.ttf"));
    mFooter.setFont(Font::get(16*scale/fonts,slot::assetRoot()+"fonts/OpenSans-Regular.ttf"));
    mTitle.setFont(Font::get(21*scale/fonts,slot::assetRoot()+"fonts/OpenSans-SemiBold.ttf"));
}

void SlotPresentation::applyTelevision() {
    const auto* tv=televisionProfile();
    if(tv==mTV)return;
    mTV=tv;
    // Each cabinet is a render at the scene's standard view angle at its own size; prepareGeometry
    // places its floor point on the console's floor line.
    if(mStageLoaded)mTelevision.setImage(slot::assetRoot()+tv->image);
    mTelevision.setResize(tv->display[0],tv->display[1]);
    mTelevision.setPosition(720-tv->display[0]-4,120);
    mBoundsReady=false;mScreenDirty=true;
}
void SlotPresentation::loadStage() {
    mStageLoaded=true;mDirty=true; // the next update sets the console image
    mShadow.setImage(slot::assetRoot()+"stage/shadow.png");mFloorGlow.setImage(slot::assetRoot()+"stage/floor.png");
    if(mTV){mTelevision.setImage(slot::assetRoot()+mTV->image);mTelevision.setResize(mTV->display[0],mTV->display[1]);}
}

std::string SlotPresentation::browseImage(FileData* game) {
    if(!game)return {};
    auto* source=game->getSourceFileData();
    const auto model=modelFor(source->getSystem()->getName(),source->getPath());
    const auto local=slot::assetRoot()+"local-models/consoles/"+model+"/"+style()+"/"+colour()+"/browse.png";
    if(Utils::FileSystem::exists(local)&&!(model=="gba"&&gbaSpChoice()=="graphicsgeek"))return local;
    return slot::assetRoot()+"stage/"+style()+"/"+colour()+"/browse-console-"+model+".png";
}

SlotPresentation::Game SlotPresentation::capture(FileData* game) {
    Game result;if(!game || game->getType()!=GAME)return result;
    auto* source=game->getSourceFileData();
    result.id=source->getPath();result.name=source->getName();result.system=source->getSystem()->getName();
    result.model=modelFor(result.system,result.id);
    result.face=cartridgeFace(result.id,result.model);
    result.cover=first({source->getMetadata(MetaDataId::BoxArt),source->getMetadata(MetaDataId::Thumbnail),source->getMetadata(MetaDataId::TitleShot),source->getMetadata(MetaDataId::Image),result.face});
    result.video=first({source->getMetadata(MetaDataId::Video)});
    result.description=source->getMetadata(MetaDataId::Desc);
    std::ostringstream facts;
    const auto released=source->getMetadata(MetaDataId::ReleaseDate);
    const auto players=source->getMetadata(MetaDataId::Players);
    result.hud=players.empty() || players=="unknown"?"Players: ?":"Players: "+players;
    if(released.size()>=4 && released.substr(0,4)!="0000" && released!="not-a-date-time")result.hud+="   "+released.substr(0,4);
    if(released.size()>=4 && released.substr(0,4)!="0000" && released!="not-a-date-time")facts<<"Released: "<<released.substr(0,4)<<"\n";
    for(const auto& field:std::vector<std::pair<MetaDataId,std::string>>{{MetaDataId::Genre,""},{MetaDataId::Players,"Players: "},{MetaDataId::Developer,"Developer: "},{MetaDataId::Publisher,"Publisher: "},{MetaDataId::Region,"Region: "},{MetaDataId::Language,"Language: "}}) {
        const auto value=source->getMetadata(field.first);
        if(!value.empty() && Utils::String::toLower(value)!="unknown")facts<<field.second<<value<<"\n";
    }
    try {float rating=std::stof(source->getMetadata(MetaDataId::Rating));if(rating>0)facts<<"Rating: "<<std::lround(100*rating)<<"%\n";}catch(...){}
    result.facts=facts.str();
    result.library="Play count: "+source->getMetadata(MetaDataId::PlayCount)+"\nPlay time: "+timePlayed(source->getMetadata(MetaDataId::GameTime));
    const auto last=source->getMetadata(MetaDataId::LastPlayed);
    if(last.size()>=8 && last.substr(0,4)!="0000" && last!="not-a-date-time")result.library+="\nLast played: "+last.substr(0,4)+"-"+last.substr(4,2)+"-"+last.substr(6,2);
    if(source->getFavorite())result.library+="\nFavorite";
    if(!first({source->getMetadata(MetaDataId::Manual)}).empty())result.library+="\nManual available in game options";
    result.library+="\nFile: "+Utils::FileSystem::getFileName(result.id);
    std::set<std::string> unique={result.cover};
    for(const auto& field:std::vector<std::pair<MetaDataId,std::string>>{{MetaDataId::TitleShot,"Title screen"},{MetaDataId::Image,"Screenshot"},{MetaDataId::BoxBack,"Box back"},{MetaDataId::FanArt,"Artwork"},{MetaDataId::Map,"Map"},{MetaDataId::Cartridge,"Cartridge"},{MetaDataId::Marquee,"Logo"}}) {
        const auto path=first({source->getMetadata(field.first)});
        if(!path.empty() && unique.insert(path).second)result.gallery.emplace_back(field.second,path);
    }
    return result;
}
// Tabletop shell for a game: the Tzakol SNES choice, or the per-game Mega Drive variant
// the shelf baker marks beside the cart face (tools/themebuild/video.py).
static std::string tableMedia(const std::string& id,const std::string& model){
    if(model=="snes"||model=="snes-us")return cartridgeChoice()=="tzakol"?model+"-tzakol":model;
    if(model=="md"||model=="md-jp"){
        const auto marker=Utils::FileSystem::getParent(id)+"/media/slotcarts/"+Utils::FileSystem::getStem(id)+".slot-profile-";
        if(Utils::FileSystem::exists(marker+"md-ea"))return "md-ea";
        if(Utils::FileSystem::exists(marker+"md-jp"))return "md-jp";
    }
    return model;
}
// Tabletop label art: a PlayStation disc carries the baked circular disc print
// (media/slotcarts/STEM.disc.png, as the standalone helper's .disc.tga) on its top face.
static std::string tableFace(const std::string& id,const std::string& model,const std::string& face){
    if(model!="psx")return face;
    return first({Utils::FileSystem::getParent(id)+"/media/slotcarts/"+Utils::FileSystem::getStem(id)+".disc.png",slot::assetRoot()+"shells/psx.disc.png"});
}
// Tabletop insert/eject durations: the NES adds an approach, slide and press; the PSP its cover.
static float tableInsertSeconds(const std::string& system){return system=="nes"||system=="psp"?1.6f:1.15f;}
static float tableEjectSeconds(const std::string& system){return system=="nes"||system=="psp"?1.3f:.95f;}
void SlotPresentation::browse(const std::vector<FileData*>& games,FileData* selected) {
    const char* overrideRoot=getenv("SLOT_TABLETOP_ASSETS");mTableRoot=overrideRoot?overrideRoot:slot::assetRoot()+"tabletop";
    Game cursor=capture(selected);if(cursor.id!=mTableSelected)mTableTVSelected=mTableTVControls=false;mTableSelected=cursor.id;
    // Consoles and handhelds with tabletop registrations (top/front loaders, the PlayStation,
    // the slide-in handhelds); those without an authored profile share the SNES layout.
    // Power controls are optional (the PlayStation's button is merged into its controls part).
    static const std::set<std::string> tabled={"snes","n64","nes","psx","md","gb","gbc","gba","nds","psp","pico8"};
    const auto tableModel=modelFor(cursor.system,"");mTableSystem=tabled.count(tableModel)?tableModel:"";
    mTableAvailable=!mTableSystem.empty()
        && (mRoomControls||(style()=="realistic"&&colour()=="original"))
        && Utils::FileSystem::exists(mTableRoot+"/table/scene.txt")
        && Utils::FileSystem::exists(mTableRoot+"/"+installedTelevision(mTableRoot,mTV->id)+"/scene.txt")
        && !slot_scene::sceneProfileFor(mTableRoot+"/layouts",mTableSystem,mTV->id).path.empty();
    mTableGames.clear();mTableOffsets.clear();int offset=0;
    for(auto* file:games){Game g=capture(file);const int source=offset++;if(g.id.empty())continue;mTableGames.push_back(g);mTableOffsets.push_back(source);if(mTableGames.size()==12)break;}
    if(mRoomControls&&!state.inserted().empty()&&!mTableHomes.count(state.inserted()))mTableHomes[state.inserted()]=slot::roomSession().console(mRoomSystem).loadedHome;
    for(size_t i=0;i<mTableGames.size();i++){
        const auto&id=mTableGames[i].id;
        if(!mTableHomes.count(id)||(id!=state.target()&&id!=state.inserted()&&id!=state.desired()))mTableHomes[id]=i;
    }
    for(auto it=mTableHomes.begin();it!=mTableHomes.end();){
        bool keep=it->first==state.target()||it->first==state.inserted()||it->first==state.desired();
        for(auto&g:mTableGames)keep|=g.id==it->first;
        if(!keep)it=mTableHomes.erase(it);else ++it;
    }
    restoreRoomMedia();mTableDirty=true;
}
bool SlotPresentation::tabletop(const Transform4x4f& trans){
    const auto authored=slot_scene::sceneProfileFor(mTableRoot+"/layouts",mTableSystem,mTV->id);
    const bool explicitTV=slot::scenePreviewActive()&&modelFor(slot::scenePreviewSystem(),"")==mTableSystem;
    const std::string tv=installedTelevision(mTableRoot,explicitTV?mTV->id:authored.tv.empty()?mTV->id:authored.tv);
    const std::string key=mTableRoot+"|"+mTableSystem+"|"+tv+"|"+style()+"|"+colour()+"|"+gbaSpChoice();
    const bool changed=key!=mTableId;bool opened=false;
    if(sharedTable&&(sharedTableRoot!=mTableRoot||sharedRoom!=mRoomControls))shutdownTabletop();
    if(!sharedTable){
        SlotRoomProbe probe("tt-open");
        setenv("SLOT_GBA_SP",gbaSpChoice().c_str(),1);sharedTable=slot_tabletop_open(Renderer::getSDLWindow(),slot::assetRoot().c_str(),mTableRoot.c_str(),mTableSystem.c_str(),tv.c_str(),style()=="cel",colour().c_str(),mRoomControls?Renderer::getWindowWidth():720,mRoomControls?Renderer::slotOutputHeight():480);
        if(sharedTable&&mRoomControls){SlotRoomProbe worldProbe("tt-world");const auto world=mTableRoot+"/layouts/room.world";if(!slot_tabletop_world(sharedTable,Utils::FileSystem::exists(world)?world.c_str():nullptr)){slot_tabletop_close(sharedTable);sharedTable=nullptr;}}
        sharedTableRoot=mTableRoot;sharedRoom=mRoomControls;opened=true;
    }
    mTable=sharedTable;if(!mTable){mTableAvailable=false;return false;}
    if(mRoomControls)slot_tabletop_appearance(mTable,style()=="cel",colour().c_str());
    if(changed){mTableId=key;mTableResident="@";mTableDirty=true;mCameraView=-1;mScreenWidth=480;mScreenHeight=360;prepareText();mScreenDirty=true;}
    auto model=[](const Game&g){return tableMedia(g.id,g.model);};
    if(mTableDirty){
        std::vector<SlotTabletopItem> items;std::vector<std::string> models,faces;
        for(auto&g:mTableGames){models.push_back(model(g));faces.push_back(tableFace(g.id,g.model,g.face));}
        for(size_t i=0;i<mTableGames.size();i++){auto&g=mTableGames[i];items.push_back({g.id.c_str(),models[i].c_str(),faces[i].c_str()});}
        bool ok;
        if(opened){{SlotRoomProbe probe("tt-items-sync");ok=slot_tabletop_items(mTable,items.data(),items.size());}if(ok){SlotRoomProbe probe("tt-stream-start");ok=slot_tabletop_stream_start(mTable);}}
        else{SlotRoomProbe probe("tt-request");ok=slot_tabletop_request(mTable,mTableSystem.c_str(),tv.c_str(),gbaSpChoice().c_str(),items.data(),items.size());}
        if(!ok){mTableAvailable=false;return false;}mTableDirty=false;mTableFailureLogged=false;
        if(mRoomControls){sharedSceneKey=key;mTableResident="@";}
        if(changed&&!mTableGames.empty()){
            auto*current=SystemData::getSystem(mTableGames.front().system);
            if(current)for(auto*next:{current->getNext(),current->getPrev()}){
                if(!next)continue;
                const auto model=modelFor(next->getName(),"");const auto profile=slot_scene::sceneProfileFor(mTableRoot+"/layouts",model,mTV->id);
                static const std::set<std::string> supported={"snes","nes","n64","md","psx","gb","gbc","gba","nds","psp","pico8"};
                const bool previewTV=slot::scenePreviewActive()&&modelFor(slot::scenePreviewSystem(),"")==model;
                if(supported.count(model)&&!profile.path.empty())slot_tabletop_prefetch(mTable,model.c_str(),(previewTV?std::string(mTV->id):profile.tv).c_str(),gbaSpChoice().c_str());
            }
            // A fresh stream (the open after a game) has no home core: B then held the lifted
            // console ~3 s while the home room prepared (aq/at). Queue it after the neighbours;
            // from then on the home core stays cached as the protected hub.
            if(opened&&mRoomControls)slot_tabletop_prefetch(mTable,"home",installedTelevision(mTableRoot,televisionProfile()->id).c_str(),gbaSpChoice().c_str());
        }
    }
    if(slot_tabletop_stream_failed(mTable)){
        if(mRoomControls){if(!mTableFailureLogged)LOG(LogWarning)<<"Slotted destination failed; retaining the live room";mTableFailureLogged=true;}
        else{LOG(LogWarning)<<"Slot scene preparation failed; retaining ordinary frontend fallback";mTableAvailable=false;return false;}
    }
    const bool ready=slot_tabletop_ready(mTable);
    const auto& active=state.busy()?state.target():state.inserted();
    if(ready&&active!=mTableResident){
        if(active.empty())slot_tabletop_resident(mTable,nullptr,0);
        else{
            Game g=mSnapshots.count(active)?mSnapshots.at(active):mDisplayed;const auto media=model(g),face=tableFace(g.id,g.model,g.face);
            SlotTabletopItem resident={g.id.c_str(),media.c_str(),face.c_str()};
            if(!slot_tabletop_resident(mTable,&resident,mTableHomes.count(active)?mTableHomes.at(active):0)){mTableAvailable=false;return false;}
        }mTableResident=active;
    }
    char clock[6]="--:--";std::time_t now=std::time(nullptr);if(auto* local=std::localtime(&now))std::strftime(clock,sizeof(clock),"%H:%M",local);
    const auto status=slot::roomStatus();slot_tabletop_status(mTable,status.battery,status.charging,status.connected,clock);
    const Uint64 pageStart=SDL_GetPerformanceCounter();mVideoBindMs=0;for(auto&v:mPageSteps)v=0;
    if(ready){if(mScreenDirty){screen(0,false);screen(1,false);mScreenDirty=mVideoDirty=mPageDirty[0]=mPageDirty[1]=false;mPageSteps[0]++;}
    else{for(unsigned i=0;i<2;i++){if(mPageDirty[i]){screen(i,false);mPageSteps[1+i]++;}else if(mVideoDirty)screenVideo(i);mPageDirty[i]=false;}mVideoDirty=false;}}
    SlotTabletopFrame f;f.seconds=mClock;f.delta=mFrameDelta;f.selected=-1;f.pageMs=1000.f*(SDL_GetPerformanceCounter()-pageStart)/SDL_GetPerformanceFrequency();f.videoBindMs=mVideoBindMs;std::copy(mPageSteps,mPageSteps+5,f.pageSteps);
    // Right-stick orbit eases to the clamped yaw while held and back on release.
    const float step=std::min(.1f,mFrameDelta);
    mOrbit+=(mOrbitGoal-mOrbit)*(1-std::exp(-step*5));f.yaw=mOrbit;
    // Inspection lifts over 0.45 s; the D-pad turns the cart at 150 degrees/s.
    mInspect=std::max(0.f,std::min(1.f,mInspect+(mInspectOpen?step:-step)/.45f));
    if(mInspectOpen){mInspectYaw=std::fmod(mInspectYaw+mSpin[0]*step*150,360.f);mInspectPitch=std::fmod(mInspectPitch+mSpin[1]*step*150,360.f);}
    else if(mInspect==0)mInspectYaw=mInspectPitch=0;
    f.inspection=mInspect;f.inspectYaw=mInspectYaw;f.inspectPitch=mInspectPitch;
    f.cameraView=mInspectOpen?4:mTableTVControls?5:mCameraView;f.automatic=mCameraView<0&&!mInspectOpen&&!mTableTVControls;
    if(mTableTVSelected&&!mTableTVControls)f.selected=-2;
    else for(size_t i=0;i<mTableGames.size();i++)if(!mTableTVControls&&mTableGames[i].id==mTableSelected)f.selected=i;
    f.phase=state.phase()==slot::Phase::Inserting?1:state.phase()==slot::Phase::Ejecting?2:0;f.progress=state.progress();
    f.screen=state.inserted().empty()&&!mTableTVControls?0:mSurface[0];f.screenU=mScreenWidth/720;f.screenV=mScreenHeight/480;
    f.handheldScreen=slot::roomControls()||state.inserted().empty()?0:mSurface[1];
    f.power=state.phase()==slot::Phase::Powering?std::min(1.f,state.progress()*state.duration()/.35f):state.phase()==slot::Phase::Zooming||state.phase()==slot::Phase::Launching||state.phase()==slot::Phase::Running?1:0;
    f.zoom=state.phase()==slot::Phase::Zooming?state.progress():state.phase()==slot::Phase::Launching||state.phase()==slot::Phase::Running?1:0;
    // Optical lid: open while loaded, closed during the one-second prelaunch interval and launch.
    f.lid=state.closing()?1-state.progress():state.preparing()||state.phase()==slot::Phase::Launching||state.phase()==slot::Phase::Running?0:-1;
    if(mRoomControls){slot::roomQueue(mTable,f);return true;}
    unsigned frame=slot_tabletop_frame(mTable,f);if(!frame){mTableAvailable=false;return false;}
    // The scene target is a normal bottom-up GL framebuffer; ES quads sample top-down.
    if(!mCarousel){Renderer::setMatrix(trans);texture(frame,0,0,720,mRoomControls?Renderer::getScreenHeight():480,1,1,true);}return true;
}
void SlotPresentation::shutdownTabletop(){if(sharedTable){slot_tabletop_remember_assets(sharedTable);slot::roomForget(sharedTable);slot_tabletop_close(sharedTable);}sharedTable=nullptr;sharedRoom=false;sharedTableRoot.clear();sharedSceneKey.clear();}
bool SlotPresentation::liveTable(SlotTabletop*table){return table&&table==sharedTable;}
SlotTabletop* SlotPresentation::homeTable(const std::vector<SlotTabletopItem>&items){
    static bool formatsLogged=false;if(!formatsLogged){LOG(LogInfo)<<"SLOTTED_ROOM1:SLOTHOME1,SLOTWORLD1,SLOTWORLD2";LOG(LogInfo)<<"SLOTTED_ROOM_FEATURES1:motion,crt,controller-devicepath";formatsLogged=true;}
    const char*overrideRoot=getenv("SLOT_TABLETOP_ASSETS");const std::string root=overrideRoot?overrideRoot:slot::assetRoot()+"tabletop",tv=installedTelevision(root,televisionProfile()->id);
    std::string key=root+"|home|"+tv+"|"+style()+"|"+colour()+"|"+gbaSpChoice();
    for(const auto&item:items)key+="|"+std::string(item.id)+":"+item.model;
    if(sharedTable&&(sharedTableRoot!=root||!sharedRoom))shutdownTabletop();
    if(!sharedTable){
        setenv("SLOT_GBA_SP",gbaSpChoice().c_str(),1);
        sharedTable=slot_tabletop_open(Renderer::getSDLWindow(),slot::assetRoot().c_str(),root.c_str(),"home",tv.c_str(),style()=="cel",colour().c_str(),Renderer::getWindowWidth(),Renderer::slotOutputHeight(),true);
        if(!sharedTable)return nullptr;
        const auto world=root+"/layouts/room.world";
        if(!slot_tabletop_world(sharedTable,Utils::FileSystem::exists(world)?world.c_str():nullptr)
            ||!slot_tabletop_items(sharedTable,items.data(),int(items.size()))||!slot_tabletop_stream_start(sharedTable)){shutdownTabletop();return nullptr;}
        sharedTableRoot=root;sharedRoom=true;sharedSceneKey=key;
        if(!items.empty())slot_tabletop_request(sharedTable,"home",tv.c_str(),gbaSpChoice().c_str(),items.data(),int(items.size()));
    }else if(sharedSceneKey!=key){
        if(!slot_tabletop_request(sharedTable,"home",tv.c_str(),gbaSpChoice().c_str(),items.data(),int(items.size())))return sharedTable;
        sharedSceneKey=key;
    }
    slot_tabletop_appearance(sharedTable,style()=="cel",colour().c_str());return sharedTable;
}
void SlotPresentation::cycleCamera(){
    if(!mTableAvailable||!tableReady()||mCarousel||inspecting()||state.busy()||state.launching())return;
    mCameraView=((mCameraView<0?slot_tabletop_default_view(mTable):mCameraView)+1)%4;
}
void SlotPresentation::leaveRoom(){
    if(!mRoomControls)return;
    const auto id=state.desired().empty()?state.inserted():state.desired();
    slot::roomSession().leave(mRoomSystem,mTableSelected,mTableHomes.count(id)?mTableHomes.at(id):0);
    mTableTVSelected=mTableTVControls=false;
}
void SlotPresentation::restoreRoomMedia(){
    if(!mRoomControls||state.inserted().empty()||mDisplayed.id==state.inserted())return;
    auto*system=SystemData::getSystem(mRoomSourceSystem);
    auto*file=system?system->getRootFolder()->FindByPath(state.inserted()):nullptr;
    if(!file||file->getType()!=GAME||!Utils::FileSystem::exists(state.inserted())){state.invalidate(state.inserted());return;}
    mDisplayed=capture(file);mSnapshots[mDisplayed.id]=mDisplayed;mLastInserted=mDisplayed.id;
    mStable=1;mDirty=mScreenDirty=true;buildPages();
}
void SlotPresentation::controlTV(bool active){
    mTableTVControls=active;if(active){mTableTVSelected=true;if(state.inserted().empty())for(const auto&game:mTableGames)if(game.id==mTableSelected){mDisplayed=game;buildPages();break;}}
    mScreenDirty=true;
}
static slot_navigation::Direction spatialDirection(int direction){
    return direction==-1?slot_navigation::Direction::Left:direction==1?slot_navigation::Direction::Right:direction==-2?slot_navigation::Direction::Up:slot_navigation::Direction::Down;
}
int SlotPresentation::spatialSelection(int direction){
    if(!navigationReady())return slot_navigation::noTarget;
    SlotTabletopFocus anchors[32];const int reference=mCameraView>=0&&mCameraView<4?mCameraView:slot_tabletop_default_view(mTable);
    const int count=slot_tabletop_focus_points(mTable,anchors,32,reference);
    std::vector<slot_navigation::Point> points;int current=mTableTVSelected?-2:slot_navigation::noTarget;
    for(int i=0;i<count;i++)points.push_back({anchors[i].item,anchors[i].x,anchors[i].y});
    if(!mTableTVSelected)for(size_t i=0;i<mTableGames.size();i++)if(mTableGames[i].id==mTableSelected)current=int(i);
    const int next=slot_navigation::neighbor(points,current,spatialDirection(direction));
    if(next==slot_navigation::noTarget)return next;
    mTableTVSelected=next==-2;
    return next>=0&&next<int(mTableOffsets.size())?mTableOffsets[next]:next;
}
int SlotPresentation::spatialEdgeEntry(int direction,int count){
    if(!navigationReady()||mTableTVSelected)return slot_navigation::noTarget;
    SlotTabletopFocus anchors[32];const int reference=mCameraView>=0&&mCameraView<4?mCameraView:slot_tabletop_default_view(mTable);
    const int n=slot_tabletop_focus_points(mTable,anchors,32,reference,true);
    std::vector<slot_navigation::Point> slots;int current=slot_navigation::noTarget;
    for(int i=0;i<n;i++)if(anchors[i].item>=0)slots.push_back({anchors[i].item,anchors[i].x,anchors[i].y});
    for(size_t i=0;i<mTableGames.size();i++)if(mTableGames[i].id==mTableSelected)current=int(i);
    return slot_navigation::incomingSlot(slots,current,spatialDirection(direction),count);
}
void SlotPresentation::highlight(FileData* game) {
    setenv("SLOT_SNES_CARTRIDGE",cartridgeChoice().c_str(),1);
    setenv("SLOT_GBA_SP",gbaSpChoice().c_str(),1);
    const auto name=game && game->getType()==GAME?game->getName():std::string();
    if(mHighlightName!=name){mHighlightName=name;mDirty=true;}
    if(game && game->getType()==GAME) {
        // Decode a textured console's albedo while browsing, before Down/Play.
        auto* source=game->getSourceFileData();
        const auto model=modelFor(source->getSystem()->getName(),source->getPath());
        if(model!=mWarmModel){mWarmModel=model;mWarmState=-2;}
    }
}
void SlotPresentation::request(FileData* game,bool launch) {
    Game value=capture(game);if(value.id.empty() || state.launching())return;
    mRequested=value;mSnapshots[value.id]=value;
    if(!state.busy())mRetract=std::min(1.f,mStable);
    // The power phase lasts the authored camera pan, so the pan to the console/TV ends before
    // the zoom into its screen starts; the power control itself still moves in 0.35 s.
    state.presentationDurations(mTableAvailable?std::max(.35f,mTable?slot_tabletop_pan_seconds(mTable):0.f):0,mTableAvailable?.85f:0);
    state.durations(mTableAvailable?tableInsertSeconds(mTableSystem):slot_native_duration(value.model.c_str(),1),mTableAvailable?tableEjectSeconds(mTableSystem):slot_native_duration(value.model.c_str(),0)+(mRetract>0?.65f:0),
        value.model=="psx"||value.model=="dreamcast"?1.f:0.f);
    if(launch)state.play(value.id);else state.insert(value.id);
    mDirty=true;
}
bool SlotPresentation::inspect(bool open){
    if(open){
        // Only a loose cart that is still on the table, with nothing in motion.
        if(!mTableAvailable||!tableReady()||mCarousel||state.busy()||state.launching()||mTableSelected.empty()||mTableSelected==state.inserted())return false;
        bool loose=false;for(auto&g:mTableGames)loose=loose||g.id==mTableSelected;
        if(!loose)return false;
    }
    mInspectOpen=open;mSpin[0]=mSpin[1]=0;return true;
}
bool SlotPresentation::insert(FileData* game){if(!game || game->getType()!=GAME||(mTableAvailable&&!tableReady()))return false;request(game,false);return true;}
bool SlotPresentation::play(FileData* game){if(!game || game->getType()!=GAME || state.launching())return false;if(mTableAvailable&&!tableReady())return true;request(game,true);return true;}
void SlotPresentation::eject(){
    if(mTableAvailable&&!tableReady())return;
    if(!state.busy())mRetract=std::min(1.f,mStable);
    const auto& g=mDisplayed.id.empty()?mMoving:mDisplayed;
    state.durations(mTableAvailable?tableInsertSeconds(mTableSystem):slot_native_duration(g.model.c_str(),1),mTableAvailable?tableEjectSeconds(mTableSystem):slot_native_duration(g.model.c_str(),0)+(mRetract>0?.65f:0));
    state.eject();mDirty=true;
}
void SlotPresentation::releaseGraphics() {
    mTable=nullptr;mTableId.clear();mTableResident.clear();mTableDirty=true;
    if(mNative){slot_native_close(mNative);mNative=nullptr;}mNativeId.clear();mNativeTexture=0;mBoundsReady=false;mNativePose=-1;
    for(int i=0;i<2;i++) {
        if(mFramebuffer[i])glDeleteFramebuffers(1,&mFramebuffer[i]);
        if(mSurface[i])Renderer::destroyTexture(mSurface[i]);
        mFramebuffer[i]=mSurface[i]=0;
    }
    mScreenDirty=true;
}
void SlotPresentation::reset() {
    mVideo.onHide();mVideo.setVideo("");mVideoStarted=false;
    releaseGraphics();if(mRoomControls)state.park();else state.reset();mDisplayed=Game();mMoving=Game();mRequested=Game();mSnapshots.clear();
    mLastTarget.clear();mLastInserted.clear();mPages.clear();mDirty=mScreenDirty=true;mStable=mRest=mRetract=0;
    mTableAvailable=false;mTableGames.clear();mTableOffsets.clear();mTableHomes.clear();mTableTVSelected=mTableTVControls=false;mCarousel=false;mOrbit=mOrbitGoal=0;
    mInspectOpen=false;mInspect=mInspectYaw=mInspectPitch=0;mSpin[0]=mSpin[1]=0;
}
void SlotPresentation::invalidate(const std::string& path){if(mRoomControls)slot::roomSession().invalidate(path);else state.invalidate(path);if(state.inserted().empty())mDisplayed=Game();mDirty=true;}
void SlotPresentation::refresh(FileData* file) {
    auto game=capture(file);if(game.id.empty())return;
    if(game.id==mDisplayed.id){mDisplayed=game;buildPages();}
    if(game.id==mRequested.id)mRequested=game;
    if(mSnapshots.count(game.id))mSnapshots[game.id]=game;
    mDirty=mScreenDirty=true;
}
void SlotPresentation::page(int direction){
    if(mPages.empty()||state.busy())return;
    int cycle=mPages.size();
    if(mTableAvailable&&mTable){int counts[2]={0,0};for(int i=0;i<2;i++){const auto*d=slot_tabletop_display_settings(mTable,i);if(d&&d->enabled)for(const auto&p:mPages)counts[i]+=slotMetadataPageVisible(p.label,p.overview,*d);}cycle=slotMetadataPageCycle(counts[0],counts[1]);}
    mPage=(mPage+direction+cycle)%cycle;prepareText();
}
void SlotPresentation::onHide(){{SlotRoomProbe probe("pres-video-hide");mVideo.onHide();}{SlotRoomProbe probe("pres-release");releaseGraphics();}GuiComponent::onHide();}
void SlotPresentation::onShow(){SlotRoomProbe probe("pres-show");if(mRoomControls){mTable=nullptr;mTableResident="@";mTableDirty=true;}GuiComponent::onShow();applyTelevision();mWarmModel.clear();mWarmState=-1;mVideoStarted=false;mStable=state.inserted().empty()?0:1;mRest=0;mVideo.onHide();mDirty=mScreenDirty=true;}
void SlotPresentation::onScreenSaverActivate(){mPaused=true;mVideo.onScreenSaverActivate();}
void SlotPresentation::onScreenSaverDeactivate(){mPaused=false;mVideo.onScreenSaverDeactivate();}
void SlotPresentation::topWindow(bool top){mPaused=!top;mVideo.topWindow(top);}

void SlotPresentation::buildPages() {
    mPages.clear();mPage=0;
    const auto& g=mDisplayed;
    mPages.push_back({"Overview",g.description.empty()?"No description available.":g.description,g.cover,true});
    mPages.push_back({"Game details",g.name+"\n"+g.facts,{}});
    if(!g.cover.empty())mPages.push_back({"Box art",{},g.cover});
    if(!g.video.empty())mPages.push_back({"Video",{},g.cover});
    for(const auto& image:g.gallery)mPages.push_back({image.first,{},image.second});
    mPages.push_back({"Your library",g.library,{}});
    prepareText();
}

void SlotPresentation::prepareText() {
    mScrollClock=mScrollOffset=0;
    if(mTableAvailable){mScreenDirty=true;return;}
    if(mPages.empty())return;
    // On the table a handheld's metadata goes to the TV like a console's (its LCDs stay blank).
    const auto layout=slotMetadataLayout(mScreenWidth,mScreenHeight,!mTableAvailable&&screenFor(mDisplayed.model)!=nullptr);
    const float type=layout.type;
    if(type!=mTypeScale)applyType(type);
    const auto& page=mPages[mPage%mPages.size()];
    const bool ds=!mTableAvailable&&mDisplayed.model=="nds",overview=page.overview;
    const bool wraps=titleLines(mTitle.getFont().get(),mDisplayed.name,mScreenWidth-2*layout.margin).find('\n')!=std::string::npos;
    // TextComponent enables multiline only above 1.8 actual font heights.
    // A hard-coded 48 px box can fall below that threshold for Open Sans.
    mHeaderHeight=std::ceil(mTitle.getFont()->getHeight(1.05f)*(wraps?2.f:1.f))+1;
    const float x=overview && !ds?std::floor(mScreenWidth*.35f):layout.margin;
    const float y=layout.bodyTop(mHeaderHeight,ds);
    mTextViewport=Vector4f(x,y,mScreenWidth-x-layout.margin,layout.bodyHeight(mScreenHeight,mHeaderHeight,ds));
    mText.setSize(mTextViewport.z(),0);mText.setText(page.text);
    mScrollExtent=std::max(0.f,mText.getSize().y()-mTextViewport.w());
    mScreenDirty=true;
}

void SlotPresentation::prepareGeometry() {
    if(mBoundsReady || !mNative)return;
    mNativeTexture=slot_native_present(mNative,1);mNativePose=1;
    if(!slot_native_bounds(mNative,mNativeBounds))return;
    const auto spec=screenFor(mDisplayed.model.empty()?mMoving.model:mDisplayed.model);
    float scale=std::min(310.f/mNativeBounds[2],280.f/mNativeBounds[3]);
    float x=170-mNativeBounds[2]*scale/2,y=470-mNativeBounds[3]*scale;
    if(spec) {
        float left=720,top=480,right=0,bottom=0;
        for(int i=0;i<spec->count;i++)for(int k=0;k<4;k++) {
            if(!slot_native_lcd(mNative,i,k,mLCD[i]+k*2))
                slot_native_project(mNative,spec->points[i]+k*3,spec->count==2 && i==0,mLCD[i]+k*2);
            left=std::min(left,mLCD[i][k*2]);right=std::max(right,mLCD[i][k*2]);
            top=std::min(top,mLCD[i][k*2+1]);bottom=std::max(bottom,mLCD[i][k*2+1]);
        }
        // Single-screen handhelds use half the original reading zoom. DS
        // already frames the complete pair; shrinking that again would leave
        // only ~64 vertical pixels per LCD for title, HUD and description.
        scale=std::min(660.f/(right-left),328.f/(bottom-top))*(spec->count==1?.5f:1.f);
        x=360-(right-left)*scale/2;y=136+(328-(bottom-top)*scale)/2;
        mTargetRect=Vector4f(x-left*scale,y-top*scale,720*scale,480*scale);
        float width=660,height=328;
        for(int i=0;i<spec->count;i++) {
            width=std::min(width,std::hypot(mLCD[i][2]-mLCD[i][0],mLCD[i][3]-mLCD[i][1])*scale);
            height=std::min(height,std::hypot(mLCD[i][6]-mLCD[i][0],mLCD[i][7]-mLCD[i][1])*scale);
            for(int k=0;k<4;k++){mLCD[i][k*2]/=720;mLCD[i][k*2+1]/=480;}
        }
        mScreenWidth=std::floor(width);mScreenHeight=std::floor(height);
    } else {
        float centre[2],extent[2],front[2];
        mHasFloor=slot_native_ground(mNative,centre,extent)&&slot_native_contact(mNative,front);
        if(mHasFloor) {
            const auto& model=mDisplayed.model.empty()?mMoving.model:mDisplayed.model;
            const auto layout=slotHomeLayout(model.c_str(),mNativeBounds,front,mTV->display,mTV->contact,mTV->units_per_mm);
            scale=layout.scale;mFloorY=layout.frontY;
            mTargetRect=Vector4f(layout.rect[0],layout.rect[1],layout.rect[2],layout.rect[3]);
            mConsoleFloor=Vector4f(mTargetRect.x()+centre[0]*scale,mTargetRect.y()+centre[1]*scale,extent[0]*scale,extent[1]*scale);
            mTelevision.setPosition(layout.tv[0],layout.tv[1]);
        } else mTargetRect=Vector4f(x-mNativeBounds[0]*scale,y-mNativeBounds[1]*scale,720*scale,480*scale);
        // Live glass size: the shorter of each pair of opposite edges of the projected quad.
        const float dw=mTV->display[0],dh=mTV->display[1],*q=mTV->quad;
        auto edge=[&](int a,int b){return std::hypot((q[b*2]-q[a*2])*dw,(q[b*2+1]-q[a*2+1])*dh);};
        mScreenWidth=std::floor(std::min(edge(0,1),edge(3,2)));
        mScreenHeight=std::floor(std::min(edge(0,3),edge(1,2)));
    }
    mBoundsReady=true;prepareText();
}

void SlotPresentation::update(int deltaTime) {
    if(mPaused)return;
    mFrameDelta=std::max(0,std::min(deltaTime,100))/1000.f;
    if(!mTableAvailable&&(mWarmState==0||mWarmState==-2))mWarmState=slot_native_prefetch(slot::assetRoot().c_str(),mWarmModel.c_str());
    if(mPreviousPhase!=state.phase()){mPreviousPhase=state.phase();mSounded=false;}
    const std::string target=state.target();
    if(!target.empty() && target!=mLastTarget) {
        mMoving=mSnapshots.count(target)?mSnapshots.at(target):mDisplayed;mLastTarget=target;
    }
    state.update(deltaTime/1000.f);mClock+=std::min(deltaTime,100)/1000.f;
    if(!state.target().empty() && state.target()!=mLastTarget) {
        mMoving=mSnapshots.count(state.target())?mSnapshots.at(state.target()):mDisplayed;mLastTarget=state.target();
    }
    if(state.busy() && !mSounded) {
        const auto& model=mMoving.model;
        // Tabletop handhelds click as the slide seats (the PSP before its cover closes).
        const bool slide=mTableAvailable&&(model=="gb"||model=="gbc"||model=="gba"||model=="nds");
        const float at=state.phase()==slot::Phase::Ejecting?.014f:slide?.9f:mTableAvailable&&model=="psp"?.8f:(model=="psx" || model=="dreamcast")?.714f:model=="gb" || model=="gbc"?.825f:model=="nds"?.849f:model=="psp"?.854f:model=="nes"&&mTableAvailable?.86f:.672f;
        if(state.progress()>=at){Sound::get(slot::assetRoot()+"sounds/"+(state.phase()==slot::Phase::Inserting?"insert.wav":"eject.wav"))->play();mSounded=true;}
    }
    if(state.inserted()!=mLastInserted) {
        {SlotRoomProbe probe("pres-video-reset");mVideo.onHide();mVideo.setVideo("");}mVideoStarted=false;mStable=mRest=mRetract=0;mBoundsReady=false;
        if(state.inserted()==mMoving.id)mDisplayed=mMoving;
        else if(state.inserted()==mRequested.id)mDisplayed=mRequested;
        else if(state.inserted().empty())mDisplayed=Game();
        mLastInserted=state.inserted();buildPages();mDirty=true;
    }
    if(state.target().empty())mLastTarget.clear();
    if(state.phase()==slot::Phase::Empty && mNative&&!mTableAvailable)releaseGraphics();
    for(auto it=mSnapshots.begin();it!=mSnapshots.end();) {
        if(it->first!=state.target() && it->first!=state.desired() && it->first!=state.inserted())it=mSnapshots.erase(it);else ++it;
    }
    if(state.phase()==slot::Phase::Inserted && !mDisplayed.id.empty()) {
        mStable+=std::min(deltaTime,100)/1000.f;mRest+=std::min(deltaTime,100)/1000.f;
        if(mStable>=1 && mScrollExtent>0) {
            mScrollClock+=std::min(deltaTime,100)/1000.f;
            const float travel=mScrollExtent/18.f,cycle=3+travel+2;
            const float offset=std::max(0.f,std::min(mScrollExtent,(std::fmod(mScrollClock,cycle)-3)*18));
            // Tabletop: only a page whose description scrolls is redrawn for it.
            if(std::abs(offset-mScrollOffset)>.1f){mScrollOffset=offset;if(mTableAvailable){for(int i=0;i<2;i++)mPageDirty[i]=mPageDirty[i]||mPageScrolls[i];}else mScreenDirty=true;}
        }
        if(!mVideoStarted && mRest>=3 && !mDisplayed.video.empty()) {
            {SlotRoomProbe probe("pres-video-start");mVideo.setVideo(mDisplayed.video);mVideo.onShow();}mVideoStarted=true;
        }
    }else if(mVideoStarted){{SlotRoomProbe probe("pres-video-stop");mVideo.onHide();}mVideoStarted=false;mRest=0;}
    // On the tabletop a video frame only redraws the video rectangles (screenVideo); rebuilding
    // both metadata pages every frame held the overview at the 10 fps frame-time floor.
    static const bool fullPages=getenv("SLOT_TABLETOP_FULL_PAGES")!=nullptr; // A/B evidence only
    if(mVideoStarted){{SlotRoomProbe probe("pres-video-update");mVideo.update(deltaTime);}if(mTableAvailable&&!fullPages)mVideoDirty=true;else mScreenDirty=true;}
    if(!mDirty)return;
    const Game& visible=mDisplayed.id.empty()?mRequested:mDisplayed;
    if(mStageLoaded)mConsole.setImage(screenFor(visible.model)?slot::assetRoot()+"stage/front/"+style()+"/"+colour()+"/"+visible.model+".png":slot::assetRoot()+"stage/"+style()+"/"+colour()+"/console-"+visible.model+".png");
    mDirty=false;
}

void SlotPresentation::pageText(unsigned index,float scale,unsigned color){
    if(!mPageText[index][0]){
        for(int k=0;k<4;k++){mPageText[index][k]=std::make_unique<TextComponent>(mWindow);auto&t=*mPageText[index][k];t.setVerticalAlignment(ALIGN_TOP);t.setLineSpacing(k?1.12f:1.05f);mPageTextSize[index][k][0]=mPageTextSize[index][k][1]=-1;}
        mPageText[index][0]->setMultiLine(TextComponent::MULTILINE);mPageTextColor[index]=0;
    }
    // Font::get returns the cached font, so setFont() changes nothing while the scale stays.
    const float fonts=Renderer::ScreenSettings::fontScale();
    mPageText[index][0]->setFont(Font::get(21*scale/fonts,slot::assetRoot()+"fonts/OpenSans-SemiBold.ttf"));
    mPageText[index][1]->setFont(Font::get(20*scale/fonts,slot::assetRoot()+"fonts/OpenSans-Regular.ttf"));
    mPageText[index][2]->setFont(Font::get(18*scale/fonts,slot::assetRoot()+"fonts/OpenSans-SemiBold.ttf"));
    mPageText[index][3]->setFont(Font::get(16*scale/fonts,slot::assetRoot()+"fonts/OpenSans-Regular.ttf"));
    if(mPageTextColor[index]!=color){for(auto&t:mPageText[index])t->setColor(color);mPageTextColor[index]=color;}
}
// setSize() re-wraps unconditionally in this frontend; only call it when the size changes.
void SlotPresentation::pageSize(unsigned index,int part,float width,float height){
    float*last=mPageTextSize[index][part];if(last[0]==width&&last[1]==height)return;
    last[0]=width;last[1]=height;mPageText[index][part]->setSize(width,height);
}
void SlotPresentation::screenTabletop(unsigned index){
    mVideoArea[index]=mPageScrolls[index]=false;const auto*settings=slot_tabletop_display_settings(mTable,index);
    if(!settings||!settings->enabled||mDisplayed.id.empty()||mPages.empty())return;
    const auto&d=*settings;auto enabled=[&](unsigned bit){return (d.fields&(1u<<bit))!=0;};
    std::vector<const Page*> pages;
    for(auto&p:mPages)if(slotMetadataPageVisible(p.label,p.overview,d))pages.push_back(&p);
    const auto&page=*pages[mPage%pages.size()];
    if(!mSurface[index]){mSurface[index]=Renderer::createTexture(Renderer::Texture::RGBA,true,false,720,480,nullptr);glGenFramebuffers(1,&mFramebuffer[index]);}
    GLint previous=0,viewport[4];glGetIntegerv(GL_FRAMEBUFFER_BINDING,&previous);glGetIntegerv(GL_VIEWPORT,viewport);
    glBindFramebuffer(GL_FRAMEBUFFER,mFramebuffer[index]);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,mSurface[index],0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE){glBindFramebuffer(GL_FRAMEBUFFER,previous);return;}
    std::unique_ptr<slot::RenderTarget> target;if(mRoomControls)target.reset(new slot::RenderTarget(720,480));
    glViewport(0,0,720,480);const auto trans=Transform4x4f::Identity();Renderer::setMatrix(trans);Renderer::pushClipRect(0,0,mScreenWidth,mScreenHeight);
    const unsigned background=(d.background<<8)|255,foreground=(d.foreground<<8)|255,accent=(d.accent<<8)|255;
    Renderer::drawRect(0,0,mScreenWidth,mScreenHeight,background);pageText(index,d.textScale,foreground);
    TextComponent&title=*mPageText[index][0],&body=*mPageText[index][1],&hud=*mPageText[index][2],&foot=*mPageText[index][3];
    const float pad=d.padding,width=mScreenWidth-2*pad,footer=enabled(5)?30*d.textScale:pad;float y=pad;
    if(enabled(0)){
        const auto lines=titleLines(title.getFont().get(),mDisplayed.name,width);const bool wraps=lines.find('\n')!=std::string::npos;
        const float h=std::ceil(title.getFont()->getHeight(1.05f)*(wraps?2:1))+1;
        title.setText(lines);title.setPosition(pad,y);pageSize(index,0,width,h);title.render(trans);y+=h+4;
    }
    if(enabled(1)){const float h=hud.getFont()->getHeight(1.05f)+1;hud.setText(mDisplayed.hud);hud.setPosition(pad,y);pageSize(index,2,width,h);hud.render(trans);y+=h+4;}
    Renderer::setMatrix(trans);Renderer::drawRect(pad,y,width,1,accent);y+=8;
    const float height=std::max(0.f,mScreenHeight-y-footer);
    const bool videoPage=page.label=="Video",hasArt=(enabled(2)&&!page.image.empty())||(enabled(6)&&mVideoStarted&&(page.overview||videoPage));
    const bool art=d.layout!=1&&hasArt,split=d.layout==0&&page.overview&&art;
    const float artWidth=split?mScreenWidth*.30f:width;
    if(art&&height>0){
        if(enabled(2)){mArtwork.setImage(page.image);mArtwork.setMaxSize(artWidth,height);mArtwork.setPosition(pad+artWidth/2,y+height/2);mArtwork.render(trans);}
        if(enabled(6)&&mVideoStarted&&(page.overview||videoPage)){
            Renderer::pushClipRect(pad,y,artWidth,height);video(pad,y,artWidth,height,false);Renderer::popClipRect();
            const float rect[4]={pad,y,artWidth,height};std::copy(rect,rect+4,mVideoRect[index]);mVideoArea[index]=true;
        }
    }
    std::string text=page.text;
    if((page.overview&&!enabled(3))||(page.label=="Game details"&&!enabled(4))||(page.label=="Your library"&&!enabled(7))||d.layout==2)text.clear();
    const float tx=split?mScreenWidth*.35f:pad,tw=mScreenWidth-tx-pad;
    body.setText(text);pageSize(index,1,tw,0);const float extent=text.empty()?0.f:std::max(0.f,body.getSize().y()-height);
    const auto*tv=slot_tabletop_display_settings(mTable,0);
    if(index==0||!tv||!tv->enabled)mScrollExtent=extent;
    mPageScrolls[index]=!text.empty()&&height>0&&extent>0;
    if(!text.empty()&&height>0){Renderer::pushClipRect(tx,y,tw,height);body.setPosition(tx,y-std::min(mScrollOffset,extent));body.render(trans);Renderer::popClipRect();}
    if(enabled(5)){foot.setPosition(pad,mScreenHeight-footer+3);pageSize(index,3,width,footer-3);foot.setText("L1 / R1   "+std::to_string(mPage%pages.size()+1)+" / "+std::to_string(pages.size())+"   "+page.label);foot.render(trans);}
    Renderer::popClipRect();glBindFramebuffer(GL_FRAMEBUFFER,previous);glViewport(viewport[0],viewport[1],viewport[2],viewport[3]);Renderer::bindTexture(0);
}

// The video draws its own background over its whole rectangle, so redrawing just that
// rectangle into the finished page gives the same pixels as rebuilding the page.
void SlotPresentation::screenVideo(unsigned index){
    if(!mVideoArea[index]||!mSurface[index]||!mFramebuffer[index])return;
    GLint previous=0,viewport[4];glGetIntegerv(GL_FRAMEBUFFER_BINDING,&previous);glGetIntegerv(GL_VIEWPORT,viewport);
    glBindFramebuffer(GL_FRAMEBUFFER,mFramebuffer[index]);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,mSurface[index],0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE){glBindFramebuffer(GL_FRAMEBUFFER,previous);return;}
    std::unique_ptr<slot::RenderTarget> target;if(mRoomControls)target.reset(new slot::RenderTarget(720,480));
    glViewport(0,0,720,480);const auto trans=Transform4x4f::Identity();Renderer::setMatrix(trans);const float*r=mVideoRect[index];
    Renderer::pushClipRect(0,0,mScreenWidth,mScreenHeight);Renderer::pushClipRect(r[0],r[1],r[2],r[3]);video(r[0],r[1],r[2],r[3],false);Renderer::popClipRect();Renderer::popClipRect();
    glBindFramebuffer(GL_FRAMEBUFFER,previous);glViewport(viewport[0],viewport[1],viewport[2],viewport[3]);Renderer::bindTexture(0);mPageSteps[3+index]++;
}

void SlotPresentation::screen(unsigned index,bool artOnly) {
    SlotRoomProbe probe("pres-screen");
    if(mTableAvailable){screenTabletop(index);return;}
    mTitle.setColor(0xF6F4EFFF);mHud.setColor(0xAAD8BCFF);mText.setColor(0xE5E1D5FF);mFooter.setColor(0xE5E1D5FF);
    if(mDisplayed.id.empty() || mPages.empty())return;
    if(!mSurface[index]) {
        mSurface[index]=Renderer::createTexture(Renderer::Texture::RGBA,true,false,720,480,nullptr);
        glGenFramebuffers(1,&mFramebuffer[index]);
    }
    GLint previous=0,viewport[4];glGetIntegerv(GL_FRAMEBUFFER_BINDING,&previous);glGetIntegerv(GL_VIEWPORT,viewport);
    glBindFramebuffer(GL_FRAMEBUFFER,mFramebuffer[index]);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,mSurface[index],0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE){glBindFramebuffer(GL_FRAMEBUFFER,previous);return;}
    glViewport(0,0,720,480);
    Renderer::pushClipRect(0,0,mScreenWidth,mScreenHeight);
    const auto trans=Transform4x4f::Identity();Renderer::setMatrix(trans);
    Renderer::drawRect(0,0,mScreenWidth,mScreenHeight,0x0E191BFF);
    mPage%=mPages.size();const Page& page=mPages[mPage];
    const bool ds=!mTableAvailable&&mDisplayed.model=="nds";
    const auto layout=slotMetadataLayout(mScreenWidth,mScreenHeight,!mTableAvailable&&screenFor(mDisplayed.model)!=nullptr);
    auto header=titleLines(mTitle.getFont().get(),ds && !artOnly?page.label:mDisplayed.name,mScreenWidth-2*layout.margin);
    mTitle.setText(header);mTitle.setPosition(layout.margin,layout.top);mTitle.setSize(mScreenWidth-2*layout.margin,ds && !artOnly?24:mHeaderHeight);mTitle.render(trans);
    if(!ds || artOnly) {
        mHud.setText(mDisplayed.hud);mHud.setPosition(layout.margin,mHeaderHeight+layout.hudGap);mHud.setSize(mScreenWidth-2*layout.margin,layout.hudHeight);mHud.render(trans);
        Renderer::setMatrix(trans);Renderer::drawRect(layout.margin,mHeaderHeight+layout.ruleGap,mScreenWidth-2*layout.margin,1,0x42665AFF);
    }
    if(artOnly || page.overview || !page.image.empty()) {
        const bool overview=!artOnly && page.overview && !ds;
        mArtwork.setImage(artOnly?mDisplayed.cover:page.image);
        const float y=ds && !artOnly?34:mHeaderHeight+layout.bodyGap+2,h=std::max(1.f,mScreenHeight-y-(artOnly?6:layout.footerReserve));
        const float w=overview?mScreenWidth*.30f:mScreenWidth-2*layout.margin;
        const float artHeight=h;
        // Keep a useful still until VLC supplies a frame (including bad media).
        if(!(ds && !artOnly && page.overview)) {
            mArtwork.setMaxSize(w,artHeight);mArtwork.setPosition(overview?w/2+layout.margin-2:mScreenWidth/2,y+artHeight/2);mArtwork.render(trans);
        }
        Renderer::setMatrix(trans);
        if(overview && mVideoStarted)video(layout.margin-2,y,w,h,false);
        else if((artOnly || page.label=="Video") && mVideoStarted)video(layout.margin,y,mScreenWidth-2*layout.margin,h,artOnly);
    }
    if(!artOnly && !page.text.empty()) {
        Renderer::pushClipRect(mTextViewport.x(),mTextViewport.y(),mTextViewport.z(),mTextViewport.w());
        mText.setPosition(mTextViewport.x(),mTextViewport.y()-mScrollOffset);mText.render(trans);
        Renderer::popClipRect();
    }
    if(!artOnly) {
        mFooter.setPosition(layout.margin,mScreenHeight-layout.footerOffset);mFooter.setSize(mScreenWidth-2*layout.margin,layout.footerHeight);
        mFooter.setText("L1 / R1   "+std::to_string(mPage+1)+" / "+std::to_string(mPages.size())+(ds?"":"   "+page.label));mFooter.render(trans);
    }
    Renderer::popClipRect();glBindFramebuffer(GL_FRAMEBUFFER,previous);glViewport(viewport[0],viewport[1],viewport[2],viewport[3]);
    Renderer::bindTexture(0);
}

void SlotPresentation::video(float x,float y,float width,float height,bool topScreen) {
    const bool ds=!mTableAvailable&&mDisplayed.model=="nds";float crop[]={0,0,1,1};
    const Uint64 bindStart=SDL_GetPerformanceCounter();const bool bound=mVideo.bindSlotFrame(ds?crop:nullptr);
    mVideoBindMs+=1000.f*(SDL_GetPerformanceCounter()-bindStart)/SDL_GetPerformanceFrequency(); // SLOT_SCENE_FRAMELOG only
    if(!bound)return;
    const auto size=mVideo.getVideoSize();if(size.x()<=0 || size.y()<=0)return;
    Renderer::drawRect(x,y,width,height,0x0E191BFF);
    mVideo.bindSlotFrame(); // drawRect changed the bound texture.
    const float sourceWidth=size.x()*(crop[2]-crop[0]),sourceHeight=size.y()*(crop[3]-crop[1]);
    const bool stacked=ds && sourceWidth/sourceHeight>.60f && sourceWidth/sourceHeight<.76f;
    const float region=stacked?.49f:1.f;
    const float from=stacked && !topScreen?.51f:0;
    const float scale=std::min(width/sourceWidth,height/(sourceHeight*region));
    const float w=sourceWidth*scale,h=sourceHeight*region*scale;
    x+=(width-w)/2;y+=(height-h)/2;
    // Crop the two DS screens from the
    // same decoded frame, preserving each screen's aspect without stretching.
    const float a=crop[1]+from*(crop[3]-crop[1]),b=a+region*(crop[3]-crop[1]);
    Renderer::Vertex q[]={{{x,y},{crop[0],a},0xFFFFFFFF},{{x,y+h},{crop[0],b},0xFFFFFFFF},{{x+w,y},{crop[2],a},0xFFFFFFFF},{{x+w,y+h},{crop[2],b},0xFFFFFFFF}};
    Renderer::drawTriangleStrips(q,4);
}

void SlotPresentation::model(float progress,const Transform4x4f& trans) {
    slot_native_optical_close(mNative,state.closing()?std::min(1.f,state.progress()/.35f):state.launching()?1.f:0.f);
    if(state.closing())mNativePose=-1;
    if(!mNative){mConsole.render(trans);return;}
    prepareGeometry();
    const float pose=std::min(1.f,progress/.65f);
    if(std::abs(pose-mNativePose)>.0001f){mNativeTexture=slot_native_present(mNative,pose);mNativePose=pose;}
    const float t=std::max(0.f,std::min(1.f,progress)),ease=t*t*(3-2*t);
    const float start[]={90,120,540,360};
    for(int i=0;i<4;i++)mNativeRect[i]=start[i]+(mTargetRect[i]-start[i])*ease;
    Renderer::setMatrix(trans);texture(mNativeTexture,mNativeRect.x(),mNativeRect.y(),mNativeRect.z(),mNativeRect.w());
}

void SlotPresentation::render(const Transform4x4f& parentTrans) {
    if(mTableAvailable){SlotRoomProbe probe("pres-tabletop");if(tabletop(parentTrans*getTransform()))return;}
    if(!hasScene())return;
    if(!mStageLoaded)loadStage();
    const auto trans=parentTrans*getTransform();Renderer::setMatrix(trans);
    Renderer::drawRect(0,120,720,360,0x08090DFF);
    const auto& visible=state.busy()?(mMoving.id.empty()?mRequested:mMoving):mDisplayed;
    const auto nativeId=visible.id+"|"+cartridgeChoice()+"|"+gbaSpChoice();
    if(mNativeId!=nativeId || !mNative) {
        if(mNative)slot_native_close(mNative);
        setenv("SLOT_SNES_CARTRIDGE",cartridgeChoice().c_str(),1);
        setenv("SLOT_GBA_SP",gbaSpChoice().c_str(),1);
        const auto face=cartridgeFace(visible.id,visible.model);
        mNative=slot_native_open(Renderer::getSDLWindow(),slot::assetRoot().c_str(),visible.id.c_str(),visible.model.c_str(),face.c_str(),style().c_str(),colour().c_str());
        mNativeId=nativeId;mBoundsReady=false;mNativePose=-1;
    }
    if(state.busy()) {
        const bool inserting=state.phase()==slot::Phase::Inserting;
        const float elapsed=state.progress()*state.duration(),lead=!inserting && mRetract>0?.65f:0;
        Renderer::pushClipRect(0,120,720,360);
        if(lead && elapsed<lead){model(mRetract*(1-elapsed/lead),trans);Renderer::popClipRect();return;}
        const float progress=inserting?state.progress():(elapsed-lead)/slot_native_duration(visible.model.c_str(),0);
        const unsigned frame=slot_native_frame(mNative,progress,inserting);
        mNativePose=-1;
        Renderer::setMatrix(trans);texture(frame,90,120,540,360);
        if(!frame)mConsole.render(trans);
        Renderer::popClipRect();
        return;
    }
    prepareGeometry();
    if(mScreenDirty){screen(0,false);if(mDisplayed.model=="nds")screen(1,true);mScreenDirty=false;}
    Renderer::setMatrix(trans);
    const auto spec=screenFor(mDisplayed.model);
    Renderer::pushClipRect(0,120,720,360);
    if(!spec) {
        // One floor under both devices: a faint glow along the contact line, soft contact shadows
        // under the console's footprint and the cabinet's, and the cable on the floor between them.
        const float floorY=mHasFloor?mFloorY:mTelevision.getPosition().y()+mTV->base[1];
        mFloorGlow.setResize(760,150);mFloorGlow.setPosition(360,floorY+8);mFloorGlow.render(trans);
        if(mHasFloor){
            mShadow.setResize(std::max(60.f,mConsoleFloor.z()*1.25f),std::max(26.f,mConsoleFloor.w()*1.3f));
            mShadow.setPosition(mConsoleFloor.x(),mConsoleFloor.y());mShadow.render(trans);
        }
        const float tvX=mTelevision.getPosition().x()+mTV->base[0];
        const float tvY=mTelevision.getPosition().y()+mTV->base[1];
        mShadow.setResize(mTV->footprint[0]*1.08f,mTV->footprint[1]*1.2f);
        mShadow.setPosition(tvX,tvY);mShadow.render(trans);Renderer::setMatrix(trans);
        if(mHasFloor){
            const float from=mConsoleFloor.x()+mConsoleFloor.z()/2;
            const float length=tvX-mTV->footprint[0]/2-from;
            if(length>0)Renderer::drawRect(from,floorY+5,length,3,0x30312FFF);
        }
        mTelevision.render(trans);Renderer::setMatrix(trans);
        lcd(mSurface[0],mTV->quad,mTelevision.getPosition(),mTelevision.getSize(),mScreenWidth/720,mScreenHeight/480);
    }
    model(std::min(1.f,mStable),trans);
    if(spec && mNative && mStable>=1) {
        Renderer::setMatrix(trans);
        const auto position=Vector3f(mNativeRect.x(),mNativeRect.y(),0);
        const auto size=Vector2f(mNativeRect.z(),mNativeRect.w());
        for(int i=0;i<spec->count;i++)lcd(mSurface[spec->count==2 && i==0?1:0],mLCD[i],position,size,mScreenWidth/720,mScreenHeight/480);
    }
    Renderer::popClipRect();
}
