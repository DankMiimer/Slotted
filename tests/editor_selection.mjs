import assert from 'node:assert/strict';
import * as THREE from '../build/tabletop/editor-vendor/three.module.js';
import {createTransformSelection} from '../tools/tabletop/editor/transform-selection.js';

const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);
const vector=(a,b)=>a.toArray().forEach((v,i)=>close(v,b.toArray()[i]));
const pose=o=>({position:o.getWorldPosition(new THREE.Vector3()),quaternion:o.getWorldQuaternion(new THREE.Quaternion())});
const rotation=(a,b)=>close(Math.abs(a.dot(b)),1);
function fixture(){
    const scene=new THREE.Scene(),groups={};
    for(const name of ['table','tv','status','console','cart0','cart1','all']){
        const o=groups[name]=new THREE.Group();o.rotation.order='YXZ';scene.add(o);
    }
    groups.tv.add(groups.status);groups.all.add(groups.cart0,groups.cart1);
    groups.tv.position.set(120,0,-300);groups.tv.rotation.y=.6;
    groups.status.position.set(0,340,200);groups.status.scale.setScalar(.7);
    groups.all.position.set(-20,15,360);groups.all.rotation.y=-.4;
    groups.cart0.position.set(-60,3,15);groups.cart0.rotation.set(.1,.5,-.1);
    groups.cart1.position.set(80,6,-30);groups.cart1.rotation.set(-.2,.7,.2);
    groups.console.position.set(300,40,600);groups.console.scale.setScalar(1/2.73);
    groups.table.scale.set(.7,.5,1.2);
    scene.updateMatrixWorld(true);
    return {scene,groups,selection:createTransformSelection(THREE,scene,groups)};
}
{
    const {groups:g,selection:s}=fixture(),original=Object.fromEntries(Object.entries(g).map(([n,o])=>[n,pose(o)]));
    s.choose(['cart0','console']);s.choose(['cart0','cart1']);
    for(const [n,o] of Object.entries(g)){vector(pose(o).position,original[n].position);rotation(pose(o).quaternion,original[n].quaternion);}
    const pivot=s.target(),center=pivot.position.clone(),delta=new THREE.Vector3(40,-10,65);
    s.begin();pivot.position.add(delta);s.change();s.change();s.end();
    for(const n of ['cart0','cart1'])vector(pose(g[n]).position,original[n].position.clone().add(delta));
    vector(pose(g.console).position,original.console.position);
    const before=pose(g.cart0),distance=pose(g.cart0).position.distanceTo(pose(g.cart1).position);
    const q=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),Math.PI/2);
    s.begin();pivot.quaternion.copy(q);s.change();s.end();
    vector(pose(g.cart0).position,before.position.clone().sub(center.clone().add(delta)).applyQuaternion(q).add(pivot.position));
    rotation(pose(g.cart0).quaternion,q.clone().multiply(before.quaternion));
    close(pose(g.cart0).position.distanceTo(pose(g.cart1).position),distance);
    assert.equal(g.cart0.parent,g.all);close(g.console.scale.x,1/2.73);
}
{
    const {groups:g,selection:s}=fixture(),a=pose(g.tv),b=pose(g.status),offset=new THREE.Vector3(18,24,30);
    s.choose(['tv','status']);assert.equal(s.roots().length,1);
    s.begin();s.target().position.add(offset);s.change();s.end();
    vector(pose(g.tv).position,a.position.clone().add(offset));vector(pose(g.status).position,b.position.clone().add(offset));
    close(g.status.scale.x,.7);
}
for(const [a,b] of [['cart0','cart1'],['tv','status'],['table','console'],['status','console']]){
    const {groups:g,selection:s}=fixture(),pa=pose(g[a]),pb=pose(g[b]),sa=g[a].scale.clone(),sb=g[b].scale.clone();
    s.choose([a,b]);assert.ok(s.swap(a,b));
    vector(pose(g[a]).position,pb.position);vector(pose(g[b]).position,pa.position);
    rotation(pose(g[a]).quaternion,pb.quaternion);rotation(pose(g[b]).quaternion,pa.quaternion);
    vector(g[a].scale,sa);vector(g[b].scale,sb);
    assert.ok(s.swap(a,b));vector(pose(g[a]).position,pa.position);rotation(pose(g[b]).quaternion,pb.quaternion);
}
{
    const {groups:g,selection:s}=fixture(),a=pose(g.cart0),b=pose(g.console);
    s.swap('cart0','console',false,true);vector(pose(g.cart0).position,a.position);vector(pose(g.console).position,b.position);
    rotation(pose(g.cart0).quaternion,b.quaternion);
    assert.equal(s.swap('cart0','cart0'),false);assert.equal(s.swap('cart0','console',false,false),false);
    s.choose(['cart0','cart0','missing']);assert.deepEqual(s.names(),['cart0']);assert.equal(s.target(),g.cart0);
    s.choose([]);assert.equal(s.target(),null);
}
console.log('Selection transforms: shared translation/rotation, parent-child handling, world swaps, scales and selection stability pass.');
