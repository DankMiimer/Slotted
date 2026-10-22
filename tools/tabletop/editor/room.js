import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {TransformControls} from 'three/addons/controls/TransformControls.js';
import {json,material,mesh,prepared,voxels} from './source-models.js';
const $=id=>document.getElementById(id),copy=v=>JSON.parse(JSON.stringify(v)),rad=v=>v*Math.PI/180,deg=v=>v*180/Math.PI;
const query=new URLSearchParams(location.search),kind=query.get('scene')==='home'?'home':'room',tv=query.get('tv')||'panasonic',draftKey=`slotted-studio-v1-${kind}-${kind==='home'?tv:'world'}`;
$('sceneType').value=kind;$('television').value=tv;$('homeOptions').hidden=kind!=='home';$('addPath').hidden=$('previewPath').hidden=kind!=='room';
$('regionalOptions').hidden=kind!=='home';
$('sceneType').onchange=()=>location.search=`?scene=${$('sceneType').value}&tv=${tv}`;$('television').onchange=()=>location.search=`?scene=home&tv=${$('television').value}`;
$('hint').textContent=kind==='room'?'Each table model has one permanent place. Heights put its feet on the floor. Travel controls are offsets from a straight flight; they do not change console layouts.':'Arrange every console and the TV. Status coordinates stay relative to the TV. Switch camera views to author the overview and the whole-TV screen view separately.';
const scene=new THREE.Scene();scene.background=new THREE.Color(.025,.030,.040);
const renderer=new THREE.WebGLRenderer({canvas:$('canvas'),antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.LinearSRGBColorSpace;
const camera=new THREE.PerspectiveCamera(40,1.5,10,30000),orbit=new OrbitControls(camera,renderer.domElement);orbit.minDistance=30;orbit.maxDistance=26000;
const gizmo=new TransformControls(camera,renderer.domElement);gizmo.setSize(.8);scene.add(gizmo.getHelper());
const content=new THREE.Group();scene.add(content);let groups={},profile,manifest,saved,baseSha=null,history=[],future=[],selected='',applying=false,loading=true,hidden=false,dragging=false,flight=null;
const preparedCache=new Map(),consoleCache=new Map();
async function sourceTable(key){if(!preparedCache.has(key))preparedCache.set(key,prepared(key));return (await preparedCache.get(key)).group.clone(true);}
async function sourceConsole(key){
    const spec=manifest.consoles[key];if(!consoleCache.has(key))consoleCache.set(key,mesh(spec.console));
    const body=(await consoleCache.get(key)).clone(),group=new THREE.Group();body.rotation.set(...spec.tableRotation.map(rad),'YXZ');group.scale.setScalar(1/spec.consoleUnits);group.add(body);return group;
}
function placement(group,value){group.position.fromArray(value.position);group.rotation.set(...value.rotation.map(rad),'YXZ');}
function atPath(path){return path.reduce((v,key)=>v[key],profile);}
function entry(name){if(kind==='room')return profile.tables[name];return profile.objects[name]||profile.consoles[name];}
function draft(){try{localStorage.setItem(draftKey,JSON.stringify({profile,baseSha,history,future,time:Date.now()}));}catch{$('state').textContent='Browser draft storage is full. Export JSON to keep these edits.';}}
function checkpoint(){history.push(JSON.stringify(profile));if(history.length>100)history.shift();future=[];}
function changed(message='Unsaved changes · browser draft retained'){draft();$('state').textContent=message;}
function applyCamera(){
    if(kind!=='home')return;applying=true;const value=profile[$('view').value]||profile.camera;camera.position.fromArray(value.position);orbit.target.fromArray(value.target);camera.fov=value.fov;camera.updateProjectionMatrix();orbit.update();applying=false;
}
function captureCamera(){profile[$('view').value]={position:camera.position.toArray(),target:orbit.target.toArray(),fov:camera.fov};}
function frameCamera(){
    const target=kind==='home'&&$('view').value==='screen'?groups.tv:content;gizmo.detach();scene.updateMatrixWorld(true);const box=new THREE.Box3().setFromObject(target),center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3());
    const forward=kind==='home'&&$('view').value==='screen'?new THREE.Vector3(0,0,1).applyQuaternion(groups.tv.quaternion).add(new THREE.Vector3(0,.22,0)).normalize():new THREE.Vector3(.12,.45,1).normalize();
    const fov=40,tanY=Math.tan(rad(fov)/2)*.9,tanX=tanY*camera.aspect;
    const right=new THREE.Vector3().crossVectors(new THREE.Vector3(0,1,0),forward).normalize(),up=new THREE.Vector3().crossVectors(forward,right).normalize();
    let distance=50,positiveX=-Infinity,negativeX=-Infinity,positiveY=-Infinity,negativeY=-Infinity;
    // Include depth toward the lens. A width/height-only fit clips the cabinet
    // and its status on a deep CRT, even when their combined bounds are used.
    for(let k=0;k<8;k++){
        const point=new THREE.Vector3(k&1?box.max.x:box.min.x,k&2?box.max.y:box.min.y,k&4?box.max.z:box.min.z).sub(center);
        const depth=point.dot(forward);distance=Math.max(distance,depth+20);
        positiveX=Math.max(positiveX,depth+point.dot(right)/tanX);negativeX=Math.max(negativeX,depth-point.dot(right)/tanX);
        positiveY=Math.max(positiveY,depth+point.dot(up)/tanY);negativeY=Math.max(negativeY,depth-point.dot(up)/tanY);
    }
    center.addScaledVector(right,(positiveX-negativeX)*tanX/2).addScaledVector(up,(positiveY-negativeY)*tanY/2);
    distance=Math.max(distance,(positiveX+negativeX)/2+20,(positiveY+negativeY)/2+20);
    applying=true;orbit.target.copy(center);camera.position.copy(center).addScaledVector(forward,distance);camera.fov=fov;camera.updateProjectionMatrix();orbit.update();applying=false;
    if(kind==='home')captureCamera();select(selected);
}
function select(name){selected=name;if(groups[name]&&!hidden){gizmo.attach(groups[name]);gizmo.enabled=true;gizmo.showX=gizmo.showZ=!(kind==='room'&&gizmo.getMode()==='rotate');}else{gizmo.detach();gizmo.enabled=false;}$('selection').textContent=name?` · ${name}`:'';for(const button of $('objects').children)button.classList.toggle('active',button.dataset.name===name);}
function redrawPaths(){
    const old=content.getObjectByName('travel-paths');if(old){content.remove(old);old.traverse(n=>{n.geometry?.dispose();n.material?.dispose();});}
    if(kind!=='room')return;const paths=new THREE.Group();paths.name='travel-paths';content.add(paths);
    for(const path of profile.paths){
        const a=new THREE.Vector3(...profile.tables[path.from].position).add(new THREE.Vector3(0,100,0)),b=new THREE.Vector3(...profile.tables[path.to].position).add(new THREE.Vector3(0,100,0));
        const curve=new THREE.CubicBezierCurve3(a,a.clone().lerp(b,1/3).add(new THREE.Vector3(...path.first)),a.clone().lerp(b,2/3).add(new THREE.Vector3(...path.second)),b);
        const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(curve.getPoints(64)),new THREE.LineBasicMaterial({color:0xffd77b}));line.userData.curve=curve;line.userData.previewOwned=true;paths.add(line);
    }
}
async function rebuild(){
    loading=true;gizmo.detach();content.traverse(node=>{if(node.userData.previewOwned){node.geometry?.dispose();node.material?.dispose();}});content.clear();groups={};
    const add=(name,body,value,parent=content)=>{const node=new THREE.Group();node.rotation.order='YXZ';node.userData.node=name;node.add(body);parent.add(node);groups[name]=node;placement(node,value);return node;};
    if(kind==='room'){
        for(const [name,value] of Object.entries(profile.tables)){const body=await sourceTable(name);body.scale.setScalar(name==='wooden-table'?.7:1);add(name,body,value);}
        await redrawSurfaces();redrawPaths();
    }else{
        const table=await sourceTable(profile.table.model);table.scale.fromArray(profile.table.scale);add('table',table,profile.objects.table);
        add('tv',await sourceTable(tv),profile.objects.tv);
        const status=voxels(manifest.consoles.snes),tvInfo=await preparedCache.get(tv),width=tvInfo.info.bounds[1][0]-tvInfo.info.bounds[0][0];status.userData.previewOwned=true;status.scale.setScalar(Math.min(1,width/468));add('status',status,profile.objects.status,groups.tv);
        const names=Object.keys(profile.consoles),bodies=await Promise.all(names.map(sourceConsole));names.forEach((name,i)=>add(name,bodies[i],profile.consoles[name]));
    }
    $('objects').replaceChildren();for(const name of Object.keys(groups)){const button=document.createElement('button');button.textContent=name;button.dataset.name=name;button.onclick=()=>{select(name);fields();};$('objects').append(button);}
    loading=false;$('loading').style.display='none';select(selected);fields();resize();if(kind==='home')applyCamera();
}
// Room surfaces: the device's tile grid (SlotRoomWorld.inc roomSurfaces). Each quad spans one
// texture repeat with 0..1 UVs, as the shared shader clamps UVs; textures are tinted on the CPU.
const SURFACES=['floor','wall','ceiling'],SURFACE_NAMES={floor:'Floor',wall:'Walls',ceiling:'Ceiling'},PLAIN={floor:[.20,.22,.24],wall:[.38,.40,.42],ceiling:[.80,.80,.78]};
function surfaceFaces(){
    const b=profile.bounds,y=profile.floor,h=y+b.height,w=b.right-b.left,d=b.front-b.back;
    return {floor:[{origin:[b.left,y,b.back],u:[w,0,0],v:[0,0,d],normal:[0,1,0],color:[.20,.22,.24]}],
        wall:[{origin:[b.left,h,b.back],u:[w,0,0],v:[0,-b.height,0],normal:[0,0,1],color:[.38,.40,.42]},{origin:[b.left,h,b.front],u:[0,0,-d],v:[0,-b.height,0],normal:[1,0,0],color:[.34,.36,.38]},{origin:[b.right,h,b.back],u:[0,0,d],v:[0,-b.height,0],normal:[-1,0,0],color:[.34,.36,.38]}],
        ceiling:[{origin:[b.left,h,b.back],u:[w,0,0],v:[0,0,d],normal:[0,-1,0],color:[.34,.36,.38]}]};
}
let surfaceLibrary=[],surfaceGeneration=0;const surfaceTextures=new Map();
function tintedTexture(name,tint){
    const key=name+'|'+tint.join(',');
    if(!surfaceTextures.has(key))surfaceTextures.set(key,new Promise((ok,fail)=>{const image=new Image();image.onload=()=>ok(image);image.onerror=()=>fail(Error(`Cannot load texture ${name}`));image.src=`/assets/surfaces/${name}.png`;}).then(image=>{
        const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;const g=canvas.getContext('2d');g.drawImage(image,0,0);
        if(tint.some(c=>c!==1)){const data=g.getImageData(0,0,canvas.width,canvas.height);for(let i=0;i<data.data.length;i+=4)for(let c=0;c<3;c++)data.data[i+c]=Math.round(data.data[i+c]*tint[c]);g.putImageData(data,0,0);}
        const texture=new THREE.CanvasTexture(canvas);texture.flipY=false;texture.colorSpace=THREE.NoColorSpace;texture.anisotropy=4;texture.needsUpdate=true;return texture;
    }).catch(e=>{surfaceTextures.delete(key);throw e;}));
    return surfaceTextures.get(key);
}
async function surfaceMesh(faces,surface){
    let map=null;if(surface?.texture){try{map=await tintedTexture(surface.texture,surface.color);}catch(e){$('state').textContent=e.message;}}
    const length=v=>Math.hypot(...v);let tile=map?surface.tile:1e9;
    const quads=()=>faces.reduce((n,f)=>n+Math.ceil(length(f.u)/tile)*Math.ceil(length(f.v)/tile),0);while(quads()*4>60000)tile*=1.25;
    const position=[],normal=[],color=[],uv=[],index=[];
    for(const f of faces){
        const c=surface&&!surface.texture?surface.color:f.color,lu=length(f.u),lv=length(f.v);
        for(let i=0;i<Math.ceil(lu/tile);i++)for(let j=0;j<Math.ceil(lv/tile);j++){
            const u0=i*tile/lu,u1=Math.min(1,(i+1)*tile/lu),v0=j*tile/lv,v1=Math.min(1,(j+1)*tile/lv),right=map?(u1-u0)*lu/tile:0,bottom=map?(v1-v0)*lv/tile:0,first=position.length/3;
            for(const [a,b,s,t]of [[u0,v0,0,0],[u1,v0,right,0],[u1,v1,right,bottom],[u0,v1,0,bottom]]){for(let k=0;k<3;k++)position.push(f.origin[k]+f.u[k]*a+f.v[k]*b);normal.push(...f.normal);color.push(...c);uv.push(s,t);}
            index.push(first,first+1,first+2,first,first+2,first+3);
        }
    }
    const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(position,3));geometry.setAttribute('normal',new THREE.Float32BufferAttribute(normal,3));
    geometry.setAttribute('color',new THREE.Float32BufferAttribute(color,3));geometry.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));geometry.setIndex(index);
    return new THREE.Mesh(geometry,material(map));
}
async function redrawSurfaces(){
    if(kind!=='room')return;const generation=++surfaceGeneration,group=new THREE.Group();group.name='room-surfaces';
    const faces=surfaceFaces(),surfaces=profile.surfaces||{};
    for(const key of SURFACES){
        if(key==='ceiling'&&!surfaces.ceiling)continue;
        const body=await surfaceMesh(faces[key],surfaces[key]);body.userData.previewOwned=true;
        // The ceiling shows from inside only, so the orbit camera can still look in from above.
        if(key==='ceiling')body.material.side=THREE.FrontSide;
        group.add(body);
    }
    if(generation!==surfaceGeneration){group.traverse(n=>{n.geometry?.dispose();n.material?.dispose();});return;}
    const old=content.getObjectByName('room-surfaces');if(old){content.remove(old);old.traverse(n=>{n.geometry?.dispose();n.material?.dispose();});}
    content.add(group);
}
const hex=c=>'#'+c.map(v=>Math.round(Math.min(1,Math.max(0,v))*255).toString(16).padStart(2,'0')).join(''),rgb=h=>[1,3,5].map(i=>Math.round(parseInt(h.slice(i,i+2),16)/255*1000)/1000);
function surfaceFields(root){
    const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Room surfaces';details.open=true;details.append(summary);
    for(const key of SURFACES){
        const current=profile.surfaces?.[key],line=document.createElement('label'),select=document.createElement('select');line.textContent=SURFACE_NAMES[key];
        const option=(value,text,parent=select)=>{const o=document.createElement('option');o.value=value;o.textContent=text;parent.append(o);};
        option('',key==='ceiling'?'No ceiling':'Original colour');option('plain','Plain colour');
        for(const [title,own]of [['Built-in textures',false],['Your textures',true]]){const group=document.createElement('optgroup');group.label=title;for(const t of surfaceLibrary.filter(t=>t.own===own))option(t.name,t.label,group);if(group.children.length)select.append(group);}
        select.value=current?(current.texture||'plain'):'';select.setAttribute('aria-label',SURFACE_NAMES[key]+' surface');
        select.onchange=()=>{
            checkpoint();const value=select.value,next={...(profile.surfaces||{})};
            if(!value)delete next[key];
            else if(value==='plain')next[key]={color:current&&!current.texture?current.color:PLAIN[key],tile:1000};
            else next[key]={color:current?.texture?current.color:[1,1,1],tile:surfaceLibrary.find(t=>t.name===value)?.tile||1000,texture:value};
            if(Object.keys(next).length)profile.surfaces=next;else delete profile.surfaces;
            redrawSurfaces();fields();changed();
        };
        line.append(select);details.append(line);
        if(!current)continue;
        const tint=document.createElement('label'),colour=document.createElement('input');tint.textContent=current.texture?'Tint · white keeps the texture as it is':'Colour';
        colour.type='color';colour.value=hex(current.color);colour.setAttribute('aria-label',SURFACE_NAMES[key]+(current.texture?' tint':' colour'));
        colour.onchange=()=>{checkpoint();profile.surfaces[key].color=rgb(colour.value);redrawSurfaces();changed();};tint.append(colour);details.append(tint);
        if(current.texture){
            const repeat=document.createElement('label'),size=document.createElement('input');repeat.textContent='One texture repeat (mm)';
            size.type='number';size.min=100;size.max=20000;size.step=50;size.value=current.tile;size.setAttribute('aria-label',SURFACE_NAMES[key]+' repeat');
            size.onchange=()=>{const value=Number(size.value);if(!(value>=100&&value<=20000)){size.value=profile.surfaces[key].tile;return;}checkpoint();profile.surfaces[key].tile=value;redrawSurfaces();changed();};
            repeat.append(size);details.append(repeat);
        }
    }
    const own=document.createElement('button');own.textContent='Add your own texture…';own.onclick=()=>$('surfaceFile').click();details.append(own);
    const hint=document.createElement('p');hint.className='hint';hint.textContent='Your image is cropped to a square and resized to 1024 px. A seamless (tileable) image hides the repeats.';details.append(hint);
    root.append(details);
}
function applyPlacements(){for(const [name,group]of Object.entries(groups))placement(group,entry(name));redrawPaths();}
function fields(){
    const root=$('fields');root.replaceChildren();
    if(kind==='home')for(const [id,base,alternate]of [['snesRegion','snes','snes-us'],['mdRegion','md','md-jp']]){
        $(id).value=profile.consoles[alternate]?alternate:base;$(id).disabled=!profile.consoles[base]&&!profile.consoles[alternate];
    }
    function field(value,path,parent,label){
        if(value&&typeof value==='object'&&!Array.isArray(value)){
            const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent=label;details.append(summary);details.open=path.length===1||path[0]==='tables'&&path[1]===selected||path[0]==='objects'&&path[1]===selected||path[0]==='consoles'&&path[1]===selected;
            for(const [key,item]of Object.entries(value))field(item,[...path,key],details,key);parent.append(details);return;
        }
        if(Array.isArray(value)&&value.some(v=>typeof v==='object')){
            const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent=label;details.append(summary);details.open=true;
            value.forEach((v,i)=>{field(v,[...path,i],details,`Path ${i+1}`);if(path.join('.')==='paths'){const remove=document.createElement('button');remove.textContent=`Remove path ${i+1}`;remove.onclick=()=>{checkpoint();profile.paths.splice(i,1);redrawPaths();fields();changed();};details.append(remove);}});parent.append(details);return;
        }
        const line=document.createElement('label');line.textContent=label;const inputs=document.createElement('div');if(Array.isArray(value))inputs.className='values';
        for(const [i,item]of (Array.isArray(value)?value:[value]).entries()){
            let input;
            const tableName=['from','to'].includes(String(path.at(-1)))||path.join('.')==='table.model';
            if(tableName){input=document.createElement('select');for(const name of (kind==='room'?Object.keys(profile.tables):Object.keys(manifest.tables))){const option=document.createElement('option');option.value=option.textContent=name;input.append(option);}input.value=item;}
            else{input=document.createElement('input');input.type=typeof item==='number'?'number':'text';input.value=item;input.step='any';}
            input.setAttribute('aria-label',path.join('.')+(Array.isArray(value)?'.'+['x','y','z'][i]:''));
            input.onchange=async()=>{
                checkpoint();let parent=atPath(path.slice(0,-1)),key=path.at(-1),next=input.type==='number'?Number(input.value):input.value;
                if(Array.isArray(value))parent[key][i]=next;else parent[key]=next;
                if(path[0]==='table'&&key==='model'){
                    // New furniture starts at the scale shared by the current console layouts.
                    // Explicit scale edits remain available, and Undo restores the prior model/scale.
                    profile.table.scale=next==='wooden-table'?[.7,.7,.7]:[1,1,1];await rebuild();fields();
                }else if(kind==='room'&&['floor','bounds'].includes(path[0]))await rebuild();
                else{applyPlacements();if(path[0]==='camera'||path[0]==='screen')applyCamera();if(path[0]==='table')groups.table.children[0].scale.fromArray(profile.table.scale);if(path[0]==='viewport')resize();}
                changed();
            };inputs.append(input);
        }
        line.append(inputs);parent.append(line);
    }
    if(kind==='room')surfaceFields(root);
    for(const [key,value]of Object.entries(profile))if(!['version','kind','tv','surfaces'].includes(key))field(value,[key],root,key);
}
gizmo.addEventListener('dragging-changed',e=>{dragging=e.value;orbit.enabled=!e.value;});gizmo.addEventListener('mouseDown',()=>checkpoint());
gizmo.addEventListener('objectChange',()=>{if(loading||!selected)return;const node=groups[selected];entry(selected).position=node.position.toArray();entry(selected).rotation=[node.rotation.x,node.rotation.y,node.rotation.z].map(deg);redrawPaths();changed();});gizmo.addEventListener('mouseUp',()=>fields());
orbit.addEventListener('start',()=>{if(!applying&&kind==='home')checkpoint();});orbit.addEventListener('change',()=>{if(!applying&&!loading&&kind==='home'){captureCamera();changed();}});orbit.addEventListener('end',()=>{if(!loading&&kind==='home')fields();});
let pointer=null;renderer.domElement.addEventListener('pointerdown',e=>pointer=[e.clientX,e.clientY]);renderer.domElement.addEventListener('pointerup',e=>{
    if(dragging||!pointer||Math.hypot(e.clientX-pointer[0],e.clientY-pointer[1])>4)return;const r=renderer.domElement.getBoundingClientRect(),ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,1-(e.clientY-r.top)/r.height*2),camera);
    for(const hit of ray.intersectObject(content,true)){let node=hit.object;while(node&&!node.userData.node)node=node.parent;if(node){select(node.userData.node);fields();break;}}
});
for(const [id,mode]of [['move','translate'],['rotate','rotate']])$(id).onclick=()=>{gizmo.setMode(mode);select(selected);$('move').classList.toggle('active',mode==='translate');$('rotate').classList.toggle('active',mode==='rotate');};
$('cameraTool').onclick=()=>select('');$('handles').onclick=()=>{hidden=!hidden;select(selected);$('handles').textContent=hidden?'Show handles':'Hide handles';};
$('view').onchange=()=>{if(!profile.screen&&$('view').value==='screen'){checkpoint();frameCamera();changed();fields();}else applyCamera();};
$('captureCamera').onclick=()=>{checkpoint();captureCamera();changed();fields();};$('frameCamera').onclick=()=>{checkpoint();frameCamera();changed();fields();};
async function restore(from,to){if(!from.length)return;to.push(JSON.stringify(profile));profile=JSON.parse(from.pop());await rebuild();changed();}
$('undo').onclick=()=>restore(history,future);$('redo').onclick=()=>restore(future,history);
for(const [id,base,alternate]of [['snesRegion','snes','snes-us'],['mdRegion','md','md-jp']])$(id).onchange=async()=>{
    if(loading)return;const previous=profile.consoles[alternate]?alternate:base,next=$(id).value;if(next===previous)return;
    checkpoint();profile.consoles=Object.fromEntries(Object.entries(profile.consoles).map(([name,value])=>[name===previous?next:name,value]));
    if(selected===previous)selected=next;await rebuild();changed('Home model changed. Its authored position and cameras are preserved.');
};
$('reload').onclick=async()=>{localStorage.setItem(draftKey+'-recovery-'+Date.now(),localStorage.getItem(draftKey)||'');profile=copy(saved.profile);baseSha=saved.sha256;history=[];future=[];await rebuild();draft();$('state').textContent='Saved scene restored. The previous browser draft is retained in recovery.';};
$('export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(profile,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=kind==='room'?'room.json':`home-${tv}.json`;a.click();URL.revokeObjectURL(url);};
async function importDraft(value){
    if(value.kind!==kind||(kind==='home'&&value.tv!==tv))throw Error('Open the matching scene and TV before importing this file.');
    checkpoint();profile=copy(value);await rebuild();changed('Imported as an undoable browser draft. Save to keep it as the local scene.');
}
$('importDevice').onclick=async()=>{const button=$('importDevice');button.disabled=true;try{const data=await json(`/api/room/device?scene=${kind}&tv=${tv}`);if(!data.found)throw Error('This scene has not been saved on the device.');await importDraft(data.profile);}catch(e){$('state').textContent=e.message;}finally{button.disabled=false;}};
$('importJSON').onclick=()=>$('jsonFile').click();
$('surfaceFile').onchange=async()=>{
    const file=$('surfaceFile').files[0];if(!file)return;
    try{
        const label=prompt('Name for this texture',file.name.replace(/\.[^.]+$/,''));if(!label)return;
        const image=await new Promise((ok,fail)=>{const reader=new FileReader();reader.onload=()=>ok(reader.result);reader.onerror=()=>fail(reader.error);reader.readAsDataURL(file);});
        $('state').textContent='Importing texture…';
        const r=await fetch('/api/room/surface',{method:'POST',headers:{'Content-Type':'application/json','X-Scene-Token':manifest.token},body:JSON.stringify({label,image})}),data=await r.json();if(!r.ok)throw Error(data.error);
        for(const key of [...surfaceTextures.keys()])if(key.startsWith(data.texture.name+'|'))surfaceTextures.delete(key);
        surfaceLibrary=(await json('/api/room/surfaces')).textures;await redrawSurfaces();fields();
        $('state').textContent=`Added “${data.texture.label}”. Choose it for the floor, walls or ceiling.`;
    }catch(e){$('state').textContent=e.message;}finally{$('surfaceFile').value='';}
};
$('jsonFile').onchange=async()=>{const file=$('jsonFile').files[0];if(!file)return;try{const value=JSON.parse(await file.text()),r=await fetch('/api/room/validate',{method:'POST',headers:{'Content-Type':'application/json','X-Scene-Token':manifest.token},body:JSON.stringify({profile:value})}),data=await r.json();if(!r.ok)throw Error(data.error);await importDraft(data.profile);}catch(e){$('state').textContent=e.message;}finally{$('jsonFile').value='';}};
$('save').onclick=async()=>{const submitted=copy(profile);try{const r=await fetch('/api/room/save',{method:'POST',headers:{'Content-Type':'application/json','X-Scene-Token':manifest.token},body:JSON.stringify({profile:submitted,expect:baseSha})}),data=await r.json();if(!r.ok)throw Error(data.error);baseSha=data.sha256;saved={profile:submitted,sha256:baseSha};draft();$('state').textContent='Scene saved. The previous saved version remains in history.';}catch(e){$('state').textContent=e.message;}};
let uploading=false;
async function uploadProgress(session,submitted=null){
    if(uploading)return;uploading=true;$('upload').disabled=true;
    try{for(;;){const state=await json('/api/upload'),items=state.progress||[],verified=items.filter(item=>['same','verified'].includes(item.state)).length;
        if(state.session!==session)throw Error('Another upload replaced this status. Your draft is retained.');
        $('uploadState').textContent=state.message+(items.length?` · ${verified}/${items.length} files verified`:'');
        if(submitted&&state.saved?.sha256){baseSha=state.saved.sha256;saved={profile:submitted,sha256:baseSha};draft();}
        if(state.state!=='running')break;await new Promise(resolve=>setTimeout(resolve,1000));
    }}finally{uploading=false;$('upload').disabled=false;}
}
$('upload').onclick=async()=>{const submitted=copy(profile);try{const r=await fetch('/api/room/upload',{method:'POST',headers:{'Content-Type':'application/json','X-Scene-Token':manifest.token},body:JSON.stringify({profile:submitted,expect:baseSha})}),state=await r.json();if(!r.ok)throw Error(state.error);if(submitted&&state.saved?.sha256){baseSha=state.saved.sha256;saved={profile:submitted,sha256:baseSha};draft();}await uploadProgress(state.session,submitted);}catch(e){$('uploadState').textContent=e.message;}};
$('addPath').onclick=()=>{const tables=Object.keys(profile.tables),pairs=tables.flatMap(from=>tables.filter(to=>to!==from).map(to=>({from,to}))),next=pairs.find(pair=>!profile.paths.some(path=>path.from===pair.from&&path.to===pair.to));if(!next){$('state').textContent='Every table pair already has a path.';return;}checkpoint();profile.paths.push({...next,seconds:1.4,first:[0,180,0],second:[0,180,0]});redrawPaths();fields();changed();};
$('previewPath').onclick=()=>{const line=content.getObjectByName('travel-paths')?.children[0];if(line)flight={curve:line.userData.curve,start:performance.now(),seconds:profile.paths[0].seconds,eye:camera.position.clone(),target:orbit.target.clone()};};
function resize(){const r=$('stage').getBoundingClientRect(),aspect=kind==='home'&&profile?profile.viewport.width/profile.viewport.height:1.5;const w=Math.max(100,Math.min(r.width-44,(r.height-44)*aspect)),h=w/aspect;$('viewport').style.width=w+'px';$('viewport').style.height=h+'px';renderer.setSize(w,h);camera.aspect=aspect;camera.updateProjectionMatrix();}
new ResizeObserver(resize).observe($('stage'));
document.addEventListener('keydown',e=>{if(e.target.matches('input,select,textarea')||e.target.isContentEditable)return;if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();$(e.shiftKey?'redo':'undo').click();}else if(e.key.toLowerCase()==='w')$('move').click();else if(e.key.toLowerCase()==='e')$('rotate').click();});
renderer.setAnimationLoop(now=>{if(flight){const t=Math.min(1,(now-flight.start)/1000/flight.seconds),point=flight.curve.getPoint(t),eye=point.clone().add(new THREE.Vector3(600,1000,1800));applying=true;camera.position.copy(eye);orbit.target.copy(point);orbit.update();applying=false;if(t===1){camera.position.copy(flight.eye);orbit.target.copy(flight.target);orbit.update();flight=null;}}renderer.render(scene,camera);});
try{
    [manifest,saved]=await Promise.all([json('/api/room/manifest?tv='+tv),json(`/api/room/profile?scene=${kind}&tv=${tv}`)]);profile=copy(saved.profile);baseSha=saved.sha256;
    let recovered=false;try{const draft=JSON.parse(localStorage.getItem(draftKey));if(draft?.profile?.kind===kind){profile=draft.profile;baseSha=draft.baseSha;history=draft.history||[];future=draft.future||[];recovered=true;}}catch{}
    if(kind==='room')surfaceLibrary=(await json('/api/room/surfaces')).textures;
    await rebuild();if(kind==='room'){camera.position.set(6500,6500,10000);orbit.target.set(0,500,0);orbit.update();}else applyCamera();
    $('state').textContent=recovered?'Browser draft restored. Saved scenes remain unchanged until Save.':'Ready · full source models. Save creates this scene separately from console layouts.';
    const pending=await json('/api/upload');if(pending.layouts?.includes(kind==='room'?'room':'home-'+tv)){if(pending.state==='running')uploadProgress(pending.session).catch(e=>$('uploadState').textContent=e.message);else $('uploadState').textContent=pending.message;}
    window.slottedRoomStudio={ready:true,snapshot:()=>copy(profile),camera:()=>({position:camera.position.toArray(),target:orbit.target.toArray(),fov:camera.fov}),triangles:()=>renderer.info.render.triangles};
}catch(e){$('loading').textContent=$('state').textContent=e.message;console.error(e);}
