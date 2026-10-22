/* Contact-driven N64 spring doors. MIT processing; credited source geometry.
 * Work in the console's rigid local frame; depth and pivot sections come from
 * the actual prepared/exported leaves, never the replacement CAD download. */
#include "n64-data.h"

static bool n64_flap_clear(const double (*profile)[2],unsigned count,const double *hinge,
                            int side,double angle,double bottom,double half_thickness)
{
    double y[count],z[count],c=cos(angle),s=sin(angle),highest=-10000;
    double boundary=half_thickness+n64_flap_clearance;
    for(unsigned i=0;i<count;i++){
        double dy=profile[i][0]-hinge[0],dz=profile[i][1]-hinge[1];
        y[i]=hinge[0]+dy*c-dz*s;z[i]=side*(hinge[1]+dy*s+dz*c-n64_cart_slot);
        if(z[i]<=boundary)highest=fmax(highest,y[i]);
    }
    for(unsigned i=0;i<count;i++)for(unsigned j=i+1;j<count;j++){
        if((z[i]<boundary&&boundary<z[j])||(z[j]<boundary&&boundary<z[i]))
            highest=fmax(highest,y[i]+(y[j]-y[i])*(boundary-z[i])/(z[j]-z[i]));
    }
    return highest<=bottom-n64_flap_clearance;
}

static double n64_flap_angle(const double (*profile)[2],unsigned count,const double *hinge,
                              int side,double bottom,double half_thickness)
{
    if(n64_flap_clear(profile,count,hinge,side,0,bottom,half_thickness))return 0;
    double lo=0,hi=89*PSX_PI/180;
    for(int i=0;i<18;i++){
        double mid=(lo+hi)/2;
        if(n64_flap_clear(profile,count,hinge,side,-side*mid,bottom,half_thickness))hi=mid;
        else lo=mid;
    }
    return -side*hi;
}

static void n64_flaps_draw(ConsoleMesh *mesh,SDL_Renderer *r,const float *global,
                            double origin,double bottom,double half_thickness)
{
    const double (*profiles[2])[2]={n64_flap_profile_0,n64_flap_profile_1};
    const unsigned counts[2]={sizeof(n64_flap_profile_0)/sizeof(n64_flap_profile_0[0]),
                              sizeof(n64_flap_profile_1)/sizeof(n64_flap_profile_1[0])};
    const double *hinges[2]={n64_flap_hinge_0,n64_flap_hinge_1};
    const unsigned *ranges[2]={n64_flap_range_0,n64_flap_range_1};
    for(int i=0;i<2;i++){
        double angle=n64_flap_angle(profiles[i],counts[i],hinges[i],i?1:-1,bottom,half_thickness);
        float matrix[16];console_hinge_matrix(matrix,global,(PsxVec){0,hinges[i][0],hinges[i][1]},angle);
        // Source panels suppress outline hulls; both ranges are independently
        // posed in one VBO and share the console/media depth attachment.
        console_mesh_draw_range(mesh,r,matrix,origin,ranges[i][0],ranges[i][1],0,0,false);
    }
}
