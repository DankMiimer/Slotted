/* Copyright (c) 2026, MIT.
 * Original PS1 geometry. One perspective camera for disc, spindle and rear hinge.
 * Texture grids approximate perspective interpolation on SDL's GLES2 renderer. */
typedef struct { double x,y,z; } PsxVec;
typedef struct { SDL_Texture *disc,*underside,*lid,*inside,*deck,*shadow; } PsxArt;
#define PSX_PI 3.14159265358979323846
#define PSX_PHI (35*PSX_PI/180)
/* TVs and handheld reading retain southwest. Home consoles face southeast about
 * physical up, keeping their feet on the same level surface as the TV. */
#define SLOT_STANDARD_YAW_DEGREES (-22)
#define SLOT_STANDARD_YAW (SLOT_STANDARD_YAW_DEGREES*PSX_PI/180)
#define SLOT_HOME_YAW_DEGREES (22)
#define SLOT_HOME_YAW (SLOT_HOME_YAW_DEGREES*PSX_PI/180)
static PsxVec psp_v(void) { return (PsxVec){0,-cos(PSX_PHI),sin(PSX_PHI)}; }
static PsxVec psx_add(PsxVec a,PsxVec b) { return (PsxVec){a.x+b.x,a.y+b.y,a.z+b.z}; }
static PsxVec psx_mul(PsxVec a,double b) { return (PsxVec){a.x*b,a.y*b,a.z*b}; }
static PsxVec psx_cross(PsxVec a,PsxVec b) { return (PsxVec){a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x}; }
static double psx_depth(PsxVec a) { return a.y*sin(PSX_PHI)+a.z*cos(PSX_PHI); }
static SDL_FPoint psx_project(PsxVec a,double origin)
{
    double k=1200/(1200-psx_depth(a));
    return (SDL_FPoint){360+a.x*k,origin+(a.z*sin(PSX_PHI)-a.y*cos(PSX_PHI))*k};
}
static double psx_ease(double x) { return smootherstep(clamp(x)); }
static void psx_polygon(SDL_Renderer *r,PsxVec *p,int count,SDL_Color colour,double origin)
{
    SDL_Vertex v[100];int indices[294];
    for (int i=0;i<count;i++)v[i]=(SDL_Vertex){psx_project(p[i],origin),colour,{0,0}};
    for (int i=1;i<count-1;i++){indices[(i-1)*3]=0;indices[(i-1)*3+1]=i;indices[(i-1)*3+2]=i+1;}
    SDL_RenderGeometry(r,NULL,v,count,indices,(count-2)*3);
}
static void psx_plane(SDL_Renderer *r,SDL_Texture *texture,PsxVec centre,PsxVec u,PsxVec v,
                      double rx,double ry,double origin)
{
    enum {GRID=12,SIDE=GRID+1};SDL_Vertex vertices[SIDE*SIDE];int indices[GRID*GRID*6];
    for(int y=0;y<SIDE;y++)for(int x=0;x<SIDE;x++){
        PsxVec p=psx_add(centre,psx_add(psx_mul(u,rx*(2.0*x/GRID-1)),psx_mul(v,ry*(2.0*y/GRID-1))));
        vertices[y*SIDE+x]=(SDL_Vertex){psx_project(p,origin),{255,255,255,255},{(float)x/GRID,(float)y/GRID}};
    }
    int n=0;
    for(int y=0;y<GRID;y++)for(int x=0;x<GRID;x++){
        int a=y*SIDE+x;int quad[]={a,a+1,a+SIDE,a+1,a+SIDE+1,a+SIDE};
        memcpy(indices+n,quad,sizeof(quad));n+=6;
    }
    SDL_RenderGeometry(r,texture,vertices,SIDE*SIDE,indices,n);
}
static void psx_circle(SDL_Renderer *r,PsxVec centre,double radius,SDL_Color colour,double origin)
{
    PsxVec p[96];
    for(int i=0;i<96;i++){double a=i*2*PSX_PI/96;p[i]=psx_add(centre,(PsxVec){radius*cos(a),0,radius*sin(a)});}
    psx_polygon(r,p,96,colour,origin);
}
static void psx_ring(SDL_Renderer *r,SDL_Texture *front,SDL_Texture *back,PsxVec centre,
                     PsxVec u,PsxVec v,double radius,double thickness,double origin,bool lid)
{
    PsxVec normal=psx_mul(psx_cross(u,v),-1),rear=psx_add(centre,psx_mul(normal,-thickness));
    SDL_Vertex vertices[768];int indices[1152],nv=0,ni=0;
    for(int ring=0;ring<(lid?1:2);ring++){
        double rad=ring?radius/8:radius;
        for(int i=0;i<96;i++){
            double a=i*2*PSX_PI/96,b=(i+1)*2*PSX_PI/96;
            PsxVec ca=psx_add(psx_mul(u,cos(a)),psx_mul(v,sin(a)));
            PsxVec cb=psx_add(psx_mul(u,cos(b)),psx_mul(v,sin(b)));
            PsxVec direction=psx_mul(psx_add(ca,cb),ring?-.5:.5);
            if(psx_depth(direction)<=0)continue;
            double light=fmax(0,-.5*direction.x+.6*direction.y+.6*direction.z);
            int tone=(int)lround(lid?116+42*light:ring?40+100*light:18+36*light);
            PsxVec p[]={psx_add(centre,psx_mul(ca,rad)),psx_add(centre,psx_mul(cb,rad)),
                        psx_add(rear,psx_mul(cb,rad)),psx_add(rear,psx_mul(ca,rad))};
            for(int j=0;j<4;j++)vertices[nv+j]=(SDL_Vertex){psx_project(p[j],origin),{tone,tone+1,tone+3,255},{0,0}};
            int quad[]={nv,nv+1,nv+2,nv,nv+2,nv+3};
            memcpy(indices+ni,quad,sizeof(quad));nv+=4;ni+=6;
        }
    }
    if(nv)SDL_RenderGeometry(r,NULL,vertices,nv,indices,ni);
    bool facing=psx_depth(normal)>=0;
    psx_plane(r,facing?front:back,facing?centre:rear,u,v,radius,radius,origin);
}
static void psx_deck(SDL_Renderer *r,PsxArt *art,double origin)
{
    double outline[][2]={{-216,-150},{216,-150},{228,-132},{228,132},{215,150},{-215,150},{-228,132},{-228,-132}};
    for(int i=2;i<=6;i++){
        int j=(i+1)%8;PsxVec p[]={{outline[i][0],0,outline[i][1]},{outline[j][0],0,outline[j][1]},
            {outline[j][0],-24,outline[j][1]},{outline[i][0],-24,outline[i][1]}};
        psx_polygon(r,p,4,(SDL_Color){133,130,135,255},origin);
    }
    psx_plane(r,art->deck,(PsxVec){0,0,0},(PsxVec){1,0,0},(PsxVec){0,0,1},228,150,origin);
    /* Stacked memory-card and controller bays on the actual front face. */
    for(int bay=0;bay<2;bay++){
        double x=bay?69:-69;
        PsxVec surround[]={{x-60,-2,150.2},{x+60,-2,150.2},{x+60,-23,150.2},{x-60,-23,150.2}};
        psx_polygon(r,surround,4,(SDL_Color){105,103,109,255},origin);
        PsxVec card[]={{x-49,-4,150.5},{x+49,-4,150.5},{x+49,-8,150.5},{x-49,-8,150.5}};
        psx_polygon(r,card,4,(SDL_Color){35,34,39,255},origin);
        PsxVec controller[]={{x-36,-12,150.6},{x+36,-12,150.6},{x+41,-16,150.6},{x+36,-22,150.6},{x-36,-22,150.6},{x-41,-16,150.6}};
        psx_polygon(r,controller,6,(SDL_Color){40,39,45,255},origin);
        for(int pin=0;pin<9;pin++){
            double px=x-28+7*pin;
            PsxVec contact[]={{px-1,-15,150.8},{px+1,-15,150.8},{px+1,-18,150.8},{px-1,-18,150.8}};
            psx_polygon(r,contact,4,(SDL_Color){143,140,123,255},origin);
        }
    }
}
static void psx_lid(SDL_Renderer *r,PsxArt *art,double origin,double opening)
{
    double a=opening*78*PSX_PI/180;
    psx_ring(r,art->lid,art->inside,(PsxVec){0,128*sin(a)+2,-128+128*cos(a)},
        (PsxVec){1,0,0},(PsxVec){0,sin(a),cos(a)},126,3,origin,true);
}
/* lid >= 0 overrides the lid opening (eject spring); spin adds disc rotation. */
static void psx_scene(SDL_Renderer *r,PsxArt *art,double time,bool returning,double lid,double eject_spin)
{
    double origin=527+(350-527)*psx_ease(time/.19);
    double opening=lid>=0?lid:psx_ease(time/.22)*(1-psx_ease((time-.66)/.19));
    double travel=psx_ease((time-.12)/.44);
    double lift=8*sin(PSX_PI*psx_ease(time/.24))*(1-travel);
    double radius=150+(120-150)*travel;
    double tilt=PSX_PHI+(PSX_PI/2-PSX_PHI)*travel,yaw=10*PSX_PI/180*(1-travel);
    double spin=returning?0:160*PSX_PI/180*pow(psx_ease((time-.57)/.14),2);
    double roll=-3*PSX_PI/180*(1-travel)+spin+eject_spin;
    PsxVec u={cos(yaw),0,-sin(yaw)},v={sin(tilt)*sin(yaw),-cos(tilt),sin(tilt)*cos(yaw)};
    PsxVec ru=psx_add(psx_mul(u,cos(roll)),psx_mul(v,sin(roll)));
    PsxVec rv=psx_add(psx_mul(u,-sin(roll)),psx_mul(v,cos(roll)));
    psx_deck(r,art,origin);psx_lid(r,art,origin,opening);
    if(travel>0){
        double size=radius*(.65+.34*travel)+5*(1-travel);
        SDL_SetTextureAlphaMod(art->shadow,(Uint8)lround(255*travel));
        psx_plane(r,art->shadow,(PsxVec){0,1.1,0},(PsxVec){1,0,0},(PsxVec){0,0,1},size*512/464,size*512/464,origin);
    }
    psx_ring(r,art->disc,art->underside,(PsxVec){0,156+(2-156)*travel+lift,0},ru,rv,
        radius,2.2,350+(origin-350)*travel,false);
    if(travel>.98)psx_circle(r,(PsxVec){0,4.4,0},5,(SDL_Color){116,115,124,255},origin);
    if(time>.66)psx_lid(r,art,origin,opening);
}
