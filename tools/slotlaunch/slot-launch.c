/* Art Book Slot launch animation. Copyright (c) 2026, MIT.
 * Native rendering uses SDL2/SDL2_image supplied by Knulli.
 */
#define _POSIX_C_SOURCE 200809L
#include <SDL.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <linux/input.h>
#include <math.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include "sunxi-layer.h"

/* SDL2_image's public loader ABI; its development header is not needed. */
extern SDL_Surface *IMG_Load(const char *path);

enum { WIDTH = 720, HEIGHT = 480, BAND_Y = 422, PATH_CAP = 4096 };
typedef struct {
    const char *system, *shell, *back, *front;
    int width, height, foot;
    bool front_loading;
} Media;
static const Media media[] = {
    {"gba", "shells/gba.png", "band-back.png", "band-front.png", 360, 212, 346, false},
    {"gb", "shells/gb.png", "band-back.png", "band-front.png", 312, 337, 380, false},
    {"gbc", "shells/gbc.png", "band-back.png", "band-front.png", 312, 337, 380, false},
    {"snes", "shells/snes.png", "band-snes-back.png", "band-snes-front.png", 360, 245, 334, false},
    {"nes", "shells/nes.png", "band-nes-back.png", "band-nes-front.png", 304, 337, 380, true},
    {"n64", "shells/n64.png", "band-n64-back.png", "band-n64-front.png", 360, 241, 332, false},
    {"megadrive", "shells/md.png", "band-md-back.png", "band-md-front.png", 360, 270, 346, false},
    {"genesis", "shells/md.png", "band-md-back.png", "band-md-front.png", 360, 270, 346, false},
    {"psx", "shells/psx.png", "band-psx.png", "band-psx.png", 336, 336, 379, false},
    {"dreamcast", "shells/dreamcast.png", "band-console-dreamcast.png", "band-console-dreamcast.png", 336, 336, 379, false},
    {"psp", "shells/psp.png", "band-psp.png", "band-psp.png", 336, 336, 379, false},
    {"nds", "shells/nds.png", "band-console-nds.png", "band-console-nds.png", 312, 341, 382, false},
    {"pico8", "shells/pico8.png", "band-console-pico8.png", "band-console-pico8.png", 264, 338, 380, false},
};
static const char *state_dir = "/tmp/art-book-slot-launch";
static double process_start;
static int return_signal = -1;
static pid_t configgen_pid;
static bool overlapping_return;
static int scene_fd = -1;
static struct timespec process_wall;

static double now(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

static void log_event(const char *message)
{
    char path[PATH_CAP];
    snprintf(path, sizeof(path), "%s/animation.log", state_dir);
    FILE *file = fopen(path, "a");
    if (file) {
        fprintf(file, "%.6f +%.4f %s\n", now(), now() - process_start, message);
        fclose(file);
    }
}

/* An overlapped eject keeps its display layers while the frontend recovers.
 * The kernel drops this lock when the process exits, including on a crash. */
static int scene_lock(bool wait)
{
    int fd = open("/tmp/art-book-slot-launch/scene.lock", O_RDWR | O_CREAT | O_CLOEXEC, 0600);
    if (fd < 0) return -1;
    double started = now();
    while (flock(fd, LOCK_EX | LOCK_NB)) {
        if (!wait || errno != EWOULDBLOCK || now() - started > 1.5) {
            log_event("scene lock unavailable");
            close(fd);
            return -1;
        }
        SDL_Delay(10);
    }
    if (now() - started > .02) {
        char message[64];
        snprintf(message, sizeof(message), "waited %.0f ms for previous scene", (now()-started)*1000);
        log_event(message);
    }
    return fd;
}

/* configgen runs the gameStop hook through a shell, so it is our grandparent.
 * ES resumes only after it exits. Returns 0 when that chain is unavailable. */
static pid_t hook_grandparent(void)
{
    char path[64], line[512];
    snprintf(path, sizeof(path), "/proc/%d/stat", (int)getppid());
    FILE *file = fopen(path, "r");
    if (!file) return 0;
    bool read_line = fgets(line, sizeof(line), file) != NULL;
    fclose(file);
    char *name_end = read_line ? strrchr(line, ')') : NULL;
    char state;
    int parent;
    if (!name_end || sscanf(name_end + 1, " %c %d", &state, &parent) != 2) return 0;
    /* Manual runs have no configgen to wait for. */
    snprintf(path, sizeof(path), "/proc/%d/comm", parent);
    file = fopen(path, "r");
    if (!file) return 0;
    read_line = fgets(line, sizeof(line), file) != NULL;
    fclose(file);
    if (!read_line || (strncmp(line, "python", 6) && strncmp(line, "emulatorlaunch", 14))) return 0;
    return parent;
}

/* Fork before SDL/Mali starts any threads. Release configgen only after our
 * private display layer has presented a frame. Unsupported layers stay sync. */
static bool detach_return(void)
{
    int ready[2];
    if (pipe(ready)) return false;
    pid_t child = fork();
    if (child < 0) { close(ready[0]); close(ready[1]); return false; }
    if (child == 0) {
        close(ready[0]);
        return_signal = ready[1];
        overlapping_return = true;
        struct sigaction ignore = {.sa_handler = SIG_IGN};
        sigemptyset(&ignore.sa_mask);
        sigaction(SIGPIPE, &ignore, NULL);
        if (setsid() < 0) _exit(1);
        DIR *fds = opendir("/proc/self/fd");
        if (!fds) _exit(1);
        int inventory = dirfd(fds);
        struct dirent *entry;
        while ((entry = readdir(fds)) != NULL) {
            char *end;
            long fd = strtol(entry->d_name, &end, 10);
            if (!*end && fd >= 0 && fd != inventory && fd != return_signal) close((int)fd);
        }
        closedir(fds);
        int null = open("/dev/null", O_RDWR);
        if (null >= 0) {
            dup2(null, 0); dup2(null, 1); dup2(null, 2);
            if (null > 2) close(null);
        }
        return false;
    }
    close(ready[1]);
    struct pollfd signal = {ready[0], POLLIN | POLLHUP, 0};
    char isolated = 0;
    int available;
    do { available = poll(&signal, 1, 3000); } while (available < 0 && errno == EINTR);
    bool presented = available > 0 && read(ready[0], &isolated, 1) == 1 && isolated == '1';
    if (presented) log_event("return: private frame latched; configgen released");
    else {
        log_event("return: synchronous fallback");
        while (waitpid(child, NULL, 0) < 0 && errno == EINTR) { }
    }
    close(ready[0]);
    return true;
}

static void signal_return(bool isolated)
{
    if (return_signal < 0) return;
    char value = isolated ? '1' : '0';
    ssize_t sent = write(return_signal, &value, 1);
    if (sent != 1) log_event("return: readiness pipe unavailable");
    close(return_signal);
    return_signal = -1;
}

static double clamp(double x) { return fmin(1.0, fmax(0.0, x)); }
static double smootherstep(double x) { return x*x*x * (x * (x*6 - 15) + 10); }
/* A released spring: quick start (80% by p = .2), about 4% overshoot near
 * p = .63, settled by p = 1. */
static double spring(double p) { p = clamp(p); return 1 - exp(-5*p)*cos(5*p); }
#include "appearance.h"
#include "psx.h"
#include "cartridge-console.h"
#include "psp.h"
#include "ps1-scene.h"

static double travel(double seat, double catch)
{
    if (seat < .42) return catch * smootherstep(seat / .42);
    if (seat < .62) return catch + .03 * (seat - .42) / .20;
    double caught = catch + .03;
    return caught + (1 - caught) * smootherstep((seat - .62) / .38);
}

static SDL_Surface *capture_framebuffer(void)
{
    int fd = open("/dev/fb0", O_RDONLY);
    struct fb_var_screeninfo var;
    struct fb_fix_screeninfo fix;
    if (fd < 0) return NULL;
    SDL_Surface *surface = NULL;
    if (ioctl(fd, FBIOGET_VSCREENINFO, &var) || ioctl(fd, FBIOGET_FSCREENINFO, &fix)) goto done;
    if (var.xres != WIDTH || var.yres != HEIGHT || var.bits_per_pixel != 32) goto done;
    Uint32 red = ((1u << var.red.length) - 1) << var.red.offset;
    Uint32 green = ((1u << var.green.length) - 1) << var.green.offset;
    Uint32 blue = ((1u << var.blue.length) - 1) << var.blue.offset;
    surface = SDL_CreateRGBSurface(0, WIDTH, HEIGHT, 32, red, green, blue, 0);
    if (!surface) goto done;
    for (int y = 0; y < HEIGHT; y++) {
        off_t offset = (off_t)(y + var.yoffset) * fix.line_length + var.xoffset * 4;
        if (pread(fd, (char *)surface->pixels + y * surface->pitch, WIDTH * 4, offset) != WIDTH * 4) {
            SDL_FreeSurface(surface);
            surface = NULL;
            break;
        }
    }
done:
    close(fd);
    return surface;
}

static int layer_command(int fd, unsigned command, SlotLayer *layer)
{
    unsigned long args[4] = {0, (unsigned long)layer, 1, 0};
    return ioctl(fd, command, args);
}
#include "animation-layer.h"

/* An independent display layer covers the primary framebuffer's clears. Keep its
 * pixels in a private uncached DMA allocation, outside the framebuffer entirely.
 * ES presenting again plus a stable primary shelf, a press, or a relaunch marks
 * the safe release. */
static void hold_handover(SDL_Surface *frame, const Media *shape)
{
    if (!frame || frame->format->BytesPerPixel != 4) return;
    int fb = open("/dev/fb0", O_RDONLY), display = open("/dev/disp", O_RDWR);
    int ion = -1, shared = -1;
    struct fb_var_screeninfo var;
    struct fb_fix_screeninfo fix;
    SlotLayer original = {0}, primary = {0};
    void *pixels = MAP_FAILED;
    size_t length = (size_t)frame->pitch * HEIGHT;
    bool enabled = false, in_child = false;
    if (fb < 0 || display < 0 || ioctl(fb, FBIOGET_VSCREENINFO, &var)
        || ioctl(fb, FBIOGET_FSCREENINFO, &fix)) goto unavailable;
    if (var.xres != WIDTH || var.yres != HEIGHT || var.bits_per_pixel != 32
        || var.red.offset != 16 || var.green.offset != 8 || var.blue.offset != 0
        || fix.line_length != (unsigned)frame->pitch) goto unavailable;
    primary.channel = 1;
    if (layer_command(display, SLOT_LAYER_GET, &primary) || !primary.enabled
        || primary.plane.window.width != WIDTH || primary.plane.window.height != HEIGHT) goto unavailable;
    original.channel = 3;
    if (layer_command(display, SLOT_LAYER_GET, &original) || original.enabled) goto unavailable;
    /* An unconfigured slot is returned as a zeroed record, including its key. */
    original.channel = 3;
    original.layer = 0;
    ion = open("/dev/ion", O_RDWR);
    if (ion < 0) goto unavailable;
    SlotAllocation allocation = {length, 4096, 1u<<0, 0, 0}; /* IOMMU system heap, uncached. */
    if (ioctl(ion, _IOWR('I', 0, SlotAllocation), &allocation)) goto unavailable;
    SlotSharedBuffer buffer = {allocation.handle, -1};
    if (ioctl(ion, _IOWR('I', 4, SlotSharedBuffer), &buffer)) goto unavailable;
    shared = buffer.fd;
    pixels = mmap(NULL, length, PROT_READ|PROT_WRITE, MAP_SHARED, shared, 0);
    if (pixels == MAP_FAILED) goto unavailable;
    memcpy(pixels, frame->pixels, length);
    SlotLayer overlay = original;
    overlay.enabled = 1;
    overlay.plane = primary.plane;
    overlay.plane.order = 15;
    overlay.plane.alpha_mode = 1;
    overlay.plane.alpha = 255;
    overlay.plane.buffer.format = 4; /* XRGB8888; global alpha makes the whole shelf opaque. */
    overlay.plane.buffer.fd = shared;
    overlay.plane.buffer.size[0] = (SlotSize){WIDTH, HEIGHT};
    overlay.plane.buffer.crop = (SlotCrop){0, 0, (int64_t)WIDTH<<32, (int64_t)HEIGHT<<32};
    if (layer_command(display, SLOT_LAYER_SET, &overlay)) goto unavailable;
    enabled = true;
    /* Let the compositor latch this layer before SDL releases the primary. */
    struct timespec latch = {0, 20000000};
    nanosleep(&latch, NULL);
    pid_t child = fork();
    if (child < 0) goto unavailable;
    if (child > 0) {
        close(fb);
        close(display);
        munmap(pixels, length);
        close(shared);
        close(ion);
        return;
    }
    in_child = true;
    if (setsid() < 0) goto unavailable;
    /* Inherited configgen output pipes would keep ES waiting for EOF. Inherited
     * Mali descriptors would retain the outgoing display. Keep only our RAM copy. */
    DIR *fds = opendir("/proc/self/fd");
    if (fds) {
        struct dirent *entry;
        int inventory = dirfd(fds);
        while ((entry = readdir(fds)) != NULL) {
            char *end;
            long fd = strtol(entry->d_name, &end, 10);
            /* The scene lock stays held until the shelf holder lets go. */
            if (!*end && fd >= 0 && fd != inventory && fd != fb && fd != display
                && fd != ion && fd != shared && fd != scene_fd) close((int)fd);
        }
        closedir(fds);
    } else {
        goto unavailable;
    }
    log_event("handover: independent layer active");
    /* Controller presses are observed, never consumed: ES still receives them. */
    int inputs[8], input_count = 0;
    for (int i = 0; i < 16 && input_count < 8; i++) {
        char device[32];
        snprintf(device, sizeof(device), "/dev/input/event%d", i);
        int input = open(device, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (input >= 0) inputs[input_count++] = input;
    }
    double started = now(), ready_since = 0, input_at = 0;
    const double points[][2] = {{.30,.08},{.70,.08},{.10,.20},{.90,.20},
                                {.08,.45},{.92,.45},{.20,.95},{.80,.95}};
    /* Full-disc/UMD previews animate the formerly static face samples. Match
     * surrounding shelf and console chrome instead; keep clock/status out. */
    const int optical_points[][2]={{48,240},{672,240},{48,280},{672,280},
                                  {24,430},{696,430},{340,400},{380,400}};
    bool optical = !strcmp(shape->system,"psx") || !strcmp(shape->system,"dreamcast") || !strcmp(shape->system,"psp");
    const double card_points[][2]={{.35,.04},{.65,.04},{.025,.20},{.975,.20},
                                  {.025,.60},{.975,.60},{.22,.955},{.78,.955}};
    const double pico_points[][2]={{.30,.08},{.70,.08},{.04,.20},{.96,.20},
                                  {.04,.60},{.96,.60},{.30,.98},{.70,.98}};
    const double (*samples)[2]=!strcmp(shape->system,"nds")?card_points:
        !strcmp(shape->system,"pico8")?pico_points:points;
    /* ES resumes once configgen has exited; its page flips then show that it
     * is presenting frames again. Selection hooks are avoided: ES forks for
     * every script on every cursor move, which drops frames while browsing. */
    bool returned = false;
    int drawn_polls = 0, flips = 0;
    __u32 last_offset = 0;
    /* ES writes its launch description before every game. A relaunch during
     * the eject or hold must not wait for a shelf that will never be drawn. */
    struct timespec held_at = process_wall;
    const int band_y = optical ? 211 : shape->foot - shape->height/2;
    const char *wallpaper_option = getenv("SLOT_WALLPAPER");
    bool black_shelf = !(wallpaper_option && !strcmp(wallpaper_option, "on"));
    while (now() - started < 5) {
        int fd = open("/dev/fb0", O_RDONLY);
        struct fb_fix_screeninfo current;
        if (fd < 0) break;
        if (ioctl(fd, FBIOGET_VSCREENINFO, &var) || ioctl(fd, FBIOGET_FSCREENINFO, &current)
            || var.xres != WIDTH || var.yres != HEIGHT || var.bits_per_pixel != 32
            || current.smem_start != fix.smem_start || current.line_length != fix.line_length) {
            close(fd);
            break;
        }
        off_t base = (off_t)var.yoffset * fix.line_length + var.xoffset * 4;
        int matches = 0;
        for (size_t i = 0; i < sizeof(points)/sizeof(points[0]); i++) {
            int x = optical ? optical_points[i][0]
                : (WIDTH-shape->width)/2 + (int)lround(shape->width*samples[i][0]);
            int y = optical ? optical_points[i][1]
                : shape->foot-shape->height + (int)lround(shape->height*samples[i][1]);
            Uint32 expected = *(Uint32 *)((char *)frame->pixels+y*frame->pitch+x*4), actual = 0;
            if (pread(fd, &actual, 4, base+y*fix.line_length+x*4) != 4) continue;
            bool match = true;
            for (int shift = 0; shift < 24; shift += 8)
                if (abs((int)((expected>>shift)&255)-(int)((actual>>shift)&255)) > 4) match = false;
            if (match) matches++;
        }
        /* After a return ES reloads cart textures asynchronously; an empty
         * black shelf must stay hidden. Carts cover most of this row. */
        int covered = 0;
        for (int i = 0; i < 24; i++) {
            Uint32 actual = 0;
            int x = 12 + i*29;
            if (pread(fd, &actual, 4, base+band_y*fix.line_length+x*4) == 4
                && ((actual&255) > 24 || ((actual>>8)&255) > 24 || ((actual>>16)&255) > 24)) covered++;
        }
        drawn_polls = !black_shelf || covered >= 10 ? drawn_polls + 1 : 0;
        close(fd);
        if (!returned && (configgen_pid <= 1 || (kill(configgen_pid, 0) && errno == ESRCH))) {
            returned = true;
            last_offset = var.yoffset;
        } else if (returned && var.yoffset != last_offset) {
            flips++;
            last_offset = var.yoffset;
        }
        bool frontend_presenting = returned && flips > 0;
        for (int i = 0; i < input_count; i++) {
            struct input_event event;
            while (read(inputs[i], &event, sizeof(event)) == (ssize_t)sizeof(event)) {
                bool pressed = (event.type == EV_KEY && event.value == 1)
                    || (event.type == EV_ABS && event.value
                        && (event.code == ABS_HAT0X || event.code == ABS_HAT0Y));
                /* Presses before ES reopens its input are lost to it anyway. */
                if (pressed && frontend_presenting && !input_at) input_at = now();
            }
        }
        struct stat launch;
        if (!stat("/tmp/game.xml", &launch) && (launch.st_mtim.tv_sec > held_at.tv_sec
                || (launch.st_mtim.tv_sec == held_at.tv_sec && launch.st_mtim.tv_nsec > held_at.tv_nsec))) {
            log_event("handover: frontend launched a game");
            break;
        }
        /* Input after ES resumed means the user is browsing. The moved shelf
         * deliberately differs from the saved one; waiting for all old samples
         * would hide navigation until the fallback. Expose the live view once
         * ES has had a frame to respond and its carts are drawn. */
        if (input_at && now() - input_at >= .05 && drawn_polls >= 2) {
            log_event("handover: frontend navigation accepted");
            break;
        }
        if (frontend_presenting && matches == 8) {
            if (!ready_since) ready_since = now();
            if (now()-ready_since >= .12) {
                log_event("handover: frontend shelf ready");
                break;
            }
        } else ready_since = 0;
        struct timespec pause = {0, 10000000};
        nanosleep(&pause, NULL);
    }
    for (int i = 0; i < input_count; i++) close(inputs[i]);
    if (now()-started >= 5) log_event("handover: bounded fallback ended");
    layer_command(display, SLOT_LAYER_SET, &original);
    nanosleep(&latch, NULL);
    munmap(pixels, length);
    close(shared);
    close(ion);
    close(fb);
    close(display);
    _exit(0);
unavailable:
    if (enabled) {
        layer_command(display, SLOT_LAYER_SET, &original);
        struct timespec release = {0, 20000000};
        nanosleep(&release, NULL);
    }
    if (pixels != MAP_FAILED) munmap(pixels, length);
    if (shared >= 0) close(shared);
    if (ion >= 0) close(ion);
    if (fb >= 0) close(fb);
    if (display >= 0) close(display);
    log_event("handover: independent layer unavailable");
    if (in_child) _exit(0);
}

static SDL_Surface *load_surface(const char *assets, const char *relative)
{
    char path[PATH_CAP];
    int length = relative[0] == '/' ? snprintf(path, sizeof(path), "%s", relative)
                                  : snprintf(path, sizeof(path), "%s/%s", assets, relative);
    if (length < 0 || length >= (int)sizeof(path)) return NULL;
    return IMG_Load(path);
}

static SDL_Texture *take_texture(SDL_Renderer *renderer,SDL_Surface **surface)
{
    if(!*surface)return NULL;
    SDL_Texture *texture=SDL_CreateTextureFromSurface(renderer,*surface);
    SDL_FreeSurface(*surface);*surface=NULL;
    return texture;
}

static SDL_Texture *load_texture(SDL_Renderer *renderer, const char *assets, const char *relative)
{
    SDL_Surface *surface = load_surface(assets,relative);
    if (!surface) return NULL;
    return take_texture(renderer,&surface);
}

static SDL_Surface *appearance_surface(const char *assets,const char *relative)
{
    char variant[PATH_CAP];SDL_Surface *surface=NULL;
    if(console_appearance_path(variant,sizeof(variant),relative)){
        size_t n=strlen(variant);
        if(n>4&&!strcmp(variant+n-4,".tga"))memcpy(variant+n-4,".png",5);
        surface=load_surface(assets,variant);
    }
    return surface?surface:load_surface(assets,relative);
}

static void play_sound(const char *assets, const char *mode)
{
    char path[PATH_CAP];
    if (snprintf(path, sizeof(path), "%s/sounds/%s.wav", assets, mode) >= (int)sizeof(path)) return;
    pid_t child = fork();
    if (child == 0) {
        /* The sound player must not retain Mali contexts or private DMA buffers
         * after the animation exits, even if the audio server is restarting. */
        DIR *fds=opendir("/proc/self/fd");
        if(!fds)_exit(0);
        int inventory=dirfd(fds);struct dirent *entry;
        while((entry=readdir(fds))!=NULL){
            char *end;long fd=strtol(entry->d_name,&end,10);
            if(!*end&&fd>=3&&fd!=inventory)close((int)fd);
        }
        closedir(fds);
        int null = open("/dev/null", O_RDWR);
        if (null >= 0) { dup2(null, STDIN_FILENO);dup2(null, STDOUT_FILENO); dup2(null, STDERR_FILENO); close(null); }
        execlp("pw-play", "pw-play", path, (char *)NULL);
        execlp("aplay", "aplay", "-q", path, (char *)NULL);
        _exit(0);
    }
}

static int animate(const char *mode, const char *rom, const char *assets)
{
    bool insert = strcmp(mode, "insert") == 0;
    char snapshot_path[PATH_CAP], baked[PATH_CAP], clean_rom[PATH_CAP];
    snprintf(snapshot_path, sizeof(snapshot_path), "%s/shelf.bmp", state_dir);
    if (strlen(rom) >= sizeof(clean_rom)) return 1;
    strcpy(clean_rom, rom);
    /* ES passes shell-escaped paths on this build. Prefer the literal path if it exists. */
    if (access(clean_rom, R_OK)) {
        char *write = clean_rom;
        for (const char *read = rom; *read; read++) if (*read != '\\') *write++ = *read;
        *write = '\0';
    }
    const char *system = strstr(clean_rom, "/roms/");
    if (!system) return 1;
    system += 6;
    const char *slash = strchr(system, '/');
    if (!slash) return 1;
    size_t syslen = slash - system;
    size_t familylen = syslen - (syslen && system[syslen-1] == 'h' ? 1 : 0);
    const Media *shape = NULL;
    for (size_t i = 0; i < sizeof(media)/sizeof(media[0]); i++) {
        if (strlen(media[i].system) == familylen && !strncmp(system, media[i].system, familylen)) {
            shape = &media[i];
            break;
        }
    }
    if (!shape) return 1;
    bool disc=!strcmp(shape->system,"psx")||!strcmp(shape->system,"dreamcast");
    bool umd=!strcmp(shape->system,"psp");
    const ConsoleSpec *console=console_spec(shape->system,clean_rom);
    bool model=disc||umd||console;
    CartridgeArt cartridge={0};
    AnimationLayer animation={.display=-1,.ion=-1,.shared={-1,-1},.pixels={MAP_FAILED,MAP_FAILED}};
    SDL_Surface *animation_frame=NULL;
    SDL_Texture *scene=NULL;

    /* Capture before SDL initialises the display. Retain the shelf for eject, too. */
    bool preview=getenv("SLOT_PREVIEW")&&!strcmp(getenv("SLOT_PREVIEW"),"1");
    SDL_Surface *snapshot = preview ? NULL : insert ? capture_framebuffer() : SDL_LoadBMP(snapshot_path);
    if (snapshot && insert) SDL_SaveBMP(snapshot, snapshot_path);
    log_event(snapshot ? "shelf captured" : "no shelf capture; black fallback");

    const char *name = strrchr(clean_rom, '/');
    name = name ? name + 1 : clean_rom;
    const char *extension = strrchr(name, '.');
    size_t stemlen = extension ? (size_t)(extension - name) : strlen(name);
    size_t folderlen = (size_t)(name - clean_rom);
    const char *cart_choice=getenv("SLOT_SNES_CARTRIDGE");
    bool tzakol=console&&(!strcmp(console->name,"snes")||!strcmp(console->name,"snes-us"))&&cart_choice&&!strcmp(cart_choice,"tzakol");
    int n = snprintf(baked, sizeof(baked), "%.*smedia/slotcarts/%.*s%s.png", (int)folderlen, clean_rom, (int)stemlen, name,tzakol?".tzakol":"");
    SDL_Surface *prepared[13]={0};
    if(model){
        /* Decode while ES still owns the display. The first native presentation
         * needs only texture uploads, avoiding a black interval during file I/O. */
        prepared[0]=n>0&&n<(int)sizeof(baked)?load_surface(assets,baked):NULL;
        if(!prepared[0])prepared[0]=load_surface(assets,tzakol?"shells/snes-tzakol.png":shape->shell);
        if(console){
            char path[128];snprintf(path,sizeof(path),"band-console-%s.png",console->name);
            prepared[1]=console_style_ready(console->name)?appearance_surface(assets,path):load_surface(assets,path);
            snprintf(path,sizeof(path),"consoles/%s/body.tga",console->name);
            prepared[2]=console_style_ready(console->name)?appearance_surface(assets,path):load_surface(assets,path);
            if(console->kind==4)prepared[3]=load_surface(assets,"shapes/nds/rear.png");
            if(umd||disc){
                char flat[PATH_CAP];
                int size=snprintf(flat,sizeof(flat),"%.*smedia/slotcarts/%.*s.disc.tga",(int)folderlen,clean_rom,(int)stemlen,name);
                prepared[3]=size>0&&size<(int)sizeof(flat)?load_surface(assets,flat):NULL;
                if(!prepared[3]){snprintf(path,sizeof(path),"shells/%s.disc.tga",shape->system);prepared[3]=load_surface(assets,path);}
                snprintf(path,sizeof(path),"shapes/%s/underside.tga",shape->system);prepared[4]=load_surface(assets,path);
            }else cartridge_outline(&cartridge,prepared[0],console->colour);
            if(!console_mesh_load(&cartridge.mesh,assets,console->name))log_event("console mesh unavailable; image fallback");
            if(!strcmp(console->name,"gb"))console_mesh_load_part(&cartridge.media_mesh,assets,"gb","media");
            if(!strcmp(console->name,"gba"))console_mesh_load_part(&cartridge.media_mesh,assets,"gba","media");
            if(!strcmp(console->name,"gbc")&&!cartridge.notched)
                console_mesh_load_part(&cartridge.media_mesh,assets,"gbc","media");
            // GB-compatible (notched) carts in a CGB are the DMG Game Pak, in 3D too.
            if(!strcmp(console->name,"gbc")&&cartridge.notched)
                cartridge.dmg_media=console_mesh_load_part(&cartridge.media_mesh,assets,"gb","media");
            const ExemplarShelf *shelf=exemplar_shelf_for(cartridge.dmg_media?"gb":console->name);
            if(shelf)cartridge_sample_plastic(&cartridge,prepared[0],shelf->sample,shelf->canvas);
            cartridge_media_colour(&cartridge,console->name);
            if(!umd&&!disc)cartridge_media_prepare(&cartridge,assets,console,prepared[0]);
            log_event("cartridge console textures prepared");
        }else{
        prepared[1]=load_surface(assets,shape->back);
        char flat[PATH_CAP];
        int size=snprintf(flat,sizeof(flat),"%.*smedia/slotcarts/%.*s.disc.tga",(int)folderlen,clean_rom,(int)stemlen,name);
        prepared[2]=size>0&&size<(int)sizeof(flat)?load_surface(assets,flat):NULL;
        if(!prepared[2]){
            char path[128];snprintf(path,sizeof(path),"shells/%s.disc.tga",shape->system);
            prepared[2]=load_surface(assets,path);
        }
        const char *files[]={"underside","lid","lid-inside","deck","shadow"};
        for(int i=0;i<5;i++){
            char path[128];snprintf(path,sizeof(path),"shapes/%s/%s.tga",i==4?"psx":shape->system,files[i]);
            prepared[3+i]=load_surface(assets,path);
        }
        log_event("disc textures prepared");
        }
    }

    if (!getenv("SDL_VIDEODRIVER")) setenv("SDL_VIDEODRIVER", "mali", 1);
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER)) goto failed;
    SDL_Window *window = SDL_CreateWindow("Art Book Slot", 0, 0, WIDTH, HEIGHT, SDL_WINDOW_FULLSCREEN);
    if (!window) goto failed;
    SDL_ShowCursor(SDL_DISABLE);
    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "linear");
    SDL_Renderer *renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    if (!renderer) renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_SOFTWARE);
    if (!renderer) goto failed;
    SDL_RenderSetLogicalSize(renderer, WIDTH, HEIGHT);
    SDL_RendererInfo renderer_info={0};
    if (!SDL_GetRendererInfo(renderer, &renderer_info)) log_event(renderer_info.name);
    log_event("display ready");

    SDL_Texture *cart = model?take_texture(renderer,&prepared[0]):n > 0 && n < (int)sizeof(baked) ? load_texture(renderer, assets, baked) : NULL;
    if (!cart) cart = load_texture(renderer, assets, shape->shell);
    SDL_Texture *back = model?take_texture(renderer,&prepared[1]):load_texture(renderer, assets, shape->back);
    SDL_Texture *front = console?NULL:load_texture(renderer, assets, shape->front);
    if (!cart || !back || (!console&&!front)) goto failed;
    PsxArt psx={0};
    if(model){
        if(console){
            cartridge.body=take_texture(renderer,&prepared[2]);
            if(console->kind==4)cartridge.rear=take_texture(renderer,&prepared[3]);
            if(umd||disc){
                psx.disc=take_texture(renderer,&prepared[3]);psx.underside=take_texture(renderer,&prepared[4]);
                if(!psx.disc||!psx.underside)goto failed;
            }
            if(!cartridge.body)goto failed;
            console_mesh_open(&cartridge.mesh,renderer);
            if(cartridge.media_mesh.vertices)console_mesh_open(&cartridge.media_mesh,renderer);
        }else{
        psx.disc=take_texture(renderer,&prepared[2]);psx.underside=take_texture(renderer,&prepared[3]);
        psx.lid=take_texture(renderer,&prepared[4]);psx.inside=take_texture(renderer,&prepared[5]);
        psx.deck=take_texture(renderer,&prepared[6]);psx.shadow=take_texture(renderer,&prepared[7]);
        if(!psx.disc||!psx.underside||!psx.lid||!psx.inside||!psx.deck||!psx.shadow)goto failed;
        }
        scene=SDL_CreateTexture(renderer,SDL_PIXELFORMAT_RGBA8888,SDL_TEXTUREACCESS_TARGET,WIDTH,HEIGHT);
        if(!scene)goto failed;
        SDL_SetTextureBlendMode(scene,SDL_BLENDMODE_NONE);
        if(animation_layer_open(&animation)){
            animation_frame=SDL_CreateRGBSurfaceWithFormat(0,WIDTH,HEIGHT,32,SDL_PIXELFORMAT_RGB888);
            if(!animation_frame)animation_layer_close(&animation);
            else log_event("animation: independent layer ready");
        }
        if(animation.display<0)log_event("animation: primary layer fallback");
    }
    SDL_Texture *wallpaper = NULL;
    if (getenv("SLOT_WALLPAPER") && !strcmp(getenv("SLOT_WALLPAPER"), "on")) {
        char path[PATH_CAP];
        snprintf(path, sizeof(path), "/userdata/theme-customizations/art-book-slot/%.*s.png", (int)syslen, system);
        wallpaper = load_texture(renderer, assets, path);
        if (!wallpaper) wallpaper = load_texture(renderer, assets, "/userdata/theme-customizations/art-book-slot/wallpaper.png");
        if (wallpaper) SDL_SetTextureColorMod(wallpaper, 97, 97, 97); /* 62% black scrim. */
    }

    int cart_width = shape->width, cart_height = shape->height;
    int foot = shape->foot;
    int seated_height = (int)lround(cart_height * 240.0 / cart_width);
    int seated_foot = HEIGHT + seated_height; /* Entire face clears the visible slot. */
    double catch = (double)(BAND_Y - foot) / (seated_foot - foot);
    SDL_Texture *footer = snapshot ? SDL_CreateTextureFromSurface(renderer, snapshot) : NULL;
    if (footer) SDL_SetTextureBlendMode(footer, SDL_BLENDMODE_BLEND);
    /* Retain a CPU copy, independent of Mali's current read buffer. ReadPixels
     * and fb0 can both expose an empty buffer during a display ownership change. */
    /* SDL_LoadBMP returns 24-bit RGB; fb0 needs four bytes per pixel (BGRX). */
    SDL_Surface *handover = !insert && snapshot ? SDL_ConvertSurfaceFormat(snapshot, SDL_PIXELFORMAT_RGB888, 0) : NULL;
    if (handover) {
        SDL_Surface *face = IMG_Load(baked);
        if (!face) {
            char fallback[PATH_CAP];
            if (snprintf(fallback, sizeof(fallback), "%s/%s", assets, shape->shell) < (int)sizeof(fallback))
                face = IMG_Load(fallback);
        }
        if (face) {
            SDL_Rect selected = {(WIDTH-cart_width)/2, foot-cart_height, cart_width, cart_height};
            SDL_BlitScaled(face, NULL, handover, &selected);
            SDL_FreeSurface(face);
        }
    }
    SDL_Texture *background = NULL;
    if (snapshot) {
        SDL_Surface *rgba = SDL_ConvertSurfaceFormat(snapshot, SDL_PIXELFORMAT_RGBA32, 0);
        SDL_FreeSurface(snapshot);
        snapshot = rgba;
    }
    if (snapshot) {
        SDL_Rect erase = {(WIDTH - cart_width) / 2, foot - cart_height, cart_width, cart_height};
        SDL_FillRect(snapshot, &erase, SDL_MapRGBA(snapshot->format, 0, 0, 0, 0));
        if(model){
            SDL_Rect console={0,BAND_Y,WIDTH,HEIGHT-BAND_Y};
            SDL_FillRect(snapshot,&console,SDL_MapRGBA(snapshot->format,0,0,0,0));
        }
        SDL_Rect status_left={0,0,225,42},status_right={520,0,200,42};
        SDL_FillRect(snapshot,&status_left,SDL_MapRGBA(snapshot->format,0,0,0,0));
        SDL_FillRect(snapshot,&status_right,SDL_MapRGBA(snapshot->format,0,0,0,0));
        background = SDL_CreateTextureFromSurface(renderer, snapshot);
        SDL_FreeSurface(snapshot);
        snapshot = NULL;
        if (background) SDL_SetTextureBlendMode(background, SDL_BLENDMODE_BLEND);
    }
    SDL_Rect band = {0, BAND_Y, WIDTH, HEIGHT - BAND_Y};
    double motion_time = shape->front_loading ? .68 : .45;
    double duration = motion_time + (insert ? .28 : .35);
    double sound_at = insert ? motion_time - .097 : 0;
    if(disc){motion_time=insert?.95:.85;duration=motion_time+(insert?.10:.35);sound_at=insert?.75:.03;}
    if(console&&!disc){
        motion_time=console->kind==1||console->kind==4||console->kind==5?(insert?1.85:1.75):console->kind==2?(insert?1.20:1.10):(insert?1.15:1.05);
        duration=motion_time+(insert?.10:.35);sound_at=insert?motion_time*(console->kind==5?.90:console->kind==4?.895:console->kind==1?.87:.73):.03;
    }
    /* Every eject lasts as long as the handheld ones: ES needs about 2.4 s after
     * configgen's release, so input is live as the motion ends. Short scenes gain
     * a physical unseat beat instead of slower motion: carts spring part-way out
     * and hold, the PS1 lid springs open while the disc spins down. The reversed
     * scene then starts where its own motion begins, skipping its old idle start. */
    double unseat = 0, unseat_scene = 1, scene_from = 1, released = 0;
    if (!insert && disc) {
        motion_time = 1.75; unseat = .85; unseat_scene = .67; scene_from = .66;
    } else if (!insert && console && (console->kind == 0 || console->kind == 3)) {
        motion_time = 1.75; unseat = .60; unseat_scene = scene_from = .78;
        /* The SP's rear slot hides a shallow pop; release enough to protrude. */
        released = console->kind == 3 ? .30 : .22;
    } else if (!insert && console && console->kind == 2) {
        motion_time = 1.75; /* NES: its door, tray and slide already form several beats. */
    }
    if (!insert) duration = motion_time + .35;
    bool sound_started = false;
    unsigned frames = 0;
    double start = now(), next_frame = start;
    while (true) {
        double elapsed = now() - start;
        if (!sound_started && elapsed >= sound_at) {
            play_sound(assets, mode);
            sound_started = true;
        }
        double seat = clamp(elapsed / motion_time);
        if (!insert) seat = 1 - seat;
        double lift = 0, lid = -1, eject_spin = 0;
        if (unseat > 0) {
            seat = elapsed < unseat ? unseat_scene
                : scene_from * (1 - clamp((elapsed - unseat) / (motion_time - unseat)));
            if (disc) {
                if (elapsed < unseat) lid = spring((elapsed - .08) / .50);
                /* One full turn decelerating to rest: the label ends where it began. */
                eject_spin = 2 * PSX_PI * (1 - pow(1 - clamp(elapsed / .80), 2));
            } else {
                lift = released * spring((elapsed - .10) / .45);
                if(console&&console->kind==3&&elapsed<unseat)lid=psx_ease((elapsed-.04)/.50);
            }
        }
        if(!insert&&console&&console->kind==4&&elapsed<.60)
            lid=psx_ease((elapsed-.04)/.50);
        if(model){
            if(SDL_SetRenderTarget(renderer,scene))goto failed;
            SDL_SetRenderDrawColor(renderer,0,0,0,255);SDL_RenderClear(renderer);
            if(wallpaper)SDL_RenderCopy(renderer,wallpaper,NULL,NULL);
            if(background){
                if(console)SDL_SetTextureAlphaMod(background,(Uint8)lround(255*(1-psx_ease(seat/.22))));
                SDL_RenderCopy(renderer,background,NULL,NULL);
            }
            if(!console){SDL_SetRenderDrawColor(renderer,35,35,41,255);SDL_RenderFillRect(renderer,&band);}
            // Cartridges are always their 3D model, the first and last frame too;
            // the shelf face is that same hero pose. Discs keep their flat poster.
            if(seat<=.001&&(!console||umd||disc)){
                SDL_RenderCopy(renderer,back,NULL,&band);
                SDL_Rect hero={(WIDTH-cart_width)/2,foot-cart_height,cart_width,cart_height};
                SDL_RenderCopy(renderer,cart,NULL,&hero);
            }else{
                SDL_SetRenderDrawBlendMode(renderer,SDL_BLENDMODE_BLEND);
                if(umd)psp_scene(renderer,&cartridge,&psx,console,seat);
                else if(disc&&console)ps1_scene(renderer,&cartridge,&psx,console,seat,!insert,lid,eject_spin);
                else if(console)cartridge_scene(renderer,&cartridge,cart,console,cart_width,cart_height,foot,seat,lift,lid);
                else psx_scene(renderer,&psx,seat,!insert,lid,eject_spin);
                SDL_SetRenderDrawBlendMode(renderer,SDL_BLENDMODE_NONE);
            }
            if(footer){
                SDL_Rect left={0,0,225,42},right={520,0,200,42};
                SDL_RenderCopy(renderer,footer,&left,&left);SDL_RenderCopy(renderer,footer,&right,&right);
            }
            double black=psx_ease((seat-(console?.94:.86))/(console?.05:.13));
            if (unseat > 0) black = 1 - psx_ease(elapsed / (console ? .063 : .12)); /* same fade-in as before */
            if(black>0){
                SDL_SetRenderDrawBlendMode(renderer,SDL_BLENDMODE_BLEND);
                SDL_SetRenderDrawColor(renderer,0,0,0,(Uint8)lround(255*black));SDL_RenderFillRect(renderer,NULL);
                SDL_SetRenderDrawBlendMode(renderer,SDL_BLENDMODE_NONE);
            }
            goto present;
        }
        double position = travel(seat, catch);
        double scale_progress = clamp(position / catch);
        int width = (int)lround(cart_width + (240 - cart_width) * scale_progress);
        int height = (int)lround(cart_height + (seated_height - cart_height) * scale_progress);
        int bottom = (int)lround(foot + (seated_foot - foot) * position);
        double fade = clamp(position / catch);
        if (shape->front_loading) {
            /* Lay the upright face forward, slide it into the horizontal tray,
             * then press it below the bezel. Eject reverses all three stages. */
            double tilt = smootherstep(clamp(seat / .42));
            double slide = smootherstep(clamp((seat - .42) / .38));
            double press = smootherstep(clamp((seat - .80) / .20));
            width = (int)lround(cart_width + (240 - cart_width) * tilt);
            height = (int)lround(cart_height + (64 - cart_height) * tilt + (18 - 64) * slide);
            bottom = (int)lround(foot + (470 - foot) * tilt + (451 - 470) * slide + 47 * press);
            fade = tilt;
        }
        SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
        SDL_RenderClear(renderer);
        if (wallpaper) SDL_RenderCopy(renderer, wallpaper, NULL, NULL);
        if (background) {
            double size = 1 - .12 * fade;
            SDL_Rect recede = {(int)lround(WIDTH * (1-size) / 2), (int)lround(foot * (1-size)), (int)lround(WIDTH*size), (int)lround(HEIGHT*size)};
            SDL_SetTextureAlphaMod(background, (Uint8)lround(255 * (1 - fade)));
            SDL_RenderCopy(renderer, background, NULL, &recede);
        }
        SDL_RenderCopy(renderer, back, NULL, &band);
        SDL_Rect rect = {(WIDTH-width)/2, bottom-height, width, height};
        SDL_RenderCopy(renderer, cart, NULL, &rect);
        SDL_RenderCopy(renderer, front, NULL, &band);
        if (footer) {
            SDL_Rect left = {0, 0, 225, 42};
            SDL_Rect right = {520, 0, 200, 42};
            SDL_RenderCopy(renderer, footer, &left, &left);
            SDL_RenderCopy(renderer, footer, &right, &right);
            SDL_Rect middle = {200, BAND_Y, 320, HEIGHT-BAND_Y};
            SDL_SetTextureAlphaMod(footer, (Uint8)lround(255*(1-fade)));
            SDL_RenderCopy(renderer, footer, &middle, &middle);
            SDL_SetTextureAlphaMod(footer, 255);
        }
        if (insert && elapsed > motion_time) {
            double end_fade = smootherstep(clamp((elapsed-motion_time)/.18));
            SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_BLEND);
            SDL_SetRenderDrawColor(renderer, 0, 0, 0, (Uint8)lround(255*end_fade));
            SDL_RenderFillRect(renderer, NULL);
            SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_NONE);
        }
present:
        if(scene){
            if(animation.display>=0&&!animation_layer_present(&animation,renderer,animation_frame)){
                log_event("animation: independent layer failed");animation_layer_close(&animation);
            }
            if(SDL_SetRenderTarget(renderer,NULL))goto failed;
            SDL_SetRenderDrawColor(renderer,0,0,0,255);SDL_RenderClear(renderer);
            if(animation.display<0)SDL_RenderCopy(renderer,scene,NULL,NULL);
        }
        SDL_RenderPresent(renderer);
        if (frames++ == 0) {
            log_event("first frame");
            signal_return(animation.enabled);
        }
        if (elapsed >= duration) break;
        SDL_Event event;
        while (SDL_PollEvent(&event)) { /* Drain events; input belongs to ES/emulator. */ }
        next_frame += 1.0 / 60;
        double delay = next_frame - now();
        if (delay > 0) SDL_Delay((Uint32)(delay * 1000));
    }
    char message[256];
    snprintf(message, sizeof(message), "%s %u frames in %.3f s (%.1f fps)", mode, frames, now()-start, frames/(now()-start));
    log_event(message);
    hold_handover(handover, shape);
    animation_layer_close(&animation);
    SDL_FreeSurface(animation_frame);
    SDL_FreeSurface(handover);
    SDL_DestroyTexture(wallpaper);
    SDL_DestroyTexture(background);
    SDL_DestroyTexture(footer);
    SDL_DestroyTexture(cart);
    SDL_DestroyTexture(back);
    SDL_DestroyTexture(front);
    SDL_DestroyTexture(psx.disc);SDL_DestroyTexture(psx.underside);SDL_DestroyTexture(psx.lid);
    SDL_DestroyTexture(psx.inside);SDL_DestroyTexture(psx.deck);SDL_DestroyTexture(psx.shadow);
    SDL_DestroyTexture(cartridge.body);SDL_DestroyTexture(cartridge.rear);console_mesh_close(&cartridge.disc_mesh);console_mesh_close(&cartridge.mesh);console_mesh_close(&cartridge.media_mesh);
    SDL_DestroyTexture(scene);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
failed:
    log_event(SDL_GetError());
    console_mesh_close(&cartridge.disc_mesh);console_mesh_close(&cartridge.mesh);
    console_mesh_close(&cartridge.media_mesh);
    animation_layer_close(&animation);
    SDL_FreeSurface(animation_frame);
    for(int i=0;i<13;i++)SDL_FreeSurface(prepared[i]);
    SDL_FreeSurface(snapshot);
    SDL_Quit();
    return 1;
}

int main(int argc, char **argv)
{
    process_start = now();
    clock_gettime(CLOCK_REALTIME, &process_wall);
    if (argc != 5 || (strcmp(argv[1], "insert") && strcmp(argv[1], "eject"))) {
        fprintf(stderr, "Usage: %s insert|eject ROM ASSET_DIR DONE_FILE\n", argv[0]);
        return 2;
    }
    mkdir(state_dir, 0700);
    if (!strcmp(argv[1], "eject")) configgen_pid = hook_grandparent();
    /* Eject overlaps the frontend's recovery by default; SLOT_RETURN_ASYNC=0
     * keeps configgen waiting for the whole scene. */
    const char *async = getenv("SLOT_RETURN_ASYNC");
    if (!strcmp(argv[1], "eject") && !(async && !strcmp(async, "0"))
        && !(getenv("SLOT_PREVIEW") && !strcmp(getenv("SLOT_PREVIEW"), "1"))) {
        if (detach_return()) return 0;
    }
    /* The detached eject claims the lock before configgen is released; an
     * insert started by an early relaunch waits for that scene to close. */
    scene_fd = scene_lock(!overlapping_return);
    log_event(argv[1]);
    int result = animate(argv[1], argv[2], argv[3]);
    signal_return(false);
    /* Always release configgen, including missing art and SDL errors. */
    if (!strcmp(argv[1], "insert")) {
        FILE *done = fopen(argv[4], "w");
        if (done) { fputs(argv[2], done); fclose(done); }
    }
    while (waitpid(-1, NULL, WNOHANG) > 0) { }
    log_event(result ? "failed (launch released)" : "done");
    if (scene_fd >= 0) close(scene_fd);
    return result;
}
