"""Blank-media SNES review sheets and timed native GIFs (Pillow, MIT)."""
import json
from pathlib import Path
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/snes'
SLOT=ROOT/'theme/art-book-slot/_slot'

def sheet(rows,path,width=360):
    columns=max(map(len,rows));height=width*2//3
    out=Image.new('RGB',(columns*width,len(rows)*(height+24)),'#17191d');draw=ImageDraw.Draw(out)
    for j,row in enumerate(rows):
        for i,(source,label) in enumerate(row):
            im=Image.open(source).convert('RGBA');back=Image.new('RGBA',im.size,'#17191d');back.alpha_composite(im)
            out.paste(back.convert('RGB').resize((width,height)),(i*width,j*(height+24)))
            draw.text((i*width+8,j*(height+24)+height+5),label,fill='white')
    out.save(path)

def main():
    views=('front','rear','side','top','bottom','three-quarter')
    rows=[]
    for name in ('snes','snes-us'):
        for version in ('before','after'):
            rows.append([(OUT/'neutral'/version/name/(v+'.png'),f'{name} {version}: {v}') for v in views])
    sheet(rows,OUT/'neutral-comparison.jpg',240)
    rows=[]
    for name in ('snes','snes-us'):
        rows.append([(OUT/'neutral/after'/name/(v+'.png'),f'{name}: {v}')
                     for v in ('three-quarter','loaded-front','loaded-side','loaded-rear')])
    sheet(rows,OUT/'models.jpg')
    for mode in ('insert','eject'):
        rows=[]
        for name in ('snes','snes-us'):
            for version in ('before','after'):
                rows.append([(OUT/version/name/(f'{mode}-{i:02d}.png'),f'{name} {version}: pose {i}/60')
                             for i in (0,18,30,45,60)])
        sheet(rows,OUT/(mode+'-poses.jpg'),288)
        for name in ('snes','snes-us'):
            folder=OUT/'timed'/name;timing=json.loads((folder/(mode+'-timing.json')).read_text())
            # GIF ticks are 10 ms. Round cumulative ticks to preserve total time.
            ticks=round(timing['duration_seconds']*100)
            durations=[10*(round((i+1)*ticks/61)-round(i*ticks/61)) for i in range(61)]
            frames=[Image.open(folder/f'{mode}-scene-{i:02d}.png').convert('RGB').resize((540,360)) for i in range(61)]
            frames[0].save(OUT/(name+'-'+mode+'.gif'),save_all=True,append_images=frames[1:],duration=durations,loop=0)
    rows=[]
    for name in ('snes','snes-us'):
        rows.append([(ROOT/'build/appearance/renders'/style/color/(name+'.png'),f'{name}: {style}, {color}')
                    for style in ('cel','realistic') for color in ('original','blue','red')])
    sheet(rows,OUT/'appearance.jpg',240)

if __name__=='__main__':main()
