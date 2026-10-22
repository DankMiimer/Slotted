// Full source geometry/materials, matching the console studio loader. MIT.
import * as THREE from 'three';
const textureCache=new Map();
async function json(url){const r=await fetch(url),value=await r.json();if(!r.ok)throw Error(value.error||`Cannot load ${url}`);return value;}
async function bytes(url,optional=false){const r=await fetch(url);if(!r.ok){if(optional&&r.status===404)return null;throw Error(`Cannot load ${url}`);}return r.arrayBuffer();}
async function texture(url){if(!textureCache.has(url))textureCache.set(url,new THREE.TextureLoader().loadAsync(url).then(t=>{t.flipY=false;t.colorSpace=THREE.NoColorSpace;return t;}));return textureCache.get(url);}
function material(map=null,unlit=false,crop=[0,0,1,1]){
    // fade < 1 previews a cart faded in front of the selected one (dithered on the device).
    return new THREE.ShaderMaterial({side:THREE.DoubleSide,vertexColors:true,uniforms:{art:{value:map},textured:{value:map?1:0},unlit:{value:unlit?1:0},crop:{value:new THREE.Vector4(...crop)},window:{value:new THREE.Vector4(0,0,1,1)},cutout:{value:0},fade:{value:1}},
        vertexShader:'varying vec3 n,c;varying vec2 v;void main(){gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);vec3 d=vec3(dot(modelMatrix[0].xyz,modelMatrix[0].xyz),dot(modelMatrix[1].xyz,modelMatrix[1].xyz),dot(modelMatrix[2].xyz,modelMatrix[2].xyz));n=mat3(modelMatrix)*(normal/max(d,vec3(.000001)));c=color;v=uv;}',
        fragmentShader:'precision mediump float;varying vec3 n,c;varying vec2 v;uniform sampler2D art;uniform float textured,unlit;uniform vec4 crop,window;uniform float cutout,fade;void main(){vec2 st=clamp((v-window.xy)/(window.zw-window.xy),0.0,1.0);vec4 tex=texture2D(art,crop.xy+st*crop.zw);if(cutout>.5&&tex.a<.5)discard;vec3 color=mix(c,tex.rgb,textured);float light=max(0.0,dot(normalize(n),normalize(vec3(-.45,.8,.5))));gl_FragColor=vec4(color*mix(.43+.57*light,1.0,unlit),fade);}'
    });
}
async function mesh(url,albedo=null,unlit=false,crop=[0,0,1,1]){
    const raw=await bytes(url),view=new DataView(raw),magic=new TextDecoder().decode(raw.slice(0,8)),legacy=magic==='SCTOON2\0';
    if(!legacy&&magic!=='SCTABL1\0')throw Error(`Invalid source mesh ${url}`);
    const n=view.getUint32(8,true),count=view.getUint32(12,true),stride=legacy?9:11;
    if(raw.byteLength!==20+n*stride*4+count*2)throw Error('Truncated source geometry');
    const source=new Float32Array(raw,20,n*stride),position=new Float32Array(n*3),normal=new Float32Array(n*3),color=new Float32Array(n*3),uv=new Float32Array(n*2);
    for(let i=0;i<n;i++){position.set(source.subarray(i*stride,i*stride+3),i*3);normal.set(source.subarray(i*stride+3,i*stride+6),i*3);color.set(source.subarray(i*stride+6,i*stride+9),i*3);if(!legacy)uv.set(source.subarray(i*stride+9,i*stride+11),i*2);}
    if(legacy){const side=await bytes(url.replace(/\.mesh$/,'.texture'),true);if(side){const header=new DataView(side);if(header.getUint32(8,true)!==n||side.byteLength!==48+n*8)throw Error('Invalid source UV sidecar');uv.set(new Float32Array(side,48,n*2));albedo=url.replace(/\.mesh$/,'.albedo.png');}}
    const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(position,3));geometry.setAttribute('normal',new THREE.BufferAttribute(normal,3));geometry.setAttribute('color',new THREE.BufferAttribute(color,3));geometry.setAttribute('uv',new THREE.BufferAttribute(uv,2));geometry.setIndex(new THREE.BufferAttribute(new Uint16Array(raw,20+n*stride*4,count),1));geometry.computeBoundingBox();
    return new THREE.Mesh(geometry,material(albedo?await texture(albedo):null,unlit,crop));
}
async function prepared(key){const info=await json(`/assets/prepared/${key}/scene.json`),group=new THREE.Group();
    const parts=await Promise.all(info.groups.map(p=>mesh(`/assets/prepared/${key}/${p.file}`,p.texture?`/assets/prepared/${key}/${p.texture}`:null)));
    parts.forEach((part,i)=>{part.userData.glass=info.groups[i].glass;part.visible=!info.groups[i].hidden;});group.add(...parts);return {group,info};
}
function voxels(manifest){
    const positions=[],normals=[],colors=[],uvs=[],indices=[],pitch=4.2,depth=5,ink=[.965,.957,.922];
    function face(points,normal){const base=positions.length/3;for(const p of points){positions.push(...p);normals.push(...normal);colors.push(...ink);uvs.push(0,0);}indices.push(base,base+1,base+2,base,base+2,base+3);}
    function mask(rows,x){const h=rows.length,filled=(a,b)=>b>=0&&b<h&&a>=0&&a<rows[b].length&&rows[b][a]!==' ';
        for(let r=0;r<h;r++)for(let c=0;c<rows[r].length;c++)if(filled(c,r)){
            const a=x+c*pitch,b=a+pitch,l=(h-1-r)*pitch,u=l+pitch,z=depth;
            face([[a,l,z],[b,l,z],[b,u,z],[a,u,z]],[0,0,1]);face([[b,l,0],[a,l,0],[a,u,0],[b,u,0]],[0,0,-1]);
            if(!filled(c-1,r))face([[a,l,0],[a,l,z],[a,u,z],[a,u,0]],[-1,0,0]);if(!filled(c+1,r))face([[b,l,z],[b,l,0],[b,u,0],[b,u,z]],[1,0,0]);
            if(!filled(c,r+1))face([[a,l,0],[b,l,0],[b,l,z],[a,l,z]],[0,-1,0]);if(!filled(c,r-1))face([[a,u,z],[b,u,z],[b,u,0],[a,u,0]],[0,1,0]);
        }
    }
    function text(value,x){for(const c of value){const glyph=manifest.glyphs[c];mask(glyph.rows.map(bits=>Array.from({length:glyph.width},(_,i)=>bits&(1<<i)?'#':' ').join('')),x);x+=glyph.advance*pitch;}return x;}
    const gauge=[' ###########  ','#           # ','# ########  ##','# ########  ##','#           # ',' ###########  '];mask(gauge,0);
    let x=text('84%',16*pitch)+2*pitch;mask(['  #######  ','##       ##','   #####   ','  #     #  ','    ###    ','     #     '],x);x+=13*pitch;text('21:48',x);
    const right=Math.max(...positions.filter((_,i)=>i%3===0));for(let i=0;i<positions.length;i+=3)positions[i]-=right/2;
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(normals,3));g.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uvs,2));g.setIndex(indices);return new THREE.Mesh(g,material());
}

export {json,bytes,texture,material,mesh,prepared,voxels};
