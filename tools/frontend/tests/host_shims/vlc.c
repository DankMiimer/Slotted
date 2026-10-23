/* Phase 0 host-only stand-in for libvlc.so.5: every call fails or does nothing, so ES runs with
 * video unavailable (libvlc_new returns NULL). The spikes do not need playback. Never shipped. */
#include <vlc/vlc.h>
#include <stddef.h>

libvlc_instance_t *libvlc_new(int argc, const char *const *argv) { (void)argc; (void)argv; return NULL; }
void libvlc_release(libvlc_instance_t *p_instance) { (void)p_instance; }
libvlc_media_t *libvlc_media_new_path(libvlc_instance_t *p_instance, const char *path) { (void)p_instance; (void)path; return NULL; }
void libvlc_media_add_option(libvlc_media_t *p_md, const char *psz_options) { (void)p_md; (void)psz_options; }
void libvlc_media_release(libvlc_media_t *p_md) { (void)p_md; }
void libvlc_media_parse(libvlc_media_t *p_md) { (void)p_md; }
int libvlc_media_parse_with_options(libvlc_media_t *p_md, libvlc_media_parse_flag_t parse_flag, int timeout) { (void)p_md; (void)parse_flag; (void)timeout; return -1; }
libvlc_media_parsed_status_t libvlc_media_get_parsed_status(libvlc_media_t *p_md) { (void)p_md; return libvlc_media_parsed_status_failed; }
unsigned libvlc_media_tracks_get(libvlc_media_t *p_md, libvlc_media_track_t ***tracks) { (void)p_md; if (tracks) *tracks = NULL; return 0; }
void libvlc_media_tracks_release(libvlc_media_track_t **p_tracks, unsigned i_count) { (void)p_tracks; (void)i_count; }
libvlc_media_player_t *libvlc_media_player_new_from_media(libvlc_media_t *p_md) { (void)p_md; return NULL; }
void libvlc_media_player_release(libvlc_media_player_t *p_mi) { (void)p_mi; }
void libvlc_media_player_set_media(libvlc_media_player_t *p_mi, libvlc_media_t *p_md) { (void)p_mi; (void)p_md; }
int libvlc_media_player_play(libvlc_media_player_t *p_mi) { (void)p_mi; return -1; }
void libvlc_media_player_pause(libvlc_media_player_t *p_mi) { (void)p_mi; }
void libvlc_media_player_stop(libvlc_media_player_t *p_mi) { (void)p_mi; }
libvlc_state_t libvlc_media_player_get_state(libvlc_media_player_t *p_mi) { (void)p_mi; return libvlc_Error; }
libvlc_time_t libvlc_media_player_get_time(libvlc_media_player_t *p_mi) { (void)p_mi; return -1; }
void libvlc_media_player_set_time(libvlc_media_player_t *p_mi, libvlc_time_t i_time) { (void)p_mi; (void)i_time; }
void libvlc_media_player_set_position(libvlc_media_player_t *p_mi, float f_pos) { (void)p_mi; (void)f_pos; }
int libvlc_media_player_set_rate(libvlc_media_player_t *p_mi, float rate) { (void)p_mi; (void)rate; return -1; }
void libvlc_audio_set_mute(libvlc_media_player_t *p_mi, int status) { (void)p_mi; (void)status; }
void libvlc_video_set_callbacks(libvlc_media_player_t *mp, libvlc_video_lock_cb lock, libvlc_video_unlock_cb unlock, libvlc_video_display_cb display, void *opaque) { (void)mp; (void)lock; (void)unlock; (void)display; (void)opaque; }
void libvlc_video_set_format(libvlc_media_player_t *mp, const char *chroma, unsigned width, unsigned height, unsigned pitch) { (void)mp; (void)chroma; (void)width; (void)height; (void)pitch; }
int libvlc_video_take_snapshot(libvlc_media_player_t *p_mi, unsigned num, const char *psz_filepath, unsigned int i_width, unsigned int i_height) { (void)p_mi; (void)num; (void)psz_filepath; (void)i_width; (void)i_height; return -1; }
