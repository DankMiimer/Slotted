/* Original cartridge console scenes, copyright 2026, MIT.
 * Cel-shaded 3D housings and live media share the PS1 perspective camera.
 * Clip the media at the physical entry plane, never at the screen edge. */
#include "console-gl.h"
#include "n64-flaps.h"
#include "handheld-lids.h"
#include "exemplar-media.h"
#include "textured-data.h"
typedef struct {
    const char *name;
    int kind;
    double rx,ry,depth,slot,mouth,cart,sink,idle,origin,radius,yscale,entry;
    SDL_Color colour;
    SDL_Rect sprite;
} ConsoleSpec;
#include "console-specs.h"
/* Physical media for the remaining cartridge consoles (tools.consolebuild.media).
 * v: width, height, thickness mm; native units per mm; label centre x/y,
 * half width/height and label plane z in mm. Pixel boxes are on the shelf canvas. */
enum {MEDIA_W,MEDIA_H,MEDIA_T,MEDIA_Q,MEDIA_LX,MEDIA_LY,MEDIA_LW,MEDIA_LH,MEDIA_LZ,MEDIA_OZ};
typedef struct {
    const char *name,*folder,*part;
    double v[10];
    int well[4],canvas[2];
    double body[4];
    int sample[4];
} MediaSpec;
/* Shelf/hero contract of the licensed handheld Game Paks: canvas, body box,
 * label (recess) crop, physical W/H mm and a plain plastic sample box. */
typedef struct {
    const char *name;
    int canvas[2];
    double body[4];
    int label[4];
    double size[2];
    int sample[4];
} ExemplarShelf;
#include "media-specs.h"
typedef struct {
    SDL_Texture *body,*rear;
    ConsoleMesh mesh,media_mesh,disc_mesh;
    double outline[70][2];
    int count,rows;
    SDL_Color plastic;
    bool notched,dmg_media;
    const MediaSpec *media;
} CartridgeArt;

static const ConsoleSpec *console_spec(const char *system,const char *rom)
{
    const char *key=system;
    if(!strcmp(system,"snes")&&(strstr(rom,"(USA")||strstr(rom,"(Canada")))key="snes-us";
    if(!strcmp(system,"megadrive")||!strcmp(system,"genesis"))
        key=strstr(rom,"Japan")&&!strstr(rom,"USA")&&!strstr(rom,"Europe")?"md-jp":"md";
    for(size_t i=0;i<sizeof(console_specs)/sizeof(console_specs[0]);i++)
        if(!strcmp(key,console_specs[i].name))return &console_specs[i];
    return NULL;
}

static void cartridge_outline(CartridgeArt *art,SDL_Surface *source,SDL_Color fallback)
{
    art->plastic=fallback;
    SDL_Surface *s=source?SDL_ConvertSurfaceFormat(source,SDL_PIXELFORMAT_RGBA32,0):NULL;
    if(!s)return;
    SDL_LockSurface(s);
    int top=s->h,bottom=-1;
    for(int y=0;y<s->h;y++)for(int x=0;x<s->w;x++){
        Uint8 *p=(Uint8 *)s->pixels+y*s->pitch+x*4;
        if(p[3]>240){if(y<top)top=y;if(y>bottom)bottom=y;break;}
    }
    if(bottom>=top){
        double left[33][2],right[33][2];int rows=0;
        unsigned red=0,green=0,blue=0,samples=0;
        for(int i=0;i<33;i++){
            int y=top+(bottom-top)*i/32,a=s->w,b=-1;
            for(int x=0;x<s->w;x++){
                Uint8 *p=(Uint8 *)s->pixels+y*s->pitch+x*4;
                if(p[3]>240){if(x<a)a=x;if(x>b)b=x;}
            }
            if(b<a)continue;
            left[rows][0]=2.0*a/s->w-1;right[rows][0]=2.0*(b+1)/s->w-1;
            left[rows][1]=right[rows][1]=2.0*y/s->h-1;rows++;
            Uint8 *p=(Uint8 *)s->pixels+y*s->pitch+(a+(int)fmin(5,b-a))*4;
            red+=p[0];green+=p[1];blue+=p[2];samples++;
        }
        for(int i=0;i<rows;i++){art->outline[art->count][0]=left[i][0];art->outline[art->count++][1]=left[i][1];}
        for(int i=rows-1;i>=0;i--){art->outline[art->count][0]=right[i][0];art->outline[art->count++][1]=right[i][1];}
        /* The existing baked alpha contour preserves DMG-compatible switch
         * notches, including explicit user shell overrides and zipped ROMs. */
        if(rows>1)art->notched=fabs(left[1][0]+right[1][0])>.08;
        art->rows=rows;
        if(samples)art->plastic=(SDL_Color){red/samples,green/samples,blue/samples,255};
    }
    SDL_UnlockSurface(s);SDL_FreeSurface(s);
}

static double cartridge_row_width(const CartridgeArt *art,int i)
{
    return art->outline[2*art->rows-1-i][0]-art->outline[i][0];
}

/* The baked face's own alpha contour chooses the physical shell, as for the
 * CGB notch: US SNES has its raised top tab, the Japanese Mega Drive its
 * narrower lower edge between the grips, and EA its narrow, taller body. */
static const MediaSpec *cartridge_media_variant(const CartridgeArt *art,const ConsoleSpec *s)
{
    const char *key=s->name;
    if(art->rows>3){
        double widest=0;
        for(int i=0;i<art->rows;i++)widest=fmax(widest,cartridge_row_width(art,i));
        if(!strcmp(key,"snes")||!strcmp(key,"snes-us"))key=cartridge_row_width(art,1)<.85*widest?"snes-us":"snes";
        if(!strcmp(key,"md")||!strcmp(key,"md-jp"))
            key=widest<1.76?"md-ea":cartridge_row_width(art,art->rows-2)<.92*widest?"md-jp":"md";
    }
    const char *choice=getenv("SLOT_SNES_CARTRIDGE");
    if(choice&&!strcmp(choice,"tzakol")&&(!strcmp(s->name,"snes")||!strcmp(s->name,"snes-us")))
        key=!strcmp(s->name,"snes-us")?"snes-us-tzakol":"snes-tzakol";
    for(size_t i=0;i<sizeof(media_specs)/sizeof(media_specs[0]);i++)
        if(!strcmp(key,media_specs[i].name))return &media_specs[i];
    return NULL;
}

static bool media_colour_is(const float *c,const float *reference)
{
    return fabsf(c[0]-reference[0])<.005f&&fabsf(c[1]-reference[1])<.005f&&fabsf(c[2]-reference[2])<.005f;
}

/* Average plain plastic inside a shelf-canvas box of the baked face. */
static void cartridge_sample_plastic(CartridgeArt *art,SDL_Surface *face,const int *box,const int *canvas)
{
    SDL_Surface *rgba=face?SDL_ConvertSurfaceFormat(face,SDL_PIXELFORMAT_RGBA32,0):NULL;
    if(rgba&&rgba->w==canvas[0]&&rgba->h==canvas[1]){
        unsigned long red=0,green=0,blue=0,samples=0;
        SDL_LockSurface(rgba);
        for(int y=box[1];y<box[3];y++)for(int x=box[0];x<box[2];x++){
            Uint8 *p=(Uint8 *)rgba->pixels+y*rgba->pitch+x*4;
            if(p[3]>240){red+=p[0];green+=p[1];blue+=p[2];samples++;}
        }
        SDL_UnlockSurface(rgba);
        if(samples)art->plastic=(SDL_Color){red/samples,green/samples,blue/samples,255};
    }
    SDL_FreeSurface(rgba);
}

/* Load the physical shell and tint its reserved plastic with the baked cart's. */
static void cartridge_media_prepare(CartridgeArt *art,const char *assets,const ConsoleSpec *s,SDL_Surface *face)
{
    const MediaSpec *m=cartridge_media_variant(art,s);
    if(!m)return;
    if(art->media_mesh.vertex_count)console_mesh_close(&art->media_mesh);
    if(!console_mesh_load_part(&art->media_mesh,assets,m->folder,m->part)){log_event("physical media mesh unavailable; extruded fallback");return;}
    art->media=m;
    cartridge_sample_plastic(art,face,m->sample,m->canvas);
    const float plastic[3]={art->plastic.r/255.f,art->plastic.g/255.f,art->plastic.b/255.f};
    if(art->media_mesh.media_weights){
        ConsoleMesh *mesh=&art->media_mesh;mesh->media_tinted=true;
        memcpy(mesh->media_tint,plastic,sizeof(plastic));
        for(unsigned i=0;i<mesh->vertex_count;i++)if(mesh->media_weights[i])
            for(int j=0;j<3;j++)mesh->vertices[i].colour[j]=fminf(1,plastic[j]*mesh->media_weights[i]/192.f);
        free(mesh->media_weights);mesh->media_weights=NULL;
    }
    for(unsigned i=0;i<art->media_mesh.vertex_count;i++){
        float *c=art->media_mesh.vertices[i].colour;
        float k=media_colour_is(c,media_shell)?1.f:media_colour_is(c,media_shade)?.72f:0;
        if(k>0)for(int j=0;j<3;j++)c[j]=plastic[j]*k;
    }
    char label[96];snprintf(label,sizeof(label),"%s-label",m->part);
    if(console_mesh_load_part(&art->disc_mesh,assets,m->folder,label)){
        ConsoleMesh *mesh=&art->disc_mesh;mesh->unlit=true;
        if(!mesh->uv){console_mesh_close(mesh);return;}
        // Source-surface UVs read only this game's measured shelf label crop.
        if(mesh->uv)for(unsigned i=0;i<mesh->vertex_count;i++)for(int j=0;j<2;j++)
            mesh->uv[i*2+j]=(m->well[j]+mesh->uv[i*2+j]*(m->well[j+2]-m->well[j]))/m->canvas[j];
    }
}

static double cartridge_dot(PsxVec a,PsxVec b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static void cartridge_media_colour(CartridgeArt *art,const char *name)
{
    if(art->media_mesh.media_tinted)return;
    bool dmg=!strcmp(name,"gb")||art->dmg_media,cgb=!dmg&&!strcmp(name,"gbc"),ags=!strcmp(name,"gba");
    if(!dmg&&!cgb&&!ags)return;
    // Every Game Pak takes the baked cart's own plastic, coloured DMG shells too.
    const float base[3]={dmg?.76f:cgb?.48f:.28f,dmg?.77f:cgb?.47f:.29f,dmg?.75f:cgb?.54f:.30f};
    for(unsigned i=0;i<art->media_mesh.vertex_count;i++){
        float *c=art->media_mesh.vertices[i].colour;
        if(fabsf(c[0]-base[0])<.005f&&fabsf(c[1]-base[1])<.005f&&fabsf(c[2]-base[2])<.005f){
            c[0]=art->plastic.r/255.f;c[1]=art->plastic.g/255.f;c[2]=art->plastic.b/255.f;
        }
    }
}
static void cartridge_edge(SDL_Renderer *r,PsxVec *points,PsxVec clip,double limit,
                           bool clipping,SDL_Color colour,double origin)
{
    PsxVec out[8];int count=0;
    for(int i=0;i<4;i++){
        PsxVec a=points[i],b=points[(i+1)%4];
        double da=cartridge_dot(a,clip)-limit,db=cartridge_dot(b,clip)-limit;
        if(!clipping||da>=0)out[count++]=a;
        if(clipping&&((da>=0)!=(db>=0)))
            out[count++]=psx_add(a,psx_mul(psx_add(b,psx_mul(a,-1)),da/(da-db)));
    }
    if(count>=3)psx_polygon(r,out,count,colour,origin);
}

static void cartridge_face(SDL_Renderer *r,SDL_Texture *texture,PsxVec centre,PsxVec u,PsxVec v,
                            double rx,double ry,double first,double last,double inset,double origin)
{
    if(last<=first)return;
    enum{GRID=12,SIDE=GRID+1};SDL_Vertex vertices[SIDE*SIDE];int indices[GRID*GRID*6];
    for(int y=0;y<SIDE;y++)for(int x=0;x<SIDE;x++){
        double tu=(double)x/GRID,tv=first+(last-first)*y/GRID;
        PsxVec p=psx_add(centre,psx_add(psx_mul(u,rx*(2*tu-1)),psx_mul(v,ry*(2*tv-1))));
        vertices[y*SIDE+x]=(SDL_Vertex){psx_project(p,origin),{255,255,255,255},{inset+(1-2*inset)*tu,tv}};
    }
    int n=0;
    for(int y=0;y<GRID;y++)for(int x=0;x<GRID;x++){
        int a=y*SIDE+x,quad[]={a,a+1,a+SIDE,a+1,a+SIDE+1,a+SIDE};
        memcpy(indices+n,quad,sizeof(quad));n+=6;
    }
    SDL_RenderGeometry(r,texture,vertices,SIDE*SIDE,indices,n);
}

static void cartridge_slab(SDL_Renderer *r,CartridgeArt *art,SDL_Texture *face,PsxVec centre,
                            PsxVec u,PsxVec v,double rx,double ry,double thickness,
                            PsxVec clip,double limit,bool clipping,double inset,double origin)
{
    PsxVec normal=psx_mul(psx_cross(u,v),-1),rear=psx_add(centre,psx_mul(normal,-thickness));
    for(int i=0;i<art->count;i++){
        int j=(i+1)%art->count;
        PsxVec ca=psx_add(psx_mul(u,art->outline[i][0]*rx),psx_mul(v,art->outline[i][1]*ry));
        PsxVec cb=psx_add(psx_mul(u,art->outline[j][0]*rx),psx_mul(v,art->outline[j][1]*ry));
        // The contour is clockwise on the printed face; shade the outer wall.
        PsxVec edge=psx_add(cb,psx_mul(ca,-1));
        PsxVec outward=psx_cross(edge,normal);
        if(psx_depth(outward)<=0)continue;
        double light=.67+.25*fmax(0,-outward.x/(sqrt(cartridge_dot(outward,outward))+1e-9));
        SDL_Color c={art->plastic.r*light,art->plastic.g*light,art->plastic.b*light,255};
        PsxVec p[]={psx_add(centre,ca),psx_add(centre,cb),psx_add(rear,cb),psx_add(rear,ca)};
        cartridge_edge(r,p,clip,limit,clipping,c,origin);
    }
    double first=0,last=1;
    if(clipping){
        double dv=cartridge_dot(v,clip)*ry,dc=cartridge_dot(centre,clip)-limit;
        if(fabs(dv)>1e-8){double cut=clamp((1-dc/dv)/2);if(dv>0)first=cut;else last=cut;}
        else if(dc<0)return;
    }
    bool back=art->rear&&psx_depth(normal)<0;
    cartridge_face(r,back?art->rear:face,back?rear:centre,u,v,rx,ry,first,last,inset,origin);
}

static void cartridge_sprite(SDL_Renderer *r,SDL_Texture *texture,SDL_Rect bounds,double origin)
{
    bounds.y+=(int)lround(origin-240);SDL_RenderCopy(r,texture,NULL,&bounds);
}

static PsxVec cartridge_mix(PsxVec a,PsxVec b,double t)
{
    return psx_add(psx_mul(a,1-t),psx_mul(b,t));
}

/* Physical media drawn by one path: q mesh and qs scene units per mm, W/H mm,
 * oz mesh-origin depth behind the face, label centre/plane/half sizes in mm,
 * the shelf label crop and the shelf body box (hero pose) on its canvas. */
typedef struct {
    double q,qs,w,h,oz,lx,ly,lz,lw,lh;
    const int *crop,*canvas;
    const double *body;
} MediaDraw;

static const ExemplarShelf *exemplar_shelf_for(const char *name)
{
    for(size_t i=0;i<sizeof(exemplar_shelf)/sizeof(exemplar_shelf[0]);i++)
        if(!strcmp(name,exemplar_shelf[i].name))return &exemplar_shelf[i];
    return NULL;
}

static bool cartridge_media_draw(const CartridgeArt *art,const ConsoleSpec *s,MediaDraw *d)
{
    if(!art->media_mesh.ready)return false;
    const MediaSpec *m=art->media;
    if(m){
        *d=(MediaDraw){m->v[MEDIA_Q],m->v[MEDIA_Q],m->v[MEDIA_W],m->v[MEDIA_H],m->v[MEDIA_OZ],
            m->v[MEDIA_LX],m->v[MEDIA_LY],m->v[MEDIA_LZ],m->v[MEDIA_LW],m->v[MEDIA_LH],m->well,m->canvas,m->body};
        return true;
    }
    bool cgb=!strcmp(s->name,"gbc"),ags=!strcmp(s->name,"gba"),dmg=!strcmp(s->name,"gb")||art->dmg_media;
    if(!dmg&&!cgb&&!ags)return false;
    const ExemplarShelf *e=exemplar_shelf_for(dmg?"gb":s->name);
    if(!e)return false;
    // The DMG Game Pak keeps its own mesh units in a CGB; the scene keeps the CGB's.
    *d=(MediaDraw){dmg?168.0/90:cgb?168.0/78:224.0/82,s->cart/e->size[0],e->size[0],e->size[1],ags?0:3.9,
        0,dmg?-4.8791:cgb?-5:-2,dmg?3.875:cgb?3.72:3.53,dmg?20.92095:cgb?20.9:22.15,dmg?18.7022:cgb?18.6:11.5,
        e->label,e->canvas,e->body};
    return true;
}

/* Offline shelf-hero capture only: draw the media alone, sub-pixel jittered. */
static bool cartridge_media_only;
static double cartridge_jitter[2];

/* lift: the fraction of seating travel already released by an eject spring
 * before the reversed motion; it scales the remaining travel continuously. */
static void cartridge_scene(SDL_Renderer *r,CartridgeArt *art,SDL_Texture *face,
                             const ConsoleSpec *s,int width,int height,int foot,double time,double lift,double lid_open)
{
    double rise=psx_ease(time/.22),align=psx_ease(time/.38),move=psx_ease((time-.34)/.44)*(1-lift);
    double origin=s->idle+(s->origin-s->idle)*rise;
    double yaw=(-8-14*psx_ease(time/.38))*PSX_PI/180,lean=0;
    if(s->kind==0||s->kind==2)yaw=SLOT_HOME_YAW;
    if(s->kind==1){yaw=(-12+180*psx_ease((time-.20)/.42))*PSX_PI/180;lean=-PSX_PHI;}
    if(s->kind==4){
        yaw=(-8+176*psx_ease((time-.20)/.38))*PSX_PI/180;
        lean=-15*PSX_PI/180*psx_ease((time-.40)/.18);
    }
    float matrix[16];console_matrix(matrix,yaw,lean);
    if(!cartridge_media_only&&!console_mesh_draw(&art->mesh,r,matrix,origin,false,true))
        cartridge_sprite(r,art->body,s->sprite,origin);
    bool dmg=!strcmp(s->name,"gb"),cgb=!strcmp(s->name,"gbc"),ags=!strcmp(s->name,"gba");
    // Physical media start exactly as the shelf shows them: their 3D hero pose
    // fills the shelf body box, then scale uniformly to the physical envelope.
    MediaDraw md={0};bool physical=cartridge_media_draw(art,s,&md);
    double hero_w=width,hero_aspect=1,cart_width=s->cart;
    double physical_aspect=dmg||cgb?65.5/57.0:ags?34.5/60.0:(double)height/width;
    double final_ry=s->cart*physical_aspect/2;
    if(physical){
        hero_w=(md.body[2]-md.body[0])*width/md.canvas[0];
        hero_aspect=((md.body[3]-md.body[1])/(md.body[2]-md.body[0]))/(md.h/md.w);
        cart_width=md.w*md.qs;final_ry=md.h*md.qs/2;
    }
    double rx=(hero_w+(cart_width-hero_w)*align)/2,ry=rx*height/width;
    PsxVec u={1,0,0},v=psp_v(),centre={0,0,0},clip={0,1,0};double limit=0;
    double hero_origin=foot-height/2.0,cart_origin=hero_origin+(origin-hero_origin)*align;
    bool clipping=align>.999;
    if(s->kind==1){
        double park=psx_ease(time/.18);align=psx_ease((time-.58)/.18);
        if(dmg){
            double edge=300.0/312+(1-300.0/312)*align;
            const double profile[][2]={{-edge,-1},{edge*24.0/28.5,-1},{edge*24.0/28.5,-25.75/32.75},{edge,-25.75/32.75},{edge,1},{-edge,1}};
            art->count=6;memcpy(art->outline,profile,sizeof(profile));
        }
        move=psx_ease((time-.74)/.17);clipping=align>.999;
        double parked_width=hero_w*(1-.48*park);
        rx=(parked_width+(cart_width-parked_width)*align)/2;
        ry=rx*((double)height/width+(physical_aspect-(double)height/width)*align);
        cart_origin=hero_origin+(170-hero_origin)*park;cart_origin+=(origin-cart_origin)*align;
        PsxVec target_u=console_rotate((PsxVec){-1,0,0},yaw,lean);
        PsxVec target_v=console_rotate((PsxVec){0,-1,0},yaw,lean);
        u=cartridge_mix(u,target_u,align);v=cartridge_mix(v,target_v,align);
        double hover=s->ry+final_ry-6,target=s->ry-final_ry-(dmg||cgb?0:3);
        double label_depth=dmg?dmg_authored_cart_label_native:cgb?cgb_cart_label_native:-s->depth+13;
        PsxVec loaded=console_rotate((PsxVec){0,hover+(target-hover)*move,label_depth},yaw,lean);
        centre=cartridge_mix((PsxVec){-210*park,0,0},loaded,align);
        clip=console_rotate((PsxVec){0,1,0},yaw,lean);limit=s->slot;
    }else if(s->kind==4){
        // Label-down entry through the rear Slot-1 edge.
        double park=psx_ease(time/.18);align=psx_ease((time-.53)/.20);
        move=psx_ease((time-.74)/.13);clipping=align>.999;
        double parked_width=hero_w*(1-.50*park);
        rx=(parked_width+(cart_width-parked_width)*align)/2;ry=rx*height/width;
        cart_origin=hero_origin+(150-hero_origin)*park;cart_origin+=(origin-cart_origin)*align;
        double flip=PSX_PHI+(-PSX_PI/2-PSX_PHI)*align;
        // Take the short turn to the rear-facing basis, avoiding a full spin
        // while the card flips down into the connector plane.
        double spin=(yaw-PSX_PI)*align;
        u=console_rotate((PsxVec){1,0,0},spin,lean*align);
        v=console_rotate((PsxVec){0,-cos(flip),sin(flip)},spin,lean*align);
        double hover=s->slot-final_ry-18,target=s->slot+final_ry-3;
        double click=3*psx_ease((time-.86)/.025)*(1-psx_ease((time-.895)/.025));
        // The physical card's face rides just above the deepened Slot-1 floor.
        PsxVec loaded=console_rotate((PsxVec){-28,physical?-70.4:-70,hover+(target-hover)*move+click},yaw,lean);
        centre=cartridge_mix((PsxVec){-216*park,0,0},loaded,align);
        clip=console_rotate((PsxVec){0,0,-1},yaw,lean);limit=-s->slot-1;
    }else if(s->kind==2||s->kind==3){
        // AGS illustration 4: connector first, label toward the underside.
        // Its short forward turn ends with u=+X, v=-Z, label normal=-Y. The
        // console's turn joins as the media aligns, so the hero is face-on.
        double angle=PSX_PHI+((ags?-PSX_PI/2:PSX_PI/2)-PSX_PHI)*align,spin=ags?0:PSX_PI*align;
        u=console_rotate(u,spin,0);v=console_rotate((PsxVec){0,-cos(angle),sin(angle)},spin,0);
        double entry=s->kind==2?s->ry:s->slot;
        double destination=s->kind==2?35:ags?24.45*(224.0/82):63;
        // A physical Game Pak rides just above the NES tray, then presses down.
        double press=physical&&s->kind==2?nes_tray_top*s->yscale+.6+md.oz*2*md.qs
            -7*s->yscale*psx_ease((time-.74)/.09):0;
        centre=(PsxVec){s->kind==2?-45*align:0,
            (physical&&s->kind==2?press:s->kind==2?(-19-7*psx_ease((time-.74)/.09))*s->yscale:ags?-26.03*(224.0/82):-59)*align,
            (entry+final_ry+9+(destination-entry-final_ry-9)*move)*align};
        u=console_rotate(u,yaw*align,0);v=console_rotate(v,yaw*align,0);centre=console_rotate(centre,yaw*align,0);
        clip=console_rotate((PsxVec){0,0,1},yaw,0);limit=entry+1;
    }else{
        double tilt=PSX_PHI*(1-align);v=(PsxVec){0,-cos(tilt),sin(tilt)};
        double entry=s->entry;
        // Physical media centre their thickness on the slot, not their face.
        centre=(PsxVec){0,(final_ry+entry+55-(s->sink+55)*move)*align,
            physical?(s->slot+md.oz*md.qs)*align:s->slot*align};
        u=console_rotate(u,yaw*align,0);v=console_rotate(v,yaw*align,0);centre=console_rotate(centre,yaw*align,0);
        limit=entry;
    }
    double thickness=dmg?9+(s->cart*7.8/57.0-9)*align:s->kind==4?10:s->kind==2?12:9;
    if(physical){
        // sx: uniform scale from hero width to the physical envelope; sy also
        // eases the hero's shelf proportion back to the physical one.
        const double q=md.q,sx=2*rx/(md.w*q),sy=sx*(1-(1-hero_aspect)*(1-align));
        PsxVec normal=psx_mul(psx_cross(u,v),-1);
        PsxVec base=psx_add(centre,psx_mul(normal,-md.oz*q*sx));
        float media_matrix[16]={0};media_matrix[15]=1;
        PsxVec basis[]={psx_mul(u,sx),psx_mul(v,-sy),psx_mul(normal,sx)};
        for(int i=0;i<3;i++){media_matrix[4*i]=basis[i].x;media_matrix[4*i+1]=basis[i].y;media_matrix[4*i+2]=basis[i].z;}
        media_matrix[12]=base.x+cartridge_jitter[0];media_matrix[13]=base.y;media_matrix[14]=base.z;
        double media_origin=cart_origin+cartridge_jitter[1];
        // Share the housing depth so its walls hide the seated shell.
        GLuint own_depth=art->media_mesh.depth;
        if(!cartridge_media_only)art->media_mesh.depth=art->mesh.depth;
        console_mesh_draw(&art->media_mesh,r,media_matrix,media_origin,false,cartridge_media_only);
        art->media_mesh.depth=own_depth;
        // The baked ROM label fills only the shell's recessed well. Pico-8's
        // fantasy cart maps its complete PNG artwork, credits included.
        bool source_label=false;
        if(face&&art->disc_mesh.vertex_count&&console_mesh_open(&art->disc_mesh,r)&&art->disc_mesh.uv_buffer){
            ConsoleMesh *label=&art->disc_mesh;SDL_RenderFlush(r);
            if(!SDL_GL_BindTexture(face,NULL,NULL)){
                GLint texture=0;cgGetIntegerv(GL_TEXTURE_BINDING_2D,&texture);SDL_GL_UnbindTexture(face);
                Uint32 format=0;SDL_QueryTexture(face,&format,NULL,NULL,NULL);
                label->swap_rb=format==SDL_PIXELFORMAT_BGRA32||format==SDL_PIXELFORMAT_BGRX32;
                GLuint own=label->depth,blank=label->albedo_texture;
                label->depth=cartridge_media_only?art->media_mesh.depth:art->mesh.depth;
                label->albedo_texture=(GLuint)texture;label->cutout=true;
                source_label=console_mesh_draw(label,r,media_matrix,media_origin,false,false);
                label->depth=own;label->albedo_texture=blank;
            }
        }
        if(face&&!source_label&&psx_depth(normal)>=0){
            PsxVec label=psx_add(base,psx_add(psx_add(psx_mul(u,md.lx*q*sx),
                psx_mul(v,-md.ly*q*sy)),psx_mul(normal,md.lz*q*sx)));
            double halfw=md.lw*q*sx,halfh=md.lh*q*sy,first=0,last=1;
            if(clipping){double dv=cartridge_dot(v,clip)*halfh,dc=cartridge_dot(label,clip)-limit;
                if(fabs(dv)>1e-8){double cut=clamp((1-dc/dv)/2);if(dv>0)first=cut;else last=cut;}
                else if(dc<0)first=1;
            }
            if(last>first){
                SDL_Vertex points[4];int indices[]={0,1,2,0,2,3};
                const double uv[4][2]={{0,first},{1,first},{1,last},{0,last}};
                for(int i=0;i<4;i++){
                    PsxVec p=psx_add(label,psx_add(psx_mul(u,halfw*(2*uv[i][0]-1)),psx_mul(v,halfh*(2*uv[i][1]-1))));
                    points[i]=(SDL_Vertex){psx_project(p,media_origin),{255,255,255,255},
                        {(md.crop[0]+(md.crop[2]-md.crop[0])*uv[i][0])/md.canvas[0],
                         (md.crop[1]+(md.crop[3]-md.crop[1])*uv[i][1])/md.canvas[1]}};
                }
                SDL_RenderGeometry(r,face,points,4,indices,6);
            }
        }
    }else cartridge_slab(r,art,face,centre,u,v,rx,ry,thickness,clip,limit,clipping,dmg?6.0/312*align:0,cart_origin);
    if(handheld_has_lid(s->name)&&!cartridge_media_only)
        handheld_lid_draw(&art->mesh,r,s->name,matrix,origin,time,lid_open);
    if(!strcmp(s->name,"n64")&&!cartridge_media_only){
        double bottom=align>.999?s->entry+55-(s->sink+55)*move:s->entry+55;
        n64_flaps_draw(&art->mesh,r,matrix,origin,bottom,physical?md.oz*md.qs:n64_cart_half_thickness);
    }
    if(s->kind==2&&art->mesh.ready&&!cartridge_media_only){
        double opening=psx_ease(time/.23)*(1-psx_ease((time-.78)/.14)),angle=-opening*80*PSX_PI/180;
        float local[16],door[16]={0};console_matrix(local,0,angle);
        PsxVec hinge={-45,2*s->yscale,s->ry-37},rotated=console_rotate(hinge,0,angle);
        local[12]=hinge.x-rotated.x;local[13]=hinge.y-rotated.y;local[14]=hinge.z-rotated.z;
        for(int col=0;col<4;col++)for(int row=0;row<4;row++)for(int k=0;k<4;k++)door[col*4+row]+=matrix[k*4+row]*local[col*4+k];
        console_mesh_draw(&art->mesh,r,door,origin,true,false);
    }
}
