// Opt-in physical-media presentation for Knulli 4041b56a (MIT).
#pragma once
#include "GuiComponent.h"
#include "components/ImageComponent.h"
#include "components/TextComponent.h"
#include "components/VideoVlcComponent.h"
#include "SlotNative.h"
#include "SlotTabletop.h"
#include "SlotState.h"
#include "SlotSpatialNavigation.h"
#include <string>
#include <map>
#include <memory>
#include <vector>

class FileData;
struct SlotTelevisionProfile;
class SlotPresentation : public GuiComponent {
    slot::State mLocalState;
    bool mRoomControls=false;std::string mRoomSystem,mRoomSourceSystem;
public:
    explicit SlotPresentation(Window* window,const std::string& system="");
    ~SlotPresentation();
    static std::string browseImage(FileData* game);
    slot::State& state;
    bool roomControls()const{return mRoomControls;}
    void leaveRoom();
    bool tvSelected()const{return mTableTVSelected;}
    bool tvControls()const{return mTableTVControls;}
    void controlTV(bool active);
    bool navigationReady()const{return tableReady()&&!mPaused&&!inspecting()&&!state.launching();}
    // -1 left, +1 right, -2 up, +2 down. Result: source window offset, TV -2,
    // or noTarget at an edge. Loaded media is independent of physical focus.
    int spatialSelection(int direction);
    int spatialEdgeEntry(int direction,int count);
    void highlight(FileData* game);
    void browse(const std::vector<FileData*>& games,FileData* selected);
    bool hasTabletop() const {return mTableAvailable;}
    bool tableReady() const {return liveTable(mTable)&&!mTableDirty&&slot_tabletop_ready(mTable);}
    static void shutdownTabletop();
    static bool liveTable(SlotTabletop*table);
    static SlotTabletop* homeTable(const std::vector<SlotTabletopItem>&items);
    // Loads and keeps the console view's text fonts (applyType(1)) during the startup
    // splash; the first console opened otherwise paid ~0.14 s for them.
    static void preloadType();
    void carousel(bool visible){mCarousel=visible;}
    // -1/0/+1 from the right stick's free horizontal axis; the scene clamps the yaw.
    void orbit(int direction){mOrbitGoal=direction*kOrbitDegrees;}
    void cycleCamera();
    static constexpr float kOrbitDegrees=8;
    // L3 inspection of the highlighted loose cart. inspecting() stays true while it
    // flies back, so browsing cannot swap the cart mid-flight.
    bool inspect(bool open);
    bool inspectionOpen() const {return mInspectOpen;}
    bool inspecting() const {return mInspectOpen || mInspect>0;}
    void spin(int horizontal,int vertical){mSpin[0]=horizontal;mSpin[1]=vertical;}
    bool insert(FileData* game);
    bool play(FileData* game);
    void eject();
    void reset();
    void update(int deltaTime) override;
    void render(const Transform4x4f& parentTrans) override;
    void onHide() override;
    void onShow() override;
    void onScreenSaverActivate() override;
    void onScreenSaverDeactivate() override;
    void topWindow(bool top) override;
    bool hasScene() const { return state.phase()!=slot::Phase::Empty; }
    void page(int direction);
    void invalidate(const std::string& path);
    void refresh(FileData* game);
    const std::string& highlightedName() const { return mHighlightName; }
private:
    struct Game {
        std::string id,name,system,model,face,cover,video,description,facts,library,hud;
        std::vector<std::pair<std::string,std::string>> gallery;
    };
    struct Page {std::string label,text,image;bool overview=false;};
    Game capture(FileData* game);
    void request(FileData* game,bool launch);
    void restoreRoomMedia();
    void buildPages();
    void prepareGeometry();
    void prepareText();
    void screen(unsigned index,bool artOnly);
    void screenTabletop(unsigned index);
    // Tabletop: a new video frame redraws only the video rectangle of each page, not the page.
    void screenVideo(unsigned index);
    void video(float x,float y,float width,float height,bool topScreen);
    void releaseGraphics();
    void model(float progress,const Transform4x4f& trans);
    void applyTelevision();
    // 2D stage images (cabinet render, shadows). In the room they only serve the
    // fallback when the 3D table is unavailable, so they load on first such use.
    bool mStageLoaded=false;void loadStage();
    void applyType(float scale);
    bool tabletop(const Transform4x4f& trans);
    const SlotTelevisionProfile* mTV=nullptr;
    Game mDisplayed,mRequested,mMoving;
    std::map<std::string,Game> mSnapshots;
    std::string mHighlightName,mLastTarget,mLastInserted,mWarmModel;
    int mWarmState=-1;
    ImageComponent mArtwork,mConsole,mTelevision,mShadow,mFloorGlow;
    VideoVlcComponent mVideo;
    TextComponent mTitle,mText,mHud,mFooter;
    std::vector<Page> mPages;
    std::shared_ptr<Font> mFont;
    SlotNative* mNative=nullptr;
    SlotTabletop* mTable=nullptr;
    std::vector<Game> mTableGames;
    std::vector<int> mTableOffsets;
    bool mTableTVSelected=false,mTableTVControls=false;
    std::map<std::string,int> mTableHomes;
    std::string mTableRoot,mTableSystem,mTableId,mTableResident,mTableSelected;
    bool mTableAvailable=false,mTableDirty=true,mCarousel=false,mTableFailureLogged=false;
    float mFrameDelta=.016f,mOrbit=0,mOrbitGoal=0;
    int mCameraView=-1;
    bool mInspectOpen=false;float mInspect=0,mInspectYaw=0,mInspectPitch=0;int mSpin[2]={0,0};
    std::string mNativeId;
    unsigned mSurface[2]={0,0},mFramebuffer[2]={0,0};
    unsigned mNativeTexture=0;
    float mNativeBounds[4]={0,0,720,480};
    float mLCD[2][8]={{0}};
    Vector4f mNativeRect,mTargetRect,mTextViewport;
    // Shared floor of the home-console scene (scene pixels): the console's footprint centre and the
    // footprint's projected extent; mFloorY is the contact line the TV's floor point is placed on.
    Vector4f mConsoleFloor;float mFloorY=400;bool mHasFloor=false;
    bool mBoundsReady=false;
    float mNativePose=-1;
    int mPage=0;
    float mClock=0,mStable=0,mRest=0,mRetract=0,mScreenWidth=360,mScreenHeight=270;
    float mScrollClock=0,mScrollOffset=0,mScrollExtent=0;
    float mHeaderHeight=48,mTypeScale=1;
    bool mVideoStarted=false,mPaused=false,mScreenDirty=true;
    bool mVideoDirty=false,mVideoArea[2]={false,false};float mVideoRect[2][4]={{0,0,0,0},{0,0,0,0}},mVideoBindMs=0,mPageSteps[5]={0,0,0,0,0};
    // Tabletop pages keep their own title/description/HUD/footer per screen: this frontend's
    // setSize() always re-wraps text, and one shared set alternating between the TV and the
    // handheld (different widths and type sizes) re-wrapped the description ~100 ms per page.
    std::unique_ptr<TextComponent> mPageText[2][4];float mPageTextSize[2][4][2];unsigned mPageTextColor[2]={0,0};
    bool mPageScrolls[2]={false,false},mPageDirty[2]={false,false};
    void pageText(unsigned index,float scale,unsigned color);
    void pageSize(unsigned index,int part,float width,float height);
    slot::Phase mPreviousPhase=slot::Phase::Empty;
    bool mSounded=false;
    bool mDirty=true;
};
