/* Slotters model finish and enclosure colours, copyright 2026, MIT. */
typedef struct { const char *name;float rgb[3]; } ConsolePaint;
#include "appearance-data.h"
static const ConsolePaint *console_paint(void)
{
    const char *name=getenv("SLOT_CONSOLE_COLOR");
    if(name)for(size_t i=0;i<sizeof(console_paints)/sizeof(console_paints[0]);i++)
        if(!strcmp(name,console_paints[i].name))return &console_paints[i];
    return NULL;
}
static bool console_realistic(void)
{
    const char *style=getenv("SLOT_MODEL_STYLE");return style&&!strcmp(style,"realistic");
}
static bool console_appearance_path(char *path,size_t size,const char *relative)
{
    const ConsolePaint *paint=console_paint();
    if(!paint&&!getenv("SLOT_MODEL_STYLE"))return false;
    int n=snprintf(path,size,"appearance/%s/%s/%s",console_realistic()?"realistic":"cel",paint?paint->name:"original",relative);
    return n>0&&n<(int)size;
}
static uint64_t console_vertex_hash(const void *data,size_t size)
{
    const unsigned char *bytes=data;uint64_t hash=UINT64_C(14695981039346656037);
    for(size_t i=0;i<size;i++){hash^=bytes[i];hash*=UINT64_C(1099511628211);}return hash;
}
static bool console_appearance_ready(const char *name)
{
    for(size_t i=0;i<sizeof(console_appearance_models)/sizeof(console_appearance_models[0]);i++)
        if(!strcmp(name,console_appearance_models[i]))return true;
    return false;
}
static bool console_style_ready(const char *name)
{
    for(size_t i=0;i<sizeof(console_style_models)/sizeof(console_style_models[0]);i++)
        if(!strcmp(name,console_style_models[i]))return true;
    return false;
}
