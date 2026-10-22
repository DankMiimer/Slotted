import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {TransformControls} from 'three/addons/controls/TransformControls.js';
import {createStudioControls} from './studio-controls.js';
import {createTransformSelection} from './transform-selection.js';
import {boxDepth,depthRange,hugNear} from './view-depth.js';

const $=id=>document.getElementById(id), radians=THREE.MathUtils.degToRad, degrees=THREE.MathUtils.radToDeg;
const cartridgeCount=12;
// Each console has its own layout and browser draft; the SNES keeps its original draft key.
const params=new URLSearchParams(location.search),system=params.get('system')||'snes',tvKey=params.get('tv')||'panasonic',query=`?system=${encodeURIComponent(system)}&tv=${encodeURIComponent(tvKey)}`;
// The plain editor address reopens the console and TV used last (a GBA + PVM layout once
// looked lost when the start link opened SNES + Panasonic).
const lastKey='slot-scene-last';
if(!params.get('system')){let last=null;try{last=JSON.parse(localStorage.getItem(lastKey));}catch{}if(last?.system&&last?.tv&&(last.system!=='snes'||last.tv!=='panasonic')){location.replace(`?system=${encodeURIComponent(last.system)}&tv=${encodeURIComponent(last.tv)}`);await new Promise(()=>{});}}
try{localStorage.setItem(lastKey,JSON.stringify({system,tv:tvKey}));}catch{}
const originalDraftKey=system==='snes'?'slot-scene-draft':`slot-scene-draft-${system}`,draftKey=tvKey==='panasonic'?originalDraftKey:`${originalDraftKey}-${tvKey}`;
const names=['table','tv','console','status',...Array.from({length:cartridgeCount},(_,i)=>`cart${i}`)];
const labels={table:'Table',tv:'Television',console:'Console',status:'TV status',all:'All cartridges',...Object.fromEntries(Array.from({length:cartridgeCount},(_,i)=>[`cart${i}`,`Cartridge ${i+1}`]))};
const clone=value=>JSON.parse(JSON.stringify(value));
const scene=new THREE.Scene();scene.background=new THREE.Color(.025,.030,.040);
const renderer=new THREE.WebGLRenderer({canvas:$('canvas'),antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.LinearSRGBColorSpace;
const camera=new THREE.PerspectiveCamera(40,1.5,150,10000);
const orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=false;orbit.maxPolarAngle=Math.PI-.02;orbit.minDistance=160;orbit.maxDistance=9000;
const gizmo=new TransformControls(camera,renderer.domElement);gizmo.setSize(.8);scene.add(gizmo.getHelper());
const groups={},textureCache=new Map(),history=[],future=[];let busy=false,loaded=false,hidden=false,dragStart=null,baseline,manifest,dirty=false;
const inputs={};let studio=null,selection=null,cameraToolActive=false;

async function json(url){const r=await fetch(url);if(!r.ok)throw Error(`Cannot load ${url}`);return r.json();}
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
// Flat recessed label for shells without a source label surface (SlotTabletop.cpp labelQuad).
function labelQuad([x,y,halfW,halfH,z],units,map,crop){
    const corner=[[-1,1],[1,1],[1,-1],[-1,-1]],position=[],uv=[];
    for(const [a,b] of corner){position.push((x+halfW*a)*units,(y+halfH*b)*units,z*units);uv.push((a+1)/2,(1-b)/2);}
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(position,3));g.setAttribute('normal',new THREE.Float32BufferAttribute([0,0,1,0,0,1,0,0,1,0,0,1],3));
    g.setAttribute('color',new THREE.Float32BufferAttribute(Array(12).fill(1),3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex([0,3,2,0,2,1]);
    return new THREE.Mesh(g,material(map,true,crop));
}
// Annular disc (SlotTabletop.cpp discMeshes): printed top face = label, dark underside and rims = shell.
function discGeometry([radius,thickness],units){
    const n=96,big=radius*units,bore=big/8,h=thickness*units/2,top={p:[],n:[],c:[],uv:[],i:[]},rest={p:[],n:[],c:[],uv:[],i:[]};
    function ring(g,r0,z0,r1,z1,radial,sign,colour,printed){
        const base=g.p.length/3;
        for(let k=0;k<=n;k++){const a=k*2*Math.PI/n,c=Math.cos(a),s=Math.sin(a);
            for(const [r,z] of [[r0,z0],[r1,z1]]){g.p.push(r*c,r*s,z);g.n.push(radial?c*sign:0,radial?s*sign:0,radial?0:sign);g.c.push(...colour);g.uv.push(printed?.5+r/big*c*.5:0,printed?.5-r/big*s*.5:0);}}
        for(let k=0;k<n;k++){const a=base+2*k;g.i.push(a,a+1,a+3,a,a+3,a+2);}
    }
    ring(top,bore,h,big,h,false,1,[1,1,1],true);ring(rest,bore,-h,big,-h,false,-1,[.06,.06,.07],false);
    ring(rest,big,-h,big,h,true,1,[.22,.23,.25],false);ring(rest,bore,-h,bore,h,true,-1,[.22,.23,.25],false);
    const geometry=g=>{const b=new THREE.BufferGeometry();b.setAttribute('position',new THREE.Float32BufferAttribute(g.p,3));b.setAttribute('normal',new THREE.Float32BufferAttribute(g.n,3));b.setAttribute('color',new THREE.Float32BufferAttribute(g.c,3));b.setAttribute('uv',new THREE.Float32BufferAttribute(g.uv,2));b.setIndex(g.i);return b;};
    return {shell:geometry(rest),label:geometry(top)};
}
async function prepared(key){const info=await json(`/assets/prepared/${key}/scene.json`),group=new THREE.Group();
    const parts=await Promise.all(info.groups.map(p=>mesh(`/assets/prepared/${key}/${p.file}`,p.texture?`/assets/prepared/${key}/${p.texture}`:null)));
    parts.forEach((part,i)=>{part.userData.glass=info.groups[i].glass;part.visible=!info.groups[i].hidden;});group.add(...parts);return {group,info};
}
function voxels(){
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
function snapshot(){return {version:1,system:manifest.system,tv:manifest.tv,viewport:{width:720,height:$('aspect').value==='4:3'?540:480},camera:{position:camera.position.toArray(),target:orbit.target.toArray(),fov:camera.fov},objects:Object.fromEntries(names.map(name=>{
    const g=groups[name],position=name.startsWith('cart')?g.getWorldPosition(new THREE.Vector3()):g.position;
    const rotation=name.startsWith('cart')?new THREE.Euler().setFromQuaternion(g.getWorldQuaternion(new THREE.Quaternion()),'YXZ'):g.rotation;
    return [name,{position:position.toArray(),rotation:[rotation.x,rotation.y,rotation.z].map(degrees)}];
})),...(studio?studio.extras():{})};}
function setNode(name,value){const g=groups[name];g.position.fromArray(value.position);g.rotation.set(...value.rotation.map(radians),'YXZ');}
function centerCartridges(){
    for(let i=0;i<cartridgeCount;i++)scene.attach(groups[`cart${i}`]);
    const center=new THREE.Vector3();for(let i=0;i<cartridgeCount;i++)center.add(groups[`cart${i}`].position);center.multiplyScalar(1/cartridgeCount);
    groups.all.position.copy(center);groups.all.rotation.set(0,0,0);groups.all.updateMatrixWorld(true);
    for(let i=0;i<cartridgeCount;i++)groups.all.attach(groups[`cart${i}`]);
}
function apply(value){busy=true;groups.all.position.set(0,0,0);groups.all.rotation.set(0,0,0);for(const name of names)setNode(name,value.objects[name]);centerCartridges();camera.position.fromArray(value.camera.position);orbit.target.fromArray(value.camera.target);camera.fov=value.camera.fov;studio?.load(value);busy=true;$('aspect').value=value.viewport.height===540?'4:3':'3:2';resize();orbit.update();selection?.refresh();busy=false;updateSelection();updateFields();}
function markDirty(){if(busy||!loaded)return;dirty=true;localStorage.setItem(draftKey,JSON.stringify(snapshot()));$('saveState').textContent='Unsaved layout · browser draft retained';}
function commit(before){if(!before)return;const now=JSON.stringify(snapshot());if(now!==before){history.push(before);if(history.length>100)history.shift();future.length=0;markDirty();}updateFields();}
function act(action){const before=JSON.stringify(snapshot());action();commit(before);}
function cameraTool(value){cameraToolActive=value;studio?.mouseCamera(value);$('cameraMouse').classList.toggle('active',value);$('cameraMouse').setAttribute('aria-pressed',value);$('cameraMouse').textContent=value?'Camera mouse tool active':'Adjust camera with mouse';updateSelection();}
function updateSelection(){
    if(!loaded||!selection)return;const chosen=selection.names(),target=selection.target(),multiple=chosen.length>1;
    if(target)gizmo.attach(target);else gizmo.detach();gizmo.enabled=!!target&&!hidden&&!cameraToolActive;gizmo.getHelper().visible=gizmo.enabled;
    const title=multiple?`${chosen.length} objects selected`:chosen.length?labels[chosen[0]]:'No objects selected';$('selection').textContent=title;$('selectionCount').textContent=title;
    for(const button of $('objects').children){const active=button.dataset.name==='all'?names.slice(4).every(name=>chosen.includes(name)):chosen.includes(button.dataset.name);button.classList.toggle('active',active);button.setAttribute('aria-pressed',active);}
    $('positionLabel').textContent=multiple?'SELECTION CENTER · WORLD MILLIMETRES':chosen[0]==='status'?'POSITION · RELATIVE TO TV':chosen[0]?.startsWith('cart')?'POSITION · RELATIVE TO GROUP':'POSITION · MILLIMETRES';
    $('objectHint').textContent=multiple?'Move the shared center or rotate around it. Spacing, model scales and parent relationships are preserved.':chosen[0]==='status'?'Status follows the TV. These coordinates are relative to its housing.':'Shift/Ctrl-click models to add or remove them, or enable Select multiple.';
    $('ground').disabled=!target;$('focus').disabled=!target;
    $('swapSelected').disabled=chosen.length!==2;
    if(chosen.length===2){$('swapFirst').value=chosen[0];$('swapSecond').value=chosen[1];}
    updateSwap();
}
function select(name,toggle=false){
    if(!loaded)return;cameraTool(false);
    if(name==='all')selection.choose(names.slice(4));
    else if(toggle){const chosen=selection.names();selection.choose(chosen.includes(name)?chosen.filter(key=>key!==name):[...chosen,name]);}
    else selection.choose([name]);
    if(/^cart[0-9]+$/.test(name)&&selection.names().includes(name))studio?.selectCartridge(Number(name.slice(4)));
    updateSelection();updateFields();
}
function updateFields(){
    if(!loaded)return;const object=selection?.target(),values={position:object?.position.toArray()||[0,0,0],rotation:object?[object.rotation.x,object.rotation.y,object.rotation.z].map(degrees):[0,0,0],eye:camera.position.toArray(),target:orbit.target.toArray()};
    for(const key of ['position','rotation','eye','target'])for(let i=0;i<3;i++){const input=inputs[key][i];input.disabled=(key==='position'||key==='rotation')&&!object;if(document.activeElement!==input)input.value=values[key][i].toFixed(1);}
    $('fov').value=camera.fov;if(document.activeElement!==$('fovNumber'))$('fovNumber').value=camera.fov.toFixed(1);$('fovValue').textContent=camera.fov.toFixed(1)+'°';
    $('cameraEditing').textContent='Editing camera: '+$('view').selectedOptions[0].textContent;$('undo').disabled=!history.length;$('redo').disabled=!future.length;
}
for(const key of ['position','rotation','eye','target']){
    inputs[key]=['X','Y','Z'].map((axis,i)=>{
        const label=document.createElement('label'),span=document.createElement('span'),input=document.createElement('input');let before=null;
        span.textContent=axis;input.type='number';input.step=key==='rotation'?'1':'5';input.setAttribute('aria-label',`${key} ${axis}`);label.append(span,input);$(key).append(label);
        input.addEventListener('focus',()=>{if(!loaded)return;if(key==='eye'||key==='target')studio?.beginCameraEdit();before=JSON.stringify(snapshot());selection?.begin();});
        input.addEventListener('input',()=>{
            if(!loaded||input.value==='')return;const value=Number(input.value);if(!Number.isFinite(value)||Math.abs(value)>10000)return;
            const object=selection?.target();
            if(key==='position'&&object)object.position.setComponent(i,value);if(key==='rotation'&&object)object.rotation[axis.toLowerCase()]=radians(value);
            if(key==='position'||key==='rotation'){selection?.change();markDirty();}
            else{const next={position:camera.position.toArray(),target:orbit.target.toArray(),fov:camera.fov};next[key==='eye'?'position':'target'][i]=value;studio?.applyManualCamera(next);}
        });
        input.addEventListener('blur',()=>{if(loaded){selection?.end();commit(before);before=null;updateFields();}});
        input.addEventListener('keydown',event=>{if(event.key==='Enter')input.blur();});return input;
    });
}
for(const name of [...names.slice(0,4),'all',...names.slice(4)]){const button=document.createElement('button');button.textContent=labels[name];button.dataset.name=name;if(name==='all')button.style.gridColumn='span 2';button.addEventListener('click',event=>select(name,event.shiftKey||event.ctrlKey||event.metaKey||$('multiSelect').checked));$('objects').append(button);}
function updateSwap(){if(!$('swapFirst').value)return;$('swapObjects').disabled=$('swapFirst').value===$('swapSecond').value||(!$('swapPosition').checked&&!$('swapRotation').checked);}
for(const id of ['swapFirst','swapSecond','swapPosition','swapRotation'])$(id).onchange=updateSwap;
for(const id of ['swapFirst','swapSecond'])for(const name of names){const option=document.createElement('option');option.value=name;option.textContent=labels[name];$(id).append(option);}
$('swapFirst').value='cart0';$('swapSecond').value='cart1';
function swapPair(first,second,position=true,rotation=true){act(()=>selection.swap(first,second,position,rotation));updateSelection();$('transformState').textContent=`Swapped ${labels[first]} and ${labels[second]}. Undo restores their previous transforms.`;}
$('swapObjects').onclick=()=>{if(loaded)swapPair($('swapFirst').value,$('swapSecond').value,$('swapPosition').checked,$('swapRotation').checked);};
$('swapSelected').onclick=()=>{if(!loaded||selection.names().length!==2)return;swapPair(...selection.names());};
$('clearSelection').onclick=()=>{if(!loaded)return;selection.choose([]);updateSelection();updateFields();};
$('selectAllObjects').onclick=()=>{if(!loaded)return;cameraTool(false);selection.choose(names);updateSelection();updateFields();};
function mode(value){cameraTool(false);gizmo.setMode(value);$('move').classList.toggle('active',value==='translate');$('rotate').classList.toggle('active',value==='rotate');}
$('move').onclick=()=>mode('translate');$('rotate').onclick=()=>mode('rotate');
$('snap').onchange=()=>{gizmo.setTranslationSnap($('snap').checked?5:null);gizmo.setRotationSnap($('snap').checked?radians(5):null);};
gizmo.addEventListener('dragging-changed',event=>{orbit.enabled=!event.value;});
gizmo.addEventListener('mouseDown',()=>{dragStart=JSON.stringify(snapshot());selection.begin();});
gizmo.addEventListener('objectChange',()=>{selection.change();updateFields();markDirty();});
gizmo.addEventListener('mouseUp',()=>{selection.end();commit(dragStart);dragStart=null;});
orbit.addEventListener('start',()=>{if(!busy)dragStart=JSON.stringify(snapshot());});
orbit.addEventListener('change',()=>{if(!busy){updateFields();markDirty();}});
orbit.addEventListener('end',()=>{if(!busy){commit(dragStart);dragStart=null;}});
$('ground').onclick=()=>act(()=>{for(const g of selection.roots()){if(g===groups.table)continue;if(g===groups.status){setNode('status',baseline.objects.status);continue;}scene.updateMatrixWorld(true);const bottom=new THREE.Box3().setFromObject(g).min.y,world=g.getWorldPosition(new THREE.Vector3());world.y+=groups.table.position.y-bottom;g.position.copy(g.parent.worldToLocal(world));}selection.refresh();updateSelection();});
$('focus').onclick=()=>act(()=>{studio.beginCameraEdit();const b=selection.bounds(),center=b.getCenter(new THREE.Vector3()),size=b.getSize(new THREE.Vector3()),offset=camera.position.clone().sub(orbit.target).normalize();studio.applyManualCamera({position:center.clone().addScaledVector(offset,Math.max(size.x,size.y,size.z)/Math.tan(radians(camera.fov)/2)*.85).toArray(),target:center.toArray(),fov:camera.fov});});
$('undo').onclick=()=>{if(!history.length)return;future.push(JSON.stringify(snapshot()));apply(JSON.parse(history.pop()));markDirty();$('transformState').textContent='Undid scene edit.';};
$('redo').onclick=()=>{if(!future.length)return;history.push(JSON.stringify(snapshot()));apply(JSON.parse(future.pop()));markDirty();$('transformState').textContent='Redid scene edit.';};
$('reset').onclick=()=>act(()=>apply(baseline));
$('clean').onclick=()=>{hidden=!hidden;updateSelection();$('clean').textContent=hidden?'Show handles':'Hide handles';};
$('aspect').onchange=()=>{if(!loaded)return;const old=snapshot();old.viewport={width:720,height:camera.aspect<1.4?540:480};const newAspect=$('aspect').value==='4:3'?4/3:1.5;camera.fov=degrees(2*Math.atan(Math.tan(radians(camera.fov)/2)*camera.aspect/newAspect));studio?.aspectChanged(camera.aspect,newAspect);resize();commit(JSON.stringify(old));};
let fovStart=null;for(const id of ['fov','fovNumber']){const input=$(id);input.addEventListener('focus',()=>{if(!loaded)return;studio?.beginCameraEdit();fovStart=JSON.stringify(snapshot());});input.oninput=()=>{if(!loaded)return;const value=Number(input.value);if(!Number.isFinite(value)||value<5||value>110)return;studio.applyManualCamera({position:camera.position.toArray(),target:orbit.target.toArray(),fov:value});updateFields();};input.onchange=()=>{if(loaded)commit(fovStart);fovStart=null;};}
$('cameraApply').onclick=()=>{if(!loaded)return;act(()=>{studio.applyManualCamera({position:inputs.eye.map(input=>Number(input.value)),target:inputs.target.map(input=>Number(input.value)),fov:Number($('fovNumber').value)});updateFields();});};
$('cameraMouse').onclick=()=>{if(loaded)cameraTool(!cameraToolActive);};
$('download').onclick=()=>{const link=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(snapshot(),null,2)+'\n'],{type:'application/json'}));link.href=url;link.download='slot-scene-layout.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('downloadImage').onclick=()=>{$('canvas').toBlob(blob=>{if(!blob)return;const link=document.createElement('a'),url=URL.createObjectURL(blob);link.href=url;link.download=`slot-scene-${system}-${tvKey}.png`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});};
$('reloadSaved').onclick=async()=>{try{const profile=await json('/api/profile'+query),before=JSON.stringify(snapshot()),raw=localStorage.getItem(draftKey);if(raw){const key=draftKey+'-recovery-'+Date.now();localStorage.setItem(key,raw);const digest=async value=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)))).join(',');if(await digest(raw)!==await digest(localStorage.getItem(key)))throw Error('Draft recovery verification failed');}apply(profile);history.push(before);future.length=0;localStorage.removeItem(draftKey);dirty=false;updateFields();$('saveState').textContent='Reloaded saved layout. Previous browser draft retained in local recovery; Undo also restores it.';}catch(error){$('saveState').textContent=error.message;}};
async function saveScene(upload=false){
    const before=JSON.stringify(snapshot()),button=$(upload?'upload':'save');
    try{
        button.disabled=true;manifest.token=(await json('/api/manifest'+query)).token;
        const response=await fetch(upload?'/api/upload':'/api/save',{method:'POST',headers:{'Content-Type':'application/json','X-Scene-Token':manifest.token},body:before});
        const result=await response.json();if(!response.ok)throw Error(result.error);
        if(JSON.stringify(snapshot())===before){dirty=false;localStorage.removeItem(draftKey);$('saveState').textContent='Saved locally.';}
        if(upload)await pollUpload();
    }catch(error){$(upload?'uploadState':'saveState').textContent=error.message;}
    finally{button.disabled=false;}
}
const tvName=key=>key==='oldtv'?'Old TV':key==='pvm'?'PVM':'Panasonic';
function savedTv(name){const saved=manifest?.savedLayouts||[];if(saved.includes(`${name}-${tvKey}`))return tvKey;const other=saved.find(key=>key.startsWith(name+'-'));return other?other.slice(name.length+1):tvKey;}
// Read-only: the layout the device renders for this console/TV becomes the editor's state
// (undoable, kept as a browser draft until saved).
$('importDevice').onclick=async()=>{
    if(!loaded)return;const button=$('importDevice'),state=$('importState');button.disabled=true;state.textContent='Reading the layout on your device…';
    try{
        const response=await fetch('/api/device-layout'+query),result=await response.json();if(!response.ok)throw Error(result.error);
        if(!result.found){
            state.textContent=`Your device has no ${manifest.system.toUpperCase()} · ${tvName(tvKey)} layout.`;
            if(result.layouts.length){state.append(' It has: ');result.layouts.forEach((key,i)=>{const [s,tv]=key.split('-'),link=document.createElement('a');link.href=`?system=${encodeURIComponent(s)}&tv=${encodeURIComponent(tv)}`;link.textContent=`${s.toUpperCase()} · ${tvName(tv)}`;state.append(i?', ':'',link);});}
            return;
        }
        const before=JSON.stringify(snapshot());act(()=>apply({...result.profile,editorView:studio?.active()}));
        if(result.matchesSaved){dirty=false;localStorage.removeItem(draftKey);$('saveState').textContent='Matches your saved layout.';}
        state.textContent=JSON.stringify(snapshot())===before?'The editor already shows the layout on your device.':
            `Imported ${manifest.system.toUpperCase()} · ${tvName(tvKey)} from your device`+(result.matchesSaved?' (same as your saved layout).':'. Save layout to keep it; Undo returns to the previous editor state.');
    }catch(error){state.textContent=error.message;}
    finally{button.disabled=false;}
};
async function post(url,body){
    manifest.token=(await json('/api/manifest'+query)).token;
    const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-Scene-Token':manifest.token},body:JSON.stringify(body)});
    const result=await response.json();if(!response.ok)throw Error(result.error);return result;
}
const pairName=key=>{if(key==='room')return 'Room · table positions & travel';const [s,tv]=key.split('-');return `${s==='home'?'Home table':s.toUpperCase()} · ${tvName(tv)}`;},currentKey=`${system}-${tvKey}`;
async function exportGroup(group){
    if(!loaded)return;const state=$('exportState'),label=group==='tv'?'TV consoles':'handheld consoles',upload=$('exportUpload').checked;
    try{
        const targets=(await json(`/api/export-plan${query}&group=${group}`)).targets;
        const list=targets.map(t=>t.system.toUpperCase()+(t.current?' (this layout)':t.saved?' (replaces its saved layout)':'')).join('\n');
        const then=upload?`\n\nThen upload all of them to your device in one transaction and open ${targets.some(t=>t.current)?pairName(currentKey):'normal startup'} afterwards.`:'';
        if(!confirm(`Save this ${manifest.system.toUpperCase()} layout with the ${tvName(tvKey)} for all ${label}?\n\n${list}\n\nReplaced layouts keep their previous version in scene-layouts/history.${then}`))return;
        const before=JSON.stringify(snapshot());
        // "…and upload": the server saves and starts one batch under its upload lock, so a
        // rejected upload (one already running) saves nothing.
        const result=await post('/api/export',{group,profile:JSON.parse(before),upload,open:targets.some(t=>t.current)?currentKey:'normal'});
        for(const item of result.results){const key=`${item.system}-${tvKey}`;if(!manifest.savedLayouts.includes(key))manifest.savedLayouts.push(key);}
        if(result.results.some(item=>item.current)&&JSON.stringify(snapshot())===before){dirty=false;localStorage.removeItem(draftKey);$('saveState').textContent='Saved locally.';}
        state.textContent=`Saved with the ${tvName(tvKey)} for ${result.results.map(item=>item.system.toUpperCase()+(item.replaced&&!item.current?' (previous kept in history)':'')).join(', ')}. `+(upload?'Uploading them in one transaction; progress is at the top right.':'Pick a console above to fine-tune it, then Upload to device.');
        if(upload)await pollUpload();
    }catch(error){state.textContent=error.message;}
}
$('exportUpload').onchange=()=>{const suffix=$('exportUpload').checked?' and upload':'';$('exportTv').textContent='Save for all TV consoles'+suffix;$('exportHandheld').textContent='Save for all handheld consoles'+suffix;};
$('exportTv').onclick=()=>exportGroup('tv');$('exportHandheld').onclick=()=>exportGroup('handheld');
// Per-file progress of the running/last upload, as reported by the host and device workers.
const fileStates={checking:'checking',same:'already on device',queued:'to send',sent:'sent',received:'received',installed:'installed',verified:'verified',mismatch:'MISMATCH',restored:'rolled back',removed:'rolled back (removed)','rollback failed':'ROLLBACK FAILED'};
function progressSummary(items){const counts={};for(const item of items)counts[item.state]=(counts[item.state]||0)+1;return Object.entries(counts).map(([key,n])=>`${n} ${fileStates[key]||key}`).join(' · ');}
function showProgress(state){
    const items=state.progress||[],list=$('uploadFiles');list.hidden=!items.length;
    if(list.dataset.session!==state.session||list.children.length!==items.length){list.dataset.session=state.session||'';list.replaceChildren(...items.map(item=>{const row=document.createElement('div'),name=document.createElement('span'),chip=document.createElement('b');name.textContent=item.name.replace(/^_slot\//,'');name.title=`${item.name} · ${item.bytes} bytes`;row.append(name,chip);return row;}));}
    items.forEach((item,i)=>{const chip=list.children[i].lastChild;chip.textContent=fileStates[item.state]||item.state;chip.dataset.state=item.state;});
    const running=state.state==='running',layouts=running&&state.layouts?.length>1?`${state.layouts.length} layouts: `:'',last=running?'':'Last upload: ';
    $('uploadSummary').textContent=state.state==='idle'?'':`${last}${layouts}${state.message}${items.length?' — '+progressSummary(items):''}`;$('uploadSummary').dataset.state=state.state;
}
let polling=null;
function pollUpload(){
    polling??=(async()=>{
        for(const id of ['upload','uploadMany'])$(id).disabled=true;$('upload').textContent='Uploading…';$('uploadStart').disabled=true;
        try{
            for(;;){
                const state=await json('/api/upload'),items=state.progress||[];
                $('uploadState').textContent=state.message+(items.length&&state.state==='running'?' ('+progressSummary(items)+')':'')+(state.state==='complete'?' Snapshot: '+state.session:'');
                $('uploadState').dataset.state=state.state;showProgress(state);
                if(state.state!=='running')return;
                await new Promise(resolve=>setTimeout(resolve,1000));
            }
        }finally{polling=null;$('upload').disabled=!loaded;$('uploadMany').disabled=false;$('upload').textContent='Upload to device';updateUploadStart();}
    })();
    return polling;
}
// Upload…: every saved layout against ONE read of the device's layout hashes.
let uploadPlan=null;
const rowStates={same:'Same as device',changed:'Changed',missing:'Not on device',unknown:'Device not read',error:'Cannot read'};
function rowStatus(row){const device=uploadPlan?.device;if(row.error)return 'error';if(!device||device.error)return 'unknown';const value=device.layouts[row.key];return !value?'missing':value.sha256===row.sha256?'same':'changed';}
function pickRows(container,predicate){for(const box of container.querySelectorAll('input[type=checkbox]'))if(!box.disabled)box.checked=predicate(box);}
function checkedKeys(container){return [...container.querySelectorAll('input[type=checkbox]:checked')].map(box=>box.value);}
function updateUploadStart(){const n=checkedKeys($('uploadRows')).length;$('uploadStart').textContent=n?`Upload ${n} layout${n===1?'':'s'}`:'Upload';$('uploadStart').disabled=!n||!!polling;}
function renderUploadPlan(previous){
    const rows=$('uploadRows'),device=uploadPlan.device;rows.replaceChildren();
    for(const row of uploadPlan.layouts){
        const status=rowStatus(row),label=document.createElement('label'),box=document.createElement('input'),name=document.createElement('span'),chip=document.createElement('b');
        box.type='checkbox';box.value=row.key;box.disabled=status==='error';box.dataset.status=status;
        // Changed rows start ticked; a refresh keeps the user's ticks and ticks rows that became changed.
        box.checked=previous?(previous.ticked.has(row.key)||(status==='changed'&&previous.status[row.key]!=='changed')):status==='changed';
        box.onchange=updateUploadStart;name.textContent=pairName(row.key)+(row.key===currentKey?' (open here)':'');chip.textContent=rowStates[status];chip.dataset.status=status;if(row.error)chip.title=row.error;
        label.append(box,name,chip);rows.append(label);
    }
    if(!uploadPlan.layouts.length)rows.textContent='No saved layouts yet. Save layout first.';
    const notes=[];
    if(!device)notes.push('Reading the layouts on your device…');
    else if(device.error)notes.push(device.error+' Statuses are unknown; ticked layouts still go through the full upload checks.');
    else{
        notes.push(`Device has ${Object.keys(device.layouts).length} layouts.`);
        if(device.themeSet&&device.themeSet!==uploadPlan.theme)notes.push(`Its theme is ${device.themeSet}; select ${uploadPlan.theme} before uploading.`);
        if(device.gameRunning)notes.push('A game is running: close it first (upload refuses while a game runs).');
        if(device.frontend===false)notes.push('The frontend is not running: start it first.');
    }
    $('uploadDevice').textContent=notes.join(' ');
    const open=$('uploadOpen'),chosen=open.value;open.replaceChildren();
    for(const [value,text] of [['normal','Normal startup (Slotted starts at home)'],...uploadPlan.layouts.filter(row=>!row.kind).map(row=>[row.key,pairName(row.key)])]){const option=document.createElement('option');option.value=value;option.textContent=text;open.append(option);}
    open.value=[...open.options].some(o=>o.value===chosen)&&chosen?chosen:uploadPlan.layouts.some(row=>row.key===currentKey)?currentKey:'normal';
    $('uploadDraft').hidden=!dirty;updateUploadStart();
}
async function refreshUploadPlan(readDevice){
    const rows=$('uploadRows'),previous=uploadPlan&&{ticked:new Set(checkedKeys(rows)),status:Object.fromEntries([...rows.querySelectorAll('input')].map(box=>[box.value,box.dataset.status]))};
    const plan=await json('/api/upload-plan'+(readDevice?'':'?local=1'));if(!readDevice)plan.device=uploadPlan?.device;
    uploadPlan=plan;renderUploadPlan(readDevice?null:previous);
}
$('uploadMany').onclick=async()=>{
    uploadPlan=null;$('uploadRows').replaceChildren();$('uploadDevice').textContent='Reading the layouts on your device…';$('uploadDraft').hidden=!dirty;updateUploadStart();
    $('uploadDialog').showModal();showProgress(await json('/api/upload'));
    try{const plan=await json('/api/upload-plan?local=1');uploadPlan=plan;renderUploadPlan();await refreshUploadPlan(true);}catch(error){$('uploadDevice').textContent=error.message;}
};
for(const button of document.querySelectorAll('#uploadDialog [data-pick]'))button.onclick=()=>{const pick=button.dataset.pick;pickRows($('uploadRows'),box=>pick==='all'||(pick==='changed'&&box.dataset.status==='changed')||(pick==='differs'&&['changed','missing'].includes(box.dataset.status)));updateUploadStart();};
$('uploadSaveFirst').onclick=async()=>{await saveScene();try{await refreshUploadPlan(false);}catch(error){$('uploadDevice').textContent=error.message;}};
$('uploadStart').onclick=async()=>{
    const keys=checkedKeys($('uploadRows'));if(!keys.length||polling)return;
    const expect=Object.fromEntries(uploadPlan.layouts.filter(row=>keys.includes(row.key)).map(row=>[row.key,row.sha256]));
    try{$('uploadStart').disabled=true;await post('/api/upload-batch',{layouts:keys,open:$('uploadOpen').value,expect});await pollUpload();}
    catch(error){$('uploadSummary').textContent=error.message;$('uploadSummary').dataset.state='failed';}
    finally{updateUploadStart();}
};
// Import all from device: device layouts that differ from the saved ones become undoable
// drafts (this layout through Undo; others as their drafts, with an undo record read when
// they open). Only one read of the device; nothing there changes.
const draftKeyFor=(s,tv)=>{const original=s==='snes'?'slot-scene-draft':`slot-scene-draft-${s}`;return tv==='panasonic'?original:`${original}-${tv}`;};
let importPlan=null;
const importStates={differs:'Differs from saved','not saved':'Not saved here',unreadable:'Cannot read',unsupported:'Not an editor layout'};
$('importAll').onclick=async()=>{
    if(!loaded)return;const rows=$('importRows');rows.replaceChildren();$('importSummary').textContent='';updateImportStart();
    $('importDeviceState').textContent='Reading every layout on your device…';$('importDialog').showModal();
    try{
        const response=await fetch('/api/device-import');importPlan=await response.json();if(!response.ok)throw Error(importPlan.error);
        const differing=importPlan.layouts.filter(row=>row.status!=='same');
        for(const row of differing){
            const label=document.createElement('label'),box=document.createElement('input'),name=document.createElement('span'),chip=document.createElement('b'),draft=row.system&&localStorage.getItem(draftKeyFor(row.system,row.tv));
            box.type='checkbox';box.value=row.key;box.disabled=!row.profile;box.checked=!!row.profile;box.onchange=updateImportStart;
            name.textContent=(row.system?pairName(row.key):row.key)+(row.key===currentKey?' (open here)':draft?' · your draft goes to recovery':'');
            chip.textContent=importStates[row.status]||row.status;chip.dataset.status=row.status;if(row.error)chip.title=row.error;label.append(box,name,chip);rows.append(label);
        }
        const same=importPlan.layouts.length-differing.length;
        $('importDeviceState').textContent=`Device has ${importPlan.layouts.length} layouts; ${same} match your saved ones`+(differing.length?'.':' — nothing to import.');
        updateImportStart();
    }catch(error){$('importDeviceState').textContent=error.message;}
};
function updateImportStart(){const n=checkedKeys($('importRows')).length;$('importStart').textContent=n?`Import ${n} layout${n===1?'':'s'}`:'Import';$('importStart').disabled=!n;}
function importDraft(row){
    if(row.system===manifest.system&&row.tv===tvKey){act(()=>apply({...row.profile,editorView:studio?.active()}));return;}
    const key=draftKeyFor(row.system,row.tv),previous=localStorage.getItem(key),value=JSON.stringify(row.profile);
    if(previous){const backup=`${key}-recovery-${Date.now()}`;localStorage.setItem(backup,previous);if(localStorage.getItem(backup)!==previous)throw Error('Draft recovery verification failed');}
    localStorage.setItem(`${key}-import-undo`,JSON.stringify({draft:value,before:previous}));localStorage.setItem(key,value);
}
$('importStart').onclick=()=>{
    const keys=checkedKeys($('importRows')),done=[];
    try{for(const row of importPlan.layouts.filter(row=>keys.includes(row.key))){importDraft(row);done.push(row);}}
    catch(error){$('importSummary').textContent=error.message;return;}
    $('importSummary').textContent='';$('importDialog').close();
    const links=done.filter(row=>row.key!==currentKey),state=$('importState');
    state.textContent=`Imported ${done.length} layout${done.length===1?' from your device as an unsaved draft':'s from your device as unsaved drafts'}`+(done.some(row=>row.key===currentKey)?'; this one is in the editor now (Undo returns)':'')+'. Save layout on each to keep it.';
    if(links.length){state.append(' Open: ');links.forEach((row,i)=>{const link=document.createElement('a');link.href=`?system=${encodeURIComponent(row.system)}&tv=${encodeURIComponent(row.tv)}`;link.textContent=pairName(row.key);state.append(i?', ':'',link);});}
};
$('save').onclick=()=>saveScene();
$('upload').onclick=()=>saveScene(true);
window.addEventListener('keydown',event=>{if(!loaded||/INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName)||document.querySelector('dialog[open]'))return;if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='z'){event.preventDefault();$(event.shiftKey?'redo':'undo').click();}else if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'){event.preventDefault();$('save').click();}else if(event.key.toLowerCase()==='w')mode('translate');else if(event.key.toLowerCase()==='e')mode('rotate');else if(event.key.toLowerCase()==='f')$('focus').click();});
const raycaster=new THREE.Raycaster();let pointerStart;
renderer.domElement.addEventListener('pointerdown',event=>{pointerStart=[event.clientX,event.clientY,gizmo.axis];});
renderer.domElement.addEventListener('pointerup',event=>{if(!loaded||cameraToolActive||!pointerStart||pointerStart[2]||Math.hypot(event.clientX-pointerStart[0],event.clientY-pointerStart[1])>4)return;const rect=renderer.domElement.getBoundingClientRect();raycaster.setFromCamera(new THREE.Vector2((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1),camera);const hits=raycaster.intersectObjects(names.map(name=>groups[name]),true).filter(hit=>{for(let object=hit.object;object;object=object.parent)if(!object.visible)return false;return true;});if(hits.length){let object=hits[0].object;while(object&&!object.userData.node)object=object.parent;if(object)select(object.userData.node,event.shiftKey||event.ctrlKey||event.metaKey||$('multiSelect').checked);}});
function resize(){const stage=$('stage'),aspect=$('aspect').value==='4:3'?4/3:1.5,w=Math.max(100,stage.clientWidth-44),h=Math.max(100,stage.clientHeight-44);let width=w,height=w/aspect;if(height>h){height=h;width=h*aspect;}$('viewport').style.width=width+'px';$('viewport').style.height=height+'px';renderer.setSize(width,height);camera.aspect=aspect;camera.updateProjectionMatrix();}
new ResizeObserver(resize).observe($('stage'));
// As on the device, the near plane stops just in front of the closest geometry in view, so a
// close camera never slices carts open (gizmo excluded).
function fitNear(){
    scene.updateMatrixWorld();camera.updateMatrixWorld();const range=depthRange(),view=camera.matrixWorldInverse.elements,tanY=Math.tan(radians(camera.fov)/2)*1.01,tanX=tanY*camera.aspect,helper=gizmo.getHelper();
    for(const child of scene.children)if(child!==helper)child.traverseVisible(object=>{if(!object.isMesh)return;const g=object.geometry;if(!g.boundingBox)g.computeBoundingBox();boxDepth(range,view,object.matrixWorld.elements,g.boundingBox.min.toArray(),g.boundingBox.max.toArray(),tanX,tanY);});
    const near=hugNear(range);if(near!==camera.near){camera.near=near;camera.updateProjectionMatrix();}
}
renderer.setAnimationLoop(now=>{studio?.tick(now);if(loaded)fitNear();renderer.render(scene,camera);});
try{
    [manifest,baseline]=await Promise.all([json('/api/manifest'+query),json('/api/default'+query)]);const saved=await json('/api/profile'+query);
    groups.all=new THREE.Group();groups.all.rotation.order='YXZ';scene.add(groups.all);
    for(const name of names){groups[name]=new THREE.Group();groups[name].rotation.order='YXZ';groups[name].userData.node=name;if(name!=='status')scene.add(groups[name]);}groups.tv.add(groups.status);
    selection=createTransformSelection(THREE,scene,groups);
    const media=manifest.media;
    const disc=media.disc?discGeometry(media.disc,media.units):null;
    const [table,tv,consoleMesh,shellMesh,labelMesh]=await Promise.all([prepared('table'),prepared(manifest.tv),mesh(manifest.console),media.shell?mesh(media.shell):null,media.label?mesh(media.label):null]);
    const cart=disc?new THREE.Mesh(disc.shell,material()):shellMesh;
    groups.table.add(table.group);groups.tv.add(tv.group);consoleMesh.rotation.set(...manifest.tableRotation.map(radians),'YXZ');groups.console.add(consoleMesh);groups.console.scale.setScalar(1/manifest.consoleUnits);
    for(let i=0;i<cartridgeCount;i++){
        // Own shell material per cart, so one cart can fade in front of the selected one.
        const shell=cart.clone();shell.material=cart.material.clone();groups[`cart${i}`].scale.setScalar(1/media.units);groups[`cart${i}`].add(shell);const face=await texture(`${manifest.faces}${i}.png`);
        let label;if(disc)label=new THREE.Mesh(disc.label,material(face,true,media.crop));
        else if(labelMesh){label=labelMesh.clone();label.material=material(face,true,media.crop);}else label=labelQuad(media.quad,media.units,face,media.crop);
        label.material.uniforms.cutout.value=media.cutout?1:0;label.material.polygonOffset=true;label.material.polygonOffsetFactor=-1;label.material.polygonOffsetUnits=-1;groups[`cart${i}`].add(label);
    }
    const picker=$('system');for(const name of manifest.systems){const option=document.createElement('option');option.value=name;option.textContent=name.toUpperCase();picker.append(option);}
    // Switching console keeps the TV when that pair is saved, else opens the console's saved TV.
    picker.value=manifest.system;picker.onchange=()=>{const next=picker.value,tv=savedTv(next);location.search=`?system=${encodeURIComponent(next)}&tv=${encodeURIComponent(tv)}`;};
    const tvPicker=$('tvModel');for(const key of manifest.tvs){const option=document.createElement('option');option.value=key;option.textContent=key==='oldtv'?'Old TV \u00b7 14 inch':key==='pvm'?'PVM \u00b7 13 inch':'Panasonic';tvPicker.append(option);}tvPicker.value=manifest.tv;tvPicker.onchange=()=>{location.search=`?system=${encodeURIComponent(system)}&tv=${encodeURIComponent(tvPicker.value)}`;};
    labels.console=`Console · ${manifest.system.toUpperCase()}`;document.title=`Slot scene studio · ${manifest.system.toUpperCase()}`;
    groups.status.add(voxels());const width=tv.info.bounds[1][0]-tv.info.bounds[0][0];groups.status.scale.setScalar(Math.min(1,width/468));
    studio=createStudioControls({scene,camera,orbit,groups,renderer,prepared,manifest,act,markDirty,updateFields,setBusy:value=>{busy=value;},material,onModelDrag:()=>cameraTool(false)});
    let initial=saved;try{const draft=JSON.parse(localStorage.getItem(draftKey));if(draft?.version===1&&(draft.system||'snes')===manifest.system&&draft.objects&&names.slice(0,12).every(name=>draft.objects[name])){initial={...draft,objects:{...saved.objects,...draft.objects}};dirty=true;const backupKey=draftKey+'-before-multiview';if(!localStorage.getItem(backupKey))localStorage.setItem(backupKey,JSON.stringify(draft));}}catch{}
    for(const button of $('objects').children)button.textContent=labels[button.dataset.name];
    for(const id of ['swapFirst','swapSecond'])for(const option of $(id).options)option.textContent=labels[option.value];
    loaded=true;apply(initial);select('tv');$('loading').style.display='none';
    // A layout imported from the device (Import all) opens as this pair's draft; Undo returns
    // to the draft or saved layout it replaced. Any later edit makes the record stale.
    let imported=false;try{const record=JSON.parse(localStorage.getItem(draftKey+'-import-undo'));if(record){if(dirty&&record.draft===localStorage.getItem(draftKey)){const before=record.before&&JSON.parse(record.before);history.push(JSON.stringify(before?.objects?{...before,objects:{...saved.objects,...before.objects}}:saved));imported=true;updateFields();}else localStorage.removeItem(draftKey+'-import-undo');}}catch{}
    $('saveState').textContent=imported?'Imported from your device as an unsaved draft. Save layout keeps it; Undo returns to the previous layout.':dirty?'Restored your unsaved browser draft.':manifest.saved||manifest.system==='snes'?'Ready · source models at their physical scale':`Starting from your SNES layout · save to give ${manifest.system.toUpperCase()} its own`;
    if(!manifest.saved&&savedTv(manifest.system)!==tvKey){const tv=savedTv(manifest.system),link=document.createElement('a');link.href=`?system=${encodeURIComponent(manifest.system)}&tv=${encodeURIComponent(tv)}`;link.textContent=`Open your saved ${manifest.system.toUpperCase()} layout (${tvName(tv)})`;$('saveState').append(' · ',link);}
    pollUpload().catch(error=>{$('uploadState').textContent=error.message;});
    // Read-only diagnostic bridge used by the editor's browser verification.
    window.slotSceneStudio={snapshot:()=>clone(snapshot()),ready:true,camera:()=>({position:camera.position.toArray(),target:orbit.target.toArray(),fov:camera.fov,near:camera.near}),selection:()=>selection.names(),transitioning:()=>studio.transitioning(),triangles:()=>renderer.info.render.triangles};
}catch(error){$('loading').textContent=error.message;$('saveState').textContent=error.message;console.error(error);}
