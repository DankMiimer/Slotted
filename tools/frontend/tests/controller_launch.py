"""Check the production controller CLI against Knulli's devicepath contract."""
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

source=Path(sys.argv[1])/'es-core/src/InputManager.cpp'
text=source.read_text();start=text.index('std::string InputManager::configureEmulators()')
brace=text.index('{',start);depth=1;end=brace+1
while depth:
    depth+=(text[end]=='{')-(text[end]=='}');end+=1
method=text[start:end]
harness=r'''
#include <iostream>
#include <sstream>
#include <string>
#include <map>
const int MAX_PLAYERS=2;
std::ostringstream sink;
#define LOG(level) sink
struct InputConfig {
    int getDeviceIndex(){return 0;}
    std::string getDeviceGUIDString(){return "pad-guid";}
    std::string getDevicePath(){return "/dev/input/event1";}
    std::string getDeviceName(){return "Anbernic RG34XX-SP Controller";}
    int getDeviceNbButtons(){return 17;}
    int getDeviceNbHats(){return 1;}
    int getDeviceNbAxes(){return 4;}
};
struct InputManager {
    InputConfig pad;
    std::map<int,InputConfig*>computePlayersConfigs(){return {{0,&pad}};}
    std::string configureEmulators();
};
'''
with tempfile.TemporaryDirectory() as temporary:
    cpp=Path(temporary)/'controller.cpp';binary=Path(temporary)/'controller'
    cpp.write_text(harness+method+'\nint main(){InputManager manager;std::cout<<manager.configureEmulators();}\n')
    for flags,argument in [([], '-p1devicepath'),(['-DWIN32=1'],'-p1path')]:
        subprocess.run(['g++','-std=c++14',*flags,str(cpp),'-o',str(binary)],check=True)
        args=shlex.split(subprocess.check_output([str(binary)],text=True))
        assert args[args.index(argument)+1]=='/dev/input/event1',args
        assert args[args.index('-p1name')+1]=='Anbernic RG34XX-SP Controller',args
        assert args.count(argument)==1 and not any(a.startswith('-p2') for a in args),args
        assert ('-p1path' not in args) if not flags else ('-p1devicepath' not in args)
print('Production controller CLI: Linux devicepath and retained Windows path PASS')
