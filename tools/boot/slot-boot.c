/* Isolated libretro firmware boot capture probe; never launches via ES (MIT).
 * Build against the pinned frontend's MIT libretro API header, not a core SDK.
 * All writable/system directories must be private copies supplied by the runner.
 */
#define _POSIX_C_SOURCE 200809L
#include "libretro.h"
#include <dlfcn.h>
#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/stat.h>

static const char *system_dir,*save_dir,*output_dir,*boot_mode;
static enum retro_pixel_format format=RETRO_PIXEL_FORMAT_0RGB1555;
static FILE *timings,*audio,*raw_video;
static unsigned current_frame,video_frames,audio_frames;
static unsigned frame_width,frame_height,frame_white,frame_dark;
static uint64_t frame_hash;
static bool capturing;
static double fps=60,sample_rate=44100;
static unsigned char rgb[640*480*3];
struct option {char *key,*value;};
static struct option options[512];static unsigned option_count;
static double clock_seconds(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
static void logger(enum retro_log_level level,const char *fmt,...){(void)level;va_list args;va_start(args,fmt);vfprintf(stderr,fmt,args);va_end(args);}
static bool environment(unsigned command,void *data){
    switch(command){
    case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:*(const char**)data=system_dir;return true;
    case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:*(const char**)data=save_dir;return true;
    case RETRO_ENVIRONMENT_GET_CAN_DUPE:*(bool*)data=true;return true;
    case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:if(*(enum retro_pixel_format*)data>RETRO_PIXEL_FORMAT_RGB565)return false;format=*(enum retro_pixel_format*)data;return true;
    case RETRO_ENVIRONMENT_GET_VARIABLE:{
        struct retro_variable*v=data;v->value=NULL;
        if(!strcmp(v->key,"pcsx_rearmed_show_bios_bootlogo")){v->value=!strcmp(boot_mode,"skip")?"disabled":"enabled";return true;}
        if(!strcmp(v->key,"pcsx_rearmed_bios")){v->value="auto";return true;}
        if(!strcmp(v->key,"gambatte_gb_bootloader")){v->value=!strcmp(boot_mode,"skip")?"disabled":"enabled";return true;}
        if(!strcmp(v->key,"mgba_use_bios")){v->value="ON";return true;}
        if(!strcmp(v->key,"mgba_skip_bios")){v->value=!strcmp(boot_mode,"skip")?"ON":"OFF";return true;}
        for(unsigned i=0;i<option_count;i++)if(!strcmp(v->key,options[i].key)){v->value=options[i].value;return true;}return false;
    }
    case RETRO_ENVIRONMENT_SET_VARIABLES:{
        const struct retro_variable*v=data;
        for(;v&&v->key&&option_count<512;v++){
            const char*begin=strstr(v->value,"; ");if(!begin)continue;begin+=2;const char*end=strchr(begin,'|');size_t n=end?(size_t)(end-begin):strlen(begin);
            options[option_count].key=strdup(v->key);options[option_count].value=strndup(begin,n);option_count++;
        }return true;
    }
    case RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE:*(bool*)data=false;return true;
    case RETRO_ENVIRONMENT_GET_CORE_OPTIONS_VERSION:*(unsigned*)data=0;return true;
    case RETRO_ENVIRONMENT_GET_LANGUAGE:*(unsigned*)data=RETRO_LANGUAGE_ENGLISH;return true;
    case RETRO_ENVIRONMENT_GET_LOG_INTERFACE:((struct retro_log_callback*)data)->log=logger;return true;
    case RETRO_ENVIRONMENT_SET_SUPPORT_NO_GAME:return true;
    case RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS:return true;
    case RETRO_ENVIRONMENT_SET_CONTROLLER_INFO:return true;
    case RETRO_ENVIRONMENT_SET_DISK_CONTROL_INTERFACE:return true;
    case RETRO_ENVIRONMENT_SET_GEOMETRY:return true;
    case RETRO_ENVIRONMENT_SET_SYSTEM_AV_INFO:{const struct retro_system_av_info*v=data;fps=v->timing.fps;sample_rate=v->timing.sample_rate;return true;}
    case RETRO_ENVIRONMENT_SET_MESSAGE:return true;
    case RETRO_ENVIRONMENT_SET_MEMORY_MAPS:return true;
    default:return false;
    }
}
static void poll_input(void){}
static int16_t input_state(unsigned port,unsigned device,unsigned index,unsigned id){(void)port;(void)device;(void)index;(void)id;return 0;}
static size_t audio_batch(const int16_t*data,size_t frames){if(!capturing)return frames;if(audio&&fwrite(data,sizeof(int16_t)*2,frames,audio)!=frames){perror("audio capture");exit(1);}audio_frames+=(unsigned)frames;return frames;}
static void audio_sample(int16_t left,int16_t right){int16_t sample[2]={left,right};audio_batch(sample,1);}
static void pixel(const unsigned char*p,unsigned char*out){
    if(format==RETRO_PIXEL_FORMAT_XRGB8888){uint32_t v;memcpy(&v,p,4);out[0]=v>>16;out[1]=v>>8;out[2]=v;}
    else{uint16_t v;memcpy(&v,p,2);if(format==RETRO_PIXEL_FORMAT_RGB565){out[0]=((v>>11)&31)*255/31;out[1]=((v>>5)&63)*255/63;out[2]=(v&31)*255/31;}else{out[0]=((v>>10)&31)*255/31;out[1]=((v>>5)&31)*255/31;out[2]=(v&31)*255/31;}}
}
static void video(const void*data,unsigned width,unsigned height,size_t pitch){
    if(!data)return;if(data==RETRO_HW_FRAME_BUFFER_VALID||!width||!height||width>2048||height>2048){fprintf(stderr,"Unsupported hardware/invalid boot frame\n");exit(1);}
    unsigned bpp=format==RETRO_PIXEL_FORMAT_XRGB8888?4:2;if(pitch<(size_t)width*bpp){fprintf(stderr,"Invalid boot pitch\n");exit(1);}
    // Normalize PSX field/resolution changes into a fixed 4:3 cache canvas.
    // This probe is deliberately not a boot-completion detector.
    unsigned white=0,dark=0;uint64_t hash=UINT64_C(14695981039346656037);
    for(unsigned y=0;y<480;y++)for(unsigned x=0;x<640;x++){
        unsigned char*p=rgb+(y*640+x)*3;pixel((const unsigned char*)data+(y*height/480)*pitch+(x*width/640)*bpp,p);
        unsigned sum=p[0]+p[1]+p[2];white+=sum>690;dark+=sum<45;
        if(!(x%16)&&!(y%16)){hash=(hash^p[0])*UINT64_C(1099511628211);hash=(hash^p[1])*UINT64_C(1099511628211);hash=(hash^p[2])*UINT64_C(1099511628211);}
    }
    frame_width=width;frame_height=height;frame_white=white;frame_dark=dark;frame_hash=hash;
    video_frames++;
}
static void output_frame(void){
    // Libretro NULL video callbacks duplicate the last frame. Output once per
    // retro_run, including duplicates, so the encoded video keeps core timing.
    fprintf(timings,"%u\t%u\t%u\t%.8f\t%.8f\t%016" PRIx64 "\n",current_frame,frame_width,frame_height,frame_white/(640.*480),frame_dark/(640.*480),frame_hash);
    if(raw_video&&fwrite(rgb,1,sizeof(rgb),raw_video)!=sizeof(rgb)){perror("video capture");exit(1);}
    if(current_frame%30==0){char path[2048];snprintf(path,sizeof(path),"%s/frame-%04u.ppm",output_dir,current_frame);FILE*f=fopen(path,"wb");if(!f){perror(path);exit(1);}fprintf(f,"P6\n640 480\n255\n");fwrite(rgb,1,sizeof(rgb),f);fclose(f);}
}
#define IMPORT(name) __typeof__(&name) name##_fn=(__typeof__(&name))dlsym(core,#name); if(!name##_fn){fprintf(stderr,"Missing core symbol: " #name "\n");return 1;}
int main(int argc,char**argv){
    if(argc!=8){fprintf(stderr,"usage: slot-boot CORE PRIVATE_BIOS_DIR PRIVATE_SAVE_DIR CONTENT OUTPUT_DIR FRAMES show|skip\n");return 2;}
    system_dir=argv[2];save_dir=argv[3];output_dir=argv[5];boot_mode=argv[7];
    unsigned frames=(unsigned)strtoul(argv[6],NULL,10);if(frames<1||frames>1800||(strcmp(boot_mode,"show")&&strcmp(boot_mode,"skip")))return 2;
    if(!strncmp(system_dir,"/userdata/bios",14)||!strncmp(save_dir,"/userdata/saves",15)){fprintf(stderr,"Use private firmware/save directories, not user originals\n");return 2;}
    char path[2048];snprintf(path,sizeof(path),"%s/frames.tsv",output_dir);timings=fopen(path,"wx");snprintf(path,sizeof(path),"%s/audio.s16le",output_dir);audio=fopen(path,"wx");if(!timings||!audio){perror("private capture outputs");return 1;}fprintf(timings,"frame\twidth\theight\twhite\tdark\thash\n");
    if(getenv("SLOT_BOOT_RAW_VIDEO")){snprintf(path,sizeof(path),"%s/video.rgb",output_dir);raw_video=fopen(path,"wx");if(!raw_video)return 1;}
    double begin=clock_seconds();void*core=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);if(!core){fprintf(stderr,"dlopen: %s\n",dlerror());return 1;}
    IMPORT(retro_set_environment);IMPORT(retro_set_video_refresh);IMPORT(retro_set_audio_sample);IMPORT(retro_set_audio_sample_batch);IMPORT(retro_set_input_poll);IMPORT(retro_set_input_state);IMPORT(retro_init);IMPORT(retro_deinit);IMPORT(retro_get_system_info);IMPORT(retro_get_system_av_info);IMPORT(retro_load_game);IMPORT(retro_unload_game);IMPORT(retro_run);
    retro_set_environment_fn(environment);retro_set_video_refresh_fn(video);retro_set_audio_sample_fn(audio_sample);retro_set_audio_sample_batch_fn(audio_batch);retro_set_input_poll_fn(poll_input);retro_set_input_state_fn(input_state);retro_init_fn();
    struct retro_system_info info={0};retro_get_system_info_fn(&info);struct retro_game_info game={0};game.path=argv[4];void*content=NULL;
    if(!info.need_fullpath){FILE*f=fopen(argv[4],"rb");if(!f)return 1;fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);if(n<0||n>64*1024*1024)return 1;content=malloc((size_t)n);if(!content||fread(content,1,(size_t)n,f)!=(size_t)n)return 1;fclose(f);game.data=content;game.size=(size_t)n;}
    if(!retro_load_game_fn(&game)){fprintf(stderr,"Core rejected content/firmware\n");retro_deinit_fn();return 1;}
    struct retro_system_av_info av={0};retro_get_system_av_info_fn(&av);fps=av.timing.fps;sample_rate=av.timing.sample_rate;double loaded=clock_seconds();
    capturing=true;
    for(current_frame=0;current_frame<frames;current_frame++){retro_run_fn();output_frame();}
    capturing=false;
    double ended=clock_seconds();retro_unload_game_fn();retro_deinit_fn();free(content);fclose(timings);fclose(audio);if(raw_video)fclose(raw_video);
    snprintf(path,sizeof(path),"%s/capture.json",output_dir);FILE*report=fopen(path,"wx");if(!report)return 1;
    fprintf(report,"{\"core\":\"%s\",\"version\":\"%s\",\"mode\":\"%s\",\"frames\":%u,\"video_frames\":%u,\"fps\":%.8f,\"audio_frames\":%u,\"sample_rate\":%.1f,\"load_seconds\":%.5f,\"capture_seconds\":%.5f,\"completion_detector\":false}\n",info.library_name,info.library_version,boot_mode,frames,video_frames,fps,audio_frames,sample_rate,loaded-begin,ended-loaded);fclose(report);
    fprintf(stdout,"boot capture mode=%s frames=%u video=%u load=%.3fs capture=%.3fs fps=%.3f audio_hz=%.0f\n",boot_mode,frames,video_frames,loaded-begin,ended-loaded,fps,sample_rate);
    for(unsigned i=0;i<option_count;i++){free(options[i].key);free(options[i].value);}dlclose(core);return 0;
}
