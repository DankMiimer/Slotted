// Shared right-handed millimetre scene math; no SDL/frontend dependency (MIT).
#pragma once
#include <cmath>
#include <algorithm>
namespace slot_scene {
struct Vec { float x,y,z; };
inline Vec add(Vec a,Vec b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
inline Vec sub(Vec a,Vec b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
inline Vec mul(Vec a,float s){return {a.x*s,a.y*s,a.z*s};}
inline float dot(Vec a,Vec b){return a.x*b.x+a.y*b.y+a.z*b.z;}
inline Vec cross(Vec a,Vec b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
inline Vec unit(Vec a){float n=std::sqrt(dot(a,a));return n>1e-8f?mul(a,1/n):Vec{0,0,0};}
struct Mat {float v[16];};
inline Mat identity(){Mat m={};m.v[0]=m.v[5]=m.v[10]=m.v[15]=1;return m;}
inline Mat product(const Mat&a,const Mat&b){Mat c={};for(int x=0;x<4;x++)for(int y=0;y<4;y++)for(int k=0;k<4;k++)c.v[x*4+y]+=a.v[k*4+y]*b.v[x*4+k];return c;}
inline Mat translate(Vec p){Mat m=identity();m.v[12]=p.x;m.v[13]=p.y;m.v[14]=p.z;return m;}
inline Mat scale(float x,float y,float z){Mat m=identity();m.v[0]=x;m.v[5]=y;m.v[10]=z;return m;}
inline Mat rotate(float x,float y,float z){
    Mat a=identity(),b=identity(),c=identity();
    a.v[5]=a.v[10]=std::cos(x);a.v[6]=std::sin(x);a.v[9]=-a.v[6];
    b.v[0]=b.v[10]=std::cos(y);b.v[8]=std::sin(y);b.v[2]=-b.v[8];
    c.v[0]=c.v[5]=std::cos(z);c.v[1]=std::sin(z);c.v[4]=-c.v[1];
    return product(product(b,a),c);
}
inline Mat pose(Vec at,float yaw,float lean=0,float size=1){return product(product(translate(at),rotate(lean,yaw,0)),scale(size,size,size));}
inline Mat lookAt(Vec eye,Vec target,Vec up={0,1,0}){
    Vec f=unit(sub(target,eye)),s=unit(cross(f,up)),u=cross(s,f);Mat m=identity();
    m.v[0]=s.x;m.v[4]=s.y;m.v[8]=s.z;m.v[1]=u.x;m.v[5]=u.y;m.v[9]=u.z;
    m.v[2]=-f.x;m.v[6]=-f.y;m.v[10]=-f.z;m.v[12]=-dot(s,eye);m.v[13]=-dot(u,eye);m.v[14]=dot(f,eye);return m;
}
inline Mat perspective(float radians,float aspect,float near,float far){Mat m={};float f=1/std::tan(radians/2);m.v[0]=f/aspect;m.v[5]=f;m.v[10]=(far+near)/(near-far);m.v[11]=-1;m.v[14]=2*far*near/(near-far);return m;}
inline Vec transform(const Mat&m,Vec p){float w=m.v[3]*p.x+m.v[7]*p.y+m.v[11]*p.z+m.v[15];if(std::abs(w)<1e-8f)w=1e-8f;return {(m.v[0]*p.x+m.v[4]*p.y+m.v[8]*p.z+m.v[12])/w,(m.v[1]*p.x+m.v[5]*p.y+m.v[9]*p.z+m.v[13])/w,(m.v[2]*p.x+m.v[6]*p.y+m.v[10]*p.z+m.v[14])/w};}
inline float ease(float x){x=std::max(0.f,std::min(1.f,x));return x*x*(3-2*x);}
inline float radians(float d){return d*3.14159265358979323846f/180.f;}
}
