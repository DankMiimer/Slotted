#include "SlotTabletopMotion.h"
#include <cassert>
#include <cstdio>
using namespace slot_scene;
static void near(float a,float b,float limit=.001f){assert(std::abs(a-b)<limit);}
int main(){
    Placement home={{-307.076f,10.0343f,719.621f},{-90,23,0}},console={{-89.1323f,48.9303f,399.854f},{0,-27,0}};
    Vec seat=snesSeat(false,78.07376f);near(seat.y-78.07376f/2,3.67f);near(seat.z,-22.7315683f);
    Mat a=cartridgePath(home,console,seat,220,0),b=home.matrix();for(int i=0;i<16;i++)near(a.v[i],b.v[i]);
    a=cartridgePath(home,console,seat,220,1);b=product(console.matrix(),translate(seat));for(int i=0;i<16;i++)near(a.v[i],b.v[i]);
    for(float boundary:{.25f,.72f}){a=cartridgePath(home,console,seat,220,boundary-.000001f);b=cartridgePath(home,console,seat,220,boundary+.000001f);for(int i=0;i<16;i++)near(a.v[i],b.v[i],.01f);}
    for(int i=0;i<=1000;i++){
        float t=i/1000.f;Mat m=cartridgePath(home,console,seat,220,t);
        for(float v:m.v)assert(std::isfinite(v));
        for(int c=0;c<3;c++)near(m.v[4*c]*m.v[4*c]+m.v[4*c+1]*m.v[4*c+1]+m.v[4*c+2]*m.v[4*c+2],1);
        if(t>=.25f&&t<=.72f)near(m.v[13],220);
    }
    // Short rotation across +/-180, without an unintended complete spin.
    a=blendRotation(rotate(0,radians(179),0),rotate(0,radians(-179),0),.5f);near(a.v[0],-1);near(a.v[10],-1);
    // Axis rotation agrees with the Euler helper and stays orthonormal.
    a=axisRotation({0,1,0},radians(33));b=rotate(0,radians(33),0);for(int i=0;i<16;i++)near(a.v[i],b.v[i]);
    a=axisRotation({1,2,3},.7f);for(int c=0;c<3;c++)near(a.v[4*c]*a.v[4*c]+a.v[4*c+1]*a.v[4*c+1]+a.v[4*c+2]*a.v[4*c+2],1);
    // Selection tilt: a flat 130 x 20 x 78 mm shell viewed from +Z lifts its far
    // (-Z) edge, keeps its near edge in place and never dips below its rest bottom.
    Mat flat=translate({50,10,0});Vec low={-65,-10,-39},high={65,10,39},eye={50,900,1500};
    a=tiltToward(flat,low,high,eye,0);for(int i=0;i<16;i++)near(a.v[i],flat.v[i]);
    a=tiltToward(flat,low,high,eye,radians(12));
    Vec far=transform(a,{0,10,-39}),nearTop=transform(a,{0,10,39});
    assert(far.y>10+78*std::sin(radians(12))-.01f);near(nearTop.z,transform(flat,{0,10,39}).z,2.5f);
    for(int k=0;k<8;k++)assert(transform(a,{k&1?high.x:low.x,k&2?high.y:low.y,k&4?high.z:low.z}).y>=-.001f);
    // Inspection: the label normal faces the eye and its top is camera-up; yaw 90
    // turns the front to camera-right; pitch -90 turns it up.
    // Authored upright rotations never receive the flat-card 12-degree tip.
    for(float yaw:{0.f,27.f,90.f,-133.f})for(float roll:{0.f,90.f}){
        Mat home=product(translate({90,40,500}),rotate(0,radians(yaw),radians(roll)));
        Mat hover=cartridgeHoverTilt(home,{-30,-40,-4},{30,40,4},eye,radians(12));
        for(int k=0;k<16;k++)near(hover.v[k],home.v[k]);
    }
    near(hoverTiltFactor(rotate(-radians(90),0,0)),1);
    for(float dt:{1/120.f,1/30.f,1/18.f,.1f}){
        float height=0,velocity=0,maximum=0;
        for(int k=0;k<int(2/dt);k++){hoverSpring(height,velocity,1,dt);maximum=std::max(maximum,height);assert(std::isfinite(height)&&std::isfinite(velocity));}
        assert(maximum>1&&maximum<1.09f);near(height,1);near(velocity,0);
        for(int k=0;k<int(2/dt);k++)hoverSpring(height,velocity,0,dt);
        near(height,0);near(velocity,0);
    }
    Vec at={0,400,900},look={100,0,0},toEye=unit(sub(at,look));
    a=inspectRotation(at,look,0,0);Vec front=transform(a,{0,0,1}),top=transform(a,{0,1,0});
    near(dot(front,toEye),1);assert(top.y>.8f);
    Vec right=unit(cross(unit(sub(look,at)),{0,1,0})),up=cross(right,unit(sub(look,at)));
    a=inspectRotation(at,look,radians(90),0);near(dot(transform(a,{0,0,1}),right),1);
    a=inspectRotation(at,look,0,radians(-90));near(dot(transform(a,{0,0,1}),up),1);
    // The blend starts at the resting pose and ends centred on the inspection point.
    Mat rest=product(product(translate({-300,12,700}),rotate(radians(-90),radians(23),0)),scale(1/1.6f,1/1.6f,1/1.6f));
    Vec pivot={0,30,5},centre={20,300,600};Mat turn=inspectRotation(at,look,radians(40),radians(-20));
    a=inspectBlend(rest,pivot,1/1.6f,turn,centre,0);for(int i=0;i<16;i++)near(a.v[i],rest.v[i]);
    a=inspectBlend(rest,pivot,1/1.6f,turn,centre,1);Vec c=transform(a,pivot);near(c.x,centre.x,.01f);near(c.y,centre.y,.01f);near(c.z,centre.z,.01f);
    for(int i=0;i<3;i++){Vec axis=transform(a,{float(i==0),float(i==1),float(i==2)}),zero=transform(a,{0,0,0}),want=transform(turn,{float(i==0),float(i==1),float(i==2)});
        Vec got=mul(sub(axis,zero),1.6f);near(got.x,want.x,.001f);near(got.y,want.y,.001f);near(got.z,want.z,.001f);}
    // Registered seats: SNES values unchanged by the table; N64 from n64.py.
    SlotRegistration md;assert(slotRegistration("md",md)&&slotRegistration("md-jp",md));
    near(md.entry*224/109,17);near(md.seatDepth*224/109,48);near(md.slot*224/109,-53);
    SlotRegistration n64;assert(!slotRegistration("nes",n64)&&slotRegistration("n64",n64));
    Vec n64Seat=cartridgeSeat(n64,76.6f);near(n64Seat.y-76.6f/2,10.87158f-27);near(n64Seat.z,-61.7f);
    // A uniform-scale rigid pose round-trips through intoFrame.
    Mat pose=product(product(translate({-89,49,400}),rotate(0,radians(-27),0)),scale(1/1.5f,1/1.5f,1/1.5f));
    Vec local={12,-30,44},back=intoFrame(pose,transform(pose,local));near(back.x,local.x,.001f);near(back.y,local.y,.001f);near(back.z,local.z,.001f);
    // N64 rear dust flap (tools/slotlaunch/n64-data.h, console units): shut while the
    // cart is above it, then opening further and always clear as the cart descends.
    FlapSection flap{{{{13.772778f,-113.327232f}},{{13.772778f,-93.195291f}},{{14.2796475f,-92.6835315f}},{{15.800514f,-92.6835315f}},
        {{16.3073775f,-113.327232f}},{{16.3073775f,-93.195291f}}},{15.04007775f,-113.327232f},-1};
    near(flapAngle(flap,-92.55f,.375f,40,13.875f),0);
    float previous=0;
    for(float bottom=16;bottom>-30;bottom-=2){
        float angle=flapAngle(flap,-92.55f,.375f,bottom,13.875f);
        assert(std::abs(angle)+1e-4f>=std::abs(previous)&&angle>=0);
        assert(flapClear(flap,-92.55f,.375f,angle,bottom,13.875f));previous=angle;
    }
    assert(previous>radians(20));
    // NES front loader: starts at the table pose, ends pressed down on its seat inside
    // the tunnel, label up and connector toward the back; continuous across phases;
    // the shell bottom never drops below the tray ride height before the press.
    {
    FrontRegistration front;assert(frontRegistration("nes",front)&&!frontRegistration("snes",front));
    Placement nesHome={{-250,9.5f,650},{-90,15,0}},nes={{-90,72,400},{0,-27,0}};
    Vec centre={0,0,0};const float length=133,thickness=19;
    a=frontLoaderPath(nesHome,nes,front,centre,length,thickness,0);b=nesHome.matrix();for(int i=0;i<16;i++)near(a.v[i],b.v[i]);
    a=frontLoaderPath(nesHome,nes,front,centre,length,thickness,1);
    Vec seated=intoFrame(nes.matrix(),transform(a,{0,0,0}));
    near(seated.x,front.x,.01f);near(seated.y,front.ride+thickness/2-front.press,.01f);near(seated.z,front.seat,.01f);
    Vec up=sub(transform(a,{0,0,1}),transform(a,{0,0,0})),toward=sub(transform(a,{0,1,0}),transform(a,{0,0,0}));
    near(up.y,1);Vec forward=transform(rotate(0,radians(-27),0),{0,0,1});near(dot(toward,forward),1);
    for(float boundary:{.2f,.55f,.85f}){a=frontLoaderPath(nesHome,nes,front,centre,length,thickness,boundary-.000001f);b=frontLoaderPath(nesHome,nes,front,centre,length,thickness,boundary+.000001f);for(int i=0;i<16;i++)near(a.v[i],b.v[i],.01f);}
    for(int i=550;i<=850;i++){Vec c=intoFrame(nes.matrix(),transform(frontLoaderPath(nesHome,nes,front,centre,length,thickness,i/1000.f),{0,0,0}));near(c.y-thickness/2,front.ride,.01f);}
    near(frontLidOpening(0),0);near(frontLidOpening(1),0);near(frontLidOpening(.7f),1);
    }
    // Handhelds: slide paths start at the table pose and end seated; GB labels face the
    // back, GBA/DS labels face down; the PSP UMD ends with its cover closed.
    {
    Placement table={{-250,10,650},{-90,15,0}},hand={{-90,40,400},{0,-27,0}};
    for(const char*name:{"gb","gbc","gba","nds","psp"}){
        HandheldRegistration h;assert(handheldRegistration(name,h));
        Mat frame=product(hand.matrix(),h.table);
        Mat start=h.cover?pspPath(table,frame,h,300,0):slidePath(table,frame,h.seat,h.media,h.out,h.travel,300,0),rest=table.matrix();
        for(int i=0;i<16;i++)near(start.v[i],rest.v[i]);
        Mat end=h.cover?pspPath(table,frame,h,300,1):slidePath(table,frame,h.seat,h.media,h.out,h.travel,300,1);
        Vec seated=intoFrame(frame,transform(end,{0,0,0}));near(seated.x,h.seat.x,.01f);near(seated.y,h.seat.y,.01f);near(seated.z,h.seat.z,.01f);
        for(float boundary:{.2f,.55f,.7f}){
            float a=boundary-.000001f,b2=boundary+.000001f;
            Mat x=slidePath(table,frame,h.seat,h.media,h.out,h.travel,300,a),y=slidePath(table,frame,h.seat,h.media,h.out,h.travel,300,b2);
            for(int i=0;i<16;i++)near(x.v[i],y.v[i],.01f);
        }
        Vec label=sub(intoFrame(frame,transform(end,{0,0,1})),seated);
        if(std::string(name)=="gb"||std::string(name)=="gbc"||std::string(name)=="psp")near(label.z,-1,.001f);else near(label.y,-1,.001f);
    }
    HandheldRegistration psp;handheldRegistration("psp",psp);Mat frame=product(hand.matrix(),psp.table);
    Mat x=pspPath(table,frame,psp,300,.82f-.000001f),y=pspPath(table,frame,psp,300,.82f+.000001f);for(int i=0;i<16;i++)near(x.v[i],y.v[i],.01f);
    near(pspCoverOpening(0),0);near(pspCoverOpening(.6f),1);near(pspCoverOpening(1),0);
    // Face-down: the PSP's back (-Z) points up on the table.
    near(sub(transform(frame,{0,0,-1}),transform(frame,{0,0,0})).y,1,.001f);
    SlotRegistration pico;assert(slotRegistration("pico8",pico));near(pico.slot*2.2f,-34);
    }
    std::puts("tabletop motion: source/home, registered seats, clearance, continuous phases, rigid rotation, selection tilt, inspection, N64 flaps, NES front loading and handheld slides passed");
}
