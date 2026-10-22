// Persistent-world camera invariance and four-direction selection checks (MIT).
#include "SlotSpatialNavigation.h"
#include "SlotWorldLayout.h"
#include <cassert>
#include <iostream>
#include <limits>
#include <set>
#include <string>
using namespace slot_scene;
using namespace slot_navigation;
namespace {
void close(Vec a,Vec b,float tolerance=.01f){assert(dot(sub(a,b),sub(a,b))<tolerance*tolerance);}
void matrixClose(const Mat&a,const Mat&b,float tolerance=.01f){
    for(int i=0;i<16;i++)if(std::abs(a.v[i]-b.v[i])>=tolerance){
        std::cerr<<"matrix element "<<i<<": "<<a.v[i]<<" vs "<<b.v[i]<<"\n";assert(false);
    }
}
void navigation(){
    // Identity is not array order; the TV participates as a separate object.
    std::vector<Point> points={{11,100,100},{9,0,100},{7,100,0},{5,200,100},{3,100,200},{-2,400,100}};
    assert(neighbor(points,11,Direction::Left)==9);
    assert(neighbor(points,11,Direction::Right)==5);
    assert(neighbor(points,11,Direction::Up)==7);
    assert(neighbor(points,11,Direction::Down)==3);
    assert(neighbor(points,5,Direction::Right)==-2);
    std::reverse(points.begin(),points.end());
    assert(neighbor(points,11,Direction::Left)==9);
    points.push_back({21,101,1000});points.push_back({22,102,100,false});
    points.push_back({23,std::numeric_limits<float>::quiet_NaN(),100});
    assert(neighbor(points,11,Direction::Right)==5);
    assert(neighbor(points,999,Direction::Right)==noTarget);
    assert(neighbor(points,-2,Direction::Right)==noTarget);
    assert(neighbor({{1,0,0},{2,0,0}},1,Direction::Right)==noTarget);
    // A diagonal-only authored arrangement remains reachable; deterministic ties
    // do not depend on the incoming object's order in a filtered collection.
    assert(neighbor({{0,0,0},{2,20,20}},0,Direction::Right)==2);
    assert(neighbor({{0,0,0},{3,20,-20},{2,20,20}},0,Direction::Right)==2);
    assert(neighbor({{0,100,100},{1,0,105}},0,Direction::Down)==noTarget);

    std::vector<Point> slots;
    for(int i=0;i<12;i++)slots.push_back({i,float(i%3)*100,float(i/3)*100});
    assert(neighbor(slots,4,Direction::Up)==1);
    assert(neighbor(slots,4,Direction::Down)==7);
    assert(neighbor(slots,4,Direction::Left)==3);
    assert(neighbor(slots,4,Direction::Right)==5);
    assert(incomingSlot(slots,5,Direction::Right,12)==3);
    assert(incomingSlot(slots,3,Direction::Left,12)==5);
    assert(incomingSlot(slots,1,Direction::Up,12)==10);
    assert(incomingSlot(slots,10,Direction::Down,12)==1);
    auto move=nextWindow(slots,5,Direction::Right,0,25,12);
    assert(move.changed&&move.first==12&&move.slot==3);
    move=nextWindow(slots,5,Direction::Right,12,25,12);
    assert(move.changed&&move.first==24&&move.slot==0); // only one real game remains
    assert(!nextWindow(slots,0,Direction::Right,24,25,12).changed);
    assert(!nextWindow(slots,0,Direction::Left,0,25,12).changed);
    assert(!nextWindow(slots,0,Direction::Right,0,1,12,true).changed);
    assert(!nextWindow(slots,0,Direction::Right,1,25,12).changed);
    move=nextWindow(slots,0,Direction::Right,24,25,12,true);
    assert(move.changed&&move.first==0&&move.slot==0);
    Point p={99,88,77};
    const auto vp=product(perspective(radians(40),1.5f,10,10000),lookAt({0,0,1000},{0,0,0}));
    assert(projectAnchor(vp,{0,0,0},720,480,1,p));
    assert(p.x==360&&p.y==240);
    const auto old=p;
    assert(!projectAnchor(vp,{0,0,2000},720,480,2,p));
    assert(p.id==old.id&&p.x==old.x&&p.y==old.y);
}
void world(const SceneProfile&profile){
    // Include rotations around all three axes: keeping the implicit world-up
    // after a world transform would incorrectly alter the saved camera framing.
    const Placement anchor={{3700,50,-2100},{12,-57,8}};
    const WorldLayout placed(profile.nodes[0],anchor);
    matrixClose(placed.model(profile.nodes[0].matrix()),anchor.matrix());
    matrixClose(product(placed.root,placed.inverse),identity());
    for(const auto&camera:profile.cameras){
        if(!camera.authored)continue;
        const auto inWorld=placed.camera(camera);
        assert(inWorld.fov==camera.fov);
        close(transform(inWorld.view(),inWorld.eye),{0,0,0});
        matrixClose(product(inWorld.view(),placed.root),lookAt(camera.eye,camera.target));
        const auto before=lookAt(camera.eye,camera.target),after=inWorld.view();
        for(int i=0;i<4+profile.cartridgeCount;i++){
            // Status is local to the TV. Compose the parent once before the
            // world root; a per-node transform would apply the world root twice.
            auto local=profile.nodes[i].matrix();
            if(i==3)local=product(profile.nodes[1].matrix(),local);
            const Vec sample=transform(local,{7,13,-19});
            close(transform(before,sample),transform(after,placed.point(sample)),.03f);
            const auto pre=product(perspective(radians(camera.fov),1.5f,10,10000),before);
            const auto post=product(perspective(radians(camera.fov),1.5f,10,10000),after);
            Point a,b;
            if(projectAnchor(pre,sample,720,480,i,a)){
                assert(projectAnchor(post,placed.point(sample),720,480,i,b));
                // Check subpixel framing inside the display. Off-screen points
                // arbitrarily close to the camera plane amplify float rounding;
                // their camera-space positions are checked above instead.
                if(a.x>=0&&a.x<=720&&a.y>=0&&a.y<=480)
                    assert(std::abs(a.x-b.x)<.03f&&std::abs(a.y-b.y)<.03f);
            }
        }
    }
}
void reachable(const SceneProfile&profile){
    const auto camera=profile.cameras[0];
    const auto vp=product(perspective(radians(camera.fov),1.5f,10,10000),lookAt(camera.eye,camera.target));
    std::vector<Point> points;
    for(int i=0;i<profile.cartridgeCount;i++){
        Point point;
        if(projectAnchor(vp,profile.nodes[4+i].position,720,480,i,point))points.push_back(point);
    }
    for(const auto&start:points){
        std::set<int> visited={start.id};std::vector<int> pending={start.id};
        for(size_t i=0;i<pending.size();i++)for(auto direction:{Direction::Left,Direction::Right,Direction::Up,Direction::Down}){
            const int next=neighbor(points,pending[i],direction);
            if(next!=noTarget&&visited.insert(next).second)pending.push_back(next);
        }
        assert(visited.size()==points.size());
    }
}
}
int main(int argc,char**argv){
    navigation();
    SceneProfile synthetic;synthetic.nodes[0]={{71,-23,113},{-19,38,7}};
    synthetic.cameras[0]={{-200,600,1400},{100,30,-40},37,true};
    world(synthetic);
    for(int i=1;i<argc;i++){
        SceneProfile profile;assert(readSceneProfile(argv[i],profile));
        world(profile);reachable(profile);
    }
    std::cout<<"World/navigation: 4 directions, TV identity, irregular layouts, partial edge windows, camera-up and projection invariance; "
             <<argc-1<<" saved profiles checked.\n";
}
