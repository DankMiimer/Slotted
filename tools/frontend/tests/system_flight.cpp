#include "SlotSystemFlight.h"
#include <cassert>
#include <cmath>
#include <cstdio>
using namespace slot_scene;
int main(){
    // Identity at rest means every saved transform, including scale, survives
    // both motion directions exactly, without an accumulate/invert round trip.
    const Mat home=product(translate({-270,17,44}),product(rotate(.4f,-1.3f,.2f),scale(1.2f,.8f,1.1f)));
    for(Vec eye: {Vec{900,700,1800},Vec{-1200,500,800},Vec{100,1800,-1100}})for(float aspect:{1.5f,4.f/3})for(bool entering:{false,true}){
        Vec target={40,0,30};
        Mat rest=product(systemFlight(eye,target,radians(40),aspect,300,0,entering),home);
        for(int k=0;k<16;k++)assert(rest.v[k]==home.v[k]);
        Mat far=systemFlight(eye,target,radians(40),aspect,300,1,entering);
        Vec right=unit(cross(unit(sub(target,eye)),{0,1,0}));
        assert(dot(transform(far,{0,0,0}),right)*(entering?1:-1)>500);
        for(float value:far.v)assert(std::isfinite(value));
        // Rigid motion preserves detail, proportions and the distance between
        // the console and its power/lid parts while they travel as one group.
        Vec a={-22,33,44},b={83,47,-19};
        float before=dot(sub(a,b),sub(a,b)),after=dot(sub(transform(far,a),transform(far,b)),sub(transform(far,a),transform(far,b)));
        assert(std::abs(before-after)<.1f);
    }
    assert(flightEase(-1)==0&&flightEase(0)==0&&flightEase(1)==1&&flightEase(2)==1);
    float last=0;for(int k=0;k<=100;k++){float q=flightEase(k/100.f);assert(q>=last-.000001f&&q>=0&&q<=1);last=q;}
    assert(std::abs(flightEase(.5f)-.5f)<.000001f);
    for(int group:{-3,-2,0,3,6,11}){
        const Vec eye={900,700,1800},target={40,0,30},pivot={-200,30,600};
        const Mat rest=waveFlight(eye,target,radians(40),1.5f,110,0,false,group,pivot,false);
        const Mat landed=waveFlight(eye,target,radians(40),1.5f,110,systemArrivalSeconds,true,group,pivot,false);
        for(int k=0;k<16;k++){assert(rest.v[k]==identity().v[k]);assert(landed.v[k]==identity().v[k]);}
        // A real lift precedes horizontal departure; later waves have not moved.
        const Mat lifted=waveFlight(eye,target,radians(40),1.5f,110,flightDelay(group)+.09f,false,group,pivot,false);
        Vec centre=transform(lifted,pivot);assert(centre.y>pivot.y+20);assert(std::abs(centre.x-pivot.x)<.001f);
        for(bool entering:{false,true})for(int frame=0;frame<=100;frame++){
            Mat m=waveFlight(eye,target,radians(40),1.5f,110,frame*.01f,entering,group,pivot,false);
            for(float value:m.v)assert(std::isfinite(value));
            Vec a={-22,33,44},b={83,47,-19};Vec d=sub(transform(m,a),transform(m,b));
            assert(std::abs(dot(d,d)-dot(sub(a,b),sub(a,b)))<1.f);
        }
    }
    for(float yaw:{0.f,90.f,-133.f})for(float t:{.31f,.35f,.39f,.43f,.47f}){
        const Mat home=product(translate({90,65,500}),rotate(0,radians(yaw),0));
        const Vec low={-60,-65,-5},high={60,65,5};
        Mat motion=waveFlight({900,700,1800},{40,0,30},radians(40),1.5f,110,t,true,0,{90,65,500},false);
        motion=supportFlight(motion,home,low,high);
        for(int k=0;k<8;k++)assert(transform(product(motion,home),{k&1?high.x:low.x,k&2?high.y:low.y,k&4?high.z:low.z}).y>=-.001f);
    }
    assert(flightDelay(0)<flightDelay(3)&&flightDelay(3)<flightDelay(6)&&flightDelay(6)<flightDelay(9));
    assert(landingSpring(0)==0&&landingSpring(.20f)==0&&landingSpring(.04f)>0&&landingSpring(.12f)<0);
    // Table slide: the authored Panasonic (table, 1x) and PVM (wooden-table, 0.7x, 90 degrees) rooms.
    const Mat panasonic=lookAt({-235.6f,749.5f,1527},{302.7f,-577.2f,332.5f}),pvm=lookAt({314.1f,257.1f,891.3f},{293.1f,127.2f,329.2f});
    for(const Mat&v:{panasonic,pvm}){Mat round=product(rigidInverse(v),v);for(int k=0;k<16;k++)assert(std::abs(round.v[k]-identity().v[k])<1e-4f);}
    {
        // Attached to its own view, a point keeps its exact screen position under another camera and lens.
        const Mat model=product(translate({40,10,-30}),rotate(0,.7f,0));const Vec p={120,60,-80};
        const float ownTan=std::tan(radians(20)),otherTan=std::tan(radians(23));
        const Vec own=transform(product(perspective(radians(40),1.5f,10,10000),pvm),transform(model,p));
        const Vec other=transform(product(perspective(radians(46),1.5f,10,10000),panasonic),transform(product(screenAttached(panasonic,otherTan,pvm,ownTan,0),model),p));
        assert(std::abs(own.x-other.x)<1e-3f&&std::abs(own.y-other.y)<1e-3f);
        const Mat same=product(screenAttached(pvm,ownTan,pvm,ownTan,0),model);for(int k=0;k<16;k++)assert(std::abs(same.v[k]-model.v[k])<1e-3f);
    }
    for(float aspect:{1.5f,4.f/3}){
        // Prepared bounds of `table` and `wooden-table`; the old one lifted 30 mm.
        const Mat oldModel=translate({0,30,0}),newModel=product(translate({0,0,66.3f}),product(rotate(0,radians(90),0),scale(.7f,.7f,.7f)));
        const Vec oldLow={-750,-805,-1301},oldHigh={750,0,1301},newLow={-750,-595,-350},newHigh={750,0,350};const float tanY=std::tan(radians(20));
        const TableSlide plan=planTableSlide(panasonic,tanY,oldModel,oldLow,oldHigh,pvm,tanY,newModel,newLow,newHigh,aspect);
        assert(plan.from>0&&plan.to>0&&std::isfinite(plan.from)&&std::isfinite(plan.to)&&(plan.side==1||plan.side==-1));
        SlidePoint o[12],n[12];const int on=slideFace(panasonic,tanY,aspect,oldModel,oldLow,oldHigh,o),nn=slideFace(pvm,tanY,aspect,newModel,newLow,newHigh,n);
        assert(on>=3&&nn>=3);
        for(int i=0;i<on;i++){o[i].x*=plan.side;assert(o[i].y>=-1.001f&&o[i].y<=1.001f);}for(int i=0;i<nn;i++)n[i].x*=plan.side;
        for(int i=0;i<on;i++)assert(o[i].x+plan.from*o[i].per>=1);   // the old table ends fully outside
        for(int i=0;i<nn;i++)assert(n[i].x-plan.to*n[i].per<=-1);    // the new table starts fully outside
        for(int i=0;i<=40;i++)for(int r=0;r<=32;r++){
            const float e=i/40.f,y=-1+r/16.f;float oldLeft,oldRight,newLeft,newRight;
            if(!slideRow(o,on,plan.from*e,y,oldLeft,oldRight)||!slideRow(n,nn,-plan.to*(1-e),y,newLeft,newRight))continue;
            assert(!(newRight>oldLeft+.03f&&newRight>-1&&oldLeft<1)); // never overlapping on screen
        }
    }
    assert(tableArrivalDelay+.31f>=tableSlideSeconds); // hardware lands after the new table
    // Departure starts on the input frame and holds the lift until the destination is ready.
    const int groups[]={-3,-2,0,3,6,9,11};
    for(int group:groups)for(int k=0;k<=200;k++){
        const float e=k*.005f;
        // Ready within the lift: exactly the original timeline.
        for(float release:{0.f,.03f,systemLiftSeconds})assert(departureClock(e,release,group)==e);
        // Waiting: the lift completes, then holds still (no flight).
        const float held=departureClock(e,systemWaiting,group);
        assert(held<=flightDelay(group)+systemLiftSeconds&&(e>flightDelay(group)+systemLiftSeconds||held==e));
    }
    const Vec eye={900,700,1800},target={40,0,30},pivot={-200,30,600};
    for(int group:groups){
        const Mat hold=waveFlight(eye,target,radians(40),1.5f,110,departureClock(5,systemWaiting,group),false,group,pivot,false);
        const Vec p=transform(hold,pivot),q=transform(hold,{-150,30,640});
        assert(std::abs(p.x-pivot.x)<1e-3f&&std::abs(p.z-pivot.z)<1e-3f&&p.y>pivot.y+20); // lifted straight up, not flying
        assert(std::abs(q.x+150)<1e-3f&&std::abs(q.y-p.y)<1e-3f&&std::abs(q.z-640)<1e-3f);  // and not turned
        assert(departureLifted(-1)>=flightDelay(group)+systemLiftSeconds-1e-6f&&departureLifted(.2f)>=.2f+flightDelay(-3)+systemLiftSeconds-1e-6f);
    }
    for(float release:{.05f,.2f,.5f,1.3f}){
        const float end=systemDepartureSeconds+departureHold(release);
        for(int group:groups){
            float last=0;
            for(int k=0;k<=1000;k++){
                // Continuous and never faster than real time: no pop when the flight is released.
                const float e=k*.002f,c=departureClock(e,release,group);
                assert(c>=last-1e-6f&&c-last<=.002f+1e-5f);last=c;
            }
            // The wave stagger survives the hold, and every wave is gone by the exit end.
            if(release>systemLiftSeconds)assert(std::abs(departureClock(release+flightDelay(group)+.1f,release,group)-flightDelay(group)-systemLiftSeconds-.1f)<1e-5f);
            assert(departureClock(end,release,group)-flightDelay(group)>=.38f-1e-5f);
        }
    }
    // Arrival: the last wave touches down (then only its wiggle remains), and the
    // wiggle ends with the exact authored pose for every group.
    assert(std::abs(systemTouchdownSeconds-flightDelay(9)-.31f)<1e-6f&&std::abs(systemArrivalSeconds-flightDelay(9)-.51f)<1e-6f);
    assert(systemArrivalSeconds>systemTouchdownSeconds&&systemTouchdownSeconds>=tableSlideSeconds&&systemTouchdownSeconds>=systemRoomSeconds);
    for(int group:groups){
        const Mat down=waveFlight(eye,target,radians(40),1.5f,110,systemTouchdownSeconds,true,group,pivot,false);
        const Vec p=transform(down,pivot);assert(std::abs(p.x-pivot.x)<4&&std::abs(p.y-pivot.y)<4&&std::abs(p.z-pivot.z)<4);
        const Mat home=waveFlight(eye,target,radians(40),1.5f,110,systemArrivalSeconds,true,group,pivot,false);
        for(int k=0;k<16;k++)assert(home.v[k]==identity().v[k]);
    }
    // Reduced motion still moves complete geometry out of view, with a steady
    // orientation and no residual bounce after touchdown.
    for(int group:groups)for(bool entering:{false,true})for(int k=0;k<=100;k++){
        const float t=k*.01f;
        const Mat motion=waveFlight(eye,target,radians(40),1.5f,110,t,entering,group,pivot,false,true);
        for(int col=0;col<3;col++)for(int row=0;row<3;row++)assert(motion.v[4*col+row]==identity().v[4*col+row]);
        for(float value:motion.v)assert(std::isfinite(value));
        if(entering&&t>=flightDelay(group)+.31f)for(int n=0;n<16;n++)assert(std::abs(motion.v[n]-identity().v[n])<.001f);
    }
    assert(systemPanSeconds>.3f&&systemPanSeconds<.8f);
    std::puts("system flight: exact authored landing, direction, rigid geometry, aspects, easing and table slide pass");
}
