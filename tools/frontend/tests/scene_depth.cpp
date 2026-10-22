// Near plane fitted to visible geometry: frustum-clipped box depths and culling (MIT).
#include "SlotSceneDepth.h"
#include <cassert>
#include <cstdio>
using namespace slot_scene;
static bool near(float a,float b,float tolerance=.01f){return std::abs(a-b)<=tolerance;}
int main(){
    // Eye at the origin looking down -Z; 90 degree square field (tangents 1, 1).
    const Mat eye=lookAt({0,0,0},{0,0,-1});
    {DepthRange r;assert(boxDepth(r,eye,identity(),{-10,-10,-260},{10,10,-200},1,1));assert(r.visible&&near(r.closest,200)&&near(r.farthest,260));}
    // Entirely beside the field, or behind the eye: culled, range untouched.
    {DepthRange r;assert(!boxDepth(r,eye,identity(),{300,-10,-260},{320,10,-200},1,1));assert(!r.visible&&r.closest==1e9f);}
    {DepthRange r;assert(!boxDepth(r,eye,identity(),{-10,-10,50},{10,10,80},1,1));assert(!r.visible);}
    // Partly in view: only the visible part counts (the box reaches x=-50 at depth 40 but
    // the field there is only 40 wide, so its closest visible point is at depth 50).
    {DepthRange r;assert(boxDepth(r,eye,identity(),{50,-10,-300},{90,10,-40},1,1));assert(near(r.closest,50,.05f));}
    // A table top under a level camera that reaches behind the eye: the lower edge of the
    // field (tangent .5) meets the top 100 mm below at depth 200.
    {DepthRange r;assert(boxDepth(r,eye,identity(),{-1000,-110,-2000},{1000,-100,500},.75f,.5f));assert(near(r.closest,200,.05f)&&near(r.farthest,2000,.05f));}
    // The eye inside a box: closest is the epsilon plane.
    {DepthRange r;assert(boxDepth(r,eye,identity(),{-5,-5,-5},{5,5,5},1,1,1));assert(r.visible&&r.closest==1);}
    // Model transforms apply: a 45 degree turned cube's nearest edge.
    {DepthRange r;Mat model=product(translate({0,0,-300}),rotate(0,radians(45),0));assert(boxDepth(r,eye,model,{-50,-50,-50},{50,50,50},1,1));assert(near(r.closest,300-50*std::sqrt(2.f),.05f));}
    // A flat quad (label) still counts.
    {DepthRange r;assert(boxDepth(r,eye,identity(),{-10,-10,-120},{10,10,-120},1,1));assert(near(r.closest,120));}
    // Near plane: just in front of the closest point, clamped 10..150; nothing visible keeps 150.
    {DepthRange r;r.visible=true;r.closest=120;assert(near(hugNear(r),114));r.closest=400;assert(hugNear(r)==150);r.closest=4;assert(hugNear(r)==10);}
    {DepthRange r;assert(hugNear(r)==150);}
    // Several boxes accumulate.
    {DepthRange r;boxDepth(r,eye,identity(),{-10,-10,-500},{10,10,-400},1,1);boxDepth(r,eye,identity(),{-10,-10,-140},{10,10,-130},1,1);assert(near(r.closest,130)&&near(r.farthest,500));}
    std::puts("scene depth ok");return 0;
}
