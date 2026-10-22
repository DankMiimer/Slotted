// Physical table-to-slot path. Source poses use millimetres; no UI/GL (MIT).
#pragma once
#include "SlotSceneProfile.h"
#include <array>
#include <string>
#include <vector>
namespace slot_scene {
struct Quaternion {float x,y,z,w;};
inline Quaternion quaternion(const Mat&m){
    Quaternion q;float t=m.v[0]+m.v[5]+m.v[10];
    if(t>0){float s=std::sqrt(t+1)*2;q={ (m.v[6]-m.v[9])/s,(m.v[8]-m.v[2])/s,(m.v[1]-m.v[4])/s,s/4};}
    else if(m.v[0]>m.v[5]&&m.v[0]>m.v[10]){float s=std::sqrt(1+m.v[0]-m.v[5]-m.v[10])*2;q={s/4,(m.v[4]+m.v[1])/s,(m.v[8]+m.v[2])/s,(m.v[6]-m.v[9])/s};}
    else if(m.v[5]>m.v[10]){float s=std::sqrt(1+m.v[5]-m.v[0]-m.v[10])*2;q={(m.v[4]+m.v[1])/s,s/4,(m.v[9]+m.v[6])/s,(m.v[8]-m.v[2])/s};}
    else{float s=std::sqrt(1+m.v[10]-m.v[0]-m.v[5])*2;q={(m.v[8]+m.v[2])/s,(m.v[9]+m.v[6])/s,s/4,(m.v[1]-m.v[4])/s};}return q;
}
inline Mat blendRotation(const Mat&a,const Mat&b,float t){
    Quaternion p=quaternion(a),q=quaternion(b);float d=p.x*q.x+p.y*q.y+p.z*q.z+p.w*q.w;
    if(d<0){q={-q.x,-q.y,-q.z,-q.w};d=-d;}
    float l=1-t,r=t;if(d<.9995f){float angle=std::acos(std::min(1.f,d)),s=std::sin(angle);l=std::sin((1-t)*angle)/s;r=std::sin(t*angle)/s;}
    q={p.x*l+q.x*r,p.y*l+q.y*r,p.z*l+q.z*r,p.w*l+q.w*r};float n=std::sqrt(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w);q={q.x/n,q.y/n,q.z/n,q.w/n};
    Mat m=identity();float x=q.x,y=q.y,z=q.z,w=q.w;
    m.v[0]=1-2*(y*y+z*z);m.v[1]=2*(x*y+z*w);m.v[2]=2*(x*z-y*w);
    m.v[4]=2*(x*y-z*w);m.v[5]=1-2*(x*x+z*z);m.v[6]=2*(y*z+x*w);
    m.v[8]=2*(x*z+y*w);m.v[9]=2*(y*z-x*w);m.v[10]=1-2*(x*x+y*y);return m;
}
inline Vec mix(Vec a,Vec b,float t){return add(a,mul(sub(b,a),t));}
// Right-handed rotation of `angle` radians about `axis`, column-major like rotate().
inline Mat axisRotation(Vec axis,float angle){
    axis=unit(axis);float c=std::cos(angle),s=std::sin(angle),t=1-c,x=axis.x,y=axis.y,z=axis.z;Mat m=identity();
    m.v[0]=t*x*x+c;m.v[1]=t*x*y+s*z;m.v[2]=t*x*z-s*y;
    m.v[4]=t*x*y-s*z;m.v[5]=t*y*y+c;m.v[6]=t*y*z+s*x;
    m.v[8]=t*x*z+s*y;m.v[9]=t*y*z-s*x;m.v[10]=t*z*z+c;return m;
}
// Raise a resting shell's far edge toward the viewer about its near edge (at
// centre height), so the label turns up without the near edge entering the table.
inline Mat tiltToward(const Mat&model,Vec low,Vec high,Vec eye,float angle){
    if(angle==0)return model;
    Vec centre=transform(model,mul(add(low,high),.5f)),toward=sub(eye,centre);toward.y=0;toward=unit(toward);
    if(dot(toward,toward)<.5f)return model;
    float reach=0;
    for(int k=0;k<8;k++)reach=std::max(reach,dot(sub(transform(model,{k&1?high.x:low.x,k&2?high.y:low.y,k&4?high.z:low.z}),centre),toward));
    Vec pivot=add(centre,mul(toward,reach));
    return product(translate(pivot),product(axisRotation(cross({0,1,0},toward),angle),product(translate(mul(pivot,-1)),model)));
}
// The label lies in mesh XY. Upright labels must stay upright when selected;
// apply the label-up tip only in proportion to its authored alignment with Y.
inline float hoverTiltFactor(const Mat&home){
    const Vec normal=unit({home.v[8],home.v[9],home.v[10]});
    const float flat=std::abs(normal.y);return flat*flat*flat*flat;
}
inline Mat cartridgeHoverTilt(const Mat&home,Vec low,Vec high,Vec eye,float angle){
    const float factor=hoverTiltFactor(home);if(factor<.0001f)return home;
    return tiltToward(home,low,high,eye,angle*factor);
}
// Exact underdamped spring step, stable at the handheld's variable frame rate.
inline void hoverSpring(float&position,float&velocity,float goal,float delta){
    const float dt=std::max(0.f,std::min(.1f,delta)),omega=23,damping=15,w=std::sqrt(omega*omega-damping*damping);
    const float c=std::cos(w*dt),sn=std::sin(w*dt),decay=std::exp(-damping*dt),x=position-goal,v=velocity;
    position=goal+decay*(x*c+(v+damping*x)/w*sn);
    velocity=decay*(v*c-(damping*v+omega*omega*x)/w*sn);
    if(std::abs(position-goal)<.0001f&&std::abs(velocity)<.001f){position=goal;velocity=0;}
}
// Inspection: shell faces the camera (mesh +X right, +Y up, +Z toward the eye),
// tilted about the camera's right axis, then spun about its up axis (turntable).
inline Mat inspectRotation(Vec eye,Vec target,float yaw,float pitch){
    Vec forward=unit(sub(target,eye)),right=unit(cross(forward,{0,1,0})),up=cross(right,forward);
    Mat face=identity();
    face.v[0]=right.x;face.v[1]=right.y;face.v[2]=right.z;face.v[4]=up.x;face.v[5]=up.y;face.v[6]=up.z;
    face.v[8]=-forward.x;face.v[9]=-forward.y;face.v[10]=-forward.z;
    return product(product(axisRotation(up,yaw),axisRotation(right,pitch)),face);
}
// Carry a resting pose (uniform scale `size`) toward `rotation` centred at `centre`;
// `pivot` is the mesh-space centre that follows the straight path.
inline Mat inspectBlend(const Mat&rest,Vec pivot,float size,const Mat&rotation,Vec centre,float t){
    Mat r=rest;r.v[12]=r.v[13]=r.v[14]=0;for(int c=0;c<3;c++)for(int k=0;k<3;k++)r.v[4*c+k]/=size;
    float q=ease(t);Vec from=transform(rest,pivot);
    return product(product(product(translate(mix(from,centre,q)),blendRotation(r,rotation,q)),scale(size,size,size)),translate(mul(pivot,-1)));
}
// Top-loading slot registrations (console mm) from tools/consolebuild/snes.py and
// n64.py. Centre-based media bottoms seat at entry-seatDepth; shell thickness stays
// centred on the slot.
struct SlotRegistration {float entry=0,seatDepth=0,slot=0;};
inline bool slotRegistration(const std::string&console,SlotRegistration&r){
    if(console=="snes")r={33.67f,30,-22.7315683f};
    else if(console=="snes-us")r={34,32,-18.132f};
    else if(console=="n64")r={10.87158f,27,-61.7f};
    // Mega Drive / Genesis (models.py media_slot, themebuild/consoles.py): entry at the
    // raised deck (10 units x yscale 1.7), sink 48 and slot -53 native, 224/109 per mm.
    else if(console=="md"||console=="md-jp"){const float q=224.f/109;r={17/q,48/q,-53/q};}
    // PICO-8 fantasy console (themebuild/consoles.py): entry 12, sink 64, slot -34 native, 2.2 per mm.
    else if(console=="pico8"){const float q=2.2f;r={12/q,64/q,-34/q};}
    else return false;
    return true;
}
inline Vec cartridgeSeat(const SlotRegistration&r,float mediaHeight){return {0,mediaHeight/2+r.entry-r.seatDepth,r.slot};}
inline Vec snesSeat(bool us,float mediaHeight){SlotRegistration r;slotRegistration(us?"snes-us":"snes",r);return cartridgeSeat(r,mediaHeight);}
// Front loader (NES; tools/consolebuild/models.py and media-specs.h), console mm:
// tunnel centre x, the height the shell's bottom rides at just above the tray, the
// console front, the seated shell-centre depth, press-down travel and the lid hinge.
struct FrontRegistration {float x=0,ride=0,front=0,seat=0,press=0,hingeY=0,hingeZ=0,lid=0;};
inline bool frontRegistration(const std::string&console,FrontRegistration&r){
    if(console!="nes")return false;
    const float q=196.f/120; // NES native units per mm
    r.x=-45/q;r.ride=(-53.55f+.6f)/q;r.front=172/q;r.seat=35/q;r.press=14.7f/q;r.hingeY=4.2f/q;r.hingeZ=135/q;r.lid=radians(80);
    return true;
}
// The shell (bounding-box centre `centre`, in its own mm frame) lies label-up with
// its connector toward the console (shell +X,+Y,+Z -> console -X,+Z,+Y). It rises
// off the table, comes down in front of the opening at tray height, slides in and
// presses down. Returns the shell-origin pose in mm, like cartridgePath.
inline Mat frontLoaderPath(const Placement&home,const Placement&console,const FrontRegistration&r,Vec centre,float length,float thickness,float t){
    t=std::max(0.f,std::min(1.f,t));
    Mat a=rotate(radians(home.rotation.x),radians(home.rotation.y),radians(home.rotation.z));
    Mat flat=identity();flat.v[0]=-1;flat.v[5]=0;flat.v[6]=1;flat.v[9]=1;flat.v[10]=0;
    Mat b=product(rotate(radians(console.rotation.x),radians(console.rotation.y),radians(console.rotation.z)),flat),place=console.matrix();
    float y=r.ride+thickness/2;
    Vec outside=transform(place,{r.x,y,r.front+5.5f+length/2}),inside=transform(place,{r.x,y,r.seat}),pressed=transform(place,{r.x,y-r.press,r.seat});
    Vec start=add(home.position,transform(a,centre)),raised=start;raised.y=std::max(start.y+30,outside.y+25);
    Vec p;Mat turn=a;
    if(t<.2f)p=mix(start,raised,ease(t/.2f));
    else if(t<.55f){float q=ease((t-.2f)/.35f);p=mix(raised,outside,q);turn=blendRotation(a,b,q);}
    else if(t<.85f){p=mix(outside,inside,ease((t-.55f)/.3f));turn=b;}
    else{p=mix(inside,pressed,ease((t-.85f)/.15f));turn=b;}
    return product(translate(sub(p,transform(turn,centre))),turn);
}
// Lid opening fraction along the same insertion progress (open before the slide,
// closed again during the press); ejection runs it backwards.
inline float frontLidOpening(float t){return ease((t-.3f)/.22f)*(1-ease((t-.88f)/.12f));}
// Top-loading optical console (PlayStation; tools/consolebuild/ps1.py / darkigorek_psx.py
// registration, 1.6 units per mm): disc mid-plane centre on the spindle, rear lid hinge
// and opening (as ps1-scene.h), disc size; console mm.
struct OpticalRegistration {Vec centre={0,0,0};float hingeY=0,hingeZ=0,lid=0,radius=60,thickness=1.2f;};
inline bool opticalRegistration(const std::string&console,OpticalRegistration&r){
    if(console!="psx")return false;
    const float q=1.6f;
    r.centre={-.000095367f/q,28.631466627f/q,0};r.hingeY=26.131391525f/q;r.hingeZ=-125.197827816f/q;r.lid=radians(78);
    return true;
}
// Discs lie label-up in the console (shell +Z -> console +Y), as they do on the table.
inline Mat discOrientation(){return rotate(radians(-90),0,0);}
// The lid opens before the disc arrives and stays open while it is loaded (ejection
// reverses); prelaunch closing is driven explicitly by the presentation.
inline float opticalLidOpening(int phase,float t){return phase==0?1.f:ease(t/.3f);}
// Handhelds (tools/slotlaunch/cartridge-console.h kinds 1/3/4/5, textured-data.h,
// media-specs.h; console mm in each model's own frame): how the console rests on the
// table (`table`), the seated media origin and orientation, the direction it slides in
// from (`out`) and how far; the PSP's UMD cover hinge and opening. GB/GBC stand
// upright (cart from above, label to the back); the GBA SP and DS Lite models already
// lie open (cart through the front edge / card through Slot-1 at the back, label
// down); the PSP lies face-down so its rear cover opens upward.
struct HandheldRegistration {Mat table=identity(),media=identity();Vec seat={0,0,0},out={0,1,0};float travel=0;bool cover=false;Vec hinge={0,0,0};float coverOpen=0;};
inline bool handheldRegistration(const std::string&console,HandheldRegistration&r){
    const float pi=3.14159265358979f;
    if(console=="gb"){ // 1.8667 native/mm; target ry-final_ry, hover ry+final_ry-6, label plane +3.9 mm
        const float q=1.8666667f;r.media=rotate(0,pi,0);r.seat={0,77.124143f/q,-26.624431f/q+3.9f};r.travel=(193.39081f-77.124143f)/q;return true;}
    if(console=="gbc"){
        const float q=2.1538462f;r.media=rotate(0,pi,0);r.seat={0,70.888721f/q,-16.127651f/q+3.9f};r.travel=(205.96564f-70.888721f)/q;return true;}
    if(console=="gba"){ // bay centre -26.03 mm, seated 24.45 mm, entering from slot+final_ry+9
        r.media=rotate(pi/2,0,0);r.seat={0,-26.03f,24.45f};r.out={0,0,1};r.travel=165.62309f/2.7317073f-24.45f;return true;}
    if(console=="nds"){ // Slot-1 mouth -113.29 native; the 35 mm card seats 1 mm proud of it
        const float q=3.037594f;r.media=product(rotate(0,pi,0),rotate(pi/2,0,0));r.seat={-28/q,-65.175f/q,-113.29114f/q+17.5f-1};r.out={0,0,-1};r.travel=38;return true;}
    if(console=="psp"){ // UMD label (0,1.13,-23.23) native, cover hinge (0,-103.42,-30.04), opens 42 degrees
        const float q=2.8335301f;r.table=rotate(pi/2,0,0);r.media=rotate(0,pi,0);r.seat={0,1.1334120f/q,(-23.234947f+5.98f)/q};
        r.travel=200/q;r.cover=true;r.hinge={0,-103.42385f/q,-30.035419f/q};r.coverOpen=radians(42);return true;}
    return false;
}
// A handheld's media rises off the table, travels at a safe height to above the point
// just outside its slot, comes down to it, then slides in along -out. `frame` is the
// console's rigid mm frame on the table (placement x table orientation).
inline Mat slidePath(const Placement&home,const Mat&frame,Vec seat,const Mat&local,Vec out,float travel,float clearance,float t){
    t=std::max(0.f,std::min(1.f,t));
    Mat a=rotate(radians(home.rotation.x),radians(home.rotation.y),radians(home.rotation.z)),turn=frame;turn.v[12]=turn.v[13]=turn.v[14]=0;
    Mat b=product(turn,local);
    Vec approach=transform(frame,add(seat,mul(out,travel))),end=transform(frame,seat);
    Vec raised=home.position;raised.y=std::max(clearance,std::max(home.position.y,approach.y)+40);
    Vec above=approach;above.y=std::max(raised.y,approach.y);
    Vec p;Mat rot=a;
    if(t<.2f)p=mix(home.position,raised,ease(t/.2f));
    else if(t<.55f){float q=ease((t-.2f)/.35f);p=mix(raised,above,q);rot=blendRotation(a,b,q);}
    else if(t<.7f){p=mix(above,approach,ease((t-.55f)/.15f));rot=b;}
    else{p=mix(approach,end,ease((t-.7f)/.3f));rot=b;}
    return product(translate(p),rot);
}
// The PSP cover opens before the UMD arrives and closes over it once it is seated.
inline float pspCoverOpening(float t){return ease((t-.3f)/.2f)*(1-ease((t-.85f)/.12f));}
inline Mat hingeFrame(const Mat&frame,Vec hinge,float angle){return product(frame,product(translate(hinge),product(axisRotation({1,0,0},angle),translate(mul(hinge,-1)))));}
inline Mat pspPath(const Placement&home,const Mat&frame,const HandheldRegistration&r,float clearance,float t){
    t=std::max(0.f,std::min(1.f,t));
    if(t<.82f)return slidePath(home,hingeFrame(frame,r.hinge,-r.coverOpen),r.seat,r.media,r.out,r.travel,clearance,t/.82f);
    Mat cover=hingeFrame(frame,r.hinge,-r.coverOpen*pspCoverOpening(t)),turn=cover;turn.v[12]=turn.v[13]=turn.v[14]=0;
    return product(translate(transform(cover,r.seat)),product(turn,r.media));
}
// A point in the local frame of a rigid pose with uniform scale.
inline Vec intoFrame(const Mat&pose,Vec world){
    Vec d=sub(world,{pose.v[12],pose.v[13],pose.v[14]});float s2=pose.v[0]*pose.v[0]+pose.v[1]*pose.v[1]+pose.v[2]*pose.v[2];
    return {(pose.v[0]*d.x+pose.v[1]*d.y+pose.v[2]*d.z)/s2,(pose.v[4]*d.x+pose.v[5]*d.y+pose.v[6]*d.z)/s2,(pose.v[8]*d.x+pose.v[9]*d.y+pose.v[10]*d.z)/s2};
}
// Contact-driven spring flap (port of tools/slotlaunch/n64-flaps.h), console units.
// `profile` is the flap's (y,z) section; it turns about the X axis through `hinge`
// just far enough that the band within halfThickness+clearance of the slot stays
// below the media's lowest point.
struct FlapSection {std::vector<std::array<float,2>> profile;float hinge[2];int side;};
inline bool flapClear(const FlapSection&f,float slot,float clearance,float angle,float bottom,float halfThickness){
    const size_t n=f.profile.size();std::vector<float> y(n),z(n);float c=std::cos(angle),s=std::sin(angle),highest=-10000,boundary=halfThickness+clearance;
    for(size_t i=0;i<n;i++){
        float dy=f.profile[i][0]-f.hinge[0],dz=f.profile[i][1]-f.hinge[1];
        y[i]=f.hinge[0]+dy*c-dz*s;z[i]=f.side*(f.hinge[1]+dy*s+dz*c-slot);
        if(z[i]<=boundary)highest=std::max(highest,y[i]);
    }
    for(size_t i=0;i<n;i++)for(size_t j=i+1;j<n;j++)
        if((z[i]<boundary&&boundary<z[j])||(z[j]<boundary&&boundary<z[i]))highest=std::max(highest,y[i]+(y[j]-y[i])*(boundary-z[i])/(z[j]-z[i]));
    return highest<=bottom-clearance;
}
inline float flapAngle(const FlapSection&f,float slot,float clearance,float bottom,float halfThickness){
    if(flapClear(f,slot,clearance,0,bottom,halfThickness))return 0;
    float lo=0,hi=radians(89);
    for(int i=0;i<18;i++){float mid=(lo+hi)/2;if(flapClear(f,slot,clearance,-f.side*mid,bottom,halfThickness))hi=mid;else lo=mid;}
    return -f.side*hi;
}
// `local` is the media's seated orientation in the console frame (identity for
// upright cartridges, discOrientation() for discs).
inline Mat cartridgePath(const Placement&home,const Placement&console,Vec seat,float clearance,float t,const Mat&local=identity()){
    t=std::max(0.f,std::min(1.f,t));Mat a=rotate(radians(home.rotation.x),radians(home.rotation.y),radians(home.rotation.z));
    Mat b=product(rotate(radians(console.rotation.x),radians(console.rotation.y),radians(console.rotation.z)),local);
    Vec end=transform(console.matrix(),seat),raised=home.position,above=end;
    raised.y=above.y=std::max(clearance,std::max(home.position.y,end.y)+55);
    Vec p;float turn=0;
    if(t<.25f)p=mix(home.position,raised,ease(t/.25f));
    else if(t<.72f){float q=ease((t-.25f)/.47f);p=mix(raised,above,q);turn=q;}
    else{p=mix(above,end,ease((t-.72f)/.28f));turn=1;}
    return product(translate(p),blendRotation(a,b,turn));
}
}
