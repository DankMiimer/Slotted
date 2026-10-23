"""Synthetic frontend metadata/artwork. Empty files are test launch targets, never games."""
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image,ImageDraw

SYSTEMS=[('snes','Super Nintendo','.sfc'),('nes','Nintendo Entertainment System','.nes'),('gba','Game Boy Advance','.gba'),
         ('ports','Ports','.sh'),('mpv','MPV','.mkv')]

def make(box,source,frontend,tv='panasonic'):
    box=Path(box).absolute();source=Path(source).resolve();frontend=Path(frontend).resolve()
    if box.exists():raise FileExistsError('Use a fresh fixture folder')
    if tv not in ('panasonic','pvm','oldtv','retro'):raise ValueError('Unsupported test TV')
    user=box/'userdata';config=user/'system/configs/emulationstation';config.mkdir(parents=True)
    (user/'system/logs').mkdir();(user/'system/knulli.conf').write_text('')
    share=box/'es-share';share.mkdir();os.symlink(frontend/'resources',share/'resources',target_is_directory=True)
    settings=ET.Element('config')
    values={'ThemeSet':'Slotted','GamelistViewStyle':'automatic','CollectionSystemsAuto':'all,recent,favorites',
        'SlottedHomeConsole':'nes','ShowHelpPrompts':True,'DrawClock':False,'ScreenSaverTime':0,
        'PowerSaverMode':'disabled','InvertButtons':False,'UIMode':'Full','Language':'en_US',
        'subset.slot-tv-model':tv,'subset.slotted-motion':'reduced','subset.slotted-crt':'off','TransitionStyle':'instant'}
    for name,value in values.items():
        tag='bool' if type(value) is bool else 'int' if type(value) is int else 'string'
        ET.SubElement(settings,tag,name=name,value=str(value).lower() if type(value) is bool else str(value))
    ET.ElementTree(settings).write(config/'es_settings.cfg',encoding='utf-8',xml_declaration=True)
    inputs=ET.Element('inputList');keyboard=ET.SubElement(inputs,'inputConfig',type='keyboard',deviceName='Keyboard',deviceGUID='-1')
    keys={'b':13,'a':27,'up':1073741906,'down':1073741905,'left':1073741904,'right':1073741903,
        'start':1073741882,'select':1073741883,'r3':1073741890,'l3':1073741891,'r2':1073741889,'l2':1073741888,'x':120,'y':121}
    for name,key in keys.items():ET.SubElement(keyboard,'input',name=name,type='key',id=str(key),value='1')
    ET.ElementTree(inputs).write(config/'es_input.cfg',encoding='utf-8',xml_declaration=True)
    systems=ET.Element('systemList')
    for name,title,ext in SYSTEMS:
        entry=ET.SubElement(systems,'system')
        for key,value in [('name',name),('fullname',title),('path','/userdata/roms/'+name),('extension',ext),('command','true'),('platform',name),('theme',name)]:ET.SubElement(entry,key).text=value
        folder=user/'roms'/name;(folder/'images').mkdir(parents=True);games=ET.Element('gameList')
        for i in range(42 if name in ('snes','gba') else 12 if name=='nes' else 3):
            title=f'Comet Meadow {i+1:02}' if i else 'A very long synthetic title for the native TV layout clipping check'
            file=f'Test {i+1:02}{ext}';(folder/file).write_bytes(b'');game=ET.SubElement(games,'game')
            art=Image.new('RGB',(256,224),((i*53)%200+30,(i*97)%200+30,(i*31)%200+30));draw=ImageDraw.Draw(art)
            draw.rectangle([8,8,247,215],outline='white',width=4);draw.text((24,100),f'ART {i:02}',fill='white');art.save(folder/'images'/f'{i:02}.png')
            for key,value in [('path','./'+file),('name',title),('image',f'./images/{i:02}.png' if i%3 else './missing.png'),
                 ('desc','Synthetic metadata. Long text must remain clipped to its own TV rectangle. '*12),('developer','Slotted test fixture'),('genre','Test'),('players','1-2')]:ET.SubElement(game,key).text=value
        ET.ElementTree(games).write(folder/'gamelist.xml',encoding='utf-8',xml_declaration=True)
    ET.ElementTree(systems).write(config/'es_systems.cfg',encoding='utf-8',xml_declaration=True)
    theme=user/'themes/Slotted';theme.mkdir(parents=True)
    for item in (source/'theme/slotted').iterdir():os.symlink(item,theme/item.name,target_is_directory=item.is_dir())
    os.symlink(source/'theme/art-book-slot/_slot',theme/'_slot',target_is_directory=True)
    return dict(synthetic=True,source=str(source),tv=tv,systems=[s[0] for s in SYSTEMS],motion='reduced',crt=False)
