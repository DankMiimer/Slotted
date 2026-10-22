// Four-direction selection from stable, projected layout anchors (MIT).
// No frontend, SDL, cursor, launcher or rendering side effects.
#pragma once
#include "SlotSceneMath.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

namespace slot_navigation {
enum class Direction { Left, Right, Up, Down };
struct Point { int id; float x,y; bool enabled=true; };
constexpr int noTarget=std::numeric_limits<int>::min();
inline bool valid(const Point&p){return p.id!=noTarget&&std::isfinite(p.x)&&std::isfinite(p.y);}
inline bool horizontal(Direction d){return d==Direction::Left||d==Direction::Right;}
inline int sign(Direction d){return d==Direction::Left||d==Direction::Up?-1:1;}

// Point identity is independent of vector order (a TV can have a negative id).
// Prefer nearby targets in the requested direction, penalizing sideways travel.
// A 90-degree cone permits staggered arrangements but prevents a tiny vertical
// offset from turning Down at a row edge into a long sideways jump.
inline int neighbor(const std::vector<Point>&points,int current,Direction direction){
    const Point*from=nullptr;
    for(const auto&p:points)if(p.id==current&&p.enabled&&valid(p)){from=&p;break;}
    if(!from)return noTarget;
    double best=std::numeric_limits<double>::infinity();int result=noTarget;
    for(const auto&p:points){
        if(p.id==current||!p.enabled||!valid(p))continue;
        const double dx=double(p.x)-from->x,dy=double(p.y)-from->y;
        const double forward=(horizontal(direction)?dx:dy)*sign(direction);
        if(forward<=.001)continue;
        const double side=horizontal(direction)?dy:dx;
        if(std::abs(side)>forward+.001)continue;
        const double score=forward+2*side*side/forward;
        if(score<best||(score==best&&p.id<result)){best=score;result=p.id;}
    }
    return result;
}

// Called only after no neighbor exists in the current cartridge window.
// An incoming window is entered from its opposite edge, near the same row or
// column. Slots contain physical home anchors, including currently empty slots;
// only ids [0,count) are occupied. Partial windows never produce a phantom game.
inline int incomingSlot(const std::vector<Point>&slots,int current,Direction direction,int count){
    if(current<0||count<=0)return noTarget;
    const Point*from=nullptr;
    float lo=std::numeric_limits<float>::infinity(),hi=-lo;
    std::vector<Point> occupied;
    for(const auto&p:slots){
        if(!p.enabled||!valid(p))continue;
        if(p.id==current)from=&p;
        if(p.id<0||p.id>=count)continue;
        occupied.push_back(p);const float axis=horizontal(direction)?p.x:p.y;
        lo=std::min(lo,axis);hi=std::max(hi,axis);
    }
    if(!from||occupied.empty())return noTarget;
    Point entry={noTarget+1,from->x,from->y};
    // Use a synthetic id that cannot shadow a cartridge slot.
    const float edge=sign(direction)>0?lo:hi;
    float offset=std::max(1.f,(hi-lo)*.1f);
    // A partial final window may have no game in the old row/column. Put its
    // virtual entry far enough outside that every occupied slot is reachable.
    for(const auto&p:occupied)
        offset=std::max(offset,1+std::abs(horizontal(direction)?p.y-from->y:p.x-from->x));
    if(horizontal(direction))entry.x=edge-sign(direction)*offset;
    else entry.y=edge-sign(direction)*offset;
    occupied.push_back(entry);
    return neighbor(occupied,entry.id,direction);
}

struct WindowMove { int first=0,slot=noTarget; bool changed=false; };
inline WindowMove nextWindow(const std::vector<Point>&slots,int current,Direction direction,
                             int first,int total,int capacity,bool wrap=false){
    WindowMove result;result.first=first;
    if(total<=0||capacity<=0||first<0||first>=total||first%capacity)return result;
    // Wider arithmetic prevents an invalid caller's counts overflowing.
    long long next=static_cast<long long>(first)+sign(direction)*static_cast<long long>(capacity);
    if(next<0||next>=total){
        if(!wrap)return result;
        next=next<0?((static_cast<long long>(total)-1)/capacity)*capacity:0;
    }
    if(next==first)return result;
    const int count=std::min(capacity,total-int(next));
    const int slot=incomingSlot(slots,current,direction,count);
    if(slot==noTarget)return result;
    result.first=int(next);result.slot=slot;result.changed=true;return result;
}

// Project an unanimated authored anchor, not an item's hovering/inserted pose.
// This rejects anchors behind the camera; viewport/frustum policy is the caller's.
inline bool projectAnchor(const slot_scene::Mat&vp,slot_scene::Vec at,int width,int height,int id,Point&out){
    if(width<=0||height<=0||id==noTarget)return false;
    const auto&m=vp.v;
    const double w=double(m[3])*at.x+double(m[7])*at.y+double(m[11])*at.z+m[15];
    if(!std::isfinite(w)||w<=1e-6)return false;
    const double x=(double(m[0])*at.x+double(m[4])*at.y+double(m[8])*at.z+m[12])/w;
    const double y=(double(m[1])*at.x+double(m[5])*at.y+double(m[9])*at.z+m[13])/w;
    Point p={id,float((x+1)*width/2),float((1-y)*height/2)};
    if(!valid(p))return false;
    out=p;return true;
}
}
