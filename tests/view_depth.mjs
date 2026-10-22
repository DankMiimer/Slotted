// Editor near-plane fit and label occluders match the native SlotSceneDepth.h cases.
import assert from 'node:assert/strict';
import * as THREE from '../build/tabletop/editor-vendor/three.module.js';
import {boxDepth,depthRange,hugNear,labelOccluders,hull,clip,area} from '../tools/tabletop/editor/view-depth.js';

const near=(a,b,t=.01)=>assert.ok(Math.abs(a-b)<=t,`${a} != ${b}`);
const I=new THREE.Matrix4().elements;
const camera=new THREE.PerspectiveCamera(90,1,10,10000);camera.position.set(0,0,0);camera.lookAt(0,0,-1);camera.updateMatrixWorld();
const eye=camera.matrixWorldInverse.elements;
let r=depthRange();assert.ok(boxDepth(r,eye,I,[-10,-10,-260],[10,10,-200],1,1));near(r.closest,200);near(r.farthest,260);
r=depthRange();assert.ok(!boxDepth(r,eye,I,[300,-10,-260],[320,10,-200],1,1));assert.equal(r.visible,false);
r=depthRange();assert.ok(!boxDepth(r,eye,I,[-10,-10,50],[10,10,80],1,1));
r=depthRange();assert.ok(boxDepth(r,eye,I,[50,-10,-300],[90,10,-40],1,1));near(r.closest,50,.05);
r=depthRange();assert.ok(boxDepth(r,eye,I,[-1000,-110,-2000],[1000,-100,500],.75,.5));near(r.closest,200,.05);near(r.farthest,2000,.05);
r=depthRange();assert.ok(boxDepth(r,eye,I,[-5,-5,-5],[5,5,5],1,1,1));assert.equal(r.closest,1);
const turned=new THREE.Matrix4().makeTranslation(0,0,-300).multiply(new THREE.Matrix4().makeRotationY(Math.PI/4)).elements;
r=depthRange();assert.ok(boxDepth(r,eye,turned,[-50,-50,-50],[50,50,50],1,1));near(r.closest,300-50*Math.SQRT2,.05);
r={visible:true,closest:120};near(hugNear(r),114);r.closest=400;assert.equal(hugNear(r),150);r.closest=4;assert.equal(hugNear(r),10);
assert.equal(hugNear(depthRange()),150);

// 2D helpers: unit square hull, half overlap.
const square=hull([[0,0],[1,0],[1,1],[0,1],[.5,.5]]);assert.equal(square.length,4);near(area(square),1);
near(area(clip(square,hull([[.5,-1],[2,-1],[2,2],[.5,2]]))),.5);

// A cart straight in front of the selected one covers its label and fades; one beside it,
// and one behind it, do not.
const view=new THREE.PerspectiveCamera(30,1.5,10,10000);view.position.set(0,80,300);view.lookAt(0,0,0);view.updateMatrixWorld();view.updateProjectionMatrix();
// Standing shells (60 mm tall) so the one in front rises into the line of sight.
const box=(x,z)=>({model:new THREE.Matrix4().makeTranslation(x,0,z).elements,low:[-29,-4,-18],high:[29,60,18]});
const carts=[{shell:box(0,0),label:{model:new THREE.Matrix4().makeTranslation(0,0,18.1).elements,low:[-20,0,0],high:[20,50,0]}},
    {shell:box(10,60),label:null},{shell:box(200,0),label:null},{shell:box(0,-80),label:null}];
const forward=new THREE.Vector3(0,-80,-300).normalize().toArray();
assert.deepEqual(labelOccluders(carts,0,view.projectionMatrix.elements,view.matrixWorldInverse.elements,[0,80,300],forward),[1]);
console.log('view depth ok');
