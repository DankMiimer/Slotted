#include "SlotMetadataPages.h"
#include <cassert>
#include <cstdio>
int main(){
    slot_scene::SceneDisplay tv,lcd;tv.fields=255&~(1u<<2)&~(1u<<6);lcd.fields=255&~(1u<<4)&~(1u<<7);
    assert(slotMetadataPageVisible("Overview",true,tv));assert(!slotMetadataPageVisible("Box art",false,tv));assert(!slotMetadataPageVisible("Video",false,tv));
    assert(slotMetadataPageVisible("Game details",false,tv)&&slotMetadataPageVisible("Your library",false,tv));
    assert(!slotMetadataPageVisible("Game details",false,lcd)&&slotMetadataPageVisible("Screenshot",false,lcd));
    lcd.layout=1;assert(!slotMetadataPageVisible("Box art",false,lcd)&&!slotMetadataPageVisible("Video",false,lcd));
    tv.layout=2;assert(!slotMetadataPageVisible("Game details",false,tv)&&!slotMetadataPageVisible("Your library",false,tv));
    int cycle=slotMetadataPageCycle(3,5);assert(cycle==15);
    for(int start=0;start<cycle;start++){int next=(start+1)%cycle,previous=(next-1+cycle)%cycle;assert(previous%3==start%3&&previous%5==start%5);}
    assert(slotMetadataPageCycle(0,4)==4&&slotMetadataPageCycle(0,0)==1);
    std::puts("independent display page filtering/cycles passed");
}
