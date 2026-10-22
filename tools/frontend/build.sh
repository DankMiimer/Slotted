#!/bin/sh
# Build a private, pinned Knulli frontend; never installs or replaces the OS binary.
set -eu
project=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
work=${SLOT_ES_BUILD_ROOT:-$HOME/slot-es-presentation}
source="$work/frontend"
headers="$work/headers/usr/include"
libs="$project/build/slotted-presentation/lib"
pin=4041b56a714265de81de8165b34fbd10f313a891
[ "$(git -C "$source" rev-parse HEAD)" = "$pin" ] || { echo 'Unexpected frontend revision' >&2; exit 1; }
[ -f "$headers/vlc/vlc.h" ] || { echo 'Prepare development headers first' >&2; exit 1; }
cmp -s "$project/build/native/SDL-release-2.32.8/include/SDL_config_minimal.h" "$headers/SDL2/SDL_config.h" || cp "$project/build/native/SDL-release-2.32.8/include/SDL_config_minimal.h" "$headers/SDL2/SDL_config.h"
mkdir -p "$headers/KHR"
cmp -s "$project/build/native/SDL-release-2.32.8/include/SDL_opengles2_khrplatform.h" "$headers/KHR/khrplatform.h" || cp "$project/build/native/SDL-release-2.32.8/include/SDL_opengles2_khrplatform.h" "$headers/KHR/khrplatform.h"
mkdir -p "$work/pkgconfig"
cat > "$work/pkgconfig/libvlc.pc" <<EOF
prefix=$work/headers/usr
libdir=$libs
includedir=$headers
Name: libvlc
Description: Target Knulli VLC
Version: 3.0.21
Libs: $libs/libvlc.so.5
Cflags: -I$headers
EOF
cat > "$work/pkgconfig/glesv2.pc" <<EOF
Name: glesv2
Description: Target Knulli GLES
Version: 2.0
Libs: $libs/libmali.so
Cflags: -I$headers
EOF
cat > "$work/toolchain.cmake" <<EOF
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_C_COMPILER aarch64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE NEVER)
set(CMAKE_CXX_FLAGS_INIT "-DH700 -DHAVE_INTL -idirafter $headers -idirafter $headers/x86_64-linux-gnu")
set(CMAKE_C_FLAGS_INIT "-idirafter $headers -idirafter $headers/x86_64-linux-gnu")
set(CMAKE_EXE_LINKER_FLAGS_INIT "-L$libs -Wl,--allow-shlib-undefined")
EOF
export PKG_CONFIG_LIBDIR="$work/pkgconfig"
cmake -S "$source" -B "$work/arm64" \
    -DCMAKE_MODULE_PATH="$project/tools/frontend/cmake" \
    -DCMAKE_TOOLCHAIN_FILE="$work/toolchain.cmake" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_FLAGS="-DH700 -DHAVE_INTL -idirafter $headers -idirafter $headers/x86_64-linux-gnu" \
    -DCMAKE_C_FLAGS="-idirafter $headers -idirafter $headers/x86_64-linux-gnu" \
    -DSLOT_SDL_IMAGE_LIBRARY="$libs/libSDL2_image-2.0.so.0" \
    -DCMAKE_EXE_LINKER_FLAGS="-L$libs -Wl,--allow-shlib-undefined" \
    -DGLES2=ON -DBATOCERA=ON -DKNULLI=ON -DCEC=OFF -DENABLE_PULSE=ON -DENABLE_TTS=ON \
    -DFREETYPE_INCLUDE_DIR_freetype2="$headers/freetype2" -DFREETYPE_INCLUDE_DIR_ft2build="$headers/freetype2" \
    -DFREETYPE_LIBRARY_RELEASE="$libs/libfreetype.so.6" \
    -DFreeImage_INCLUDE_DIR="$headers" -DFreeImage_LIBRARY="$libs/libfreeimage.so.3" \
    -DSDL2_INCLUDE_DIR="$project/build/native/SDL-release-2.32.8/include" \
    -DSDL2_LIBRARY_TEMP="$libs/libSDL2-2.0.so.0" -DSDL2_LIBRARY="$libs/libSDL2-2.0.so.0" \
    -DSDLMIXER_INCLUDE_DIR="$headers/SDL2" -DSDLMIXER_LIBRARY="$libs/libSDL2_mixer-2.0.so.0" \
    -DCURL_INCLUDE_DIR="$headers/x86_64-linux-gnu" -DCURL_LIBRARY_RELEASE="$libs/libcurl.so.4" \
    -DVLC_INCLUDE_DIR="$headers" -DVLC_LIBRARIES="$libs/libvlc.so.5" \
    -DRAPIDJSON_INCLUDE_DIRS="$headers" -DRAPIDJSON_INCLUDE_DIR="$headers" \
    -DOPENGLES2_INCLUDE_DIR="$headers" -DOPENGLES2_gl_LIBRARY="$libs/libmali.so" \
    -DPULSEAUDIO_INCLUDE_DIR="$headers" -DPULSEAUDIO_LIBRARY="$libs/libpulse.so.0" \
    -DUDEV_INCLUDE_DIR="$headers" -DUDEV_LIBRARY="$libs/libudev.so.1" \
    -DLIBESPEAK_LIBRARIES="$libs/libespeak.so.1" \
    -DALSA_INCLUDE_DIR="$headers" -DALSA_LIBRARY="$libs/libasound.so.2"
cmake --build "$work/arm64" -j "${SLOT_ES_JOBS:-4}"
