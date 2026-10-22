/* Original cel-shaded PSP-3000 and rigid UMD holder, copyright 2026, MIT.
 * The front turns to the rear, then the bottom-hinged door receives the shell. */
static void psp_slab(SDL_Renderer *r,PsxArt *art,PsxVec centre,PsxVec u,PsxVec v,
                     double radius,double origin)
{
    double scale=radius/32,thickness=4.2*scale;
    PsxVec normal=psx_mul(psx_cross(u,v),-1),rear=psx_add(centre,psx_mul(normal,-thickness));
    int count=(int)(sizeof(umd_case_outline)/sizeof(umd_case_outline[0]));
    double outline[count][2];
    for(int i=0;i<count;i++)for(int j=0;j<2;j++)outline[i][j]=umd_case_outline[i][j]*scale;
    for(int i=0;i<count;i++){
        int j=(i+1)%count;
        PsxVec ca=psx_add(psx_mul(u,outline[i][0]),psx_mul(v,outline[i][1]));
        PsxVec cb=psx_add(psx_mul(u,outline[j][0]),psx_mul(v,outline[j][1]));
        if(psx_depth(psx_add(ca,cb))<=0)continue;
        PsxVec p[]={psx_add(centre,ca),psx_add(centre,cb),psx_add(rear,cb),psx_add(rear,ca)};
        psx_polygon(r,p,4,(SDL_Color){150,158,147,255},origin);
    }
    bool facing=psx_depth(normal)>=0;
    // The textured face is clipped to the physical case footprint. The old
    // square media plane let the approximate raster silhouette define fit.
    SDL_Vertex vertices[count+1];int indices[count*3];
    PsxVec face=facing?centre:rear;
    vertices[0]=(SDL_Vertex){psx_project(face,origin),{255,255,255,255},{.5f,.5f}};
    double canvas=radius*162/157;
    for(int i=0;i<count;i++){
        PsxVec p=psx_add(face,psx_add(psx_mul(u,outline[i][0]),psx_mul(v,outline[i][1])));
        vertices[i+1]=(SDL_Vertex){psx_project(p,origin),{255,255,255,255},
            {(float)(.5+outline[i][0]/(2*canvas)),(float)(.5+outline[i][1]/(2*canvas))}};
        indices[i*3]=0;indices[i*3+1]=i+1;indices[i*3+2]=(i+1)%count+1;
    }
    SDL_RenderGeometry(r,facing?art->disc:art->underside,vertices,count+1,indices,count*3);
}
static PsxVec psp_door_point(PsxVec p,double angle)
{
    PsxVec hinge={psp_authored_hinge_native[0],psp_authored_hinge_native[1],psp_authored_hinge_native[2]};
    return psx_add(hinge,console_rotate(psx_add(p,psx_mul(hinge,-1)),0,angle));
}
static void psp_scene(SDL_Renderer *r,CartridgeArt *model,PsxArt *art,
                       const ConsoleSpec *s,double time)
{
    double park=psx_ease(time/.18),rise=psx_ease(time/.22);
    double yaw=(-14+180*psx_ease((time-.20)/.36))*PSX_PI/180,lean=-PSX_PHI;
    double origin=s->idle+(s->origin-s->idle)*rise;
    double opening=psx_ease((time-.48)/.13)*(1-psx_ease((time-.83)/.07));
    double angle=-opening*42*PSX_PI/180;
    float matrix[16],local[16],door[16]={0};console_matrix(matrix,yaw,lean);
    if(!console_mesh_draw(&model->mesh,r,matrix,origin,false,true))
        cartridge_sprite(r,model->body,s->sprite,origin);
    console_matrix(local,0,angle);
    PsxVec shift=psp_door_point((PsxVec){0,0,0},angle);
    local[12]=shift.x;local[13]=shift.y;local[14]=shift.z;
    for(int col=0;col<4;col++)for(int row=0;row<4;row++)for(int k=0;k<4;k++)
        door[col*4+row]+=matrix[k*4+row]*local[col*4+k];
    double align=psx_ease((time-.57)/.15),travel=psx_ease((time-.72)/.105);
    double radius=(150*(1-.48*park))*(1-align)+(s->cart/2)*align;
    double media_origin=350+(150-350)*park;media_origin+=(origin-media_origin)*align;
    PsxVec target=psp_door_point((PsxVec){psp_authored_umd_label_native[0],psp_authored_umd_label_native[1]+200*(1-travel),psp_authored_umd_label_native[2]},angle);
    target=console_rotate(target,yaw,lean);
    PsxVec parked=cartridge_mix((PsxVec){0,156,0},(PsxVec){-216,0,0},park);
    PsxVec centre=cartridge_mix(parked,target,align);
    // A short, continuous turn to the printed rear-facing basis. After seating,
    // both case and holder use the same hinge angle through complete closure.
    double initial_yaw=10*PSX_PI/180,roll=-3*PSX_PI/180;
    PsxVec iu={cos(initial_yaw),0,-sin(initial_yaw)};
    PsxVec iv={sin(PSX_PHI)*sin(initial_yaw),-cos(PSX_PHI),sin(PSX_PHI)*cos(initial_yaw)};
    PsxVec ru=psx_add(psx_mul(iu,cos(roll)),psx_mul(iv,sin(roll)));
    PsxVec rv=psx_add(psx_mul(iu,-sin(roll)),psx_mul(iv,cos(roll)));
    PsxVec u=cartridge_mix(ru,console_rotate((PsxVec){-1,0,0},yaw,lean),align);
    PsxVec v=cartridge_mix(rv,console_rotate(console_rotate((PsxVec){0,-1,0},0,angle),yaw,lean),align);
    // Turn the free case slightly in the hand, then square it to the holder.
    // The twist ends at .70, before the .72 feed; eject reverses that order.
    double twist=12*PSX_PI/180*psx_ease((time-.52)/.08)*(1-psx_ease((time-.64)/.06));
    PsxVec tilted_u=psx_add(psx_mul(u,cos(twist)),psx_mul(v,sin(twist)));
    v=psx_add(psx_mul(u,-sin(twist)),psx_mul(v,cos(twist)));
    u=tilted_u;
    psp_slab(r,art,centre,u,v,radius,media_origin);
    // SDL's textured case does not write the model depth buffer. Draw the door
    // once after it, so the closed cover occludes the complete seated shell.
    console_mesh_draw(&model->mesh,r,door,origin,true,false);
}
