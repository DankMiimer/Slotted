// Native-grid glyph/icon extrusion. Each occupied pixel is a voxel; internal
// side faces are omitted, preserving glyph holes and visible depth (MIT).
#pragma once
#include "SlotSceneMath.h"
#include "SlotStatusGlyphs.h"
#include <vector>
#include <string>
#include <cstdint>
namespace slot_scene {
struct VoxelVertex {float p[3],n[3],color[3],uv[2];};
struct VoxelGeometry {std::vector<VoxelVertex> vertices;std::vector<uint16_t> indices;};
inline void voxelFace(VoxelGeometry&g,Vec a,Vec b,Vec c,Vec d,Vec n,Vec color){
    uint16_t base=(uint16_t)g.vertices.size();
    for(Vec p:{a,b,c,d})g.vertices.push_back({{p.x,p.y,p.z},{n.x,n.y,n.z},{color.x,color.y,color.z},{0,0}});
    for(int i:{0,1,2,0,2,3})g.indices.push_back(base+i);
}
inline void voxelMask(VoxelGeometry&g,const std::vector<std::string>&mask,float x,float y,float pitch,float depth,Vec color){
    int h=(int)mask.size();auto filled=[&](int col,int row){return row>=0&&row<h&&col>=0&&col<(int)mask[row].size()&&mask[row][col]!=' ';};
    for(int row=0;row<h;row++)for(int col=0;col<(int)mask[row].size();col++)if(filled(col,row)){
        float a=x+col*pitch,b=a+pitch,l=y+(h-1-row)*pitch,u=l+pitch,z=depth;
        voxelFace(g,{a,l,z},{b,l,z},{b,u,z},{a,u,z},{0,0,1},color);
        voxelFace(g,{b,l,0},{a,l,0},{a,u,0},{b,u,0},{0,0,-1},color);
        if(!filled(col-1,row))voxelFace(g,{a,l,0},{a,l,z},{a,u,z},{a,u,0},{-1,0,0},color);
        if(!filled(col+1,row))voxelFace(g,{b,l,z},{b,l,0},{b,u,0},{b,u,z},{1,0,0},color);
        if(!filled(col,row+1))voxelFace(g,{a,l,0},{b,l,0},{b,l,z},{a,l,z},{0,-1,0},color);
        if(!filled(col,row-1))voxelFace(g,{a,u,z},{b,u,z},{b,u,0},{a,u,0},{0,1,0},color);
    }
}
inline float voxelText(VoxelGeometry&g,const std::string&text,float x,float y,float pitch,float depth,Vec color){
    float start=x;
    for(char c:text)for(auto&glyph:statusGlyphs)if(c==glyph.code){
        std::vector<std::string>mask(5,std::string(glyph.width,' '));
        for(int row=0;row<5;row++)for(int col=0;col<glyph.width;col++)if(glyph.rows[row]&(1<<col))mask[row][col]='#';
        voxelMask(g,mask,x,y,pitch,depth,color);x+=glyph.advance*pitch;break;
    }
    return x-start;
}
inline VoxelGeometry statusVoxels(int battery,bool charging,bool connected,const std::string&clock){
    VoxelGeometry g;const Vec ink={.965f,.957f,.922f},low={.9f,.3f,.23f};const float pitch=4.2f,depth=5.f;
    std::vector<std::string>gauge={" ###########  ","#           # ","#           ##","#           ##","#           # "," ###########  "};
    int fill=battery<0?0:std::max(0,std::min(9,(int)std::round(battery*9.f/100)));
    for(int row=2;row<=3;row++)for(int col=2;col<2+fill;col++)gauge[row][col]='#';
    voxelMask(g,gauge,0,0,pitch,depth,battery>=0&&battery<=10?low:ink);
    float x=16*pitch;x+=voxelText(g,battery<0?"?%":std::to_string(std::max(0,std::min(100,battery)))+"%",x,0,pitch,depth,ink);
    if(charging){voxelMask(g,{"  ##"," ## ","####"," ## ","##  "},x,0,pitch,depth,{.55f,.88f,.61f});x+=5*pitch;}
    x+=2*pitch;
    const std::vector<std::string>wifi={"  #######  ","##       ##","   #####   ","  #     #  ","    ###    ","     #     "};
    voxelMask(g,wifi,x,0,pitch,depth,connected?ink:Vec{.38f,.4f,.43f});x+=13*pitch;
    voxelText(g,clock,x,0,pitch,depth,ink);
    // Center the complete cluster on its TV anchor, including a changing 3-digit percentage.
    float right=0;for(auto&v:g.vertices)right=std::max(right,v.p[0]);for(auto&v:g.vertices)v.p[0]-=right/2;
    return g;
}
}
