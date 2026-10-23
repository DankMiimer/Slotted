/* Phase 0 host-only stand-in for libfreeimage.so.3 (no x86_64 FreeImage runtime is on this PC).
 * Decodes through SDL2_image and keeps FreeImage's conventions that ImageIO relies on:
 * 32 bpp, little-endian BGRA (0xAARRGGBB words) and bottom-up scanlines. Never shipped. */
#include <FreeImage.h>
#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

extern SDL_Surface *IMG_Load_RW(SDL_RWops *src, int freesrc);

typedef struct { int w, h; unsigned char *px; } Bitmap; /* top-down rows of w*4 bytes */
typedef struct { const BYTE *data; DWORD size; } Memory;

static FIBITMAP *wrap(int w, int h) {
    FIBITMAP *dib = malloc(sizeof *dib); Bitmap *b = malloc(sizeof *b);
    b->w = w; b->h = h; b->px = calloc((size_t)w * h, 4); dib->data = b; return dib;
}
static Bitmap *bm(FIBITMAP *dib) { return dib ? (Bitmap *)dib->data : NULL; }

static FREE_IMAGE_FORMAT sniff(const BYTE *d, size_t n) {
    if (n >= 8 && !memcmp(d, "\x89PNG", 4)) return FIF_PNG;
    if (n >= 3 && d[0] == 0xFF && d[1] == 0xD8) return FIF_JPEG;
    if (n >= 6 && !memcmp(d, "GIF8", 4)) return FIF_GIF;
    if (n >= 2 && !memcmp(d, "BM", 2)) return FIF_BMP;
    if (n >= 12 && !memcmp(d, "RIFF", 4) && !memcmp(d + 8, "WEBP", 4)) return FIF_WEBP;
    return FIF_UNKNOWN;
}

static FIBITMAP *decode(SDL_RWops *rw) {
    if (!rw) return NULL;
    SDL_Surface *raw = IMG_Load_RW(rw, 1); if (!raw) return NULL;
    SDL_Surface *s = SDL_ConvertSurfaceFormat(raw, SDL_PIXELFORMAT_ARGB8888, 0); SDL_FreeSurface(raw);
    if (!s) return NULL;
    FIBITMAP *dib = wrap(s->w, s->h); Bitmap *b = bm(dib);
    for (int y = 0; y < s->h; y++) memcpy(b->px + (size_t)y * s->w * 4, (unsigned char *)s->pixels + (size_t)y * s->pitch, (size_t)s->w * 4);
    SDL_FreeSurface(s); return dib;
}

void DLL_CALLCONV FreeImage_Initialise(BOOL load_local_plugins_only) { (void)load_local_plugins_only; }
void DLL_CALLCONV FreeImage_DeInitialise(void) {}

FIMEMORY *DLL_CALLCONV FreeImage_OpenMemory(BYTE *data, DWORD size) {
    FIMEMORY *m = malloc(sizeof *m); Memory *mm = malloc(sizeof *mm); mm->data = data; mm->size = size; m->data = mm; return m;
}
void DLL_CALLCONV FreeImage_CloseMemory(FIMEMORY *stream) { if (stream) { free(stream->data); free(stream); } }
FREE_IMAGE_FORMAT DLL_CALLCONV FreeImage_GetFileTypeFromMemory(FIMEMORY *stream, int size) {
    (void)size; Memory *m = stream ? stream->data : NULL; return m ? sniff(m->data, m->size) : FIF_UNKNOWN;
}
BOOL DLL_CALLCONV FreeImage_FIFSupportsReading(FREE_IMAGE_FORMAT fif) { return fif != FIF_UNKNOWN; }
FIBITMAP *DLL_CALLCONV FreeImage_LoadFromMemory(FREE_IMAGE_FORMAT fif, FIMEMORY *stream, int flags) {
    (void)fif; (void)flags; Memory *m = stream ? stream->data : NULL; return m ? decode(SDL_RWFromConstMem(m->data, (int)m->size)) : NULL;
}
FIMULTIBITMAP *DLL_CALLCONV FreeImage_LoadMultiBitmapFromMemory(FREE_IMAGE_FORMAT fif, FIMEMORY *stream, int flags) { (void)fif; (void)stream; (void)flags; return NULL; }
FIBITMAP *DLL_CALLCONV FreeImage_LockPage(FIMULTIBITMAP *bitmap, int page) { (void)bitmap; (void)page; return NULL; }
void DLL_CALLCONV FreeImage_UnlockPage(FIMULTIBITMAP *bitmap, FIBITMAP *data, BOOL changed) { (void)bitmap; (void)data; (void)changed; }
BOOL DLL_CALLCONV FreeImage_CloseMultiBitmap(FIMULTIBITMAP *bitmap, int flags) { (void)bitmap; (void)flags; return TRUE; }
int DLL_CALLCONV FreeImage_GetPageCount(FIMULTIBITMAP *bitmap) { (void)bitmap; return 0; }

unsigned DLL_CALLCONV FreeImage_GetBPP(FIBITMAP *dib) { return dib ? 32 : 0; }
unsigned DLL_CALLCONV FreeImage_GetWidth(FIBITMAP *dib) { return dib ? (unsigned)bm(dib)->w : 0; }
unsigned DLL_CALLCONV FreeImage_GetHeight(FIBITMAP *dib) { return dib ? (unsigned)bm(dib)->h : 0; }
BYTE *DLL_CALLCONV FreeImage_GetScanLine(FIBITMAP *dib, int scanline) {
    Bitmap *b = bm(dib); if (!b || scanline < 0 || scanline >= b->h) return NULL;
    return b->px + (size_t)(b->h - 1 - scanline) * b->w * 4; /* FreeImage scanline 0 is the bottom row */
}
void DLL_CALLCONV FreeImage_Unload(FIBITMAP *dib) { if (dib) { free(bm(dib)->px); free(dib->data); free(dib); } }
FIBITMAP *DLL_CALLCONV FreeImage_ConvertTo32Bits(FIBITMAP *dib) {
    Bitmap *b = bm(dib); if (!b) return NULL; FIBITMAP *c = wrap(b->w, b->h); memcpy(bm(c)->px, b->px, (size_t)b->w * b->h * 4); return c;
}
/* Area average (FILTER_BOX-like); only used for oversized pictures. */
FIBITMAP *DLL_CALLCONV FreeImage_Rescale(FIBITMAP *dib, int w, int h, FREE_IMAGE_FILTER filter) {
    (void)filter; Bitmap *s = bm(dib); if (!s || w <= 0 || h <= 0) return NULL;
    FIBITMAP *out = wrap(w, h); Bitmap *d = bm(out);
    for (int y = 0; y < h; y++) {
        int y0 = (int)((long long)y * s->h / h), y1 = (int)((long long)(y + 1) * s->h / h); if (y1 <= y0) y1 = y0 + 1;
        for (int x = 0; x < w; x++) {
            int x0 = (int)((long long)x * s->w / w), x1 = (int)((long long)(x + 1) * s->w / w); if (x1 <= x0) x1 = x0 + 1;
            unsigned long sum[4] = {0, 0, 0, 0}, n = 0;
            for (int yy = y0; yy < y1 && yy < s->h; yy++) for (int xx = x0; xx < x1 && xx < s->w; xx++) {
                const unsigned char *p = s->px + ((size_t)yy * s->w + xx) * 4; for (int k = 0; k < 4; k++) sum[k] += p[k]; n++;
            }
            unsigned char *q = d->px + ((size_t)y * w + x) * 4; for (int k = 0; k < 4; k++) q[k] = (unsigned char)(n ? (sum[k] + n / 2) / n : 0);
        }
    }
    return out;
}

static FREE_IMAGE_FORMAT fileType(const char *path) {
    BYTE head[16]; FILE *f = fopen(path, "rb"); if (!f) return FIF_UNKNOWN;
    size_t n = fread(head, 1, sizeof head, f); fclose(f); return sniff(head, n);
}
FREE_IMAGE_FORMAT DLL_CALLCONV FreeImage_GetFileType(const char *filename, int size) { (void)size; return fileType(filename); }
FREE_IMAGE_FORMAT DLL_CALLCONV FreeImage_GetFIFFromFilename(const char *filename) {
    const char *dot = filename ? strrchr(filename, '.') : NULL; if (!dot) return FIF_UNKNOWN;
    if (!SDL_strcasecmp(dot, ".png")) return FIF_PNG;
    if (!SDL_strcasecmp(dot, ".jpg") || !SDL_strcasecmp(dot, ".jpeg")) return FIF_JPEG;
    if (!SDL_strcasecmp(dot, ".gif")) return FIF_GIF;
    if (!SDL_strcasecmp(dot, ".bmp")) return FIF_BMP;
    if (!SDL_strcasecmp(dot, ".webp")) return FIF_WEBP;
    return FIF_UNKNOWN;
}
FIBITMAP *DLL_CALLCONV FreeImage_Load(FREE_IMAGE_FORMAT fif, const char *filename, int flags) { (void)fif; (void)flags; return decode(SDL_RWFromFile(filename, "rb")); }
BOOL DLL_CALLCONV FreeImage_Save(FREE_IMAGE_FORMAT fif, FIBITMAP *dib, const char *filename, int flags) { (void)fif; (void)dib; (void)filename; (void)flags; return FALSE; }

static char *narrow(const wchar_t *w) { size_t n = wcstombs(NULL, w, 0); if (n == (size_t)-1) return NULL; char *s = malloc(n + 1); wcstombs(s, w, n + 1); return s; }
FREE_IMAGE_FORMAT DLL_CALLCONV FreeImage_GetFileTypeU(const wchar_t *filename, int size) { char *s = narrow(filename); FREE_IMAGE_FORMAT f = s ? FreeImage_GetFileType(s, size) : FIF_UNKNOWN; free(s); return f; }
FREE_IMAGE_FORMAT DLL_CALLCONV FreeImage_GetFIFFromFilenameU(const wchar_t *filename) { char *s = narrow(filename); FREE_IMAGE_FORMAT f = s ? FreeImage_GetFIFFromFilename(s) : FIF_UNKNOWN; free(s); return f; }
FIBITMAP *DLL_CALLCONV FreeImage_LoadU(FREE_IMAGE_FORMAT fif, const wchar_t *filename, int flags) { char *s = narrow(filename); FIBITMAP *b = s ? FreeImage_Load(fif, s, flags) : NULL; free(s); return b; }
BOOL DLL_CALLCONV FreeImage_SaveU(FREE_IMAGE_FORMAT fif, FIBITMAP *dib, const wchar_t *filename, int flags) { (void)fif; (void)dib; (void)filename; (void)flags; return FALSE; }

BOOL DLL_CALLCONV FreeImage_GetMetadata(FREE_IMAGE_MDMODEL model, FIBITMAP *dib, const char *key, FITAG **tag) { (void)model; (void)dib; (void)key; if (tag) *tag = NULL; return FALSE; }
DWORD DLL_CALLCONV FreeImage_GetTagCount(FITAG *tag) { (void)tag; return 0; }
const void *DLL_CALLCONV FreeImage_GetTagValue(FITAG *tag) { (void)tag; return NULL; }
