/* Offline native GLES mechanical-pose capture, Slotters, MIT.
 * Includes the real renderer/scenes. main() below does not call animate(),
 * hooks, framebuffers, audio, ION or any device/display-layer entry point. */
#ifndef SLOT_HELPER_SOURCE
#define SLOT_HELPER_SOURCE "../slotlaunch/slot-launch.c"
#endif
#define main slot_application_main
#include SLOT_HELPER_SOURCE
#undef main
extern int IMG_SavePNG(SDL_Surface *surface,const char *file);

static bool dmg_clip_check(SDL_Surface *pixels,const ConsoleSpec *s,const char *out)
{
    // Independent N3 rear-opening anchor, not the runtime's clipping value.
    bool cgb=!strcmp(s->name,"gbc");
    const double q=cgb?168.0/78:168.0/90,yaw=168*PSX_PI/180;
    const double lip=cgb?33.4:45.5,depth=cgb?-6.5:-13;
    PsxVec a=console_rotate((PsxVec){-28.5*q,lip*q,depth*q},yaw,-PSX_PHI);
    PsxVec b=console_rotate((PsxVec){28.5*q,lip*q,depth*q},yaw,-PSX_PHI);
    SDL_FPoint pa=psx_project(a,s->origin),pb=psx_project(b,s->origin);
    unsigned green=0,leaks=0;
    for(int y=0;y<HEIGHT;y++)for(int x=0;x<WIDTH;x++){
        Uint8 *p=(Uint8 *)pixels->pixels+y*pixels->pitch+x*4;
        if(p[0]>20||p[1]<240||p[2]<70||p[2]>130)continue;
        green++;
        double edge=pa.y+(pb.y-pa.y)*(x+.5-pa.x)/(pb.x-pa.x);
        if(y+.5>edge+1)leaks++;
    }
    char file[PATH_CAP];snprintf(file,sizeof(file),"%s/clip-check.json",out);
    FILE *f=fopen(file,"w");if(!f)return false;
    fprintf(f,"{\"visible_green_pixels\":%u,\"pixels_below_lip\":%u,\"lip_mm\":%.1f,\"tolerance_px\":1}\n",green,leaks,lip);
    fclose(f);
    fprintf(stderr,"DMG seated diagnostic: %u green, %u below lip\n",green,leaks);
    return green>300&&leaks==0;
}

#ifdef SLOT_CARTRIDGE_MEDIA
static unsigned green_pixels(SDL_Surface *pixels,const ConsoleSpec *s,const MediaSpec *ms,unsigned *below)
{
    // Independent entry line: the deck plane at the physical shell's front face,
    // rotated with the seated console. Not the renderer's clip value.
    PsxVec a={-200,s->entry,s->slot+ms->v[MEDIA_T]*ms->v[MEDIA_Q]/2},b={200,a.y,a.z};
    double yaw=-22*PSX_PI/180;
    SDL_FPoint pa=psx_project(console_rotate(a,yaw,0),s->origin),pb=psx_project(console_rotate(b,yaw,0),s->origin);
    unsigned green=0;*below=0;
    for(int y=0;y<HEIGHT;y++)for(int x=0;x<WIDTH;x++){
        Uint8 *p=(Uint8 *)pixels->pixels+y*pixels->pitch+x*4;
        if(p[0]>20||p[1]<240||p[2]<70||p[2]>130)continue;
        green++;
        double edge=pa.y+(pb.y-pa.y)*(x+.5-pa.x)/(pb.x-pa.x);
        if(s->kind==0&&y+.5>edge+1)(*below)++;
    }
    return green;
}
#endif

#ifdef SLOT_CARTRIDGE_MEDIA
/* The shelf face is the 3D hero pose: render only the media at seat 0 with 4x4
 * sub-pixel jitter (smooth silhouettes), no label; a green probe then measures
 * the label rectangle. Writes hero.png (canvas crop, RGBA) and hero.json. */
static int hero_capture(SDL_Renderer *r,CartridgeArt *art,const ConsoleSpec *s,const char *system,const char *out)
{
    const Media *m=NULL;
    for(size_t i=0;i<sizeof(media)/sizeof(media[0]);i++)if(!strcmp(media[i].system,system))m=&media[i];
    if(!m||!art->media_mesh.ready){fprintf(stderr,"hero: media mesh missing\n");return 1;}
    SDL_Rect crop={(WIDTH-m->width)/2,m->foot-m->height,m->width,m->height};
    SDL_Surface *pixels=SDL_CreateRGBSurfaceWithFormat(0,WIDTH,HEIGHT,32,SDL_PIXELFORMAT_RGBA32);
    SDL_Surface *result=SDL_CreateRGBSurfaceWithFormat(0,crop.w,crop.h,32,SDL_PIXELFORMAT_RGBA32);
    double *sum=calloc((size_t)crop.w*crop.h*4,sizeof(double));
    if(!pixels||!result||!sum)return 1;
    cartridge_media_only=true;
    bool authored=art->media_mesh.media_tinted;
    for(int pass=0;pass<(authored?2:1);pass++){
    memset(sum,0,(size_t)crop.w*crop.h*4*sizeof(double));
    if(pass)for(int c=0;c<3;c++)art->media_mesh.media_tint[c]=0;
    for(int j=0;j<4;j++)for(int i=0;i<4;i++){
        cartridge_jitter[0]=(i+.5)/4-.5;cartridge_jitter[1]=(j+.5)/4-.5;
        SDL_SetRenderDrawColor(r,0,0,0,0);SDL_RenderClear(r);
        cartridge_scene(r,art,NULL,s,m->width,m->height,m->foot,0,0,-1);
        SDL_RenderFlush(r);
        if(SDL_RenderReadPixels(r,NULL,SDL_PIXELFORMAT_RGBA32,pixels->pixels,pixels->pitch))return 1;
        for(int y=0;y<crop.h;y++)for(int x=0;x<crop.w;x++){
            Uint8 *p=(Uint8 *)pixels->pixels+(y+crop.y)*pixels->pitch+(x+crop.x)*4;
            double a=p[3]/255.0,*q=sum+((size_t)y*crop.w+x)*4;
            for(int c=0;c<3;c++)q[c]+=p[c]*a;
            q[3]+=a;
        }
    }
    for(int y=0;y<crop.h;y++)for(int x=0;x<crop.w;x++){
        double *q=sum+((size_t)y*crop.w+x)*4;Uint8 *p=(Uint8 *)result->pixels+y*result->pitch+x*4;
        for(int c=0;c<3;c++)p[c]=(Uint8)lround(q[3]>0?q[c]/q[3]:0);
        p[3]=(Uint8)lround(q[3]/16*255);
    }
    char file[PATH_CAP];snprintf(file,sizeof(file),"%s/hero%s.png",out,pass?"-fixed":"");
    if(IMG_SavePNG(result,file))return 1;
    }
    if(authored)for(int c=0;c<3;c++)art->media_mesh.media_tint[c]=128/255.f;
    // Label probe: a solid green face at the unjittered pose.
    cartridge_jitter[0]=cartridge_jitter[1]=0;
    SDL_Surface *marker=SDL_CreateRGBSurfaceWithFormat(0,64,64,32,SDL_PIXELFORMAT_RGBA32);
    SDL_FillRect(marker,NULL,SDL_MapRGBA(marker->format,0,255,96,255));
    SDL_Texture *green=SDL_CreateTextureFromSurface(r,marker);SDL_FreeSurface(marker);
    SDL_SetRenderDrawColor(r,0,0,0,0);SDL_RenderClear(r);
    cartridge_scene(r,art,green,s,m->width,m->height,m->foot,0,0,-1);SDL_RenderFlush(r);
    if(SDL_RenderReadPixels(r,NULL,SDL_PIXELFORMAT_RGBA32,pixels->pixels,pixels->pitch))return 1;
    int x0=crop.w,y0=crop.h,x1=-1,y1=-1;
    for(int y=0;y<crop.h;y++)for(int x=0;x<crop.w;x++){
        Uint8 *p=(Uint8 *)pixels->pixels+(y+crop.y)*pixels->pitch+(x+crop.x)*4;
        if(p[0]<20&&p[1]>240&&p[2]>70&&p[2]<130){if(x<x0)x0=x;if(y<y0)y0=y;if(x>x1)x1=x;if(y>y1)y1=y;}
        Uint8 *q=(Uint8 *)result->pixels+y*result->pitch+x*4;
        q[0]=q[1]=q[2]=255;q[3]=(p[0]<20&&p[1]>240&&p[2]>70&&p[2]<130)?255:0;
    }
    char file[PATH_CAP];snprintf(file,sizeof(file),"%s/hero.json",out);
    FILE *f=fopen(file,"w");if(!f)return 1;
    fprintf(f,"{\"canvas\":[%d,%d],\"label\":[%d,%d,%d,%d]}\n",crop.w,crop.h,x0,y0,x1+1,y1+1);fclose(f);
    snprintf(file,sizeof(file),"%s/hero-label.png",out);if(IMG_SavePNG(result,file))return 1;
    fprintf(stderr,"hero %s: label %d,%d,%d,%d\n",system,x0,y0,x1+1,y1+1);
    free(sum);SDL_FreeSurface(pixels);SDL_FreeSurface(result);SDL_DestroyTexture(green);
    return 0;
}
#endif

int main(int argc,char **argv)
{
    if(argc<5||argc>7){fprintf(stderr,"usage: offline-preview SYSTEM ASSETS OUTPUT_DIR insert|eject|hero [shell=NAME] [diagnostic|compatible|timed]\n");return 2;}
    const char *system=argv[1],*assets=argv[2],*out=argv[3];
    state_dir=out;process_start=now();
    const ConsoleSpec *s=console_spec(system,"");if(!s)return 2;
    bool insert=!strcmp(argv[4],"insert"),hero=!strcmp(argv[4],"hero");
    (void)hero; /* Unused when building a receiving branch's baseline. */
    bool diagnostic=false,compatible=false,timed=false,first=false;const char *shell=NULL;
    for(int i=5;i<argc;i++){
        if(!strcmp(argv[i],"diagnostic"))diagnostic=true;
        else if(!strcmp(argv[i],"timed"))timed=true;
        else if(!strcmp(argv[i],"first"))first=true;
        else if(!strcmp(argv[i],"compatible")&&!strcmp(system,"gbc"))compatible=true;
        // A regional/EA shelf shell selects its physical shell, as a baked face does.
        else if(!strncmp(argv[i],"shell=",6))shell=argv[i]+6;
    }
    if(!shell)shell=compatible?"gb":system;
    // Shelf media table names for the console folders.
    const char *media_system=!strcmp(system,"snes-us")?"snes":!strcmp(system,"md")||!strcmp(system,"md-jp")?"megadrive":system;
    SDL_SetHint(SDL_HINT_RENDER_DRIVER,"opengles2");
    if(SDL_Init(SDL_INIT_VIDEO)){fprintf(stderr,"SDL: %s\n",SDL_GetError());return 1;}
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_ES);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,2);SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,0);
    SDL_Window *w=SDL_CreateWindow("Slotters offline",0,0,WIDTH,HEIGHT,SDL_WINDOW_HIDDEN);
    int driver=-1;
    for(int i=0;i<SDL_GetNumRenderDrivers();i++){SDL_RendererInfo candidate={0};SDL_GetRenderDriverInfo(i,&candidate);if(candidate.name&&!strcmp(candidate.name,"opengles2"))driver=i;}
    SDL_Renderer *r=w&&driver>=0?SDL_CreateRenderer(w,driver,SDL_RENDERER_ACCELERATED|SDL_RENDERER_TARGETTEXTURE):NULL;
    if(!r){fprintf(stderr,"renderer: %s\n",SDL_GetError());return 1;}
    SDL_RendererInfo info={0};SDL_GetRendererInfo(r,&info);fprintf(stderr,"renderer: %s\n",info.name?info.name:"missing");
    SDL_Texture *scene=SDL_CreateTexture(r,SDL_PIXELFORMAT_RGBA8888,SDL_TEXTUREACCESS_TARGET,WIDTH,HEIGHT);
    SDL_SetRenderTarget(r,scene);
    CartridgeArt model={0};PsxArt optical={0};
    if(!console_mesh_load(&model.mesh,assets,system)){fprintf(stderr,"mesh load failed: %s/%s\n",assets,system);return 1;}
    if(!console_mesh_open(&model.mesh,r)){fprintf(stderr,"mesh GLES setup failed: %s\n",SDL_GetError());return 1;}
#ifdef SLOT_AUTHORED_MEDIA
    if(!compatible&&(!strcmp(system,"gb")||!strcmp(system,"gbc")||!strcmp(system,"gba")))
        console_mesh_load_part(&model.media_mesh,assets,system,"media");
#ifdef SLOT_CARTRIDGE_MEDIA
    if(compatible)model.dmg_media=console_mesh_load_part(&model.media_mesh,assets,"gb","media");
#endif
#endif
    char file[PATH_CAP];snprintf(file,sizeof(file),"consoles/%s/body.png",system);
    model.body=load_texture(r,assets,file);
    snprintf(file,sizeof(file),"shells/%s.png",shell);
    SDL_Surface *flat=load_surface(assets,file);
    cartridge_outline(&model,flat,s->colour);
#ifdef SLOT_CARTRIDGE_MEDIA
    // The shelf-hero capture uses neutral plastic: the baker tints per game.
    if(hero)model.plastic=(SDL_Color){128,128,128,255};
    else{
        const ExemplarShelf *shelf=exemplar_shelf_for(model.dmg_media?"gb":system);
        if(shelf&&model.media_mesh.vertices)cartridge_sample_plastic(&model,flat,shelf->sample,shelf->canvas);
    }
    cartridge_media_prepare(&model,assets,s,hero?NULL:flat);
    if(model.media)fprintf(stderr,"physical media: %s/%s (%s)\n",model.media->folder,model.media->part,model.media->name);
#endif
    SDL_FreeSurface(flat);
#ifdef SLOT_NEXT_MEDIA
    cartridge_media_colour(&model,system);
#endif
#ifdef SLOT_AUTHORED_MEDIA
    if(model.media_mesh.vertices)console_mesh_open(&model.media_mesh,r);
#endif
    SDL_Texture *face=load_texture(r,assets,file);
    if(diagnostic){
        SDL_Surface *marker=SDL_CreateRGBSurfaceWithFormat(0,s->kind==6?512:312,s->kind==6?512:337,32,SDL_PIXELFORMAT_RGBA32);
        if(!marker)return 1;
        SDL_FillRect(marker,NULL,SDL_MapRGBA(marker->format,0,255,96,255));
        if(s->kind==6)for(int y=0;y<512;y++)for(int x=0;x<512;x++){
            double radius=hypot(x+.5-256,y+.5-256);
            if(radius<32||radius>256)((Uint32 *)((Uint8 *)marker->pixels+y*marker->pitch))[x]=0;
        }
        SDL_DestroyTexture(face);face=SDL_CreateTextureFromSurface(r,marker);SDL_FreeSurface(marker);
    }
    if(s->kind==5||s->kind==6){
        snprintf(file,sizeof(file),"shells/%s.disc.tga",system);optical.disc=load_texture(r,assets,file);
        snprintf(file,sizeof(file),"shapes/%s/underside.tga",system);optical.underside=load_texture(r,assets,file);
        if(diagnostic&&s->kind==6){SDL_DestroyTexture(optical.disc);optical.disc=face;}
    }
    if(!face||((s->kind==5||s->kind==6)&&(!optical.disc||!optical.underside))){fprintf(stderr,"media load: %s\n",SDL_GetError());return 1;}
    SDL_Surface *pixels=SDL_CreateRGBSurfaceWithFormat(0,WIDTH,HEIGHT,32,SDL_PIXELFORMAT_RGBA32);
#ifdef SLOT_CARTRIDGE_MEDIA
    if(hero)return hero_capture(r,&model,s,media_system,out);
#endif
#ifdef SLOT_NEXT_MEDIA
    unsigned ags_free_green=0;
#endif
    // 61 fixed samples include both mechanical endpoints. Elapsed values are
    // the production 1.85/1.75-second motion; the 0.10/0.35-second holds remain.
    for(int frame=0;frame<=60;frame++){
        double seat=frame/60.0;if(!insert)seat=1-seat;
        double timed_lift=0;
        if(timed&&s->kind==0){
            // Production home top-loader timing, including the existing eject
            // spring/hold override. Default output remains mechanical poses.
            double elapsed=frame/60.0*(insert?1.25:2.10);
            if(insert)seat=clamp(elapsed/1.15);
            else{
                seat=elapsed<.60?.78:.78*(1-clamp((elapsed-.60)/1.15));
                timed_lift=.22*spring((elapsed-.10)/.45);
            }
        }
        SDL_SetRenderDrawColor(r,22,24,28,255);SDL_RenderClear(r);
        SDL_SetRenderDrawBlendMode(r,SDL_BLENDMODE_BLEND);
        if(s->kind==5)psp_scene(r,&model,&optical,s,seat);
        else if(s->kind==6){
            double lid=-1,spin=0;
            if(timed&&!insert){
                double elapsed=frame/60.0*2.10;
                seat=elapsed<.85?.67:.66*(1-clamp((elapsed-.85)/.90));
                if(elapsed<.85)lid=spring((elapsed-.08)/.50);
                spin=2*PSX_PI*(1-pow(1-clamp(elapsed/.80),2));
            }
            ps1_scene(r,&model,&optical,s,seat,!insert,lid,spin);
        }
        else {
            const Media *m=NULL;
            for(size_t i=0;i<sizeof(media)/sizeof(media[0]);i++)if(!strcmp(media[i].system,media_system))m=&media[i];
            if(!m)return 2;
            double lift=timed_lift,lid_open=-1;
            if(!insert&&s->kind==3){
                double elapsed=frame/60.0*1.75;
                seat=elapsed<.60?.78:.78*(1-clamp((elapsed-.60)/1.15));
                lift=.30*spring((elapsed-.10)/.45);
                if(elapsed<.60)lid_open=psx_ease((elapsed-.04)/.50);
            }
            if(!insert&&s->kind==4){
                double elapsed=frame/60.0*1.75;
                if(elapsed<.60)lid_open=psx_ease((elapsed-.04)/.50);
            }
            cartridge_scene(r,&model,face,s,m->width,m->height,m->foot,seat,lift,lid_open);
        }
        SDL_RenderFlush(r);
        if(SDL_RenderReadPixels(r,NULL,SDL_PIXELFORMAT_RGBA32,pixels->pixels,pixels->pitch))return 1;
#ifdef SLOT_NEXT_MEDIA
        if(diagnostic&&insert&&!strcmp(system,"gba")&&(frame==0||frame==24)){
            unsigned green=0;
            for(int y=0;y<HEIGHT;y++)for(int x=0;x<WIDTH;x++){
                Uint8 *p=(Uint8 *)pixels->pixels+y*pixels->pitch+x*4;
                if(p[0]<20&&p[1]>240&&p[2]>70&&p[2]<130)green++;
            }
            if(frame==0)ags_free_green=green;
            else {
                // At .40 the Pak is aligned but still outside the front edge.
                // A label-up feed exposes green here; the manual requires it
                // underneath. The free label is a visible positive control.
                snprintf(file,sizeof(file),"%s/orientation-check.json",out);
                FILE *f=fopen(file,"w");if(!f)return 1;
                fprintf(f,"{\"free_label_pixels\":%u,\"aligned_label_pixels\":%u,\"label_faces_underside\":%s}\n",ags_free_green,green,green==0?"true":"false");fclose(f);
                if(ags_free_green<300||green!=0)return 1;
            }
        }
#endif
        if(diagnostic&&insert&&frame==60&&s->kind==1&&!dmg_clip_check(pixels,s,out))return 1;
#ifdef SLOT_CARTRIDGE_MEDIA
        if(diagnostic&&insert&&model.media&&(frame==0||frame==60)){
            static unsigned free_green;unsigned below=0,green=green_pixels(pixels,s,model.media,&below);
            if(frame==0)free_green=green;
            else{
                // Top-loaders keep a visible label above the deck; the NES Game
                // Pak is inside behind its closed door; the DS card is label-down.
                bool hidden=s->kind!=0,ok=free_green>300&&below==0&&(hidden?green==0:green>300);
                snprintf(file,sizeof(file),"%s/label-check.json",out);
                FILE *f=fopen(file,"w");if(!f)return 1;
                fprintf(f,"{\"variant\":\"%s\",\"free_label_pixels\":%u,\"seated_label_pixels\":%u,\"pixels_below_entry\":%u,\"seated_label_expected\":\"%s\",\"pass\":%s}\n",
                        model.media->name,free_green,green,below,hidden?"hidden":"visible above deck",ok?"true":"false");
                fclose(f);if(!ok)return 1;
            }
        }
#endif
        snprintf(file,sizeof(file),"%s/%s-%02d.png",out,argv[4],frame);
        if(IMG_SavePNG(pixels,file))return 1;
        double black=psx_ease((seat-.94)/.05);
        if(timed&&s->kind==0&&!insert)black=1-psx_ease((frame/60.0*2.10)/.063);
        if(black>0){SDL_SetRenderDrawColor(r,0,0,0,(Uint8)lround(255*black));SDL_RenderFillRect(r,NULL);}
        SDL_RenderFlush(r);
        if(SDL_RenderReadPixels(r,NULL,SDL_PIXELFORMAT_RGBA32,pixels->pixels,pixels->pitch))return 1;
        snprintf(file,sizeof(file),"%s/%s-scene-%02d.png",out,argv[4],frame);
        if(IMG_SavePNG(pixels,file))return 1;
        if(first)break; /* Fast shelf hand-off check; production scenes unchanged. */
    }
    if(timed&&s->kind==0){
        snprintf(file,sizeof(file),"%s/%s-timing.json",out,argv[4]);
        FILE *f=fopen(file,"w");if(!f)return 1;
        fprintf(f,"{\"motion_seconds\":%.2f,\"hold_seconds\":%.2f,\"duration_seconds\":%.2f,\"base_eject_seconds\":1.05,\"eject_unseat_seconds\":0.60,\"eject_release\":0.22,\"eject_fade_in_seconds\":0.063,\"samples\":61}\n",insert?1.15:1.75,insert?.10:.35,insert?1.25:2.10);
        fclose(f);
    }
    console_mesh_close(&model.disc_mesh);console_mesh_close(&model.mesh);
#ifdef SLOT_AUTHORED_MEDIA
    console_mesh_close(&model.media_mesh);
#endif
    SDL_FreeSurface(pixels);SDL_DestroyRenderer(r);SDL_DestroyWindow(w);SDL_Quit();
    return 0;
}
