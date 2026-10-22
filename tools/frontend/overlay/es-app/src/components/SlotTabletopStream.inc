// Included by SlotTabletop.cpp after the native asset loaders (MIT).
namespace {
struct StreamRequest {std::string system,tv,gba,key;std::vector<Item> items;uint64_t generation=0;};
std::string coreKey(const std::string&system,const std::string&tv,const std::string&gba){return system+"|"+tv+"|"+gba;}
bool memoryPressure(){std::ifstream in("/proc/meminfo");std::string line;while(std::getline(in,line))if(line.find("MemAvailable:")==0){std::istringstream value(line.substr(13));unsigned long long kb=0;value>>kb;return kb<256u*1024;}return false;}
void copyCore(SlotTabletop&to,const SlotTabletop&from){
    const bool world=bool(to.world),cel=to.cel;const auto paint=to.paint;
    to.root=from.root;to.prepared=from.prepared;to.system=from.system;to.tv=from.tv;to.paint=from.paint;to.cel=from.cel;to.gbaChoice=from.gbaChoice;to.ignoreLayout=from.ignoreLayout;
    to.pool=from.pool;to.logicalWidth=from.logicalWidth;to.logicalHeight=from.logicalHeight;to.width=from.width;to.height=from.height;to.npotMips=from.npotMips;to.anisotropy=from.anisotropy;
    to.table=from.table;to.television=from.television;for(int i=0;i<2;i++)to.consoles[i]=from.consoles[i];to.consoleCount=from.consoleCount;
    to.media=from.media;to.layout=from.layout;to.authored=from.authored;to.layoutBottom=from.layoutBottom;to.layoutMediaLow=from.layoutMediaLow;to.layoutMediaKnown=from.layoutMediaKnown;
    to.triangles=from.triangles;to.textures=from.textures;to.imageLeases=from.imageLeases;
    to.home=from.home;to.bootstrapHome=from.bootstrapHome;to.homeLayout=from.homeLayout;to.homeItems=from.homeItems;
    if(world){to.cel=cel;to.paint=paint;}
}
double millis(Uint64 from,Uint64 to){return 1000.0*(to-from)/SDL_GetPerformanceFrequency();}
struct SceneStream {
    std::mutex mutex;std::condition_variable wake;std::thread worker;SlotUploadContext upload;
    bool stop=false,motion=false,ticket=true,uploading=false,failed=false;uint64_t desired=0,active=0;std::atomic<uint64_t>loads{0},uploads{0};
    std::deque<StreamRequest> jobs;std::map<std::string,std::shared_ptr<SlotTabletop>> cores;std::deque<std::string> lru;std::string homeKey;
    std::shared_ptr<SlotTabletop> candidate,base;StreamRequest wanted;SlotTabletop*owner=nullptr;std::string failure;
    // Main-thread choreography. 0 stable, 1 same room preparing new items, 2 departure
    // (lifts on the input frame, holds while preparing, then flies), 3 arrival,
    // 4 landing wiggle and saved-camera pan.
    int phase=0;float elapsed=0,arrival=0,tvExitStart=0;bool televisionChanges=false;
    // Departure seconds at which the destination was ready. A retarget back to this
    // room before then lowers the lifted waves again instead of flying them away.
    float release=systemWaiting;bool returning=false;float touchdownAt=systemTouchdownSeconds,arrivalEnd=systemArrivalSeconds;
    // A held lift is still, so the GPU uploads continue then. SLOT_SCENE_LIFT_UPLOADS=1
    // also allows them while it lifts (A/B evidence only).
    bool liftUploads=false;
    // A ready destination with meshes the render context has not drawn often enough has them drawn
    // first, on a still frame of the hold (warmPending, see warmDestination), and only then flies.
    std::shared_ptr<SlotTabletop> warmPending;std::weak_ptr<SlotTabletop> warmedFor;uint64_t warmGeneration=0;std::string warmKey;    // Home table <-> console room: that room's console stays (departAnchor: its group here, -2 a
    // room's console, -100 none) and glides to its pose on the other side (arrivalAnchor). A
    // retarget elsewhere releases it at anchorReleased and it flies like the rest. Home consoles
    // leave and land in waves ordered by distance from it (rank: group -> wave index).
    std::string anchorSystem;int departAnchor=-100,arrivalAnchor=-100;float anchorReleased=-1;Mat anchorFrom=identity();std::vector<int> rank;
    SlotTabletopFrame previous,last;Vec fromEye={},fromTarget={};float fromFov=0;
    Mat fromTV=identity(),fromStatus=identity(),fromTable=identity();
    // A different table asset is a different room: the old table (kept with its
    // GPU leases) slides out on the old view while the new one slides in on its own.
    bool tableChanges=false,slidePlanned=false;float tableLift=0;TableSlide slide;Model oldTable;Vec toEye={},toTarget={};float toFov=0;
    // World mode keeps both furniture instances fixed. Only hardware/camera move.
    std::string fromTableModel;Mat fromRoot=identity();WorldPath worldPath;float travelSeconds=0;
    Vec fromConsole={0,0,0};
    float exitEnd()const{const float start=televisionChanges?tvExitStart:0;return release>=systemWaiting?systemWaiting:systemDepartureSeconds+start+departureHold(release-start);}
    float lifted()const{return departureLifted(televisionChanges?tvExitStart:-1);}
    // Worker-only preparation timing for the stream log.
    Uint64 began=0;double waited=0,uploaded=0,longest=0;uint64_t job=0;
    // Worker-only: while an upload waits for a still frame (the lift), the worker
    // decodes the request's remaining images, in loading order, on the CPU.
    // Decoded-but-unconsumed surfaces are capped (aheadBytes): a TV's 4096^2 textures are
    // 48-64 MB each, and unbounded decoding beside GPU uploads ran the device out of memory (ar).
    std::deque<std::string> ahead;std::map<std::string,SDL_Surface*> decoded;int decodedAhead=0;size_t decodedBytes=0;
    static size_t surfaceBytes(const SDL_Surface*p){return p?size_t(p->pitch)*p->h:0;}
    static constexpr size_t aheadBytes=64u*1024*1024;
    FILE*log=nullptr;
    SceneStream(SlotTabletop*s):owner(s){base=std::make_shared<SlotTabletop>();copyCore(*base,*s);base->samples=s->samples;base->imageLeases.clear();base->table={};base->television={};for(auto&c:base->consoles)c={};base->media.clear();}
    ~SceneStream(){if(log)std::fclose(log);}
    void event(const char*name,uint64_t generation,const std::string&key,const std::string&detail=""){if(log){std::fprintf(log,"%u\t%s\t%llu\t%s\t%zu%s%s\n",SDL_GetTicks(),name,(unsigned long long)generation,key.c_str(),base->pool->retired->bytes.load(),detail.empty()?"":"\t",detail.c_str());std::fflush(log);}}
    // (Locked.) A prefetch yields to a waiting request for another room and, for its
    // own room, is awaited like that request (no reused-frame ticket needed).
    bool superseded(const StreamRequest&r)const{return stop||(r.generation&&r.generation!=desired)||(!r.generation&&!jobs.empty()&&jobs.front().generation&&jobs.front().key!=r.key);}
    bool awaited(const StreamRequest&r)const{return r.generation||(!jobs.empty()&&jobs.front().generation&&jobs.front().key==r.key);}
    void check(const StreamRequest&r){
        std::lock_guard<std::mutex> lock(mutex);
        if(superseded(r))throw std::runtime_error("Scene preparation superseded");
    }
    void begin(const StreamRequest&r){
        const Uint64 asked=SDL_GetPerformanceCounter();
        std::unique_lock<std::mutex> lock(mutex);
        for(;;){
            if(superseded(r))throw std::runtime_error("Scene upload superseded");
            if(!motion&&(ticket||awaited(r)))break;
            if(ahead.empty()||decodedBytes>=aheadBytes){wake.wait(lock);continue;}
            const std::string path=ahead.front();ahead.pop_front();lock.unlock();
            try{if(!decoded.count(path)){SDL_Surface*p=decodeImage(path);decoded[path]=p;decodedBytes+=surfaceBytes(p);decodedAhead++;}}catch(const std::exception&){} // image() reports it
            lock.lock();
        }
        ticket=false;uploading=true;began=SDL_GetPerformanceCounter();waited+=millis(asked,began);
    }
    // Images this request will load and the GPU does not already hold.
    void plan(const StreamRequest&r,const SlotTabletop*cached){
        clearDecoded();
        auto albedo=[&](const std::string&mesh){const std::string stem=mesh.substr(0,mesh.size()-5);if(exists(stem+".texture")&&!pooled(base.get(),stem+".albedo.png"))ahead.push_back(stem+".albedo.png");};
        if(r.system=="home"){if(!cached)for(const auto&i:r.items)albedo(consoleMesh(base->root,i.model,r.gba));return;}
        if(!cached){
            albedo(consoleMesh(base->root,r.system,r.gba));const std::string regional=regionalConsole(r.system);
            if(!regional.empty()&&exists(base->root+"/consoles/"+regional+"/model.mesh"))albedo(consoleMesh(base->root,regional,r.gba));
        }
        std::set<std::string> models={r.system};for(const auto&i:r.items)models.insert(i.model);
        for(const auto&m:models){OpticalRegistration optical;if(opticalRegistration(m,optical)||(cached&&cached->media.count(m)))continue;const std::string b=mediaBase(base->root,m);albedo(b+".mesh");if(exists(b+"-label.mesh"))albedo(b+"-label.mesh");}
        for(const auto&i:r.items)if(!i.face.empty()&&!pooled(base.get(),i.face)&&std::find(ahead.begin(),ahead.end(),i.face)==ahead.end())ahead.push_back(i.face);
        // A TV this room has not loaded: its prepared textures (a PVM's four 4096^2 PNGs were
        // ~3.7 s of serial decoding on a first visit, aq), last, within the aheadBytes cap.
        if(!cached){std::lock_guard<std::mutex> lock(base->pool->mutex);if(base->pool->rooms.count(base->prepared+"/"+r.tv))return;}
        if(!cached)for(const auto&path:preparedTextures(base->prepared+"/"+r.tv))if(!pooled(base.get(),path)&&std::find(ahead.begin(),ahead.end(),path)==ahead.end())ahead.push_back(path);
    }
    // The loader's image: decoded ahead, or now claimed so it is not decoded twice.
    SDL_Surface*take(const std::string&path){ahead.erase(std::remove(ahead.begin(),ahead.end(),path),ahead.end());auto i=decoded.find(path);if(i==decoded.end())return nullptr;SDL_Surface*p=i->second;decoded.erase(i);decodedBytes-=std::min(decodedBytes,surfaceBytes(p));return p;}
    void clearDecoded(){for(auto&d:decoded)SDL_FreeSurface(d.second);decoded.clear();ahead.clear();decodedAhead=0;decodedBytes=0;}
    void finish(){
        glFinish();const double took=millis(began,SDL_GetPerformanceCounter());uploaded+=took;longest=std::max(longest,took);
        {std::lock_guard<std::mutex> lock(mutex);uploading=false;uploads++;}wake.notify_all();
        char detail[48];std::snprintf(detail,sizeof(detail),"upload_ms=%.1f",took);event("upload",job,"",detail);
    }
    void cache(const std::string&key,std::shared_ptr<SlotTabletop>core){
        if(owner->world&&core->home)homeKey=key;
        cores[key]=std::move(core);lru.erase(std::remove(lru.begin(),lru.end(),key),lru.end());lru.push_back(key);
        auto evict=[&](bool budget)->bool{
            const bool pressure=memoryPressure();
            // The soft GPU budget alone also keeps the two newest cores: the room just
            // prepared and the other neighbour prefetch. Evicting a prefetch as it was cached
            // made the next request prepare it again (8 per trial, up to 7 s on a TV change).
            const size_t newest=budget&&!pressure?2:0;
            for(size_t n=0;n+newest<lru.size();n++){
                const auto oldest=lru.begin()+n;
                // The one home core is the navigation hub. Keep it among the same
                // three bounded entries instead of repeatedly reloading all consoles.
                // Actual low-memory pressure may still evict it; no quality changes.
                if(owner->world&&!pressure&&*oldest==homeKey&&lru.size()>1)continue;
                event("evict",job,*oldest);cores.erase(*oldest);lru.erase(oldest);return true;
            }
            return false;
        };
        while(lru.size()>3&&evict(false)){}
        const size_t soft=768u*1024*1024;
        while((base->pool->retired->bytes>soft||memoryPressure())&&lru.size()>1&&evict(true)){}
        while((base->pool->retired->bytes>soft||memoryPressure())&&base->pool->roomLru.size()>1){base->pool->rooms.erase(base->pool->roomLru.front());base->pool->roomLru.pop_front();}
        std::lock_guard<std::mutex> lock(base->pool->mutex);
        for(auto i=base->pool->images.begin();i!=base->pool->images.end();)if(i->second.expired())i=base->pool->images.erase(i);else ++i;
    }
    void run(){
        if(!upload.bind()){std::lock_guard<std::mutex> lock(mutex);failure="Could not open scene upload context";failed=true;return;}
        for(;;){
            StreamRequest r;{std::unique_lock<std::mutex> lock(mutex);wake.wait(lock,[&]{return stop||!jobs.empty();});if(stop)break;r=std::move(jobs.front());jobs.pop_front();}
            const Uint64 started=SDL_GetPerformanceCounter();const uint64_t before=uploads;job=r.generation;waited=uploaded=longest=0;
            try{
                if(!r.generation&&memoryPressure())continue;
                check(r);auto stage=std::make_shared<SlotTabletop>();
                auto existing=cores.find(r.key);const bool hit=existing!=cores.end();plan(r,hit?existing->second.get():nullptr);
                auto hooks=[&](SlotTabletop*t){t->checkPreparation=[&,r]{check(r);};t->beginUpload=[&,r]{begin(r);};t->endUpload=[&]{finish();};t->takeDecoded=[&](const std::string&p){return take(p);};};
                auto unhook=[](SlotTabletop*t){t->checkPreparation={};t->beginUpload={};t->endUpload={};t->takeDecoded={};};
                if(hit)copyCore(*stage,*existing->second);
                else{
                    stage->root=base->root;stage->prepared=base->prepared;stage->system=r.system;stage->tv=r.tv;stage->gbaChoice=r.gba;stage->pool=base->pool;
                    stage->cel=base->cel;stage->paint=base->paint;
                    stage->logicalWidth=base->logicalWidth;stage->logicalHeight=base->logicalHeight;stage->width=base->width;stage->height=base->height;stage->npotMips=base->npotMips;stage->anisotropy=base->anisotropy;stage->ignoreLayout=base->ignoreLayout;
                    hooks(stage.get());loadScene(stage.get());unhook(stage.get());
                    cache(r.key,stage);loads++;
                    auto working=std::make_shared<SlotTabletop>();copyCore(*working,*stage);stage=std::move(working);
                }
                hooks(stage.get());
                for(const auto&requested:r.items){check(r);Item item=requested;if(r.system!="home"){media(stage.get(),item.model);if(!item.face.empty()){item.texture=image(stage.get(),item.face,true);item.textureLease=stage->imageLeases.at(item.face);}}stage->items.push_back(std::move(item));}
                unhook(stage.get());glFinish();check(r);
                // Preparation split: waiting for a still frame (decoding ahead meanwhile), GPU upload (with completion) and the rest (CPU).
                char detail[192];std::snprintf(detail,sizeof(detail),"prepare_ms=%.0f wait_ms=%.0f upload_ms=%.0f uploads=%llu max_upload_ms=%.1f cached=%d decoded_ahead=%d unused=%zu",
                    millis(started,SDL_GetPerformanceCounter()),waited,uploaded,(unsigned long long)(uploads-before),longest,hit,decodedAhead,decoded.size());clearDecoded();
                {std::lock_guard<std::mutex> lock(mutex);if(r.generation&&r.generation==desired){candidate=stage;failed=false;event("ready",r.generation,r.key,detail);}}
                if(!r.generation)event("prefetched",0,r.key,detail);
            }catch(const std::exception&e){std::lock_guard<std::mutex> lock(mutex);if(!stop&&r.generation&&r.generation==desired){failure=e.what();failed=true;std::fprintf(stderr,"Tabletop stream: %s\n",e.what());}}
            clearDecoded();
        }
        clearDecoded();cores.clear();base->pool->retired->drain();glFinish();upload.unbind();
    }
};
void stopStream(SlotTabletop*s){
    if(!s->stream)return;auto stream=s->stream;
    {std::lock_guard<std::mutex> lock(stream->mutex);stream->stop=true;stream->candidate.reset();stream->jobs.clear();}stream->wake.notify_all();
    if(stream->worker.joinable())stream->worker.join();s->stream.reset();
}
Mat blendedTransform(const Mat&a,const Mat&b,float t){
    if(t<=0)return a;if(t>=1)return b;Mat x=a,y=b;float sa[3],sb[3];
    for(int c=0;c<3;c++){sa[c]=std::sqrt(a.v[c*4]*a.v[c*4]+a.v[c*4+1]*a.v[c*4+1]+a.v[c*4+2]*a.v[c*4+2]);sb[c]=std::sqrt(b.v[c*4]*b.v[c*4]+b.v[c*4+1]*b.v[c*4+1]+b.v[c*4+2]*b.v[c*4+2]);for(int k=0;k<3;k++){x.v[c*4+k]/=std::max(.00001f,sa[c]);y.v[c*4+k]/=std::max(.00001f,sb[c]);}}
    Mat r=blendRotation(x,y,t);for(int c=0;c<3;c++)for(int k=0;k<3;k++)r.v[c*4+k]*=sa[c]+(sb[c]-sa[c])*t;
    for(int k=12;k<15;k++)r.v[k]=a.v[k]+(b.v[k]-a.v[k])*t;return r;
}
// The destination's meshes (and the texture each is drawn with) that the render context has
// drawn fewer than warmDraws() times; each mesh once.
std::vector<std::pair<const Mesh*,GLuint>> coldMeshes(const SlotTabletop*s,const SlotTabletop&c){
    std::vector<std::pair<const Mesh*,GLuint>> out;std::set<const GpuResource*> seen;
    auto add=[&](const Mesh&m,GLuint texture){if(m.vertices&&m.count&&!m.hidden&&m.indexLease&&seen.insert(m.indexLease.get()).second&&drawUses(s,m)<warmDraws())out.push_back({&m,texture});};
    for(auto&m:c.table.parts)add(m,m.texture);for(auto&m:c.television.parts)add(m,m.texture);
    for(int i=0;i<c.consoleCount;i++){const auto&k=c.consoles[i];for(auto&m:k.model.parts)add(m,m.texture);add(k.power,k.power.texture);add(k.led,k.led.texture);add(k.lid,k.lid.texture);for(auto&f:k.flaps)add(f.mesh,f.mesh.texture);}
    for(const auto&h:c.homeItems){const auto&k=h.console;for(auto&m:k.model.parts)add(m,m.texture);add(k.power,k.power.texture);add(k.led,k.led.texture);add(k.lid,k.lid.texture);for(auto&f:k.flaps)add(f.mesh,f.mesh.texture);}
    for(auto&m:c.media){GLuint label=0;for(auto&i:c.items)if(i.model==m.first&&i.texture){label=i.texture;break;}add(m.second.shell,m.second.shell.texture);add(m.second.label,label);}
    return out;
}
// On the current render context: room `c`'s cold meshes, logged as `warmed`.
bool warmRoom(SlotTabletop*s,SceneStream&st,const SlotTabletop&c,uint64_t generation,const std::string&key,bool incremental=false){
    const Uint64 start=SDL_GetPerformanceCounter();const auto meshes=coldMeshes(s,c);std::string rounds;const long triangles=warmMeshes(s,meshes,rounds,incremental);
    char detail[160];std::snprintf(detail,sizeof(detail),"warm_ms=%.0f meshes=%zu triangles=%ld rounds_ms=%s",millis(start,SDL_GetPerformanceCounter()),meshes.size(),triangles,rounds.c_str());
    const bool done=coldMeshes(s,c).empty();st.event(done?"warmed":"warm-step",generation,key,detail);return done;
}
// Before this frame draws: the pending destination.
void warmDestination(SlotTabletop*s,SceneStream&st){
    if(!st.warmPending)return;
    if(st.warmGeneration!=st.desired){st.warmPending.reset();return;}
    auto c=st.warmPending;
    if(warmRoom(s,st,*c,st.warmGeneration,st.warmKey,bool(s->world))){st.warmedFor=c;st.warmPending.reset();}
}
// Home consoles leave and land nearest-first from the anchor (else from the highlighted one).
void homeRanks(const SlotTabletop*s,SceneStream&st,int anchor){
    st.rank.assign(s->homeItems.size(),0);if(!s->home)return;
    int from=anchor>=0?anchor:-1;for(size_t i=0;from<0&&i<s->homeItems.size();i++)if(homeEntry(s,i)==s->selected)from=(int)i;
    const Vec origin=from>=0?transform(s->homeItems[from].pose,{0,0,0}):transform(s->tvPose,{0,0,0});
    std::vector<std::pair<float,int>> order;for(size_t i=0;i<s->homeItems.size();i++){const Vec p=sub(transform(s->homeItems[i].pose,{0,0,0}),origin);order.push_back({dot(p,p),(int)i});}
    std::sort(order.begin(),order.end());int wave=0;for(const auto&o:order)if(o.second!=anchor)st.rank[o.second]=wave++;
}
// The anchor of a departure toward st.wanted, decided when the hardware starts lifting.
void planAnchor(const SlotTabletop*s,SceneStream&st){
    st.departAnchor=-100;st.anchorReleased=-1;st.anchorSystem.clear();
    if(s->home&&st.wanted.system!="home"){for(size_t i=0;i<s->homeItems.size();i++)if(homeSystem(s->homeItems[i].model)==st.wanted.system&&homeEntry(s,i)>=0){st.departAnchor=(int)i;st.anchorSystem=st.wanted.system;}}
    else if(!s->home&&st.wanted.system=="home"){st.departAnchor=-2;st.anchorSystem=s->system;}
    homeRanks(s,st,st.departAnchor);
}
// The hardware starts lifting on the input frame; preparation continues meanwhile.
void depart(SlotTabletop*s,SceneStream&st,bool television){
    planAnchor(s,st);st.phase=2;st.elapsed=0;st.release=systemWaiting;st.returning=false;st.tvExitStart=0;st.tableLift=0;st.tableChanges=false;st.televisionChanges=television;
    {std::lock_guard<std::mutex> lock(st.mutex);if(!st.liftUploads)st.motion=true;}
    st.event("depart",st.desired,st.wanted.key);
}
// A newer request that waited for the landing: same room swaps items, else depart.
void follow(SlotTabletop*s,SceneStream&st,const SlotTabletopFrame&input){
    st.previous=input;st.previous.screen=st.previous.handheldScreen=0;st.elapsed=0;
    if(st.wanted.key==coreKey(s->system,s->tv,s->gbaChoice))st.phase=1;else depart(s,st,s->tv!=st.wanted.tv);
}
SlotTabletopFrame streamFrame(SlotTabletop*s,const SlotTabletopFrame&input){
    if(!s->stream)return input;auto&st=*s->stream;std::shared_ptr<SlotTabletop> ready;
    {std::lock_guard<std::mutex> lock(st.mutex);if(!st.uploading)ready=st.candidate;}
    if(ready&&s->world){
        std::string problem;
        if(!s->world->profile.tables.count(ready->layout.tableAsset))problem="Requested layout has no room table position";
        const auto existing=s->world->tablePoses.find(ready->layout.tableAsset);
        if(existing!=s->world->tablePoses.end()){
            const auto&pose=existing->second;const auto&scale=ready->layout.tableScale;
            const float wanted[3]={scale.x,scale.y,scale.z};
            for(int c=0;c<3;c++){
                const float actual=std::sqrt(pose.v[c*4]*pose.v[c*4]+pose.v[c*4+1]*pose.v[c*4+1]+pose.v[c*4+2]*pose.v[c*4+2]);
                if(std::abs(actual-wanted[c])>.0001f)problem="Saved layouts use different scales for the same room table";
            }
        }
        if(!problem.empty()){s->error=problem;std::lock_guard<std::mutex> lock(st.mutex);st.failure=problem;st.failed=true;st.candidate.reset();ready.reset();}
    }
    {std::lock_guard<std::mutex> lock(st.mutex);if(st.failed){s->error=st.failure;st.phase=0;st.motion=false;st.televisionChanges=false;return input;}}
    const std::string current=coreKey(s->system,s->tv,s->gbaChoice);
    if(st.phase==1&&ready&&current==st.wanted.key){
        for(auto&n:ready->items)for(auto&o:s->items)if(n.id==o.id){n.hover=o.hover;n.hoverVelocity=o.hoverVelocity;n.fade=o.fade;}
        s->items=ready->items;for(auto&m:ready->media)s->media.emplace(m.first,m.second);
        for(auto&p:s->labelTextures)s->imageLeases.erase(p.first);
        s->labelTextures=ready->labelTextures;for(auto&p:ready->imageLeases)s->imageLeases[p.first]=p.second;
        if(s->hasResident&&!s->resident.face.empty()){s->labelTextures[s->resident.face]=s->resident.texture;s->imageLeases[s->resident.face]=s->resident.textureLease;}
        trimLabels(s);s->cacheValid=false;
        std::lock_guard<std::mutex> lock(st.mutex);st.active=st.desired;st.candidate.reset();st.phase=0;st.event("items",st.active,st.wanted.key);
    }else if(st.phase==1&&current!=st.wanted.key)depart(s,st,s->tv!=st.wanted.tv);
    const float dt=std::max(0.f,std::min(.05f,input.delta));
    if(st.phase==2){
        // Back to this room before the flight: the lifted waves settle again in reverse.
        st.returning=!s->bootstrapHome&&st.release>=systemWaiting&&st.wanted.key==current;
        if(st.returning){
            st.elapsed=std::min(st.elapsed,st.lifted())-dt;
            if(st.elapsed<=0){st.elapsed=0;st.returning=false;st.televisionChanges=false;st.phase=1;st.event("returned",st.desired,current);}
        }else{
            st.elapsed+=dt;
            if(ready){
                // A retarget may change the table; its TV and status then leave too.
                st.tableChanges=s->layout.tableAsset!=ready->layout.tableAsset;
                if((st.tableChanges||s->tv!=ready->tv)&&!st.televisionChanges){st.televisionChanges=true;st.tvExitStart=st.elapsed;}
                if(st.release>=systemWaiting){
                    // New meshes are drawn first, once everything is lifted and still.
                    if(warmDraws()>0&&st.warmedFor.lock()!=ready&&!coldMeshes(s,*ready).empty()){if(st.elapsed>=st.lifted()){st.warmPending=ready;st.warmGeneration=st.desired;st.warmKey=st.wanted.key;}}
                    else{st.release=st.elapsed;st.event("release",st.desired,st.wanted.key);}
                }
            }
            // The old table lifts as the last wave leaves, then slides on commit.
            st.tableLift=st.tableChanges&&!s->world?30*flightEase((st.elapsed-(st.exitEnd()-.11f))/.11f):0;
            if(st.elapsed>=st.exitEnd()&&ready){
                st.fromEye=s->cameraEye;st.fromTarget=s->cameraTarget;st.fromFov=s->cameraFov;st.fromTV=s->tvPose;st.fromStatus=s->statusPose;
                st.fromTable=product(s->layout.nodes[0].matrix(),scale(s->layout.tableScale.x,s->layout.tableScale.y,s->layout.tableScale.z));
                if(s->world){
                    st.fromRoot=roomRoot(s);st.fromTableModel=s->layout.tableAsset;
                    st.fromTable=product(st.fromRoot,st.fromTable);st.fromTV=product(st.fromRoot,st.fromTV);st.fromStatus=product(st.fromRoot,st.fromStatus);
                    st.fromConsole=transform(st.fromRoot,transform(s->consolePose,{0,0,0}));
                    st.worldPath=worldPath(s->world->profile,s->layout.tableAsset,ready->layout.tableAsset);st.travelSeconds=st.worldPath.seconds;
                }
                if(st.tableChanges){st.oldTable=s->table;st.slidePlanned=false;}
                // The anchor console's last pose here, and its group on the other side.
                st.arrivalAnchor=-100;
                if(st.departAnchor!=-100&&st.anchorReleased<0){
                    st.anchorFrom=product(translate({0,(s->reducedMotion?3:12)*flightEase(st.elapsed/.2f),0}),st.departAnchor==-2?s->consolePose:s->homeItems[st.departAnchor].pose);
                    if(s->world)st.anchorFrom=product(st.fromRoot,st.anchorFrom);
                    if(ready->home){for(size_t i=0;i<ready->homeItems.size();i++)if(homeSystem(ready->homeItems[i].model)==st.anchorSystem&&homeEntry(ready.get(),i)>=0)st.arrivalAnchor=(int)i;}
                    else if(ready->system==st.anchorSystem)st.arrivalAnchor=-2;
                }
                s->cached.clear();s->calls.clear();copyCore(*s,*ready);s->items=ready->items;s->labelTextures=ready->labelTextures;
                s->resident={};s->hasResident=false;s->selected=-1;s->selectedSince=input.seconds;s->orbitReady=false;s->cameraView=-1;s->cameraSelection=-1;s->panTime=0;s->cacheValid=false;
                for(size_t i=0;i<s->homeItems.size();i++){Placement at=s->homeItems[i].at;s->homeItems[i].pose=consoleModel(s->homeItems[i].console,at);s->homeItems[i].hover=s->homeItems[i].lift=0;}
                if(!s->home)s->consolePose=consoleModel(s->consoles[0],consolePlacement(s,0));
                homeRanks(s,st,st.arrivalAnchor>=0?st.arrivalAnchor:-1);
                const float slide=s->world?st.travelSeconds:st.tableChanges?tableArrivalDelay:0;st.phase=3;st.elapsed=0;st.arrival=0;st.touchdownAt=systemTouchdownSeconds+slide;st.arrivalEnd=systemArrivalSeconds+slide;
                std::lock_guard<std::mutex> lock(st.mutex);st.active=st.desired;st.candidate.reset();st.event("commit",st.active,st.wanted.key);
            }
        }
    }else if(st.phase==3||st.phase==4){
        st.arrival+=dt;const bool newer=st.active!=st.desired;
        // The saved-view pan begins as the last wave touches down; its wiggle settles meanwhile.
        if(st.phase==3&&!newer&&st.arrival>=st.touchdownAt){st.phase=4;st.elapsed=0;s->cacheValid=false;st.event("landed",st.active,current);}
        else if(st.phase==4)st.elapsed+=dt;
        if(st.arrival>=st.arrivalEnd){
            if(st.tableChanges){st.tableChanges=false;st.oldTable={};s->cacheValid=false;}
            if(newer){if(st.phase==3)st.event("landed",st.active,current);follow(s,st,input);}
            else if(st.phase==4){
                const int goal=input.cameraView<0?s->layout.browseView:input.cameraView;
                if(st.elapsed>=(goal==0?0:std::min(systemPanSeconds,s->layout.transitionSeconds))){st.phase=0;s->cacheValid=false;st.event("settled",st.active,current);}
            }
        }
    }
    SlotTabletopFrame frame=input;
    if(st.phase==1||st.phase==2){frame=st.previous;frame.delta=input.delta;frame.seconds=input.seconds;frame.screen=frame.handheldScreen=0;}
    // Incoming hardware lands in the author's literal everything view. Only
    // as the last wave touches down does panCamera see the saved view.
    if(st.phase==3){frame.cameraView=0;frame.automatic=false;frame.yaw=frame.elevation=0;frame.selected=-1;}
    if(st.phase==0||st.phase==3||st.phase==4)st.last=input;
    s->panLimit=st.phase==4?systemPanSeconds:0;
    {std::lock_guard<std::mutex> lock(st.mutex);
        const bool flying=st.release<systemWaiting&&st.elapsed<st.exitEnd(),lifting=!st.liftUploads&&st.elapsed<st.lifted();
        st.motion=(st.phase==2&&(st.returning||lifting||flying))||st.phase==3||st.phase==4||input.phase||input.inspection>0||input.power>0||input.zoom>0;
        if(st.motion)st.ticket=false;
    }
    st.wake.notify_all();return frame;
}
void streamCamera(SlotTabletop*s){
    if(s->world)return; // one world camera is evaluated after all local poses are queued
    if(!s->stream||s->stream->phase!=3)return;auto&st=*s->stream;
    st.toEye=s->cameraEye;st.toTarget=s->cameraTarget;st.toFov=s->cameraFov; // this room's own, unblended view
    const float seconds=st.tableChanges?tableSlideSeconds:systemRoomSeconds;if(st.arrival>=seconds)return;float q=flightEase(st.arrival/seconds);
    s->cameraEye=mix(st.fromEye,s->cameraEye,q);s->cameraTarget=mix(st.fromTarget,s->cameraTarget,q);s->cameraFov=st.fromFov+(s->cameraFov-st.fromFov)*q;
    s->eyeView=lookAt(s->cameraEye,s->cameraTarget);s->projectionFov=s->cameraFov;s->view=product(perspective(s->projectionFov,(float)s->width/s->height,150,10000),s->eyeView);
}
void streamDraws(SlotTabletop*s){
    if(s->world){roomDraws(s);return;}
    if(!s->stream)return;auto&st=*s->stream;
    // Arrival flights continue through the landing wiggle, into the saved-view pan.
    const bool departing=st.phase==2,arriving=(st.phase==3||st.phase==4)&&st.arrival<st.arrivalEnd;if(!departing&&!arriving)return;
    const float q=flightEase(st.arrival/systemRoomSeconds),aspect=(float)s->width/s->height;
    Mat currentTable=product(s->layout.nodes[0].matrix(),scale(s->layout.tableScale.x,s->layout.tableScale.y,s->layout.tableScale.z));
    const bool slide=arriving&&st.tableChanges;Mat newTable=identity(),oldTable=identity();
    if(slide){
        const Mat from=lookAt(st.fromEye,st.fromTarget),to=lookAt(st.toEye,st.toTarget),current=lookAt(s->cameraEye,s->cameraTarget);
        if(!st.slidePlanned){
            st.slide=planTableSlide(from,std::tan(st.fromFov/2),product(translate({0,st.tableLift,0}),st.fromTable),st.oldTable.low,st.oldTable.high,
                                    to,std::tan(st.toFov/2),currentTable,s->table.low,s->table.high,aspect);
            st.slidePlanned=true;
        }
        // Both tables move the same way in lockstep; the new one arrives lifted,
        // settles and bounces once while the hardware follows it in.
        const float t=st.arrival,e=flightEase(t/tableSlideSeconds),currentTan=std::tan(s->cameraFov/2);
        const float lift=30*(1-flightEase((t/tableSlideSeconds-.62f)/.38f))+std::abs(landingSpring(t-tableSlideSeconds))*6;
        newTable=translate({0,lift,0});
        if(t<tableSlideSeconds){
            newTable=product(screenAttached(current,currentTan,to,std::tan(st.toFov/2),-st.slide.side*st.slide.to*(1-e)),newTable);
            oldTable=product(screenAttached(current,currentTan,from,std::tan(st.fromFov/2),st.slide.side*st.slide.from*e),product(translate({0,st.tableLift,0}),st.fromTable));
        }
    }
    std::map<int,Mat> flights;
    for(auto&call:s->calls){
        const int group=call.flightGroup;
        if(group==-1){
            if(slide)call.model=product(newTable,call.model);
            else if(departing&&st.tableChanges)call.model=product(translate({0,st.tableLift,0}),call.model);
            else if(arriving)call.model=blendedTransform(st.fromTable,currentTable,q);
            continue;
        }
        const bool tv=group==-3,console=group==-2;
        // The anchor console: lifted a little while the others leave, then it glides on an arc.
        if(departing&&group==st.departAnchor&&st.anchorReleased<0){call.model=product(translate({0,12*flightEase(st.elapsed/.2f),0}),call.model);continue;}
        if(arriving&&group==st.arrivalAnchor){
            const Mat to=group==-2?s->consolePose:s->homeItems[group].pose;const float a=flightEase(st.arrival/systemAnchorSeconds);
            Mat moved=blendedTransform(st.anchorFrom,to,a);moved.v[13]+=systemAnchorArc*std::sin(3.14159265f*a);
            call.model=product(product(moved,affineInverse(to)),call.model);continue;
        }
        if(tv&&!st.televisionChanges){if(arriving)call.model=blendedTransform(call.mesh==&s->status?st.fromStatus:st.fromTV,call.model,q);continue;}
        auto found=flights.find(group);
        if(found==flights.end()){
            Mat home;Vec low,high;
            if(tv){home=s->tvPose;low=s->television.low;high=s->television.high;}
            else if(console){home=s->consolePose;const auto&model=s->consoles[activeConsole(s)].model;low=model.low;high=model.high;}
            else if(s->home){const auto&h=s->homeItems[group];home=h.pose;low=h.console.model.low;high=h.console.model.high;}
            else{const auto&item=s->items[group];const auto&m=s->media.at(item.model);home=item.pose;low=m.shell.low;high=m.shell.high;}
            // After a table slide the hardware follows the new table in from its side.
            const Vec centre=transform(home,mul(add(low,high),.5f));const bool right=slide?st.slide.side<0:transform(s->view,centre).x>0;
            // Home consoles use their wave index for timing; a released anchor leaves from then.
            const int wave=s->home&&group>=0&&group<(int)st.rank.size()?st.rank[group]:group;
            const float start=tv?st.tvExitStart:group==st.departAnchor&&st.anchorReleased>=0?st.anchorReleased:0;
            const float clock=departing?departureClock(st.elapsed-start,st.release-start,wave):st.arrival-(slide?tableArrivalDelay:0);
            Mat motion=waveFlight(s->cameraEye,s->cameraTarget,s->cameraFov,aspect,tv?450:console||s->home?300:110,clock,arriving,wave,centre,right);
            found=flights.emplace(group,supportFlight(motion,home,low,high)).first;
        }
        call.model=product(found->second,call.model);
    }
    if(slide&&st.arrival<tableSlideSeconds)
        for(auto&m:st.oldTable.parts)if(m.vertices&&!m.hidden)s->calls.push_back({&m,oldTable,0,false,false,false,{{0,0,1,1}},{{0,0,1,1}},0,1.f,false,-4});
}
void roomDraws(SlotTabletop*s){
    auto&room=*s->world;room.root=roomRoot(s);const auto root=room.root;
    const Mat localView=s->eyeView;
    s->cameraEye=transform(root,s->cameraEye);s->cameraTarget=transform(root,s->cameraTarget);
    s->eyeView=product(localView,inverseRigid(root));
    const Mat table=product(root,product(s->layout.nodes[0].matrix(),scale(s->layout.tableScale.x,s->layout.tableScale.y,s->layout.tableScale.z)));
    room.tablePoses[s->layout.tableAsset]=table;
    SceneStream*st=s->stream.get();
    const bool departing=st&&st->phase==2;
    const bool arriving=st&&(st->phase==3||st->phase==4)&&st->arrival<st->arrivalEnd;
    const float travel=arriving?st->travelSeconds:0;
    const float progress=travel>0?flightEase(st->arrival/travel):1;
    if(departing&&!s->bootstrapHome){
        // A navigation action leaves an authored detail view by showing the
        // current arrangement before hardware travels. Browsing cameras stay exact.
        const auto overview=viewCamera(s,0,-1);const float q=flightEase(st->elapsed/.35f);
        s->cameraEye=mix(s->cameraEye,transform(root,overview.eye),q);
        s->cameraTarget=mix(s->cameraTarget,transform(root,overview.target),q);
        const float fov=2*std::atan(std::tan(radians(overview.fov)/2)*float(s->layout.width)/s->layout.height*s->height/s->width);
        s->cameraFov+=(fov-s->cameraFov)*q;s->eyeView=lookAt(s->cameraEye,s->cameraTarget);
    }
    Mat anchorTo=identity(),anchorMoved=identity();bool anchor=false;
    if(arriving&&st->arrivalAnchor!=-100){
        anchorTo=product(root,st->arrivalAnchor==-2?s->consolePose:s->homeItems[st->arrivalAnchor].pose);
        anchorMoved=blendedTransform(st->anchorFrom,anchorTo,progress);
        const Vec from={st->anchorFrom.v[12],st->anchorFrom.v[13],st->anchorFrom.v[14]},to={anchorTo.v[12],anchorTo.v[13],anchorTo.v[14]};
        const Vec position=worldFlight(from,to,st->worldPath,progress);
        anchorMoved.v[12]=position.x;anchorMoved.v[13]=position.y;anchorMoved.v[14]=position.z;anchor=true;
    }
    if(arriving&&travel>0&&st->arrival<travel){
        Vec from=st->fromConsole,to=transform(root,transform(s->consolePose,{0,0,0}));
        if(anchor){from={st->anchorFrom.v[12],st->anchorFrom.v[13],st->anchorFrom.v[14]};to={anchorTo.v[12],anchorTo.v[13],anchorTo.v[14]};}
        else if(s->home)to=transform(table,{0,0,0});
        const auto moving=worldFlight(from,to,st->worldPath,progress);
        s->cameraEye=add(moving,mix(sub(st->fromEye,from),sub(s->cameraEye,to),progress));
        s->cameraTarget=add(moving,mix(sub(st->fromTarget,from),sub(s->cameraTarget,to),progress));
        s->cameraFov=st->fromFov+(s->cameraFov-st->fromFov)*progress;
        if(st->tableChanges){
            // Leave exact authored close-ups smoothly, then follow from above
            // the furniture. A mere box/frustum intersection accepts an edge
            // sliver or a camera inside the table; fit a complete tabletop
            // during the middle of the trip. Endpoints remain authored poses.
            const float hump=std::sin(3.14159265f*progress);
            s->cameraEye.y+=900*hump;
            s->cameraTarget=mix(s->cameraTarget,moving,hump);
            s->cameraFov+=(std::max(s->cameraFov,radians(38))-s->cameraFov)*hump;
            const Vec eye=s->cameraEye,back=unit(sub(eye,s->cameraTarget));
            const float tanY=std::tan(s->cameraFov/2)*.88f,tanX=tanY*s->width/s->height;
            auto tableInView=[&](float retreat){
                const Mat view=lookAt(add(eye,mul(back,retreat)),s->cameraTarget);
                auto fits=[&](const Mat&at,const Model&model){
                    for(int k=0;k<4;k++){
                        const Vec point=transform(view,transform(at,{k&1?model.high.x:model.low.x,model.high.y,k&2?model.high.z:model.low.z}));
                        if(point.z>-200||std::abs(point.x)>-point.z*tanX||std::abs(point.y)>-point.z*tanY)return false;
                    }return true;
                };
                return fits(table,s->table)||fits(st->fromTable,st->oldTable);
            };
            if(!tableInView(0)){
                float low=0,high=100;
                while(high<12800&&!tableInView(high)){low=high;high*=2;}
                for(int i=0;i<12;i++){const float middle=(low+high)/2;if(tableInView(middle))high=middle;else low=middle;}
                const float blend=flightEase(std::min(progress,1-progress)/.15f);
                s->cameraEye=add(eye,mul(back,high*blend));
            }
        }
        s->eyeView=lookAt(s->cameraEye,s->cameraTarget);
    }
    s->projectionFov=s->cameraFov;s->view=product(perspective(s->cameraFov,float(s->width)/s->height,150,10000),s->eyeView);
    std::map<int,Mat> flights;
    for(auto&call:s->calls){
        call.model=product(root,call.model);const int group=call.flightGroup;
        if(group==-1||(!departing&&!arriving))continue; // furniture never slides or lifts
        if(departing&&group==st->departAnchor&&st->anchorReleased<0){call.model=product(translate({0,(s->reducedMotion?3:12)*flightEase(st->elapsed/.2f),0}),call.model);continue;}
        if(arriving&&anchor&&group==st->arrivalAnchor){call.model=product(product(anchorMoved,affineInverse(anchorTo)),call.model);continue;}
        const bool tv=group==-3,console=group==-2;
        if(tv&&!st->televisionChanges){if(arriving)call.model=blendedTransform(call.mesh==&s->status?st->fromStatus:st->fromTV,call.model,progress);continue;}
        auto found=flights.find(group);
        if(found==flights.end()){
            Mat at;Vec low,high;
            if(tv){at=product(root,s->tvPose);low=s->television.low;high=s->television.high;}
            else if(console){at=product(root,s->consolePose);const auto&m=s->consoles[activeConsole(s)].model;low=m.low;high=m.high;}
            else if(s->home){const auto&h=s->homeItems[group];at=product(root,h.pose);low=h.console.model.low;high=h.console.model.high;}
            else{const auto&i=s->items[group];const auto&m=s->media.at(i.model);at=product(root,i.pose);low=m.shell.low;high=m.shell.high;}
            const auto centre=transform(at,mul(add(low,high),.5f));const bool right=transform(s->view,centre).x>0;
            const int wave=s->home&&group>=0&&group<int(st->rank.size())?st->rank[group]:group;
            const float start=tv?st->tvExitStart:group==st->departAnchor&&st->anchorReleased>=0?st->anchorReleased:0;
            const float clock=departing?departureClock(st->elapsed-start,st->release-start,wave):st->arrival-travel;
            const Mat motion=waveFlight(s->cameraEye,s->cameraTarget,s->cameraFov,float(s->width)/s->height,tv?450:console||s->home?300:110,clock,arriving,wave,centre,right,s->reducedMotion);
            found=flights.emplace(group,supportFlight(motion,at,low,high)).first;
        }
        call.model=product(found->second,call.model);
    }
    room.tableCount=1;room.visibleTables=0;
    auto visible=[&](const Mat&pose,const Model&model){DepthRange range;return boxDepth(range,s->eyeView,pose,model.low,model.high,std::tan(s->cameraFov/2)*s->width/s->height,std::tan(s->cameraFov/2));};
    room.visibleTables+=visible(table,s->table);
    if(arriving&&st->tableChanges&&st->arrival<travel){
        for(auto&m:st->oldTable.parts)if(m.vertices&&!m.hidden)s->calls.push_back({&m,st->fromTable,0,false,false,false,{{0,0,1,1}},{{0,0,1,1}},0,1.f,false,-4});
        room.tablePoses[st->fromTableModel]=st->fromTable;room.tableCount++;
        room.visibleTables+=visible(st->fromTable,st->oldTable);
    }
    if(room.surfaces.empty())s->calls.push_back({&room.surroundings,identity(),0,false,false,false,{{0,0,1,1}},{{0,0,1,1}},0,1.f,false,-6});
    for(auto&m:room.surfaces)s->calls.push_back({&m,identity(),0,false,false,false,{{0,0,1,1}},{{0,0,1,1}},0,1.f,false,-6});
    if(s->selected==-2&&!departing&&!arriving){
        const auto low=s->television.low,high=s->television.high;
        const auto selector=product(product(root,s->tvPose),product(translate({(low.x+high.x)/2,(low.y+high.y)/2,high.z+4}),scale(high.x-low.x+18,high.y-low.y+18,1)));
        s->calls.push_back({&room.selector,selector,0,true,false,false,{{0,0,1,1}},{{0,0,1,1}},0,1.f,false,-7});
    }
    for(auto&corner:s->display)corner=transform(root,corner);
}
}
bool slot_tabletop_stream_start(SlotTabletop*s){
    if(!s)return false;if(s->stream)return true;
    auto st=std::make_shared<SceneStream>(s);SDL_GL_MakeCurrent(s->window,s->context);bool ok=st->upload.create();SDL_GL_MakeCurrent(s->window,s->owner);if(!ok)return false;
    if(const char*path=getenv("SLOT_SCENE_STREAMLOG"))st->log=std::fopen(path,"a");
    st->liftUploads=getenv("SLOT_SCENE_LIFT_UPLOADS")&&std::strcmp(getenv("SLOT_SCENE_LIFT_UPLOADS"),"1")==0;
    // The opened room flies in from the next frame (phase 3 below): its meshes are drawn first,
    // still within this synchronous load, so the fly-in never pays libmali's one-time cost.
    SDL_GL_MakeCurrent(s->window,s->context);warmRoom(s,*st,*s,0,coreKey(s->system,s->tv,s->gbaChoice));SDL_GL_MakeCurrent(s->window,s->owner);
    auto initial=std::make_shared<SlotTabletop>();copyCore(*initial,*s);for(auto&p:s->labelTextures)initial->imageLeases.erase(p.first);
    if(!s->bootstrapHome)st->cache(coreKey(s->system,s->tv,s->gbaChoice),initial);
    st->wanted.key=s->bootstrapHome?"bootstrap":coreKey(s->system,s->tv,s->gbaChoice);st->wanted.items=s->items;
    st->phase=s->bootstrapHome?0:3;st->televisionChanges=!s->bootstrapHome;
    st->fromEye=s->layout.eye;st->fromTarget=s->layout.target;st->fromFov=authoredFov(s);
    st->fromTable=product(s->layout.nodes[0].matrix(),scale(s->layout.tableScale.x,s->layout.tableScale.y,s->layout.tableScale.z));
    s->stream=st;st->worker=std::thread([st]{st->run();});return true;
}
bool slot_tabletop_request(SlotTabletop*s,const char*system,const char*tv,const char*gba,const SlotTabletopItem*items,int count){
    if(!s||!s->stream||!system||!tv||!gba||count<0||count>sceneMaxCartridges)return false;auto&st=*s->stream;StreamRequest r;r.system=system;r.tv=tv;r.gba=gba;r.key=coreKey(r.system,r.tv,r.gba);
    for(int i=0;i<count;i++){Item n;n.id=items[i].id?items[i].id:"";n.model=items[i].model?items[i].model:system;n.face=items[i].face?items[i].face:"";r.items.push_back(std::move(n));}
    bool same=r.key==st.wanted.key&&r.items.size()==st.wanted.items.size();for(size_t i=0;same&&i<r.items.size();i++)same=r.items[i].id==st.wanted.items[i].id&&r.items[i].model==st.wanted.items[i].model&&r.items[i].face==st.wanted.items[i].face;
    {std::lock_guard<std::mutex> lock(st.mutex);if(same&&!st.failed)return true;}
    {std::lock_guard<std::mutex> lock(st.mutex);r.generation=++st.desired;st.wanted=r;st.failed=false;st.failure.clear();st.candidate.reset();st.jobs.clear();st.jobs.push_front(r);st.ticket=true;}s->error.clear();
    st.event("request",r.generation,r.key);
    if(st.phase==2){
        if(!st.televisionChanges&&s->tv!=r.tv)st.tvExitStart=st.elapsed;st.televisionChanges=st.televisionChanges||s->tv!=r.tv;
        // A new destination releases the anchor; it then leaves like the others.
        if(st.departAnchor!=-100&&st.anchorReleased<0&&r.system!=(st.departAnchor==-2?std::string("home"):st.anchorSystem)&&r.key!=coreKey(s->system,s->tv,s->gbaChoice))st.anchorReleased=st.elapsed;
    }
    else if(st.phase==3||(st.phase==4&&st.arrival<st.arrivalEnd)){} // departs once the landing settles
    else{
        // Visible at once: a different room lifts on this frame. The same room
        // only swaps its prepared items.
        st.previous=st.last;st.previous.screen=st.previous.handheldScreen=0;st.elapsed=0;
        if(r.key==coreKey(s->system,s->tv,s->gbaChoice)&&!s->bootstrapHome)st.phase=1;else depart(s,st,s->tv!=r.tv);
    }
    st.wake.notify_all();return true;
}
void slot_tabletop_prefetch(SlotTabletop*s,const char*system,const char*tv,const char*gba){
    if(!s||!s->stream||!system||!tv||!gba)return;auto&st=*s->stream;StreamRequest r;r.system=system;r.tv=tv;r.gba=gba;r.key=coreKey(r.system,r.tv,r.gba);
    std::lock_guard<std::mutex> lock(st.mutex);if(st.stop||r.key==st.wanted.key)return;for(auto&j:st.jobs)if(j.key==r.key)return;
    if(st.jobs.size()<3)st.jobs.push_back(std::move(r));st.wake.notify_all();
}
bool slot_tabletop_ready(SlotTabletop*s){if(!s)return false;if(!s->stream)return true;auto&st=*s->stream;std::lock_guard<std::mutex> lock(st.mutex);return !st.failed&&st.active==st.desired&&st.phase==0;}
bool slot_tabletop_stream_failed(SlotTabletop*s){if(!s||!s->stream)return false;std::lock_guard<std::mutex> lock(s->stream->mutex);return s->stream->failed;}
bool slot_tabletop_stream_stats(SlotTabletop*s,unsigned long long v[6]){if(!s||!s->stream)return false;auto&st=*s->stream;std::lock_guard<std::mutex> lock(st.mutex);v[0]=st.desired;v[1]=st.active;v[2]=st.loads.load();v[3]=s->pool->retired->bytes;v[4]=st.phase;v[5]=st.uploads;return true;}
