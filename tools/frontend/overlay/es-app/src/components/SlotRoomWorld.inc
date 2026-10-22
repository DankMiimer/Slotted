// Main-thread persistent-room renderer. The stream still prepares immutable cores (MIT).
namespace {
struct RoomWorld {
    WorldProfile profile;Mesh surroundings,selector;
    std::vector<Mesh> surfaces; // replaces `surroundings` when the profile sets any surface
    std::set<std::string> calibrated;
    Mat root=identity();int tableCount=0,visibleTables=0;
    std::map<std::string,Mat> tablePoses;
    explicit RoomWorld(const WorldProfile&p):profile(p){}
};
Mat roomRoot(SlotTabletop*s){
    if(!s->world)return identity();
    auto&world=*s->world;auto found=world.profile.tables.find(s->layout.tableAsset);
    if(found==world.profile.tables.end())throw std::runtime_error("No world position for table model "+s->layout.tableAsset);
    if(!world.profile.authored&&world.calibrated.insert(found->first).second){
        // A one-time starter suggestion, never applied to authored world positions.
        float bottom=1e9f;const auto&scale=s->layout.tableScale;
        const auto orientation=product(rotate(0,radians(found->second.rotation.y),0),slot_scene::scale(scale.x,scale.y,scale.z));
        for(int k=0;k<8;k++)bottom=std::min(bottom,transform(orientation,{k&1?s->table.high.x:s->table.low.x,k&2?s->table.high.y:s->table.low.y,k&4?s->table.high.z:s->table.low.z}).y);
        found->second.position.y=world.profile.floor-bottom;
    }
    const WorldLayout placed(s->layout.nodes[0],found->second);return placed.root;
}
Mesh roomMesh(SlotTabletop*s,const WorldProfile&p){
    std::vector<Vertex> vertices;std::vector<uint16_t> indices;
    auto face=[&](Vec a,Vec b,Vec c,Vec d,Vec normal,Vec color){
        const uint16_t first=uint16_t(vertices.size());
        for(auto v:{a,b,c,d})vertices.push_back({{v.x,v.y,v.z},{normal.x,normal.y,normal.z},{color.x,color.y,color.z},{0,0}});
        for(int i:{0,1,2,0,2,3})indices.push_back(first+i);
    };
    const float y=p.floor,h=y+p.height;
    face({p.left,y,p.front},{p.right,y,p.front},{p.right,y,p.back},{p.left,y,p.back},{0,1,0},{.20f,.22f,.24f});
    face({p.left,y,p.back},{p.right,y,p.back},{p.right,h,p.back},{p.left,h,p.back},{0,0,1},{.38f,.40f,.42f});
    face({p.left,y,p.front},{p.left,y,p.back},{p.left,h,p.back},{p.left,h,p.front},{1,0,0},{.34f,.36f,.38f});
    face({p.right,y,p.back},{p.right,y,p.front},{p.right,h,p.front},{p.right,h,p.back},{-1,0,0},{.34f,.36f,.38f});
    return makeMesh(s,vertices,indices);
}
// A surface texture multiplied by its colour on the CPU (the scene shader shows a texture
// instead of the vertex colour), mipmapped when power-of-two like the scene's other images.
GLuint surfaceTexture(SlotTabletop*s,const WorldSurface&surface,Gpu&held){
    SDL_Surface*p=decodeImage(s->prepared+"/surfaces/"+surface.texture+".png");
    const bool rgb=p->format->format==SDL_PIXELFORMAT_RGB24;const int bytes=rgb?3:4;const float tint[3]={surface.color.x,surface.color.y,surface.color.z};
    GLint maxSize;glGetIntegerv(GL_MAX_TEXTURE_SIZE,&maxSize);
    if(p->w>maxSize||p->h>maxSize||(p->pitch!=p->w*bytes&&p->pitch!=((p->w*bytes+3)&~3))){SDL_FreeSurface(p);throw std::runtime_error("Unsupported surface texture: "+surface.texture);}
    for(int y=0;y<p->h;y++){auto*row=(unsigned char*)p->pixels+y*p->pitch;for(int x=0;x<p->w;x++)for(int c=0;c<3;c++){auto&v=row[x*bytes+c];v=(unsigned char)std::lround(v*tint[c]);}}
    UploadScope upload(s);GLuint t=0;glGenTextures(1,&t);glBindTexture(GL_TEXTURE_2D,t);glPixelStorei(GL_UNPACK_ALIGNMENT,p->pitch==p->w*bytes?1:4);
    glTexImage2D(GL_TEXTURE_2D,0,rgb?GL_RGB:GL_RGBA,p->w,p->h,0,rgb?GL_RGB:GL_RGBA,GL_UNSIGNED_BYTE,p->pixels);glPixelStorei(GL_UNPACK_ALIGNMENT,1);
    const bool pot=((p->w&(p->w-1))==0&&(p->h&(p->h-1))==0)||s->npotMips;
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,pot?GL_LINEAR_MIPMAP_LINEAR:GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);if(pot)glGenerateMipmap(GL_TEXTURE_2D);
    if(pot&&s->anisotropy>1)glTexParameterf(GL_TEXTURE_2D,0x84FE,s->anisotropy); // GL_TEXTURE_MAX_ANISOTROPY_EXT
    held=lease(s,t,true,(size_t)p->w*p->h*4*(pot?4.f/3:1));SDL_FreeSurface(p);return t;
}
// The room box when the profile sets surfaces: floor, the three walls and (if set) the ceiling
// as separate meshes. A textured face is one quad per tile, each spanning the texture's whole
// 0..1 range: the scene shader clamps UVs (labels crop with them), so repeats come from geometry.
// Unset floor/walls keep their original colours.
std::vector<Mesh> roomSurfaces(SlotTabletop*s,const WorldProfile&p){
    struct Face {Vec origin,u,v,normal,color;}; // u runs right, v down the texture as seen from inside
    const float y=p.floor,h=y+p.height,w=p.right-p.left,d=p.front-p.back;
    auto length=[](Vec v){return std::sqrt(dot(v,v));};
    std::vector<Mesh> meshes;
    auto build=[&](const WorldSurface&surface,const std::vector<Face>&faces){
        Gpu held;GLuint texture=0;
        if(surface.set&&!surface.texture.empty()){
            // A missing or unreadable texture keeps the room open with the original colours.
            try{texture=surfaceTexture(s,surface,held);}
            catch(const std::exception&e){std::fprintf(stderr,"Tabletop: room %s texture unavailable (%s)\n",surface.texture.c_str(),e.what());}
        }
        float tile=texture?surface.tile:1e9f;
        auto quads=[&]{size_t n=0;for(const auto&f:faces)n+=size_t(std::ceil(length(f.u)/tile))*size_t(std::ceil(length(f.v)/tile));return n;};
        while(quads()*4>60000)tile*=1.25f; // 16-bit indices
        std::vector<Vertex> vertices;std::vector<uint16_t> indices;
        for(const auto&f:faces){
            const Vec color=surface.set&&surface.texture.empty()?surface.color:f.color;
            const float lu=length(f.u),lv=length(f.v);const int nu=int(std::ceil(lu/tile)),nv=int(std::ceil(lv/tile));
            for(int i=0;i<nu;i++)for(int j=0;j<nv;j++){
                const float u0=i*tile/lu,u1=std::min(1.f,(i+1)*tile/lu),v0=j*tile/lv,v1=std::min(1.f,(j+1)*tile/lv);
                const float right=texture?(u1-u0)*lu/tile:0,bottom=texture?(v1-v0)*lv/tile:0;
                const float corners[4][2]={{u0,v0},{u1,v0},{u1,v1},{u0,v1}},uv[4][2]={{0,0},{right,0},{right,bottom},{0,bottom}};
                const uint16_t first=uint16_t(vertices.size());
                for(int k=0;k<4;k++){const Vec at=add(f.origin,add(mul(f.u,corners[k][0]),mul(f.v,corners[k][1])));vertices.push_back({{at.x,at.y,at.z},{f.normal.x,f.normal.y,f.normal.z},{color.x,color.y,color.z},{uv[k][0],uv[k][1]}});}
                for(int k:{0,1,2,0,2,3})indices.push_back(uint16_t(first+k));
            }
        }
        Mesh m=makeMesh(s,vertices,indices);m.texture=texture;m.textureLease=held;meshes.push_back(std::move(m));
    };
    build(p.surfaces[SurfaceFloor],{{{p.left,y,p.back},{w,0,0},{0,0,d},{0,1,0},{.20f,.22f,.24f}}});
    build(p.surfaces[SurfaceWall],{{{p.left,h,p.back},{w,0,0},{0,-p.height,0},{0,0,1},{.38f,.40f,.42f}},
                                  {{p.left,h,p.front},{0,0,-d},{0,-p.height,0},{1,0,0},{.34f,.36f,.38f}},
                                  {{p.right,h,p.back},{0,0,d},{0,-p.height,0},{-1,0,0},{.34f,.36f,.38f}}});
    if(p.surfaces[SurfaceCeiling].set)build(p.surfaces[SurfaceCeiling],{{{p.left,h,p.back},{w,0,0},{0,0,d},{0,-1,0},{.34f,.36f,.38f}}});
    return meshes;
}
Mesh roomSelector(SlotTabletop*s){
    std::vector<Vertex> vertices;std::vector<uint16_t> indices;
    auto strip=[&](float left,float bottom,float right,float top){
        const uint16_t first=uint16_t(vertices.size());
        for(auto p:{Vec{left,bottom,0},Vec{right,bottom,0},Vec{right,top,0},Vec{left,top,0}})
            vertices.push_back({{p.x,p.y,p.z},{0,0,1},{1,.82f,.27f},{0,0}});
        for(int i:{0,1,2,0,2,3})indices.push_back(first+i);
    };
    strip(-.5f,-.5f,.5f,-.492f);strip(-.5f,.492f,.5f,.5f);
    strip(-.5f,-.492f,-.492f,.492f);strip(.492f,-.492f,.5f,.492f);
    return makeMesh(s,vertices,indices);
}
// Defined after SceneStream, with access to the existing transient wave clocks.
void roomDraws(SlotTabletop*s);
}
bool slot_tabletop_world(SlotTabletop*s,const char*path){
    if(!s||s->stream)return false;
    WorldProfile profile;
    if(path&&*path&&!readWorldProfile(path,profile)){s->error="Invalid room world profile";return false;}
    if(!profile.tables.count(s->layout.tableAsset)){s->error="World profile omits active table";return false;}
    SDL_GL_MakeCurrent(s->window,s->context);
    try{
        auto room=std::make_shared<RoomWorld>(profile);
        if(worldHasSurfaces(profile))room->surfaces=roomSurfaces(s,profile);else room->surroundings=roomMesh(s,profile);
        room->selector=roomSelector(s);s->world=std::move(room);
        s->world->root=roomRoot(s);s->cacheValid=false;
        SDL_GL_MakeCurrent(s->window,s->owner);return true;
    }catch(const std::exception&e){s->world.reset();s->error=e.what();SDL_GL_MakeCurrent(s->window,s->owner);return false;}
}
bool slot_tabletop_world_table(SlotTabletop*s,const char*model,float matrix[16]){
    if(!s||!s->world||!model||!matrix)return false;
    auto it=s->world->tablePoses.find(model);if(it==s->world->tablePoses.end())return false;
    std::copy(it->second.v,it->second.v+16,matrix);return true;
}
bool slot_tabletop_world_stats(SlotTabletop*s,int counts[2]){
    if(!s||!s->world||!counts)return false;counts[0]=s->world->tableCount;counts[1]=s->world->visibleTables;return true;
}
bool slot_tabletop_world_transform(SlotTabletop*s,float matrix[16]){
    if(!s||!s->world||!matrix)return false;
    std::copy(s->world->root.v,s->world->root.v+16,matrix);return true;
}
bool slot_tabletop_appearance(SlotTabletop*s,bool cel,const char*paint){
    if(!s||!s->world||!paint)return false;
    const std::set<std::string> allowed={"original","black","white","red","blue","purple","green","yellow"};
    if(!allowed.count(paint))return false;
    if(s->cel!=cel||s->paint!=paint){s->cel=cel;s->paint=paint;s->cacheValid=false;}
    return true;
}
const char* slot_tabletop_television(SlotTabletop*s){return s?s->tv.c_str():"";}
