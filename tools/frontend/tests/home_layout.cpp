// Check the production layout with current native-rendered silhouettes and floor anchors.
#include "../overlay/es-app/src/components/SlotHomeLayout.h"
#include "../overlay/es-app/src/components/SlotTelevision.h"
#include <cassert>
#include <cmath>
#include <iostream>
#include <string>
int main() {
    std::string model;float b[4],p[2];unsigned count=0;
    while(std::cin>>model>>b[0]>>b[1]>>b[2]>>b[3]>>p[0]>>p[1]) {
        for(const auto& tv:slotTelevisions) {
            auto l=slotHomeLayout(model.c_str(),b,p,tv.display,tv.contact,tv.units_per_mm);
            const float front=l.rect[1]+p[1]*l.scale,tvFront=l.tv[1]+tv.contact[1];
            assert(std::abs(front-tvFront)<.001f);
            assert(l.rect[0]+b[0]*l.scale>=12);
            assert(l.rect[0]+(b[0]+b[2])*l.scale<=l.tv[0]-16);
            assert(l.rect[1]+b[1]*l.scale>=123.99f);
            assert(l.rect[1]+(b[1]+b[3])*l.scale<=478.01f);
            assert(l.tv[1]>=123.99f && l.tv[1]+tv.display[1]<=478.01f);
            // These nine registered models fit without sacrificing their physical size ratio.
            assert(std::abs(l.scale*slotHomeUnitsPerMM(model.c_str())-tv.units_per_mm)<.001f);
            ++count;
        }
    }
    assert(count==27);
    std::cout<<count<<" layouts: front edges aligned, physical scales retained, all silhouettes inside scene\n";
}
