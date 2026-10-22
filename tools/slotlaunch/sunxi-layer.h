/* Minimal userspace bindings for the Sunxi disp2 DMA-buffer layer ABI (ARM64).
 * Protocol layout: Allwinner's public include/video/sunxi_display2.h.
 * Our implementation uses an unused layer; it never changes the primary layer.
 * Copyright (c) 2026, MIT. */
#ifndef SLOT_SUNXI_LAYER_H
#define SLOT_SUNXI_LAYER_H
#include <stdint.h>
#include <stddef.h>

typedef struct { uint32_t width, height; } SlotSize;
typedef struct { int32_t x, y; uint32_t width, height; } SlotWindow;
typedef struct { int64_t x, y, width, height; } SlotCrop;
typedef struct {
    int32_t fd;
    SlotSize size[3];
    uint32_t alignment[3], format, colour_space;
    int32_t right_fd;
    uint8_t premultiplied;
    SlotCrop crop;
    uint32_t flags, scan, eotf;
    int32_t depth;
    uint32_t compressed;
    int32_t metadata_fd;
    uint32_t metadata_size, metadata_flags;
} SlotBuffer;
typedef struct {
    uint8_t enabled;
    uint32_t mode, rows, columns;
    int32_t fd;
} SlotWarp;
typedef struct {
    uint8_t enabled, demo;
    SlotWindow window;
    uint8_t strength[3], threshold[2];
} SlotNoise;
typedef struct {
    uint32_t mode;
    uint8_t order, alpha_mode, alpha;
    SlotWindow window;
    uint8_t stereo;
    uint32_t stereo_mode;
    SlotBuffer buffer;
    uint32_t frame_id;
    SlotWarp warp;
    uint32_t transform;
    SlotNoise noise;
} SlotPlane;
typedef struct {
    SlotPlane plane;
    uint8_t enabled;
    uint32_t channel, layer;
} SlotLayer;
_Static_assert(sizeof(SlotLayer) == 224, "Sunxi layer ABI requires ARM64 alignment");

enum { SLOT_LAYER_SET = 0x49, SLOT_LAYER_GET = 0x4a };
typedef struct {
    size_t length, alignment;
    uint32_t heap_mask, flags;
    int32_t handle;
} SlotAllocation;
typedef struct { int32_t handle, fd; } SlotSharedBuffer;
#endif
