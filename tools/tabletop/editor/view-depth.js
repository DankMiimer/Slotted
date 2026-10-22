// Mirrors SlotSceneDepth.h and SlotTabletop.cpp labelOccluders so the editor preview
// matches the device: the near plane stops just in front of the closest geometry in view
// (10..150 mm), and carts that cover the selected cart's label in the cartridge view fade.
// Matrices are column-major 16-element arrays (Three.js Matrix4.elements).

function apply(m,[x,y,z]){const w=m[3]*x+m[7]*y+m[11]*z+m[15]||1e-8;return [(m[0]*x+m[4]*y+m[8]*z+m[12])/w,(m[1]*x+m[5]*y+m[9]*z+m[13])/w,(m[2]*x+m[6]*y+m[10]*z+m[14])/w];}
function product(a,b){const c=new Array(16).fill(0);for(let x=0;x<4;x++)for(let y=0;y<4;y++)for(let k=0;k<4;k++)c[x*4+y]+=a[k*4+y]*b[x*4+k];return c;}
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]],dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2],cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const corners=(low,high)=>Array.from({length:8},(_,k)=>[k&1?high[0]:low[0],k&2?high[1]:low[1],k&4?high[2]:low[2]]);

export const depthRange=()=>({closest:1e9,farthest:0,visible:false});
// Clips the box to the frustum (camera looks down -Z) and widens `range` by what remains.
export function boxDepth(range,view,model,low,high,tanX,tanY,epsilon=1){
    const m=product(view,model),c=corners(low,high).map(p=>apply(m,p));
    const e1=sub(c[1],c[0]),e2=sub(c[2],c[0]),e3=sub(c[4],c[0]),o=c[0].map(v=>-v),det=dot(e1,cross(e2,e3));let inside=false;
    if(Math.abs(det)>1e-6){const a=dot(o,cross(e2,e3))/det,b=dot(e1,cross(o,e3))/det,d=dot(e1,cross(e2,o))/det;inside=a>=0&&a<=1&&b>=0&&b<=1&&d>=0&&d<=1;}
    if(inside){range.closest=Math.min(range.closest,epsilon);range.visible=true;}
    const planes=[[0,0,-1,-epsilon],[1,0,-tanX,0],[-1,0,-tanX,0],[0,1,-tanY,0],[0,-1,-tanY,0]];
    const faces=[[0,2,6,4],[1,3,7,5],[0,1,5,4],[2,3,7,6],[0,1,3,2],[4,5,7,6]];let any=false;
    for(const face of faces){
        let poly=face.map(i=>c[i]);
        for(const p of planes){
            const next=[];
            for(let i=0;i<poly.length;i++){const a=poly[i],b=poly[(i+1)%poly.length],da=p[0]*a[0]+p[1]*a[1]+p[2]*a[2]+p[3],db=p[0]*b[0]+p[1]*b[1]+p[2]*b[2]+p[3];
                if(da>=0)next.push(a);if((da>=0)!==(db>=0)){const t=da/(da-db);next.push([a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t]);}}
            poly=next;if(!poly.length)break;
        }
        for(const v of poly){range.closest=Math.min(range.closest,-v[2]);range.farthest=Math.max(range.farthest,-v[2]);any=true;}
    }
    range.visible=range.visible||any;return any||inside;
}
export const hugNear=(range,floor=10,ceiling=150)=>range.visible?Math.max(floor,Math.min(ceiling,range.closest*.95)):ceiling;

// 2D convex geometry over projected (NDC) points.
const turn=(o,a,b)=>(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0]);
export function hull(points){
    const p=[...points].sort((a,b)=>a[0]-b[0]||a[1]-b[1]),h=[];
    for(const q of p){while(h.length>=2&&turn(h[h.length-2],h[h.length-1],q)<=0)h.pop();h.push(q);}
    for(let i=p.length-2,t=h.length+1;i>=0;i--){while(h.length>=t&&turn(h[h.length-2],h[h.length-1],p[i])<=0)h.pop();h.push(p[i]);}
    h.pop();return h;
}
export const area=p=>Math.abs(p.reduce((s,u,i)=>{const v=p[(i+1)%p.length];return s+u[0]*v[1]-u[1]*v[0];},0))/2;
export function clip(subject,clipper){
    for(let i=0;i<clipper.length&&subject.length;i++){
        const a=clipper[i],b=clipper[(i+1)%clipper.length],out=[];
        for(let j=0;j<subject.length;j++){const p=subject[j],q=subject[(j+1)%subject.length],dp=turn(a,b,p),dq=turn(a,b,q);
            if(dp>=0)out.push(p);if((dp>=0)!==(dq>=0)){const t=dp/(dp-dq);out.push([p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t]);}}
        subject=out;
    }
    return subject;
}
// Projected outline of a box, or [] when a corner is not at least 1 mm in front of the eye.
export function outline(projection,view,model,low,high){
    const toEye=product(view,model),toClip=product(projection,toEye),points=[];
    for(const p of corners(low,high)){if(apply(toEye,p)[2]>-1)return [];const q=apply(toClip,p);points.push([q[0],q[1]]);}
    return hull(points);
}
// Indices of carts nearer than the selected one whose outline covers > 2% of its label.
// carts[i] = {shell:{model,low,high}, label:{model,low,high}|null}; eye/forward in world mm.
export function labelOccluders(carts,selected,projection,view,eye,forward){
    const centre=b=>{const c=apply(b.model,b.low.map((v,i)=>(v+b.high[i])/2));return dot(sub(c,eye),forward);};
    const face=carts[selected].label||carts[selected].shell,label=outline(projection,view,face.model,face.low,face.high),whole=label.length>2?area(label):0,out=[];
    if(whole<=0)return out;const far=centre(carts[selected].shell);
    carts.forEach((cart,i)=>{
        if(i===selected||centre(cart.shell)>=far)return;
        const h=outline(projection,view,cart.shell.model,cart.shell.low,cart.shell.high);
        if(h.length>2&&area(clip(label,h))>.02*whole)out.push(i);
    });
    return out;
}
