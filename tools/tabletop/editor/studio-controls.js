import * as THREE from 'three';
import {labelOccluders} from './view-depth.js';

const $=id=>document.getElementById(id),clone=v=>JSON.parse(JSON.stringify(v));
const fields={title:'Title header',hud:'Players / year',artwork:'Box art / gallery',description:'Description',facts:'Game details',footer:'Page indicator',video:'Video preview',library:'Library statistics'};
export const defaultDisplay=enabled=>({enabled,layout:'split',textScale:1,padding:12,background:'#0e191b',foreground:'#e8e9e7',accent:'#42665a',fields:Object.fromEntries(Object.keys(fields).map(k=>[k,true]))});

// Five authored cameras share the same world and projection as every scene object.
// Only explicit frame/reset operations derive a camera; existing views never auto-fit.
export function createStudioControls({scene,camera,orbit,groups,renderer,prepared,manifest,act,markDirty,updateFields,setBusy,material,onModelDrag}){
    let cameras={},active='all',transition=null,table={model:'table',scale:[1,1,1]},displays={tv:defaultDisplay(true),handheld:defaultDisplay(false)};
    let pan=.8,browseView='all',cartIndex=0,inspection=null,yaw=0,pitch=0,drag=null,tableRequest=0;
    const tableModels=new Map(),screenMeshes={tv:[],handheld:[]},displayTextures={};
    const cameraValue=()=>({position:camera.position.toArray(),target:orbit.target.toArray(),fov:camera.fov});
    const cameraDelta=new THREE.Vector3();
    const applyCamera=c=>{camera.position.fromArray(c.position);orbit.target.fromArray(c.target);camera.fov=c.fov;camera.updateProjectionMatrix();orbit.update();};
    const cartDelta=()=>groups[`cart${cartIndex}`].getWorldPosition(new THREE.Vector3()).sub(groups.cart0.getWorldPosition(new THREE.Vector3()));
    function canonical(c,sign){const p=clone(c);if(active==='cartridge'){if(sign>0)cameraDelta.copy(cartDelta());const d=cameraDelta.clone().multiplyScalar(sign);p.position=new THREE.Vector3(...p.position).add(d).toArray();p.target=new THREE.Vector3(...p.target).add(d).toArray();}return p;}
    function remember(){if(!transition)cameras[active]=canonical(cameraValue(),-1);}
    function beginCameraEdit(){
        if(!transition)return;
        const to=transition.to;transition=null;setBusy(true);applyCamera(to);setBusy(false);orbit.enabled=true;updateFields();
    }
    function applyManualCamera(value){
        const numbers=[...value.position,...value.target,value.fov];
        if(numbers.some(n=>!Number.isFinite(n))||[...value.position,...value.target].some(n=>Math.abs(n)>10000)
            ||value.fov<5||value.fov>110||new THREE.Vector3(...value.position).distanceToSquared(new THREE.Vector3(...value.target))<100){
            $('cameraState').textContent='Use valid XYZ values, FOV 5–110°, and keep the look-at point at least 10 mm from the camera.';return false;
        }
        beginCameraEdit();setBusy(true);applyCamera(value);if(active==='cartridge')cameraDelta.copy(cartDelta());cameras[active]=canonical(value,-1);setBusy(false);orbit.enabled=true;
        $('cameraState').textContent='Camera set for '+$('view').selectedOptions[0].textContent+'. Other views are unchanged.';markDirty();return true;
    }
    function mouseCamera(value){$('modelDrag').checked=!value;}
    function frame(key){
        const object=key==='tv'?groups.tv:key==='console'?groups.console:key==='cartridge'?groups.cart0:groups.all;
        scene.updateMatrixWorld(true);
        const bounds=new THREE.Box3().setFromObject(object),center=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3());
        let normal=new THREE.Vector3(0,.38,1);
        if(key==='tv')normal.set(0,0,1).applyQuaternion(groups.tv.getWorldQuaternion(new THREE.Quaternion()));
        if(key==='cartridge')normal.set(0,.78,.62);
        if(key==='console')normal.set(0,.6,1);
        const fov=key==='cartridge'?34:40;
        normal.normalize();const right=new THREE.Vector3(0,1,0).cross(normal).normalize(),up=normal.clone().cross(right),tangent=Math.tan(THREE.MathUtils.degToRad(fov)/2);
        let distance=180;for(let k=0;k<8;k++){const point=new THREE.Vector3(k&1?bounds.max.x:bounds.min.x,k&2?bounds.max.y:bounds.min.y,k&4?bounds.max.z:bounds.min.z).sub(center),depth=point.dot(normal);
            distance=Math.max(distance,depth+150,depth+Math.abs(point.dot(up))/(tangent*.9),depth+Math.abs(point.dot(right))/(tangent*camera.aspect*.9));}
        distance+=20;
        if(key==='inspect')return clone(cameras.all);
        return {position:center.clone().addScaledVector(normal.normalize(),distance).toArray(),target:center.toArray(),fov};
    }
    function switchView(key,animate=true,rememberCurrent=true){
        if(rememberCurrent)remember();const from=cameraValue();active=key;if(!cameras[key])cameras[key]=frame(key);
        const to=canonical(cameras[key],1);$('view').value=key;$('inspectionTools').hidden=key!=='inspect';$('cameraState').textContent='';
        if(animate){transition={from,to,start:performance.now(),duration:pan*1000};setBusy(true);orbit.enabled=false;}
        else{transition=null;setBusy(true);applyCamera(to);setBusy(false);orbit.enabled=true;}
        refreshInspection();updateFields();
    }
    function extras(){
        remember();return {camera:clone(cameras.all||cameraValue()),cameras:clone(cameras),transitionSeconds:pan,browseView,
            table:clone(table),displays:clone(displays),editorView:active};
    }
    async function tableModel(key){
        const request=++tableRequest;
        try{
            if(!tableModels.has(key))tableModels.set(key,(await prepared(key)).group);
            if(request!==tableRequest)return;
            groups.table.clear();groups.table.add(tableModels.get(key));
            $('tableCredit').textContent=key==='tv-stand'?'Qu3st10n · CC BY-NC-SA 4.0 · noncommercial, share alike':key==='wooden-table'?'AndreyUEDev · CC BY 4.0':'lena-wachs · CC BY 4.0';
        }catch(error){$('saveState').textContent=error.message;}
    }
    function load(value){
        transition=null;orbit.enabled=true;setBusy(true);cameras=clone(value.cameras||{});cameras.all=clone(value.camera);$('cameraState').textContent='';
        table=clone(value.table||{model:'table',scale:[1,1,1]});displays=clone(value.displays||{tv:defaultDisplay(true),handheld:defaultDisplay(false)});
        pan=value.transitionSeconds||.8;browseView=value.browseView||'all';active=value.editorView||'all';
        if(!cameras[active])active='all';
        groups.table.scale.fromArray(table.scale);tableModel(table.model);
        $('tableModel').value=table.model;scaleInputs.forEach((input,i)=>input.value=table.scale[i]);
        $('panSeconds').value=pan;$('browseView').value=browseView;displayFields();refreshDisplays();
        applyCamera(canonical(cameras[active],1));$('view').value=active;$('inspectionTools').hidden=active!=='inspect';refreshInspection();setBusy(false);
    }
    function refreshInspection(){
        if(inspection){scene.remove(inspection);inspection=null;}
        for(let i=0;i<12;i++)groups[`cart${i}`].visible=true;
        if(active!=='inspect'&&active!=='cartridge')return;
        const original=groups[`cart${cartIndex}`];inspection=original.clone(true);inspection.userData={};inspection.visible=true;
        inspection.scale.copy(original.getWorldScale(new THREE.Vector3()));scene.add(inspection);original.visible=false;
    }
    // Carts in front of the selected one that cover its label fade in the cartridge view, as
    // SlotTabletop.cpp labelOccluders does: resting poses, judged at the pan's destination.
    const probe=new THREE.PerspectiveCamera();
    function fadeOccluders(){
        let faded=[];
        if(active==='cartridge'){
            const c=transition?transition.to:cameraValue();probe.position.fromArray(c.position);probe.fov=c.fov;probe.aspect=camera.aspect;probe.near=10;probe.far=10000;
            probe.lookAt(...c.target);probe.updateProjectionMatrix();probe.updateMatrixWorld();scene.updateMatrixWorld();
            const box=mesh=>{const g=mesh.geometry;if(!g.boundingBox)g.computeBoundingBox();return {model:mesh.matrixWorld.elements,low:g.boundingBox.min.toArray(),high:g.boundingBox.max.toArray()};};
            const carts=Array.from({length:12},(_,i)=>{const [shell,label]=groups[`cart${i}`].children;return {shell:box(shell),label:label?box(label):null};});
            faded=labelOccluders(carts,cartIndex,probe.projectionMatrix.elements,probe.matrixWorldInverse.elements,c.position,new THREE.Vector3(...c.target).sub(probe.position).normalize().toArray());
        }
        for(let i=0;i<12;i++){const fade=faded.includes(i)?.25:1;groups[`cart${i}`].traverse(o=>{const u=o.isMesh&&o.material.uniforms?.fade;if(u&&u.value!==fade){u.value=fade;o.material.transparent=fade<1;o.material.needsUpdate=true;}});}
    }
    function tick(now){
        fadeOccluders();
        if(transition){
            let t=Math.min(1,(now-transition.start)/transition.duration);t=t*t*(3-2*t);
            const {from,to}=transition;
            applyCamera({position:from.position.map((v,i)=>v+(to.position[i]-v)*t),target:from.target.map((v,i)=>v+(to.target[i]-v)*t),fov:from.fov+(to.fov-from.fov)*t});
            updateFields();if(t>=1){transition=null;setBusy(false);orbit.enabled=true;markDirty();}
        }
        if(inspection){
            if(active==='cartridge'){
                const original=groups[`cart${cartIndex}`];inspection.position.copy(original.getWorldPosition(new THREE.Vector3())).add(new THREE.Vector3(0,3,0));inspection.quaternion.copy(original.getWorldQuaternion(new THREE.Quaternion()));
                const right=new THREE.Vector3(1,0,0).applyQuaternion(camera.quaternion);inspection.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(right,-Math.PI/15));return;
            }
            // Same 55% framing and 150 mm near-plane clearance as native inspectModel.
            const mesh=inspection.children[0],box=mesh.geometry.boundingBox||new THREE.Box3().setFromBufferAttribute(mesh.geometry.attributes.position);
            const size=box.getSize(new THREE.Vector3()).multiply(inspection.scale),pivot=box.getCenter(new THREE.Vector3()).multiply(inspection.scale);
            const tangent=Math.tan(THREE.MathUtils.degToRad(camera.fov)/2),radius=size.length()/2;
            const distance=Math.max(size.y/(.55*2*tangent),size.x/(.55*2*tangent*camera.aspect),160+radius);
            const center=camera.position.clone().addScaledVector(orbit.target.clone().sub(camera.position).normalize(),distance);
            inspection.quaternion.copy(camera.quaternion).multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(pitch,yaw,0,'YXZ')));
            inspection.position.copy(center).sub(pivot.applyQuaternion(inspection.quaternion));
        }
    }
    function lcd(points){
        const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(points,3));g.setAttribute('uv',new THREE.Float32BufferAttribute([0,0,1,0,1,1,0,1],2));
        g.setAttribute('normal',new THREE.Float32BufferAttribute(Array(4).fill([0,0,1]).flat(),3));g.setAttribute('color',new THREE.Float32BufferAttribute(Array(12).fill(1),3));g.setIndex([0,3,2,0,2,1]);return g;
    }
    function displayFields(){const d=displays[$('displayTarget').value];$('displayEnabled').checked=d.enabled;$('displayLayout').value=d.layout;$('textScale').value=d.textScale;$('displayPadding').value=d.padding;
        for(const key of ['background','foreground','accent'])$(key).value=d[key];for(const key of Object.keys(fields))$(`field-${key}`).checked=d.fields[key];}
    function drawDisplay(key){
        const page=$('metadataPage').value,d=displays[key],canvas=displayTextures[key].image,c=canvas.getContext('2d'),w=canvas.width,h=canvas.height,p=d.padding,f=d.fields,s=d.textScale;
        c.fillStyle=d.background;c.fillRect(0,0,w,h);if(!d.enabled){displayTextures[key].needsUpdate=true;return;}
        c.save();c.beginPath();c.rect(p,p,w-p*2,h-p*2);c.clip();c.fillStyle=d.foreground;c.textBaseline='top';
        let y=p;if(f.title){c.font=`600 ${21*s}px system-ui`;c.fillText('Super Mario World',p,y,w-2*p);y+=28*s;}
        if(f.hud){c.font=`${18*s}px system-ui`;c.fillText('Players: 1-2   1990',p,y,w-2*p);y+=26*s;}
        c.fillStyle=d.accent;c.fillRect(p,y,w-2*p,1);y+=8;
        const art=d.layout!=='text'&&((f.artwork&&['overview','artwork'].includes(page))||(f.video&&['overview','video'].includes(page))),split=d.layout==='split'&&page==='overview'&&art;
        if(art){const aw=split?w*.30:w-2*p,ah=Math.max(1,h-y-(f.footer?35:10));c.fillStyle=d.accent;c.fillRect(p,y,aw,ah);c.fillStyle=d.foreground;c.font=`${17*s}px system-ui`;c.fillText(f.video?'VIDEO / ART':'BOX ART',p+5,y+ah/2,aw-10);}
        if(d.layout!=='artwork'){
            const x=split?w*.35:p,tw=w-x-p;c.fillStyle=d.foreground;c.font=`${20*s}px system-ui`;
            const text=[page==='overview'&&f.description?'Explore Dinosaur Land with Mario and Yoshi. Discover secret exits and collect power-ups.':'',page==='facts'&&f.facts?'Nintendo · Platform · SNES':'',page==='library'&&f.library?'Played 12 times · Last played yesterday':''].filter(Boolean).join('\n\n');
            for(const paragraph of text.split('\n')){let line='';for(const word of paragraph.split(' ')){if(c.measureText(line+word).width>tw&&line){c.fillText(line,x,y);line='';y+=25*s;}line+=word+' ';}c.fillText(line,x,y);y+=25*s;}
        }
        if(f.footer){c.fillStyle=d.background;c.fillRect(0,h-30,w,30);c.fillStyle=d.foreground;c.font=`${16*s}px system-ui`;c.fillText('L1 / R1   1 / 4   '+$('metadataPage').selectedOptions[0].textContent,p,h-24,w-2*p);}
        c.restore();displayTextures[key].needsUpdate=true;
    }
    function refreshDisplays(){for(const key of ['tv','handheld']){if(!displayTextures[key])continue;drawDisplay(key);for(const mesh of screenMeshes[key])mesh.visible=displays[key].enabled;}}
    function bindScreens(){
        for(const key of ['tv','handheld']){const canvas=document.createElement('canvas');canvas.width=480;canvas.height=360;const texture=new THREE.CanvasTexture(canvas);texture.flipY=false;texture.colorSpace=THREE.NoColorSpace;displayTextures[key]=texture;}
        groups.tv.traverse(object=>{if(object.isMesh&&object.userData.glass){object.material=material(displayTextures.tv,true);const inset=manifest.tv==='panasonic'?.07:manifest.tv==='pvm'?.03:.04;
            object.material.uniforms.window.value.set(inset,inset,1-inset,1-inset);screenMeshes.tv.push(object);}});
        for(const points of manifest.lcd){const m=new THREE.Mesh(lcd(points),material(displayTextures.handheld,true));m.material.polygonOffset=true;m.material.polygonOffsetFactor=-2;m.material.polygonOffsetUnits=-2;
            // LCD corners share the source housing's coordinates and tabletop rotation.
            groups.console.children[0].add(m);screenMeshes.handheld.push(m);}
        refreshDisplays();
    }
    for(const [key,label] of Object.entries(manifest.tables)){const option=document.createElement('option');option.value=key;option.textContent=label;$('tableModel').append(option);}
    const scaleInputs=['Width','Height','Depth'].map((label,i)=>{const wrap=document.createElement('label'),span=document.createElement('span'),input=document.createElement('input');span.textContent=label[0];input.type='number';input.min=.1;input.max=5;input.step=.05;input.setAttribute('aria-label',`Table ${label.toLowerCase()} scale`);input.onchange=()=>{const value=Number(input.value);if(!Number.isFinite(value)||value<.1||value>5)return;act(()=>{if($('tableUniform').checked){const ratio=value/table.scale[i];table.scale=table.scale.map(s=>Math.max(.1,Math.min(5,s*ratio)));}else table.scale[i]=value;groups.table.scale.fromArray(table.scale);scaleInputs.forEach((field,j)=>field.value=table.scale[j]);});};input.addEventListener('input',()=>input.onchange());wrap.append(span,input);$('tableScale').append(wrap);return input;});
    for(const [key,label] of Object.entries(fields)){const wrap=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.id=`field-${key}`;input.onchange=()=>act(()=>{displays[$('displayTarget').value].fields[key]=input.checked;refreshDisplays();});wrap.append(input,document.createTextNode(label));$('metadataFields').append(wrap);}
    for(let i=0;i<12;i++){const option=document.createElement('option');option.value=i;option.textContent=`Cartridge ${i+1}`;$('previewCart').append(option);}
    function selectCartridge(index){remember();cartIndex=index;$('previewCart').value=index;if(active==='cartridge')switchView(active,true,false);refreshInspection();}
    $('previewCart').onchange=()=>selectCartridge(Number($('previewCart').value));
    $('view').onchange=()=>act(()=>switchView($('view').value));$('viewOverview').onclick=()=>act(()=>switchView('all'));
    $('viewGenerate').onclick=()=>act(()=>{remember();cameras[active]=frame(active);switchView(active,true,false);});
    $('browseView').onchange=()=>act(()=>{browseView=$('browseView').value;});
    $('panSeconds').onchange=()=>{const value=Number($('panSeconds').value);if(Number.isFinite(value)&&value>=.1&&value<=5)act(()=>{pan=value;});};
    $('tableModel').onchange=()=>act(()=>{table.model=$('tableModel').value;tableModel(table.model);});
    $('displayTarget').onchange=displayFields;$('metadataPage').onchange=refreshDisplays;
    for(const [id,key] of [['displayEnabled','enabled'],['displayLayout','layout'],['textScale','textScale'],['displayPadding','padding'],['background','background'],['foreground','foreground'],['accent','accent']]){
        $(id).onchange=()=>act(()=>{const input=$(id),value=input.type==='checkbox'?input.checked:input.type==='number'?Number(input.value):input.value;if(typeof value==='number'&&(!Number.isFinite(value)||value<Number(input.min)||value>Number(input.max)))return;displays[$('displayTarget').value][key]=value;refreshDisplays();});
    }
    for(const id of ['panSeconds','textScale','displayPadding'])$(id).addEventListener('input',()=>$(id).onchange());
    $('inspectReset').onclick=()=>{yaw=pitch=0;};
    $('modelDrag').onchange=()=>{if($('modelDrag').checked)onModelDrag?.();};
    renderer.domElement.addEventListener('pointerdown',event=>{if(active!=='inspect'||!$('modelDrag').checked||event.button!==0)return;drag=[event.clientX,event.clientY];orbit.enabled=false;event.stopImmediatePropagation();renderer.domElement.setPointerCapture(event.pointerId);},true);
    renderer.domElement.addEventListener('pointermove',event=>{if(!drag)return;yaw+=(event.clientX-drag[0])*.012;pitch+=(event.clientY-drag[1])*.012;drag=[event.clientX,event.clientY];},true);
    renderer.domElement.addEventListener('pointerup',event=>{if(!drag)return;drag=null;orbit.enabled=true;event.stopImmediatePropagation();},true);
    window.addEventListener('keydown',event=>{if(active!=='inspect'||/INPUT|SELECT/.test(document.activeElement.tagName)||document.querySelector('dialog[open]'))return;if(event.key==='ArrowLeft')yaw-=.15;else if(event.key==='ArrowRight')yaw+=.15;else if(event.key==='ArrowUp')pitch-=.15;else if(event.key==='ArrowDown')pitch+=.15;else if(event.key.toLowerCase()==='b')act(()=>switchView('all'));else return;event.preventDefault();});
    bindScreens();
    function aspectChanged(oldAspect,newAspect){for(const [key,value] of Object.entries(cameras))if(key!==active)value.fov=THREE.MathUtils.radToDeg(2*Math.atan(Math.tan(THREE.MathUtils.degToRad(value.fov)/2)*oldAspect/newAspect));}
    return {extras,load,tick,transitioning:()=>!!transition,active:()=>active,refreshDisplays,aspectChanged,selectCartridge,beginCameraEdit,applyManualCamera,mouseCamera};
}
