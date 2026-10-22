// Private renderer loading/flight study. Never links into the live frontend (MIT).
#include <SDL.h>
#define SDL_USE_BUILTIN_OPENGL_DEFINITIONS 1
#include <SDL_opengles2.h>
#include <algorithm>
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
extern "C" SDL_Surface* IMG_Load(const char*);
namespace measurement {
double now(){return 1000.0*SDL_GetPerformanceCounter()/SDL_GetPerformanceFrequency();}
double png=0,texture=0,mips=0,buffers=0,contexts=0,compile=0;
size_t gpuBytes=0,pixels=0;int images=0,uploads=0;
extern "C" SDL_Surface* load(const char*p){double t=now();auto*r=IMG_Load(p);png+=now()-t;images++;return r;}
SDL_GLContext context(SDL_Window*w){double t=now();auto*r=SDL_GL_CreateContext(w);contexts+=now()-t;return r;}
void tex(GLenum a,GLint b,GLint c,GLsizei w,GLsizei h,GLint d,GLenum e,GLenum f,const void*p){double t=now();glTexImage2D(a,b,c,w,h,d,e,f,p);texture+=now()-t;gpuBytes+=(size_t)w*h*4;if(p){pixels+=(size_t)w*h;uploads++;}}
void mip(GLenum a){double t=now();glGenerateMipmap(a);mips+=now()-t;}
void buffer(GLenum a,GLsizeiptr b,const void*c,GLenum d){double t=now();glBufferData(a,b,c,d);buffers+=now()-t;gpuBytes+=b;}
void shader(GLuint a){double t=now();glCompileShader(a);compile+=now()-t;}
void reset(){png=texture=mips=buffers=contexts=compile=0;gpuBytes=pixels=0;images=uploads=0;}
}
#define IMG_Load measurement::load
#define SDL_GL_CreateContext measurement::context
#define glTexImage2D measurement::tex
#define glGenerateMipmap measurement::mip
#define glBufferData measurement::buffer
#define glCompileShader measurement::shader
// This private executable observes the exact native implementation, including
// validation, UV sidecars, regional models, MSAA, and the local NeilVFX GBA SP.
#include "SlotTabletop.cpp"
#undef IMG_Load
#undef SDL_GL_CreateContext
#undef glTexImage2D
#undef glGenerateMipmap
#undef glBufferData
#undef glCompileShader
#include "SlotSystemFlight.h"

namespace {
long memory(const std::string&name){std::ifstream f("/proc/self/status");std::string line;while(std::getline(f,line))if(line.find(name+":")==0){std::istringstream in(line.substr(name.size()+1));long k=0;in>>k;return k;}return -1;}
struct Request {std::string system,tv;std::vector<std::string>faces;};
bool capture(SlotTabletop*s,GLuint texture,const std::string&path){
    GLuint fbo;glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)return false;
    SDL_Surface*im=SDL_CreateRGBSurfaceWithFormat(0,s->width,s->height,32,SDL_PIXELFORMAT_RGBA32);glReadPixels(0,0,s->width,s->height,GL_RGBA,GL_UNSIGNED_BYTE,im->pixels);
    std::vector<unsigned char> row(im->pitch);for(int y=0;y<im->h/2;y++){auto*a=(unsigned char*)im->pixels+y*im->pitch,*b=(unsigned char*)im->pixels+(im->h-1-y)*im->pitch;std::memcpy(row.data(),a,im->pitch);std::memcpy(a,b,im->pitch);std::memcpy(b,row.data(),im->pitch);}
    bool ok=SDL_SaveBMP(im,path.c_str())==0;SDL_FreeSurface(im);glBindFramebuffer(GL_FRAMEBUFFER,0);glDeleteFramebuffers(1,&fbo);return ok;
}
void flight(SlotTabletop*s,const std::vector<DrawCall>&home,float off,bool entering,bool tv){
    // Research only: adjust draw matrices after they have been queued, then use
    // the normal shared-depth submission. The source profile stays byte-exact.
    s->calls=home; // submit() consumes its queue; retain the original home draws.
    const Mat motion=systemFlight(s->cameraEye,s->cameraTarget,s->cameraFov,(float)s->width/s->height,300,off,entering);
    for(auto&call:s->calls){
        bool environment=false;
        for(auto&m:s->table.parts)environment|=call.mesh==&m;
        if(!tv){for(auto&m:s->television.parts)environment|=call.mesh==&m;environment|=call.mesh==&s->status;}
        if(!environment)call.model=product(motion,call.model);
    }
    SDL_GL_MakeCurrent(s->window,s->context);s->cacheValid=false;submit(s);glFinish();SDL_GL_MakeCurrent(s->window,s->owner);
}
struct DecodeJob {std::string path;std::atomic<bool>done{false};SDL_Surface*pixels=nullptr;double ms=0;};
int decodeWorker(void*data){
    auto*j=(DecodeJob*)data;double t=measurement::now();
    SDL_Surface*raw=IMG_Load(j->path.c_str());
    if(raw){j->pixels=SDL_ConvertSurfaceFormat(raw,SDL_PIXELFORMAT_RGBA32,0);SDL_FreeSurface(raw);}
    j->ms=measurement::now()-t;j->done.store(true,std::memory_order_release);return j->pixels?0:1;
}
// Private EGL experiment: a worker needs its own surface/context. Making the
// frontend's SDL window surface current on two threads would be invalid.
struct UploadJob {
    void*library=nullptr,*display=nullptr,*context=nullptr,*surface=nullptr;
    unsigned (*makeCurrent)(void*,void*,void*,void*)=nullptr;
    unsigned (*destroyContext)(void*,void*)=nullptr;
    unsigned (*destroySurface)(void*,void*)=nullptr;
    SDL_Surface*pixels=nullptr;GLuint texture=0;std::atomic<bool>done{false};
    double ms=0,createMs=0;GLenum error=0;bool current=false;
};
int uploadWorker(void*data){
    auto*j=(UploadJob*)data;double t=measurement::now();
    if(j->makeCurrent(j->display,j->surface,j->surface,j->context)){
        j->current=true;glGenTextures(1,&j->texture);glBindTexture(GL_TEXTURE_2D,j->texture);glPixelStorei(GL_UNPACK_ALIGNMENT,1);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,j->pixels->w,j->pixels->h,0,GL_RGBA,GL_UNSIGNED_BYTE,j->pixels->pixels);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR_MIPMAP_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
        glGenerateMipmap(GL_TEXTURE_2D);glFinish();j->error=glGetError();j->makeCurrent(j->display,nullptr,nullptr,nullptr);
    }
    j->ms=measurement::now()-t;j->done.store(true,std::memory_order_release);return j->current&&!j->error?0:1;
}
bool uploadContext(UploadJob&j,SlotTabletop*s){
    double t=measurement::now();j.library=SDL_LoadObject("libEGL.so.1");if(!j.library)j.library=SDL_LoadObject("libmali.so");if(!j.library)return false;
    auto at=[&](const char*name){return SDL_LoadFunction(j.library,name);};
    auto getDisplay=(void*(*)())at("eglGetCurrentDisplay");auto getContext=(void*(*)())at("eglGetCurrentContext");
    auto query=(unsigned(*)(void*,void*,int,int*))at("eglQueryContext");auto choose=(unsigned(*)(void*,const int*,void**,int,int*))at("eglChooseConfig");
    auto surface=(void*(*)(void*,void*,const int*))at("eglCreatePbufferSurface");auto context=(void*(*)(void*,void*,void*,const int*))at("eglCreateContext");
    j.makeCurrent=(unsigned(*)(void*,void*,void*,void*))at("eglMakeCurrent");j.destroyContext=(unsigned(*)(void*,void*))at("eglDestroyContext");j.destroySurface=(unsigned(*)(void*,void*))at("eglDestroySurface");
    if(!getDisplay||!getContext||!query||!choose||!surface||!context||!j.makeCurrent||!j.destroyContext||!j.destroySurface)return false;
    SDL_GL_MakeCurrent(s->window,s->context);j.display=getDisplay();void*share=getContext(),*config=nullptr;int id=0,n=0;
    bool ok=query(j.display,share,0x3028,&id);const int attributes[]={0x3028,id,0x3038};ok=ok&&choose(j.display,attributes,&config,1,&n)&&n==1;
    if(ok){const int size[]={0x3057,1,0x3056,1,0x3038},version[]={0x3098,2,0x3038};j.surface=surface(j.display,config,size);if(j.surface)j.context=context(j.display,config,share,version);}
    SDL_GL_MakeCurrent(s->window,s->owner);j.createMs=measurement::now()-t;return j.context&&j.surface;
}
void closeUpload(UploadJob&j){if(j.context)j.destroyContext(j.display,j.context);if(j.surface)j.destroySurface(j.display,j.surface);if(j.library)SDL_UnloadObject(j.library);}
void streamStudy(SlotTabletop*s,const std::string&output){
    std::ofstream log(output+"/streaming.tsv");log<<"stage\tframes\tp50_ms\tp95_ms\tmax_ms\trss_kb\tpeak_rss_kb\n";
    SlotTabletopFrame f;f.selected=3;f.cameraView=0;
    auto render=[&](){s->cacheValid=false;f.seconds+=1/60.f;if(!slot_tabletop_frame(s,f))throw std::runtime_error(slot_tabletop_error(s));};
    auto record=[&](const char*stage,std::vector<double>&samples){std::sort(samples.begin(),samples.end());log<<stage<<'\t'<<samples.size()<<'\t'<<samples[samples.size()/2]<<'\t'<<samples[samples.size()*95/100]<<'\t'<<samples.back()<<'\t'<<memory("VmRSS")<<'\t'<<memory("VmHWM")<<'\n';log.flush();};
    std::vector<double> samples;
    for(int k=0;k<90;k++){double t=measurement::now();render();samples.push_back(measurement::now()-t);}record("scene_only",samples);
    DecodeJob job;job.path=s->prepared+"/pvm/albedo-03.png";
    SDL_Thread*thread=SDL_CreateThread(decodeWorker,"private-png-decode",&job);if(!thread)throw std::runtime_error(SDL_GetError());samples.clear();
    while(!job.done.load(std::memory_order_acquire)||samples.size()<90){double t=measurement::now();render();samples.push_back(measurement::now()-t);}
    int result=0;SDL_WaitThread(thread,&result);if(result||!job.pixels)throw std::runtime_error("Worker PNG decode failed");record("worker_decode",samples);
    std::ofstream meta(output+"/streaming-meta.tsv");meta<<"decode_ms\twidth\theight\tallocation_ms\tmipmap_ms\tstrip_bytes\n";
    SDL_GL_MakeCurrent(s->window,s->context);GLuint texture=0;glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);glPixelStorei(GL_UNPACK_ALIGNMENT,1);
    double t=measurement::now();glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,job.pixels->w,job.pixels->h,0,GL_RGBA,GL_UNSIGNED_BYTE,nullptr);glFinish();double allocate=measurement::now()-t;
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);SDL_GL_MakeCurrent(s->window,s->owner);
    samples.clear();constexpr int rows=64;
    for(int y=0;y<job.pixels->h;y+=rows){
        t=measurement::now();SDL_GL_MakeCurrent(s->window,s->context);glBindTexture(GL_TEXTURE_2D,texture);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,y,job.pixels->w,std::min(rows,job.pixels->h-y),GL_RGBA,GL_UNSIGNED_BYTE,(unsigned char*)job.pixels->pixels+y*job.pixels->pitch);
        SDL_GL_MakeCurrent(s->window,s->owner);render();samples.push_back(measurement::now()-t);
    }record("upload_1MiB_plus_scene",samples);
    SDL_GL_MakeCurrent(s->window,s->context);glBindTexture(GL_TEXTURE_2D,texture);t=measurement::now();glGenerateMipmap(GL_TEXTURE_2D);glFinish();double mip=measurement::now()-t;
    // At this point all pixels/mips have completed on the GPU; only now would
    // production readiness be published. This texture has never been sampled.
    meta<<job.ms<<'\t'<<job.pixels->w<<'\t'<<job.pixels->h<<'\t'<<allocate<<'\t'<<mip<<'\t'<<rows*job.pixels->w*4<<'\n';
    glDeleteTextures(1,&texture);GLenum error=glGetError();SDL_GL_MakeCurrent(s->window,s->owner);
    if(error)throw std::runtime_error("Streaming GL error "+std::to_string(error));
    UploadJob upload;upload.pixels=job.pixels;bool contextOK=uploadContext(upload,s);int worker=1;bool pixelsOK=false;
    if(contextOK){
        thread=SDL_CreateThread(uploadWorker,"private-shared-upload",&upload);if(!thread)throw std::runtime_error(SDL_GetError());samples.clear();std::vector<double> active;
        while(!upload.done.load(std::memory_order_acquire)||samples.size()<90){bool busy=!upload.done.load(std::memory_order_acquire);t=measurement::now();render();double ms=measurement::now()-t;samples.push_back(ms);if(busy)active.push_back(ms);}
        SDL_WaitThread(thread,&worker);record("shared_context_upload_plus_scene",samples);if(!active.empty())record("shared_upload_active_frames",active);
        SDL_GL_MakeCurrent(s->window,s->context);
        if(!worker){
            GLuint check;glGenFramebuffers(1,&check);glBindFramebuffer(GL_FRAMEBUFFER,check);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,upload.texture,0);pixelsOK=glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE;
            for(int y:{0,127,1023,4095})for(int x:{0,127,1023,4095}){unsigned char rgba[4];glReadPixels(x,y,1,1,GL_RGBA,GL_UNSIGNED_BYTE,rgba);pixelsOK=pixelsOK&&!std::memcmp(rgba,(unsigned char*)job.pixels->pixels+y*job.pixels->pitch+x*4,4);}
            glBindFramebuffer(GL_FRAMEBUFFER,0);glDeleteFramebuffers(1,&check);
        }
        if(upload.texture)glDeleteTextures(1,&upload.texture);SDL_GL_MakeCurrent(s->window,s->owner);
    }
    std::ofstream sharing(output+"/shared-context.tsv");sharing<<"supported\tcreate_ms\tworker_ms\tworker_exit\tgl_error\tpixels_match\n"<<contextOK<<'\t'<<upload.createMs<<'\t'<<upload.ms<<'\t'<<worker<<'\t'<<upload.error<<'\t'<<pixelsOK<<'\n';
    closeUpload(upload);SDL_FreeSurface(job.pixels);
    if(contextOK&&(worker||!pixelsOK))throw std::runtime_error("Shared upload failed completion/pixel validation");
}
}
int main(int argc,char**argv){
    if(argc<5){std::fprintf(stderr,"switch-probe MODELS PREPARED REQUESTS.tsv OUTPUT [passes=2] [3:2|4:3] [capture]\n");return 2;}
    std::vector<Request>requests;std::ifstream input(argv[3]);std::string line;
    while(std::getline(input,line)){std::istringstream in(line);Request r;if(!(in>>r.system>>r.tv))continue;std::string face;while(in>>face)r.faces.push_back(face);requests.push_back(std::move(r));}
    if(requests.empty()||SDL_Init(SDL_INIT_VIDEO))return 1;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    const int height=argc>6&&std::string(argv[6])=="4:3"?540:480;
    SDL_Window*w=SDL_CreateWindow("Private switch research",0,0,720,height,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);auto owner=w?SDL_GL_CreateContext(w):nullptr;if(!owner){std::fprintf(stderr,"%s\n",SDL_GetError());return 1;}
    std::printf("renderer=%s\n",glGetString(GL_RENDERER));
    std::ofstream results(std::string(argv[4])+"/loads.tsv");
    results<<"pass\tsystem\ttv\topen_ms\titems_ms\tfirst_frame_ms\tclose_ms\tcontext_ms\tpng_ms\ttex_ms\tmipmap_ms\tbuffer_ms\tcompile_ms\timages\tpixels\tuploaded_bytes_lower_bound\trss_kb\tpeak_rss_kb\ttriangles\tflight_p95_ms\n";
    const int passes=argc>5?std::atoi(argv[5]):2;
    for(int pass=0;pass<passes;pass++)for(const auto&r:requests){
        SDL_Event event;while(SDL_PollEvent(&event))if(event.type==SDL_QUIT)return 3;
        const bool captures=argc>7&&pass==0&&(r.system=="snes"||r.system=="gba");
        measurement::reset();double start=measurement::now();auto*s=slot_tabletop_open(w,argv[1],argv[2],r.system.c_str(),r.tv.c_str(),false,"original",720,height);double opened=measurement::now()-start;if(!s)return 1;
        SlotTabletopItem items[12];std::string ids[12];for(int k=0;k<12;k++){ids[k]="research-"+std::to_string(k);items[k]={ids[k].c_str(),r.system.c_str(),r.faces.empty()?"":r.faces[k%r.faces.size()].c_str()};}
        start=measurement::now();if(!slot_tabletop_items(s,items,12)){std::fprintf(stderr,"%s\n",slot_tabletop_error(s));return 1;}double itemMs=measurement::now()-start;
        slot_tabletop_status(s,100,true,true,"18:08");SlotTabletopFrame f;f.selected=3;f.cameraView=0;
        start=measurement::now();GLuint texture=slot_tabletop_frame(s,f);double first=measurement::now()-start;if(!texture)return 1;
        if(getenv("SLOT_RESEARCH_STREAM")){streamStudy(s,argv[4]);slot_tabletop_close(s);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(w);SDL_Quit();return 0;}
        const std::string stem=std::string(argv[4])+"/"+r.system+"-"+r.tv;
        if(captures&&!capture(s,texture,stem+"-home.bmp"))return 1;
        const auto home=s->cached;std::vector<double> samples;
        for(int k=0;k<25;k++){
            const float off=flightEase(k/24.f);start=measurement::now();flight(s,home,off,false,false);samples.push_back(measurement::now()-start);
            if(captures&&(k%3==0)&&!capture(s,s->target,stem+"-out-"+std::to_string(k)+".bmp"))return 1;
        }
        // Same renderer/home matrices, arriving from the other side. This proves
        // geometry/landing feasibility, not a working asynchronous UI transition.
        for(int k=0;k<25&&captures;k++){
            flight(s,home,1-flightEase(k/24.f),true,true);
            if(k%3==0&&!capture(s,s->target,stem+"-in-tv-"+std::to_string(k)+".bmp"))return 1;
        }
        std::sort(samples.begin(),samples.end());long rss=memory("VmRSS"),peak=memory("VmHWM");int triangles=slot_tabletop_triangles(s);
        GLenum error=glGetError();if(error){std::fprintf(stderr,"Private flight GL error=%u\n",error);return 1;}
        start=measurement::now();slot_tabletop_close(s);double close=measurement::now()-start;
        results<<pass<<'\t'<<r.system<<'\t'<<r.tv<<'\t'<<opened<<'\t'<<itemMs<<'\t'<<first<<'\t'<<close<<'\t'<<measurement::contexts<<'\t'<<measurement::png<<'\t'<<measurement::texture<<'\t'<<measurement::mips<<'\t'<<measurement::buffers<<'\t'<<measurement::compile<<'\t'<<measurement::images<<'\t'<<measurement::pixels<<'\t'<<measurement::gpuBytes<<'\t'<<rss<<'\t'<<peak<<'\t'<<triangles<<'\t'<<samples[samples.size()*95/100]<<'\n';results.flush();
        std::printf("pass=%d %s/%s open=%.2f items=%.2f first=%.2f png=%.2f texture=%.2f buffer=%.2f context=%.2f flight_p95=%.2f rss_kb=%ld\n",pass,r.system.c_str(),r.tv.c_str(),opened,itemMs,first,measurement::png,measurement::texture,measurement::buffers,measurement::contexts,samples[samples.size()*95/100],rss);std::fflush(stdout);
    }
    SDL_GL_DeleteContext(owner);SDL_DestroyWindow(w);SDL_Quit();return 0;
}
