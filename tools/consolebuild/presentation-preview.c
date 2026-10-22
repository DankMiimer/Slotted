/* Front/open poses for live LCD presentation, using the approved renderer. MIT. */
#define main slot_application_main
#include "../slotlaunch/slot-launch.c"
#undef main
extern int IMG_SavePNG(SDL_Surface *,const char *);
int main(int argc,char **argv) {
    if(argc!=3 && argc!=4)return 2;
    if(!getenv("SLOT_MODEL_STYLE"))setenv("SLOT_MODEL_STYLE","realistic",1);
    if(!getenv("SLOT_CONSOLE_COLOR"))setenv("SLOT_CONSOLE_COLOR","original",1);
    /* Log outside the theme; the output folder ships with the stage assets. */
    state_dir=getenv("SLOT_STATE")?getenv("SLOT_STATE"):"/tmp/art-book-slot-launch";process_start=now();
    if(SDL_Init(SDL_INIT_VIDEO))return 1;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    SDL_Window *window=SDL_CreateWindow("Slot presentation poses",0,0,WIDTH,HEIGHT,SDL_WINDOW_HIDDEN);
    int driver=-1;
    for(int i=0;i<SDL_GetNumRenderDrivers();i++){SDL_RendererInfo info={0};SDL_GetRenderDriverInfo(i,&info);if(info.name&&!strcmp(info.name,"opengles2"))driver=i;}
    SDL_Renderer *r=window&&driver>=0?SDL_CreateRenderer(window,driver,SDL_RENDERER_ACCELERATED|SDL_RENDERER_TARGETTEXTURE):NULL;
    if(!r){fprintf(stderr,"GLES2: %s\n",SDL_GetError());return 1;}
    SDL_Texture *target=SDL_CreateTexture(r,SDL_PIXELFORMAT_RGBA8888,SDL_TEXTUREACCESS_TARGET,WIDTH,HEIGHT);
    SDL_SetRenderTarget(r,target);
    SDL_Surface *pixels=SDL_CreateRGBSurfaceWithFormat(0,WIDTH,HEIGHT,32,SDL_PIXELFORMAT_RGBA32);
    for(size_t i=0;i<sizeof(console_specs)/sizeof(console_specs[0]);i++) {
        const ConsoleSpec *s=&console_specs[i];
        if(s->kind!=1&&s->kind!=3&&s->kind!=4&&s->kind!=5)continue;
        SDL_SetRenderDrawColor(r,0,0,0,0);SDL_RenderClear(r);
        ConsoleMesh mesh={0};
        if(!console_mesh_load(&mesh,argv[1],s->name)||!console_mesh_open(&mesh,r))return 1;
        float matrix[16];console_matrix(matrix,0,s->kind==1||s->kind==5?-PSX_PHI:0);
        if(!console_mesh_draw(&mesh,r,matrix,240,false,true))return 1;
        if(mesh.door<mesh.count) {
            if(handheld_has_lid(s->name))handheld_lid_draw(&mesh,r,s->name,matrix,240,1,1);
            else console_mesh_draw(&mesh,r,matrix,240,true,false);
        }
        console_mesh_close(&mesh);SDL_RenderFlush(r);
        if(SDL_RenderReadPixels(r,NULL,SDL_PIXELFORMAT_RGBA32,pixels->pixels,pixels->pitch))return 1;
        char path[PATH_CAP];snprintf(path,sizeof(path),argc==4?"%s/%s.png":"%s/%s-front.png",argv[2],s->name);
        SDL_Surface *output=pixels;
        if(argc==4){
            SDL_Rect box={WIDTH,HEIGHT,0,0};int right=0,bottom=0;
            for(int y=0;y<HEIGHT;y++)for(int x=0;x<WIDTH;x++)if(((Uint8*)pixels->pixels)[y*pixels->pitch+x*4+3]){
                if(x<box.x)box.x=x;
                if(y<box.y)box.y=y;
                if(x+1>right)right=x+1;
                if(y+1>bottom)bottom=y+1;
            }
            box.w=right-box.x;box.h=bottom-box.y;if(box.w<=0||box.h<=0)return 1;
            output=SDL_CreateRGBSurfaceWithFormat(0,box.w,box.h,32,SDL_PIXELFORMAT_RGBA32);
            SDL_SetSurfaceBlendMode(pixels,SDL_BLENDMODE_NONE);SDL_BlitSurface(pixels,&box,output,NULL);
        }
        if(IMG_SavePNG(output,path))return 1;
        if(output!=pixels)SDL_FreeSurface(output);
    }
    SDL_FreeSurface(pixels);SDL_DestroyRenderer(r);SDL_DestroyWindow(window);SDL_Quit();return 0;
}
