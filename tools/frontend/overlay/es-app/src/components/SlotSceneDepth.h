// Visible depth of model-space boxes, so the near plane follows the closest thing in view (MIT).
#pragma once
#include "SlotSceneMath.h"
namespace slot_scene {
struct DepthRange {float closest=1e9f,farthest=0;bool visible=false;};
// Clips the box `low..high` (model space) to the view frustum and widens `range` by the
// camera depths that remain. `view` is lookAt (camera looks down -Z); tanX/tanY are the
// half-field tangents. Returns false when no part of the box is in view.
inline bool boxDepth(DepthRange&range,const Mat&view,const Mat&model,Vec low,Vec high,float tanX,float tanY,float epsilon=1){
    const Mat m=product(view,model);Vec c[8];
    for(int k=0;k<8;k++)c[k]=transform(m,{k&1?high.x:low.x,k&2?high.y:low.y,k&4?high.z:low.z});
    // A box around the eye reaches the eye itself (parallelepiped coordinates of the origin).
    Vec e1=sub(c[1],c[0]),e2=sub(c[2],c[0]),e3=sub(c[4],c[0]),o=mul(c[0],-1);float det=dot(e1,cross(e2,e3));bool inside=false;
    if(std::abs(det)>1e-6f){
        float a=dot(o,cross(e2,e3))/det,b=dot(e1,cross(o,e3))/det,d=dot(e1,cross(e2,o))/det;
        inside=a>=0&&a<=1&&b>=0&&b<=1&&d>=0&&d<=1;
        if(inside){range.closest=std::min(range.closest,epsilon);range.visible=true;}
    }
    // Inside is >= 0 for each plane (a, b, c) . p + w; depth is -z.
    const float plane[5][4]={{0,0,-1,-epsilon},{1,0,-tanX,0},{-1,0,-tanX,0},{0,1,-tanY,0},{0,-1,-tanY,0}};
    const int face[6][4]={{0,2,6,4},{1,3,7,5},{0,1,5,4},{2,3,7,6},{0,1,3,2},{4,5,7,6}};
    bool any=false;
    for(const auto&f:face){
        Vec poly[16],next[16];int n=4;for(int i=0;i<4;i++)poly[i]=c[f[i]];
        for(const auto&p:plane){
            int count=0;
            for(int i=0;i<n;i++){
                Vec a=poly[i],b=poly[(i+1)%n];float da=p[0]*a.x+p[1]*a.y+p[2]*a.z+p[3],db=p[0]*b.x+p[1]*b.y+p[2]*b.z+p[3];
                if(da>=0&&count<16)next[count++]=a;
                if(((da>=0)!=(db>=0))&&count<16)next[count++]=add(a,mul(sub(b,a),da/(da-db)));
            }
            n=count;for(int i=0;i<n;i++)poly[i]=next[i];if(!n)break;
        }
        for(int i=0;i<n;i++){range.closest=std::min(range.closest,-poly[i].z);range.farthest=std::max(range.farthest,-poly[i].z);any=true;}
    }
    range.visible=range.visible||any;return any||inside;
}
// Largest near plane (mm) that still keeps everything in `range`: just in front of its
// closest point, never past `ceiling` and never closer than `floor`.
inline float hugNear(const DepthRange&range,float floor=10,float ceiling=150){
    return range.visible?std::max(floor,std::min(ceiling,range.closest*.95f)):ceiling;
}
}
