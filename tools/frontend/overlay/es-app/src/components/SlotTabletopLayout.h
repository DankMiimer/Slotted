// Physical layout/framing helpers for the shared scene (MIT).
#pragma once
#include "SlotSceneMath.h"
#include <vector>
namespace slot_scene {
inline Vec tableCartridge(int index){int row=index/2;return {-285.f+row*20.f+(index%2)*137.f,0,270.f+row*105.f};}
inline void frameBox(std::vector<Vec>&points,Vec low,Vec high,const Mat&pose){
    for(int i=0;i<8;i++)points.push_back(transform(pose,{i&1?high.x:low.x,i&2?high.y:low.y,i&4?high.z:low.z}));
}
struct SceneCamera {Mat matrix;float distance;Vec target;};
// Solve perspective framing from the required front surfaces and media. The
// table and rear/top cabinet are deliberately not framing constraints. A pan
// along camera-right/up changes no depths, so each point gives an exact allowed
// pan interval. Binary search finds the closest distance with intersecting
// intervals; this avoids aspect-ratio crops and arbitrary per-model scaling.
// centred: aim at the middle of the allowed vertical range (an overview) instead of its bottom.
inline SceneCamera frameScene(const std::vector<Vec>&points,float yaw,float elevation,float width,float height,bool centred=false){
    Vec forward={std::sin(yaw)*std::cos(elevation),std::sin(elevation),std::cos(yaw)*std::cos(elevation)};
    Vec right={std::cos(yaw),0,-std::sin(yaw)},up=unit(cross(forward,right));
    const float aspect=width/height,focalX=1/(std::tan(radians(40)/2)*1.5f),focalY=focalX*aspect;
    const float edgeX=1-20/width,edgeY=1-20/height;Vec origin={0,130,0};
    float minX=0,maxX=0,minY=0,maxY=0;
    auto fits=[&](float distance){
        minX=minY=-1e9f;maxX=maxY=1e9f;
        for(Vec point:points){Vec p=sub(point,origin);float depth=distance-dot(p,forward);if(depth<160)return false;
            float x=dot(p,right),y=dot(p,up),halfX=edgeX*depth/focalX,halfY=edgeY*depth/focalY;
            minX=std::max(minX,x-halfX);maxX=std::min(maxX,x+halfX);minY=std::max(minY,y-halfY);maxY=std::min(maxY,y+halfY);
        }
        return minX<=maxX&&minY<=maxY;
    };
    float low=160,high=4000;for(int i=0;i<28;i++){float middle=(low+high)/2;if(fits(middle))high=middle;else low=middle;}
    fits(high+.5f);Vec target=add(origin,add(mul(right,(minX+maxX)/2),mul(up,centred?(minY+maxY)/2:minY)));
    float fov=2*std::atan(1/focalY);return {product(perspective(fov,aspect,150,5000),lookAt(add(target,mul(forward,high+.5f)),target)),high+.5f,target};
}
}
