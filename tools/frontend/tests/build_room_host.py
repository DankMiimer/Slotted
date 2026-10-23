"""Fresh Linux x86-64 native UI test build. Audio/video stand-ins are test-only."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from tools.frontend.apply import PIN,apply,change
from tools.frontend.prepare_build import verify_workspace,sha

ROOT=Path(__file__).resolve().parents[3]

def fixed_updates(source):
    path=Path(source)/'es-core/src/Window.cpp'
    text=path.read_text()
    text=change(text,'void Window::update(int deltaTime)\n{','void Window::update(int deltaTime)\n{\n    deltaTime = 16; // Host screenshot fixture only; never installed.')
    path.write_text(text)

def build(work,sdk,library_dirs=(),jobs=6):
    work=Path(work).absolute();sdk=Path(sdk).resolve()
    if work.exists():raise FileExistsError('Use a fresh host build folder')
    verify_workspace(sdk)
    directories=[Path(p).resolve() for p in library_dirs]+[Path('/usr/lib/x86_64-linux-gnu'),Path('/lib/x86_64-linux-gnu')]
    def library(name):
        for directory in directories:
            path=directory/name
            if path.is_file():return str(path)
        raise ValueError('Install the host runtime library '+name+' or provide --libraries')
    names=('libSDL2-2.0.so.0','libSDL2_image-2.0.so.0','libGLESv2.so.2','libEGL.so.1',
           'libfreetype.so.6','libcurl.so.4','libpulse.so.0','libudev.so.1','libasound.so.2')
    libraries={name:library(name) for name in names}
    work.mkdir(parents=True);source=work/'frontend';shim=work/'host-shim';shim.mkdir()
    subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(sdk/'frontend'),str(source)],check=True)
    subprocess.run(['git','-C',str(source),'checkout','--detach',PIN],check=True)
    subprocess.run(['git','-C',str(source),'submodule','update','--init','--recursive','--depth=1'],check=True)
    apply(source)
    fixed_updates(source)
    headers=sdk/'headers/usr/include';sdl=sdk/'SDL-release-2.32.8/include'
    for name,soname,extra in [('freeimage','libfreeimage.so.3',[libraries['libSDL2_image-2.0.so.0'],libraries['libSDL2-2.0.so.0']]),
        ('vlc','libvlc.so.5',[]),('mixer','libSDL2_mixer-2.0.so.0',[libraries['libSDL2-2.0.so.0']])]:
        subprocess.run(['gcc','-O2','-fPIC','-shared','-I'+str(headers),'-I'+str(sdl),'-I'+str(headers/'SDL2'),
            str(ROOT/'tools/frontend/tests/host_shims'/str(name+'.c')),'-Wl,-soname,'+soname,*extra,'-o',str(shim/soname)],check=True)
    (shim/'libEGL.so').write_text('INPUT ( '+libraries['libEGL.so.1']+' )\n')
    pc=work/'pkgconfig';pc.mkdir()
    for name,lib,version in [('libvlc',str(shim/'libvlc.so.5'),'3.0.21'),('glesv2',libraries['libGLESv2.so.2'],'2.0')]:
        (pc/(name+'.pc')).write_text(f'Name: {name}\nDescription: Native UI test only\nVersion: {version}\nLibs: {lib}\nCflags: -I{headers}\n')
    flags=f'-DH700 -DHAVE_INTL -DSLOT_ROOM_TEST_DRIVER -DSLOT_ROOM_TEST_FIXED_STATUS -I{ROOT}/tools/frontend/tests -idirafter {headers} -idirafter {headers}/x86_64-linux-gnu'
    cmake={'CMAKE_BUILD_TYPE':'Release','CMAKE_MODULE_PATH':str(ROOT/'tools/frontend/cmake'),
        'CMAKE_CXX_FLAGS':flags,'CMAKE_C_FLAGS':f'-idirafter {headers} -idirafter {headers}/x86_64-linux-gnu',
        'CMAKE_EXE_LINKER_FLAGS':'-L'+str(shim)+' '+' '.join('-Wl,-rpath-link,'+str(d) for d in directories),
        'SLOT_SDL_IMAGE_LIBRARY':libraries['libSDL2_image-2.0.so.0'],
        'GLES2':'ON','BATOCERA':'ON','KNULLI':'ON','CEC':'OFF','ENABLE_PULSE':'ON','ENABLE_TTS':'OFF',
        'FREETYPE_INCLUDE_DIR_freetype2':str(headers/'freetype2'),'FREETYPE_INCLUDE_DIR_ft2build':str(headers/'freetype2'),
        'FREETYPE_LIBRARY_RELEASE':libraries['libfreetype.so.6'],'FreeImage_INCLUDE_DIR':str(headers),'FreeImage_LIBRARY':str(shim/'libfreeimage.so.3'),
        'SDL2_INCLUDE_DIR':str(sdl),'SDL2_LIBRARY_TEMP':libraries['libSDL2-2.0.so.0'],'SDL2_LIBRARY':libraries['libSDL2-2.0.so.0'],
        'SDLMIXER_INCLUDE_DIR':str(headers/'SDL2'),'SDLMIXER_LIBRARY':str(shim/'libSDL2_mixer-2.0.so.0'),
        'CURL_INCLUDE_DIR':str(headers/'x86_64-linux-gnu'),'CURL_LIBRARY_RELEASE':libraries['libcurl.so.4'],
        'VLC_INCLUDE_DIR':str(headers),'VLC_LIBRARIES':str(shim/'libvlc.so.5'),
        'RAPIDJSON_INCLUDE_DIRS':str(headers),'RAPIDJSON_INCLUDE_DIR':str(headers),
        'OPENGLES2_INCLUDE_DIR':str(headers),'OPENGLES2_gl_LIBRARY':libraries['libGLESv2.so.2'],
        'PULSEAUDIO_INCLUDE_DIR':str(headers),'PULSEAUDIO_LIBRARY':libraries['libpulse.so.0'],
        'UDEV_INCLUDE_DIR':str(headers),'UDEV_LIBRARY':libraries['libudev.so.1'],'ALSA_INCLUDE_DIR':str(headers),'ALSA_LIBRARY':libraries['libasound.so.2']}
    env=dict(os.environ,PKG_CONFIG_LIBDIR=str(pc))
    subprocess.run(['cmake','-S',str(source),'-B',str(work/'cmake'),*['-D'+k+'='+v for k,v in cmake.items()]],env=env,check=True)
    subprocess.run(['cmake','--build',str(work/'cmake'),'-j',str(jobs)],env=env,check=True)
    result=dict(sourcePin=PIN,binarySha256=sha(source/'emulationstation'),sdk=str(sdk),
        runtimeDirectories=[str(shim)]+list(map(str,directories)),libraryHashes={name:sha(path) for name,path in libraries.items()},
        nativeAudioVideo=False,fixedStatus=True,state='host-native-test-build-only')
    (work/'host-build.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--sdk',type=Path,required=True)
    p.add_argument('--libraries',type=Path,action='append',default=[]);p.add_argument('--jobs',type=int,default=6)
    a=p.parse_args();print(json.dumps(build(a.output,a.sdk,a.libraries,a.jobs),indent=2))
