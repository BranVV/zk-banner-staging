import subprocess,csv,io,re,sys,glob
from PIL import Image, ImageDraw
from relabel import bg_and_fg
EN=re.compile(r'^(STOOL|BOX|SHELF|TABLE|CHAIR|RACK|WALL|PANEL|BOOKEND|ORGANIZER|TRIVET|BENCHBACK|DRAWERS|CABINET|BENCH|DESK|CHEST|ISLAND|STAND|HOLDER)$')
def en_pass(p):
    out=subprocess.run(['tesseract',p,'-','-l','eng','--psm','11','tsv'],capture_output=True,text=True).stdout
    rows=[r for r in csv.DictReader(io.StringIO(out),delimiter='\t',quoting=csv.QUOTE_NONE) if (r.get('text') or '').strip()]
    for r in rows:
        for k in ('left','top','width','height'): r[k]=float(r[k])
    im=Image.open(p).convert('L'); d=ImageDraw.Draw(im); done=[]
    for r in rows:
        t=r['text'].strip()
        if not EN.match(t): continue
        x,y,w,h=r['left'],r['top'],r['width'],r['height']
        line=sorted([q for q in rows if abs((q['top']+q['height']/2)-(y+h/2))<h*0.6],key=lambda q:q['left'])
        after=[q for q in line if q['left']>=x+w-1 and len(q['text'].strip())>=3]
        if not after: continue
        y0=int(min(q['top'] for q in line))-4; y1=int(max(q['top']+q['height'] for q in line))+4
        x_end=int(max(q['left']+q['width'] for q in line))+4; gs=int(x); ge=int(after[0]['left'])
        tail=im.crop((ge,y0,x_end,y1)); bg,_=bg_and_fg(im,(gs,y0,x_end,y1)); d.rectangle((gs,y0,x_end,y1),fill=bg); im.paste(tail,(gs,y0)); done.append(t)
    im.save(p); return done
if __name__=='__main__':
    for p in sorted(glob.glob('out/img2/*.png')):
        r=en_pass(p)
        if r: print(p,r)
