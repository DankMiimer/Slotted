/* Original cel-shaded console renderer, copyright 2026, MIT.
 * Share SDL's offscreen colour buffer, with our own depth attachment. Attribute
 * slots 3..5 leave SDL's position/colour/UV pointers in slots 0..2 untouched. */
#define SDL_USE_BUILTIN_OPENGL_DEFINITIONS 1
#include <SDL_opengles2.h>
typedef struct { float position[3],normal[3],colour[3]; } ToonVertex;
typedef struct {
    ToonVertex *vertices;
    uint16_t *index_data;
    unsigned vertex_count,count,door;
    GLuint program,buffer,indices,depth,outline_indices;
    unsigned outline_count,outline_door;
    GLint transform,origin,outline,finish;
    float *uv;
    SDL_Surface *albedo;  /* borrowed from console_albedo_cache until upload */
    unsigned texture_width,texture_height;
    float paint_luma;
    GLuint uv_buffer,albedo_texture;
    GLint textured,sampler,paint_colour,paint_enabled,paint_reference;
    GLint cutout_uniform,unlit_uniform,swap_uniform;
    bool cutout,unlit,swap_rb;
    bool ready,exemplar,realistic,paintable;
    bool media_tinted;
    float media_tint[3];
    unsigned char *media_weights;
    /* Floor height and footprint (x left/right, z near/far) of the vertices within 4 units of the
     * lowest point, kept after the CPU copy is freed so a scene can stand other objects on it. */
    bool has_footprint;float floor_y,footprint[4];
    float front_contact[3];
} ConsoleMesh;

#define CONSOLE_GL_API(X) \
 X(void,GetIntegerv,(GLenum,GLint *)) \
 X(void,GetBooleanv,(GLenum,GLboolean *)) \
 X(GLboolean,IsEnabled,(GLenum)) \
 X(void,Enable,(GLenum)) X(void,Disable,(GLenum)) \
 X(GLuint,CreateShader,(GLenum)) X(void,ShaderSource,(GLuint,GLsizei,const GLchar **,const GLint *)) \
 X(void,CompileShader,(GLuint)) X(void,GetShaderiv,(GLuint,GLenum,GLint *)) \
 X(void,GetShaderInfoLog,(GLuint,GLsizei,GLsizei *,GLchar *)) X(void,DeleteShader,(GLuint)) \
 X(GLuint,CreateProgram,(void)) X(void,AttachShader,(GLuint,GLuint)) \
 X(void,BindAttribLocation,(GLuint,GLuint,const GLchar *)) X(void,LinkProgram,(GLuint)) \
 X(void,GetProgramiv,(GLuint,GLenum,GLint *)) X(void,GetProgramInfoLog,(GLuint,GLsizei,GLsizei *,GLchar *)) X(void,DeleteProgram,(GLuint)) \
 X(void,UseProgram,(GLuint)) X(GLint,GetUniformLocation,(GLuint,const GLchar *)) \
 X(void,UniformMatrix4fv,(GLint,GLsizei,GLboolean,const GLfloat *)) X(void,Uniform1f,(GLint,GLfloat)) \
 X(void,Uniform1i,(GLint,GLint)) X(void,Uniform3f,(GLint,GLfloat,GLfloat,GLfloat)) \
 X(void,ActiveTexture,(GLenum)) X(void,GenTextures,(GLsizei,GLuint *)) \
 X(void,BindTexture,(GLenum,GLuint)) X(void,TexParameteri,(GLenum,GLenum,GLint)) \
 X(void,TexImage2D,(GLenum,GLint,GLint,GLsizei,GLsizei,GLint,GLenum,GLenum,const void *)) \
 X(void,DeleteTextures,(GLsizei,const GLuint *)) X(GLenum,GetError,(void)) X(void,GenerateMipmap,(GLenum)) \
 X(void,GenBuffers,(GLsizei,GLuint *)) X(void,BindBuffer,(GLenum,GLuint)) \
 X(void,BufferData,(GLenum,GLsizeiptr,const void *,GLenum)) X(void,DeleteBuffers,(GLsizei,const GLuint *)) \
 X(void,EnableVertexAttribArray,(GLuint)) X(void,DisableVertexAttribArray,(GLuint)) \
 X(void,GetVertexAttribiv,(GLuint,GLenum,GLint *)) \
 X(void,VertexAttribPointer,(GLuint,GLint,GLenum,GLboolean,GLsizei,const void *)) \
 X(void,DrawElements,(GLenum,GLsizei,GLenum,const void *)) X(void,CullFace,(GLenum)) X(void,FrontFace,(GLenum)) \
 X(void,DepthFunc,(GLenum)) X(void,DepthMask,(GLboolean)) X(void,ClearDepthf,(GLfloat)) X(void,Clear,(GLbitfield)) \
 X(void,GenRenderbuffers,(GLsizei,GLuint *)) X(void,BindRenderbuffer,(GLenum,GLuint)) \
 X(void,RenderbufferStorage,(GLenum,GLenum,GLsizei,GLsizei)) \
 X(void,FramebufferRenderbuffer,(GLenum,GLenum,GLenum,GLuint)) \
 X(void,DeleteRenderbuffers,(GLsizei,const GLuint *)) X(GLenum,CheckFramebufferStatus,(GLenum))
#define GL_DECLARE(result,name,args) static result (GL_APIENTRY *cg##name) args;
CONSOLE_GL_API(GL_DECLARE)
#undef GL_DECLARE

extern SDL_Surface *IMG_Load_RW(SDL_RWops *source,int free_source);
/* Recently decoded albedos stay in RAM between scene opens: reopening the same
 * model re-uploads instead of decoding its PNG again. CPU pixels have no GL
 * context lifetime, unlike a cached texture name. Keyed by the PNG file hash;
 * an entry in use by a loaded-but-unopened mesh is never evicted. */
static struct { uint64_t hash; SDL_Surface *pixels; int users; double used; } console_albedo_cache[2];

static void console_albedo_release(SDL_Surface *pixels)
{
    if(!pixels)return;
    for(int i=0;i<2;i++)if(console_albedo_cache[i].pixels==pixels){console_albedo_cache[i].users--;return;}
    SDL_FreeSurface(pixels);  /* uncached: every slot was in use */
}

/* Read, verify and decode one albedo PNG. Touches no shared state, so the
 * frontend may run it on a worker thread while the user is still browsing. */
static SDL_Surface *console_albedo_read(const char *path,uint64_t expected,uint32_t w,uint32_t h)
{
    SDL_RWops *file=SDL_RWFromFile(path,"rb");
    Sint64 size=file?SDL_RWsize(file):-1;
    unsigned char *data=size>0&&size<(Sint64)64<<20?malloc((size_t)size):NULL;
    bool ok=data&&SDL_RWread(file,data,1,(size_t)size)==(size_t)size;
    if(file)SDL_RWclose(file);
    ok=ok&&console_vertex_hash(data,(size_t)size)==expected;
    SDL_Surface *png=ok?IMG_Load_RW(SDL_RWFromConstMem(data,(int)size),1):NULL;
    free(data);
    if(png&&png->format->format!=SDL_PIXELFORMAT_RGBA32){
        SDL_Surface *rgba=SDL_ConvertSurfaceFormat(png,SDL_PIXELFORMAT_RGBA32,0);SDL_FreeSurface(png);png=rgba;
    }
    if(!png||png->w!=(int)w||png->h!=(int)h||png->pitch!=(int)w*4){if(png)SDL_FreeSurface(png);return NULL;}
    return png;
}

static SDL_Surface *console_albedo_cached(uint64_t hash,uint32_t w,uint32_t h)
{
    for(int i=0;i<2;i++){
        SDL_Surface *p=console_albedo_cache[i].pixels;
        if(p&&console_albedo_cache[i].hash==hash&&p->w==(int)w&&p->h==(int)h){console_albedo_cache[i].used=now();return p;}
    }
    return NULL;
}

/* Insert an unused entry (users 0); returns false when every slot is in use. */
static bool console_albedo_store(SDL_Surface *pixels,uint64_t hash,int users)
{
    int slot=-1;
    for(int i=0;i<2;i++)if(!console_albedo_cache[i].users&&(slot<0||console_albedo_cache[i].used<console_albedo_cache[slot].used))slot=i;
    if(slot<0)return false;
    if(console_albedo_cache[slot].pixels)SDL_FreeSurface(console_albedo_cache[slot].pixels);
    console_albedo_cache[slot].pixels=pixels;console_albedo_cache[slot].hash=hash;
    console_albedo_cache[slot].users=users;console_albedo_cache[slot].used=now();return true;
}

/* At most one background decode; joined (adopted into the cache) before any
 * synchronous lookup so the main thread never races the worker. */
static struct { SDL_Thread *thread; SDL_atomic_t done; char path[PATH_CAP]; uint64_t hash; uint32_t w,h; SDL_Surface *result; } console_albedo_prefetch;
__attribute__((unused)) static int console_albedo_worker(void *unused)
{
    (void)unused;
    console_albedo_prefetch.result=console_albedo_read(console_albedo_prefetch.path,console_albedo_prefetch.hash,
                                                       console_albedo_prefetch.w,console_albedo_prefetch.h);
    SDL_AtomicSet(&console_albedo_prefetch.done,1);
    return 0;
}
static void console_albedo_join(void)
{
    if(!console_albedo_prefetch.thread)return;
    SDL_WaitThread(console_albedo_prefetch.thread,NULL);console_albedo_prefetch.thread=NULL;
    SDL_Surface *result=console_albedo_prefetch.result;console_albedo_prefetch.result=NULL;
    if(result&&(console_albedo_cached(console_albedo_prefetch.hash,result->w,result->h)
                ||!console_albedo_store(result,console_albedo_prefetch.hash,0)))SDL_FreeSurface(result);
}

static SDL_Surface *console_albedo_decode(const char *path,uint64_t expected,uint32_t w,uint32_t h)
{
    console_albedo_join();
    SDL_Surface *p=console_albedo_cached(expected,w,h);
    if(p){for(int i=0;i<2;i++)if(console_albedo_cache[i].pixels==p)console_albedo_cache[i].users++;return p;}
    double started=now();
    SDL_Surface *png=console_albedo_read(path,expected,w,h);
    if(png)console_albedo_store(png,expected,1);  /* uncached when all slots are in use */
    char timing[64];snprintf(timing,sizeof(timing),"albedo read+verify+decode %.0f ms",1000*(now()-started));log_event(timing);
    return png;
}

/* Frontend hint: decode a textured model's albedo ahead of its first scene.
 * Reads only the small sidecar header on the calling thread and never waits
 * for a running decode. Returns 1 when ready, 0 while pending (call again
 * later), -1 when the model has no valid texture sidecar. */
__attribute__((unused)) static int console_albedo_warm_part(const char *assets,const char *name,const char *part)
{
    char path[PATH_CAP];
    int n=snprintf(path,sizeof(path),"%s/consoles/%s/%s.texture",assets,name,part);
    if(n<0||n>=(int)sizeof(path))return -1;
    FILE *f=fopen(path,"rb");if(!f)return -1;
    unsigned char magic[8];uint32_t header[4];uint64_t hashes[3];
    bool ok=fread(magic,1,8,f)==8&&!memcmp(magic,"SCTEX003",8)&&fread(header,4,4,f)==4&&fread(hashes,8,3,f)==3;
    fclose(f);
    if(!ok||header[1]==0||header[2]==0||header[1]>4096||header[2]>4096)return -1;
    if(console_albedo_prefetch.thread){
        if(!SDL_AtomicGet(&console_albedo_prefetch.done))return 0;
        console_albedo_join();  /* finished: adopting it does not block */
    }
    if(console_albedo_cached(hashes[2],header[1],header[2]))return 1;
    n=snprintf(console_albedo_prefetch.path,sizeof(console_albedo_prefetch.path),"%s/consoles/%s/%s.albedo.png",assets,name,part);
    if(n<0||n>=(int)sizeof(console_albedo_prefetch.path))return -1;
    console_albedo_prefetch.hash=hashes[2];console_albedo_prefetch.w=header[1];console_albedo_prefetch.h=header[2];
    SDL_AtomicSet(&console_albedo_prefetch.done,0);
    console_albedo_prefetch.thread=SDL_CreateThread(console_albedo_worker,"slot-albedo",NULL);
    return console_albedo_prefetch.thread?0:-1;
}
__attribute__((unused)) static int console_albedo_warm(const char *assets,const char *name)
{return console_albedo_warm_part(assets,name,"model");}

/* Optional versioned UV/albedo sidecar (SCTEX003). Legacy SCTOON2 meshes stay
 * unchanged. Vertex and index hashes bind the UVs to the exact topology before
 * paint; a hash of the albedo PNG's bytes binds that file. Alpha marks
 * repaintable plastic (relative to paint_luma), never output transparency. */
static void console_texture_load(ConsoleMesh *m,const char *assets,const char *name,const char *part)
{
    char path[PATH_CAP];
    int n=snprintf(path,sizeof(path),"%s/consoles/%s/%s.texture",assets,name,part);
    if(n<0||n>=(int)sizeof(path))return;
    FILE *f=fopen(path,"rb");if(!f)return;
    unsigned char magic[8];uint32_t count=0,w=0,h=0;float luma=0;uint64_t vertices=0,indices=0,file=0;
    bool ok=fread(magic,1,8,f)==8&&!memcmp(magic,"SCTEX003",8)
        &&fread(&count,4,1,f)==1&&fread(&w,4,1,f)==1&&fread(&h,4,1,f)==1&&fread(&luma,4,1,f)==1
        &&fread(&vertices,8,1,f)==1&&fread(&indices,8,1,f)==1&&fread(&file,8,1,f)==1
        &&count==m->vertex_count&&w>0&&h>0&&w<=4096&&h<=4096&&isfinite(luma)&&luma>=.02f&&luma<=1
        &&vertices==console_vertex_hash(m->vertices,(size_t)count*sizeof(ToonVertex))
        &&indices==console_vertex_hash(m->index_data,(size_t)m->count*2);
    if(ok){m->uv=malloc((size_t)count*2*sizeof(float));ok=m->uv&&fread(m->uv,2*sizeof(float),count,f)==count&&fgetc(f)==EOF;}
    fclose(f);
    if(ok)for(unsigned i=0;i<count*2;i++)if(!isfinite(m->uv[i])||m->uv[i]<0||m->uv[i]>1)ok=false;
    if(ok){
        n=snprintf(path,sizeof(path),"%s/consoles/%s/%s.albedo.png",assets,name,part);
        m->albedo=n>0&&n<(int)sizeof(path)?console_albedo_decode(path,file,w,h):NULL;
        ok=m->albedo!=NULL;
    }
    if(!ok){
        free(m->uv);m->uv=NULL;m->albedo=NULL;
        log_event("invalid texture sidecar; legacy vertex colours retained");return;
    }
    m->texture_width=w;m->texture_height=h;m->paint_luma=luma;
}

static bool console_mesh_load_part(ConsoleMesh *m,const char *assets,const char *name,const char *part)
{
    char path[PATH_CAP];
    int length=snprintf(path,sizeof(path),"%s/consoles/%s/%s.mesh",assets,name,part);
    if(length<0||length>=(int)sizeof(path))return false;
    FILE *f=fopen(path,"rb");if(!f)return false;
    unsigned char magic[8];uint32_t vertices=0,count=0,door=0;
    bool ok=fread(magic,1,8,f)==8&&!memcmp(magic,"SCTOON2\0",8)
        &&fread(&vertices,4,1,f)==1&&fread(&count,4,1,f)==1&&fread(&door,4,1,f)==1
        &&vertices>0&&vertices<=65535&&count>0&&count<=600000&&count%3==0&&door<=count&&door%3==0;
    if(ok){
        m->vertices=malloc((size_t)vertices*sizeof(ToonVertex));m->index_data=malloc((size_t)count*2);
        ok=m->vertices&&m->index_data&&fread(m->vertices,sizeof(ToonVertex),vertices,f)==vertices
            &&fread(m->index_data,2,count,f)==count&&fgetc(f)==EOF;
    }
    fclose(f);
    if(ok)for(unsigned i=0;i<vertices;i++)for(int j=0;j<9;j++){
        float value=((float *)&m->vertices[i])[j];
        if(!isfinite(value)||fabsf(value)>(j<3?1000:2))ok=false;
    }
    if(ok)for(unsigned i=0;i<count;i++)if(m->index_data[i]>=vertices)ok=false;
    if(!ok){free(m->vertices);free(m->index_data);m->vertices=NULL;m->index_data=NULL;return false;}
    m->vertex_count=vertices;m->count=count;m->door=door;
    console_texture_load(m,assets,name,part);
    if(strncmp(part,"media",5)==0){
        snprintf(path,sizeof(path),"%s/consoles/%s/%s.paint.mask",assets,name,part);
        FILE *mask=fopen(path,"rb");
        if(mask){
            unsigned char header[8];uint32_t n=0;uint64_t hash=0;
            bool valid=fread(header,1,8,mask)==8&&!memcmp(header,"SCPAINT1",8)
                &&fread(&n,4,1,mask)==1&&fread(&hash,8,1,mask)==1&&n==vertices
                &&hash==console_vertex_hash(m->vertices,(size_t)vertices*sizeof(ToonVertex));
            unsigned char *weights=valid?malloc(vertices):NULL;
            valid=valid&&weights&&fread(weights,1,vertices,mask)==vertices&&fgetc(mask)==EOF;
            if(valid)m->media_weights=weights;else free(weights);
            fclose(mask);
        }
    }
    m->realistic=console_style_ready(name)&&console_realistic();
    m->paintable=console_appearance_ready(name)&&!strcmp(part,"model");
    const ConsolePaint *paint=console_appearance_ready(name)?console_paint():NULL;
    if(paint&&!strcmp(part,"model")){
        snprintf(path,sizeof(path),"%s/consoles/%s/paint.mask",assets,name);
        FILE *mask=fopen(path,"rb");
        if(mask){
            unsigned char header[8];uint32_t n=0;uint64_t hash=0;
            bool valid=fread(header,1,8,mask)==8&&!memcmp(header,"SCPAINT1",8)
                &&fread(&n,4,1,mask)==1&&fread(&hash,8,1,mask)==1&&n==vertices
                &&hash==console_vertex_hash(m->vertices,(size_t)vertices*sizeof(ToonVertex));
            unsigned char *weights=valid?malloc(vertices):NULL;
            valid=valid&&weights&&fread(weights,1,vertices,mask)==vertices&&fgetc(mask)==EOF;
            if(valid)for(unsigned i=0;i<vertices;i++)if(weights[i])for(int c=0;c<3;c++)
                m->vertices[i].colour[c]=fminf(1.f,paint->rgb[c]*weights[i]/192.f);
            if(!valid)log_event("console paint mask unavailable or stale; original colours retained");
            free(weights);fclose(mask);
        }else log_event("console paint mask missing; original colours retained");
    }
    /* Every physical media shell shares the exemplars' thin hull and soft bands. */
    m->exemplar=!strcmp(name,"gb")||!strcmp(name,"psp")||!strcmp(name,"gbc")||!strcmp(name,"gba")
        ||!strcmp(name,"snes")||!strcmp(name,"snes-us")||!strcmp(name,"n64")||!strcmp(name,"psx")||!strcmp(name,"dreamcast")||!strncmp(part,"media",5);return true;
}

static bool console_mesh_load(ConsoleMesh *m,const char *assets,const char *name)
{
    return console_mesh_load_part(m,assets,name,"model");
}

static GLuint console_shader(GLenum type,const char *source)
{
    GLuint shader=cgCreateShader(type);cgShaderSource(shader,1,&source,NULL);cgCompileShader(shader);
    GLint status=0;cgGetShaderiv(shader,GL_COMPILE_STATUS,&status);
    if(!status){char message[512];cgGetShaderInfoLog(shader,sizeof(message),NULL,message);log_event(message);cgDeleteShader(shader);return 0;}
    return shader;
}

static bool console_mesh_open(ConsoleMesh *m,SDL_Renderer *r)
{
    SDL_RendererInfo info={0};SDL_GetRendererInfo(r,&info);
    if(!info.name||strcmp(info.name,"opengles2")||!m->vertices)return false;
    SDL_RenderFlush(r);
#define GL_LOAD(result,name,args) cg##name=(result (GL_APIENTRY *) args)SDL_GL_GetProcAddress("gl" #name);if(!cg##name){log_event("missing GLES function: gl" #name);return false;}
    CONSOLE_GL_API(GL_LOAD)
#undef GL_LOAD
    const char *vertex=
        "attribute vec3 aPosition,aNormal,aColour;attribute vec2 aUV;varying mediump vec2 vUV;uniform mat4 uTransform;"
        "uniform float uOrigin;uniform mediump float uOutline;varying mediump vec3 vNormal,vColour;"
        "void main(){if(uOutline>0.0&&dot(aNormal,aNormal)<.25){"
        "gl_Position=vec4(2.0,2.0,2.0,1.0);vNormal=vec3(0.0,0.0,1.0);vColour=vec3(0.0);return;}"
        "vec3 p=(uTransform*vec4(aPosition+aNormal*uOutline,1.0)).xyz;"
        "vNormal=mat3(uTransform)*aNormal;vColour=aColour;vUV=aUV;"
        "float d=p.y*.57357644+p.z*.81915204;float w=1.0-d/1200.0;"
        "gl_Position=vec4(p.x/360.0,((uOrigin-240.0)*w+p.z*.57357644-p.y*.81915204)/240.0,-d/900.0,w);}";
    const char *cel_fragment=
        "precision mediump float;varying mediump vec3 vNormal,vColour;uniform mediump float uOutline,uFinish;"
        "varying mediump vec2 vUV;uniform sampler2D uAlbedo;uniform float uTextured,uPaintEnabled,uLuma,uSwapRB;uniform vec3 uPaint;"
        "vec3 base(){if(uTextured<.5)return vColour;vec4 a=texture2D(uAlbedo,vUV);if(uSwapRB>.5)a=a.bgra;"
        "float l=dot(a.rgb,vec3(.299,.587,.114));return mix(a.rgb,uPaint*clamp(l/uLuma,.25,1.5),a.a*uPaintEnabled);}"
        "uniform float uCutout,uUnlit;"
        "void main(){if(uCutout>.5&&texture2D(uAlbedo,vUV).a<.5)discard;"
        "if(uUnlit>.5){gl_FragColor=vec4(base(),1.0);return;}"
        "if(uOutline>0.0){gl_FragColor=vec4(.025,.030,.040,1.0);return;}"
        "float light=dot(normalize(vNormal),normalize(vec3(-.45,.74,.50)));"
        "float band=light>.48?1.0:light>.12?mix(.72,.83,uFinish):mix(.50,.65,uFinish);"
        "gl_FragColor=vec4(base()*band,1.0);}";
    const char *realistic_fragment=
        "precision mediump float;varying mediump vec3 vNormal,vColour;"
        "varying mediump vec2 vUV;uniform sampler2D uAlbedo;uniform float uTextured,uPaintEnabled,uLuma,uSwapRB;uniform vec3 uPaint;"
        "vec3 base(){if(uTextured<.5)return vColour;vec4 a=texture2D(uAlbedo,vUV);if(uSwapRB>.5)a=a.bgra;"
        "float l=dot(a.rgb,vec3(.299,.587,.114));return mix(a.rgb,uPaint*clamp(l/uLuma,.25,1.5),a.a*uPaintEnabled);}"
        "uniform float uCutout,uUnlit;"
        "void main(){if(uCutout>.5&&texture2D(uAlbedo,vUV).a<.5)discard;"
        "if(uUnlit>.5){gl_FragColor=vec4(base(),1.0);return;}"
        "vec3 n=normalize(vNormal);"
        "float light=dot(n,normalize(vec3(-.45,.74,.50)));"
        "float diffuse=.40+.60*max(light,0.0);"
        "vec3 h=normalize(normalize(vec3(-.45,.74,.50))+vec3(0.0,.57357644,.81915204));"
        "float gloss=.10*pow(max(dot(n,h),0.0),24.0);"
        "gl_FragColor=vec4(base()*diffuse+vec3(gloss),1.0);}";
    const char *fragment=m->realistic?realistic_fragment:cel_fragment;
    GLuint vs=console_shader(GL_VERTEX_SHADER,vertex),fs=console_shader(GL_FRAGMENT_SHADER,fragment);
    if(!vs||!fs){if(vs)cgDeleteShader(vs);if(fs)cgDeleteShader(fs);return false;}
    m->program=cgCreateProgram();cgAttachShader(m->program,vs);cgAttachShader(m->program,fs);
    cgBindAttribLocation(m->program,3,"aPosition");cgBindAttribLocation(m->program,4,"aNormal");cgBindAttribLocation(m->program,5,"aColour");
    cgBindAttribLocation(m->program,6,"aUV");
    cgLinkProgram(m->program);cgDeleteShader(vs);cgDeleteShader(fs);
    GLint status=0;cgGetProgramiv(m->program,GL_LINK_STATUS,&status);
    if(!status){char message[512];cgGetProgramInfoLog(m->program,sizeof(message),NULL,message);log_event(message);return false;}
    m->transform=cgGetUniformLocation(m->program,"uTransform");m->origin=cgGetUniformLocation(m->program,"uOrigin");m->outline=cgGetUniformLocation(m->program,"uOutline");
    m->finish=cgGetUniformLocation(m->program,"uFinish");
    m->textured=cgGetUniformLocation(m->program,"uTextured");m->sampler=cgGetUniformLocation(m->program,"uAlbedo");
    m->paint_colour=cgGetUniformLocation(m->program,"uPaint");m->paint_enabled=cgGetUniformLocation(m->program,"uPaintEnabled");
    m->paint_reference=cgGetUniformLocation(m->program,"uLuma");
    m->cutout_uniform=cgGetUniformLocation(m->program,"uCutout");
    m->unlit_uniform=cgGetUniformLocation(m->program,"uUnlit");
    m->swap_uniform=cgGetUniformLocation(m->program,"uSwapRB");
    GLint previous=0;cgGetIntegerv(GL_ARRAY_BUFFER_BINDING,&previous);
    if(m->uv){
        GLint limit=0;cgGetIntegerv(GL_MAX_TEXTURE_SIZE,&limit);
        if(m->texture_width<=(unsigned)limit&&m->texture_height<=(unsigned)limit){
            GLint active=0,bound=0;cgGetIntegerv(GL_ACTIVE_TEXTURE,&active);cgActiveTexture(GL_TEXTURE0);
            cgGetIntegerv(GL_TEXTURE_BINDING_2D,&bound);
            /* GLES2 mipmaps need power-of-two sizes; minified 2x browse poses
             * otherwise alias printed source detail. Clear stale errors first. */
            bool mipmaps=!(m->texture_width&(m->texture_width-1))&&!(m->texture_height&(m->texture_height-1));
            double upload=now();
            while(cgGetError()!=GL_NO_ERROR){}
            cgGenTextures(1,&m->albedo_texture);cgBindTexture(GL_TEXTURE_2D,m->albedo_texture);
            cgTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,mipmaps?GL_LINEAR_MIPMAP_LINEAR:GL_LINEAR);
            cgTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
            cgTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);cgTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
            cgTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,m->texture_width,m->texture_height,0,GL_RGBA,GL_UNSIGNED_BYTE,m->albedo->pixels);
            if(mipmaps)cgGenerateMipmap(GL_TEXTURE_2D);
            GLenum error=cgGetError();
            char timing[64];snprintf(timing,sizeof(timing),"albedo upload+mipmaps %.0f ms",1000*(now()-upload));log_event(timing);
            cgBindTexture(GL_TEXTURE_2D,(GLuint)bound);cgActiveTexture((GLenum)active);
            if(error){cgDeleteTextures(1,&m->albedo_texture);m->albedo_texture=0;log_event("albedo upload failed; vertex colours retained");}
            else{
                cgGenBuffers(1,&m->uv_buffer);cgBindBuffer(GL_ARRAY_BUFFER,m->uv_buffer);
                cgBufferData(GL_ARRAY_BUFFER,(GLsizeiptr)m->vertex_count*2*sizeof(float),m->uv,GL_STATIC_DRAW);
                log_event("validated UV/albedo texture ready (simple lighting; no PBR)");
            }
        }else log_event("albedo exceeds GLES texture limit; vertex colours retained");
        free(m->uv);console_albedo_release(m->albedo);m->uv=NULL;m->albedo=NULL;
    }
    cgGenBuffers(1,&m->buffer);cgBindBuffer(GL_ARRAY_BUFFER,m->buffer);
    cgBufferData(GL_ARRAY_BUFFER,(GLsizeiptr)m->vertex_count*sizeof(ToonVertex),m->vertices,GL_STATIC_DRAW);
    cgBindBuffer(GL_ARRAY_BUFFER,(GLuint)previous);
    cgGetIntegerv(GL_ELEMENT_ARRAY_BUFFER_BINDING,&previous);
    cgGenBuffers(1,&m->indices);cgBindBuffer(GL_ELEMENT_ARRAY_BUFFER,m->indices);
    cgBufferData(GL_ELEMENT_ARRAY_BUFFER,(GLsizeiptr)m->count*2,m->index_data,GL_STATIC_DRAW);
    /* The shader clips ink/non-outlined panels before rasterization. Omit
     * those same triangles from the hull's index buffer to avoid processing
     * the complete detailed housing a second time. File format stays intact. */
    uint16_t *hull=m->exemplar?malloc((size_t)m->count*2):NULL;
    if(hull){
        for(unsigned i=0;i<m->count;i+=3){
            bool outlined=false;
            for(int j=0;j<3;j++){
                const float *n=m->vertices[m->index_data[i+j]].normal;
                if(n[0]*n[0]+n[1]*n[1]+n[2]*n[2]>=.25f)outlined=true;
            }
            if(outlined){memcpy(hull+m->outline_count,m->index_data+i,6);m->outline_count+=3;}
            if(i<m->door)m->outline_door=m->outline_count;
        }
        cgGenBuffers(1,&m->outline_indices);cgBindBuffer(GL_ELEMENT_ARRAY_BUFFER,m->outline_indices);
        cgBufferData(GL_ELEMENT_ARRAY_BUFFER,(GLsizeiptr)m->outline_count*2,hull,GL_STATIC_DRAW);
        free(hull);
    }
    cgBindBuffer(GL_ELEMENT_ARRAY_BUFFER,(GLuint)previous);free(m->index_data);m->index_data=NULL;
    if(m->vertex_count){
        float floor=m->vertices[0].position[1],left=1e9f,right=-1e9f,near=1e9f,far=-1e9f;
        for(unsigned i=1;i<m->vertex_count;i++)if(m->vertices[i].position[1]<floor)floor=m->vertices[i].position[1];
        double front_screen=-1e9,home_sin=sin(SLOT_HOME_YAW),home_cos=cos(SLOT_HOME_YAW);
        for(unsigned i=0;i<m->vertex_count;i++){
            const float *p=m->vertices[i].position;
            // Visible front edge of the lower housing (feet may be recessed behind an overhang).
            // Evaluate in the level home pose, independent of any preceding handheld camera.
            double z=-p[0]*home_sin+p[2]*home_cos;
            double screen=(z*sin(PSX_PHI)-p[1]*cos(PSX_PHI))*1200/(1200-p[1]*sin(PSX_PHI)-z*cos(PSX_PHI));
            if(screen>front_screen){front_screen=screen;memcpy(m->front_contact,p,3*sizeof(float));}
            if(p[1]>floor+4.f)continue;
            if(p[0]<left)left=p[0];
            if(p[0]>right)right=p[0];
            if(p[2]<near)near=p[2];
            if(p[2]>far)far=p[2];
        }
        if(left<=right){m->has_footprint=true;m->floor_y=floor;m->footprint[0]=left;m->footprint[1]=right;m->footprint[2]=near;m->footprint[3]=far;}
    }
    free(m->vertices);m->vertices=NULL;
    cgGetIntegerv(GL_RENDERBUFFER_BINDING,&previous);
    cgGenRenderbuffers(1,&m->depth);cgBindRenderbuffer(GL_RENDERBUFFER,m->depth);
    /* Sub-millimetre moulded seams need more precision than the 16-bit
     * buffer at our camera range. Keep the GLES2-compatible fallback. */
    GLenum depth_format=m->exemplar&&SDL_GL_ExtensionSupported("GL_OES_depth24")?0x81A6:GL_DEPTH_COMPONENT16;
    cgRenderbufferStorage(GL_RENDERBUFFER,depth_format,WIDTH,HEIGHT);
    cgBindRenderbuffer(GL_RENDERBUFFER,(GLuint)previous);
    m->ready=true;log_event("cel-shaded GLES mesh ready");return true;
}

static PsxVec console_rotate(PsxVec p,double yaw,double lean)
{
    double x=p.x*cos(yaw)+p.z*sin(yaw),z=-p.x*sin(yaw)+p.z*cos(yaw);
    return (PsxVec){x,p.y*cos(lean)-z*sin(lean),p.y*sin(lean)+z*cos(lean)};
}

static void console_matrix(float *matrix,double yaw,double lean)
{
    memset(matrix,0,16*sizeof(float));matrix[15]=1;
    PsxVec basis[]={{1,0,0},{0,1,0},{0,0,1}};
    for(int i=0;i<3;i++){PsxVec b=console_rotate(basis[i],yaw,lean);matrix[4*i]=b.x;matrix[4*i+1]=b.y;matrix[4*i+2]=b.z;}
}

/* The reading pose of a handheld: lean the device to face a screen toward the camera, and turn it about
 * the camera's own screen-up axis, expressed in the device's frame (the model's +Y for an upright
 * handheld, its rear -Z for the flat-modelled DS, the lid's up for an SP). The turn is then a horizontal
 * skew of the screen at any lean, never a roll in the image. Right-hand turn, like console_rotate's yaw. */
__attribute__((unused)) static void console_matrix_turn(float *matrix,double yaw,double lean)
{
    memset(matrix,0,16*sizeof(float));matrix[15]=1;
    const PsxVec camera_up={0,cos(PSX_PHI),-sin(PSX_PHI)};
    const PsxVec axis=console_rotate(camera_up,0,-lean);
    PsxVec basis[]={{1,0,0},{0,1,0},{0,0,1}};
    for(int i=0;i<3;i++){
        const PsxVec e=basis[i];
        const double along=axis.x*e.x+axis.y*e.y+axis.z*e.z;
        const PsxVec cross={axis.y*e.z-axis.z*e.y,axis.z*e.x-axis.x*e.z,axis.x*e.y-axis.y*e.x};
        const PsxVec turned={e.x*cos(yaw)+cross.x*sin(yaw)+axis.x*along*(1-cos(yaw)),
                             e.y*cos(yaw)+cross.y*sin(yaw)+axis.y*along*(1-cos(yaw)),
                             e.z*cos(yaw)+cross.z*sin(yaw)+axis.z*along*(1-cos(yaw))};
        const PsxVec b=console_rotate(turned,0,lean);
        matrix[4*i]=b.x;matrix[4*i+1]=b.y;matrix[4*i+2]=b.z;
    }
}

static bool console_mesh_draw_range(ConsoleMesh *m,SDL_Renderer *r,const float *transform,
                               double origin,unsigned first,unsigned count,
                               unsigned hull_first,unsigned hull_count,bool clear)
{
    if(!m->ready||first>m->count||count>m->count-first||first%3||count%3)return false;
    SDL_RenderFlush(r);
    GLint program,buffer,indices,front,cull,depthfunc,active,bound,uv_enabled;
    GLboolean depthmask;bool blend=cgIsEnabled(GL_BLEND),depth=cgIsEnabled(GL_DEPTH_TEST),
        culling=cgIsEnabled(GL_CULL_FACE),scissor=cgIsEnabled(GL_SCISSOR_TEST);
    cgGetIntegerv(GL_CURRENT_PROGRAM,&program);cgGetIntegerv(GL_ARRAY_BUFFER_BINDING,&buffer);
    cgGetIntegerv(GL_ELEMENT_ARRAY_BUFFER_BINDING,&indices);
    cgGetIntegerv(GL_FRONT_FACE,&front);cgGetIntegerv(GL_CULL_FACE_MODE,&cull);cgGetIntegerv(GL_DEPTH_FUNC,&depthfunc);cgGetBooleanv(GL_DEPTH_WRITEMASK,&depthmask);
    cgFramebufferRenderbuffer(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_RENDERBUFFER,m->depth);
    if(cgCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE){m->ready=false;log_event("console depth attachment unavailable");return false;}
    cgGetIntegerv(GL_ACTIVE_TEXTURE,&active);cgActiveTexture(GL_TEXTURE0);cgGetIntegerv(GL_TEXTURE_BINDING_2D,&bound);
    cgGetVertexAttribiv(6,GL_VERTEX_ATTRIB_ARRAY_ENABLED,&uv_enabled);
    cgDisable(GL_BLEND);cgDisable(GL_SCISSOR_TEST);cgEnable(GL_DEPTH_TEST);cgDepthFunc(GL_LESS);cgDepthMask(GL_TRUE);
    if(clear){cgClearDepthf(1);cgClear(GL_DEPTH_BUFFER_BIT);}
    cgUseProgram(m->program);cgUniformMatrix4fv(m->transform,1,GL_FALSE,transform);cgUniform1f(m->origin,origin);
    cgUniform1f(m->finish,m->exemplar?1.f:0.f);
    cgUniform1f(m->cutout_uniform,m->cutout?1.f:0.f);
    cgUniform1f(m->unlit_uniform,m->unlit?1.f:0.f);
    cgUniform1f(m->swap_uniform,m->swap_rb?1.f:0.f);
    cgUniform1f(m->textured,m->albedo_texture?1.f:0.f);cgUniform1i(m->sampler,0);
    const ConsolePaint *paint=m->paintable?console_paint():NULL;cgUniform1f(m->paint_enabled,(paint||m->media_tinted)?1.f:0.f);
    cgUniform1f(m->paint_reference,m->paint_luma>0?m->paint_luma:.55f);
    cgUniform3f(m->paint_colour,m->media_tinted?m->media_tint[0]:paint?paint->rgb[0]:1.f,
        m->media_tinted?m->media_tint[1]:paint?paint->rgb[1]:1.f,m->media_tinted?m->media_tint[2]:paint?paint->rgb[2]:1.f);
    cgBindTexture(GL_TEXTURE_2D,m->albedo_texture);
    if(m->uv_buffer){cgBindBuffer(GL_ARRAY_BUFFER,m->uv_buffer);cgEnableVertexAttribArray(6);cgVertexAttribPointer(6,2,GL_FLOAT,GL_FALSE,0,NULL);}
    else cgDisableVertexAttribArray(6);
    cgBindBuffer(GL_ARRAY_BUFFER,m->buffer);
    cgBindBuffer(GL_ELEMENT_ARRAY_BUFFER,m->indices);
    GLint sdl_attributes[3];
    for(int i=0;i<3;i++){
        cgGetVertexAttribiv(i,GL_VERTEX_ATTRIB_ARRAY_ENABLED,&sdl_attributes[i]);
        cgDisableVertexAttribArray(i);
    }
    for(int i=0;i<3;i++){cgEnableVertexAttribArray(3+i);cgVertexAttribPointer(3+i,3,GL_FLOAT,GL_FALSE,sizeof(ToonVertex),(const void *)(uintptr_t)(i*3*sizeof(float)));}
    cgEnable(GL_CULL_FACE);cgFrontFace(GL_CW);
    const void *offset=(const void *)(uintptr_t)(first*2);
    cgCullFace(GL_FRONT);cgUniform1f(m->outline,m->exemplar?.4f:1.35f);
    if(!m->realistic&&m->outline_indices){
        cgBindBuffer(GL_ELEMENT_ARRAY_BUFFER,m->outline_indices);
        if(hull_count)cgDrawElements(GL_TRIANGLES,hull_count,GL_UNSIGNED_SHORT,(const void *)(uintptr_t)(hull_first*2));
        cgBindBuffer(GL_ELEMENT_ARRAY_BUFFER,m->indices);
    }else if(!m->realistic)cgDrawElements(GL_TRIANGLES,count,GL_UNSIGNED_SHORT,offset);
    cgCullFace(GL_BACK);cgUniform1f(m->outline,0);cgDrawElements(GL_TRIANGLES,count,GL_UNSIGNED_SHORT,offset);
    for(int i=0;i<3;i++)cgDisableVertexAttribArray(3+i);
    for(int i=0;i<3;i++)if(sdl_attributes[i])cgEnableVertexAttribArray(i);
    cgBindBuffer(GL_ARRAY_BUFFER,(GLuint)buffer);cgUseProgram((GLuint)program);
    cgBindBuffer(GL_ELEMENT_ARRAY_BUFFER,(GLuint)indices);
    cgFrontFace((GLenum)front);cgCullFace((GLenum)cull);cgDepthFunc((GLenum)depthfunc);cgDepthMask(depthmask);
    if(!culling)cgDisable(GL_CULL_FACE);
    if(!depth)cgDisable(GL_DEPTH_TEST);
    if(blend)cgEnable(GL_BLEND);
    if(scissor)cgEnable(GL_SCISSOR_TEST);
    if(uv_enabled)cgEnableVertexAttribArray(6);else cgDisableVertexAttribArray(6);
    cgBindTexture(GL_TEXTURE_2D,(GLuint)bound);cgActiveTexture((GLenum)active);
    return true;
}

static bool console_mesh_draw(ConsoleMesh *m,SDL_Renderer *r,const float *transform,
                               double origin,bool door,bool clear)
{
    return console_mesh_draw_range(m,r,transform,origin,door?m->door:0,
        door?m->count-m->door:m->door,door?m->outline_door:0,
        door?m->outline_count-m->outline_door:m->outline_door,clear);
}

static void console_hinge_matrix(float *out,const float *global,PsxVec hinge,double angle)
{
    float local[16];console_matrix(local,0,angle);memset(out,0,16*sizeof(float));
    PsxVec p=console_rotate(hinge,0,angle);
    local[12]=hinge.x-p.x;local[13]=hinge.y-p.y;local[14]=hinge.z-p.z;
    for(int col=0;col<4;col++)for(int row=0;row<4;row++)for(int k=0;k<4;k++)
        out[col*4+row]+=global[k*4+row]*local[col*4+k];
}

static void console_mesh_close(ConsoleMesh *m)
{
    free(m->media_weights);m->media_weights=NULL;
    free(m->vertices);free(m->index_data);m->vertices=NULL;m->index_data=NULL;
    free(m->uv);console_albedo_release(m->albedo);m->uv=NULL;m->albedo=NULL;
    if(cgDeleteBuffers&&m->uv_buffer)cgDeleteBuffers(1,&m->uv_buffer);
    if(cgDeleteTextures&&m->albedo_texture)cgDeleteTextures(1,&m->albedo_texture);
    if(cgDeleteBuffers&&m->buffer)cgDeleteBuffers(1,&m->buffer);
    if(cgDeleteBuffers&&m->indices)cgDeleteBuffers(1,&m->indices);
    if(cgDeleteBuffers&&m->outline_indices)cgDeleteBuffers(1,&m->outline_indices);
    if(cgDeleteRenderbuffers&&m->depth)cgDeleteRenderbuffers(1,&m->depth);
    if(cgDeleteProgram&&m->program)cgDeleteProgram(m->program);
    memset(m,0,sizeof(*m));
}
