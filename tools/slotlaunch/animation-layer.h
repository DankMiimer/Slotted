/* Private, double-buffered Sunxi output for the disc/UMD animations (MIT).
 * ES can clear the primary framebuffer while the early launch helper renders.
 * Keep the complete scene in our own buffers; channel 3 remains for handover. */
typedef struct {
    int display,ion,shared[2],next;
    void *pixels[2];
    size_t length;
    SlotLayer original,overlay;
    bool enabled;
} AnimationLayer;

static void animation_layer_close(AnimationLayer *layer)
{
    if(layer->enabled){
        layer_command(layer->display,SLOT_LAYER_SET,&layer->original);
        struct timespec latch={0,20000000};nanosleep(&latch,NULL);
    }
    for(int i=0;i<2;i++){
        if(layer->pixels[i]!=MAP_FAILED)munmap(layer->pixels[i],layer->length);
        if(layer->shared[i]>=0)close(layer->shared[i]);
    }
    if(layer->ion>=0)close(layer->ion);
    if(layer->display>=0)close(layer->display);
    *layer=(AnimationLayer){.display=-1,.ion=-1,.shared={-1,-1},.pixels={MAP_FAILED,MAP_FAILED}};
}

static bool animation_layer_open(AnimationLayer *layer)
{
    int fb=open("/dev/fb0",O_RDONLY);
    struct fb_var_screeninfo var;struct fb_fix_screeninfo fix;
    bool supported=fb>=0&&!ioctl(fb,FBIOGET_VSCREENINFO,&var)&&!ioctl(fb,FBIOGET_FSCREENINFO,&fix)
        &&var.xres==WIDTH&&var.yres==HEIGHT&&var.bits_per_pixel==32
        &&var.red.offset==16&&var.green.offset==8&&var.blue.offset==0&&fix.line_length==WIDTH*4;
    if(fb>=0)close(fb);
    if(!supported)return false;
    const char *stage="display/layer availability";
    layer->display=open("/dev/disp",O_RDWR);
    SlotLayer primary={.channel=1};
    layer->original.channel=2;
    if(layer->display<0||layer_command(layer->display,SLOT_LAYER_GET,&primary)||!primary.enabled
        ||primary.plane.window.width!=WIDTH||primary.plane.window.height!=HEIGHT
        ||layer_command(layer->display,SLOT_LAYER_GET,&layer->original)||layer->original.enabled)goto failed;
    layer->original.channel=2;layer->original.layer=0;
    stage="open ION";
    layer->ion=open("/dev/ion",O_RDWR);
    layer->length=WIDTH*HEIGHT*4;
    if(layer->ion<0)goto failed;
    for(int i=0;i<2;i++){
        stage="allocate animation DMA";
        /* The BSP display IOMMU accepts the system heap. CMA can become
         * fragmented after renderer/emulator handoffs despite free RAM. */
        SlotAllocation allocation={layer->length,4096,1u<<0,0,0};
        if(ioctl(layer->ion,_IOWR('I',0,SlotAllocation),&allocation))goto failed;
        SlotSharedBuffer buffer={allocation.handle,-1};
        stage="share animation DMA";
        if(ioctl(layer->ion,_IOWR('I',4,SlotSharedBuffer),&buffer))goto failed;
        layer->shared[i]=buffer.fd;
        stage="map animation DMA";
        layer->pixels[i]=mmap(NULL,layer->length,PROT_READ|PROT_WRITE,MAP_SHARED,buffer.fd,0);
        if(layer->pixels[i]==MAP_FAILED)goto failed;
    }
    layer->overlay=layer->original;
    layer->overlay.enabled=1;
    layer->overlay.plane=primary.plane;
    layer->overlay.plane.order=14;
    layer->overlay.plane.alpha_mode=1;layer->overlay.plane.alpha=255;
    layer->overlay.plane.buffer.format=0; /* ARGB8888, globally opaque. */
    layer->overlay.plane.buffer.size[0]=(SlotSize){WIDTH,HEIGHT};
    layer->overlay.plane.buffer.crop=(SlotCrop){0,0,(int64_t)WIDTH<<32,(int64_t)HEIGHT<<32};
    return true;
failed:
    {
        char message[200];snprintf(message,sizeof(message),"animation layer unavailable: %s (%s)",stage,strerror(errno));
        log_event(message);
    }
    animation_layer_close(layer);
    return false;
}

static bool animation_layer_present(AnimationLayer *layer,SDL_Renderer *renderer,SDL_Surface *frame)
{
    if(SDL_RenderReadPixels(renderer,NULL,SDL_PIXELFORMAT_ARGB8888,frame->pixels,frame->pitch))return false;
    memcpy(layer->pixels[layer->next],frame->pixels,layer->length);
    layer->overlay.plane.buffer.fd=layer->shared[layer->next];
    layer->overlay.plane.frame_id++;
    if(layer_command(layer->display,SLOT_LAYER_SET,&layer->overlay))return false;
    layer->enabled=true;layer->next^=1;
    return true;
}
