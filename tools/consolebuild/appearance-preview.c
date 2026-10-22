/* Render appearance derivatives through the production GLES renderer (MIT).
 * Local SDL offscreen only; no hooks, audio, device layers or ROM processing. */
#define main slot_application_main
#include "../slotlaunch/slot-launch.c"
#undef main
extern int IMG_SavePNG(SDL_Surface *,const char *);

int main(int argc,char **argv)
{
    if(argc!=5)return 2;
    const char *assets=argv[1],*out=argv[2];
    setenv("SLOT_MODEL_STYLE",argv[3],1);setenv("SLOT_CONSOLE_COLOR",argv[4],1);
    state_dir=out;process_start=now();
    if(SDL_Init(SDL_INIT_VIDEO))return 1;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    SDL_Window *w=SDL_CreateWindow("Slotters appearance",0,0,WIDTH,HEIGHT,SDL_WINDOW_HIDDEN);
    int driver=-1;for(int i=0;i<SDL_GetNumRenderDrivers();i++){
        SDL_RendererInfo info={0};SDL_GetRenderDriverInfo(i,&info);
        if(info.name&&!strcmp(info.name,"opengles2"))driver=i;
    }
    SDL_Renderer *r=w&&driver>=0?SDL_CreateRenderer(w,driver,SDL_RENDERER_ACCELERATED|SDL_RENDERER_TARGETTEXTURE):NULL;
    if(!r){fprintf(stderr,"GLES2: %s\n",SDL_GetError());return 1;}
    SDL_Texture *target=SDL_CreateTexture(r,SDL_PIXELFORMAT_RGBA8888,SDL_TEXTUREACCESS_TARGET,WIDTH,HEIGHT);
    SDL_SetRenderTarget(r,target);
    SDL_Surface *pixels=SDL_CreateRGBSurfaceWithFormat(0,WIDTH,HEIGHT,32,SDL_PIXELFORMAT_RGBA32);
    for(size_t i=0;i<sizeof(console_specs)/sizeof(console_specs[0]);i++){
        const ConsoleSpec *s=&console_specs[i];
        if(!console_style_ready(s->name))continue;
        SDL_SetRenderDrawColor(r,0,0,0,0);SDL_RenderClear(r);
            ConsoleMesh mesh={0};
            if(!console_mesh_load(&mesh,assets,s->name)||!console_mesh_open(&mesh,r))return 1;
            double yaw=(s->kind==0||s->kind==2||s->kind==6?SLOT_HOME_YAW_DEGREES:s->kind==1?-12:s->kind==5?-14:-8)*PSX_PI/180;
            float matrix[16];console_matrix(matrix,yaw,s->kind==1||s->kind==5?-PSX_PHI:0);
            if(!console_mesh_draw(&mesh,r,matrix,240,false,true))return 1;
            if(mesh.door<mesh.count){
                if(handheld_has_lid(s->name))handheld_lid_draw(&mesh,r,s->name,matrix,240,0,0);
                else console_mesh_draw(&mesh,r,matrix,240,true,false);
            }
            console_mesh_close(&mesh);
        SDL_RenderFlush(r);
        if(SDL_RenderReadPixels(r,NULL,SDL_PIXELFORMAT_RGBA32,pixels->pixels,pixels->pitch))return 1;
        char path[PATH_CAP];snprintf(path,sizeof(path),"%s/%s.png",out,s->name);
        if(IMG_SavePNG(pixels,path))return 1;
    }
    SDL_FreeSurface(pixels);SDL_DestroyRenderer(r);SDL_DestroyWindow(w);SDL_Quit();return 0;
}
