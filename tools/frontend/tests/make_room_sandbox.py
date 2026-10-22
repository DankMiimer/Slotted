"""Fresh host-only room fixture; never touches device /userdata or authored layouts."""
from pathlib import Path
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

repo=Path(__file__).resolve().parents[3]
box=Path(sys.argv[1]).resolve()
if box.exists():raise SystemExit('Use a fresh sandbox path: '+str(box))
subprocess.run([sys.executable,str(repo/'spikes/slotted-phase0/tvhost/make_sandbox.py'),str(box),'B'],check=True)
user=box/'userdata'
(user/'system/knulli.conf').write_text('')
settings=user/'system/configs/emulationstation/es_settings.cfg'
doc=ET.parse(settings)
for item in doc.getroot():
    if item.get('name')=='ThemeSet':item.set('value','Slotted')
    if item.get('name')=='GamelistViewStyle':item.set('value','automatic')
ET.SubElement(doc.getroot(),'string',name='CollectionSystemsAuto',value='all,recent,favorites')
ET.SubElement(doc.getroot(),'string',name='SlottedHomeConsole',value='nes')
# Optional short screensaver for idle checks: SLOT_ROOM_SCREENSAVER="milliseconds[:behavior]".
if os.environ.get('SLOT_ROOM_SCREENSAVER'):
    ms,_,behavior=os.environ['SLOT_ROOM_SCREENSAVER'].partition(':')
    for item in list(doc.getroot()):
        if item.get('name') in ('ScreenSaverTime','ScreenSaverBehavior'):doc.getroot().remove(item)
    ET.SubElement(doc.getroot(),'int',name='ScreenSaverTime',value=str(int(ms)))
    ET.SubElement(doc.getroot(),'string',name='ScreenSaverBehavior',value=behavior or 'dim')
doc.write(settings,encoding='utf-8',xml_declaration=True)
inputs=user/'system/configs/emulationstation/es_input.cfg'
doc=ET.parse(inputs)
for name,key in [('r3',1073741890),('l3',1073741891),('r2',1073741889),('l2',1073741888)]:
    ET.SubElement(doc.getroot()[0],'input',name=name,type='key',id=str(key),value='1')
doc.write(inputs,encoding='utf-8',xml_declaration=True)
theme=user/'themes/Slotted';theme.mkdir()
for item in (repo/'theme/slotted').iterdir():os.symlink(item,theme/item.name,target_is_directory=item.is_dir())
os.symlink(repo/'theme/art-book-slot/_slot',theme/'_slot',target_is_directory=True)
systems=user/'system/configs/emulationstation/es_systems.cfg';doc=ET.parse(systems)
for name,title,ext,count in [('gba','Game Boy Advance','.gba',42),('ports','Ports','.sh',3),('mpv','MPV','.mkv',2)]:
    entry=ET.SubElement(doc.getroot(),'system')
    for key,value in [('name',name),('fullname',title),('path','/userdata/roms/'+name),('extension',ext),('command','true'),('platform',name),('theme',name)]:ET.SubElement(entry,key).text=value
    folder=user/'roms'/name;folder.mkdir()
    games=ET.Element('gameList')
    for i in range(count):
        file=f'Test {i+1:02}{ext}';(folder/file).write_bytes(b'');game=ET.SubElement(games,'game')
        for key,value in [('path','./'+file),('name',f'{title} test {i+1:02}'),('image','/userdata/roms/snes/images/00.png'),('desc','Host fixture. No real game or media data.')]:ET.SubElement(game,key).text=value
    ET.ElementTree(games).write(folder/'gamelist.xml',encoding='utf-8',xml_declaration=True)
doc.write(systems,encoding='utf-8',xml_declaration=True)
print('Fresh Slotted fixture:',box)
