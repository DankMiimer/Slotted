/* Native slot/hinge scenes, embedded without invoking the standalone launcher.
 * ES retains its window, event loop and swap. SDL's separate shared GLES2
 * context renders into a target texture; one cached bounds readback per model.
 * Copyright 2026, MIT. Model attribution remains in _slot/MODEL_CREDITS.txt. */
static float slot_camera_matrix[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
static int slot_presenting;
static double slot_presentation;
static double slot_view_origin=240;
/* Private local profiles override registration without changing the accepted
 * standalone helper or distributing user-supplied geometry in the theme. */
static double slot_model_hinge[3],slot_model_angle;
#define SLOT_RASTER_SCALE 2
#define main slot_standalone_main
#include SLOT_HELPER_SOURCE
#undef main
#include "SlotNative.h"

struct SlotNative {
    SDL_Window *window;
    SDL_GLContext owner,context;
    SDL_Renderer *renderer;
    SDL_Texture *target,*face;
    CartridgeArt cartridge;
    PsxArt disc;
    const ConsoleSpec *console;
    const Media *shape;
    unsigned texture;
    float presentation,optical_close;
    bool presenting;
    bool local;
    float registration[16];
};

static void slot_registration(SlotNative *s) {
    for(int i=0;i<3;i++)slot_model_hinge[i]=s->local?s->registration[i]:ags_lid_hinge[i];
    slot_model_angle=s->local?s->registration[3]:ags_lid_open_radians;
}

static int slot_local(SlotNative *s,const char *assets,const char *model) {
    if(strcmp(model,"gba"))return 0;
    // Theme setting "slot-gba-sp-model": the packaged thegraphicsgeek SP is chosen explicitly;
    // anything else keeps the local NeilVFX profile when it is installed and valid.
    const char *sp_choice=getenv("SLOT_GBA_SP");
    if(sp_choice&&!strcmp(sp_choice,"graphicsgeek"))return 0;
    char root[PATH_CAP],path[PATH_CAP];
    if(snprintf(root,sizeof(root),"%s/local-models",assets)>=(int)sizeof(root))return 0;
    if(snprintf(path,sizeof(path),"%s/consoles/gba/model.pose",root)>=(int)sizeof(path))return 0;
    FILE *f=fopen(path,"rb");if(!f)return 0;
    char magic[8];float values[16];uint64_t hash=0;
    int valid=fread(magic,1,8,f)==8&&!memcmp(magic,"SCLCD001",8)
        &&fread(values,sizeof(float),16,f)==16&&fread(&hash,sizeof(hash),1,f)==1&&fgetc(f)==EOF;
    fclose(f);
    for(int i=0;valid&&i<16;i++)if(!isfinite(values[i])||fabsf(values[i])>1000)valid=0;
    if(!valid||values[3]<1.5f||values[3]>3.2f)return 0;
    ConsoleMesh local={0};
    if(!console_mesh_load(&local,root,model))return 0;
    uint64_t geometry=UINT64_C(14695981039346656037);
    for(unsigned i=0;i<local.vertex_count;i++)for(int j=0;j<24;j++)
        geometry=(geometry^((const unsigned char*)(local.vertices+i))[j])*UINT64_C(1099511628211);
    if(hash!=geometry){console_mesh_close(&local);return 0;}
    console_mesh_close(&s->cartridge.mesh);s->cartridge.mesh=local;
    memcpy(s->registration,values,sizeof(values));s->local=true;
    log_event("Local user-supplied GBA SP profile loaded");return 1;
}

int slot_native_lcd(SlotNative *s,int screen,int corner,float result[2]) {
    if(!s||!s->local||screen!=0||corner<0||corner>3)return 0;
    slot_native_project(s,s->registration+4+corner*3,1,result);return 1;
}

void slot_native_raster_size(int *width,int *height){*width=WIDTH*SLOT_RASTER_SCALE;*height=HEIGHT*SLOT_RASTER_SCALE;}

static void slot_camera(SlotNative *s,float progress);
unsigned slot_native_browse(SlotNative *s) {
    if(!s)return 0;
    slot_camera(s,0);SDL_GL_MakeCurrent(s->window,s->context);
    SDL_SetRenderTarget(s->renderer,s->target);
    SDL_SetRenderDrawColor(s->renderer,0,0,0,0);SDL_RenderClear(s->renderer);
    const int kind=s->console->kind;
    const double yaw=(kind==0||kind==2||kind==6?SLOT_HOME_YAW_DEGREES:kind==1?-12:kind==5?-14:-8)*PSX_PI/180;
    float matrix[16];console_matrix(matrix,yaw,kind==1||kind==5?-PSX_PHI:0);
    console_mesh_draw(&s->cartridge.mesh,s->renderer,matrix,240,false,true);
    if(handheld_has_lid(s->console->name))handheld_lid_draw(&s->cartridge.mesh,s->renderer,s->console->name,matrix,240,0,0);
    else console_mesh_draw(&s->cartridge.mesh,s->renderer,matrix,240,true,false);
    SDL_RenderFlush(s->renderer);
    void (GL_APIENTRY *finish)(void)=SDL_GL_GetProcAddress("glFinish");finish();
    SDL_GL_MakeCurrent(s->window,s->owner);return s->texture;
}

static void slot_camera(SlotNative *s,float progress) {
    slot_registration(s);
    float native[16],target[16],camera[16]={0};
    int kind=s->console->kind;
    const int home=kind==0||kind==2||kind==6;
    double yaw=kind==1||kind==4?168:kind==5?166:home?SLOT_HOME_YAW_DEGREES:SLOT_STANDARD_YAW_DEGREES;
    double lean=kind==1||kind==5?-PSX_PHI:kind==4?-15*PSX_PI/180:0;
    console_matrix(native,yaw*PSX_PI/180,lean);
    double target_lean=kind==1||kind==5?-PSX_PHI:kind==3?slot_model_angle-PSX_PI/2-PSX_PHI:kind==4?PSX_PI/2-PSX_PHI:0;
    // Home consoles rotate about physical up. Handhelds retain their existing LCD reading pose.
    if(home)console_matrix(target,SLOT_HOME_YAW,0);
    else console_matrix_turn(target,SLOT_STANDARD_YAW,target_lean);
    for(int c=0;c<3;c++)for(int r=0;r<3;r++)for(int k=0;k<3;k++)camera[c*4+r]+=target[k*4+r]*native[k*4+c];
    double angle=acos(fmax(-1,fmin(1,(camera[0]+camera[5]+camera[10]-1)/2)));
    double axis[]={camera[6]-camera[9],camera[8]-camera[2],camera[1]-camera[4]};
    double length=sqrt(axis[0]*axis[0]+axis[1]*axis[1]+axis[2]*axis[2]);
    memset(slot_camera_matrix,0,sizeof(slot_camera_matrix));slot_camera_matrix[15]=1;
    if(length<1e-6||progress<=0){slot_camera_matrix[0]=slot_camera_matrix[5]=slot_camera_matrix[10]=1;return;}
    for(int i=0;i<3;i++)axis[i]/=length;
    double a=angle*psx_ease(progress),c=cos(a),v=1-c,si=sin(a);
    for(int col=0;col<3;col++)for(int row=0;row<3;row++)slot_camera_matrix[col*4+row]=(row==col?c:0)+axis[row]*axis[col]*v;
    slot_camera_matrix[1]+=axis[2]*si;slot_camera_matrix[4]-=axis[2]*si;
    slot_camera_matrix[2]-=axis[1]*si;slot_camera_matrix[8]+=axis[1]*si;
    slot_camera_matrix[6]+=axis[0]*si;slot_camera_matrix[9]-=axis[0]*si;
}

float slot_native_origin(SlotNative *s){return s&&s->console->kind==6?s->console->origin:s&&s->console->kind==4?326:s&&s->console->kind==2?180:240;}
void slot_native_optical_close(SlotNative *s,float closed){if(s)s->optical_close=clamp(closed);}
void slot_native_project(SlotNative *s,const float point[3],int lid,float result[2]) {
    PsxVec p={point[0],point[1],point[2]};int kind=s->console->kind;
    if(lid && kind==4) {
        PsxVec hinge={ds_lid_hinge[0],ds_lid_hinge[1],ds_lid_hinge[2]};
        p=psx_add(hinge,console_rotate(psx_add(p,psx_mul(hinge,-1)),0,-(PSX_PI-ds_lid_open_radians)));
    }
    double yaw=(kind==1||kind==4?168:kind==5?166:kind==0||kind==2||kind==6?SLOT_HOME_YAW_DEGREES:SLOT_STANDARD_YAW_DEGREES)*PSX_PI/180;
    double lean=kind==1||kind==5?-PSX_PHI:kind==4?-15*PSX_PI/180:0;
    p=console_rotate(p,yaw,lean);slot_camera(s,1);
    SDL_FPoint projected=psx_project(p,slot_native_origin(s));result[0]=projected.x;result[1]=projected.y;
}
unsigned slot_native_present(SlotNative *s,float progress) {
    if(!s)return 0;
    s->presenting=true;s->presentation=clamp(progress);slot_camera(s,progress);
    slot_presenting=1;slot_presentation=progress;slot_view_origin=slot_native_origin(s);
    unsigned result=slot_native_frame(s,1,1);s->presenting=false;slot_presenting=0;return result;
}
// Floor contact of a home console in the presentation pose (native 720 x 480 raster pixels): the
// projected centre of its footprint and the extent of the projected footprint, so the frontend can
// stand a TV on the same floor line and draw matching contact shadows.
int slot_native_ground(SlotNative *s,float centre[2],float extent[2]) {
    if(!s||!s->console||s->local)return 0;
    const ConsoleMesh *m=&s->cartridge.mesh;
    if(!m->has_footprint)return 0;
    const float floor=m->floor_y,left=m->footprint[0],right=m->footprint[1],near=m->footprint[2],far=m->footprint[3];
    const float middle[3]={(left+right)/2,floor,(near+far)/2};
    slot_native_project(s,middle,0,centre);
    float lo[2]={1e9f,1e9f},hi[2]={-1e9f,-1e9f};
    for(int i=0;i<4;i++){
        const float corner[3]={i&1?right:left,floor,i&2?far:near};float point[2];
        slot_native_project(s,corner,0,point);
        for(int k=0;k<2;k++){if(point[k]<lo[k])lo[k]=point[k];if(point[k]>hi[k])hi[k]=point[k];}
    }
    extent[0]=hi[0]-lo[0];extent[1]=hi[1]-lo[1];
    return 1;
}
// Visible front base edge, including any housing overhang ahead of the feet. The footprint
// centre separately anchors its shadow; centres do not align devices of different depths.
int slot_native_contact(SlotNative *s,float front[2]) {
    if(!s||!s->cartridge.mesh.has_footprint)return 0;
    slot_native_project(s,s->cartridge.mesh.front_contact,0,front);
    return 1;
}
int slot_native_bounds(SlotNative *s,float bounds[4]) {
    if(!s)return 0;
    SDL_GL_MakeCurrent(s->window,s->context);
    const int w=WIDTH*SLOT_RASTER_SCALE,h=HEIGHT*SLOT_RASTER_SCALE;
    SDL_Surface *pixels=SDL_CreateRGBSurfaceWithFormat(0,w,h,32,SDL_PIXELFORMAT_RGBA32);
    int left=w,top=h,right=0,bottom=0;
    if(pixels&&!SDL_RenderReadPixels(s->renderer,NULL,SDL_PIXELFORMAT_RGBA32,pixels->pixels,pixels->pitch))
        for(int y=0;y<h;y++)for(int x=0;x<w;x++)if(((Uint8*)pixels->pixels)[y*pixels->pitch+x*4+3]>20){
            if(x<left)left=x;
            if(y<top)top=y;
            if(x+1>right)right=x+1;
            if(y+1>bottom)bottom=y+1;
        }
    if(pixels)SDL_FreeSurface(pixels);SDL_GL_MakeCurrent(s->window,s->owner);
    bounds[0]=(float)left/SLOT_RASTER_SCALE;bounds[1]=(float)top/SLOT_RASTER_SCALE;
    bounds[2]=(float)(right-left)/SLOT_RASTER_SCALE;bounds[3]=(float)(bottom-top)/SLOT_RASTER_SCALE;
    return bounds[2]>0&&bounds[3]>0;
}

int slot_native_prefetch(const char *assets,const char *model) {
    int housing=console_albedo_warm(assets,model);if(housing==0)return 0;
    const char *choice=getenv("SLOT_SNES_CARTRIDGE");
    const char *part=choice&&!strcmp(choice,"tzakol")&&(!strcmp(model,"snes")||!strcmp(model,"snes-us"))?"media-tzakol":"media";
    int cartridge=console_albedo_warm_part(assets,model,part);
    return cartridge==0?0:housing==1||cartridge==1?1:-1;
}

float slot_native_duration(const char *model,int inserting) {
    if(!strcmp(model,"psx")||!strcmp(model,"dreamcast"))return inserting?1.05f:2.10f;
    if(!strcmp(model,"gb")||!strcmp(model,"gbc")||!strcmp(model,"nds")||!strcmp(model,"psp"))return inserting?1.95f:2.10f;
    if(!strcmp(model,"nes"))return inserting?1.30f:2.10f;
    return inserting?1.25f:2.10f;
}

void slot_native_close(SlotNative *s) {
    if(!s)return;
    if(s->context)SDL_GL_MakeCurrent(s->window,s->context);
    console_mesh_close(&s->cartridge.disc_mesh);console_mesh_close(&s->cartridge.media_mesh);console_mesh_close(&s->cartridge.mesh);
    SDL_Texture *textures[]={s->face,s->target,s->cartridge.body,s->cartridge.rear,s->disc.disc,s->disc.underside};
    for(unsigned i=0;i<sizeof(textures)/sizeof(textures[0]);i++)if(textures[i])SDL_DestroyTexture(textures[i]);
    if(s->renderer)SDL_DestroyRenderer(s->renderer);
    SDL_GL_MakeCurrent(s->window,s->owner);
    free(s);
}

SlotNative *slot_native_open(SDL_Window *window,const char *assets,const char *rom,
                            const char *model,const char *face,const char *style,const char *colour) {
    SlotNative *s=calloc(1,sizeof(*s));if(!s)return NULL;
    s->window=window;s->owner=SDL_GL_GetCurrentContext();
    for(unsigned i=0;i<sizeof(console_specs)/sizeof(console_specs[0]);i++)if(!strcmp(model,console_specs[i].name))s->console=&console_specs[i];
    const char *family=!strcmp(model,"md")||!strcmp(model,"md-jp")?"megadrive":!strcmp(model,"snes-us")?"snes":model;
    for(unsigned i=0;i<sizeof(media)/sizeof(media[0]);i++)if(!strcmp(family,media[i].system))s->shape=&media[i];
    if(!s->console||!s->shape)goto failed;
    setenv("SLOT_MODEL_STYLE",style,1);setenv("SLOT_CONSOLE_COLOR",colour,1);
    SDL_GL_SetAttribute(SDL_GL_SHARE_WITH_CURRENT_CONTEXT,1);
    int driver=-1;
    for(int i=0;i<SDL_GetNumRenderDrivers();i++){SDL_RendererInfo info={0};SDL_GetRenderDriverInfo(i,&info);if(info.name&&!strcmp(info.name,"opengles2"))driver=i;}
    if(driver<0)goto failed;
    s->renderer=SDL_CreateRenderer(window,driver,SDL_RENDERER_ACCELERATED|SDL_RENDERER_TARGETTEXTURE);
    SDL_GL_SetAttribute(SDL_GL_SHARE_WITH_CURRENT_CONTEXT,0);
    if(!s->renderer)goto failed;
    s->context=SDL_GL_GetCurrentContext();
    s->target=SDL_CreateTexture(s->renderer,SDL_PIXELFORMAT_RGBA8888,SDL_TEXTUREACCESS_TARGET,WIDTH*SLOT_RASTER_SCALE,HEIGHT*SLOT_RASTER_SCALE);
    if(!s->target||SDL_SetRenderTarget(s->renderer,s->target))goto failed;
    SDL_RenderSetScale(s->renderer,SLOT_RASTER_SCALE,SLOT_RASTER_SCALE);
    SDL_SetTextureScaleMode(s->target,SDL_ScaleModeLinear);
    SDL_SetTextureBlendMode(s->target,SDL_BLENDMODE_BLEND);
    SDL_Surface *surface=load_surface(assets,face);
    if(!surface)surface=load_surface(assets,s->shape->shell);
    if(!surface)goto failed;
    cartridge_outline(&s->cartridge,surface,s->console->colour);
    bool disc=!strcmp(model,"psx")||!strcmp(model,"dreamcast")||!strcmp(model,"psp");
    if(!console_mesh_load(&s->cartridge.mesh,assets,model)) {SDL_FreeSurface(surface);goto failed;}
    slot_local(s,assets,model);
    const char *part=!strcmp(model,"gbc")&&s->cartridge.notched?"gb":model;
    if(!strcmp(part,"gb")||!strcmp(part,"gbc")||!strcmp(part,"gba"))
        s->cartridge.dmg_media=!strcmp(model,"gbc")&&!strcmp(part,"gb");
    if(!strcmp(part,"gb")||!strcmp(part,"gbc")||!strcmp(part,"gba"))console_mesh_load_part(&s->cartridge.media_mesh,assets,part,"media");
    const ExemplarShelf *shelf=exemplar_shelf_for(part);
    if(shelf)cartridge_sample_plastic(&s->cartridge,surface,shelf->sample,shelf->canvas);
    cartridge_media_colour(&s->cartridge,model);
    if(!disc)cartridge_media_prepare(&s->cartridge,assets,s->console,surface);
    s->face=take_texture(s->renderer,&surface);
    char path[PATH_CAP];snprintf(path,sizeof(path),"consoles/%s/body.tga",model);
    s->cartridge.body=load_texture(s->renderer,assets,path);
    if(!strcmp(model,"nds"))s->cartridge.rear=load_texture(s->renderer,assets,"shapes/nds/rear.png");
    if(disc){
        const char *name=strrchr(rom,'/');name=name?name+1:rom;const char *ext=strrchr(name,'.');
        snprintf(path,sizeof(path),"%.*smedia/slotcarts/%.*s.disc.tga",(int)(name-rom),rom,(int)(ext?ext-name:strlen(name)),name);
        s->disc.disc=load_texture(s->renderer,assets,path);
        if(!s->disc.disc){snprintf(path,sizeof(path),"shells/%s.disc.tga",family);s->disc.disc=load_texture(s->renderer,assets,path);}
        snprintf(path,sizeof(path),"shapes/%s/underside.tga",family);s->disc.underside=load_texture(s->renderer,assets,path);
        if(!s->disc.disc||!s->disc.underside)goto failed;
    }
    if(!s->face||!s->cartridge.body||!console_mesh_open(&s->cartridge.mesh,s->renderer))goto failed;
    if(s->console->kind==6)optical_disc_prepare(&s->cartridge.disc_mesh,s->renderer);
    if(s->cartridge.media_mesh.vertices&&!console_mesh_open(&s->cartridge.media_mesh,s->renderer))goto failed;
    SDL_GL_BindTexture(s->target,NULL,NULL);
    void (GL_APIENTRY *get)(GLenum,GLint*)=SDL_GL_GetProcAddress("glGetIntegerv");
    GLint texture=0;get(GL_TEXTURE_BINDING_2D,&texture);s->texture=(unsigned)texture;
    SDL_GL_UnbindTexture(s->target);
    SDL_GL_MakeCurrent(window,s->owner);
    GLboolean (GL_APIENTRY *isTexture)(GLuint)=SDL_GL_GetProcAddress("glIsTexture");
    if(!s->texture||!isTexture(s->texture))goto failed;
    return s;
failed:
    fprintf(stderr,"Slot native scene unavailable: %s\n",SDL_GetError());
    SDL_GL_SetAttribute(SDL_GL_SHARE_WITH_CURRENT_CONTEXT,0);slot_native_close(s);return NULL;
}

unsigned slot_native_frame(SlotNative *s,float progress,int inserting) {
    if(!s)return 0;
    if(!s->presenting)slot_camera(s,0);
    SDL_GL_MakeCurrent(s->window,s->context);
    const ConsoleSpec *c=s->console;
    bool disc=c->kind==6,umd=c->kind==5;
    double motion=disc?(inserting?.95:1.75):inserting?(c->kind==1||c->kind==4||umd?1.85:c->kind==2?1.20:1.15):1.75;
    double elapsed=clamp(progress)*slot_native_duration(c->name,inserting);
    double seat=clamp(elapsed/motion),lift=0,lid=-1,spin=0;
    if(!inserting){
        seat=1-seat;
        double unseat=disc?.85:c->kind==0||c->kind==3?.60:0;
        double scene=disc?.66:.78;
        if(unseat>0){
            seat=elapsed<unseat?(disc?.67:scene):scene*(1-clamp((elapsed-unseat)/(motion-unseat)));
            if(disc){if(elapsed<unseat)lid=spring((elapsed-.08)/.50);spin=2*PSX_PI*(1-pow(1-clamp(elapsed/.80),2));}
            else {lift=(c->kind==3?.30:.22)*spring((elapsed-.10)/.45);if(c->kind==3&&elapsed<unseat)lid=psx_ease((elapsed-.04)/.50);}
        }
        if(c->kind==4&&elapsed<.60)lid=psx_ease((elapsed-.04)/.50);
    }
    if(s->presenting && (c->kind==3 || c->kind==4))lid=psx_ease(s->presentation);
    if(disc)lid=s->presenting?1-s->optical_close:inserting?psx_ease(seat/.22):1;
    SDL_SetRenderTarget(s->renderer,s->target);
    SDL_SetRenderDrawColor(s->renderer,0,0,0,0);SDL_RenderClear(s->renderer);
    SDL_SetRenderDrawBlendMode(s->renderer,SDL_BLENDMODE_BLEND);
    if(umd)psp_scene(s->renderer,&s->cartridge,&s->disc,c,seat);
    else if(disc)ps1_scene(s->renderer,&s->cartridge,&s->disc,c,seat,!inserting,lid,spin);
    else cartridge_scene(s->renderer,&s->cartridge,s->face,c,s->shape->width,s->shape->height,s->shape->foot,seat,lift,lid);
    SDL_RenderFlush(s->renderer);
    // Mali needs completion before another context samples the shared target.
    void (GL_APIENTRY *finish)(void)=SDL_GL_GetProcAddress("glFinish");finish();
    SDL_GL_MakeCurrent(s->window,s->owner);
    return s->texture;
}
