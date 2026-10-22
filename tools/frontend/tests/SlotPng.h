// TEST-ONLY. Do not include in the frontend: there libpng16.so.16 is already loaded by
// libfreetype, so dlopen returns that copy (RTLD_DEEPBIND has no effect) and its zlib
// imports resolve partly to FreeImage's bundled zlib and partly to the system zlib; the
// 21 Oct trial-t candidate crashed decoding textures that way. Kept for the measurement
// in png_decode_check.cpp (same bytes as SDL_image/stb, about half the time standalone).
// Lossless decode of plain 8-bit RGB/RGBA PNGs with the system libpng (MIT).
// Knulli's SDL_image decodes PNG with its bundled stb_image; libpng with the
// system zlib returns the same bytes for these files in about half the time
// (tools/frontend/tests/png_decode_check.cpp). libpng16.so.16 is opened at run
// time with RTLD_DEEPBIND: the frontend also links FreeImage, which exports an
// older bundled libpng/zlib that is slower and would otherwise win symbol lookup.
// Any other PNG (palette, grey, 16-bit, interlaced, tRNS), a missing library or
// an error returns nullptr and the caller keeps using IMG_Load. RGB stays RGB24.
#pragma once
#include <SDL.h>
#include <png.h>
#include <dlfcn.h>
#include <cstdio>
#include <cstdlib>
#include <csetjmp>
#include <type_traits>
namespace slot_png {
struct Api {
    decltype(&png_sig_cmp) sigCmp=nullptr;decltype(&png_create_read_struct) createRead=nullptr;
    decltype(&png_create_info_struct) createInfo=nullptr;decltype(&png_destroy_read_struct) destroyRead=nullptr;
    decltype(&png_set_longjmp_fn) longjmpFn=nullptr;decltype(&png_init_io) initIo=nullptr;
    decltype(&png_set_sig_bytes) sigBytes=nullptr;decltype(&png_read_info) readInfo=nullptr;
    decltype(&png_get_IHDR) ihdr=nullptr;decltype(&png_get_valid) valid=nullptr;
    decltype(&png_get_rowbytes) rowBytes=nullptr;decltype(&png_read_image) readImage=nullptr;
    decltype(&png_read_end) readEnd=nullptr;bool ready=false;
};
inline const Api& api() {
    static const Api loaded=[]{
        Api a;void* library=dlopen("libpng16.so.16",RTLD_NOW|RTLD_LOCAL|RTLD_DEEPBIND);if(!library)return a;
        auto load=[&](auto& function,const char* name){function=reinterpret_cast<typename std::remove_reference<decltype(function)>::type>(dlsym(library,name));return function!=nullptr;};
        a.ready=load(a.sigCmp,"png_sig_cmp")&&load(a.createRead,"png_create_read_struct")&&load(a.createInfo,"png_create_info_struct")
            &&load(a.destroyRead,"png_destroy_read_struct")&&load(a.longjmpFn,"png_set_longjmp_fn")&&load(a.initIo,"png_init_io")
            &&load(a.sigBytes,"png_set_sig_bytes")&&load(a.readInfo,"png_read_info")&&load(a.ihdr,"png_get_IHDR")&&load(a.valid,"png_get_valid")
            &&load(a.rowBytes,"png_get_rowbytes")&&load(a.readImage,"png_read_image")&&load(a.readEnd,"png_read_end");
        return a;
    }();
    return loaded;
}
inline SDL_Surface* decode(const char* path) {
    const Api& png_=api();if(!png_.ready)return nullptr;
    FILE* file=std::fopen(path,"rb");if(!file)return nullptr;
    unsigned char signature[8];
    if(std::fread(signature,1,8,file)!=8||png_.sigCmp(signature,0,8)){std::fclose(file);return nullptr;}
    png_structp png=png_.createRead(PNG_LIBPNG_VER_STRING,nullptr,nullptr,nullptr);
    png_infop info=png?png_.createInfo(png):nullptr;
    if(!info){png_.destroyRead(&png,nullptr,nullptr);std::fclose(file);return nullptr;}
    // No C++ objects live across setjmp/longjmp; both owners are plain pointers.
    SDL_Surface* volatile surface=nullptr;png_bytep* volatile rows=nullptr;
    if(setjmp(*png_.longjmpFn(png,longjmp,sizeof(jmp_buf)))){
        std::free(rows);if(surface)SDL_FreeSurface(surface);
        png_.destroyRead(&png,&info,nullptr);std::fclose(file);return nullptr;
    }
    png_.initIo(png,file);png_.sigBytes(png,8);png_.readInfo(png,info);
    png_uint_32 width=0,height=0;int depth=0,type=0,interlace=0;
    png_.ihdr(png,info,&width,&height,&depth,&type,&interlace,nullptr,nullptr);
    const bool rgb=type==PNG_COLOR_TYPE_RGB,plain=depth==8&&interlace==PNG_INTERLACE_NONE&&(rgb||type==PNG_COLOR_TYPE_RGB_ALPHA)
        &&!png_.valid(png,info,PNG_INFO_tRNS)&&width>0&&height>0&&width<=16384&&height<=16384;
    if(plain)surface=SDL_CreateRGBSurfaceWithFormat(0,(int)width,(int)height,rgb?24:32,rgb?SDL_PIXELFORMAT_RGB24:SDL_PIXELFORMAT_RGBA32);
    if(surface&&png_.rowBytes(png,info)<=(png_size_t)surface->pitch)rows=(png_bytep*)std::malloc(sizeof(png_bytep)*height);
    if(!rows){
        if(surface)SDL_FreeSurface(surface);
        png_.destroyRead(&png,&info,nullptr);std::fclose(file);return nullptr;
    }
    for(png_uint_32 y=0;y<height;y++)rows[y]=(png_bytep)surface->pixels+(size_t)y*surface->pitch;
    png_.readImage(png,rows);png_.readEnd(png,nullptr);
    std::free(rows);png_.destroyRead(&png,&info,nullptr);std::fclose(file);
    return surface;
}
}
