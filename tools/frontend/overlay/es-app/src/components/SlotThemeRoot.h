// The active theme's runtime asset folder: Slotted, or the legacy art-book-slot (MIT).
#pragma once
#include "Settings.h"
#include "utils/FileSystemUtil.h"
#include <string>

namespace slot {
constexpr const char* kLegacyTheme="art-book-slot";
constexpr const char* kSlottedTheme="Slotted";
inline bool roomControls(){const auto name=Settings::getInstance()->getString("ThemeSet");return name==kSlottedTheme||name=="slotted";}
inline std::string themeFolder(const std::string& name){return "/userdata/themes/"+name;}
// A theme provides the tabletop by shipping _slot/ (Slotted does). Any other theme set falls back
// to the legacy folder, so existing installs keep working. Ends in '/'. Main thread only; the
// returned reference stays valid, but its value follows ThemeSet changes.
inline const std::string& assetRoot(){
    static std::string set,root;
    const auto current=Settings::getInstance()->getString("ThemeSet");
    if(root.empty()||current!=set){
        set=current;
        const bool plain=!current.empty()&&current.find('/')==std::string::npos&&current!="."&&current!="..";
        const auto own=themeFolder(current)+"/_slot/";
        root=plain&&Utils::FileSystem::isDirectory(own)?own:themeFolder(kLegacyTheme)+"/_slot/";
    }
    return root;
}
}
