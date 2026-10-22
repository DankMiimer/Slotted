// Capability probe: shared scene texture exists in ES's original GLES context.
#include <SDL.h>
#define SDL_USE_BUILTIN_OPENGL_DEFINITIONS 1
#include <SDL_opengles2.h>
#include "../overlay/es-app/src/components/SlotNative.h"
#include "../overlay/es-app/src/components/SlotScreens.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
int main(int argc,char **argv) {
    if(argc<3||argc>5)return 2;
    if(SDL_Init(SDL_INIT_VIDEO))return 1;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    SDL_Window *w=SDL_CreateWindow("Slot shared texture probe",0,0,720,480,SDL_WINDOW_OPENGL|SDL_WINDOW_HIDDEN);
    SDL_GLContext owner=w?SDL_GL_CreateContext(w):NULL;
    if(!owner){fprintf(stderr,"owner: %s\n",SDL_GetError());return 1;}
    GLint max_texture=0,max_attributes=0,max_units=0;
    glGetIntegerv(GL_MAX_TEXTURE_SIZE,&max_texture);glGetIntegerv(GL_MAX_VERTEX_ATTRIBS,&max_attributes);glGetIntegerv(GL_MAX_TEXTURE_IMAGE_UNITS,&max_units);
    printf("GLES limits: texture=%d attributes=%d fragment_units=%d; renderer=%s\n",max_texture,max_attributes,max_units,glGetString(GL_RENDERER));
    const char *extensions=(const char *)glGetString(GL_EXTENSIONS);
    printf("compressed textures: astc_ldr=%d etc1=%d etc2(ES3)=%d\n",extensions&&strstr(extensions,"GL_KHR_texture_compression_astc_ldr")!=NULL,
           extensions&&strstr(extensions,"GL_OES_compressed_ETC1_RGB8_texture")!=NULL,extensions&&strstr(extensions,"GL_OES_compressed_ETC2")!=NULL);
    const char *model=argc>3?argv[3]:"gba";
    if(getenv("SLOT_PREFETCH")){
        /* As while browsing: warm on a worker, then open once it settles. */
        Uint64 warm=SDL_GetPerformanceCounter();int state;
        while((state=slot_native_prefetch(argv[1],model))==0)SDL_Delay(5);
        printf("prefetch state=%d after %.3f ms\n",state,1000.0*(SDL_GetPerformanceCounter()-warm)/SDL_GetPerformanceFrequency());
    }
    Uint64 load_start=SDL_GetPerformanceCounter();
    SlotNative *s=slot_native_open(w,argv[1],"/userdata/roms/gba/Probe.gba",model,"missing.png",getenv("SLOT_MODEL_STYLE")?getenv("SLOT_MODEL_STYLE"):"realistic",getenv("SLOT_CONSOLE_COLOR")?getenv("SLOT_CONSOLE_COLOR"):"original");
    if(!s)return 1;
    if(getenv("SLOT_CLOSE"))slot_native_optical_close(s,atof(getenv("SLOT_CLOSE")));
    printf("load_ms=%.3f\n",1000.0*(SDL_GetPerformanceCounter()-load_start)/SDL_GetPerformanceFrequency());
    if(getenv("SLOT_REOPEN")){
        /* The frontend reopens a scene for each newly visible game. */
        slot_native_close(s);load_start=SDL_GetPerformanceCounter();
        s=slot_native_open(w,argv[1],"/userdata/roms/gba/Probe.gba",model,"missing.png",getenv("SLOT_MODEL_STYLE")?getenv("SLOT_MODEL_STYLE"):"realistic",getenv("SLOT_CONSOLE_COLOR")?getenv("SLOT_CONSOLE_COLOR"):"original");
        if(!s)return 1;
        printf("reopen_ms=%.3f\n",1000.0*(SDL_GetPerformanceCounter()-load_start)/SDL_GetPerformanceFrequency());
    }
    if(getenv("SLOT_BENCH")){
        double frames[180];
        for(int i=-20;i<180;i++){
            Uint64 start=SDL_GetPerformanceCounter();slot_native_present(s,1);glFinish();
            if(i>=0)frames[i]=1000.0*(SDL_GetPerformanceCounter()-start)/SDL_GetPerformanceFrequency();
        }
        for(int i=0;i<180;i++)for(int j=i+1;j<180;j++)if(frames[j]<frames[i]){double t=frames[i];frames[i]=frames[j];frames[j]=t;}
        printf("scene_ms n=180 p50=%.3f p95=%.3f p99=%.3f max=%.3f\n",frames[90],frames[171],frames[178],frames[179]);
    }
    if(getenv("SLOT_EXPECT_LOCAL")) {
        float p[2];int local=slot_native_lcd(s,0,0,p);
        if(local!=atoi(getenv("SLOT_EXPECT_LOCAL"))){fprintf(stderr,"Wrong local profile selection\n");return 1;}
    }
    int front=argc==5&&!strcmp(argv[4],"front"),browse=argc==5&&!strcmp(argv[4],"browse");
    GLuint texture=browse?slot_native_browse(s):front?slot_native_present(s,1):slot_native_frame(s,argc==5?atof(argv[4]):.35f,1),fbo=0;
    float bounds[4];if(argc==5 && !slot_native_bounds(s,bounds))return 1;
    int clipped=0;
    if(front)printf("bounds %s %.1f %.1f %.1f %.1f\n",model,bounds[0],bounds[1],bounds[2],bounds[3]);
    if(front && (bounds[0]<=0 || bounds[1]<=0 || bounds[0]+bounds[2]>=720 || bounds[1]+bounds[3]>=480)) {
        fprintf(stderr,"Presentation clips the %s silhouette\n",model);clipped=1;   // the image is still saved for review
    }
    if(front)for(unsigned i=0;i<sizeof(slotScreens)/sizeof(slotScreens[0]);i++)if(!strcmp(slotScreens[i].name,model)) {
        printf("lcd %s",model);
        for(int j=0;j<slotScreens[i].count;j++)for(int k=0;k<4;k++) {
            float p[2];if(!slot_native_lcd(s,j,k,p))slot_native_project(s,slotScreens[i].points[j]+k*3,j==0 && slotScreens[i].count==2,p);
            printf(" %.3f %.3f",p[0],p[1]);
        }
        printf("\n");
    }
    if(front){float c[2],e[2];if(slot_native_ground(s,c,e))printf("ground %s %.3f %.3f %.3f %.3f\n",model,c[0],c[1],e[0],e[1]);}
    if(front){float p[2];if(slot_native_contact(s,p))printf("contact %s %.3f %.3f\n",model,p[0],p[1]);}
    glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
    if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)return 1;
    int width,height;slot_native_raster_size(&width,&height);
    SDL_Surface *image=SDL_CreateRGBSurfaceWithFormat(0,width,height,32,SDL_PIXELFORMAT_RGBA32);
    glReadPixels(0,0,width,height,GL_RGBA,GL_UNSIGNED_BYTE,image->pixels);
    if(front) {
        int left=width,top=height,right=0,bottom=0;
        for(int y=0;y<height;y++)for(int x=0;x<width;x++)if(((unsigned char*)image->pixels)[y*image->pitch+x*4+3]>20) {
            if(x<left)left=x;if(y<top)top=y;if(x+1>right)right=x+1;if(y+1>bottom)bottom=y+1;
        }
        const float scale=width/720.f;
        float expected[]={left/scale,top/scale,(right-left)/scale,(bottom-top)/scale};
        for(int i=0;i<4;i++)if(fabsf(expected[i]-bounds[i])>1.f){fprintf(stderr,"High resolution bounds mismatch %s: %f / %f\n",model,expected[i],bounds[i]);return 1;}
    }
    unsigned visible=0;for(int i=0;i<width*height;i++)if(((unsigned char*)image->pixels)[i*4+3])visible++;
    printf("shared texture %u; visible pixels %u; GL error %u\n",texture,visible,glGetError());
    SDL_SaveBMP(image,argv[2]);SDL_FreeSurface(image);
    glBindFramebuffer(GL_FRAMEBUFFER,0);glDeleteFramebuffers(1,&fbo);
    slot_native_close(s);SDL_GL_DeleteContext(owner);SDL_DestroyWindow(w);SDL_Quit();
    return clipped||visible<=1000?1:0;
}
