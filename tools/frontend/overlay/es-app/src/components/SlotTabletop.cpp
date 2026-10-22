// Textured GLES2 scene. Source geometry stays resident; all nodes share camera/depth (MIT).
#include "SlotTabletop.h"
#include "SlotSceneMath.h"
#include "SlotVoxel.h"
#include "SlotTabletopLayout.h"
#include "SlotSceneProfile.h"
#include "SlotHomeProfile.h"
#include "SlotSpatialNavigation.h"
#include "SlotWorldProfile.h"
#include "SlotTabletopMotion.h"
#include "SlotScreens.h"
#include "SlotSceneCamera.h"
#include "SlotSceneDepth.h"
#include "SlotSystemFlight.h"
#include "SlotUploadContext.h"
#include <functional>
#include <future>
#define SDL_USE_BUILTIN_OPENGL_DEFINITIONS 1
#include <SDL_opengles2.h>
extern "C" SDL_Surface* IMG_Load(const char*);
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include <atomic>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <deque>
using namespace slot_scene;
namespace {
struct Vertex {float p[3],n[3],color[3],uv[2];};
// Resources may be released by the preparation worker. Actual GL deletion is
// drained on a current render/upload context; a copied mesh retains its buffers.
struct RetiredGpu {
    std::mutex mutex;std::vector<std::pair<bool,GLuint>> names;std::atomic<size_t> bytes{0};
    void drain(){std::vector<std::pair<bool,GLuint>> gone;{std::lock_guard<std::mutex> lock(mutex);gone.swap(names);}for(auto p:gone)if(p.first)glDeleteTextures(1,&p.second);else glDeleteBuffers(1,&p.second);}
};
struct GpuResource {
    GLuint id;bool texture;size_t bytes;std::shared_ptr<RetiredGpu> retired;
    GpuResource(GLuint n,bool t,size_t b,std::shared_ptr<RetiredGpu> r):id(n),texture(t),bytes(b),retired(std::move(r)){retired->bytes+=bytes;}
    ~GpuResource(){std::lock_guard<std::mutex> lock(retired->mutex);retired->names.emplace_back(texture,id);retired->bytes-=bytes;}
};
using Gpu=std::shared_ptr<GpuResource>;
struct Mesh {GLuint vertices=0,indices=0,texture=0;unsigned count=0;bool glass=false,hidden=false,sharedVertices=false;Vec low={},high={};Gpu vertexLease,indexLease,textureLease;};
struct Model {std::vector<Mesh> parts;Vec low={},high={},glassLow={},glassHigh={};};
struct Media {Mesh shell,label;float units=1;std::array<float,4> crop={{0,0,1,1}};bool cutout=false;};
struct Item {std::string id,model,face;GLuint texture=0;float hover=0,hoverVelocity=0,lift=0,tilt=0,fade=1;Mat pose=identity();Gpu textureLease;};
struct Flap {Mesh mesh;FlapSection section;};
// One queued draw; `offset` 1/2 pulls labels/LCDs forward by that polygon offset; `fade` < 1
// blends it over what lies behind (see submit); `screen` is a live TV/LCD picture.
struct DrawCall {const Mesh*mesh;Mat model;GLuint texture;bool unlit,paint,cutout;std::array<float,4> crop,window;int offset;float fade;bool screen;int flightGroup;};
// `table` turns the model frame into its resting pose; rest/top are its lowest and highest
// points in that pose (mm, relative to the placement origin).
// lcdCorners: each registered screen's top-left, top-right, bottom-right, bottom-left (model units).
struct Console {std::string name;Model model;Mesh power,led,lid;std::vector<Mesh> lcds;std::vector<std::array<Vec,4>> lcdCorners;std::vector<Flap> flaps;float flapSlot=0,flapClearance=0;Mat table=identity();float rest=0,top=0;};
// A console on Slotted's home table: its model (regional variants allowed), table pose and hover.
struct HomeItem {std::string model;Console console;Placement at;float hover=0,hoverVelocity=0,lift=0;Mat pose=identity();};
struct ScenePool {
    std::shared_ptr<RetiredGpu> retired=std::make_shared<RetiredGpu>();std::mutex mutex;
    std::map<std::string,std::weak_ptr<GpuResource>> images;
    std::map<std::string,Model> rooms;std::deque<std::string> roomLru;
};
struct SceneStream;struct RoomWorld;
std::vector<unsigned char> bytes(const std::string& path){std::ifstream f(path,std::ios::binary|std::ios::ate);if(!f)throw std::runtime_error("Missing scene asset: "+path);auto n=f.tellg();if(n<0||n>128*1024*1024)throw std::runtime_error("Invalid asset size: "+path);std::vector<unsigned char>d((size_t)n);f.seekg(0);if(n&&!f.read((char*)d.data(),n))throw std::runtime_error("Truncated asset: "+path);return d;}
template<class T>T read(const std::vector<unsigned char>&d,size_t pos){if(pos+sizeof(T)>d.size())throw std::runtime_error("Truncated mesh header");T v;std::memcpy(&v,d.data()+pos,sizeof(v));return v;}
uint64_t fnv(const unsigned char*p,size_t n){uint64_t h=UINT64_C(14695981039346656037);for(size_t i=0;i<n;i++)h=(h^p[i])*UINT64_C(1099511628211);return h;}
bool exists(const std::string&p){std::ifstream f(p);return bool(f);}
// Native units per mm of each console's media (and of the console unless consoleUnits differs).
// GB/GBC Game Paks share their console's units (cartridge-console.h exemplar MediaDraw).
float units(const std::string&m){if(m=="gb")return 1.8666667f;if(m=="gbc")return 2.1538462f;if(m=="snes")return 1.6f;if(m=="snes-us")return 1.55f;if(m=="n64")return 1.5f;if(m=="nes")return 196.f/120;if(m=="md"||m=="md-jp")return 224.f/109;if(m=="pico8")return 2.2f;if(m=="psx")return 1.6f;if(m=="dreamcast")return 1.3f;if(m=="gba")return 224.f/82;if(m=="nds")return 2.75f;if(m=="psp")return 2.8335301f;return 168.f/57;}
// The DS Lite housing (registration.json 3.0376/mm) is finer than its card (2.75/mm).
float consoleUnits(const std::string&m){return m=="nds"?3.037594f:units(m);}
GLuint shader(GLenum kind,const char*source){GLuint s=glCreateShader(kind);glShaderSource(s,1,&source,nullptr);glCompileShader(s);GLint ok;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);if(!ok){char log[2048];glGetShaderInfoLog(s,sizeof(log),nullptr,log);glDeleteShader(s);throw std::runtime_error(log);}return s;}
// Linked programs keep their binaries for the process (GL_OES_get_program_binary): the frontend
// destroys its GL contexts for every game, and reloading a binary skips ~110 ms of shader
// compilation before the first room frame afterwards. A rejected binary compiles from source;
// SLOT_SCENE_PROGRAM_CACHE=0 always compiles (A/B evidence).
struct BinaryApi {
    using Get=void(*)(GLuint,GLsizei,GLsizei*,GLenum*,void*);using Load=void(*)(GLuint,GLenum,const void*,GLint);
    Get get=nullptr;Load load=nullptr;bool ready=false;
};
const BinaryApi&binaryApi(){
    static const BinaryApi api=[]{
        BinaryApi a;const char*cache=getenv("SLOT_SCENE_PROGRAM_CACHE");if(cache&&std::strcmp(cache,"0")==0)return a;
        const char*extensions=(const char*)glGetString(GL_EXTENSIONS);GLint formats=0;glGetIntegerv(0x87FE/*GL_NUM_PROGRAM_BINARY_FORMATS_OES*/,&formats);
        if(!extensions||!std::strstr(extensions,"GL_OES_get_program_binary")||formats<1)return a;
        a.get=(BinaryApi::Get)SDL_GL_GetProcAddress("glGetProgramBinaryOES");a.load=(BinaryApi::Load)SDL_GL_GetProcAddress("glProgramBinaryOES");a.ready=a.get&&a.load;return a;
    }();
    return api;
}
// Compiles and links (or reloads) a program; attributes take locations 0, 1, ... in order.
GLuint link(const char*vs,const char*fs,std::initializer_list<const char*> attributes,const char*failure){
    static std::mutex mutex;static std::map<std::string,std::pair<GLenum,std::vector<unsigned char>>> binaries;
    const std::string key=std::string(vs)+'\0'+fs;const BinaryApi&api=binaryApi();GLint ok=0;
    if(api.ready){
        std::lock_guard<std::mutex> lock(mutex);auto found=binaries.find(key);
        if(found!=binaries.end()){GLuint p=glCreateProgram();api.load(p,found->second.first,found->second.second.data(),(GLint)found->second.second.size());glGetProgramiv(p,GL_LINK_STATUS,&ok);if(ok)return p;glDeleteProgram(p);binaries.erase(found);while(glGetError()!=GL_NO_ERROR){}}
    }
    GLuint v=shader(GL_VERTEX_SHADER,vs),f=shader(GL_FRAGMENT_SHADER,fs),p=glCreateProgram();glAttachShader(p,v);glAttachShader(p,f);GLuint at=0;for(auto name:attributes)glBindAttribLocation(p,at++,name);glLinkProgram(p);glDeleteShader(v);glDeleteShader(f);glGetProgramiv(p,GL_LINK_STATUS,&ok);if(!ok){glDeleteProgram(p);throw std::runtime_error(failure);}
    if(api.ready){
        GLint length=0;glGetProgramiv(p,0x8741/*GL_PROGRAM_BINARY_LENGTH_OES*/,&length);std::vector<unsigned char> data((size_t)std::max(length,0));GLenum format=0;GLsizei written=0;
        if(length>0)api.get(p,length,&written,&format,data.data());
        if(written>0){data.resize((size_t)written);std::lock_guard<std::mutex> lock(mutex);binaries[key]={format,std::move(data)};}
    }
    return p;
}
// Two builds of one shader. Any `discard` in a program makes the Mali GPU test depth only after
// shading, so hidden pixels are shaded too; measured on the RG34XXSP (GBA/PVM, Mali-G31) the
// discard-free build is 1.9x (overview) to 4.5x (cartridge view) faster with identical pixels.
// Only cut-out labels (PSP UMD window) use the clipped build.
// uHole draws a live screen as transparent black into the cached scene (see composite()).
struct Shading {GLuint program=0;GLint vp=-1,model=-1,textured=-1,unlit=-1,cel=-1,crop=-1,window=-1,paintOn=-1,paint=-1,cutout=-1,texture=-1,hole=-1,crt=-1;};
Shading program(bool clipped){
    const char* vs="attribute vec3 aP,aN,aC;attribute vec2 aUV;uniform mat4 uVP,uModel;varying mediump vec3 n,c;varying mediump vec2 uv;void main(){gl_Position=uVP*uModel*vec4(aP,1.0);vec3 d=vec3(dot(uModel[0].xyz,uModel[0].xyz),dot(uModel[1].xyz,uModel[1].xyz),dot(uModel[2].xyz,uModel[2].xyz));n=mat3(uModel)*(aN/max(d,vec3(.000001)));c=aC;uv=aUV;}";
    const bool derivatives=std::strstr((const char*)glGetString(GL_EXTENSIONS),"GL_OES_standard_derivatives")!=nullptr;
    const std::string fs=std::string(derivatives?"#extension GL_OES_standard_derivatives : enable\n":"")+"precision mediump float;varying mediump vec3 n,c;varying mediump vec2 uv;uniform sampler2D uTexture;uniform float uTextured,uUnlit,uCel,uPaintOn,uCutout,uHole,uCrt;uniform vec3 uPaint;uniform vec4 uCrop,uWindow;void main(){"+
        "vec2 st=clamp((uv-uWindow.xy)/(uWindow.zw-uWindow.xy),0.0,1.0);vec4 tex=texture2D(uTexture,uCrop.xy+st*uCrop.zw);"+(clipped?"if(uCutout>0.5&&tex.a<0.5)discard;":"")+
        "vec3 color=mix(c,tex.rgb,uTextured);float lum=dot(color,vec3(.299,.587,.114));color=mix(color,uPaint*clamp(lum/.55,.25,1.5),tex.a*uPaintOn*uTextured);"+
        // Filter fine scanlines away at distant views instead of making them crawl.
        (derivatives?"float lineFootprint=fwidth(st.y)*240.0;float lineGain=1.0-smoothstep(.35,.9,lineFootprint);":"float lineGain=0.0;")+
        "if(uCrt>.5){vec2 edge=(st-.5)*vec2(1.0,.75);float scan=.985+.015*cos(st.y*1507.96447)*lineGain;color*=scan*(1.0-.08*dot(edge,edge));}float light=max(0.0,dot(normalize(n),normalize(vec3(-.45,.8,.5))));float shade=mix(.43+.57*light,light>.62?1.0:light>.15?.74:.48,uCel);gl_FragColor=vec4(color*mix(shade,1.0,uUnlit),1.0)*(1.0-uHole);}";
    GLuint p=link(vs,fs.c_str(),{"aP","aN","aC","aUV"},"Scene shader link failed");
    Shading s;s.program=p;auto at=[p](const char*name){return glGetUniformLocation(p,name);};
    s.vp=at("uVP");s.model=at("uModel");s.textured=at("uTextured");s.unlit=at("uUnlit");s.cel=at("uCel");s.crop=at("uCrop");s.window=at("uWindow");s.paintOn=at("uPaintOn");s.paint=at("uPaint");s.cutout=at("uCutout");s.texture=at("uTexture");s.hole=at("uHole");s.crt=at("uCrt");
    return s;
}
// Exact same-size copy of the cached scene (texel centres from gl_FragCoord need highp past 1024).
struct Copy {GLuint program=0;GLint texture=-1,size=-1;};
Copy copyProgram(){
    const char* vs="attribute vec2 aP;void main(){gl_Position=vec4(aP,0.0,1.0);}";
    const char* fs="#ifdef GL_FRAGMENT_PRECISION_HIGH\nprecision highp float;\n#else\nprecision mediump float;\n#endif\nuniform sampler2D uTexture;uniform vec2 uSize;void main(){gl_FragColor=texture2D(uTexture,gl_FragCoord.xy/uSize);}";
    GLuint p=link(vs,fs,{"aP"},"Scene copy shader link failed");
    Copy c;c.program=p;c.texture=glGetUniformLocation(p,"uTexture");c.size=glGetUniformLocation(p,"uSize");return c;
}
}
struct SlotTabletop {
    SDL_Window*window=nullptr;SDL_GLContext owner=nullptr,context=nullptr;
    GLuint target=0,fbo=0,depth=0;Shading shading[2];int width=1440,height=960,triangles=0; // shading: solid, clipped
    // The 3D scene renders into scene* (screens cut out as alpha 0); `target` is the composited
    // frame. While nothing moves, the cached scene is reused and only the screens are redrawn.
    GLuint sceneTexture=0,sceneFbo=0;Copy copy;std::vector<DrawCall> cached;Mat cachedView=identity();bool cacheValid=false,reuse=true;
    long rendered=0,reused=0,partials=0; // frames that rendered the scene / reused the cache / of the rendered, re-rendered only a moved region
    float frameTiming[3]={0,0,0}; // slot_tabletop_frame_timing
    // SLOT_SCENE_GPU_TIMING=1: GL_EXT_disjoint_timer_query around the scene pass and the
    // composite, read back two frames later and averaged in the frame log (evidence only).
    GLuint gpuQueries[2][2]={{0,0},{0,0}};bool gpuIssued[2][2]={{false,false},{false,false}};int gpuSlot=0,gpuKind[2]={0,0};
    double logGpu[3]={0,0,0};int logGpuCount[3]={0,0,0}; // full scene, partial scene, composite
    // Draws of each mesh (by its index buffer) on this render context, and the tiny target the
    // warm-up draws into (see warmMeshes).
    std::map<const GpuResource*,std::pair<std::weak_ptr<GpuResource>,int>> drawUses;GLuint warmFbo=0,warmColour=0;
    std::map<const GpuResource*,std::pair<std::weak_ptr<GpuResource>,unsigned>> warmOffsets;
    FILE*frameLog=nullptr;double logFrontend=0,logScene=0,logPage=0,logBind=0,logStart=0,logSteps[5]={0,0,0,0,0};int logFrames=0,logRendered=0,logPartials=0; // SLOT_SCENE_FRAMELOG
    // Raster is 2x the logical size (supersampled), or 1x with `samples` on-tile MSAA samples.
    int logicalWidth=720,logicalHeight=480,samples=0;bool npotMips=false;float anisotropy=0;
    std::string root,prepared,system,tv,error,paint;bool cel=false,ignoreLayout=false,reducedMotion=false,crt=false;
    std::string gbaChoice="neilvfx";std::shared_ptr<ScenePool> pool=std::make_shared<ScenePool>();
    std::shared_ptr<SceneStream> stream;std::map<std::string,Gpu> imageLeases;
    std::shared_ptr<RoomWorld> world; // owner only; preparation cores never mutate room positions
    std::function<void()> checkPreparation,beginUpload,endUpload;
    std::function<SDL_Surface*(const std::string&)> takeDecoded; // pixels the stream decoded ahead
    std::map<std::string,GLuint> textures,labelTextures;std::map<std::string,Media> media;
    // consoles[0] is the authored layout console; [1] its regional variant (US SNES, JP Mega Drive).
    Console consoles[2];int consoleCount=1;float layoutBottom=0; // authored console's base height, mm
    // A borrowed layout's cartridge nodes rest its own media: lowest face (shell z, mm).
    float layoutMediaLow=0;bool layoutMediaKnown=false;
    float flapAngles[4]={0,0,0,0};int flapCount=0; // last frame, radians
    Model television,table;std::vector<Item> items;
    Item resident;Placement residentHome;bool hasResident=false;int selected=-1;float selectedSince=0;
    float orbitLimit[2]={8,8};bool orbitReady=false; // permitted |yaw| to the left/right of the authored eye
    Vec cameraEye={0,0,0},cameraTarget={0,0,-1};float cameraFov=.7f; // this frame's camera, for the inspection pose
    Mesh status;std::string statusKey;
    SceneProfile layout;bool authored=false;
    // A pan lasts the profile's transition; panLimit (set by the stream after a system switch) caps a new one.
    ProfileCamera panFrom,panTo,panCurrent;int cameraView=-1,cameraSelection=-1;float panTime=0,panSeconds=.8f,panLimit=0;
    Mat view=identity(),consolePose=identity(),tvPose=identity(),statusPose=identity();
    // Authored frames queue their draws; the near plane then hugs the closest geometry in view.
    std::vector<DrawCall> calls;Mat eyeView=identity();float projectionFov=.7f,nearPlane=150;bool fitNear=false,cull=true,sort=true;int drawn=0,culled=0;
    int drawFlightGroup=-1;float drawFade=1;bool drawScreen=false;int focusView=-1; // queued with draw(); this frame's authored camera view
    Vec paintColor={1,1,1};
    Vec display[4]={{0,0,0},{0,0,0},{0,0,0},{0,0,0}};
    // Slotted's home table (system "home"); see loadHome and homeFrame.
    bool home=false,bootstrapHome=false;HomeProfile homeLayout;std::vector<HomeItem> homeItems;
};
namespace {
// Diagnostic: main-thread open steps to "<SLOT_SCENE_STREAMLOG>.open.tsv" (evidence only).
// loadScene also runs on the stream worker; only slot_tabletop_open's thread logs.
thread_local bool openStepsActive=false;
FILE*openStepFile(){static FILE*file=[]()->FILE*{const char*p=getenv("SLOT_SCENE_STREAMLOG");return p?std::fopen((std::string(p)+".open.tsv").c_str(),"a"):nullptr;}();return file;}
bool openStepsLogging(){return openStepsActive&&openStepFile();}
void openStep(const char*system,const char*name){
    static Uint64 last=0;if(!openStepsLogging())return;const Uint64 now=SDL_GetPerformanceCounter();
    if(name){std::fprintf(openStepFile(),"%u\t%s\t%s\t%.3f\n",SDL_GetTicks(),system,name,1000.0*(now-last)/SDL_GetPerformanceFrequency());std::fflush(openStepFile());}
    last=now;
}
struct UploadScope {
    SlotTabletop*s;explicit UploadScope(SlotTabletop*scene):s(scene){if(s->beginUpload)s->beginUpload();}
    ~UploadScope(){if(s->endUpload)s->endUpload();}
};
Gpu lease(SlotTabletop*s,GLuint name,bool texture,size_t size){return std::make_shared<GpuResource>(name,texture,size,s->pool->retired);}
// RGBA pixels of a scene texture; CPU only, never touches GL.
// RGB stays RGB24 (uploaded as GL_RGB, same samples); other layouts become RGBA32.
// Not libpng: in the frontend, libpng16 is already loaded by FreeType with its zlib
// imports split between FreeImage's bundled zlib and the system one, which crashed
// (see tools/frontend/tests/SlotPng.h). IMG_Load keeps the proven decoder.
SDL_Surface*decodeImage(const std::string&path){
    SDL_Surface*raw=IMG_Load(path.c_str());if(!raw)throw std::runtime_error("Cannot load texture: "+path);openStep("png","img-imgload");
    if(raw->format->format==SDL_PIXELFORMAT_RGB24)return raw;
    SDL_Surface*p=SDL_ConvertSurfaceFormat(raw,SDL_PIXELFORMAT_RGBA32,0);SDL_FreeSurface(raw);if(!p)throw std::runtime_error(SDL_GetError());return p;
}
std::string imageKey(const SlotTabletop*s,const std::string&path){return path+"|"+std::to_string(s->npotMips)+"|"+std::to_string(s->anisotropy);}
bool pooled(const SlotTabletop*s,const std::string&path){std::lock_guard<std::mutex> lock(s->pool->mutex);auto i=s->pool->images.find(imageKey(s,path));return i!=s->pool->images.end()&&!i->second.expired();}
// A synchronous open (startup, return from a game) blocks the first room frame on
// its textures. While it runs, the large prepared models' textures decode on worker
// threads in parallel with the rest of the load; image() takes them when it gets
// there. The stream worker's preparations are unchanged.
using Decodes=std::map<std::string,std::future<SDL_Surface*>>;
thread_local Decodes*openDecodes=nullptr;
// Decodes started when a game exited (main thread only): the first room frame after
// the game reopens the same table and TV, and the next open adopts these; the first
// item sync after it adopts the labels (returnLabels) and frees the rest.
Decodes returnDecodes,returnLabels;
void drain(Decodes&decodes){for(auto&d:decodes){try{SDL_FreeSurface(d.second.get());}catch(...){}}decodes.clear();}
struct OpenDecodes {
    Decodes decodes;
    OpenDecodes():decodes(std::move(returnDecodes)){returnDecodes.clear();openDecodes=&decodes;}
    ~OpenDecodes(){openDecodes=nullptr;drain(decodes);}
};
// Texture files of one prepared model (its scene.txt), empty if unreadable.
std::vector<std::string> preparedTextures(const std::string&folder){
    std::vector<std::string> paths;std::ifstream f(folder+"/scene.txt");std::string magic;unsigned count=0;float bounds;
    if(!(f>>magic>>count)||magic!="SCTABLETOP1"||count>64)return paths;
    for(int i=0;i<12;i++)f>>bounds;
    for(unsigned i=0;i<count;i++){
        std::string file,texture;int glass;if(!(f>>file>>texture>>glass))break;
        if(texture=="-"||texture.find('/')!=std::string::npos||texture.find("..")!=std::string::npos)continue;
        paths.push_back(folder+"/"+texture);
    }
    return paths;
}
void prefetchPrepared(SlotTabletop*s,const std::string&key){
    if(!openDecodes||key.empty())return;
    const std::string folder=s->prepared+"/"+key;
    {std::lock_guard<std::mutex> lock(s->pool->mutex);if(s->pool->rooms.count(folder))return;}
    for(const auto&path:preparedTextures(folder))
        if(!openDecodes->count(path)&&!s->textures.count(path)&&!pooled(s,path))(*openDecodes)[path]=std::async(std::launch::async,decodeImage,path);
}
struct ReturnAssets {std::string prepared,table,tv;std::vector<std::string> labels;} returnAssets;
GLuint image(SlotTabletop*s,const std::string&path,bool label=false){
    if(s->checkPreparation)s->checkPreparation();
    auto&cache=label?s->labelTextures:s->textures;
    if(path.empty())return 0;auto found=cache.find(path);if(found!=cache.end())return found->second;
    const std::string key=imageKey(s,path);
    {std::lock_guard<std::mutex> lock(s->pool->mutex);auto i=s->pool->images.find(key);if(i!=s->pool->images.end())if(auto held=i->second.lock()){s->imageLeases[path]=held;cache[path]=held->id;return held->id;}}
    const std::string step=path.substr(path.rfind('/',path.rfind('/')-1)+1);openStep(step.c_str(),"img-before");
    SDL_Surface*p=s->takeDecoded?s->takeDecoded(path):nullptr;
    if(!p&&openDecodes){auto found=openDecodes->find(path);if(found!=openDecodes->end()){auto decode=std::move(found->second);openDecodes->erase(found);p=decode.get();}}
    if(!p)p=decodeImage(path);openStep(step.c_str(),"img-decode");
    GLint maxSize;glGetIntegerv(GL_MAX_TEXTURE_SIZE,&maxSize);if(p->w>maxSize||p->h>maxSize){SDL_FreeSurface(p);throw std::runtime_error("Source texture exceeds GLES limit");}
    // CPU decode never owns the render context. A speculative upload waits for
    // a reusable room frame; system/launch flight pauses all GPU preparation.
    std::unique_ptr<UploadScope> upload;try{upload.reset(new UploadScope(s));}catch(...){SDL_FreeSurface(p);throw;}
    // SDL rows are tightly packed or padded to 4 bytes (RGB24 with a width not divisible by 4).
    const bool rgb=p->format->format==SDL_PIXELFORMAT_RGB24;const GLenum format=rgb?GL_RGB:GL_RGBA;
    if(p->pitch!=p->w*(rgb?3:4)&&p->pitch!=((p->w*(rgb?3:4)+3)&~3)){SDL_FreeSurface(p);throw std::runtime_error("Unexpected texture row pitch: "+path);}
    GLuint t=0;glGenTextures(1,&t);glBindTexture(GL_TEXTURE_2D,t);glPixelStorei(GL_UNPACK_ALIGNMENT,p->pitch==p->w*(rgb?3:4)?1:4);
    glTexImage2D(GL_TEXTURE_2D,0,format,p->w,p->h,0,format,GL_UNSIGNED_BYTE,p->pixels);glPixelStorei(GL_UNPACK_ALIGNMENT,1);openStep(step.c_str(),"img-upload");
    bool pot=((p->w&(p->w-1))==0&&(p->h&(p->h-1))==0)||s->npotMips;
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,pot?GL_LINEAR_MIPMAP_LINEAR:GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);if(pot)glGenerateMipmap(GL_TEXTURE_2D);
    if(openStepsLogging()){glFinish();openStep(step.c_str(),"img-mipmap+finish");}
    if(pot&&s->anisotropy>1)glTexParameterf(GL_TEXTURE_2D,0x84FE,s->anisotropy); // GL_TEXTURE_MAX_ANISOTROPY_EXT
    auto held=lease(s,t,true,(size_t)p->w*p->h*4*(pot?4.f/3:1));SDL_FreeSurface(p);s->imageLeases[path]=held;
    {std::lock_guard<std::mutex> lock(s->pool->mutex);s->pool->images[key]=held;}cache[path]=t;return t;
}
Mesh mesh(SlotTabletop*s,const std::string&path,const std::string&texture=""){
    if(s->checkPreparation)s->checkPreparation();
    auto d=bytes(path);if(d.size()<20)throw std::runtime_error("Short scene mesh");
    bool legacy=std::memcmp(d.data(),"SCTOON2\0",8)==0,scene=std::memcmp(d.data(),"SCTABL1\0",8)==0;
    if(!legacy&&!scene)throw std::runtime_error("Invalid scene mesh magic");
    auto n=read<uint32_t>(d,8),count=read<uint32_t>(d,12),flags=read<uint32_t>(d,16);size_t stride=legacy?36:44;
    if(!n||n>65535||!count||count>600000||count%3||d.size()!=20+n*stride+count*2)throw std::runtime_error("Invalid scene mesh dimensions");
    std::vector<Vertex>v(n);Mesh m;m.count=count;m.glass=scene&&flags;m.low={1e9f,1e9f,1e9f};m.high={-1e9f,-1e9f,-1e9f};
    for(unsigned i=0;i<n;i++){
        std::memcpy(&v[i],d.data()+20+i*stride,stride);if(legacy){v[i].uv[0]=v[i].uv[1]=0;}
        for(int j=0;j<11;j++)if(!std::isfinite(((float*)&v[i])[j]))throw std::runtime_error("Non-finite scene vertex");
        for(int j=0;j<3;j++){((float*)&m.low)[j]=std::min(((float*)&m.low)[j],v[i].p[j]);((float*)&m.high)[j]=std::max(((float*)&m.high)[j],v[i].p[j]);}
    }
    auto indices=d.data()+20+n*stride;for(unsigned i=0;i<count;i++)if(read<uint16_t>(d,20+n*stride+i*2)>=n)throw std::runtime_error("Scene mesh index out of range");
    if(legacy){
        auto stem=path.substr(0,path.size()-5);if(exists(stem+".texture")){
            auto t=bytes(stem+".texture");if(t.size()!=48+n*8||std::memcmp(t.data(),"SCTEX003",8)||read<uint32_t>(t,8)!=n||read<uint64_t>(t,24)!=fnv(d.data()+20,n*stride)||read<uint64_t>(t,32)!=fnv(indices,count*2))throw std::runtime_error("Invalid UV sidecar: "+stem);
            auto png=bytes(stem+".albedo.png");if(read<uint64_t>(t,40)!=fnv(png.data(),png.size()))throw std::runtime_error("Albedo hash mismatch");
            for(unsigned i=0;i<n;i++)std::memcpy(v[i].uv,t.data()+48+i*8,8);
            m.texture=image(s,stem+".albedo.png");
        }
    }else if(!texture.empty())m.texture=image(s,texture);
    UploadScope upload(s);glGenBuffers(1,&m.vertices);glBindBuffer(GL_ARRAY_BUFFER,m.vertices);glBufferData(GL_ARRAY_BUFFER,v.size()*sizeof(Vertex),v.data(),GL_STATIC_DRAW);
    glGenBuffers(1,&m.indices);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,m.indices);glBufferData(GL_ELEMENT_ARRAY_BUFFER,count*2,indices,GL_STATIC_DRAW);
    m.vertexLease=lease(s,m.vertices,false,v.size()*sizeof(Vertex));m.indexLease=lease(s,m.indices,false,count*2);
    for(auto&i:s->imageLeases)if(i.second->id==m.texture){m.textureLease=i.second;break;}s->triangles+=count/3;return m;
}
// A prepared scene's bounds (scene.txt header) without loading its meshes.
bool sceneBounds(const std::string&folder,Vec&low,Vec&high){
    std::ifstream f(folder+"/scene.txt");std::string magic;unsigned count;
    return bool(f>>magic>>count>>low.x>>low.y>>low.z>>high.x>>high.y>>high.z)&&magic=="SCTABLETOP1";
}
Model prepared(SlotTabletop*s,const std::string&key){
    const std::string cacheKey=s->prepared+"/"+key;
    auto&pool=*s->pool;auto found=pool.rooms.find(cacheKey);
    pool.roomLru.erase(std::remove(pool.roomLru.begin(),pool.roomLru.end(),cacheKey),pool.roomLru.end());pool.roomLru.push_back(cacheKey);
    if(found!=pool.rooms.end()){for(auto&m:found->second.parts)s->triangles+=m.count/3;return found->second;}
    std::string folder=s->prepared+"/"+key;std::ifstream f(folder+"/scene.txt");std::string magic;unsigned count;Model m;
    if(!(f>>magic>>count)||magic!="SCTABLETOP1"||count>64)throw std::runtime_error("Missing/invalid prepared scene: "+folder);
    f>>m.low.x>>m.low.y>>m.low.z>>m.high.x>>m.high.y>>m.high.z>>m.glassLow.x>>m.glassLow.y>>m.glassLow.z>>m.glassHigh.x>>m.glassHigh.y>>m.glassHigh.z;
    for(unsigned i=0;i<count;i++){std::string file,texture;int glass;if(!(f>>file>>texture>>glass)||file.find('/')!=std::string::npos||file.find("..")!=std::string::npos||texture.find('/')!=std::string::npos||texture.find("..")!=std::string::npos)throw std::runtime_error("Invalid prepared scene part");Mesh p=mesh(s,folder+"/"+file,texture=="-"?"":folder+"/"+texture);p.glass=(glass&1)!=0;p.hidden=(glass&2)!=0;m.parts.push_back(p);}
    // Three table assets and three TVs are independent room resources. A
    // three-entry limit evicts the PVM when a saved layout uses another table;
    // the streamer's byte budget and memory reserve govern their retention.
    pool.rooms[cacheKey]=m;while(pool.roomLru.size()>6){pool.rooms.erase(pool.roomLru.front());pool.roomLru.pop_front();}return m;
}
// Flat label for shells without a source label surface: the recessed well from
// tools/slotlaunch/media-specs.h (centre x/y, half width/height, plane z in mm).
Mesh labelQuad(SlotTabletop*s,float units,float x,float y,float halfW,float halfH,float z){
    UploadScope upload(s);
    Vertex v[4];const float corner[4][2]={{-1,1},{1,1},{1,-1},{-1,-1}};
    for(int i=0;i<4;i++)v[i]={{(x+halfW*corner[i][0])*units,(y+halfH*corner[i][1])*units,z*units},{0,0,1},{1,1,1},{(corner[i][0]+1)/2,(1-corner[i][1])/2}};
    const uint16_t indices[6]={0,3,2,0,2,1};Mesh m;m.count=6;
    m.low={(x-halfW)*units,(y-halfH)*units,z*units};m.high={(x+halfW)*units,(y+halfH)*units,z*units};
    glGenBuffers(1,&m.vertices);glBindBuffer(GL_ARRAY_BUFFER,m.vertices);glBufferData(GL_ARRAY_BUFFER,sizeof(v),v,GL_STATIC_DRAW);
    glGenBuffers(1,&m.indices);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,m.indices);glBufferData(GL_ELEMENT_ARRAY_BUFFER,sizeof(indices),indices,GL_STATIC_DRAW);
    m.vertexLease=lease(s,m.vertices,false,sizeof(v));m.indexLease=lease(s,m.indices,false,sizeof(indices));
    s->triangles+=2;return m;
}
Mesh makeMesh(SlotTabletop*s,const std::vector<Vertex>&v,const std::vector<uint16_t>&indices){
    UploadScope upload(s);
    Mesh m;m.count=indices.size();m.low={1e9f,1e9f,1e9f};m.high={-1e9f,-1e9f,-1e9f};
    for(auto&w:v)for(int j=0;j<3;j++){((float*)&m.low)[j]=std::min(((float*)&m.low)[j],w.p[j]);((float*)&m.high)[j]=std::max(((float*)&m.high)[j],w.p[j]);}
    glGenBuffers(1,&m.vertices);glBindBuffer(GL_ARRAY_BUFFER,m.vertices);glBufferData(GL_ARRAY_BUFFER,v.size()*sizeof(Vertex),v.data(),GL_STATIC_DRAW);
    glGenBuffers(1,&m.indices);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,m.indices);glBufferData(GL_ELEMENT_ARRAY_BUFFER,indices.size()*2,indices.data(),GL_STATIC_DRAW);
    m.vertexLease=lease(s,m.vertices,false,v.size()*sizeof(Vertex));m.indexLease=lease(s,m.indices,false,indices.size()*2);
    s->triangles+=m.count/3;return m;
}
// Annular disc as tools/slotlaunch/optical-disc.h: 96 segments, bore radius/8. The
// printed top face (+Z, circular UV over the disc art) is the label; the dark
// underside and the outer/bore rims form the shell. Centred on its mid-plane.
void discMeshes(SlotTabletop*s,float units,float radius,float thickness,Mesh&shell,Mesh&label){
    const int n=96;const float big=radius*units,bore=big/8,h=thickness*units/2,pi=3.14159265f;
    std::vector<Vertex> top,rest;std::vector<uint16_t> topIndex,restIndex;
    auto ring=[&](std::vector<Vertex>&v,std::vector<uint16_t>&index,float r0,float z0,float r1,float z1,bool radial,float sign,Vec colour,bool printed){
        const uint16_t base=v.size();
        for(int i=0;i<=n;i++){
            float a=i*2*pi/n,c=std::cos(a),sn=std::sin(a);
            Vec normal=radial?Vec{c*sign,sn*sign,0}:Vec{0,0,sign};
            for(auto pr:{std::pair<float,float>{r0,z0},std::pair<float,float>{r1,z1}}){
                Vertex w={{pr.first*c,pr.first*sn,pr.second},{normal.x,normal.y,normal.z},{colour.x,colour.y,colour.z},
                          {printed?.5f+pr.first/big*c*.5f:0.f,printed?.5f-pr.first/big*sn*.5f:0.f}};
                v.push_back(w);
            }
        }
        for(int i=0;i<n;i++){uint16_t a=base+2*i;for(uint16_t k:{a,uint16_t(a+1),uint16_t(a+3),a,uint16_t(a+3),uint16_t(a+2)})index.push_back(k);}
    };
    ring(top,topIndex,bore,h,big,h,false,1,{1,1,1},true);
    ring(rest,restIndex,bore,-h,big,-h,false,-1,{.06f,.06f,.07f},false);
    ring(rest,restIndex,big,-h,big,h,true,1,{.22f,.23f,.25f},false);
    ring(rest,restIndex,bore,-h,bore,h,true,-1,{.22f,.23f,.25f},false);
    shell=makeMesh(s,rest,restIndex);label=makeMesh(s,top,topIndex);
}
// Alternate shells share their console's folder: Tzakol SNES carts, EA Mega Drive carts.
std::string mediaFolder(const std::string&name){return name=="snes-tzakol"||name=="snes-us-tzakol"?name.substr(0,name.size()-7):name=="md-ea"?"md":name;}
std::string mediaBase(const std::string&root,const std::string&name){
    const bool alternate=name=="snes-tzakol"||name=="snes-us-tzakol",ea=name=="md-ea";
    return root+"/consoles/"+mediaFolder(name)+(alternate?"/media-tzakol":ea?"/media-ea":"/media");
}
Media&media(SlotTabletop*s,const std::string&name){
    auto found=s->media.find(name);if(found!=s->media.end())return found->second;
    OpticalRegistration optical;
    if(opticalRegistration(name,optical)){
        Media m;m.units=units(name);discMeshes(s,m.units,optical.radius,optical.thickness,m.shell,m.label);
        return s->media.emplace(name,std::move(m)).first->second;
    }
    bool alternate=name=="snes-tzakol"||name=="snes-us-tzakol",ea=name=="md-ea";
    Media m;m.units=units(mediaFolder(name));std::string base=mediaBase(s->root,name);m.shell=mesh(s,base+".mesh");
    if(exists(base+"-label.mesh"))m.label=mesh(s,base+"-label.mesh");
    else if(name=="snes-us")m.label=labelQuad(s,m.units,0,22.7213115f,42.0224719f,18.7540984f,9.53f);
    else if(name=="nes")m.label=labelQuad(s,m.units,16.0927152f,20.4462687f,28.013245f,44.8626866f,9.03f);
    else if(name=="md")m.label=labelQuad(s,m.units,.302777778f,2.39316239f,39.3611111f,31.4102564f,8.03f);
    else if(name=="md-jp")m.label=labelQuad(s,m.units,.151388889f,2.24358974f,39.5125f,30.9615385f,8.03f);
    else if(ea)m.label=labelQuad(s,m.units,6.47773973f,7.08703704f,34.3818493f,36.4240741f,8.03f);
    // Handheld label wells: Game Pak recess, DS card face, PSP UMD front (cut out by the face's alpha).
    else if(name=="gb")m.label=labelQuad(s,m.units,0,-4.8791f,20.92095f,18.7022f,3.875f);
    else if(name=="gbc")m.label=labelQuad(s,m.units,0,-5,20.9f,18.6f,3.72f);
    else if(name=="nds")m.label=labelQuad(s,m.units,0,1.13569322f,14.1580645f,14.7123894f,1.73f);
    else if(name=="psp"){m.label=labelQuad(s,m.units,0,0,33.019f,33.019f,5.98f/2.8335301f+.05f);m.cutout=true;}
    // Printed well of the baked per-game face. Source-surface label UVs are 0..1.
    if(name=="snes")m.crop={{42.f/360,22.f/245,276.f/360,99.f/245}};
    else if(name=="snes-us")m.crop={{70.f/360,7.f/245,220.f/360,104.f/245}};
    else if(name=="gba")m.crop={{50.f/360,52.f/212,260.f/360,135.f/212}};
    else if(name=="gb")m.crop={{47.f/312,97.f/337,218.f/312,193.f/337}};
    else if(name=="gbc")m.crop={{48.f/312,99.f/337,216.f/312,191.f/337}};
    else if(name=="nds")m.crop={{23.f/312,17.f/341,266.f/312,285.f/341}};
    else if(name=="n64")m.crop={{96.f/360,22.f/241,168.f/360,197.f/241}};
    else if(name=="pico8")m.crop={{26.f/264,41.f/338,205.f/264,277.f/338}};
    else if(name=="nes")m.crop={{122.f/304,4.f/337,141.f/304,226.f/337}};
    else if(name=="md")m.crop={{51.f/360,22.f/270,260.f/360,210.f/270}};
    else if(name=="md-jp")m.crop={{50.f/360,24.f/270,261.f/360,207.f/270}};
    else if(ea)m.crop={{96.f/360,3.f/270,207.f/360,221.f/270}};
    if(alternate)m.crop={{88.f/360,6.f/245,187.f/360,114.f/245}};
    return s->media.emplace(name,std::move(m)).first->second;
}
// Queued in frame order; submit() issues them once the camera's near plane is known.
void draw(SlotTabletop*s,const Mesh&m,const Mat&model,GLuint texture=0,bool unlit=false,const std::array<float,4>&crop={{0,0,1,1}},bool paint=false,int offset=0,bool cutout=false,const std::array<float,4>&window={{0,0,1,1}}){
    if(m.vertices&&!m.hidden)s->calls.push_back({&m,model,texture,unlit,paint,cutout,crop,window,offset,s->drawFade,s->drawScreen,s->drawFlightGroup});
}
// Printed label over its shell; a cut-out face (PSP UMD window) keeps only its opaque part.
void drawLabel(SlotTabletop*s,const Media&m,const Mat&pose,GLuint texture){
    if(m.label.vertices&&texture)draw(s,m.label,pose,texture,true,m.crop,false,1,m.cutout);
}
// A fixed 150 mm near plane sliced close carts open (the GBA cartridge view sits ~170 mm from
// its cart, with other carts nearer still). The near plane now stops just in front of the
// closest queued geometry inside the frustum (10..150 mm), and draws wholly outside the
// frustum are skipped; nothing in view changes. Bounds are each mesh's box under its pose.
// libmali (RG34XXSP, Mali-G31) spends ~2.5 us per triangle once on about the 5th to 8th draw of
// a new mesh on a context, then draws it faster (GBA SP, 81k triangles: ~200 ms once). Measured
// per context: the preparation worker's draws do not count. Mid-flight this froze arrivals for
// 50-200 ms, so a system switch draws every new destination mesh first (warmMeshes).
// SLOT_SCENE_WARM_DRAWS sets the count (default 10; 0 disables, A/B evidence only).
int warmDraws(){static const int n=getenv("SLOT_SCENE_WARM_DRAWS")?std::max(0,std::min(32,std::atoi(getenv("SLOT_SCENE_WARM_DRAWS")))):10;return n;}
// Incremental warm-up completes its draws every this many index batches. Each glFinish is a
// ~1.3 ms round trip on the RG34XXSP: finishing every 1,024-triangle batch measured ~1.6 ms a
// batch (an/ap), against ~0.1-0.25 ms of drawing plus the one-time ~2.5 ms of a range's spike,
// so warm-ups took 0.4-3.6 s per system and 7-9 s for the home room. A few batches per finish
// keeps each step's overrun bounded (6 ms budget, checked after every finish).
// SLOT_SCENE_WARM_FINISH_BATCHES=1 finishes every batch (A/B evidence).
int warmFinishBatches(){static const int n=getenv("SLOT_SCENE_WARM_FINISH_BATCHES")?std::max(1,std::min(64,std::atoi(getenv("SLOT_SCENE_WARM_FINISH_BATCHES")))):6;return n;}
int drawUses(const SlotTabletop*s,const Mesh&m){
    auto u=m.indexLease?s->drawUses.find(m.indexLease.get()):s->drawUses.end();
    return u==s->drawUses.end()||u->second.first.expired()?0:u->second.second;
}
void countDraw(SlotTabletop*s,const Mesh&m){
    if(!m.indexLease)return;auto&u=s->drawUses[m.indexLease.get()];
    if(u.first.expired()){u.first=m.indexLease;u.second=0;}u.second++;
}
unsigned indexBatch(const SlotTabletop*s,const Mesh&m){
    if(!s->world)return m.count;
    static const unsigned limit=[](){const char*value=getenv("SLOT_SCENE_INDEX_BATCH");return value?unsigned(std::max(0,std::min(1048576,std::atoi(value)))/3*3):3072u;}();
    return limit?std::min(limit,m.count):m.count;
}
void drawIndices(const SlotTabletop*s,const Mesh&m){
    const unsigned batch=indexBatch(s,m);
    for(unsigned offset=0;offset<m.count;offset+=batch)glDrawElements(GL_TRIANGLES,std::min(batch,m.count-offset),GL_UNSIGNED_SHORT,(void*)(uintptr_t(offset)*sizeof(uint16_t)));
}
void issue(SlotTabletop*s,const DrawCall&c,int&active,int&offset,bool hole=false){
    const Mesh&m=*c.mesh;countDraw(s,m);const int clipped=c.cutout;const Shading&p=s->shading[clipped];if(clipped!=active){glUseProgram(p.program);active=clipped;}
    if(c.offset!=offset){if(c.offset){glEnable(GL_POLYGON_OFFSET_FILL);glPolygonOffset(-c.offset,-c.offset);}else glDisable(GL_POLYGON_OFFSET_FILL);offset=c.offset;}
    glUniform4fv(p.window,1,c.window.data());glUniform1f(p.cutout,c.cutout?1:0);glUniform1f(p.hole,hole?1:0);
    glUniform1f(p.crt,s->crt&&c.screen&&!hole?1:0);
    glUniformMatrix4fv(p.model,1,GL_FALSE,c.model.v);glUniform1f(p.textured,(c.texture||m.texture)?1:0);glUniform1f(p.unlit,c.unlit);glUniform1f(p.paintOn,c.paint?1:0);glUniform4fv(p.crop,1,c.crop.data());glBindTexture(GL_TEXTURE_2D,c.texture?c.texture:m.texture);
    glBindBuffer(GL_ARRAY_BUFFER,m.vertices);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,m.indices);
    glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,sizeof(Vertex),(void*)0);glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,sizeof(Vertex),(void*)(3*sizeof(float)));glVertexAttribPointer(2,3,GL_FLOAT,GL_FALSE,sizeof(Vertex),(void*)(6*sizeof(float)));glVertexAttribPointer(3,2,GL_FLOAT,GL_FALSE,sizeof(Vertex),(void*)(9*sizeof(float)));drawIndices(s,m);
}
// The cached scene still matches this frame: the same draws with the same settings, and every
// corner of every mesh box within a quarter (logical) pixel of where it was rendered. Screen
// pictures may change freely; composite() draws them every frame.
// Draws each mesh until this context has drawn it warmDraws() times: one round per pass, each
// completed before the next, the mesh fitted into a tiny target with the scene shader and its
// real attribute layout. Nothing on screen changes. Returns the triangles drawn; `rounds` lists
// each round's milliseconds.
long warmMeshes(SlotTabletop*s,const std::vector<std::pair<const Mesh*,GLuint>>&meshes,std::string&rounds,bool incremental=false){
    int most=0;for(auto&m:meshes)most=std::max(most,warmDraws()-drawUses(s,*m.first));
    if(most<=0)return 0;
    // Frames hand off with fences, so earlier GPU work may still be queued here. Drain it
    // first, so each batch's glFinish below (and the 6 ms budget) measures warming alone.
    if(incremental)glFinish();
    if(!s->warmFbo){
        glGenTextures(1,&s->warmColour);glBindTexture(GL_TEXTURE_2D,s->warmColour);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,32,32,0,GL_RGBA,GL_UNSIGNED_BYTE,nullptr);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
        glGenFramebuffers(1,&s->warmFbo);glBindFramebuffer(GL_FRAMEBUFFER,s->warmFbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,s->warmColour,0);
    }
    const Shading&p=s->shading[0];const Mat vp=identity();const GLfloat full[4]={0,0,1,1};
    glBindFramebuffer(GL_FRAMEBUFFER,s->warmFbo);glViewport(0,0,32,32);glDisable(GL_DEPTH_TEST);glDisable(GL_BLEND);glUseProgram(p.program);
    glUniformMatrix4fv(p.vp,1,GL_FALSE,vp.v);glUniform1i(p.texture,0);glUniform1f(p.cel,0);glUniform3f(p.paint,1,1,1);glUniform1f(p.unlit,0);glUniform1f(p.paintOn,0);
    glUniform4fv(p.crop,1,full);glUniform4fv(p.window,1,full);glUniform1f(p.cutout,0);glUniform1f(p.hole,0);glUniform1f(p.crt,0);glActiveTexture(GL_TEXTURE0);for(int i=0;i<4;i++)glEnableVertexAttribArray(i);
    long triangles=0;const Uint64 began=SDL_GetPerformanceCounter();bool complete=false;int pending=0;
    for(int round=0;round<most;round++){
        const Uint64 start=SDL_GetPerformanceCounter();
        for(auto&e:meshes){
            const Mesh&m=*e.first;if(drawUses(s,m)>=warmDraws())continue;
            const Vec centre=mul(add(m.low,m.high),.5f),half=mul(sub(m.high,m.low),.5f);
            const Mat model=product(scale(1/std::max(.001f,half.x),1/std::max(.001f,half.y),1/std::max(.001f,half.z)),translate(mul(centre,-1)));
            glUniformMatrix4fv(p.model,1,GL_FALSE,model.v);glUniform1f(p.textured,e.second?1:0);glBindTexture(GL_TEXTURE_2D,e.second);
            glBindBuffer(GL_ARRAY_BUFFER,m.vertices);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,m.indices);
            glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,sizeof(Vertex),(void*)0);glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,sizeof(Vertex),(void*)(3*sizeof(float)));glVertexAttribPointer(2,3,GL_FLOAT,GL_FALSE,sizeof(Vertex),(void*)(6*sizeof(float)));glVertexAttribPointer(3,2,GL_FLOAT,GL_FALSE,sizeof(Vertex),(void*)(9*sizeof(float)));
            if(incremental){
                auto&progress=s->warmOffsets[m.indexLease.get()];if(progress.first.expired()||progress.second>=m.count){progress.first=m.indexLease;progress.second=0;}
                while(progress.second<m.count){
                    const unsigned count=std::min(indexBatch(s,m),m.count-progress.second);
                    glDrawElements(GL_TRIANGLES,count,GL_UNSIGNED_SHORT,(void*)(uintptr_t(progress.second)*sizeof(uint16_t)));triangles+=count/3;progress.second+=count;
                    if(++pending>=warmFinishBatches()){glFinish();pending=0;}
                    complete=progress.second==m.count;if(complete){progress.second=0;countDraw(s,m);}
                    if(!pending&&1000.0*(SDL_GetPerformanceCounter()-began)/SDL_GetPerformanceFrequency()>=6)goto finished;
                    if(complete)break;
                }
            }else{drawIndices(s,m);countDraw(s,m);triangles+=m.count/3;}
        }
        glFinish();pending=0;char b[16];std::snprintf(b,sizeof(b),"%s%.0f",round?",":"",1000.0*(SDL_GetPerformanceCounter()-start)/SDL_GetPerformanceFrequency());rounds+=b;
    }
finished:
    if(pending)glFinish();
    glBindFramebuffer(GL_FRAMEBUFFER,0);
    for(auto i=s->drawUses.begin();i!=s->drawUses.end();)if(i->second.first.expired())i=s->drawUses.erase(i);else ++i;
    for(auto i=s->warmOffsets.begin();i!=s->warmOffsets.end();)if(i->second.first.expired())i=s->warmOffsets.erase(i);else ++i;
    return triangles;
}
bool sameScene(const SlotTabletop*s){
    if(s->calls.size()!=s->cached.size())return false;
    const float halfW=s->logicalWidth/2.f,halfH=s->logicalHeight/2.f;
    for(size_t i=0;i<s->calls.size();i++){
        const DrawCall&a=s->calls[i],&b=s->cached[i];
        if(a.mesh!=b.mesh||a.screen!=b.screen||a.unlit!=b.unlit||a.paint!=b.paint||a.cutout!=b.cutout||a.offset!=b.offset||std::abs(a.fade-b.fade)>.002f)return false;
        if(!a.screen&&(a.texture!=b.texture||a.crop!=b.crop||a.window!=b.window))return false;
        const Mat now=product(s->view,a.model),then=product(s->cachedView,b.model);const Vec lo=a.mesh->low,hi=a.mesh->high;
        for(int k=0;k<8;k++){
            const Vec c={k&1?hi.x:lo.x,k&2?hi.y:lo.y,k&4?hi.z:lo.z},p=transform(now,c),q=transform(then,c);
            if(std::abs(p.x-q.x)*halfW>.25f||std::abs(p.y-q.y)*halfH>.25f)return false;
        }
    }
    return true;
}
struct GpuTimerApi {
    using Gen=void(*)(GLsizei,GLuint*);using Begin=void(*)(GLenum,GLuint);using End=void(*)(GLenum);
    using Getu=void(*)(GLuint,GLenum,GLuint*);using Get64=void(*)(GLuint,GLenum,uint64_t*);
    Gen gen=nullptr;Begin begin=nullptr;End end=nullptr;Getu getu=nullptr;Get64 get64=nullptr;bool ready=false;
};
const GpuTimerApi&gpuTimer(){
    static const GpuTimerApi api=[]{
        GpuTimerApi a;const char*on=getenv("SLOT_SCENE_GPU_TIMING");if(!on||std::strcmp(on,"1"))return a;
        const char*extensions=(const char*)glGetString(GL_EXTENSIONS);if(!extensions||!std::strstr(extensions,"GL_EXT_disjoint_timer_query"))return a;
        a.gen=(GpuTimerApi::Gen)SDL_GL_GetProcAddress("glGenQueriesEXT");a.begin=(GpuTimerApi::Begin)SDL_GL_GetProcAddress("glBeginQueryEXT");
        a.end=(GpuTimerApi::End)SDL_GL_GetProcAddress("glEndQueryEXT");a.getu=(GpuTimerApi::Getu)SDL_GL_GetProcAddress("glGetQueryObjectuivEXT");
        a.get64=(GpuTimerApi::Get64)SDL_GL_GetProcAddress("glGetQueryObjectui64vEXT");a.ready=a.gen&&a.begin&&a.end&&a.getu&&a.get64;return a;
    }();
    return api;
}
// Reads this slot's results from two frames ago, if the GPU has them and no disjoint occurred.
void gpuCollect(SlotTabletop*s){
    const auto&t=gpuTimer();if(!t.ready)return;
    if(!s->gpuQueries[0][0])t.gen(4,&s->gpuQueries[0][0]);
    GLint disjoint=0;glGetIntegerv(0x8FBB/*GL_GPU_DISJOINT_EXT*/,&disjoint);
    for(int q=0;q<2;q++){
        if(!s->gpuIssued[s->gpuSlot][q])continue;s->gpuIssued[s->gpuSlot][q]=false;
        GLuint available=0;t.getu(s->gpuQueries[s->gpuSlot][q],0x8867/*GL_QUERY_RESULT_AVAILABLE_EXT*/,&available);
        if(!available||disjoint)continue;uint64_t ns=0;t.get64(s->gpuQueries[s->gpuSlot][q],0x8866/*GL_QUERY_RESULT_EXT*/,&ns);
        const int kind=q==1?2:s->gpuKind[s->gpuSlot];s->logGpu[kind]+=ns/1e6;s->logGpuCount[kind]++;
    }
}
void gpuBegin(SlotTabletop*s,int q){const auto&t=gpuTimer();if(t.ready){t.begin(0x88BF/*GL_TIME_ELAPSED_EXT*/,s->gpuQueries[s->gpuSlot][q]);s->gpuIssued[s->gpuSlot][q]=true;}}
void gpuEnd(){const auto&t=gpuTimer();if(t.ready)t.end(0x88BF);}
// Scene-pixel rectangle (x0,y0,x1,y1; GL origin) of a call's mesh box under `view`; false when
// a corner is at or behind the eye, where the projected box is no bound.
bool screenRect(const SlotTabletop*s,const Mat&view,const DrawCall&c,float r[4]){
    const Mat m=product(view,c.model);const Vec lo=c.mesh->low,hi=c.mesh->high;
    r[0]=r[1]=1e30f;r[2]=r[3]=-1e30f;
    for(int k=0;k<8;k++){
        const Vec p={k&1?hi.x:lo.x,k&2?hi.y:lo.y,k&4?hi.z:lo.z};
        const float w=m.v[3]*p.x+m.v[7]*p.y+m.v[11]*p.z+m.v[15];if(w<1e-3f)return false;
        const float x=((m.v[0]*p.x+m.v[4]*p.y+m.v[8]*p.z+m.v[12])/w+1)*s->width/2,y=((m.v[1]*p.x+m.v[5]*p.y+m.v[9]*p.z+m.v[13])/w+1)*s->height/2;
        r[0]=std::min(r[0],x);r[1]=std::min(r[1],y);r[2]=std::max(r[2],x);r[3]=std::max(r[3],y);
    }
    return true;
}
// Some draws moved while the camera stayed (the home table's hovering console): the same draws
// in the same order and state, and an identical projection apart from its depth row (the near
// plane hugs the closest geometry). Every other draw has exactly its cached pose, so only the
// rectangle covering the moved draws' old and new boxes can differ from the cached scene.
// SLOT_SCENE_PARTIAL=0 always re-renders the whole scene (A/B pixel evidence).
bool partialScene(const SlotTabletop*s,int rect[4]){
    static const bool enabled=!(getenv("SLOT_SCENE_PARTIAL")&&std::strcmp(getenv("SLOT_SCENE_PARTIAL"),"0")==0);
    if(!enabled||!s->cacheValid||s->calls.size()!=s->cached.size())return false;
    for(int row:{0,1,3})for(int col=0;col<4;col++)if(s->view.v[col*4+row]!=s->cachedView.v[col*4+row])return false;
    float dirty[4]={1e30f,1e30f,-1e30f,-1e30f};bool moved=false;
    for(size_t i=0;i<s->calls.size();i++){
        const DrawCall&a=s->calls[i],&b=s->cached[i];
        if(a.mesh!=b.mesh||a.screen!=b.screen||a.unlit!=b.unlit||a.paint!=b.paint||a.cutout!=b.cutout||a.offset!=b.offset)return false;
        bool same=a.fade==b.fade&&(a.screen||(a.texture==b.texture&&a.crop==b.crop&&a.window==b.window));
        for(int k=0;same&&k<16;k++)same=a.model.v[k]==b.model.v[k];
        if(same)continue;
        float r[4];
        for(const auto&box:{std::make_pair(&s->view,&a),std::make_pair(&s->cachedView,&b)}){
            if(!screenRect(s,*box.first,*box.second,r))return false;
            dirty[0]=std::min(dirty[0],r[0]);dirty[1]=std::min(dirty[1],r[1]);dirty[2]=std::max(dirty[2],r[2]);dirty[3]=std::max(dirty[3],r[3]);
        }
        moved=true;
    }
    if(!moved)return false;
    // Two pixels of margin cover rasterisation and multisample coverage at the box edges.
    rect[0]=std::max(0,(int)std::floor(dirty[0])-2);rect[1]=std::max(0,(int)std::floor(dirty[1])-2);
    rect[2]=std::min(s->width,(int)std::ceil(dirty[2])+2);rect[3]=std::min(s->height,(int)std::ceil(dirty[3])+2);
    if(rect[2]<=rect[0]||rect[3]<=rect[1])return false;
    return (rect[2]-rect[0])*(rect[3]-rect[1])<=s->width*s->height*6/10;
}
// The frame: the cached scene copied as is, then each live screen blended in through the hole
// it left (source x (1 - hole alpha) + cached colour), so anything in front of a screen,
// including a faded cart, still covers it; finally alpha is made opaque for the frontend.
void composite(SlotTabletop*s,const std::vector<char>&visible,int&active,int&offset){
    glBindFramebuffer(GL_FRAMEBUFFER,s->fbo);glViewport(0,0,s->width,s->height);glDisable(GL_DEPTH_TEST);glDepthMask(GL_FALSE);glDisable(GL_BLEND);
    static const GLfloat quad[8]={-1,-1,1,-1,-1,1,1,1};
    glUseProgram(s->copy.program);active=-1;glUniform1i(s->copy.texture,0);glUniform2f(s->copy.size,(float)s->width,(float)s->height);glBindTexture(GL_TEXTURE_2D,s->sceneTexture);
    for(int i=1;i<4;i++)glDisableVertexAttribArray(i);
    glBindBuffer(GL_ARRAY_BUFFER,0);glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,0,quad);glDrawArrays(GL_TRIANGLE_STRIP,0,4);
    for(int i=1;i<4;i++)glEnableVertexAttribArray(i);
    // Alpha saturates where a screen was drawn, so overlapping glass parts (the PVM's) add it once.
    glEnable(GL_BLEND);glBlendFuncSeparate(GL_ONE_MINUS_DST_ALPHA,GL_ONE,GL_ONE,GL_ONE);
    for(size_t i=0;i<s->calls.size();i++)if(s->calls[i].screen&&visible[i])issue(s,s->calls[i],active,offset);
    glDisable(GL_BLEND);glColorMask(GL_FALSE,GL_FALSE,GL_FALSE,GL_TRUE);glClearColor(0,0,0,1);glClear(GL_COLOR_BUFFER_BIT);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
    glDepthMask(GL_TRUE);glEnable(GL_DEPTH_TEST);
}
// Order: opaque draws nearest first (hidden pixels then fail the depth test before shading),
// cut-out labels, then faded carts. A faded cart first lays down the depth of its nearest
// surface with colour writes off, then blends that surface alone (GL_EQUAL) at its fade over
// what is behind it: translucent without a discard, and its own hidden parts stay hidden.
void submit(SlotTabletop*s){
    gpuCollect(s);
    const size_t n=s->calls.size();std::vector<char> visible(n,1);std::vector<float> closest(n,0);
    if(s->fitNear){
        const float tanY=std::tan(s->projectionFov/2)*1.01f,tanX=tanY*s->width/s->height;DepthRange range;float farthest=0;
        for(size_t i=0;i<n;i++){
            const auto&c=s->calls[i];DepthRange own;visible[i]=boxDepth(own,s->eyeView,c.model,c.mesh->low,c.mesh->high,tanX,tanY)||!s->cull;closest[i]=own.closest;
            if(own.visible){
                farthest=std::max(farthest,own.farthest);
                // The combined floor/wall box encloses the camera. Its box's
                // zero depth is not an actual nearby surface; including it
                // forces a 10 mm near plane and wastes room-scale depth precision.
                if(!s->world||c.flightGroup!=-6){range.visible=true;range.closest=std::min(range.closest,own.closest);range.farthest=std::max(range.farthest,own.farthest);}
            }
        }
        const float farPlane=s->world&&farthest>0?std::max(10000.f,farthest+500.f):10000.f;
        s->nearPlane=hugNear(range);s->view=product(perspective(s->projectionFov,(float)s->width/s->height,s->nearPlane,farPlane),s->eyeView);
    }
    for(const auto&p:s->shading){glUseProgram(p.program);glUniformMatrix4fv(p.vp,1,GL_FALSE,s->view.v);glUniform1i(p.texture,0);glUniform1f(p.cel,s->cel);glUniform3f(p.paint,s->paintColor.x,s->paintColor.y,s->paintColor.z);}
    std::vector<size_t> order;for(size_t i=0;i<n;i++)if(visible[i])order.push_back(i);s->drawn=(int)order.size();s->culled=(int)(n-order.size());
    int offset=0,active=-1;
    int rect[4];
    if(s->reuse&&s->cacheValid&&sameScene(s))s->reused++;
    else{
        const bool partial=s->reuse&&partialScene(s,rect);
        if(partial){
            // Only draws whose box reaches the rectangle can change pixels inside it.
            order.erase(std::remove_if(order.begin(),order.end(),[&](size_t k){float r[4];return screenRect(s,s->view,s->calls[k],r)&&(r[2]<rect[0]||r[0]>rect[2]||r[3]<rect[1]||r[1]>rect[3]);}),order.end());
            glEnable(GL_SCISSOR_TEST);glScissor(rect[0],rect[1],rect[2]-rect[0],rect[3]-rect[1]);s->partials++;
        }
        // Screens draw as holes (transparent black); composite() fills them every frame.
        glBindFramebuffer(GL_FRAMEBUFFER,s->sceneFbo);s->gpuKind[s->gpuSlot]=partial?1:0;gpuBegin(s,0);
        glViewport(0,0,s->width,s->height);glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LEQUAL);glDepthMask(GL_TRUE);glClearColor(.025f,.030f,.040f,1);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
        auto pass=[&](size_t i){const auto&c=s->calls[i];return c.fade<1?2:c.cutout?1:0;};
        std::stable_sort(order.begin(),order.end(),[&](size_t a,size_t b){int pa=pass(a),pb=pass(b);return pa!=pb?pa<pb:s->sort&&closest[a]<closest[b];});
        size_t i=0;
        for(;i<order.size()&&pass(order[i])<2;i++)issue(s,s->calls[order[i]],active,offset,s->calls[order[i]].screen);
        if(i<order.size()){
            glColorMask(GL_FALSE,GL_FALSE,GL_FALSE,GL_FALSE);for(size_t k=i;k<order.size();k++)issue(s,s->calls[order[k]],active,offset);
            glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glDepthFunc(GL_EQUAL);glDepthMask(GL_FALSE);glEnable(GL_BLEND);glBlendFunc(GL_CONSTANT_ALPHA,GL_ONE_MINUS_CONSTANT_ALPHA);
            for(size_t k=i;k<order.size();k++){glBlendColor(0,0,0,s->calls[order[k]].fade);issue(s,s->calls[order[k]],active,offset);}
            glDisable(GL_BLEND);glDepthMask(GL_TRUE);glDepthFunc(GL_LEQUAL);
        }
        gpuEnd();if(partial)glDisable(GL_SCISSOR_TEST);
        s->cached=s->calls;s->cachedView=s->view;s->cacheValid=true;s->rendered++;
    }
    gpuBegin(s,1);composite(s,visible,active,offset);gpuEnd();s->gpuSlot^=1;
    if(offset)glDisable(GL_POLYGON_OFFSET_FILL);s->calls.clear();
}
// Part of the glass UV square left visible by the bezel, with a small margin.
// Panasonic measured with a 5% grid: ~5% hidden frontally, ~6.5% at the browse angle.
std::array<float,4> screenWindow(const std::string&tv){
    if(tv=="panasonic")return {{.07f,.07f,.93f,.93f}};
    // 5% grid on the glass, zoomed (session-20261018m): the PVM bezel hides ~3%, the Old TV's
    // rounded tube corners ~4%.
    if(tv=="pvm")return {{.03f,.03f,.97f,.97f}};
    if(tv=="oldtv")return {{.04f,.04f,.96f,.96f}};
    return {{0,0,1,1}};
}
void deleteMesh(Mesh&m){m={};}
// Moving parts are original triangles of model.mesh: the registered power slider
// and, on the N64, the two dust flaps. Each shares the body's vertex buffer.
void splitControls(SlotTabletop*s,Console&c,Mesh&body,const std::string&modelPath){
    FrontRegistration front;OpticalRegistration optical;HandheldRegistration handheld;
    const bool lidded=frontRegistration(c.name,front)||opticalRegistration(c.name,optical)||(handheldRegistration(c.name,handheld)&&handheld.cover);
    if(!lidded&&!exists(s->prepared+"/"+c.name+"/power.control")&&!exists(s->prepared+"/"+c.name+"/led.control")&&!exists(s->prepared+"/"+c.name+"/flaps.control"))return;
    auto source=bytes(modelPath);const uint64_t hash=fnv(source.data(),source.size());
    // Parts: 0 body, 1 power control, 2 power indicator, 3 front-loader lid, 4+ flaps.
    const unsigned triangles=body.count/3;std::vector<unsigned> part(triangles,0);bool moving=false;
    auto powerPath=s->prepared+"/"+c.name+"/power.control";
    if(exists(powerPath)){
        auto mask=bytes(powerPath);
        if(mask.size()<20||std::memcmp(mask.data(),"SCSWCH1\0",8)||read<uint64_t>(mask,8)!=hash)throw std::runtime_error("Invalid power-control source registration");
        unsigned count=read<uint32_t>(mask,16);if(!count||count>triangles||mask.size()!=20+count*4)throw std::runtime_error("Invalid power-control mask");
        for(unsigned i=0;i<count;i++){unsigned t=read<uint32_t>(mask,20+i*4);if(t>=triangles||part[t])throw std::runtime_error("Invalid control triangle");part[t]=1;}
        moving=true;
    }
    auto ledPath=s->prepared+"/"+c.name+"/led.control";
    if(exists(ledPath)){
        auto mask=bytes(ledPath);
        if(mask.size()<20||std::memcmp(mask.data(),"SCSWCH1\0",8)||read<uint64_t>(mask,8)!=hash)throw std::runtime_error("Invalid indicator source registration");
        unsigned count=read<uint32_t>(mask,16);if(!count||count>triangles||mask.size()!=20+count*4)throw std::runtime_error("Invalid indicator mask");
        for(unsigned i=0;i<count;i++){unsigned t=read<uint32_t>(mask,20+i*4);if(t>=triangles||part[t])throw std::runtime_error("Invalid indicator triangle");part[t]=2;}
        moving=true;
    }
    // A front loader's, optical console's or PSP's lid/cover is the tail of the index
    // buffer (the SCTOON2 door field).
    if(lidded&&std::memcmp(source.data(),"SCTOON2\0",8)==0){
        unsigned door=read<uint32_t>(source,16);if(door%3||door>body.count)throw std::runtime_error("Invalid lid range");
        for(unsigned t=door/3;t<triangles;t++){if(part[t])throw std::runtime_error("Overlapping moving parts");part[t]=3;}
        moving=moving||door<body.count;
    }
    auto flapPath=s->prepared+"/"+c.name+"/flaps.control";
    if(exists(flapPath)){
        std::ifstream in(flapPath);std::string magic;unsigned long long registered=0;unsigned count=0;
        if(!(in>>magic>>registered>>c.flapClearance>>c.flapSlot>>count)||magic!="SCFLAPS1"||registered!=hash||!count||count>4)throw std::runtime_error("Invalid flap registration");
        for(unsigned i=0;i<count;i++){
            Flap flap;unsigned first=0,length=0,points=0;
            if(!(in>>first>>length>>flap.section.hinge[0]>>flap.section.hinge[1]>>flap.section.side>>points)||first%3||length%3||!length||first+length>body.count||points<2||points>64)throw std::runtime_error("Invalid flap section");
            flap.section.profile.resize(points);for(auto&p:flap.section.profile)if(!(in>>p[0]>>p[1]))throw std::runtime_error("Truncated flap profile");
            for(unsigned t=first/3;t<(first+length)/3;t++){if(part[t])throw std::runtime_error("Overlapping moving parts");part[t]=4+i;}
            c.flaps.push_back(flap);
        }
        moving=true;
    }
    if(!moving)return;
    size_t start=20+read<uint32_t>(source,8)*36;std::vector<std::vector<uint16_t>> lists(4+c.flaps.size());
    for(unsigned t=0;t<triangles;t++)for(int v=0;v<3;v++)lists[part[t]].push_back(read<uint16_t>(source,start+(t*3+v)*2));
    auto upload=[&](Mesh&m,const std::vector<uint16_t>&list){
        UploadScope permission(s);
        m=body;m.sharedVertices=true;m.count=list.size();glGenBuffers(1,&m.indices);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,m.indices);glBufferData(GL_ELEMENT_ARRAY_BUFFER,list.size()*2,list.data(),GL_STATIC_DRAW);
        m.indexLease=lease(s,m.indices,false,list.size()*2);
    };
    if(!lists[1].empty())upload(c.power,lists[1]);
    if(!lists[2].empty())upload(c.led,lists[2]);
    if(!lists[3].empty())upload(c.lid,lists[3]);
    for(size_t i=0;i<c.flaps.size();i++)upload(c.flaps[i].mesh,lists[4+i]);
    body.count=lists[0].size();glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,body.indices);glBufferData(GL_ELEMENT_ARRAY_BUFFER,lists[0].size()*2,lists[0].data(),GL_STATIC_DRAW);
}
// The theme's GBA SP setting keeps the user's local NeilVFX housing (same frame and
// bay as the packaged SP) unless the packaged thegraphicsgeek SP is chosen.
std::string consoleMesh(const std::string&root,const std::string&name,const std::string&gbaChoice){
    if(name=="gba"&&gbaChoice!="graphicsgeek"&&exists(root+"/local-models/consoles/gba/model.mesh"))return root+"/local-models/consoles/gba/model.mesh";
    return root+"/consoles/"+name+"/model.mesh";
}
Console loadConsole(SlotTabletop*s,const std::string&name){
    Console c;c.name=name;const std::string path=consoleMesh(s->root,name,s->gbaChoice);
    Mesh body=mesh(s,path);c.model.low=body.low;c.model.high=body.high;
    splitControls(s,c,body,path);c.model.parts.push_back(body);
    for(const auto&spec:slotScreens)if(name==spec.name)for(int display=0;display<spec.count;display++){
        float points[12];std::copy(spec.points[display],spec.points[display]+12,points);
        if(name=="gba"&&path.find("local-models/")!=std::string::npos){
            auto pose=bytes(path.substr(0,path.size()-5)+".pose");
            if(pose.size()!=80||std::memcmp(pose.data(),"SCLCD001",8))throw std::runtime_error("Invalid local LCD registration");
            for(int i=0;i<12;i++)points[i]=read<float>(pose,24+i*4);
        }
        // The registered screen is coplanar with the housing's glass (measured: no glass vertex
        // in front of it, PSP aside), and the launch zoom ends ~57 mm from it, where a polygon
        // offset alone no longer wins; lift it 0.2 mm off the glass along its front.
        {Vec p0={points[0],points[1],points[2]},p1={points[3],points[4],points[5]},p3={points[9],points[10],points[11]};
         Vec lift=mul(unit(cross(sub(p1,p0),sub(p0,p3))),.2f*consoleUnits(name));for(int k=0;k<4;k++){points[k*3]+=lift.x;points[k*3+1]+=lift.y;points[k*3+2]+=lift.z;}}
        c.lcdCorners.push_back({{{points[0],points[1],points[2]},{points[3],points[4],points[5]},{points[6],points[7],points[8]},{points[9],points[10],points[11]}}});
        Vertex vertices[4];const float uv[4][2]={{0,0},{1,0},{1,1},{0,1}};
        for(int i=0;i<4;i++)vertices[i]={{points[i*3],points[i*3+1],points[i*3+2]},{0,0,1},{1,1,1},{uv[i][0],uv[i][1]}};
        const uint16_t indices[]={0,3,2,0,2,1};Mesh lcd;lcd.count=6;lcd.low={1e9f,1e9f,1e9f};lcd.high={-1e9f,-1e9f,-1e9f};
        for(auto&v:vertices)for(int j=0;j<3;j++){((float*)&lcd.low)[j]=std::min(((float*)&lcd.low)[j],v.p[j]);((float*)&lcd.high)[j]=std::max(((float*)&lcd.high)[j],v.p[j]);}
        UploadScope permission(s);glGenBuffers(1,&lcd.vertices);glBindBuffer(GL_ARRAY_BUFFER,lcd.vertices);glBufferData(GL_ARRAY_BUFFER,sizeof(vertices),vertices,GL_STATIC_DRAW);
        glGenBuffers(1,&lcd.indices);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,lcd.indices);glBufferData(GL_ELEMENT_ARRAY_BUFFER,sizeof(indices),indices,GL_STATIC_DRAW);
        lcd.vertexLease=lease(s,lcd.vertices,false,sizeof(vertices));lcd.indexLease=lease(s,lcd.indices,false,sizeof(indices));c.lcds.push_back(lcd);
    }
    HandheldRegistration handheld;if(handheldRegistration(name,handheld))c.table=handheld.table;
    c.rest=1e9f;c.top=-1e9f;const float u=consoleUnits(name);
    for(int k=0;k<8;k++){Vec p=transform(c.table,{k&1?body.high.x:body.low.x,k&2?body.high.y:body.low.y,k&4?body.high.z:body.low.z});c.rest=std::min(c.rest,p.y/u);c.top=std::max(c.top,p.y/u);}
    return c;
}
// The console's placement frame on the table in mm, and its model matrix (native units).
Mat consoleFrame(const Console&c,const Placement&at){return product(at.matrix(),c.table);}
Mat consoleModel(const Console&c,const Placement&at){return product(consoleFrame(c,at),scale(1/consoleUnits(c.name),1/consoleUnits(c.name),1/consoleUnits(c.name)));}
// Lowest vertex coordinate of a mesh along an axis without uploading it, for layouts
// authored on another console (its console base, its media's resting face).
float meshLow(const std::string&path,int axis){
    auto d=bytes(path);if(d.size()<20)throw std::runtime_error("Short scene mesh");
    size_t stride=std::memcmp(d.data(),"SCTOON2\0",8)==0?36:44;unsigned n=read<uint32_t>(d,8);float low=1e9f;
    for(unsigned i=0;i<n;i++)low=std::min(low,read<float>(d,20+i*stride+4*axis));
    return low;
}
float meshLowY(const std::string&path){return meshLow(path,1);}
// Power-control travel when switched on, console mm (CONTROLS in tools/tabletop/prepare_controls.py).
Vec powerTravel(const std::string&console){
    if(console=="n64")return {0,0,7};
    if(console=="nes")return {0,0,-2};
    if(console=="md"||console=="md-jp")return {-12/(224.f/109),0,0};
    return {0,0,-6};
}
// A borrowed layout's cartridge nodes rest its own console's media on the table: lift
// or lower other media (thinner carts, flat discs) so their lowest face rests the same.
float restOffset(const SlotTabletop*s,const Media&m){return s->layoutMediaKnown?s->layoutMediaLow-m.shell.low.z/m.units:0;}
// Regional console shown while that region's media is in play (US SNES, Japanese Mega Drive).
std::string regionalConsole(const std::string&system){return system=="snes"?"snes-us":system=="md"?"md-jp":"";}
// The US SNES replaces the authored PAL console while a USA cart is inserted,
// moving or loaded; with nothing loaded the table keeps the authored console.
int activeConsole(const SlotTabletop*s){return s->consoleCount>1&&s->hasResident&&s->resident.model.rfind(s->consoles[1].name,0)==0?1:0;}
// The authored console node's footprint and turn; lifted so this console's base rests
// on the plane the layout's own console stood on (US SNES, or N64 on a SNES layout).
Placement consolePlacement(const SlotTabletop*s,int index){
    Placement p=s->layout.nodes[2];const Console&b=s->consoles[index];
    p.position.y+=s->layoutBottom-b.rest;
    return p;
}
// Authored camera: horizontal framing kept when the viewport ratio changes.
float authoredFov(const SlotTabletop*s){float tangent=std::tan(radians(s->layout.fov)/2)*(float)s->layout.width/s->layout.height;return 2*std::atan(tangent*s->height/s->width);}
Vec orbitEye(const SlotTabletop*s,float yaw,float elevation){if(yaw==0&&elevation==0)return s->layout.eye;return add(s->layout.target,transform(rotate(radians(elevation),radians(yaw),0),sub(s->layout.eye,s->layout.target)));}
Mat authoredView(const SlotTabletop*s,Vec eye,Vec target){return product(perspective(authoredFov(s),(float)s->width/s->height,150,10000),lookAt(eye,target));}
// Slotted's home table ---------------------------------------------------------------------
// items[] lists the frontend's systems with games (model = its console); a placed console is
// shown when its room is among them. Returns that entry's index, or -1.
int homeEntry(const SlotTabletop*s,size_t i){
    const std::string room=homeSystem(s->homeItems[i].model);
    for(size_t k=0;k<s->items.size();k++)if(homeSystem(s->items[k].model)==room)return (int)k;
    return -1;
}
// Dedicated UI view: the whole TV cabinet and its top status UI stay visible.
// An authored home screen camera wins; no existing saved camera is reframed.
ProfileCamera screenCamera(const SlotTabletop*s){
    if(s->home&&s->homeLayout.screen.authored)return s->homeLayout.screen;
    const auto tv=s->layout.nodes[1].matrix();
    const float statusScale=std::min(1.f,(s->television.high.x-s->television.low.x)/468.f);
    const auto status=product(tv,s->layout.nodes[3].matrix(statusScale));
    std::vector<Vec> points;
    auto bounds=[&](Vec low,Vec high,const Mat&at){
        for(int i=0;i<8;i++)points.push_back(transform(at,{i&1?high.x:low.x,i&2?high.y:low.y,i&4?high.z:low.z}));
    };
    bounds(s->television.low,s->television.high,tv);
    // Reserve the widest supported cluster, so clock/battery changes cannot
    // cause the computed UI camera to move or clip newly visible status glyphs.
    static const std::array<Vec,2> statusExtent=[](){
        auto geometry=statusVoxels(100,true,true,"88:88");
        Vec low={1e9f,1e9f,1e9f},high={-1e9f,-1e9f,-1e9f};
        for(const auto&v:geometry.vertices){low={std::min(low.x,v.p[0]),std::min(low.y,v.p[1]),std::min(low.z,v.p[2])};high={std::max(high.x,v.p[0]),std::max(high.y,v.p[1]),std::max(high.z,v.p[2])};}
        return std::array<Vec,2>{{low,high}};
    }();
    bounds(statusExtent[0],statusExtent[1],status);
    Vec low=points.front(),high=low;
    for(auto p:points){low={std::min(low.x,p.x),std::min(low.y,p.y),std::min(low.z,p.z)};high={std::max(high.x,p.x),std::max(high.y,p.y),std::max(high.z,p.z)};}
    Vec centre=mul(add(low,high),.5f);
    Vec normal=unit(sub(transform(tv,{0,0,1}),transform(tv,{0,0,0})));
    if(std::abs(normal.y)>.999f)normal=unit(add(normal,{0,0,.05f})); // avoid a singular world-up camera for a face-up TV
    // See the top edge from slightly above: a level perspective camera lets
    // the front rim hide the bottom of status glyphs standing farther back.
    normal=unit(add(normal,{0,.22f,0}));
    const Vec right=unit(cross({0,1,0},normal)),up=cross(normal,right);
    const float fov=30,aspect=float(s->logicalWidth)/s->logicalHeight,t=std::tan(radians(fov)/2);
    float distance=170,positiveX=-1e9f,negativeX=-1e9f,positiveY=-1e9f,negativeY=-1e9f;
    const float tx=t*aspect*.92f,ty=t*.92f;
    for(auto p:points){
        const Vec offset=sub(p,centre);const float depth=dot(offset,normal);
        distance=std::max(distance,depth+150);
        positiveX=std::max(positiveX,depth+dot(offset,right)/tx);negativeX=std::max(negativeX,depth-dot(offset,right)/tx);
        positiveY=std::max(positiveY,depth+dot(offset,up)/ty);negativeY=std::max(negativeY,depth-dot(offset,up)/ty);
    }
    // Balance the opposite perspective constraints. A world-box centre leaves
    // deep CRTs low in the picture and unnecessarily shrinks the readable glass.
    centre=add(centre,add(mul(right,(positiveX-negativeX)*tx*.5f),mul(up,(positiveY-negativeY)*ty*.5f)));
    distance=std::max({distance,(positiveX+negativeX)*.5f,(positiveY+negativeY)*.5f});
    // Ordinary camera evaluation compensates a saved profile's aspect ratio.
    // This new computed view fits the current viewport, so express its FOV in
    // that same source convention before the existing compensation is applied.
    ProfileCamera c;c.target=centre;c.eye=add(centre,mul(normal,distance));
    c.fov=2*std::atan(t*aspect*s->layout.height/s->layout.width)*180/3.14159265f;c.authored=true;return c;
}
// Overview leaning toward the highlighted console (view 0) or, more, the TV (view 1, channels).
ProfileCamera homeCamera(const SlotTabletop*s,int view,int selected){
    if(view==5)return screenCamera(s);
    ProfileCamera c=s->homeLayout.overview;Vec focus={0,0,0};bool lean=false;float amount=s->homeLayout.follow;
    if(view==1){const Vec lo=s->television.glassLow,hi=s->television.glassHigh;focus=transform(s->tvPose,mul(add(lo,hi),.5f));lean=true;amount=std::min(.8f,amount*1.6f);}
    else if(selected>=0)for(size_t i=0;i<s->homeItems.size();i++)if(homeEntry(s,i)==selected){
        const auto&h=s->homeItems[i];focus=transform(consoleModel(h.console,h.at),mul(add(h.console.model.low,h.console.model.high),.5f));lean=true;
    }
    if(lean){const Vec delta=mul(sub(focus,c.target),amount);c.target=add(c.target,delta);c.eye=add(c.eye,mul(delta,.5f));}
    return c;
}
ProfileCamera viewCamera(const SlotTabletop*s,int view,int selected){
    if(s->home)return homeCamera(s,view,selected);
    if(view==5)return screenCamera(s);
    ProfileCamera c;c.eye=s->layout.eye;c.target=s->layout.target;c.fov=s->layout.fov;c.authored=true;
    if(view>0&&s->layout.cameras[view].authored)c=s->layout.cameras[view];
    else if(view>0&&view<4){
        Vec low,high;Mat model=identity();Vec normal={0,.6f,1};
        if(view==1){low=s->television.low;high=s->television.high;model=s->tvPose;normal=unit(sub(transform(model,{0,0,1}),transform(model,{0,0,0})));}
        else if(view==3){low=s->consoles[0].model.low;high=s->consoles[0].model.high;model=consoleModel(s->consoles[0],consolePlacement(s,0));}
        else{const auto&m=s->media.at(s->system);low=m.shell.low;high=m.shell.high;model=s->layout.nodes[4].matrix(1/m.units);normal={0,.78f,.62f};}
        Vec lo={1e9f,1e9f,1e9f},hi={-1e9f,-1e9f,-1e9f};
        for(int k=0;k<8;k++){Vec v=transform(model,{k&1?high.x:low.x,k&2?high.y:low.y,k&4?high.z:low.z});for(int i=0;i<3;i++){((float*)&lo)[i]=std::min(((float*)&lo)[i],((float*)&v)[i]);((float*)&hi)[i]=std::max(((float*)&hi)[i],((float*)&v)[i]);}}
        if(view==1)for(int k=0;k<8;k++){Vec v=transform(s->statusPose,{k&1?200.f:-200.f,k&2?26.f:0.f,k&4?5.f:0.f});for(int i=0;i<3;i++){((float*)&lo)[i]=std::min(((float*)&lo)[i],((float*)&v)[i]);((float*)&hi)[i]=std::max(((float*)&hi)[i],((float*)&v)[i]);}}
        c.target=mul(add(lo,hi),.5f);c.fov=view==2?34:40;float aspect=(float)s->layout.width/s->layout.height,tangent=std::tan(radians(c.fov)/2);
        normal=unit(normal);Vec right=unit(cross({0,1,0},normal)),up=cross(normal,right);float distance=180;
        for(int k=0;k<8;k++){Vec point=sub({k&1?hi.x:lo.x,k&2?hi.y:lo.y,k&4?hi.z:lo.z},c.target);float depth=dot(point,normal);distance=std::max({distance,depth+150,depth+std::abs(dot(point,up))/(tangent*.9f),depth+std::abs(dot(point,right))/(tangent*aspect*.9f)});}
        c.eye=add(c.target,mul(normal,distance+20));
    }
    if(view==2&&selected>=0&&selected<s->layout.cartridgeCount){Vec delta=sub(s->layout.nodes[4+selected].position,s->layout.nodes[4].position);c.eye=add(c.eye,delta);c.target=add(c.target,delta);}
    return c;
}
ProfileCamera panCamera(SlotTabletop*s,int view,int selected,float delta){
    const auto goal=viewCamera(s,view,selected);
    if(s->cameraView<0){s->panCurrent=goal;s->panTo=goal;s->panSeconds=s->panTime=s->layout.transitionSeconds;}
    if(view!=s->cameraView||((view==2||(s->home&&view!=5))&&selected!=s->cameraSelection)){
        s->panFrom=s->panCurrent;s->panTo=goal;s->panTime=0;s->cameraView=view;s->cameraSelection=selected;
        s->panSeconds=s->panLimit>0?std::min(s->panLimit,s->layout.transitionSeconds):s->layout.transitionSeconds;
    }
    s->panTime+=std::max(0.f,std::min(.1f,delta));s->panCurrent=blendCamera(s->panFrom,s->panTo,s->panTime/s->panSeconds);return s->panCurrent;
}
// Logical pixels by which projected points leave the 720 x 480 view.
float overflow(const SlotTabletop*s,const Mat&view,const std::vector<Vec>&points){
    float left=1e9f,top=1e9f,right=-1e9f,bottom=-1e9f,w=(float)s->logicalWidth,h=(float)s->logicalHeight;
    for(auto&p:points){Vec q=transform(view,p);float x=(q.x+1)*w/2,y=(1-q.y)*h/2;left=std::min(left,x);right=std::max(right,x);top=std::min(top,y);bottom=std::max(bottom,y);}
    return std::max(0.f,-left)+std::max(0.f,right-w)+std::max(0.f,-top)+std::max(0.f,bottom-h);
}
// The user's camera may already crop; orbiting must not crop the TV screen,
// status or console any further. Sampled per side in 0.5 degree steps.
void orbitLimits(SlotTabletop*s,const Mat&consolePose){
    // The screen is the part of the glass the bezel leaves visible (screenWindow).
    std::vector<Vec> groups[3];Vec lo=s->television.glassLow,hi=s->television.glassHigh;auto w=screenWindow(s->tv);
    for(int k=0;k<4;k++){float u=w[k==1||k==2?2:0],v=w[k>=2?3:1];groups[0].push_back(transform(s->tvPose,{lo.x+(hi.x-lo.x)*u,hi.y-(hi.y-lo.y)*v,hi.z}));}
    frameBox(groups[1],{-200,0,0},{200,26,5},s->statusPose);frameBox(groups[2],s->consoles[0].model.low,s->consoles[0].model.high,consolePose);
    float rest[3];Mat view=authoredView(s,s->layout.eye,s->layout.target);for(int g=0;g<3;g++)rest[g]=overflow(s,view,groups[g]);
    for(int side=0;side<2;side++){
        s->orbitLimit[side]=0;
        for(float step=.5f;step<=8.001f;step+=.5f){
            view=authoredView(s,orbitEye(s,side?step:-step,0),s->layout.target);bool ok=true;
            for(int g=0;g<3;g++)ok=ok&&overflow(s,view,groups[g])<=rest[g]+1;
            if(!ok)break;s->orbitLimit[side]=step;
        }
    }
}
// The selected loose cart lifted toward the camera, centred at about half the view
// height, and far enough that a full turn never reaches the 150 mm near plane.
Mat inspectModel(const SlotTabletop*s,const Media&m,const Mat&rest,const SlotTabletopFrame&f){
    Vec size=mul(sub(m.shell.high,m.shell.low),1/m.units),pivot=mul(add(m.shell.low,m.shell.high),.5f);
    float radius=std::sqrt(dot(size,size))/2,tangent=std::tan(s->cameraFov/2),aspect=(float)s->width/s->height;
    float distance=std::max({size.y/(.55f*2*tangent),size.x/(.55f*2*tangent*aspect),150+radius+10});
    Vec centre=add(s->cameraEye,mul(unit(sub(s->cameraTarget,s->cameraEye)),distance));
    return inspectBlend(rest,pivot,1/m.units,inspectRotation(s->cameraEye,s->cameraTarget,radians(f.inspectYaw),radians(f.inspectPitch)),centre,f.inspection);
}
// Projected (NDC) convex outline of a model-space box, counter-clockwise; empty when a corner
// is not in front of the eye.
using Outline=std::vector<std::array<float,2>>;
float turn(const std::array<float,2>&o,const std::array<float,2>&a,const std::array<float,2>&b){return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0]);}
Outline outline(const Mat&projection,const Mat&eye,const Mat&model,Vec low,Vec high){
    const Mat toEye=product(eye,model),toClip=product(projection,toEye);Outline p;
    for(int k=0;k<8;k++){Vec c={k&1?high.x:low.x,k&2?high.y:low.y,k&4?high.z:low.z};if(transform(toEye,c).z>-1)return {};Vec q=transform(toClip,c);p.push_back({{q.x,q.y}});}
    std::sort(p.begin(),p.end());Outline h(2*p.size());size_t k=0;
    for(size_t i=0;i<p.size();i++){while(k>=2&&turn(h[k-2],h[k-1],p[i])<=0)k--;h[k++]=p[i];}
    for(size_t i=p.size()-1,t=k+1;i>0;i--){while(k>=t&&turn(h[k-2],h[k-1],p[i-1])<=0)k--;h[k++]=p[i-1];}
    h.resize(k>0?k-1:0);return h;
}
float area(const Outline&p){float a=0;for(size_t i=0;i<p.size();i++){const auto&u=p[i],&v=p[(i+1)%p.size()];a+=u[0]*v[1]-u[1]*v[0];}return std::abs(a)/2;}
// Part of `subject` inside the convex counter-clockwise `clipper`.
Outline clip(Outline subject,const Outline&clipper){
    for(size_t i=0;i<clipper.size()&&!subject.empty();i++){
        const auto&a=clipper[i],&b=clipper[(i+1)%clipper.size()];Outline out;
        for(size_t j=0;j<subject.size();j++){
            const auto&p=subject[j],&q=subject[(j+1)%subject.size()];float dp=turn(a,b,p),dq=turn(a,b,q);
            if(dp>=0)out.push_back(p);
            if((dp>=0)!=(dq>=0)){float t=dp/(dp-dq);out.push_back({{p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t}});}
        }
        subject=out;
    }
    return subject;
}
// Loose carts nearer the cartridge camera than the selected cart that cover more than 2% of
// its label. Judged at the pan's destination with resting poses, so the choice settles once
// per selection instead of flickering while the camera travels.
std::vector<char> labelOccluders(const SlotTabletop*s,int selected){
    std::vector<char> out(s->items.size(),0);if(selected<0||selected>=(int)s->items.size())return out;
    const ProfileCamera&c=s->panTo;const float aspect=(float)s->width/s->height;
    const float fov=2*std::atan(std::tan(radians(c.fov)/2)*(float)s->layout.width/s->layout.height/aspect);
    const Mat eye=lookAt(c.eye,c.target),projection=perspective(fov,aspect,10,10000);const Vec forward=unit(sub(c.target,c.eye));
    auto home=[&](size_t i){const Media&m=s->media.at(s->items[i].model);Placement p=s->layout.nodes[i+4];p.position.y+=restOffset(s,m);return p.matrix(1/m.units);};
    auto depth=[&](size_t i){const Media&m=s->media.at(s->items[i].model);return dot(sub(transform(home(i),mul(add(m.shell.low,m.shell.high),.5f)),c.eye),forward);};
    const Media&sm=s->media.at(s->items[selected].model);const Mesh&face=sm.label.vertices?sm.label:sm.shell;
    const Outline label=outline(projection,eye,home(selected),face.low,face.high);const float whole=label.size()>2?area(label):0;
    if(whole<=0)return out;const float far=depth(selected);
    for(size_t i=0;i<s->items.size();i++){
        if((int)i==selected||(s->hasResident&&s->items[i].id==s->resident.id)||depth(i)>=far)continue;
        const Media&m=s->media.at(s->items[i].model);const Outline hull=outline(projection,eye,home(i),m.shell.low,m.shell.high);
        out[i]=hull.size()>2&&area(clip(label,hull))>.02f*whole;
    }
    return out;
}
void trimLabels(SlotTabletop*s){std::set<std::string>keep;for(auto&i:s->items)keep.insert(i.face);if(s->hasResident)keep.insert(s->resident.face);for(auto t=s->labelTextures.begin();t!=s->labelTextures.end();)if(!keep.count(t->first)){s->imageLeases.erase(t->first);t=s->labelTextures.erase(t);}else ++t;}
// Slotted's home table: the home layout saved for this TV (or with another TV), else a default
// arrangement. Every placed console loads; frames show those whose room has games.
void loadHome(SlotTabletop*s){
    s->home=true;s->consoleCount=0;
    const std::string path=s->ignoreLayout?std::string():homeProfileFor(s->prepared+"/layouts",s->tv,[](const std::string&p){return exists(p);});
    {HomeProfile early;prefetchPrepared(s,s->tv);prefetchPrepared(s,!path.empty()&&readHomeProfile(path,early)?early.tableAsset:std::string("table"));}
    s->television=prepared(s,s->tv);openStep("home","scene-tv");
    HomeProfile p;
    if(!path.empty()){
        if(!readHomeProfile(path,p))throw std::runtime_error("Invalid home table layout");
        const size_t at=path.rfind("home-")+5;const std::string savedTv=path.substr(at,path.size()-at-6);
        std::fprintf(stderr,"Tabletop: home layout=%s tv=%s requested_tv=%s\n",path.c_str(),savedTv.c_str(),s->tv.c_str());
        if(savedTv!=s->tv){
            // As a console room: same footprint turn, front edge where the authored TV's was.
            Vec low,high;if(!sceneBounds(s->prepared+"/"+savedTv,low,high))throw std::runtime_error("Missing authored TV bounds");
            const Mat m=p.tv.matrix();p.tv.position=add(p.tv.position,sub(transform(m,{0,0,high.z-s->television.high.z}),transform(m,{0,0,0})));
            p.status={{0,s->television.high.y+2,s->television.glassHigh.z-28},{0,0,0}};
        }
    }else{
        std::vector<std::string> models;for(const char*m:{"snes","n64","nes","md","psx","gb","gbc","gba","nds","psp","pico8"})if(exists(consoleMesh(s->root,m,s->gbaChoice)))models.push_back(m);
        p=defaultHomeProfile(models);p.status={{0,s->television.high.y+2,s->television.glassHigh.z-28},{0,0,0}};
    }
    openStep("home","scene-layout");s->table=prepared(s,p.tableAsset);openStep("home","scene-table");
    for(const auto&c:p.consoles){
        if(s->bootstrapHome)break; // the stream prepares complete console meshes after the first room frame
        if(!exists(consoleMesh(s->root,c.model,s->gbaChoice)))continue;
        HomeItem h;h.model=c.model;h.console=loadConsole(s,c.model);h.at=c.at;s->homeItems.push_back(std::move(h));
    }
    if(path.empty()&&!s->bootstrapHome){
        // Unauthored: rows on the table left of the TV, handhelds in front and home consoles behind,
        // each spaced by its own footprint and resting on the table top; then frame them with the TV.
        const float right=p.tv.position.x-(s->television.high.x-s->television.low.x)/2-40,left=std::min(right-300,s->table.low.x*p.tableScale.x+60);
        float x=right,front=640,depth=0;
        auto place=[&](HomeItem&h){
            Vec lo={1e9f,1e9f,1e9f},hi={-1e9f,-1e9f,-1e9f};const Mat m=consoleModel(h.console,Placement{});
            for(int k=0;k<8;k++){const Vec v=transform(m,{k&1?h.console.model.high.x:h.console.model.low.x,k&2?h.console.model.high.y:h.console.model.low.y,k&4?h.console.model.high.z:h.console.model.low.z});lo={std::min(lo.x,v.x),std::min(lo.y,v.y),std::min(lo.z,v.z)};hi={std::max(hi.x,v.x),std::max(hi.y,v.y),std::max(hi.z,v.z)};}
            if(x-(hi.x-lo.x)<left&&x<right){front-=depth+50;x=right;depth=0;}
            h.at={{x-hi.x,-h.console.rest,front-hi.z},{0,0,0}};x-=hi.x-lo.x+45;depth=std::max(depth,hi.z-lo.z);
        };
        for(int handhelds=1;handhelds>=0;handhelds--){
            for(auto&h:s->homeItems){HandheldRegistration hh;if(handheldRegistration(h.model,hh)==bool(handhelds))place(h);}
            if(x<right){front-=depth+50;x=right;depth=0;}
        }
        // Frame every console and the TV, aiming at the middle of the allowed range.
        std::vector<Vec> framing;for(const auto&h:s->homeItems)frameBox(framing,h.console.model.low,h.console.model.high,consoleModel(h.console,h.at));
        frameBox(framing,{s->television.low.x,0,s->television.glassHigh.z},s->television.high,p.tv.matrix());
        const auto camera=frameScene(framing,0,radians(24),(float)s->logicalWidth,(float)s->logicalHeight,true);const Vec forward={0,std::sin(radians(24)),std::cos(radians(24))};
        p.width=s->logicalWidth;p.height=s->logicalHeight;
        p.overview={add(camera.target,mul(forward,camera.distance)),camera.target,2*std::atan(std::tan(radians(20))*1.5f*s->height/s->width)*180/3.14159265f,true};
    }
    // Export the actual suggested arrangement, rather than the earlier
    // placeholder rows. An authored home profile's placements stay unchanged.
    if(path.empty()&&!s->bootstrapHome){p.consoles.clear();for(const auto&h:s->homeItems)p.consoles.push_back({h.model,h.at});}
    s->homeLayout=p;s->authored=true;auto&L=s->layout;
    L.width=p.width;L.height=p.height;L.eye=p.overview.eye;L.target=p.overview.target;L.fov=p.overview.fov;L.cameras[0]=p.overview;
    L.nodes[0]=p.table;L.nodes[1]=p.tv;L.nodes[3]=p.status;L.tableAsset=p.tableAsset;L.tableScale=p.tableScale;
    L.transitionSeconds=p.transitionSeconds;L.browseView=0;L.cartridgeCount=0;L.displays[0].enabled=true;L.displays[1].enabled=false;L.extended=true;
}
void loadScene(SlotTabletop*s){
        if(s->system=="home"){loadHome(s);return;}
        SlotRegistration slot;FrontRegistration front;OpticalRegistration optical;
        HandheldRegistration handheld;if(!slotRegistration(s->system,slot)&&!frontRegistration(s->system,front)&&!opticalRegistration(s->system,optical)&&!handheldRegistration(s->system,handheld))throw std::runtime_error("No tabletop slot registration for "+s->system);
        const char*step=s->system.c_str();
        const auto authored=sceneProfileFor(s->prepared+"/layouts",s->system,s->tv);
        const auto&layoutPath=authored.path;const auto&layoutConsole=authored.system;const auto&layoutTv=authored.tv;
        const bool useLayout=!s->ignoreLayout&&exists(layoutPath);
        // The layout's own table loads once (the plain table used to load first and then be
        // replaced), and a synchronous open starts decoding the table's and TV's textures
        // before the console and media load.
        std::string tableAsset="table";
        if(useLayout){SceneProfile early;if(readSceneProfile(layoutPath,early))tableAsset=early.tableAsset;}
        prefetchPrepared(s,tableAsset);prefetchPrepared(s,s->tv);
        s->television=prepared(s,s->tv);openStep(step,"scene-tv");
        s->consoles[0]=loadConsole(s,s->system);openStep(step,"scene-console");media(s,s->system);openStep(step,"scene-media");
        const std::string regional=regionalConsole(s->system);
        if(!regional.empty()&&exists(s->root+"/consoles/"+regional+"/model.mesh")){
            try{s->consoles[1]=loadConsole(s,regional);s->consoleCount=2;}
            catch(const std::exception&e){std::fprintf(stderr,"Tabletop: %s console unavailable, keeping %s: %s\n",regional.c_str(),s->system.c_str(),e.what());}
            openStep(step,"scene-regional");
        }
        s->table=prepared(s,tableAsset);openStep(step,"scene-table");
        s->layoutBottom=s->consoles[0].rest;
        if(useLayout){
            if(!readSceneProfile(layoutPath,s->layout))throw std::runtime_error("Invalid authored scene layout");s->authored=true;
            std::fprintf(stderr,"Tabletop: authored layout=%s system=%s tv=%s requested_tv=%s\n",layoutPath.c_str(),layoutConsole.c_str(),layoutTv.c_str(),s->tv.c_str());
            if(layoutConsole!=s->system){
                s->layoutBottom=meshLowY(s->root+"/consoles/"+layoutConsole+"/model.mesh")/units(layoutConsole);
                // Its cartridge nodes rest that console's own media on the table.
                s->layoutMediaLow=meshLow(s->root+"/consoles/"+layoutConsole+"/media.mesh",2)/units(layoutConsole);s->layoutMediaKnown=true;
            }
            if(layoutTv!=s->tv){
                // Same footprint turn with the front edge where the authored TV's was; the
                // status cluster sits on this cabinet (the editor's default status pose).
                Vec low,high;if(!sceneBounds(s->prepared+"/"+layoutTv,low,high))throw std::runtime_error("Missing authored TV bounds");
                Placement&tvAt=s->layout.nodes[1];Mat at=tvAt.matrix();
                tvAt.position=add(tvAt.position,sub(transform(at,{0,0,high.z-s->television.high.z}),transform(at,{0,0,0})));
                s->layout.nodes[3]={{0,s->television.high.y+2,s->television.glassHigh.z-28},{0,0,0}};
            }
        }
        if(s->layout.tableAsset!=tableAsset){
            for(auto&m:s->table.parts)s->triangles-=m.count/3;s->table=prepared(s,s->layout.tableAsset);
        }
}

}
#include "SlotRoomWorld.inc"
#include "SlotTabletopStream.inc"

namespace {
// Slotted's home table: table, TV with its live picture, status, and every console whose room has
// games, the highlighted one lifted. f.selected: the frontend's highlighted entry (-1 none).
// f.cameraView: -1/0 overview leaning toward it, 1 leaning toward the TV (channels), 5 the TV screen.
// f.zoom (launch from a 2D list) moves from the screen view into the glass.
void homeFrame(SlotTabletop*s,const SlotTabletopFrame&f,bool painted){
    s->tvPose=s->layout.nodes[1].matrix();
    const float statusScale=std::min(1.f,(s->television.high.x-s->television.low.x)/468.f);
    s->statusPose=product(s->tvPose,s->layout.nodes[3].matrix(statusScale));
    const int view=f.cameraView==1||f.cameraView==5?f.cameraView:0;
    if(f.selected!=s->selected){s->selected=f.selected;s->selectedSince=f.seconds;}
    for(size_t i=0;i<s->homeItems.size();i++){
        auto&h=s->homeItems[i];const int entry=homeEntry(s,i);
        const float goal=entry>=0&&entry==f.selected&&view==0?1.f:0.f,was=h.hover;
        if(s->reducedMotion){h.hover=goal;h.hoverVelocity=0;}else hoverSpring(h.hover,h.hoverVelocity,goal,f.delta);if(was!=goal&&h.hover==goal)s->cacheValid=false;
        const float quiet=f.seconds-s->selectedSince,idle=!s->reducedMotion&&goal>0?ease(quiet-2.5f)*h.hover:0,wave=std::sin(6.2831853f*quiet/3.6f);
        h.lift=std::max(0.f,h.hover*(s->reducedMotion?4:14)+idle*3*wave);Placement at=h.at;at.position.y+=h.lift;h.pose=consoleModel(h.console,at);
    }
    const auto cam=panCamera(s,view,f.selected,f.delta);s->focusView=view;
    const float fov=2*std::atan(std::tan(radians(cam.fov)/2)*(float)s->layout.width/s->layout.height*s->height/s->width);
    Vec eye=cam.eye,target=cam.target;
    if(f.zoom>0){
        const Vec lo=s->television.glassLow,hi=s->television.glassHigh,center=transform(s->tvPose,{(lo.x+hi.x)/2,(lo.y+hi.y)/2,hi.z});
        const Vec normal=unit(sub(transform(s->tvPose,{0,0,1}),transform(s->tvPose,{0,0,0})));
        const float distance=std::max((hi.y-lo.y)/(2*std::tan(fov/2)),(hi.x-lo.x)/(2*std::tan(fov/2)*s->width/s->height))*1.02f;
        const float q=ease(f.zoom);eye=mix(eye,add(center,mul(normal,std::max(170.f,distance))),q);target=mix(target,center,q);
    }
    s->eyeView=lookAt(eye,target);s->projectionFov=fov;s->fitNear=true;
    s->view=product(perspective(fov,(float)s->width/s->height,150,10000),s->eyeView);s->cameraEye=eye;s->cameraTarget=target;s->cameraFov=fov;
    streamCamera(s);
    const Vec lo=s->television.glassLow,hi=s->television.glassHigh;const Vec corners[]={{lo.x,hi.y,hi.z},{hi.x,hi.y,hi.z},{hi.x,lo.y,hi.z},{lo.x,lo.y,hi.z}};
    for(int i=0;i<4;i++)s->display[i]=transform(s->tvPose,corners[i]);
    for(int i=0;i<4;i++)glEnableVertexAttribArray(i);
    s->calls.clear();s->drawFlightGroup=-1;
    for(auto&m:s->table.parts)draw(s,m,product(s->layout.nodes[0].matrix(),scale(s->layout.tableScale.x,s->layout.tableScale.y,s->layout.tableScale.z)));
    for(size_t i=0;i<s->homeItems.size();i++){
        if(homeEntry(s,i)<0)continue;const auto&h=s->homeItems[i];const Console&c=h.console;s->drawFlightGroup=(int)i;
        for(auto&m:c.model.parts)draw(s,m,h.pose,0,false,{{0,0,1,1}},painted);
        draw(s,c.power,h.pose,0,false,{{0,0,1,1}},painted);draw(s,c.led,h.pose);draw(s,c.lid,h.pose,0,false,{{0,0,1,1}},painted);
        for(auto&flap:c.flaps)draw(s,flap.mesh,h.pose,0,false,{{0,0,1,1}},painted);
    }
    s->drawFlightGroup=-3;
    for(auto&m:s->television.parts){
        if(m.glass&&f.screen){s->drawScreen=true;draw(s,m,s->tvPose,f.screen,true,f.screenTopDown?std::array<float,4>{{f.screenLeft,0,f.screenU,f.screenV}}:std::array<float,4>{{f.screenLeft,1,f.screenU,-f.screenV}},false,0,false,screenWindow(s->tv));s->drawScreen=false;}
        else draw(s,m,s->tvPose);
    }
    draw(s,s->status,s->statusPose);
}
}
SlotTabletop* slot_tabletop_open(SDL_Window*w,const char*models,const char*prep,const char*model,const char*tv,bool cel,const char*paint,int logicalWidth,int logicalHeight,bool bootstrapHome){
    if(logicalWidth<320||logicalHeight<240||logicalWidth>1920||logicalHeight>1200)return nullptr;
    openStepsActive=true;openStep(model,nullptr);
    auto*s=new SlotTabletop;s->window=w;s->owner=SDL_GL_GetCurrentContext();s->root=models;s->prepared=prep;s->system=model;s->tv=tv;s->cel=cel;s->paint=paint;s->bootstrapHome=bootstrapHome&&s->system=="home";
    s->ignoreLayout=getenv("SLOT_SCENE_IGNORE_LAYOUT")!=nullptr;
    if(const char*choice=getenv("SLOT_GBA_SP"))s->gbaChoice=choice;
    s->logicalWidth=logicalWidth;s->logicalHeight=logicalHeight;s->width=logicalWidth*2;s->height=logicalHeight*2;
    s->cull=!getenv("SLOT_SCENE_NO_CULL");s->sort=!getenv("SLOT_SCENE_NO_SORT"); // A/B evidence only
    try{
        OpenDecodes parallel; // texture decodes started by this synchronous load
        SDL_GL_SetAttribute(SDL_GL_SHARE_WITH_CURRENT_CONTEXT,1);s->context=SDL_GL_CreateContext(w);SDL_GL_SetAttribute(SDL_GL_SHARE_WITH_CURRENT_CONTEXT,0);if(!s->context)throw std::runtime_error(SDL_GetError());SDL_GL_MakeCurrent(w,s->context);openStep(model,"context");
        s->shading[0]=program(false);s->shading[1]=program(true);openStep(model,"programs");
        // Render at the logical size with 4x on-tile multisampling and mipmapped labels (also
        // non-power-of-two ones), the user's choice (19 Oct) over 2x supersampling: the same
        // look on the device and 15-60% faster per frame. 4x anisotropic filtering is requested
        // too but the RG34XXSP's GLES2 context does not apply it (renders measured identical).
        // Drivers without EXT_multisampled_render_to_texture keep supersampling.
        // SLOT_SCENE_MSAA overrides it: 0 supersampling, 4 plain MSAA, 4m + mipmaps, 4ma + anisotropy.
        const char*extensions=(const char*)glGetString(GL_EXTENSIONS);auto has=[&](const char*name){return extensions&&std::strstr(extensions,name);};
        using TextureMS=void(*)(GLenum,GLenum,GLenum,GLuint,GLint,GLsizei);using StorageMS=void(*)(GLenum,GLsizei,GLenum,GLsizei,GLsizei);TextureMS textureMS=nullptr;StorageMS storageMS=nullptr;
        const char*msaa=getenv("SLOT_SCENE_MSAA")?getenv("SLOT_SCENE_MSAA"):"4ma";
        if(std::atoi(msaa)>1&&has("GL_EXT_multisampled_render_to_texture")){
            textureMS=(TextureMS)SDL_GL_GetProcAddress("glFramebufferTexture2DMultisampleEXT");storageMS=(StorageMS)SDL_GL_GetProcAddress("glRenderbufferStorageMultisampleEXT");
            GLint most=0;glGetIntegerv(0x8D57,&most); // GL_MAX_SAMPLES_EXT
            if(textureMS&&storageMS&&most>1){s->samples=std::min(std::atoi(msaa),(int)most);s->width=logicalWidth;s->height=logicalHeight;s->npotMips=std::strchr(msaa,'m')&&has("GL_OES_texture_npot");
                if(std::strchr(msaa,'a')&&has("GL_EXT_texture_filter_anisotropic")){GLfloat limit=1;glGetFloatv(0x84FF,&limit);s->anisotropy=std::min(4.f,limit);}} // MAX_TEXTURE_MAX_ANISOTROPY
        }
        std::fprintf(stderr,"Tabletop: %dx%d raster, %s\n",s->width,s->height,s->samples?(std::to_string(s->samples)+"x MSAA"+(s->npotMips?", label mipmaps":"")+(s->anisotropy>1?", anisotropic":"")).c_str():"2x supersampling");
        // Composited output the frontend samples (no depth), and the 3D scene buffer it copies.
        s->copy=copyProgram();s->reuse=!(getenv("SLOT_SCENE_CACHE")&&std::strcmp(getenv("SLOT_SCENE_CACHE"),"0")==0); // 0: A/B evidence only
        if(const char*log=getenv("SLOT_SCENE_FRAMELOG"))s->frameLog=std::fopen(log,"a");
        auto colour=[&](GLuint&texture,GLenum filter){glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,s->width,s->height,0,GL_RGBA,GL_UNSIGNED_BYTE,nullptr);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,filter);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,filter);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);};
        colour(s->target,GL_LINEAR);glGenFramebuffers(1,&s->fbo);glBindFramebuffer(GL_FRAMEBUFFER,s->fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,s->target,0);
        if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)throw std::runtime_error("Tabletop output framebuffer incomplete");
        colour(s->sceneTexture,GL_NEAREST);glGenFramebuffers(1,&s->sceneFbo);glBindFramebuffer(GL_FRAMEBUFFER,s->sceneFbo);
        if(s->samples)textureMS(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,s->sceneTexture,0,s->samples);else glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,s->sceneTexture,0);
        glGenRenderbuffers(1,&s->depth);glBindRenderbuffer(GL_RENDERBUFFER,s->depth);GLenum depthFormat=!getenv("SLOT_SCENE_DEPTH16")&&has("GL_OES_depth24")?0x81A6:GL_DEPTH_COMPONENT16;
        if(s->samples)storageMS(GL_RENDERBUFFER,s->samples,depthFormat,s->width,s->height);else glRenderbufferStorage(GL_RENDERBUFFER,depthFormat,s->width,s->height);
        glFramebufferRenderbuffer(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_RENDERBUFFER,s->depth);if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)throw std::runtime_error("Tabletop framebuffer incomplete");
        GLint depthBits=0;glGetRenderbufferParameteriv(GL_RENDERBUFFER,GL_RENDERBUFFER_DEPTH_SIZE,&depthBits);std::fprintf(stderr,"Tabletop: depth buffer %d bits\n",int(depthBits));
        openStep(model,"targets");loadScene(s);openStep(model,"load-scene");openStepsActive=false;
        SDL_GL_MakeCurrent(w,s->owner);return s;
    }catch(const std::exception&e){openStepsActive=false;s->error=e.what();std::fprintf(stderr,"Tabletop: %s\n",e.what());slot_tabletop_close(s);return nullptr;}
}
bool slot_tabletop_items(SlotTabletop*s,const SlotTabletopItem*items,int count){
    if(!s||count<0||count>sceneMaxCartridges||(s->authored&&!s->home&&count>s->layout.cartridgeCount))return false;SDL_GL_MakeCurrent(s->window,s->context);
    struct Labels {Decodes*previous=openDecodes;Labels(){if(!returnLabels.empty())openDecodes=&returnLabels;}~Labels(){openDecodes=previous;drain(returnLabels);}} labels; // first sync after a game
    try{
        std::vector<Item> next;for(int i=0;i<count;i++){
            Item n;n.id=items[i].id?items[i].id:"";n.model=items[i].model?items[i].model:s->system;n.face=items[i].face?items[i].face:"";
            for(auto&old:s->items)if(old.id==n.id){n.hover=old.hover;n.fade=old.fade;}
            if(!s->home)media(s,n.model);if(!n.face.empty()){n.texture=image(s,n.face,true);n.textureLease=s->imageLeases.at(n.face);}next.push_back(n);
        }s->items=std::move(next);trimLabels(s);s->cacheValid=false;SDL_GL_MakeCurrent(s->window,s->owner);return true;
    }catch(const std::exception&e){s->error=e.what();trimLabels(s);SDL_GL_MakeCurrent(s->window,s->owner);return false;}
}
bool slot_tabletop_resident(SlotTabletop*s,const SlotTabletopItem*item,int homeIndex){
    if(!s||homeIndex<0||homeIndex>=s->layout.cartridgeCount)return false;
    SDL_GL_MakeCurrent(s->window,s->context);
    try{
        if(!item){s->hasResident=false;s->resident=Item();}
        else if(!s->hasResident||s->resident.id!=(item->id?item->id:"")){
            Item n;n.id=item->id?item->id:"";n.model=item->model?item->model:s->system;n.face=item->face?item->face:"";
            media(s,n.model);n.texture=image(s,n.face,true);if(!n.face.empty())n.textureLease=s->imageLeases.at(n.face);s->resident=n;s->residentHome=s->layout.nodes[4+homeIndex];
            s->hasResident=true;s->cacheValid=false;
        }
        trimLabels(s);SDL_GL_MakeCurrent(s->window,s->owner);return true;
    }catch(const std::exception&e){s->error=e.what();trimLabels(s);SDL_GL_MakeCurrent(s->window,s->owner);return false;}
}
bool slot_tabletop_status(SlotTabletop*s,int battery,bool charging,bool connected,const char*clock){
    if(!s)return false;std::string time=clock?clock:"--:--";
    if(time.size()!=5||time[2]!=':')return false;for(size_t i=0;i<time.size();i++)if(i!=2&&(time[i]<'0'||time[i]>'9')&&time[i]!='-')return false;
    std::string key=std::to_string(battery)+(charging?"c":"-")+(connected?"w":"-")+time;if(key==s->statusKey)return true;
    SDL_GL_MakeCurrent(s->window,s->context);auto g=statusVoxels(battery,charging,connected,time);deleteMesh(s->status);s->cacheValid=false;
    static_assert(sizeof(Vertex)==sizeof(VoxelVertex),"Shared voxel vertex format");
    glGenBuffers(1,&s->status.vertices);glBindBuffer(GL_ARRAY_BUFFER,s->status.vertices);glBufferData(GL_ARRAY_BUFFER,g.vertices.size()*sizeof(Vertex),g.vertices.data(),GL_STATIC_DRAW);
    glGenBuffers(1,&s->status.indices);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,s->status.indices);glBufferData(GL_ELEMENT_ARRAY_BUFFER,g.indices.size()*2,g.indices.data(),GL_STATIC_DRAW);s->status.count=(unsigned)g.indices.size();
    s->status.vertexLease=lease(s,s->status.vertices,false,g.vertices.size()*sizeof(Vertex));s->status.indexLease=lease(s,s->status.indices,false,g.indices.size()*2);
    s->status.low={1e9f,1e9f,1e9f};s->status.high={-1e9f,-1e9f,-1e9f};for(auto&v:g.vertices)for(int i=0;i<3;i++){((float*)&s->status.low)[i]=std::min(((float*)&s->status.low)[i],v.p[i]);((float*)&s->status.high)[i]=std::max(((float*)&s->status.high)[i],v.p[i]);}
    s->statusKey=key;SDL_GL_MakeCurrent(s->window,s->owner);return true;
}
void slot_tabletop_reduced_motion(SlotTabletop*s,bool enabled){if(s&&s->reducedMotion!=enabled){s->reducedMotion=enabled;s->cacheValid=false;}}
void slot_tabletop_crt(SlotTabletop*s,bool enabled){if(s)s->crt=enabled;}
namespace {
// GPU ordering between the owner's context and this renderer's shared context. Shared
// contexts do not order reads/writes of shared textures implicitly. With EGL_KHR_fence_sync
// and EGL_KHR_wait_sync, a fence in the current context and a GPU-side wait in the next one
// order exactly that work without blocking the CPU (glFinish waited for the whole GPU queue,
// serialising CPU and GPU every frame). SLOT_SCENE_SYNC=finish keeps glFinish (A/B evidence).
struct FenceApi {
    using Display=void*(*)();using Query=const char*(*)(void*,int);using Create=void*(*)(void*,unsigned,const int*);
    using Wait=int(*)(void*,void*,int);using Destroy=unsigned(*)(void*,void*);
    Display display=nullptr;Create create=nullptr;Wait wait=nullptr;Destroy destroy=nullptr;bool ready=false;
};
const FenceApi&fences(){
    static const FenceApi api=[]{
        FenceApi a;const char*mode=getenv("SLOT_SCENE_SYNC");if(mode&&std::strcmp(mode,"finish")==0)return a;
        a.display=(FenceApi::Display)SDL_GL_GetProcAddress("eglGetCurrentDisplay");auto query=(FenceApi::Query)SDL_GL_GetProcAddress("eglQueryString");
        a.create=(FenceApi::Create)SDL_GL_GetProcAddress("eglCreateSyncKHR");a.wait=(FenceApi::Wait)SDL_GL_GetProcAddress("eglWaitSyncKHR");
        a.destroy=(FenceApi::Destroy)SDL_GL_GetProcAddress("eglDestroySyncKHR");
        const char*extensions=a.display&&query?query(a.display(),0x3055/*EGL_EXTENSIONS*/):nullptr;
        a.ready=a.create&&a.wait&&a.destroy&&extensions&&std::strstr(extensions,"EGL_KHR_fence_sync")&&std::strstr(extensions,"EGL_KHR_wait_sync");
        std::fprintf(stderr,"Tabletop: context hand-off by %s\n",a.ready?"EGL fence + GPU wait":"glFinish");
        return a;
    }();
    return api;
}
// Makes `next` current after the work submitted so far in the current context; that work
// completes on the GPU before anything `next` submits afterwards.
void handOff(SlotTabletop*s,SDL_GLContext next){
    const FenceApi&f=fences();void*display=f.ready?f.display():nullptr;
    void*sync=display?f.create(display,0x30F9/*EGL_SYNC_FENCE_KHR*/,nullptr):nullptr;
    if(!sync){glFinish();SDL_GL_MakeCurrent(s->window,next);return;}
    glFlush();SDL_GL_MakeCurrent(s->window,next);
    if(f.wait(display,sync,0)!=1)glFinish();f.destroy(display,sync);
}
}
unsigned slot_tabletop_frame(SlotTabletop*s,const SlotTabletopFrame&input){
    if(!s)return 0;
    // The owner just wrote the TV picture and may still be sampling our last
    // output: handOff orders that work before this context reads or overwrites
    // the shared textures; the matching hand-off back is below.
    const Uint64 waitStarted=SDL_GetPerformanceCounter();
    const auto f=streamFrame(s,input);const Uint64 started=SDL_GetPerformanceCounter();
    handOff(s,s->context);const Uint64 waited=SDL_GetPerformanceCounter();if(s->stream)warmDestination(s,*s->stream);glDisable(GL_SCISSOR_TEST);glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LEQUAL);glDepthMask(GL_TRUE);glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glActiveTexture(GL_TEXTURE0);
    s->pool->retired->drain();const long renderedBefore=s->rendered;const long reusedBefore=s->reused;const long partialsBefore=s->partials;
    const std::map<std::string,Vec>paints={{"black",{.11f,.12f,.14f}},{"white",{.86f,.85f,.81f}},{"red",{.7f,.15f,.13f}},{"blue",{.15f,.34f,.68f}},{"purple",{.43f,.22f,.59f}},{"green",{.2f,.5f,.3f}},{"yellow",{.82f,.65f,.12f}}};auto chosen=paints.find(s->paint);s->paintColor=chosen==paints.end()?Vec{1,1,1}:chosen->second;
    if(s->home)homeFrame(s,f,chosen!=paints.end());
    else{
    if(!s->authored){
        s->layout.nodes[1]={{340,0,440},{0,-12,0}};s->layout.nodes[2]={{-220,-s->consoles[0].rest,40},{0,18,0}};
        s->layout.nodes[3]={{0,s->television.high.y+2,s->television.glassHigh.z-28},{0,0,0}};
        for(int i=0;i<sceneMaxCartridges;i++){auto&m=s->media.at(i<(int)s->items.size()?s->items[i].model:s->system);Vec at=tableCartridge(i);at.y=m.shell.high.z/m.units;s->layout.nodes[i+4]={at,{-90,(i%3-1)*3.f,0}};}
    }
    const int active=activeConsole(s);const Console&console=s->consoles[active];const Placement consoleAt=consolePlacement(s,active);
    s->consolePose=consoleModel(console,consoleAt);s->tvPose=s->layout.nodes[1].matrix();
    float statusScale=std::min(1.f,(s->television.high.x-s->television.low.x)/468.f);
    s->statusPose=product(s->tvPose,s->layout.nodes[3].matrix(statusScale));
    std::vector<Vec> framing;
    // Frame the authored console so a region swap never moves the default camera.
    frameBox(framing,s->consoles[0].model.low,s->consoles[0].model.high,consoleModel(s->consoles[0],s->layout.nodes[2]));
    frameBox(framing,{s->television.low.x,0,s->television.glassHigh.z},{s->television.high.x,s->television.high.y,s->television.high.z},s->tvPose);
    // Reserve the widest charging / 100% / 88:88 cluster, so value changes cannot move the camera.
    frameBox(framing,{-200,0,0},{200,26,5},s->statusPose);
    for(int i=0;i<sceneMaxCartridges;i++){auto&m=s->media.at(i<(int)s->items.size()?s->items[i].model:s->system);Vec at=tableCartridge(i);at.y=m.shell.high.z/m.units+4;frameBox(framing,m.shell.low,m.shell.high,pose(at,radians((i%3-1)*3.f),-radians(90),1/m.units));}
    if(s->authored){
        if(!s->orbitReady){orbitLimits(s,consoleModel(s->consoles[0],s->layout.nodes[2]));s->orbitReady=true;}
        // Requested +/-8 degrees map onto each side's measured permitted range.
        float request=std::max(-8.f,std::min(8.f,f.yaw)),yaw=request*s->orbitLimit[request>0]/8;
        int view=f.cameraView<0?(f.inspection>0?4:s->layout.browseView):f.cameraView==5?5:std::max(0,std::min(4,f.cameraView));
        const bool residentSelected=s->hasResident&&f.selected>=0&&f.selected<(int)s->items.size()&&s->items[f.selected].id==s->resident.id;
        // Launch (user, 19 Oct): pan to the handheld's console view and zoom into its screen, or
        // to the TV view and into the glass. The screen must face that console camera (the PSP
        // lies face-down; PICO-8 has none), otherwise the TV is used. DS: the top screen.
        const bool launch=s->hasResident&&(f.lid>=0||f.power>0||f.zoom>0);int screen=-1;Vec corner[4];
        if(!s->world&&launch&&!console.lcdCorners.empty()){
            for(int k=0;k<4;k++)corner[k]=transform(s->consolePose,console.lcdCorners[0][k]);
            Vec middle=mul(add(add(corner[0],corner[1]),add(corner[2],corner[3])),.25f),front=cross(sub(corner[1],corner[0]),sub(corner[0],corner[3]));
            if(dot(front,sub(viewCamera(s,3,f.selected).eye,middle))>0)screen=0;
        }
        if(launch)view=screen>=0?3:1;
        // A seated game that is selected pans out to the overview after slotting; while it moves
        // (or with a hand-picked cartridge view) its console is framed instead of the empty home.
        else if(residentSelected&&f.automatic&&f.phase==0)view=0;
        else if(view==2&&residentSelected)view=3;
        auto cam=panCamera(s,view,f.selected,f.delta);s->focusView=view;
        float fov=2*std::atan(std::tan(radians(cam.fov)/2)*(float)s->layout.width/s->layout.height*s->height/s->width);
        Vec eye=view==0&&s->panTime>=s->panSeconds?orbitEye(s,yaw,f.elevation):cam.eye,target=cam.target,up={0,1,0};
        if(f.zoom>0&&screen>=0){
            // The registered screen fills the view, upright in its own frame.
            Vec across=sub(corner[1],corner[0]),rise=sub(corner[0],corner[3]),middle=mul(add(add(corner[0],corner[1]),add(corner[2],corner[3])),.25f);
            float w=std::sqrt(dot(across,across)),h=std::sqrt(dot(rise,rise)),distance=std::max(h/(2*std::tan(fov/2)),w/(2*std::tan(fov/2)*s->width/s->height))*1.02f;
            float q=ease(f.zoom);eye=mix(eye,add(middle,mul(unit(cross(across,rise)),std::max(30.f,distance))),q);target=mix(target,middle,q);up=unit(mix(up,unit(rise),q));
        }else if(f.zoom>0){
            Vec lo=s->television.glassLow,hi=s->television.glassHigh,center=transform(s->tvPose,{(lo.x+hi.x)/2,(lo.y+hi.y)/2,hi.z});
            Vec normal=unit(sub(transform(s->tvPose,{0,0,1}),transform(s->tvPose,{0,0,0})));
            float distance=std::max((hi.y-lo.y)/(2*std::tan(fov/2)),(hi.x-lo.x)/(2*std::tan(fov/2)*s->width/s->height))*1.02f;
            float q=ease(f.zoom);eye=mix(eye,add(center,mul(normal,std::max(170.f,distance))),q);target=mix(target,center,q);
        }
        s->eyeView=lookAt(eye,target,up);s->projectionFov=fov;s->fitNear=true;
        s->view=product(perspective(fov,(float)s->width/s->height,150,10000),s->eyeView);s->cameraEye=eye;s->cameraTarget=target;s->cameraFov=fov;
    }else{
        s->fitNear=false;s->focusView=-1;
        auto camera=frameScene(framing,radians(std::max(-8.f,std::min(8.f,f.yaw))),radians(24+std::max(-4.f,std::min(4.f,f.elevation))),(float)s->logicalWidth,(float)s->logicalHeight);s->view=camera.matrix;
        Vec forward={std::sin(radians(f.yaw))*std::cos(radians(24+f.elevation)),std::sin(radians(24+f.elevation)),std::cos(radians(f.yaw))*std::cos(radians(24+f.elevation))};
        s->layout.eye=add(camera.target,mul(forward,camera.distance));s->layout.target=camera.target;s->layout.width=s->logicalWidth;s->layout.height=s->logicalHeight;s->layout.fov=2*std::atan(std::tan(radians(20))*1.5f*s->height/s->width)*180/3.14159265358979323846f;
        s->cameraEye=s->layout.eye;s->cameraTarget=s->layout.target;s->cameraFov=radians(s->layout.fov);
    }
    streamCamera(s);
    Vec lo=s->television.glassLow,hi=s->television.glassHigh;Vec corners[]={{lo.x,hi.y,hi.z},{hi.x,hi.y,hi.z},{hi.x,lo.y,hi.z},{lo.x,lo.y,hi.z}};for(int i=0;i<4;i++)s->display[i]=transform(s->tvPose,corners[i]);
    for(int i=0;i<4;i++)glEnableVertexAttribArray(i);
    s->calls.clear();s->drawFlightGroup=-1;for(auto&m:s->table.parts)draw(s,m,product(s->layout.nodes[0].matrix(),scale(s->layout.tableScale.x,s->layout.tableScale.y,s->layout.tableScale.z)));
    SlotRegistration slot;slotRegistration(console.name,slot);
    FrontRegistration front;const bool frontLoader=frontRegistration(console.name,front);
    // The moving/loaded cart's pose comes first: the N64 dust flaps open against it.
    OpticalRegistration optical;const bool opticalConsole=opticalRegistration(console.name,optical);
    HandheldRegistration hh;const bool handheld=handheldRegistration(console.name,hh);
    float mediaBottom=1e9f,mediaHalf=0,lidOpening=0;
    if(s->hasResident){
        auto&item=s->resident;auto&m=s->media.at(item.model);float height=(m.shell.high.y-m.shell.low.y)/m.units;
        float t=f.phase==1?f.progress:f.phase==2?1-f.progress:1;
        float clearance=consoleAt.position.y+console.top+(opticalConsole?optical.thickness:height)+24;
        Placement home=s->residentHome;home.position.y+=restOffset(s,m);float tilt=0;for(auto&loose:s->items)if(loose.id==item.id){home.position.y+=loose.lift;tilt=loose.tilt;}
        if(frontLoader){
            lidOpening=frontLidOpening(t);Vec size=mul(sub(m.shell.high,m.shell.low),1/m.units);
            item.pose=product(frontLoaderPath(home,consoleAt,front,mul(add(m.shell.low,m.shell.high),.5f/m.units),size.y,size.z,t),scale(1/m.units,1/m.units,1/m.units));
        }else if(opticalConsole){
            // The disc crosses in front of the open lid and drops flat onto the spindle.
            lidOpening=opticalLidOpening(f.phase,t);
            item.pose=product(cartridgePath(home,consoleAt,optical.centre,clearance,t,discOrientation()),scale(1/m.units,1/m.units,1/m.units));
        }else if(handheld){
            // Cart/card/UMD slides in along its registered entry; the PSP cover opens and closes over it.
            Mat frame=consoleFrame(console,consoleAt);if(hh.cover)lidOpening=pspCoverOpening(t);
            item.pose=product(hh.cover?pspPath(home,frame,hh,clearance,t):slidePath(home,frame,hh.seat,hh.media,hh.out,hh.travel,clearance,t),scale(1/m.units,1/m.units,1/m.units));
        }else item.pose=product(cartridgePath(home,consoleAt,cartridgeSeat(slot,height),clearance,t),scale(1/m.units,1/m.units,1/m.units));
        // Carry the selection tilt off (and back onto) the table so the hand-off never pops.
        item.pose=tiltToward(item.pose,m.shell.low,m.shell.high,s->layout.eye,tilt*hoverTiltFactor(home.matrix())*(1-ease(t/.25f)));
        Vec lo=m.shell.low,hi=m.shell.high;
        for(int k=0;k<8;k++)mediaBottom=std::min(mediaBottom,intoFrame(s->consolePose,transform(item.pose,{k&1?hi.x:lo.x,k&2?hi.y:lo.y,k&4?hi.z:lo.z})).y);
        mediaHalf=(hi.z-lo.z)/2/m.units*consoleUnits(console.name);
    }
    s->drawFlightGroup=-2;
    for(auto&m:console.model.parts)draw(s,m,s->consolePose,0,false,{{0,0,1,1}},chosen!=paints.end());
    draw(s,console.power,product(s->consolePose,translate(mul(powerTravel(console.name),consoleUnits(console.name)*ease(f.power)))),0,false,{{0,0,1,1}},chosen!=paints.end());
    // The power indicator glows (unlit) once the console is switched on.
    draw(s,console.led,s->consolePose,0,f.power>.5f);
    if(s->layout.displays[1].enabled&&f.handheldScreen){s->drawScreen=true;for(auto&m:console.lcds)draw(s,m,s->consolePose,f.handheldScreen,true,f.screenTopDown?std::array<float,4>{{0,0,f.screenU,f.screenV}}:std::array<float,4>{{0,1,f.screenU,-f.screenV}},false,2);s->drawScreen=false;}
    if(console.lid.vertices){
        // Front-loader, optical or PSP UMD lid turns about its hinge (console units). The
        // presentation closes an optical lid explicitly before launch (f.lid).
        if(opticalConsole&&f.lid>=0)lidOpening=f.lid;
        Vec hinge=frontLoader?Vec{0,front.hingeY,front.hingeZ}:opticalConsole?Vec{0,optical.hingeY,optical.hingeZ}:hh.hinge;hinge=mul(hinge,consoleUnits(console.name));
        float open=(frontLoader?front.lid:opticalConsole?optical.lid:hh.coverOpen)*lidOpening;
        draw(s,console.lid,product(s->consolePose,product(translate(hinge),product(axisRotation({1,0,0},-open),translate(mul(hinge,-1))))),0,false,{{0,0,1,1}},chosen!=paints.end());
    }
    s->flapCount=0;
    for(auto&flap:console.flaps){
        float angle=s->hasResident?flapAngle(flap.section,console.flapSlot,console.flapClearance,mediaBottom,mediaHalf):0;
        if(s->flapCount<4)s->flapAngles[s->flapCount++]=angle;
        Vec hinge={0,flap.section.hinge[0],flap.section.hinge[1]};
        draw(s,flap.mesh,product(s->consolePose,product(translate(hinge),product(axisRotation({1,0,0},angle),translate(mul(hinge,-1))))),0,false,{{0,0,1,1}},chosen!=paints.end());
    }
    s->drawFlightGroup=-3;
    for(auto&m:s->television.parts){
        if(m.glass&&f.screen&&s->layout.displays[0].enabled)
            {s->drawScreen=true;draw(s,m,s->tvPose,f.screen,true,f.screenTopDown?std::array<float,4>{{f.screenLeft,0,f.screenU,f.screenV}}:std::array<float,4>{{f.screenLeft,1,f.screenU,-f.screenV}},false,0,false,screenWindow(s->tv));s->drawScreen=false;}
        else draw(s,m,s->tvPose);
    }
    draw(s,s->status,s->statusPose);
    if(s->hasResident){
        s->drawFlightGroup=-2;auto&item=s->resident;auto&m=s->media.at(item.model);
        draw(s,m.shell,item.pose);drawLabel(s,m,item.pose,item.texture);
    }
    if(f.selected!=s->selected){s->selected=f.selected;s->selectedSince=f.seconds;}
    // In the close cartridge view, carts in front of the selected one would hide part of its
    // label; they fade to a quarter (~0.2 s) and return when the camera moves on.
    const auto occluding=s->focusView==2?labelOccluders(s,f.selected):std::vector<char>(s->items.size(),0);
    for(size_t i=0;i<s->items.size();i++){
        auto&item=s->items[i];auto&m=s->media.at(item.model);float goal=(int)i==f.selected?1:0;const float wasHover=item.hover;if(s->reducedMotion){item.hover=goal;item.hoverVelocity=0;}else hoverSpring(item.hover,item.hoverVelocity,goal,f.delta);if(wasHover!=goal&&item.hover==goal)s->cacheValid=false;
        const float clear=occluding[i]&&(int)i!=f.loaded?.25f:1;item.fade+=(clear-item.fade)*(1-std::exp(-std::min(.1f,std::max(0.f,f.delta))*14));
        if(std::abs(clear-item.fade)<.02f)item.fade=clear; // settles exactly (opaque again at 1)
        // Selected: ~3 mm rise and a 12 degree tilt toward the viewer; after a quiet
        // moment, a much smaller breathing motion (TABLETOP_SCENE_PLAN section 5).
        float quiet=f.seconds-s->selectedSince,idle=!s->reducedMotion&&(int)i==f.selected?ease(quiet-2.5f)*item.hover:0,wave=std::sin(6.2831853f*quiet/3.6f);
        item.lift=std::max(0.f,item.hover*(s->reducedMotion?.6f:3)+idle*.8f*wave);item.tilt=radians(s->reducedMotion?2:12)*ease(item.hover)+radians(1.5f)*idle*wave;
        if(s->hasResident&&item.id==s->resident.id){item.pose=s->resident.pose;continue;}
        Placement placement=s->layout.nodes[i+4];placement.position.y+=item.lift+restOffset(s,m);Mat model=cartridgeHoverTilt(placement.matrix(1/m.units),m.shell.low,m.shell.high,s->layout.eye,item.tilt);
        if((int)i==f.selected&&f.inspection>0)model=inspectModel(s,m,model,f);
        if((int)i==f.loaded){
            float height=(m.shell.high.y-m.shell.low.y)/m.units;
            if(frontLoader){Vec size=mul(sub(m.shell.high,m.shell.low),1/m.units);model=product(frontLoaderPath(placement,consoleAt,front,mul(add(m.shell.low,m.shell.high),.5f/m.units),size.y,size.z,1),scale(1/m.units,1/m.units,1/m.units));}
            else if(opticalConsole)model=product(product(product(consoleAt.matrix(),translate(optical.centre)),discOrientation()),scale(1/m.units,1/m.units,1/m.units));
            else if(handheld)model=product(slidePath(placement,consoleFrame(console,consoleAt),hh.seat,hh.media,hh.out,hh.travel,0,1),scale(1/m.units,1/m.units,1/m.units));
            else model=product(product(consoleAt.matrix(),translate(cartridgeSeat(slot,height))),scale(1/m.units,1/m.units,1/m.units));
        }
        item.pose=model;s->drawFlightGroup=i;s->drawFade=item.fade;draw(s,m.shell,model);drawLabel(s,m,model,item.texture);s->drawFade=1;
    }
    }
    streamDraws(s);submit(s);const Uint64 submitted=SDL_GetPerformanceCounter();GLenum error=glGetError();
    if(s->stream){std::lock_guard<std::mutex> lock(s->stream->mutex);if(!s->stream->motion&&s->reused>reusedBefore)s->stream->ticket=true;s->stream->wake.notify_all();}if(error)s->error="GLES scene error "+std::to_string(error);
    if(s->frameLog){
        // SLOT_SCENE_FRAMELOG: every ~2 s, the frontend's frame rate (from its frame deltas), this
        // renderer's time per frame (CPU + GPU, glFinish) and how many frames re-rendered the scene.
        s->logFrontend+=std::max(0.f,f.delta);s->logScene+=1000.0*(SDL_GetPerformanceCounter()-started)/SDL_GetPerformanceFrequency();s->logPage+=f.pageMs;s->logBind+=f.videoBindMs;for(int k=0;k<5;k++)s->logSteps[k]+=f.pageSteps[k];s->logFrames++;s->logRendered+=s->rendered>renderedBefore;s->logPartials+=s->partials>partialsBefore;
        if(s->logFrontend>=2){std::fprintf(s->frameLog,"t=%.1f frontend_fps=%.1f frontend_ms=%.2f scene_ms=%.2f page_ms=%.2f video_fetch_ms=%.2f rendered=%d/%d partial=%d view=%d\n",s->logStart+=s->logFrontend,s->logFrames/s->logFrontend,1000*s->logFrontend/s->logFrames,s->logScene/s->logFrames,s->logPage/s->logFrames,s->logBind/s->logFrames,s->logRendered,s->logFrames,s->logPartials,s->focusView);if(gpuTimer().ready){auto avg=[&](int k){return s->logGpuCount[k]?s->logGpu[k]/s->logGpuCount[k]:0.0;};std::fprintf(s->frameLog,"   gpu: full scene %.2f ms x%d, partial scene %.2f ms x%d, composite %.2f ms x%d\n",avg(0),s->logGpuCount[0],avg(1),s->logGpuCount[1],avg(2),s->logGpuCount[2]);for(int k=0;k<3;k++){s->logGpu[k]=0;s->logGpuCount[k]=0;}}std::fprintf(s->frameLog,"   page redraws: both %.0f tv %.0f lcd %.0f, video only: tv %.0f lcd %.0f\n",s->logSteps[0],s->logSteps[1],s->logSteps[2],s->logSteps[3],s->logSteps[4]);for(auto&v:s->logSteps)v=0;std::fflush(s->frameLog);s->logFrontend=s->logScene=s->logPage=s->logBind=0;s->logFrames=s->logRendered=s->logPartials=0;}
    }
    const Uint64 handing=SDL_GetPerformanceCounter();handOff(s,s->owner);
    {const double tick=1000.0/SDL_GetPerformanceFrequency();const Uint64 finished=SDL_GetPerformanceCounter();
     s->frameTiming[0]=float((waited-started)*tick);s->frameTiming[1]=float(((started-waitStarted)+(submitted-waited)+(handing-submitted))*tick);s->frameTiming[2]=float((finished-handing)*tick);}
    return error?0:s->target;
}
bool slot_tabletop_display(SlotTabletop*s,float xy[8]){if(!s)return false;for(int i=0;i<4;i++){Vec p=transform(s->view,s->display[i]);xy[2*i]=(p.x+1)*s->logicalWidth/2;xy[2*i+1]=(1-p.y)*s->logicalHeight/2;}return true;}
bool slot_tabletop_bounds(SlotTabletop*s,int item,float xy[4]){
    if(!s||item< -2||item>=(int)s->items.size())return false;
    Vec low,high;Mat model;
    if(item==-2){low={s->television.low.x,0,s->television.glassHigh.z};high=s->television.high;model=s->tvPose;}
    else {const Mesh&m=item<0?s->status:s->media.at(s->items[item].model).shell;if(!m.vertices)return false;low=m.low;high=m.high;model=item<0?s->statusPose:s->items[item].pose;}
    if(s->world)model=product(s->world->root,model);
    Mat vp=product(s->view,model);float left=1e9f,top=1e9f,right=-1e9f,bottom=-1e9f;
    for(int i=0;i<8;i++){Vec p=transform(vp,{i&1?high.x:low.x,i&2?high.y:low.y,i&4?high.z:low.z});float x=(p.x+1)*s->logicalWidth/2,y=(1-p.y)*s->logicalHeight/2;left=std::min(left,x);top=std::min(top,y);right=std::max(right,x);bottom=std::max(bottom,y);}
    xy[0]=left;xy[1]=top;xy[2]=right-left;xy[3]=bottom-top;return true;
}
int slot_tabletop_focus_points(SlotTabletop*s,SlotTabletopFocus*out,int capacity,int referenceView,bool emptySlots){
    if(!s||!out||capacity<=0||!s->authored||!slot_tabletop_ready(s)||referenceView<0||referenceView>3)return 0;
    const auto camera=viewCamera(s,referenceView,-1);
    const float fov=2*std::atan(std::tan(radians(camera.fov)/2)*float(s->layout.width)/s->layout.height*s->logicalHeight/s->logicalWidth);
    const auto vp=product(perspective(fov,float(s->logicalWidth)/s->logicalHeight,10,10000),lookAt(camera.eye,camera.target));
    int count=0;
    auto append=[&](int item,Vec at){
        slot_navigation::Point point;
        if(count<capacity&&slot_navigation::projectAnchor(vp,at,s->logicalWidth,s->logicalHeight,item,point))
            out[count++]={item,point.x,point.y};
    };
    if(s->home){
        for(size_t i=0;i<s->homeItems.size();i++){
            const int entry=homeEntry(s,i);if(entry<0)continue;
            const auto&h=s->homeItems[i];
            append(entry,transform(consoleModel(h.console,h.at),mul(add(h.console.model.low,h.console.model.high),.5f)));
        }
    }else{
        const size_t slots=emptySlots?size_t(s->layout.cartridgeCount):std::min(s->items.size(),size_t(s->layout.cartridgeCount));
        for(size_t i=0;i<slots;i++){
            const auto&m=s->media.at(i<s->items.size()?s->items[i].model:s->system);Placement at=s->layout.nodes[4+i];
            at.position.y+=restOffset(s,m);
            append(int(i),transform(at.matrix(1/m.units),mul(add(m.shell.low,m.shell.high),.5f)));
        }
    }
    const auto tv=s->layout.nodes[1].matrix();
    append(-2,transform(tv,{(s->television.low.x+s->television.high.x)/2,
                           (s->television.low.y+s->television.high.y)/2,s->television.glassHigh.z}));
    return count;
}
int slot_tabletop_flaps(SlotTabletop*s,float degrees[4]){if(!s)return 0;for(int i=0;i<s->flapCount;i++)degrees[i]=s->flapAngles[i]*180/3.14159265f;return s->flapCount;}
bool slot_tabletop_orbit_limits(SlotTabletop*s,float limits[2]){if(!s||!s->authored||!s->orbitReady)return false;limits[0]=s->orbitLimit[0];limits[1]=s->orbitLimit[1];return true;}
float slot_tabletop_near(SlotTabletop*s){return s?s->nearPlane:0;}
bool slot_tabletop_cache(SlotTabletop*s,long counts[2]){if(!s)return false;counts[0]=s->rendered;counts[1]=s->reused;return true;}
bool slot_tabletop_frame_timing(SlotTabletop*s,float ms[3]){if(!s)return false;for(int i=0;i<3;i++)ms[i]=s->frameTiming[i];return true;}
void slot_tabletop_remember_assets(SlotTabletop*s){
    if(!s)return;
    returnAssets={s->prepared,s->layout.tableAsset.empty()?std::string("table"):s->layout.tableAsset,s->tv,{}};
    for(const auto&item:s->items)if(!item.face.empty())returnAssets.labels.push_back(item.face);
    if(s->hasResident&&!s->resident.face.empty())returnAssets.labels.push_back(s->resident.face);
}
void slot_tabletop_predecode_remembered(){
    drain(returnDecodes);drain(returnLabels);if(returnAssets.prepared.empty())return;
    for(const auto&key:{returnAssets.table,returnAssets.tv})
        for(const auto&path:preparedTextures(returnAssets.prepared+"/"+key))
            if(!returnDecodes.count(path))returnDecodes[path]=std::async(std::launch::async,decodeImage,path);
    for(const auto&path:returnAssets.labels)
        if(!returnLabels.count(path))returnLabels[path]=std::async(std::launch::async,decodeImage,path);
}
bool slot_tabletop_raster(SlotTabletop*s,int size[3]){if(!s)return false;size[0]=s->width;size[1]=s->height;size[2]=s->samples;return true;}
bool slot_tabletop_draws(SlotTabletop*s,int counts[2]){if(!s)return false;counts[0]=s->drawn;counts[1]=s->culled;return true;}
int slot_tabletop_label_count(SlotTabletop*s){return s?(int)s->labelTextures.size():0;}
int slot_tabletop_triangles(SlotTabletop*s){return s?s->triangles:0;}
bool slot_tabletop_export_layout(SlotTabletop*s,const char*path){return s&&path&&(s->home?writeHomeProfile(path,s->homeLayout):writeSceneProfile(path,s->layout));}
const SceneDisplay* slot_tabletop_display_settings(SlotTabletop*s,int display){return s&&display>=0&&display<2?&s->layout.displays[display]:nullptr;}
int slot_tabletop_default_view(SlotTabletop*s){return s?s->layout.browseView:0;}
float slot_tabletop_pan_seconds(SlotTabletop*s){return s?s->layout.transitionSeconds:.8f;}
bool slot_tabletop_camera(SlotTabletop*s,float values[7]){if(!s)return false;values[0]=s->cameraEye.x;values[1]=s->cameraEye.y;values[2]=s->cameraEye.z;values[3]=s->cameraTarget.x;values[4]=s->cameraTarget.y;values[5]=s->cameraTarget.z;values[6]=s->cameraFov*180/3.14159265358979323846f;return true;}
const char*slot_tabletop_error(SlotTabletop*s){return s?s->error.c_str():"Tabletop unavailable";}
void slot_tabletop_close(SlotTabletop*s){
    if(!s)return;
    if(s->owner&&SDL_GL_GetCurrentContext()==s->owner)glFinish();
    // stopStream is defined by the streaming implementation; it joins only on
    // real shutdown/game handoff, never on a normal system change.
    stopStream(s);
    if(s->context){
        SDL_GL_MakeCurrent(s->window,s->context);
        s->cached.clear();s->calls.clear();s->items.clear();s->resident={};
        for(auto&c:s->consoles)c={};s->table={};s->television={};s->media.clear();s->status={};
        s->world.reset();s->imageLeases.clear();s->pool->rooms.clear();s->pool->retired->drain();
        if(s->depth)glDeleteRenderbuffers(1,&s->depth);if(s->fbo)glDeleteFramebuffers(1,&s->fbo);
        if(s->target)glDeleteTextures(1,&s->target);if(s->sceneFbo)glDeleteFramebuffers(1,&s->sceneFbo);if(s->sceneTexture)glDeleteTextures(1,&s->sceneTexture);
        for(auto&p:s->shading)if(p.program)glDeleteProgram(p.program);if(s->copy.program)glDeleteProgram(s->copy.program);
        if(s->warmFbo)glDeleteFramebuffers(1,&s->warmFbo);if(s->warmColour)glDeleteTextures(1,&s->warmColour);
        if(s->frameLog)std::fclose(s->frameLog);glFinish();
        SDL_GL_MakeCurrent(s->window,s->owner);SDL_GL_DeleteContext(s->context);
    }delete s;
}
