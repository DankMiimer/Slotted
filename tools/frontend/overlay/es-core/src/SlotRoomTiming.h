// Diagnostic stages for the room frame log; inert unless SLOT_SCENE_ROOMLOG is set (MIT).
#pragma once
struct SlotRoomStage {
    enum Kind{Input,Update,Home,Count};
    explicit SlotRoomStage(Kind kind);
    ~SlotRoomStage();
    SlotRoomStage(const SlotRoomStage&)=delete;
    SlotRoomStage&operator=(const SlotRoomStage&)=delete;
private:
    Kind kind;unsigned long long started;
};
// Logs a labelled section taking 10 ms or more to "<SLOT_SCENE_ROOMLOG>.probes.tsv".
struct SlotRoomProbe {
    explicit SlotRoomProbe(const char*label);
    ~SlotRoomProbe();
    SlotRoomProbe(const SlotRoomProbe&)=delete;
    SlotRoomProbe&operator=(const SlotRoomProbe&)=delete;
private:
    const char*label;unsigned long long started;
};
