/* Independent occlusion regression: put the same disc above/below a tray. */
#define main slot_application_main
#include "../../slotlaunch/slot-launch.c"
#undef main
int main(void)
{
    if(SDL_Init(SDL_INIT_VIDEO))return 1;
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);
    SDL_Window *w=SDL_CreateWindow("optical depth",0,0,720,480,SDL_WINDOW_HIDDEN);
    SDL_SetHint(SDL_HINT_RENDER_DRIVER,"opengles2");
    SDL_Renderer *r=SDL_CreateRenderer(w,-1,SDL_RENDERER_ACCELERATED|SDL_RENDERER_TARGETTEXTURE);
    if(!r)return 1;
    SDL_Texture *target=SDL_CreateTexture(r,SDL_PIXELFORMAT_RGBA8888,SDL_TEXTUREACCESS_TARGET,720,480);
    SDL_SetRenderTarget(r,target);
    CartridgeArt art={0};ConsoleMesh *m=&art.mesh;
    m->vertices=calloc(4,sizeof(ToonVertex));m->index_data=malloc(12);
    m->vertex_count=4;m->count=m->door=6;m->realistic=true;
    ToonVertex v[]={{{-140,0,-140},{0,1,0},{.5,.5,.5}},{{140,0,-140},{0,1,0},{.5,.5,.5}},
                    {{140,0,140},{0,1,0},{.5,.5,.5}},{{-140,0,140},{0,1,0},{.5,.5,.5}}};
    uint16_t indices[]={0,2,1,0,3,2};
    memcpy(m->vertices,v,sizeof(v));memcpy(m->index_data,indices,sizeof(indices));
    if(!console_mesh_open(m,r))return 1;
    SDL_Surface *p=SDL_CreateRGBSurfaceWithFormat(0,720,480,32,SDL_PIXELFORMAT_RGBA32);
    SDL_FillRect(p,NULL,SDL_MapRGBA(p->format,0,255,96,255));
    PsxArt disc={0};disc.disc=SDL_CreateTextureFromSurface(r,p);disc.underside=disc.disc;
    unsigned green[2]={0};
    for(int side=0;side<2;side++){
        SDL_SetRenderDrawColor(r,0,0,0,255);SDL_RenderClear(r);
        float matrix[16];console_matrix(matrix,0,0);
        if(!console_mesh_draw(m,r,matrix,240,false,true))return 1;
        if(!optical_disc_draw(&art,r,&disc,(PsxVec){0,side?-25:25,0},
            (PsxVec){1,0,0},(PsxVec){0,0,1},75,2,240))return 1;
        SDL_RenderFlush(r);
        SDL_RenderReadPixels(r,NULL,SDL_PIXELFORMAT_RGBA32,p->pixels,p->pitch);
        for(int y=0;y<480;y++)for(int x=0;x<720;x++){
            Uint8 *q=(Uint8 *)p->pixels+y*p->pitch+x*4;
            if(q[0]<20&&q[1]>240&&q[2]>70&&q[2]<130)green[side]++;
        }
    }
    GLenum error=cgGetError();
    console_mesh_close(&art.disc_mesh);console_mesh_close(m);
    SDL_DestroyTexture(disc.disc);SDL_FreeSurface(p);SDL_DestroyRenderer(r);SDL_DestroyWindow(w);SDL_Quit();
    printf("disc above tray: %u green; below tray: %u green; GL error %u\n",green[0],green[1],error);
    return green[0]>5000&&green[1]==0&&error==GL_NO_ERROR?0:1;
}
