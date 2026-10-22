/* Native optical disc, MIT. Console, spindle, disc and lid share depth.
 * SDL_RenderGeometry projects to 2D and cannot preserve these intersections. */
static bool optical_disc_prepare(ConsoleMesh *m,SDL_Renderer *r)
{
    if(m->ready)return true;
    if(m->count)return false; /* Failed setup: keep the fallback until close. */
    enum {N=96,V=N*8,I=N*24};
    m->count=I; /* Also latch allocation failures; close frees partial setup. */
    m->vertices=calloc(V,sizeof(ToonVertex));m->index_data=malloc(I*sizeof(uint16_t));
    float uv[V*2];unsigned at=0;
    if(!m->vertices||!m->index_data)return false;
    m->vertex_count=V;m->count=I;m->door=I;m->realistic=true;m->unlit=true;
    for(int i=0;i<N;i++){
        double a=i*2*PSX_PI/N,b=(i+1)*2*PSX_PI/N;
        double x[]={cos(a)/8,cos(a),cos(b),cos(b)/8};
        double z[]={sin(a)/8,sin(a),sin(b),sin(b)/8};
        for(int side=0;side<2;side++)for(int k=0;k<4;k++){
            unsigned j=i*8+side*4+k;
            m->vertices[j]=(ToonVertex){{x[k],-side,z[k]},{0,side?-1:1,0},{.22f,.23f,.25f}};
            uv[j*2]=.5f+x[k]*.5f;uv[j*2+1]=.5f+z[k]*.5f;
        }
    }
    /* Contiguous front, underside, then outer/bore rims. */
    for(int group=0;group<4;group++)for(int i=0;i<N;i++){
        unsigned j=i*8;uint16_t q[4];
        if(group==0){q[0]=j;q[1]=j+3;q[2]=j+2;q[3]=j+1;}
        else if(group==1){q[0]=j+4;q[1]=j+5;q[2]=j+6;q[3]=j+7;}
        else if(group==2){q[0]=j+1;q[1]=j+2;q[2]=j+6;q[3]=j+5;}
        else {q[0]=j+3;q[1]=j;q[2]=j+4;q[3]=j+7;}
        uint16_t tri[]={q[0],q[1],q[2],q[0],q[2],q[3]};
        memcpy(m->index_data+at,tri,sizeof(tri));at+=6;
    }
    if(!console_mesh_open(m,r))return false;
    GLint previous;cgGetIntegerv(GL_ARRAY_BUFFER_BINDING,&previous);
    cgGenBuffers(1,&m->uv_buffer);cgBindBuffer(GL_ARRAY_BUFFER,m->uv_buffer);
    cgBufferData(GL_ARRAY_BUFFER,sizeof(uv),uv,GL_STATIC_DRAW);
    cgBindBuffer(GL_ARRAY_BUFFER,(GLuint)previous);
    return true;
}

static bool optical_disc_draw(CartridgeArt *model,SDL_Renderer *r,PsxArt *art,
                             PsxVec centre,PsxVec u,PsxVec v,double radius,double thickness,double origin)
{
    ConsoleMesh *m=&model->disc_mesh;
    if(!optical_disc_prepare(m,r))return false;
    PsxVec n=psx_mul(psx_cross(u,v),-1);
    float transform[]={u.x*radius,u.y*radius,u.z*radius,0,
        n.x*thickness,n.y*thickness,n.z*thickness,0,v.x*radius,v.y*radius,v.z*radius,0,
        centre.x,centre.y,centre.z,1};
    SDL_RenderFlush(r);
    /* Reuse the housing's depth contents. Keep ownership of our own attachment
     * so close never destroys the housing or an SDL-owned artwork texture. */
    GLuint own_depth=m->depth;m->depth=model->mesh.depth;
    bool ok=true;
    for(int side=0;side<3;side++){
        GLint texture=0;
        if(side<2){
            SDL_Texture *source=side?art->underside:art->disc;
            Uint32 format=0;SDL_QueryTexture(source,&format,NULL,NULL,NULL);
            m->swap_rb=format==SDL_PIXELFORMAT_BGRA32||format==SDL_PIXELFORMAT_BGRX32;
            if(SDL_GL_BindTexture(source,NULL,NULL)){ok=false;break;}
            cgGetIntegerv(GL_TEXTURE_BINDING_2D,&texture);
            SDL_GL_UnbindTexture(source);
        }
        m->albedo_texture=(GLuint)texture;m->cutout=side<2;
        unsigned first=side*96*6,count=(side==2?2:1)*96*6;
        if(!console_mesh_draw_range(m,r,transform,origin,first,count,0,0,false))ok=false;
        m->albedo_texture=0;
    }
    m->depth=own_depth;m->albedo_texture=0;
    return ok;
}
