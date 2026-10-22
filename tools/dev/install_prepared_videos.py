"""Install verified square-pixel preview copies and reversible video-only links.

Requires stopped ES. Originals stay intact. A journal records each old/new video
field and copies affected gamelists before editing; restore changes only links
still owned by this update, preserving subsequent play counts and other metadata.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import xml.etree.ElementTree as E


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return E.parse(path,E.XMLParser(target=E.TreeBuilder(insert_comments=True)))


def save(tree,path):
    path=Path(path)
    with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.slot-video-',suffix='.xml',delete=False) as f:
        stage=Path(f.name)
    try:
        tree.write(stage,encoding='utf-8',xml_declaration=True)
        os.replace(stage,path)
    finally:
        stage.unlink(missing_ok=True)


def install(root,plan,archive,journal):
    root,journal=Path(root).resolve(),Path(journal)
    if journal.exists():
        raise FileExistsError('Keep the existing journal: '+str(journal))
    entries=json.loads(Path(plan).read_text())
    replacements={}
    for entry in entries:
        source,target=Path(entry['path']).resolve(),Path(entry['target']).resolve()
        if not source.is_relative_to(root) or not target.is_relative_to(root):
            raise ValueError('Preview path escapes ROM library')
        if target.parent!=source.parent/'.slot-square-pixels' or source==target:
            raise ValueError('Unexpected preview cache path')
        if not re.fullmatch(r'[0-9a-f]{16}\.mp4',entry['archive']):
            raise ValueError('Invalid archive member')
        if digest(source)!=entry['original_sha256']:
            raise ValueError('Original clip changed: '+str(source))
        if target.exists() and digest(target)!=entry['preview_sha256']:
            raise FileExistsError('Keep existing preview: '+str(target))
        replacements[source]=entry
    changes,trees=[],{}
    for path in root.glob('*/gamelist.xml'):
        tree=load(path)
        for game in tree.getroot().iter('game'):
            video=game.find('video')
            if video is None or not video.text:
                continue
            source=(path.parent/video.text).resolve()
            if source not in replacements:
                continue
            target=Path(replacements[source]['target'])
            try:new='./'+target.relative_to(path.parent).as_posix()
            except ValueError:new=str(target)
            changes.append(dict(gamelist=str(path),rom=game.findtext('path'),old=video.text,new=new))
            video.text=new
            trees[path]=tree
    journal.mkdir(parents=True)
    hashes={}
    for path in trees:
        copied=journal/(path.parent.name+'-gamelist.xml')
        hashes[str(path)]=digest(path)
        shutil.copy2(path,copied)
        if digest(copied)!=hashes[str(path)]:
            raise ValueError('Gamelist backup mismatch')
    record=dict(root=str(root),entries=entries,changes=changes,gamelists=hashes)
    (journal/'journal.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    with tarfile.open(archive) as tar:
        for entry in entries:
            target=Path(entry['target'])
            if target.exists():continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent,prefix='.preparing-',delete=False) as f:
                stage=Path(f.name)
            try:
                member=tar.getmember(entry['archive'])
                if not member.isfile():
                    raise ValueError('Prepared clip must be a regular archive member')
                with tar.extractfile(member) as stream, stage.open('wb') as output:
                    shutil.copyfileobj(stream,output)
                if digest(stage)!=entry['preview_sha256']:
                    raise ValueError('Prepared clip hash mismatch')
                target.hardlink_to(stage)
            finally:stage.unlink(missing_ok=True)
    # Publish gamelists only after every corrected clip is available and original
    # sources and current gamelists still match the pre-edit hashes.
    for entry in entries:
        if digest(entry['path'])!=entry['original_sha256']:
            raise ValueError('Original changed before publication')
    for path,expected in hashes.items():
        if digest(path)!=expected:raise ValueError('Gamelist changed before publication')
    for path,tree in trees.items():save(tree,path)
    return dict(copies=len(entries),links=len(changes),gamelists=len(trees),journal=str(journal))


def restore(journal):
    record=json.loads((Path(journal)/'journal.json').read_text())
    restored,skipped=0,0
    for path in {item['gamelist'] for item in record['changes']}:
        tree=load(path)
        nodes={game.findtext('path'):game for game in tree.getroot().iter('game')}
        changed=False
        for item in record['changes']:
            if item['gamelist']!=path:continue
            game=nodes.get(item['rom'])
            video=game.find('video') if game is not None else None
            if video is None or video.text!=item['new']:
                skipped+=1
                continue
            video.text=item['old'];restored+=1;changed=True
        if changed:save(tree,path)
    return dict(restored=restored,skipped=skipped)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='action',required=True)
    create=commands.add_parser('install')
    for name in ('root','plan','archive','journal'):create.add_argument(name,type=Path)
    undo=commands.add_parser('restore');undo.add_argument('journal',type=Path)
    options=parser.parse_args()
    if os.name=='posix' and subprocess.run(['pidof','emulationstation'],capture_output=True).returncode==0:
        parser.error('Stop EmulationStation before updating video links')
    print(json.dumps(install(options.root,options.plan,options.archive,options.journal)
                     if options.action=='install' else restore(options.journal)))
