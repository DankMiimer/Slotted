// Transient, camera-relative system motion. Never edits an authored profile (MIT).
#pragma once
#include "SlotTabletopMotion.h"
#include <algorithm>
#include <cmath>

namespace slot_scene {
// Each wave lifts for systemLiftSeconds, then flies. The last wave touches down
// at systemTouchdownSeconds and its landing wiggle ends at systemArrivalSeconds.
constexpr float systemDepartureSeconds=.52f,systemLiftSeconds=.11f,systemTouchdownSeconds=.43f,systemArrivalSeconds=.63f;
// Camera, table and unchanged TV glide together over the same arrival time. A
// changed table slides sideways instead; hardware then follows it in.
constexpr float systemRoomSeconds=.31f,tableSlideSeconds=.42f,tableArrivalDelay=tableSlideSeconds-.31f+.02f;
// After a switch the saved browse view is reached from the everything view in at
// most this long (the profile's own transition still governs ordinary pans); it
// starts as the last wave touches down, while the landing wiggle settles.
constexpr float systemPanSeconds=.5f;
// Home table <-> console room: the chosen console glides between its two poses on an arc.
constexpr float systemAnchorSeconds=.5f,systemAnchorArc=60.f;
// Quintic has zero velocity and acceleration at each end. A complete flight is
// short; a slow loader must extend the table-only wait, never the motion itself.
inline float flightEase(float t) {
    t=std::max(0.f,std::min(1.f,t));return t*t*t*(t*(t*6-15)+10);
}
// Amount off the resting pose, 0 at home, 1 completely outside the camera frustum.
// Objects leave left/up, and arrive from right/up. The camera's right vector
// makes this work with the user's rotated cameras as well as the default view.
inline Mat systemFlight(Vec eye,Vec target,float verticalFov,float aspect,float radius,
                        float amount,bool entering,int index=-1) {
    if(amount<=0)return identity();
    const Vec forward=unit(sub(target,eye)),right=unit(cross(forward,{0,1,0}));
    const Vec up=unit(cross(right,forward));
    const float distance=std::sqrt(dot(sub(eye,target),sub(eye,target)));
    const float extent=distance*std::tan(verticalFov/2)*aspect;
    // Include a conservative object radius so the trailing housing/cart clears
    // the viewport too. No raster fade and no geometry/texture substitution.
    const float travel=2*extent+2*std::max(0.f,radius)+100;
    const float side=entering?1.f:-1.f;
    Vec movement=add(mul(right,side*travel*amount),mul(up,(100+(index<0?0:index%3*12))*amount));
    return product(translate(movement),axisRotation(up,side*radians(index<0?5.f:8.f)*amount));
}
// Three cartridges lift together, followed by the next row. Console parts and
// the complete TV/status assembly each share one clock and one world pivot.
inline float flightDelay(int group){return group>=0?.04f*std::min(3,group/3):group==-2?.04f:.08f;}
// The lift starts on the input frame while the destination is still being
// prepared. Each group then holds its lift; once the destination is ready at
// `release` (departure seconds, infinite while waiting) it flies with the same
// stagger. A destination ready within the lift keeps the original timeline.
constexpr float systemWaiting=1e9f;
inline float departureClock(float elapsed,float release,int group){
    const float lifted=flightDelay(group)+systemLiftSeconds;
    if(elapsed<=lifted)return elapsed;
    if(release>=systemWaiting)return lifted;
    const float start=std::max(lifted,release+flightDelay(group));
    return elapsed<start?lifted:elapsed-(start-lifted);
}
// How much later than the original departure the last wave leaves.
inline float departureHold(float release){return std::max(0.f,release-systemLiftSeconds);}
// Every wave (the last cart row, or a TV that started leaving at `tvStart`) is lifted.
inline float departureLifted(float tvStart){return std::max(flightDelay(9),tvStart+flightDelay(-3))+systemLiftSeconds;}
inline float landingSpring(float seconds){
    if(seconds<=0||seconds>=.20f)return 0;
    return std::sin(seconds*38)*std::exp(-seconds*17)*ease(seconds/.025f)*(1-ease(seconds/.20f));
}
inline Mat waveFlight(Vec eye,Vec target,float fov,float aspect,float radius,
                      float elapsed,bool arriving,int group,Vec pivot,bool rightSide,bool reduced=false){
    const float time=elapsed-flightDelay(group);
    if(!arriving&&time<=0)return identity();
    if(arriving&&time>=.51f)return identity(); // exact saved pose, no residual drift
    const Vec forward=unit(sub(target,eye)),right=unit(cross(forward,{0,1,0})),up=unit(cross(right,forward));
    const float distance=std::sqrt(dot(sub(eye,target),sub(eye,target)));
    const float travel=2*distance*std::tan(fov/2)*aspect+2*radius+100,side=rightSide?1.f:-1.f;
    const float off=arriving?1-flightEase(time/.31f):flightEase((time-.11f)/.27f);
    const float lift=(reduced?.2f:1.f)*(group>=0?28.f:group==-2?38.f:30.f)*(arriving?1-flightEase((time-.19f)/.12f):flightEase(time/.11f));
    const float spring=arriving&&!reduced?landingSpring(time-.31f):0,weight=group>=0?1.f:group==-2?.45f:.28f;
    Vec movement=add(mul(right,side*(travel*off+spring*1.5f*weight)),{0,lift+std::abs(spring)*2*weight,0});
    movement=add(movement,mul(up,std::sin(off*3.14159265f)*(reduced?0:24)));
    const Mat turn=reduced?identity():product(axisRotation(forward,radians(side*(8*off+spring*3.5f*weight))),axisRotation(up,radians(side*5*off)));
    return product(translate(add(pivot,movement)),product(turn,translate(mul(pivot,-1))));
}
// Rock about the assembly's centre, then keep its authored support height. This
// prevents a tall standing card's lower corner from dipping through the table.
inline Mat supportFlight(Mat motion,const Mat&home,Vec low,Vec high){
    float rest=1e9f,moving=1e9f;
    for(int k=0;k<8;k++){
        const Vec p=transform(home,{k&1?high.x:low.x,k&2?high.y:low.y,k&4?high.z:low.z});
        rest=std::min(rest,p.y);moving=std::min(moving,transform(motion,p).y);
    }
    motion.v[13]+=std::max(0.f,rest-moving);return motion;
}
// Inverse of an affine model matrix (rotation, uniform or non-uniform scale, translation).
inline Mat affineInverse(const Mat&m){
    const float a=m.v[0],b=m.v[4],c=m.v[8],d=m.v[1],e=m.v[5],f=m.v[9],g=m.v[2],h=m.v[6],k=m.v[10];
    const float A=e*k-f*h,B=f*g-d*k,C=d*h-e*g,det=a*A+b*B+c*C;if(std::abs(det)<1e-12f)return identity();
    Mat r=identity();const float s=1/det;
    r.v[0]=A*s;r.v[4]=(c*h-b*k)*s;r.v[8]=(b*f-c*e)*s;r.v[1]=B*s;r.v[5]=(a*k-c*g)*s;r.v[9]=(c*d-a*f)*s;r.v[2]=C*s;r.v[6]=(b*g-a*h)*s;r.v[10]=(a*e-b*d)*s;
    for(int i=0;i<3;i++)r.v[12+i]=-(r.v[i]*m.v[12]+r.v[4+i]*m.v[13]+r.v[8+i]*m.v[14]);return r;
}
// Inverse of a rotation + translation (a lookAt view).
inline Mat rigidInverse(const Mat&m){
    Mat r=identity();for(int c=0;c<3;c++)for(int k=0;k<3;k++)r.v[c*4+k]=m.v[k*4+c];
    for(int k=0;k<3;k++)r.v[12+k]=-(r.v[k]*m.v[12]+r.v[4+k]*m.v[13]+r.v[8+k]*m.v[14]);return r;
}
// A table drawn under the current camera exactly as `own` frames it, shifted
// `shift` mm along own's x. Attached to the screen, it ignores the camera blend,
// while its lighting turns smoothly with that blend (no pop at either end).
inline Mat screenAttached(const Mat&current,float currentTanY,const Mat&own,float ownTanY,float shift){
    const float k=currentTanY/ownTanY;
    return product(rigidInverse(current),product(scale(k,k,1),product(translate({shift,0,0}),own)));
}
// Room change with a different table: the old one leaves past one screen edge
// while the new one follows it in from the other, both moving the same way.
// Distances are camera-space mm (old/new camera); side +1 = old leaves right.
struct TableSlide {float side=1,from=0,to=0;};
// The tabletop (high.y face) as NDC points, clipped to the screen's rows and to
// depths ahead of the eye. A slide moves camera x only, so the clip never changes
// and each point moves `per` NDC columns per mm.
struct SlidePoint {float x,y,per;};
inline int slideFace(const Mat&view,float tanY,float aspect,const Mat&model,Vec low,Vec high,SlidePoint out[12]){
    Vec poly[12],next[12];int n=0;const Mat m=product(view,model);
    for(Vec p:{Vec{low.x,high.y,low.z},Vec{high.x,high.y,low.z},Vec{high.x,high.y,high.z},Vec{low.x,high.y,high.z}}){const Vec c=transform(m,p);poly[n++]={c.x,c.y,-c.z};}
    for(int plane=0;plane<3;plane++){
        auto inside=[&](Vec v){return plane==0?tanY*v.z-v.y:plane==1?tanY*v.z+v.y:v.z-50;};int k=0;
        for(int i=0;i<n;i++){
            const Vec a=poly[i],b=poly[(i+1)%n];const float fa=inside(a),fb=inside(b);
            if(fa>=0)next[k++]=a;if((fa>=0)!=(fb>=0))next[k++]=add(a,mul(sub(b,a),fa/(fa-fb)));
        }
        n=k;for(int i=0;i<n;i++)poly[i]=next[i];
    }
    for(int i=0;i<n;i++)out[i]={poly[i].x/(poly[i].z*tanY*aspect),poly[i].y/(poly[i].z*tanY),1/(poly[i].z*tanY*aspect)};
    return n;
}
// Columns the face covers on screen row y after sliding `shift` mm.
inline bool slideRow(const SlidePoint*p,int n,float shift,float y,float&low,float&high){
    low=1e9f;high=-1e9f;
    for(int i=0;i<n;i++){
        const SlidePoint&a=p[i],&b=p[(i+1)%n];const float ax=a.x+shift*a.per,bx=b.x+shift*b.per;
        if(a.y==b.y){if(a.y==y){low=std::min({low,ax,bx});high=std::max({high,ax,bx});}continue;}
        if((a.y-y)*(b.y-y)>0)continue;
        const float x=ax+(bx-ax)*(y-a.y)/(b.y-a.y);low=std::min(low,x);high=std::max(high,x);
    }
    return low<=high;
}
// Picks the side leaving the least empty screen between the tables mid-slide
// (then the shorter travel); distances grow until no screen row shows them overlap.
inline TableSlide planTableSlide(const Mat&oldView,float oldTanY,const Mat&oldModel,Vec oldLow,Vec oldHigh,
                                 const Mat&newView,float newTanY,const Mat&newModel,Vec newLow,Vec newHigh,float aspect){
    SlidePoint o[12],n[12];
    const int on=slideFace(oldView,oldTanY,aspect,oldModel,oldLow,oldHigh,o),nn=slideFace(newView,newTanY,aspect,newModel,newLow,newHigh,n);
    TableSlide best;float bestGap=1e9f,bestTravel=1e9f;
    for(float side:{1.f,-1.f}){
        // Mirrored so the old table always leaves toward +x.
        SlidePoint a[12],b[12];float from=1,to=1,gap=0,oldPer=0,newPer=0;
        for(int i=0;i<on;i++){a[i]={side*o[i].x,o[i].y,o[i].per};from=std::max(from,(1.02f-a[i].x)/a[i].per);oldPer+=a[i].per/on;}
        for(int i=0;i<nn;i++){b[i]={side*n[i].x,n[i].y,n[i].per};to=std::max(to,(1.02f+b[i].x)/b[i].per);newPer+=b[i].per/nn;}
        for(int pass=0;pass<40;pass++){
            bool early=false,late=false;gap=0;
            for(int i=0;i<=30;i++)for(int r=0;r<=24;r++){
                const float e=i/30.f,y=-1+r/12.f;float oldLeft,oldRight,newLeft,newRight;
                if(!slideRow(a,on,from*e,y,oldLeft,oldRight)||!slideRow(b,nn,-to*(1-e),y,newLeft,newRight))continue;
                if(newRight>oldLeft-.02f&&newRight>-1&&oldLeft<1)(e<.5f?early:late)=true; // keeps a hairline apart between samples
                if(e>=.2f&&e<=.8f)gap=std::max(gap,std::min(oldLeft,1.f)-std::max(newRight,-1.f));
            }
            if(!early&&!late)break;if(early)to*=1.05f;if(late)from*=1.05f;
        }
        const float travel=from*oldPer+to*newPer;
        if(gap<bestGap-.02f||(gap<=bestGap+.02f&&travel<bestTravel)){bestGap=std::min(gap,bestGap);bestTravel=travel;best={side,from,to};}
    }
    return best;
}
}
