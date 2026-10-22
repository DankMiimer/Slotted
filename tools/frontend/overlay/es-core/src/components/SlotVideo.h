// Conservative detection of stacked DS footage pillarboxed into a wide clip.
// Sample decoded CPU pixels while they are already locked; never read GPU data.
#pragma once
#include <algorithm>
namespace slot {
inline bool stackedVideoBounds(const unsigned char* rgba,int w,int h,float out[4]) {
    if(!rgba || w<=0 || h<=0 || float(w)/h<1.2f)return false;
    const int dx=std::max(1,w/160),dy=std::max(1,h/96);
    int left=w,top=h,right=0,bottom=0,count=0;
    for(int y=0;y<h;y+=dy)for(int x=0;x<w;x+=dx) {
        const auto* p=rgba+4*(y*w+x);
        if(std::max(p[0],std::max(p[1],p[2]))>24) {
            left=std::min(left,x);right=std::max(right,x+dx);
            top=std::min(top,y);bottom=std::max(bottom,y+dy);++count;
        }
    }
    if(!count || bottom-top<h*.85f || right-left>w*.65f)return false;
    const float ratio=float(right-left)/(bottom-top);
    if(ratio<.60f || ratio>.76f || left<w*.08f || right>w*.92f)return false;
    out[0]=float(std::max(0,left-dx))/w;out[1]=float(std::max(0,top-dy))/h;
    out[2]=float(std::min(w,right+dx))/w;out[3]=float(std::min(h,bottom+dy))/h;
    return true;
}
}
