// Compares SlotPng.h's libpng decode with the IMG_Load + RGBA32 path the
// tabletop used: identical pixel bytes and the time of each, per file (MIT).
// Usage: png_decode_check FILE.png...   Read-only; exit 1 on any mismatch.
#include "SlotPng.h"
#include <cstring>
#include <vector>
#include <cstdlib>
extern "C" SDL_Surface* IMG_Load(const char*);
// TurboJPEG (libturbojpeg.so.0 on Knulli), declared here: the sysroot has no header.
extern "C" {
typedef void* tjhandle;
tjhandle tjInitDecompress(void);
int tjDecompressHeader3(tjhandle,const unsigned char*,unsigned long,int*,int*,int*,int*);
int tjDecompress2(tjhandle,const unsigned char*,unsigned long,unsigned char*,int,int,int,int,int);
int tjDestroy(tjhandle);
}
static double now(){return 1000.0*SDL_GetPerformanceCounter()/SDL_GetPerformanceFrequency();}
// JPEG files (some textures are JPEG data named .png): TurboJPEG vs SDL_image, reported only.
static void jpeg(const char*path,SDL_Surface*rgba,double stbMs){
    FILE*f=std::fopen(path,"rb");std::vector<unsigned char>d;if(f){std::fseek(f,0,SEEK_END);d.resize(std::ftell(f));std::fseek(f,0,SEEK_SET);if(std::fread(d.data(),1,d.size(),f)!=d.size())d.clear();std::fclose(f);}
    if(d.size()<4||d[0]!=0xFF||d[1]!=0xD8)return;
    for(int flags:{0,4096,256}){ // default, ACCURATEDCT, FASTUPSAMPLE
        const double t0=now();tjhandle h=tjInitDecompress();int w=0,hh=0,sub=0,cs=0;
        if(!h||tjDecompressHeader3(h,d.data(),d.size(),&w,&hh,&sub,&cs)){if(h)tjDestroy(h);return;}
        std::vector<unsigned char>out((size_t)w*hh*3);const int r=tjDecompress2(h,d.data(),d.size(),out.data(),w,w*3,hh,0/*TJPF_RGB*/,flags);tjDestroy(h);const double t1=now();
        if(r||w!=rgba->w||hh!=rgba->h){std::printf("%s\tturbojpeg flags=%d failed\n",path,flags);continue;}
        long differing=0;int maxDiff=0;
        for(int y=0;y<hh;y++){const auto*a=(const unsigned char*)rgba->pixels+(size_t)y*rgba->pitch;const auto*b=out.data()+(size_t)y*w*3;
            for(int x=0;x<w;x++){int m=0;for(int c=0;c<3;c++)m=std::max(m,std::abs(a[x*4+c]-b[x*3+c]));if(m){differing++;maxDiff=std::max(maxDiff,m);}}}
        std::printf("%s\tjpeg subsamp=%d stb_ms=%.1f turbojpeg_flags=%d_ms=%.1f\t%s differing_pixels=%.4f%% max_diff=%d\n",path,sub,stbMs,flags,t1-t0,
            differing?"DIFFERENT":"identical",100.0*differing/((double)w*hh),maxDiff);std::fflush(stdout);
    }
}
int main(int argc,char**argv){
    int mismatches=0;double before=0,after=0;
    for(int i=1;i<argc;i++){
        const double t0=now();SDL_Surface*raw=IMG_Load(argv[i]);
        SDL_Surface*rgba=raw?SDL_ConvertSurfaceFormat(raw,SDL_PIXELFORMAT_RGBA32,0):nullptr;const double t1=now();
        SDL_Surface*fast=slot_png::decode(argv[i]);const double t2=now();
        if(!rgba){std::printf("%s\tIMG_Load failed\n",argv[i]);mismatches++;if(raw)SDL_FreeSurface(raw);if(fast)SDL_FreeSurface(fast);continue;}
        const char*verdict="fallback";
        if(fast){
            bool same=fast->w==rgba->w&&fast->h==rgba->h;
            const int channels=fast->format->BytesPerPixel;
            for(int y=0;same&&y<fast->h;y++){
                const auto*a=(const unsigned char*)rgba->pixels+(size_t)y*rgba->pitch;const auto*b=(const unsigned char*)fast->pixels+(size_t)y*fast->pitch;
                if(channels==4)same=std::memcmp(a,b,(size_t)fast->w*4)==0;
                else for(int x=0;same&&x<fast->w;x++)same=a[x*4]==b[x*3]&&a[x*4+1]==b[x*3+1]&&a[x*4+2]==b[x*3+2]&&a[x*4+3]==255;
            }
            verdict=same?(channels==3?"identical-rgb":"identical-rgba"):"MISMATCH";if(!same)mismatches++;
            before+=t1-t0;after+=t2-t1;
        }
        std::printf("%s\t%dx%d\timg_load+rgba_ms=%.1f\tlibpng_ms=%.1f\t%s\n",argv[i],rgba->w,rgba->h,t1-t0,t2-t1,verdict);std::fflush(stdout);
        if(!fast)jpeg(argv[i],rgba,t1-t0);
        SDL_FreeSurface(raw);SDL_FreeSurface(rgba);if(fast)SDL_FreeSurface(fast);
    }
    std::printf("total compared: before %.0f ms, after %.0f ms, mismatches %d\n",before,after,mismatches);
    return mismatches?1:0;
}
