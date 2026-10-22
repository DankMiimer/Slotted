// A virtual group pivot keeps source nodes in their original hierarchy.
// In particular, TV status follows its parent once and model scales stay intact.
export function createTransformSelection(THREE, scene, groups) {
    const pivot=new THREE.Group();pivot.rotation.order='YXZ';scene.add(pivot);
    let selected=[],baseline=null;
    const pose=object=>({position:object.getWorldPosition(new THREE.Vector3()),quaternion:object.getWorldQuaternion(new THREE.Quaternion())});
    function setPose(object,value){
        scene.updateMatrixWorld(true);
        object.position.copy(object.parent.worldToLocal(value.position.clone()));
        object.quaternion.copy(object.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(value.quaternion));
        object.updateMatrixWorld(true);
    }
    const roots=()=>selected.map(name=>groups[name]).filter(object=>{
        for(let parent=object.parent;parent;parent=parent.parent)if(selected.some(name=>groups[name]===parent))return false;
        return true;
    });
    function refresh(){
        baseline=null;scene.updateMatrixWorld(true);
        if(selected.length<2)return;
        const objects=roots();pivot.position.set(0,0,0);
        for(const object of objects)pivot.position.add(object.getWorldPosition(new THREE.Vector3()));
        pivot.position.multiplyScalar(1/objects.length);pivot.quaternion.identity();pivot.updateMatrixWorld(true);
    }
    function choose(names){selected=[...new Set(names)].filter(name=>groups[name]);refresh();}
    const target=()=>selected.length>1?pivot:selected.length?groups[selected[0]]:null;
    function begin(){
        if(selected.length<2)return;
        baseline={pivot:pose(pivot),objects:roots().map(object=>({object,...pose(object)}))};
    }
    function change(){
        if(!baseline)return;
        const rotation=pivot.quaternion.clone().multiply(baseline.pivot.quaternion.clone().invert());
        for(const entry of baseline.objects)setPose(entry.object,{
            position:entry.position.clone().sub(baseline.pivot.position).applyQuaternion(rotation).add(pivot.position),
            quaternion:rotation.clone().multiply(entry.quaternion)
        });
    }
    function swap(first,second,position=true,rotation=true){
        if(first===second||!groups[first]||!groups[second]||(!position&&!rotation))return false;
        scene.updateMatrixWorld(true);const a=groups[first],b=groups[second],pa=pose(a),pb=pose(b);
        const desired=new Map([[a,{position:position?pb.position:pa.position,quaternion:rotation?pb.quaternion:pa.quaternion}],
            [b,{position:position?pa.position:pb.position,quaternion:rotation?pa.quaternion:pb.quaternion}]]);
        // Parent first if the pair contains both TV and its status display.
        const depth=object=>{let n=0;for(let p=object.parent;p;p=p.parent)n++;return n;};
        for(const object of [a,b].sort((x,y)=>depth(x)-depth(y)))setPose(object,desired.get(object));
        refresh();return true;
    }
    function bounds(){const box=new THREE.Box3();for(const object of roots())box.union(new THREE.Box3().setFromObject(object));return box;}
    return {choose,refresh,target,begin,change,end:()=>{baseline=null;},swap,bounds,roots,names:()=>[...selected]};
}
