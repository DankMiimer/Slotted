// Camera pans use finite endpoints and smoothstep, including interrupted pans (MIT).
#pragma once
#include "SlotSceneProfile.h"
namespace slot_scene {
inline ProfileCamera blendCamera(const ProfileCamera&a,const ProfileCamera&b,float progress){
    if(progress<=0)return a;if(progress>=1)return b;
    float q=ease(progress);ProfileCamera c;c.eye=add(a.eye,mul(sub(b.eye,a.eye),q));c.target=add(a.target,mul(sub(b.target,a.target),q));c.fov=a.fov+(b.fov-a.fov)*q;c.authored=true;
    // Opposite authored views can cross their look-at point. Keep a finite direction.
    if(dot(sub(c.eye,c.target),sub(c.eye,c.target))<100){Vec direction=unit(sub(a.eye,a.target));c.eye=add(c.target,mul(direction,10));}
    return c;
}
}
