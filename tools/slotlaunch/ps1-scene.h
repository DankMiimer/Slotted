/* Authored PlayStation console and source-registered hinge/spindle (MIT code).
 * The existing optical disc projection shares the console's perspective.
 * Geometry is credited separately in MODEL_CREDITS.txt. */
#include "ps1-data.h"
#include "dreamcast-data.h"
#include "optical-disc.h"

static void ps1_scene(SDL_Renderer *r,CartridgeArt *model,PsxArt *art,
                      const ConsoleSpec *s,double time,bool returning,double lid,double eject_spin)
{
    bool dreamcast=!strcmp(s->name,"dreamcast");
    const double *hinge_point=dreamcast?dreamcast_hinge:ps1_hinge;
    const double *disc_point=dreamcast?dreamcast_disc_centre:ps1_disc_centre;
    double disc_radius=dreamcast?dreamcast_disc_radius:ps1_disc_radius;
    double origin=s->idle+(s->origin-s->idle)*psx_ease(time/.19);
    double opening=lid>=0?lid:psx_ease(time/.22)*(1-psx_ease((time-.66)/.19));
    double yaw=SLOT_HOME_YAW,angle=-opening*(dreamcast?74:78)*PSX_PI/180;
    float matrix[16],local[16],door[16]={0};console_matrix(matrix,yaw,0);
    if(!console_mesh_draw(&model->mesh,r,matrix,origin,false,true))
        cartridge_sprite(r,model->body,s->sprite,origin);
    console_matrix(local,0,angle);
    PsxVec hinge={hinge_point[0],hinge_point[1],hinge_point[2]},rotated=console_rotate(hinge,0,angle);
    local[12]=hinge.x-rotated.x;local[13]=hinge.y-rotated.y;local[14]=hinge.z-rotated.z;
    for(int col=0;col<4;col++)for(int row=0;row<4;row++)for(int k=0;k<4;k++)
        door[col*4+row]+=matrix[k*4+row]*local[col*4+k];
    double travel=psx_ease((time-.12)/.44);
    double radius=150+(disc_radius-150)*travel;
    double tilt=PSX_PHI+((dreamcast?dreamcast_disc_tilt:PSX_PI/2)-PSX_PHI)*travel;
    double disc_yaw=10*PSX_PI/180*(1-travel)+yaw*travel;
    double spin=returning?0:160*PSX_PI/180*pow(psx_ease((time-.57)/.14),2);
    double roll=-3*PSX_PI/180*(1-travel)+spin+eject_spin;
    PsxVec u={cos(disc_yaw),0,-sin(disc_yaw)},v={sin(tilt)*sin(disc_yaw),-cos(tilt),sin(tilt)*cos(disc_yaw)};
    PsxVec ru=psx_add(psx_mul(u,cos(roll)),psx_mul(v,sin(roll)));
    PsxVec rv=psx_add(psx_mul(u,-sin(roll)),psx_mul(v,cos(roll)));
    PsxVec target=console_rotate((PsxVec){disc_point[0],disc_point[1],disc_point[2]},yaw,0);
    PsxVec centre=cartridge_mix((PsxVec){0,156,0},target,travel);
    centre.y+=8*sin(PSX_PI*psx_ease(time/.24))*(1-travel);
    double thickness=2.2+(1.2*(dreamcast?dreamcast_disc_radius/60:1.6)-2.2)*travel;
    double disc_origin=350+(origin-350)*travel;
    if(!optical_disc_draw(model,r,art,centre,ru,rv,radius,thickness,disc_origin))
        psx_ring(r,art->disc,art->underside,centre,ru,rv,radius,thickness,disc_origin,false);
    // As in the UMD scene, the moving native cover is drawn after the SDL
    // artwork and shares the body's depth attachment. Its real rim/underside
    // occludes the disc during closure; the disc bore leaves the spindle visible.
    console_mesh_draw(&model->mesh,r,door,origin,true,false);
}
