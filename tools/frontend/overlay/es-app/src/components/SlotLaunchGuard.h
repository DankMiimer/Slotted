// One private launch transaction, shared with the existing launch hooks. MIT.
#pragma once
#include <cerrno>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <fcntl.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <unistd.h>
#include "SlotThemeRoot.h"

namespace slot {
inline std::string processStart() {
    std::ifstream in("/proc/self/stat");std::string line;
    if(!std::getline(in,line))return {};
    const auto end=line.rfind(')');if(end==std::string::npos)return {};
    std::istringstream fields(line.substr(end+2));std::string value;
    for(int field=3;field<=22;++field)if(!(fields>>value))return {};
    return value;
}
inline bool beginLaunch(const std::string& rom) {
    if(rom.empty() || rom.find_first_of("\r\n")!=std::string::npos)return false;
    if(access((slot::assetRoot()+"launch/frontend-owned.sh").c_str(),R_OK))return false;
    const std::string dir="/tmp/art-book-slot-launch";
    if(mkdir(dir.c_str(),0700) && errno!=EEXIST)return false;
    struct stat info{};
    if(lstat(dir.c_str(),&info) || !S_ISDIR(info.st_mode) || info.st_uid!=getuid() || (info.st_mode&0077))return false;
    unsigned char random[16];if(getrandom(random,sizeof(random),0)!=sizeof(random))return false;
    char nonce[33];for(int i=0;i<16;++i)snprintf(nonce+2*i,3,"%02x",random[i]);
    const auto start=processStart();if(start.empty())return false;
    const std::string temporary=dir+"/frontend-owned.part."+std::to_string(getpid());
    int fd=open(temporary.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);
    if(fd<0)return false;
    const std::string data="1\n"+std::to_string(getpid())+"\n"+start+"\n"+nonce+"\n"+rom+"\n";
    size_t position=0;bool ok=true;
    while(position<data.size()) {
        const auto written=write(fd,data.data()+position,data.size()-position);
        if(written<0 && errno==EINTR)continue;
        if(written<=0){ok=false;break;}position+=written;
    }
    if(close(fd))ok=false;
    if(ok && !rename(temporary.c_str(),(dir+"/frontend-owned").c_str()))return true;
    unlink(temporary.c_str());return false;
}
inline void endLaunch() {
    const std::string path="/tmp/art-book-slot-launch/frontend-owned";
    std::ifstream in(path);std::string version,pid,start;
    if(std::getline(in,version)&&std::getline(in,pid)&&std::getline(in,start)
        && version=="1" && pid==std::to_string(getpid()) && start==processStart())unlink(path.c_str());
}
}
