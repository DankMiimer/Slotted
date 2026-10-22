/* Registered handheld lid motion, MIT. The lid does not operate the cart slot. */
#include "lid-data.h"

static bool handheld_has_lid(const char *name)
{
    return !strcmp(name,"gba")||!strcmp(name,"nds");
}

static void handheld_lid_draw(ConsoleMesh *mesh,SDL_Renderer *r,const char *name,
                               const float *global,double origin,double time,double override)
{
    bool ds=!strcmp(name,"nds");
    double opened=override>=0?clamp(override):psx_ease((time-.10)/.20)*(1-psx_ease((time-.82)/.10));
    const double *h=ds?ds_lid_hinge:ags_lid_hinge;
    PsxVec hinge={h[0],h[1],h[2]};
    float matrix[16];console_hinge_matrix(matrix,global,hinge,(ds?ds_lid_open_radians:ags_lid_open_radians)*(1-opened));
    console_mesh_draw(mesh,r,matrix,origin,true,false);
}
