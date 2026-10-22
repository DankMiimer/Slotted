/* Measure the production handheld scene without display capture (MIT).
 * Only wraps SDL_RenderPresent; geometry, motion, layers and pacing are the
 * actual helper implementation. Run with SLOT_PREVIEW=1 and isolated assets. */
#define _GNU_SOURCE
#include <SDL.h>
static void benchmark_present(SDL_Renderer *renderer);
#define SDL_RenderPresent benchmark_present
#define main slot_application_main
#include "../slotlaunch/slot-launch.c"
#undef main
#undef SDL_RenderPresent

static double presented[4096];
static unsigned present_count;
static void benchmark_present(SDL_Renderer *renderer)
{
    SDL_RenderPresent(renderer);
    if(present_count<sizeof(presented)/sizeof(presented[0]))presented[present_count++]=now();
}
static int compare_time(const void *a,const void *b)
{
    double x=*(const double *)a,y=*(const double *)b;
    return (x>y)-(x<y);
}
int main(int argc,char **argv)
{
    int status=slot_application_main(argc,argv);
    if(argc!=5||present_count<2)return status?status:1;
    unsigned count=present_count-1,over_20=0,over_25=0;
    double intervals[4096],sum=0;
    for(unsigned i=0;i<count;i++){
        intervals[i]=1000*(presented[i+1]-presented[i]);sum+=intervals[i];
        over_20+=intervals[i]>20;over_25+=intervals[i]>25;
    }
    qsort(intervals,count,sizeof(double),compare_time);
    char path[PATH_CAP];snprintf(path,sizeof(path),"%s.frames.json",argv[4]);
    FILE *f=fopen(path,"w");if(!f)return 1;
    fprintf(f,"{\"mode\":\"%s\",\"presents\":%u,\"fps\":%.6f,\"interval_ms_p50\":%.6f,\"interval_ms_p95\":%.6f,\"interval_ms_max\":%.6f,\"intervals_over_20ms\":%u,\"intervals_over_25ms\":%u,\"exit\":%d}\n",
        argv[1],present_count,1000*count/sum,intervals[count/2],intervals[(count-1)*95/100],intervals[count-1],over_20,over_25,status);
    fclose(f);return status;
}
