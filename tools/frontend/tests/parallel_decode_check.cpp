// Decodes the given textures concurrently, as a synchronous tabletop open prefetches
// them (SlotTabletop.cpp decodeImage), ROUNDS times in fresh threads (MIT).
// Usage: parallel_decode_check ROUNDS FILE...   No display or GL needed.
#include "SlotPng.h"
#include <future>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
extern "C" SDL_Surface* IMG_Load(const char*);
static SDL_Surface* decodeImage(const std::string& path){
    if(SDL_Surface* png=slot_png::decode(path.c_str()))return png;
    SDL_Surface* raw=IMG_Load(path.c_str());if(!raw)throw std::runtime_error("Cannot load texture: "+path);
    if(raw->format->format==SDL_PIXELFORMAT_RGB24)return raw;
    SDL_Surface* p=SDL_ConvertSurfaceFormat(raw,SDL_PIXELFORMAT_RGBA32,0);SDL_FreeSurface(raw);if(!p)throw std::runtime_error(SDL_GetError());return p;
}
int main(int argc,char** argv){
    if(argc<3)return 2;
    const int rounds=std::atoi(argv[1]);
    for(int r=0;r<rounds;r++){
        const double start=1000.0*SDL_GetPerformanceCounter()/SDL_GetPerformanceFrequency();
        std::map<std::string,std::future<SDL_Surface*>> decodes;
        for(int i=2;i<argc;i++)decodes[argv[i]]=std::async(std::launch::async,decodeImage,std::string(argv[i]));
        size_t bytes=0;
        for(auto& d:decodes){SDL_Surface* s=d.second.get();bytes+=(size_t)s->pitch*s->h;SDL_FreeSurface(s);}
        std::printf("round %d: %zu files, %.0f MB, %.0f ms\n",r,decodes.size(),bytes/1048576.0,1000.0*SDL_GetPerformanceCounter()/SDL_GetPerformanceFrequency()-start);std::fflush(stdout);
    }
    return 0;
}
