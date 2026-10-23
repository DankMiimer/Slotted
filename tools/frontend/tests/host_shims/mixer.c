/* Phase 0 host-only stand-in for libSDL2_mixer-2.0.so.0: audio cannot open, so ES runs silent.
 * Never shipped. */
#include <SDL_mixer.h>

int Mix_OpenAudio(int frequency, Uint16 format, int channels, int chunksize) { (void)frequency; (void)format; (void)channels; (void)chunksize; SDL_SetError("phase0 host: no mixer"); return -1; }
void Mix_CloseAudio(void) {}
Mix_Chunk *Mix_LoadWAV_RW(SDL_RWops *src, int freesrc) { if (src && freesrc) SDL_RWclose(src); return NULL; }
Mix_Chunk *Mix_LoadWAV(const char *file) { (void)file; return NULL; } /* real functions since SDL_mixer 2.6 */
int Mix_PlayChannel(int channel, Mix_Chunk *chunk, int loops) { (void)channel; (void)chunk; (void)loops; return -1; }
Mix_Music *Mix_LoadMUS(const char *file) { (void)file; return NULL; }
void Mix_FreeChunk(Mix_Chunk *chunk) { (void)chunk; }
void Mix_FreeMusic(Mix_Music *music) { (void)music; }
int Mix_PlayChannelTimed(int channel, Mix_Chunk *chunk, int loops, int ticks) { (void)channel; (void)chunk; (void)loops; (void)ticks; return -1; }
int Mix_FadeInMusic(Mix_Music *music, int loops, int ms) { (void)music; (void)loops; (void)ms; return -1; }
int Mix_FadeOutMusic(int ms) { (void)ms; return 0; }
int Mix_HaltChannel(int channel) { (void)channel; return 0; }
int Mix_HaltMusic(void) { return 0; }
void Mix_HookMusicFinished(void (SDLCALL *music_finished)(void)) { (void)music_finished; }
int Mix_PlayingMusic(void) { return 0; }
int Mix_VolumeMusic(int volume) { (void)volume; return 0; }
