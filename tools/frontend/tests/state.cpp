#include "../SlotState.h"
#include "../overlay/es-core/src/components/SlotVideo.h"
#include <vector>
#include <cassert>
#include <iostream>

static void finish(slot::State& s) { for (int n=0; n<100 && s.busy(); ++n) s.update(.05f); }
int main() {
    {
        std::vector<unsigned char> rgba(856*480*4,0);float crop[4];
        assert(!slot::stackedVideoBounds(rgba.data(),856,480,crop));
        for(int y=0;y<480;y++)for(int x=280;x<600;x++)rgba[(y*856+x)*4]=180;
        assert(slot::stackedVideoBounds(rgba.data(),856,480,crop));
        assert(crop[0]>.31f && crop[0]<.34f && crop[2]>.69f && crop[2]<.72f);
        assert(crop[1]==0 && crop[3]==1);
        for(auto& p:rgba)p=180;
        assert(!slot::stackedVideoBounds(rgba.data(),856,480,crop));
        assert(!slot::stackedVideoBounds(rgba.data(),320,480,crop));
    }
    slot::State s;
    {
        slot::State tabletop;tabletop.durations(.1f,.1f);tabletop.presentationDurations(.2f,.3f);
        tabletop.insert("A");finish(tabletop);assert(tabletop.takeLaunch().empty());
        tabletop.play("A");assert(tabletop.takeLaunch().empty()&&tabletop.phase()==slot::Phase::Powering);
        tabletop.insert("B");tabletop.eject();assert(tabletop.inserted()=="A"&&tabletop.desired()=="A");
        tabletop.update(.1f);tabletop.cancelLaunch();assert(!tabletop.launching()&&tabletop.takeLaunch().empty());
        tabletop.play("A");assert(tabletop.takeLaunch().empty());
        for(int i=0;i<20;i++){tabletop.update(.05f);if(tabletop.phase()==slot::Phase::Zooming)break;}
        assert(tabletop.phase()==slot::Phase::Zooming&&tabletop.takeLaunch().empty());
        tabletop.cancelLaunch();assert(tabletop.inserted()=="A"&&tabletop.takeLaunch().empty());
        tabletop.play("A");assert(tabletop.takeLaunch().empty());
        for(int i=0;i<20;i++)tabletop.update(.05f);
        assert(tabletop.takeLaunch()=="A"&&tabletop.takeLaunch().empty());
        tabletop.returned();tabletop.play("A");assert(tabletop.takeLaunch().empty()&&tabletop.phase()==slot::Phase::Powering);
    }
    {
        slot::State optical;optical.durations(.1f,.1f,1.f);
        optical.insert("discA");finish(optical);
        assert(optical.phase()==slot::Phase::Inserted && optical.takeLaunch().empty());
        optical.play("discA");assert(optical.takeLaunch().empty() && optical.closing());
        for(int i=0;i<9;i++){optical.update(.1f);assert(optical.takeLaunch().empty());}
        optical.play("discB");optical.eject();assert(optical.inserted()=="discA");
        for(int i=0;i<3;i++)optical.update(.1f);
        assert(optical.takeLaunch()=="discA" && optical.takeLaunch().empty());
        optical.returned();assert(optical.phase()==slot::Phase::Inserted);
        optical.play("discB");finish(optical);
        assert(optical.inserted()=="discB" && optical.takeLaunch().empty() && optical.closing());
        for(int i=0;i<22;i++)optical.update(.05f);
        assert(optical.takeLaunch()=="discB" && optical.takeLaunch().empty());
    }
    s.eject(); assert(s.phase()==slot::Phase::Empty);
    s.insert("gb:/games/A.gb");
    assert(s.target()=="gb:/games/A.gb" && s.inserted().empty());
    // New highlighted entries do not touch this independent controller.
    finish(s); assert(s.inserted()=="gb:/games/A.gb" && s.takeLaunch().empty());
    s.insert("gb:/games/A.gb"); assert(!s.busy());
    s.insert("gb:/games/B.gb");
    assert(s.phase()==slot::Phase::Ejecting && s.target()=="gb:/games/A.gb");
    s.insert("gb:/games/C.gb"); finish(s);
    assert(s.inserted()=="gb:/games/C.gb");
    s.play("gb:/games/B.gb"); finish(s);
    assert(s.takeLaunch()=="gb:/games/B.gb");
    assert(s.takeLaunch().empty());
    s.play("gb:/games/C.gb"); assert(s.inserted()=="gb:/games/B.gb");
    s.running(); s.returned(); assert(s.phase()==slot::Phase::Inserted);
    s.play("gb:/games/C.gb"); s.eject(); finish(s);
    assert(s.inserted().empty() && s.takeLaunch().empty());
    s.insert("gb:/games/A.gb"); s.play("gb:/games/B.gb"); finish(s);
    assert(s.inserted()=="gb:/games/B.gb" && s.takeLaunch()=="gb:/games/B.gb");
    s.returned(); s.invalidate("gb:/games/B.gb"); assert(s.inserted().empty());
    s.insert("gb:/games/A.gb"); s.update(-100); assert(s.progress()==0);
    s.update(100); assert(s.busy()); // Sleep/resume does not skip all mechanics.
    s.reset();
    for (int n=0;n<50;++n) {
        s.insert("A"); finish(s); assert(s.inserted()=="A" && s.takeLaunch().empty());
        s.play("B"); finish(s); assert(s.takeLaunch()=="B" && s.takeLaunch().empty());
        s.returned(); s.eject(); finish(s); assert(s.inserted().empty());
    }
    std::cout << "Slot state: independent insertion, swaps, bounded commands, cancellation, invalidation and 50 launch/eject cycles passed.\n";
}
