"""Apply the opt-in slot extension to exactly the recorded Scarab source pin.

Existing source files are regenerated from git objects, never fuzzy-patched.
Only this extension's allowlisted files are touched. No deployment is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

PIN='4041b56a714265de81de8165b34fbd10f313a891'
HERE=Path(__file__).resolve().parent


def original(source,path):
    return subprocess.check_output(['git','-C',str(source),'show',PIN+':'+path]).decode('utf-8-sig',errors='surrogateescape').replace('\r\n','\n')


def change(content,before,after):
    if content.count(before)!=1:
        raise ValueError('Expected one source anchor: '+before[:90])
    return content.replace(before,after,1)


def apply(source):
    if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=PIN:
        raise ValueError('Unsupported source revision')
    if not (source/'.git').is_dir():
        raise ValueError('Use a dedicated source clone, not an existing worktree')
    ownership=source/'.git/slot-presentation-output.json'
    if ownership.exists():
        for path,expected in json.loads(ownership.read_text()).items():
            target=source/path
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
                raise ValueError('Locally edited extension output; preserve/review it before reapplying: '+path)
    else:
        if subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip():
            raise ValueError('First application requires a clean dedicated source clone')
    edits={}
    # This pin passes a controller path only on Windows. Current Knulli configgen
    # requires the Linux event path too (notably for MPV/Ports evmapy controls).
    path='es-core/src/InputManager.cpp'
    content=original(source,path)
    content=change(content,'#if WIN32\n\t  command << " -p" << player+1 << "path \\\""     << playerInputConfig->getDevicePath() << "\\\"";\n#endif',
        '#if WIN32\n\t  command << " -p" << player+1 << "path \\\""     << playerInputConfig->getDevicePath() << "\\\"";\n#elif defined(__linux__)\n      command << " -p" << player+1 << "devicepath \\\"" << playerInputConfig->getDevicePath() << "\\\"";\n#endif')
    edits[path]=content
    path='es-app/src/views/gamelist/CarouselGameListView.h'
    content=original(source,path)
    content=change(content,'#include "DetailedContainer.h"','#include "DetailedContainer.h"\n#include "components/SlotPresentation.h"\n#include "FileData.h"')
    content=change(content,'\tvirtual void update(int deltaTime) override;','''\tvirtual void update(int deltaTime) override;
    bool input(InputConfig* config, Input input) override;
    void moveSlotCursor(int direction);
    void onShow() override;
    void onHide() override;
    std::vector<HelpPrompt> getHelpPrompts() override;
    bool queueSlotLaunch(FileData* game, const LaunchGameOptions& options, Vector3f center);
    // R3 toggles the tabletop's full-screen carousel instead of skipping music.
    bool ownsSlotCarouselButton() { return mSlotEnabled && mSlot.hasTabletop(); }''')
    content=change(content,'    bool ownsSlotCarouselButton() { return mSlotEnabled && mSlot.hasTabletop(); }','''    bool ownsSlotCarouselButton() { return mSlotEnabled && (mSlot.roomControls() || mSlot.hasTabletop()); }
    bool ownsSlotTabletop() { return mSlotEnabled && mSlot.hasTabletop() && !mSlotFullCarousel; }
    bool prepareSlotTabletop() { if(!mSlotEnabled)return false;updateInfoPanel();return mSlot.hasTabletop(); }''')
    content=change(content,'\tDetailedContainerHost mDetails;','''\tDetailedContainerHost mDetails;
    SlotPresentation mSlot;
    bool mSlotEnabled=false, mSlotSmall=false, mSlotFullCarousel=false;
    bool mSlotConfirmHeld=false,mSlotCarouselHeld=false,mSlotLaunchDispatch=false;
    bool mSlotSelectHeld=false,mSlotSelectUsed=false;int mSlotSelectMs=0;
    bool mSlotBackHeld=false;int mSlotHeldAxes[2]={0,0},mSlotNavMs=0,mSlotNavRepeat=350;
    int mSlotDirectionHeld=0,mSlotSpin[2]={0,0};
    Vector3f mSlotListPosition, mSlotVideoPosition;
    LaunchGameOptions mSlotLaunchOptions;
    Vector3f mSlotLaunchCenter;''')
    edits[path]=content
    path='es-app/src/views/gamelist/CarouselGameListView.cpp'
    content=original(source,path)
    content=change(content,'#include "GameNameFormatter.h"','#include "GameNameFormatter.h"\n#include "components/SlotLaunchGuard.h"\n#include "components/SlotRoomRoutes.h"\n#include "SlotRoomTiming.h"\n#include <fstream>')
    content=change(content,'mDetails(this, &mList, mWindow, DetailedContainer::DetailedView)','mDetails(this, &mList, mWindow, DetailedContainer::DetailedView), mSlot(window,mRoot->getSystem()->getName())')
    content=change(content,'\taddChild(&mList);','\taddChild(&mList);\n    addChild(&mSlot);')
    content=change(content,'\tmList.applyTheme(theme, getName(), "gamecarousel", ThemeFlags::ALL);','''\tmList.applyTheme(theme, getName(), "gamecarousel", ThemeFlags::ALL);
    mSlot.reset(); mSlotSmall=false;mSlotFullCarousel=false;mSlotConfirmHeld=mSlotCarouselHeld=false;
    mSlotListPosition=mList.getPosition();mList.setScaleOrigin(0.f);
    mSlotEnabled=theme->getElement(getName(), "slot-capability", "text") != nullptr
        && !mRoot->getSystem()->isCollection()
        && (mSlot.roomControls() || (Renderer::getScreenWidth()==720 && Renderer::getScreenHeight()==480));
    mList.setSlotInteraction(mSlotEnabled);
    for(auto extra:mThemeExtras)if(extra->getTag()=="slot_video")mSlotVideoPosition=extra->getPosition();''')
    content=change(content,'\tupdateThemeExtrasBindings();','''\tupdateThemeExtrasBindings();
    if(mSlotEnabled) {
        mSlot.highlight(getCursor());
        std::vector<FileData*> games;
        for(auto* object:mList.slotObjects())games.push_back(static_cast<FileData*>(object));
        mSlot.browse(games,getCursor());
        for(auto extra:mThemeExtras)if(!mSlot.hasTabletop() && extra->getTag()=="slot-browse-console") {
            auto* image=dynamic_cast<ImageComponent*>(extra);
            if(image)image->setImage(SlotPresentation::browseImage(getCursor()));
        }
    }''')
    content=change(content,'\tif(change == FILE_METADATA_CHANGED)','''    if(file && change==FILE_REMOVED)mSlot.invalidate(file->getSourceFileData()->getPath());
    if(file && change==FILE_METADATA_CHANGED && mSlotEnabled)mSlot.refresh(file);
\tif(change == FILE_METADATA_CHANGED && !mSlotEnabled)''')
    content=change(content,'\tISimpleGameListView::update(deltaTime);','''\tISimpleGameListView::update(deltaTime);
    if(!mSlotEnabled)return;
    if(mSlotSelectHeld)mSlotSelectMs+=std::max(0,std::min(deltaTime,100));
    if(mSlot.roomControls()&&mSlotDirectionHeld) {
        if(!mSlot.navigationReady()){mSlotDirectionHeld=0;mSlotHeldAxes[0]=mSlotHeldAxes[1]=0;}
        else {
            mSlotNavMs+=std::max(0,std::min(deltaTime,100));
            if(mSlotNavMs>=mSlotNavRepeat){mSlotNavMs=0;mSlotNavRepeat=140;moveSlotCursor(mSlotDirectionHeld);}
        }
    }
    mList.setSlotInserted(mSlot.state.inserted());
    const bool tabletop=mSlot.hasTabletop();
    mList.setSlotScene(!tabletop && mSlot.hasScene());
    mList.setVisible(!tabletop || mSlotFullCarousel);mSlot.carousel(mSlotFullCarousel);
    for(auto extra:mThemeExtras)if(extra->getTag()=="slot_video")
        extra->setPosition(mSlotVideoPosition+Vector3f(0,mList.slotIdleOffset(),0));
    const bool small=mSlot.hasScene() || tabletop;
    if(small!=mSlotSmall) {
        mList.stopScrolling();
        mSlotSmall=small;
        mList.setScale(1.f);mList.setPosition(mSlotListPosition);
        for(auto extra:mThemeExtras) {
            if(extra->getTag()=="slot_video") { if(small)extra->onHide();else extra->onShow();extra->setVisible(!small); }
            if(extra->getTag()=="slot-browse-console")extra->setVisible(!small);
        }
    }
    // Cursor bindings can re-enable extras. Enforce ownership every update.
    for(auto extra:mThemeExtras) {
        if(extra->getTag()=="slot_video" || extra->getTag()=="slot-browse-console")extra->setVisible(!small);
        if(extra->getTag()=="slot-console-appearance" || extra->getTag()=="slot-band")extra->setVisible(false);
        const auto& tag=extra->getTag();
        if(tag.find("slot-status")==0 || tag.find("slot-battery")==0 || tag=="slot-clock" || tag=="slot-network")extra->setOpacity(tabletop&&!mSlotFullCarousel?0:255);
    }
    const std::string ready=mSlot.state.takeLaunch();
    if(!ready.empty()) {
        auto* game=mRoot->getSystem()->getRootFolder()->FindByPath(ready);
        if(game && game->getType()==GAME && Utils::FileSystem::exists(ready) && slot::beginLaunch(ready)) {
            mSlotLaunchDispatch=true;
            ViewController::get()->launch(game,mSlotLaunchOptions,mSlotLaunchCenter,false);
            mSlotLaunchDispatch=false;
        }
        else mSlot.reset();
    }''')
    content+='''
void CarouselGameListView::onShow() {
    SlotRoomProbe probe("console-show");
    if(mSlot.state.launching())slot::endLaunch();
    mSlot.state.returned();mSlotDirectionHeld=0;mSlotSpin[0]=mSlotSpin[1]=0;mSlotConfirmHeld=mSlotCarouselHeld=mSlotBackHeld=false;mSlotSelectHeld=mSlotSelectUsed=false;mSlotSelectMs=0;mSlotHeldAxes[0]=mSlotHeldAxes[1]=0;mSlotNavMs=0;mSlotNavRepeat=350;
    ISimpleGameListView::onShow();updateInfoPanel();
    if(mSlotEnabled && getenv("SLOT_PRESENTATION_DIAGNOSTICS")) {
        std::ofstream out("/tmp/art-book-slot-launch/presentation-layout.txt");
        for(auto extra:mThemeExtras)if(extra->getTag().find("slot")==0)
            out<<extra->getTag()<<" z="<<extra->getZIndex()<<" visible="<<extra->isVisible()<<" value="<<extra->getValue()<<"\\n";
    }
}

void CarouselGameListView::onHide() {
    SlotRoomProbe probe("console-hide");
    mList.stopScrolling();
    if(mSlot.roomControls())mSlot.leaveRoom();else if(!mSlot.state.launching())mSlot.reset();
    mSlotDirectionHeld=0;mSlotSelectHeld=mSlotSelectUsed=false;mSlotSelectMs=0;
    ISimpleGameListView::onHide();
}

bool CarouselGameListView::input(InputConfig* config,Input event) {
    if(mSlotEnabled) {
        if(event.value)mList.resetSlotIdle();
        if(mSlot.hasTabletop()) {
            // One Back press has one owner: a held/repeated B cannot close TV
            // controls, then eject, then leave the room on the same press.
            if(mSlot.roomControls() && config->isMappedTo(BUTTON_BACK,event)) {
                if(!event.value){mSlotBackHeld=false;return true;}
                if(mSlotBackHeld)return true;mSlotBackHeld=true;
                mSlotDirectionHeld=0;mSlotHeldAxes[0]=mSlotHeldAxes[1]=0;mList.stopScrolling();
                if(mSlot.inspecting()){if(mSlot.inspectionOpen())mSlot.inspect(false);return true;}
                if(mSlot.tvControls()){mSlot.controlTV(false);updateHelpPrompts();return true;}
                if(mSlot.state.preparing()||mSlot.state.closing()){mSlot.state.park();return true;}
                if(mSlot.state.launching())return true;
                if(mSlot.state.busy()||!mSlot.state.inserted().empty()){mSlot.eject();updateHelpPrompts();return true;}
                if(slot::roomReturn(mRoot->getSystem()->getName()))return true;
                return ISimpleGameListView::input(config,event);
            }
            // Select is deferred until release so a camera chord never opens options
            // or toggles favorites. Its ordinary short/long actions remain available.
            if(config->isMappedTo("select",event)) {
                if(event.value){if(!mSlotSelectHeld){mSlotSelectHeld=true;mSlotSelectUsed=false;mSlotSelectMs=0;}}
                else if(mSlotSelectHeld){
                    mSlotSelectHeld=false;
                    if(!mSlotSelectUsed&&!mSlot.inspecting()) {
                        if(mSlotSelectMs>=500)toggleFavoritesFilter();
                        else{Input press=event;press.value=1;ISimpleGameListView::input(config,press);ISimpleGameListView::input(config,event);}
                    }
                }return true;
            }
            // L3 inspects the highlighted loose cart (replacing the save-state shortcut
            // here only); while open the D-pad turns it and B or L3 puts it back.
            if(mSlot.inspecting()) {
                if(event.value && (config->isMappedTo("l3",event) || config->isMappedTo(BUTTON_BACK,event))) {
                    if(mSlot.inspectionOpen()){mSlot.inspect(false);updateHelpPrompts();}
                    return true;
                }
                const bool left=config->isMappedLike("left",event),right=config->isMappedLike("right",event);
                const bool up=config->isMappedLike("up",event),down=config->isMappedLike("down",event);
                if(left || right || up || down) {
                    // A hat reports both axes at once; sticks and keys one axis per event.
                    if(event.type==TYPE_HAT){mSlotSpin[0]=!event.value?0:left?-1:right?1:0;mSlotSpin[1]=!event.value?0:up?-1:down?1:0;}
                    else {
                        if(left || right)mSlotSpin[0]=!event.value?0:left?-1:1;
                        if(up || down)mSlotSpin[1]=!event.value?0:up?-1:1;
                    }
                    mSlot.spin(mSlotSpin[0],mSlotSpin[1]);
                }
                return true;
            }
            if(config->isMappedTo("l3",event)) {
                if(event.value && mSlot.inspect(true)){mList.stopScrolling();mSlotSpin[0]=mSlotSpin[1]=0;updateHelpPrompts();}
                return true;
            }
            // Right stick X is otherwise unused here (its Y axis stays volume).
            if(config->isMappedTo("joystick2left",event) || config->isMappedTo("joystick2left",event,true)) {
                mSlot.orbit(!event.value?0:config->isMappedTo("joystick2left",event)?-1:1);return true;
            }
            if(config->isMappedTo("r3",event)) {
                if(!event.value)mSlotCarouselHeld=false;
                else if(!mSlotCarouselHeld){
                    mSlotCarouselHeld=true;
                    if(mSlot.roomControls()){
                        if(mSlotSelectHeld)mSlotSelectUsed=true;
                        mSlot.controlTV(false);mSlot.cycleCamera();mSlotDirectionHeld=0;mSlotHeldAxes[0]=mSlotHeldAxes[1]=0;
                    }else if(mSlotSelectHeld){mSlotSelectUsed=true;mSlot.cycleCamera();}else mSlotFullCarousel=!mSlotFullCarousel;
                    mList.stopScrolling();updateHelpPrompts();
                }
                return true;
            }
            if(mSlot.roomControls() && config->isMappedTo(BUTTON_OK,event) && (mSlot.tvSelected()||mSlot.tvControls())) {
                if(!event.value)mSlotConfirmHeld=false;
                else if(!mSlotConfirmHeld){mSlotConfirmHeld=true;if(mSlot.tableReady()){mSlot.controlTV(true);updateHelpPrompts();}}
                return true;
            }
            if(config->isMappedTo(BUTTON_BACK,event) && (mSlotFullCarousel || mSlot.state.preparing())) {
                if(event.value){mSlotFullCarousel=false;mSlot.state.cancelLaunch();mList.stopScrolling();}return true;
            }
            if(config->isMappedTo(BUTTON_OK,event) && getCursor() && getCursor()->getType()==GAME) {
                if(!event.value)mSlotConfirmHeld=false;
                else if(!mSlotConfirmHeld) {
                    mSlotConfirmHeld=true;mList.stopScrolling();
                    if(!mSlot.tableReady())return true;
                    const auto id=getCursor()->getSourceFileData()->getPath();
                    if(!mSlot.state.launching()) {
                        if(!mSlot.state.busy() && mSlot.state.inserted()==id)launchSelectedGame();
                        else mSlot.insert(getCursor());
                    }
                }return true;
            }
        }
        const bool up=config->isMappedLike("up",event);
        const bool down=config->isMappedLike("down",event);
        if(mSlot.roomControls()) {
            const bool left=config->isMappedLike("left",event),right=config->isMappedLike("right",event);
            if(left||right||up||down) {
                if(event.type==TYPE_HAT){mSlotHeldAxes[0]=!event.value?0:left?-1:right?1:0;mSlotHeldAxes[1]=!event.value?0:up?-2:down?2:0;}
                else {if(left||right)mSlotHeldAxes[0]=!event.value?0:left?-1:1;if(up||down)mSlotHeldAxes[1]=!event.value?0:up?-2:2;}
                const int direction=event.value?(left||right?mSlotHeldAxes[0]:mSlotHeldAxes[1]):mSlotHeldAxes[0]?mSlotHeldAxes[0]:mSlotHeldAxes[1];
                mList.stopScrolling();
                if(direction!=mSlotDirectionHeld){mSlotDirectionHeld=direction;mSlotNavMs=0;mSlotNavRepeat=350;if(direction)moveSlotCursor(direction);}
                return true;
            }
        }
        // Hat neutral matches every direction on that hat. Forward it before
        // consuming Up/Down, otherwise Left/Right's repeat velocity survives.
        if(!event.value && (up || down || config->isMappedLike("left",event) || config->isMappedLike("right",event))) {
            mSlotDirectionHeld=0;mList.input(config,event);return true;
        }
        if(up || down) {
            const int direction=down?1:-1;
            if(!event.value)mSlotDirectionHeld=0;
            else if(mSlotDirectionHeld!=direction) {
                mSlotDirectionHeld=direction;
                mList.stopScrolling();
                if(down)mSlot.insert(getCursor());else mSlot.eject();
            }
            return true;
        }
        if((mSlot.hasScene() || (mSlot.roomControls()&&mSlot.tvControls())) && (config->isMappedLike("pageup",event) || config->isMappedLike("pagedown",event))) {
            if(event.value)mSlot.page(config->isMappedLike("pagedown",event)?1:-1);
            return true;
        }
    }
    return ISimpleGameListView::input(config,event);
}

void CarouselGameListView::moveSlotCursor(int direction) {
    if(!mSlot.navigationReady()||mList.size()==0)return;
    if(mSlot.tvControls()){mSlot.page(direction>0?1:-1);return;}
    const int first=(mList.getCursorIndex()/12)*12;
    const int next=mSlot.spatialSelection(direction);
    if(next>=0 && first+next<mList.size())mList.setCursorIndex(first+next);
    else if(next==slot_navigation::noTarget&&!mSlot.tvSelected()) {
        int page=first+(direction>0?12:-12);
        if(page<0)page=((mList.size()-1)/12)*12;else if(page>=mList.size())page=0;
        if(page!=first){const int entry=mSlot.spatialEdgeEntry(direction,std::min(12,mList.size()-page));if(entry>=0)mList.setCursorIndex(page+entry);}
    }
    updateHelpPrompts();
}

bool CarouselGameListView::queueSlotLaunch(FileData* game,const LaunchGameOptions& options,Vector3f center) {
    if(!mSlotEnabled || mSlotLaunchDispatch)return false;
    if(mSlot.state.launching())return true;
    mSlotLaunchOptions=options;mSlotLaunchCenter=center;
    mSlotFullCarousel=false;mSlot.carousel(false);
    return mSlot.play(game);
}

std::vector<HelpPrompt> CarouselGameListView::getHelpPrompts() {
    auto prompts=ISimpleGameListView::getHelpPrompts();
    if(mSlotEnabled) {
        if(mSlot.hasTabletop()) {
            if(mSlot.inspectionOpen())return {HelpPrompt("up/down/left/right","TURN"),HelpPrompt(BUTTON_BACK,"PUT BACK")};
            for(auto& prompt:prompts)if(prompt.first==BUTTON_OK)prompt.second="INSERT / PLAY";
            prompts.push_back(HelpPrompt("r3",mSlot.roomControls()?"CAMERA":mSlotFullCarousel?"TABLETOP":"CAROUSEL"));
            prompts.push_back(HelpPrompt("l3","INSPECT"));
            for(auto& prompt:prompts)if(prompt.first=="select")prompt.second=mSlot.roomControls()?"OPTIONS / HOLD FAVOURITES":"OPTIONS / HOLD + R3 CAMERA";
            if(mSlot.roomControls())for(auto&prompt:prompts){
                if(prompt.first=="left/right"){prompt.first="up/down/left/right";prompt.second="BROWSE";}
                if(prompt.first==BUTTON_OK)prompt.second=mSlot.tvSelected()?"TV CONTROLS":"INSERT / PLAY";
                if(prompt.first==BUTTON_BACK)prompt.second=mSlot.tvControls()?"TABLETOP":mSlot.state.inserted().empty()?"BACK":"EJECT";
            }
        }else prompts.push_back(HelpPrompt("down","INSERT"));
        if(!mSlot.roomControls())prompts.push_back(HelpPrompt("up","EJECT"));
        if(mSlot.hasScene())prompts.push_back(HelpPrompt("l1/r1","DISPLAY PAGE"));
    }
    return prompts;
}
'''
    edits[path]=content
    path='es-app/src/views/ViewController.cpp'
    content=original(source,path)
    content=change(content,'#include "views/ViewController.h"','#include "views/ViewController.h"\n#include "views/gamelist/CarouselGameListView.h"\n#include "components/SlotScenePreview.h"\n#include "components/SlotThemeRoot.h"\n#include "components/SlotRoomHost.h"\n#include "components/SlotRoomSession.h"\n#include "components/SlotRoomRoutes.h"\n#include "SlotRoomTiming.h"')
    content=change(content,'ViewController::~ViewController()\n{','ViewController::~ViewController()\n{\n    SlotPresentation::shutdownTabletop();')
    # Diagnostic probes (inert unless SLOT_SCENE_ROOMLOG is set).
    content=change(content,'void ViewController::goToSystemView(SystemData* system, bool forceImmediate)\n{','void ViewController::goToSystemView(SystemData* system, bool forceImmediate)\n{\n    SlotRoomProbe slotProbe("vc-goToSystemView");')
    content=change(content,'void ViewController::reloadAll(Window* window, bool reloadTheme)\n{','void ViewController::reloadAll(Window* window, bool reloadTheme)\n{\n    SlotRoomProbe slotProbe("vc-reloadAll");')
    content=change(content,'std::shared_ptr<IGameListView> ViewController::getGameListView(SystemData* system, bool loadIfnull, const std::function<void()>& createAsPopupAndSetExitFunction)\n{','std::shared_ptr<IGameListView> ViewController::getGameListView(SystemData* system, bool loadIfnull, const std::function<void()>& createAsPopupAndSetExitFunction)\n{\n    const std::string slotLabel=std::string("vc-getGameListView:")+(system?system->getName():std::string());SlotRoomProbe slotProbe(slotLabel.c_str());')
    content=change(content,'void ViewController::goToGameList(SystemData* system, bool forceImmediate)\n{','''void ViewController::goToGameList(SystemData* system, bool forceImmediate)
{
    SlotRoomProbe slotProbe("vc-goToGameList");
    if(slot::roomControls()&&system&&!slot::roomSession().originTarget().empty()&&slot::roomSession().originTarget()!=system->getName())slot::roomSession().clearOrigin();
    auto* previousSlot=dynamic_cast<CarouselGameListView*>(mCurrentView.get());
    const bool wasTabletop=previousSlot && previousSlot->ownsSlotTabletop();''')
    content=change(content,'\tmDeferPlayViewTransitionTo = nullptr;\n\n\tif (forceImmediate || Settings::TransitionStyle() == "fade")','''\tmDeferPlayViewTransitionTo = nullptr;
    auto* nextSlot=dynamic_cast<CarouselGameListView*>(view.get());
    if(wasTabletop && nextSlot && nextSlot->prepareSlotTabletop()) {
        // The persistent 3D session owns system transitions. Keep ordinary
        // system menus, non-tabletop views and real game launch transitions.
        cancelAnimation(0);mFadeOpacity=0;
        if(mCurrentView)mCurrentView->onHide();mCurrentView=view;mCurrentView->onShow();
        mCamera.translation()=-view->getPosition();updateHelpPrompts();return;
    }
\tif (forceImmediate || Settings::TransitionStyle() == "fade")''')
    content=change(content,'bool ViewController::doLaunchGame(FileData* game, LaunchGameOptions options)\n{\n\tif (mCurrentView) mCurrentView->onHide();','''bool ViewController::doLaunchGame(FileData* game, LaunchGameOptions options)
{
\tif (mCurrentView) mCurrentView->onHide();
    // Prediction/cache memory is returned before the normal emulator owner runs.
    slot::RoomExecution roomExecution;
    SlotPresentation::shutdownTabletop();''')
    content=change(content,'void ViewController::goToStart(bool forceImmediate)\n{','''void ViewController::goToStart(bool forceImmediate)
{
    if(slot::roomControls()&&!slot::scenePreviewActive()){
        for(auto*system:SystemData::sSystemVector)if(system->isVisible()&&!system->isGroupChildSystem()){goToSystemView(system,true);return;}
    }
    if(slot::scenePreviewActive()) {
        auto* previewSystem=SystemData::getSystem(slot::scenePreviewSystem());
        if(previewSystem && !previewSystem->isGroupChildSystem()) {
            goToGameList(previewSystem,forceImmediate);
            return;
        }
    }''')
    content=change(content,'\tTransform4x4f origCamera = mCamera;','''    // Ordinary launch validation above remains the sole authority. Seating is
    // deferred only for the opted-in shelf; no fake game launch is performed.
    auto* slotSource=game->getSourceFileData()->getSystem();
    if(slot::roomControls()&&!slot::roomDirectLaunch()&&mState.getSystem()!=slotSource&&slot::roomOpenGame(mState.getSystem(),game))return;
    auto* slotView=dynamic_cast<CarouselGameListView*>(mCurrentView.get());
    if(slotView && slotView->queueSlotLaunch(game,options,center))return;

\tTransform4x4f origCamera = mCamera;''')
    content=change(content,'''	if (((mState.viewing != GAME_LIST && config->isMappedTo("l3", input)) || config->isMappedTo("r3", input)) && input.value != 0)''','''	auto* slotInputView=dynamic_cast<CarouselGameListView*>(mCurrentView.get());
	const bool slotCarouselButton=mState.viewing==GAME_LIST && slotInputView && slotInputView->ownsSlotCarouselButton();
	if (((mState.viewing != GAME_LIST && config->isMappedTo("l3", input)) || (config->isMappedTo("r3", input) && !slotCarouselButton)) && input.value != 0)''')
    edits[path]=content
    # Room navigation has one immediate view handoff; native hardware and the
    # world camera animate independently of ES's screen/fade transitions.
    content=change(content,'bool ViewController::input(InputConfig* config, Input input)\n{','bool ViewController::input(InputConfig* config, Input input)\n{\n    slot::roomMenuTheme();')
    content=change(content,'if (((mState.viewing != GAME_LIST','if (!slot::roomControls() && ((mState.viewing != GAME_LIST')
    content=change(content,'if (forceImmediate || Settings::TransitionStyle() == "fade")','if (slot::roomControls() || forceImmediate || Settings::TransitionStyle() == "fade")')
    content=change(content,'void ViewController::playViewTransition(bool forceImmediate)\n{','''void ViewController::playViewTransition(bool forceImmediate)
{
    if(slot::roomControls()){
        cancelAnimation(0);mFadeOpacity=0;
        if(mCurrentView){mCurrentView->onShow();mCamera.translation()=-mCurrentView->getPosition();}
        updateHelpPrompts();return;
    }''')
    content=change(content,'\t// Create the view\n\tswitch (selectedViewType)','''    if(slot::roomControls()&&!system->isCollection()&&themeHasGamecarouselView&&!slot::roomModel(system->getName()).empty()){
        selectedViewType=GAMECAROUSEL;customThemeName.clear();
    }
\t// Create the view
\tswitch (selectedViewType)''')
    edits[path]=content
    path='es-app/src/services/HttpServerThread.cpp'
    content=original(source,path)
    content='#include "components/SlotRoomRoutes.h"\n'+content
    content=change(content,'mWindow->postToUiThread([file]() { ViewController::get()->launch(file); });','mWindow->postToUiThread([file]() { slot::RoomDirectLaunch direct; ViewController::get()->launch(file); });')
    edits[path]=content
    path='es-app/src/views/gamelist/ISimpleGameListView.cpp'
    content=original(source,path)
    content='#include "components/SlotRoomRoutes.h"\n'+content
    content=change(content,'void ISimpleGameListView::launchSelectedGame()\n{','''void ISimpleGameListView::launchSelectedGame()
{
    if(slot::roomCollection(mRoot->getSystem(),getCursor()))return;''')
    edits[path]=content
    path='es-app/src/views/SystemView.h'
    content=original(source,path)
    content=change(content,'#include "SystemViewControlWrapper.h"','#include "SystemViewControlWrapper.h"\n#include "components/SlotHome.h"')
    content=change(content,'\tControlWrapper','    slot::Home mSlotHome;\n\tControlWrapper')
    edits[path]=content
    path='es-app/src/views/SystemView.cpp'
    content=original(source,path)
    content=change(content,'#include "views/SystemView.h"','#include "views/SystemView.h"\n#include "components/SlotThemeRoot.h"\n#include "SlotRoomTiming.h"')
    content=change(content,'SystemView::SystemView(Window* window) : GuiComponent(window),','SystemView::SystemView(Window* window) : GuiComponent(window), mSlotHome(window),')
    content=change(content,'bool SystemView::input(InputConfig* config, Input input)\n{','''bool SystemView::input(InputConfig* config, Input input)
{
    if(slot::roomControls())return mSlotHome.input(config,input,getObjects());''')
    content=change(content,'void SystemView::render(const Transform4x4f& parentTrans)\n{','''void SystemView::render(const Transform4x4f& parentTrans)
{
    if(slot::roomControls()){SlotRoomStage slotStage(SlotRoomStage::Home);mSlotHome.render(getObjects());return;}''')
    content=change(content,'void SystemView::update(int deltaTime)\n{','''void SystemView::update(int deltaTime)
{
    if(slot::roomControls()){mSlotHome.update(deltaTime);GuiComponent::update(deltaTime);return;}''')
    content=change(content,'void SystemView::onShow()\n{','''void SystemView::onShow()
{
    if(slot::roomControls())mSlotHome.show();''')
    content=change(content,'std::vector<HelpPrompt> SystemView::getHelpPrompts()\n{','''std::vector<HelpPrompt> SystemView::getHelpPrompts()
{
    if(slot::roomControls())return {HelpPrompt("up/down/left/right","BROWSE"),HelpPrompt(BUTTON_OK,"OPEN"),HelpPrompt(BUTTON_BACK,"BACK"),HelpPrompt("r3","CAMERA"),HelpPrompt("start","MENU")};''')
    edits[path]=content
    path='es-app/src/main.cpp'
    content=original(source,path)
    content=change(content,'static bool enable_startup_game = true;','#include "components/SlotScenePreview.h"\n#include "components/SlotThemeRoot.h"\n#include "components/SlotRoomHost.h"\nstatic bool enable_startup_game = true;')
    # Subscribe to watcher changes before their first checks (5 s after this),
    # so the room's status seed never waits on the watcher thread's lock.
    content=change(content,'NetworkThread* nthread = new NetworkThread(&window);','NetworkThread* nthread = new NetworkThread(&window);\n\tslot::roomStartup();')
    content=change(content,'if(enable_startup_game) {','if(enable_startup_game && !slot::scenePreviewActive() && !slot::roomControls()) {')
    content=change(content,'bool splashScreen = Settings::getInstance()->getBool("SplashScreen");','bool splashScreen = slot::roomControls() || Settings::getInstance()->getBool("SplashScreen");')
    edits[path]=content
    path='es-core/src/Window.h'
    content=original(source,path)
    content=change(content,'\tvoid render();\n','\tvoid render();\n\tvoid renderContents(); // ordinary GUI stack, optionally on the room TV\n')
    edits[path]=content
    path='es-core/src/Window.cpp'
    content=original(source,path)
    content=change(content,'#include "Window.h"','#include "Window.h"\n#include "SlotRoomTiming.h"')
    # Diagnostic only: splits room frame-log stalls into input/update time.
    content=change(content,'void Window::input(InputConfig* config, Input input)\n{','void Window::input(InputConfig* config, Input input)\n{\n    SlotRoomStage slotStage(SlotRoomStage::Input);')
    content=change(content,'void Window::update(int deltaTime)\n{','void Window::update(int deltaTime)\n{\n    SlotRoomStage slotStage(SlotRoomStage::Update);')
    content=change(content,'void Window::render()\n{\n\tTransform4x4f transform','''bool slotRoomRenderWindow(Window* window);
void Window::render()
{
    if(!slotRoomRenderWindow(this))renderContents();
}
void Window::renderContents()
{
\tTransform4x4f transform''')
    content=change(content,'void Window::renderSplashScreen(std::string text, float percent, float opacity)\n{','''bool slotRoomSplash(Window* window,bool swap);
void Window::renderSplashScreen(std::string text, float percent, float opacity)
{
    if(slotRoomSplash(this,true))return;''')
    content=change(content,'void Window::renderSplashScreen(float opacity, bool swapBuffers)\n{','''void Window::renderSplashScreen(float opacity, bool swapBuffers)
{
    if(slotRoomSplash(this,swapBuffers))return;''')
    edits[path]=content
    path='es-core/src/renderers/Renderer.cpp'
    content=original(source,path)
    content=change(content,'#include <stack>','#include <stack>\n#include <array>')
    content=change(content,'\t\tsetupWindow();','''        const auto slotTheme=Settings::getInstance()->getString("ThemeSet");
        if(slotTheme=="Slotted"||slotTheme=="slotted"){
            // Frontend widgets use the measured 4:3 TV canvas. The room is
            // composited separately at the physical window resolution.
            screenWidth=640;screenHeight=480;screenOffsetX=screenOffsetY=screenRotate=0;
        }
\t\tsetupWindow();''')
    content=change(content,'\tint         getWindowHeight()  { return windowHeight; }','''    static int slotTargetHeight=0;
    static std::stack<std::array<int,8>> slotTargets;
    int slotOutputHeight(){return windowHeight;}
    void slotPushTarget(int width,int height){
        slotTargets.push({screenWidth,screenHeight,screenOffsetX,screenOffsetY,screenRotate,screenMargin.x(),screenMargin.y(),slotTargetHeight});
        screenWidth=width;screenHeight=height;screenOffsetX=screenOffsetY=screenRotate=0;screenMargin=Vector2i(0,0);slotTargetHeight=height;
        updateProjection();
    }
    void slotPopTarget(){
        if(slotTargets.empty())return;const auto old=slotTargets.top();slotTargets.pop();
        screenWidth=old[0];screenHeight=old[1];screenOffsetX=old[2];screenOffsetY=old[3];screenRotate=old[4];screenMargin=Vector2i(old[5],old[6]);slotTargetHeight=old[7];
        updateProjection();
    }
\tint         getWindowHeight()  { return slotTargetHeight?slotTargetHeight:windowHeight; }''')
    edits[path]=content
    path='es-core/src/components/HelpComponent.cpp'
    content=original(source,path)
    content=change(content,'\tauto pathLookup = ICON_PATH_MAP.find(name);','''    const auto slotTheme=Settings::getInstance()->getString("ThemeSet");
    if((slotTheme=="Slotted"||slotTheme=="slotted")&&(std::string(name)=="r3"||std::string(name)=="l3")){
        const auto file="/userdata/themes/"+slotTheme+"/_tv/help-"+name+".svg";
        if(ResourceManager::getInstance()->fileExists(file)){auto tex=TextureResource::get(file);mIconCache[name]=tex;return tex;}
    }
\tauto pathLookup = ICON_PATH_MAP.find(name);''')
    edits[path]=content
    path='es-core/src/components/CarouselComponent.h'
    content=original(source,path)
    content=change(content,'\tfloat getTransitionSpeed() { return mTransitionSpeed; }','''\tfloat getTransitionSpeed() { return mTransitionSpeed; }
    void setSlotInteraction(bool enabled) {mSlotInteraction=enabled;mSlotIdleTime=0;}
    void setSlotInserted(const std::string& path) {mSlotInserted=path;}
    void setSlotScene(bool scene) {mSlotScene=scene;}
    void resetSlotIdle() {mSlotIdleTime=0;}
    float slotIdleOffset() const;
    std::vector<IBindable*> slotObjects() {
        std::vector<IBindable*> result;int first=(getCursorIndex()/12)*12;
        for(int i=first;i<std::min(first+12,size());i++)result.push_back(mEntries[i].object);
        return result;
    }''')
    content=change(content,'\tbool mDisable;','''\tbool mDisable;
    void renderSlotStrip(const Transform4x4f& parentTrans);
    bool mSlotInteraction=false, mSlotScene=false;
    float mSlotIdleTime=0;
    std::string mSlotInserted;
    TextComponent mSlotMarker;''')
    edits[path]=content
    path='es-core/src/components/CarouselComponent.cpp'
    content=original(source,path)
    content=change(content,'IList<CarouselComponentData, IBindable*>(window, LIST_SCROLL_STYLE_SLOW, LIST_ALWAYS_LOOP)','IList<CarouselComponentData, IBindable*>(window, LIST_SCROLL_STYLE_SLOW, LIST_ALWAYS_LOOP), mSlotMarker(window)')
    content=change(content,'void CarouselComponent::update(int deltaTime)\n{','''float CarouselComponent::slotIdleOffset() const {
    if(!mSlotInteraction || mDisable || mScreensaverActive || mSlotIdleTime<4)return 0;
    const float phrase=fmod(mSlotIdleTime-4,10.f);
    if(phrase>1.8f)return 0;
    const float wave=sin(3.14159265f*phrase/1.8f);
    return -2.f*wave*wave;
}
void CarouselComponent::update(int deltaTime)
{
    if(mSlotInteraction) {
        if(mDisable || mScreensaverActive || isScrolling())mSlotIdleTime=0;
        else mSlotIdleTime+=std::max(0,std::min(deltaTime,100))/1000.f;
    }''')
    content=change(content,'void CarouselComponent::onCursorChanged(const CursorState& state)\n{','void CarouselComponent::onCursorChanged(const CursorState& state)\n{\n    mSlotIdleTime=0;')
    content=change(content,'void CarouselComponent::render(const Transform4x4f& parentTrans)\n{','''void CarouselComponent::render(const Transform4x4f& parentTrans)
{
    if(mSlotScene && mVisible && size()>0) {
        Renderer::pushClipRect(0,0,720,120);renderSlotStrip(parentTrans);Renderer::popClipRect();return;
    }''')
    content=change(content,'\t\tcomp->render(logoTrans);','''        const bool inserted=mSlotInteraction && !mSlotInserted.empty()
            && mEntries.at(index).object->getProperty("path").toString()==mSlotInserted;
        if(inserted) {
            const auto marker=comp->getTransform()*logoTrans;
            Renderer::setMatrix(marker);
            const auto size=comp->getSize();
            Renderer::drawSolidRectangle(12,12,size.x()-24,size.y()-24,0x151A20B0,0xAAA694FF,3,12);
            mSlotMarker.setFont(Font::get(46));mSlotMarker.setColor(0xF6F4EFFF);
            mSlotMarker.setHorizontalAlignment(ALIGN_CENTER);
            mSlotMarker.setSize(size.x(),80);mSlotMarker.setPosition(0,size.y()/2-40);
            mSlotMarker.setText("INSERTED");mSlotMarker.render(marker);
        } else {
            if(index==mCursor)logoTrans.translate(Vector3f(0,slotIdleOffset(),0));
            comp->render(logoTrans);
        }''')
    content+='''
void CarouselComponent::renderSlotStrip(const Transform4x4f& parentTrans) {
    const int centre=int(floor(mCamOffset));
    for(int i=centre-4;i<=centre+4;i++) {
        int index=i%int(mEntries.size());if(index<0)index+=mEntries.size();
        ensureLogo(mEntries.at(index));auto comp=mEntries.at(index).data.logo;
        const auto size=comp->getSize();if(size.x()<=0 || size.y()<=0)continue;
        const bool active=index==mCursor;
        const float scale=std::min(126.f/size.x(),78.f/size.y())*(active?1.f:.82f);
        const float w=size.x()*scale,h=size.y()*scale,x=360+(i-mCamOffset)*118,y=112-h+(active?slotIdleOffset()*.3f:0);
        const bool inserted=!mSlotInserted.empty() && mEntries.at(index).object->getProperty("path").toString()==mSlotInserted;
        if(inserted) {
            Renderer::setMatrix(parentTrans);
            Renderer::drawSolidRectangle(x-w/2,y,w,h,0x151A20B0,0xAAA694FF,1,4);
            mSlotMarker.setFont(Font::get(14/Renderer::ScreenSettings::fontScale()));mSlotMarker.setColor(0xF6F4EFFF);
            mSlotMarker.setHorizontalAlignment(ALIGN_CENTER);mSlotMarker.setSize(w,22);mSlotMarker.setPosition(x-w/2,y+h/2-11);
            mSlotMarker.setText("INSERTED");mSlotMarker.render(parentTrans);
        }else {
            auto position=comp->getPosition();auto origin=comp->getOrigin();auto previousScale=comp->getScale();
            comp->setPosition(0,0);comp->setOrigin(0,0);comp->setScale(scale);
            auto trans=parentTrans;trans.translate(x-w/2,y);comp->render(trans);
            comp->setPosition(position);comp->setOrigin(origin);comp->setScale(previousScale);
        }
    }
}
'''
    edits[path]=content
    path='es-core/src/components/VideoVlcComponent.h'
    content=original(source,path)
    content=change(content,'\tvoid render(const Transform4x4f& parentTrans) override;', '''\tvoid render(const Transform4x4f& parentTrans) override;
    // Upload once; callers may sample one decoder on several physical screens.
    bool bindSlotFrame(float* sourceBounds=nullptr);''')
    content=change(content,'\tstd::shared_ptr<TextureResource> mTexture;', '''\tstd::shared_ptr<TextureResource> mTexture;
    std::string mSlotFramePath;
    float mSlotCrop[4]={0,0,1,1},mSlotCandidate[4]={1,1,0,0};
    int mSlotCropSamples=0,mSlotProbeFrames=0;''')
    edits[path]=content
    path='es-core/src/components/VideoVlcComponent.cpp'
    content=original(source,path)
    content+='''
#include "SlotVideo.h"
bool VideoVlcComponent::bindSlotFrame(float* sourceBounds) {
    // SlotPresentation owns the three-second delay and configures zero here.
    handleLooping();
    if(!mIsPlaying || !mContext.valid || mPlayingVideoPath!=mVideoPath)return false;
    if(mSlotFramePath!=mPlayingVideoPath) {
        mTexture.reset();mSlotFramePath=mPlayingVideoPath;mSlotCropSamples=mSlotProbeFrames=0;
        for(int i=0;i<4;i++){mSlotCrop[i]=i<2?0:1;mSlotCandidate[i]=i<2?1:0;}
    }
    const int frame=mContext.surfaceId;
    {
        std::lock_guard<std::mutex> lock(mContext.mutexes[frame]);
        if(mContext.hasFrame[frame]) {
            if(sourceBounds && mSlotCropSamples<12 && (mSlotProbeFrames++<180 || mSlotProbeFrames%30==0)) {
                float candidate[4];
                if(slot::stackedVideoBounds(mContext.surfaces[frame],mVideoWidth,mVideoHeight,candidate)) {
                    for(int i=0;i<4;i++)mSlotCandidate[i]=i<2?std::min(mSlotCandidate[i],candidate[i]):std::max(mSlotCandidate[i],candidate[i]);
                    if(++mSlotCropSamples==12)for(int i=0;i<4;i++)mSlotCrop[i]=mSlotCandidate[i];
                }else {
                    mSlotCropSamples=0;for(int i=0;i<4;i++)mSlotCandidate[i]=i<2?1:0;
                }
            }
            if(!mTexture)mTexture=TextureResource::get("",false,true);
            mTexture->updateFromExternalPixels(mContext.surfaces[frame],mVideoWidth,mVideoHeight);
            mContext.hasFrame[frame]=false;
        }
    }
    if(sourceBounds)for(int i=0;i<4;i++)sourceBounds[i]=mSlotCrop[i];
    return mTexture && mTexture->bind();
}
'''
    edits[path]=content
    path='es-app/CMakeLists.txt'
    content=original(source,path)
    content=change(content,'set(ES_SOURCES','set(ES_SOURCES\n    ${CMAKE_CURRENT_SOURCE_DIR}/src/components/SlotRoomRoutes.cpp\n    ${CMAKE_CURRENT_SOURCE_DIR}/src/components/SlotHome.cpp\n    ${CMAKE_CURRENT_SOURCE_DIR}/src/components/SlotRoomHost.cpp\n    ${CMAKE_CURRENT_SOURCE_DIR}/src/components/SlotPresentation.cpp\n    ${CMAKE_CURRENT_SOURCE_DIR}/src/components/SlotTabletop.cpp\n    ${CMAKE_CURRENT_SOURCE_DIR}/src/components/SlotNative.c')
    # Adapt private copies of the existing scene renderer. The standalone helper
    # and its accepted mechanics keep their existing choreography.
    scene=source/'es-app/src/components/slot-scene'
    scene.mkdir(parents=True,exist_ok=True)
    for native in (HERE.parent/'slotlaunch').iterdir():
        if native.suffix not in ('.c','.h'):continue
        data=native.read_text(encoding='utf-8')
        if native.name=='psx.h':
            data=change(data,'static double psx_depth(PsxVec a) { return a.y*sin(PSX_PHI)+a.z*cos(PSX_PHI); }','''static PsxVec slot_camera_point(PsxVec a) {
    return (PsxVec){slot_camera_matrix[0]*a.x+slot_camera_matrix[4]*a.y+slot_camera_matrix[8]*a.z,
        slot_camera_matrix[1]*a.x+slot_camera_matrix[5]*a.y+slot_camera_matrix[9]*a.z,
        slot_camera_matrix[2]*a.x+slot_camera_matrix[6]*a.y+slot_camera_matrix[10]*a.z};
}
static double psx_depth(PsxVec a) {a=slot_camera_point(a);return a.y*sin(PSX_PHI)+a.z*cos(PSX_PHI);}''')
            data=change(data,'    double k=1200/(1200-psx_depth(a));','    a=slot_camera_point(a);\n    double k=1200/(1200-a.y*sin(PSX_PHI)-a.z*cos(PSX_PHI));')
        if native.name=='console-gl.h':
            data=change(data,'cgRenderbufferStorage(GL_RENDERBUFFER,depth_format,WIDTH,HEIGHT);',
                'cgRenderbufferStorage(GL_RENDERBUFFER,depth_format,WIDTH*SLOT_RASTER_SCALE,HEIGHT*SLOT_RASTER_SCALE);')
            data=change(data,'    GLint program,buffer,indices,front,cull,depthfunc,active,bound,uv_enabled;', '''    GLint program,buffer,indices,front,cull,depthfunc,active,bound,uv_enabled;
    GLint viewport[4];cgGetIntegerv(GL_VIEWPORT,viewport);
    void (GL_APIENTRY *slotViewport)(GLint,GLint,GLsizei,GLsizei)=SDL_GL_GetProcAddress("glViewport");
    slotViewport(0,0,WIDTH*SLOT_RASTER_SCALE,HEIGHT*SLOT_RASTER_SCALE);''')
            data=change(data,'    if(scissor)cgEnable(GL_SCISSOR_TEST);',
                '    if(scissor)cgEnable(GL_SCISSOR_TEST);\n    slotViewport(viewport[0],viewport[1],viewport[2],viewport[3]);')
            data=change(data,'cgUniformMatrix4fv(m->transform,1,GL_FALSE,transform);','''
    float view_transform[16]={0};
    for(int col=0;col<4;col++)for(int row=0;row<4;row++)for(int k=0;k<4;k++)
        view_transform[4*col+row]+=slot_camera_matrix[4*k+row]*transform[4*col+k];
    cgUniformMatrix4fv(m->transform,1,GL_FALSE,view_transform);''')
        if native.name in ('cartridge-console.h','psp.h'):
            data=change(data,'    double origin=s->idle+(s->origin-s->idle)*rise;',
                '    double origin=s->idle+(s->origin-s->idle)*rise;\n    if(slot_presenting)origin+=(slot_view_origin-s->origin)*psx_ease(slot_presentation);')
        if native.name=='ps1-scene.h':
            data=change(data,'    double origin=s->idle+(s->origin-s->idle)*psx_ease(time/.19);',
                '    double origin=s->idle+(s->origin-s->idle)*psx_ease(time/.19);\n    if(slot_presenting)origin+=(slot_view_origin-s->origin)*psx_ease(slot_presentation);')
        if native.name=='psp.h':
            data=change(data,'    psp_slab(r,art,centre,u,v,radius,media_origin);',
                '    if(!slot_presenting)psp_slab(r,art,centre,u,v,radius,media_origin);')
        if native.name=='handheld-lids.h':
            data=data.replace('ags_lid_hinge','slot_model_hinge').replace('ags_lid_open_radians','slot_model_angle')
            data=change(data,'    float matrix[16];console_hinge_matrix(matrix,global,hinge,(ds?ds_lid_open_radians:slot_model_angle)*(1-opened));','''    double angle=(ds?ds_lid_open_radians:slot_model_angle)*(1-opened);
    if(slot_presenting && ds)angle-=(PSX_PI-ds_lid_open_radians)*psx_ease(slot_presentation);
    float matrix[16];console_hinge_matrix(matrix,global,hinge,angle);''')
        target=scene/native.name
        if not target.exists() or target.read_text()!=data:target.write_text(data)
    helper=(scene/'slot-launch.c').as_posix()
    content+='\nset_source_files_properties(${CMAKE_CURRENT_SOURCE_DIR}/src/components/SlotNative.c PROPERTIES COMPILE_DEFINITIONS [=[SLOT_HELPER_SOURCE="'+helper+'"]=])\n'
    content+='target_link_libraries(emulationstation ${SLOT_SDL_IMAGE_LIBRARY})\n'
    edits[path]=content
    path='CMakeLists.txt'
    content=original(source,path)
    content=change(content,'COMMAND "${PYTHON3_EXECUTABLE}" "resources/checkWheelGunGamesResources.py"','COMMAND "${PYTHON3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/resources/checkWheelGunGamesResources.py" WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"')
    edits[path]=content
    path='external/libcheevos/CMakeLists.txt'
    content=original(source,path)
    content='include_directories(BEFORE ${CMAKE_CURRENT_SOURCE_DIR}/libretro-common/include)\n'+content
    edits[path]=content
    path='es-core/src/utils/Platform.cpp'
    content=original(source,path)
    content=change(content,'#include "Platform.h"','#include "Platform.h"\n#include <cmath>')
    edits[path]=content
    # The main menu's version line ran knulli-version (~40 ms) up to four times per Start
    # press (getApplicationName calls getVersion too). Neither changes while the frontend
    # runs (updates restart it), so the label's inputs are read once per run.
    path='es-app/src/guis/GuiMenu.cpp'
    content=original(source,path)
    content=change(content,'''	std::string label;

	if (!ApiSystem::getInstance()->getVersion().empty())
	{
		if (ApiSystem::getInstance()->getApplicationName() == "BATOCERA")
			label = "BATOCERA.LINUX ES V" + ApiSystem::getInstance()->getVersion() + buildDate;
		else
		{
			std::string aboutInfo = ApiSystem::getInstance()->getApplicationName() + " " + ApiSystem::getInstance()->getVersion();''','''	std::string label;
	static const std::string slotVersion = ApiSystem::getInstance()->getVersion();
	static const std::string slotApplication = slotVersion.empty() ? std::string() : ApiSystem::getInstance()->getApplicationName();

	if (!slotVersion.empty())
	{
		if (slotApplication == "BATOCERA")
			label = "BATOCERA.LINUX ES V" + slotVersion + buildDate;
		else
		{
			std::string aboutInfo = slotApplication + " " + slotVersion;''')
    edits[path]=content
    # As soon as a game exits, the room starts decoding the table/TV it reopens next.
    path='es-app/src/FileData.cpp'
    content=original(source,path)
    content=change(content,'#include "FileData.h"','#include "FileData.h"\n#include "components/SlotRoomHost.h"')
    content=change(content,'\tint exitCode = process.run();','\tint exitCode = process.run();\n\tslot::roomGameEnded();')
    edits[path]=content
    # Diagnostic probes for stock settings menus (inert unless SLOT_SCENE_ROOMLOG is set).
    path='es-app/src/guis/GuiSettings.cpp'
    content=original(source,path)
    content=change(content,'#include "guis/GuiSettings.h"','#include "guis/GuiSettings.h"\n#include "SlotRoomTiming.h"')
    content=change(content,'void GuiSettings::save()\n{','void GuiSettings::save()\n{\n    SlotRoomProbe slotProbe("settings-save");')
    content=change(content,'\tif (mOnFinalizeFunc != nullptr)\n\t\tmOnFinalizeFunc();','\tif (mOnFinalizeFunc != nullptr)\n\t{\n\t\tSlotRoomProbe slotProbe("settings-finalize");\n\t\tmOnFinalizeFunc();\n\t}')
    edits[path]=content
    for path,content in edits.items():
        destination=source/path
        if not destination.exists() or destination.read_text(encoding='utf-8',errors='surrogateescape')!=content:
            destination.write_text(content,encoding='utf-8',errors='surrogateescape')
    for path in (HERE/'overlay').rglob('*'):
        if path.is_file():
            target=source/path.relative_to(HERE/'overlay');target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() or path.read_bytes()!=target.read_bytes():shutil.copy2(path,target)
    state_target=source/'es-app/src/components/SlotState.h'
    if not state_target.exists() or state_target.read_bytes()!=(HERE/'SlotState.h').read_bytes():shutil.copy2(HERE/'SlotState.h',state_target)
    owned=set(edits)
    owned.update(path.relative_to(source).as_posix() for path in scene.iterdir() if path.is_file())
    owned.update(path.relative_to(HERE/'overlay').as_posix() for path in (HERE/'overlay').rglob('*') if path.is_file())
    owned.add('es-app/src/components/SlotState.h')
    record={path:hashlib.sha256((source/path).read_bytes()).hexdigest() for path in sorted(owned)}
    (source/'.git/slot-presentation-output.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Applied slot extension to',PIN)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    apply(parser.parse_args().source)
