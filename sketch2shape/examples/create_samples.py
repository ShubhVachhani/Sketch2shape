"""Recreate the bundled original line-art input fixtures with Pillow."""
from pathlib import Path
import shutil
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent
TARGET=ROOT.parent/'app/static/samples'
TARGET.mkdir(parents=True,exist_ok=True)
S=3
def new():
    im=Image.new('RGB',(512*S,512*S),'white')
    return im,ImageDraw.Draw(im)
def line(d,pts,closed=False):
    pts=[(int(x*S),int(y*S)) for x,y in pts]
    if closed:pts.append(pts[0])
    d.line(pts,fill='#20252b',width=5*S,joint='curve')
def ellipse(d,box): d.ellipse(tuple(int(v*S) for v in box),outline='#20252b',width=5*S)
def save(im,name):
    im=im.resize((512,512),Image.Resampling.LANCZOS)
    path=ROOT/f'{name}-sketch.png';im.save(path);shutil.copyfile(path,TARGET/path.name)

im,d=new()
line(d,[(222,75),(290,75),(290,150),(335,205),(335,425),(177,425),(177,205),(222,150)],True)
line(d,[(222,100),(290,100)]);line(d,[(177,275),(335,275)]);line(d,[(177,365),(335,365)])
save(im,'bottle')

im,d=new()
line(d,[(145,155),(325,155),(325,185),(365,185),(390,210),(390,290),(365,320),(325,320),(310,375),(160,375)],True)
line(d,[(325,220),(350,220),(355,230),(355,270),(345,285),(325,285)],True)
line(d,[(145,180),(325,180)]);save(im,'mug')

im,d=new()
line(d,[(75,265),(95,210),(145,150),(205,110),(256,95),(307,110),(367,150),(417,210),(437,265),(295,265),(315,415),(197,415),(217,265)],True)
line(d,[(75,265),(437,265)]);ellipse(d,(170,165,210,202));ellipse(d,(295,170,330,205));ellipse(d,(245,130,272,157))
save(im,'mushroom')

im,d=new()
line(d,[(256,65),(285,105),(315,175),(320,275),(380,370),(320,350),(307,405),(205,405),(192,350),(132,370),(192,275),(197,175),(227,105)],True)
ellipse(d,(220,165,292,237));line(d,[(205,340),(307,340)]);line(d,[(235,405),(235,450),(256,435),(277,450),(277,405)])
save(im,'rocket')

im,d=new()
line(d,[(75,256),(115,205),(175,170),(245,160),(305,180),(345,215),(425,155),(425,357),(345,297),(305,332),(245,352),(175,342),(115,307)],True)
ellipse(d,(130,232,146,248));line(d,[(185,180),(205,220),(210,256),(205,292),(185,333)]);line(d,[(265,205),(310,256),(265,307)],True)
save(im,'fish')

im,d=new()
line(d,[(205,90),(307,90),(370,240),(268,240),(268,385),(345,415),(345,435),(167,435),(167,415),(244,385),(244,240),(142,240)],True)
line(d,[(142,240),(370,240)]);line(d,[(244,240),(268,240)]);save(im,'lamp')

im,d=new()
line(d,[(145,90),(315,90),(315,290),(385,290),(385,425),(355,425),(355,325),(175,325),(175,425),(145,425)],True)
line(d,[(145,290),(315,290)]);line(d,[(175,125),(285,125),(285,250),(175,250)],True);save(im,'chair')

im,d=new()
line(d,[(75,245),(256,85),(330,150),(330,100),(370,100),(370,185),(437,245),(395,245),(395,425),(117,425),(117,245)],True)
line(d,[(117,245),(395,245)]);line(d,[(225,425),(225,310),(285,310),(285,425)])
line(d,[(150,285),(195,285),(195,335),(150,335)],True);line(d,[(315,285),(360,285),(360,335),(315,335)],True)
save(im,'house')

shutil.copyfile(ROOT/'vase-sketch.png',TARGET/'vase-sketch.png')
print('Created 8 additional sketches and copied all 9 into the app.')
