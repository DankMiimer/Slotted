// Place an unchanged authored layout at a fixed room table anchor (MIT).
// World placement is separate from saved SceneProfile/HomeProfile data.
#pragma once
#include "SlotSceneProfile.h"

namespace slot_scene {
// Only for rigid matrices produced by Placement::matrix() with size=1.
// Furniture's authored scale stays in its draw model; it is not in this root.
inline Mat inverseRigid(const Mat&m){
    Mat out=identity();
    for(int col=0;col<3;col++)for(int row=0;row<3;row++)out.v[col*4+row]=m.v[row*4+col];
    const Vec t={m.v[12],m.v[13],m.v[14]};
    out.v[12]=-dot({out.v[0],out.v[4],out.v[8]},t);
    out.v[13]=-dot({out.v[1],out.v[5],out.v[9]},t);
    out.v[14]=-dot({out.v[2],out.v[6],out.v[10]},t);
    return out;
}
struct WorldCamera {
    Vec eye,target,up;
    float fov;
    Mat worldView;
    Mat view()const{return worldView;}
};
struct WorldLayout {
    Mat root,inverse;
    WorldLayout(const Placement&savedTable,const Placement&worldTable){
        root=product(worldTable.matrix(),inverseRigid(savedTable.matrix()));
        inverse=inverseRigid(root);
    }
    Vec point(Vec local)const{return transform(root,local);}
    Vec direction(Vec local)const{
        return {root.v[0]*local.x+root.v[4]*local.y+root.v[8]*local.z,
                root.v[1]*local.x+root.v[5]*local.y+root.v[9]*local.z,
                root.v[2]*local.x+root.v[6]*local.y+root.v[10]*local.z};
    }
    Mat model(const Mat&local)const{return product(root,local);}
    // Keep the authored view basis rather than reconstructing it from rounded
    // world-space eye/target values. Close inspection cameras otherwise drift
    // after a large room translation. The transformed up vector is also kept
    // for travel/interpolation; table rotations must not introduce camera roll.
    WorldCamera camera(const ProfileCamera&local)const{
        return {point(local.eye),point(local.target),direction({0,1,0}),local.fov,view(local)};
    }
    Mat view(const ProfileCamera&local)const{
        return product(lookAt(local.eye,local.target),inverse);
    }
};
}
