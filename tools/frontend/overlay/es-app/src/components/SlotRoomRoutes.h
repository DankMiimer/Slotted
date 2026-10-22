// Collection selection routes to physical media before ordinary launch (MIT).
#pragma once
#include <string>
class SystemData;class FileData;
namespace slot {
bool roomCollection(SystemData*collection,FileData*game);
bool roomOpenGame(SystemData*origin,FileData*game);
bool roomReturn(const std::string&system);
// Explicit remote launch requests retain their execution semantics. GUI browsing
// still routes modelled games into physical layouts before insertion/launch.
bool roomDirectLaunch();
struct RoomDirectLaunch {RoomDirectLaunch();~RoomDirectLaunch();};

}
