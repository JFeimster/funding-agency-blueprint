"""Local raster artwork and deterministic typography. Input JSON on stdin."""
import sys, json, os, pathlib, tempfile
from PIL import Image, ImageOps, ImageDraw, ImageFont
p=json.load(sys.stdin)
action=sys.argv[1]
dest=pathlib.Path(p["dest"])
if dest.exists() and not p.get("force"):
    print("Skip existing "+str(dest));sys.exit(0)
w,h=int(p["width"]),int(p["height"])
palette=p.get("palette",{})
def font(size,bold=True):
    override=os.environ.get("CREATIVE_FONT_BOLD" if bold else "CREATIVE_FONT_REGULAR")
    names=[override, "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for name in names:
        if name:
            try:return ImageFont.truetype(name,size)
            except OSError:pass
    return ImageFont.load_default(size=size)
def load(f): 
    with Image.open(f) as im:return ImageOps.exif_transpose(im).convert("RGBA")
def fit(im,size,transparent=False):
    if transparent:
        canvas=Image.new("RGBA",size);im=ImageOps.contain(im,size,Image.Resampling.LANCZOS)
        canvas.alpha_composite(im,((size[0]-im.width)//2,(size[1]-im.height)//2));return canvas
    return ImageOps.fit(im,size,Image.Resampling.LANCZOS)
def save(im):
    dest.parent.mkdir(parents=True,exist_ok=True)
    mode=p["format"].upper()
    if mode=="WEBP" and not p.get("transparent"):
        bg=Image.new("RGBA",im.size,"#F6F5EE");bg.alpha_composite(im);im=bg.convert("RGB")
    fd,tmp=tempfile.mkstemp(dir=dest.parent,suffix="."+p["format"]);os.close(fd)
    try:
        im.save(tmp,format=mode,**({"quality":p.get("quality",88),"method":6} if mode=="WEBP" else {"optimize":True}))
        os.replace(tmp,dest)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print(str(dest)+" / "+str(w)+"x"+str(h))
if action=="optimize":
    im=load(p["source"])
    if p.get("transparent") and im.getextrema()[3][0]==255:raise ValueError("Expected real alpha channel")
    save(fit(im,(w,h),p.get("transparent",False)));sys.exit(0)
ink=palette["ink"];lime=palette["lime"];paper=palette["paper"];red=palette["red"]
if action=="logo":
    im=Image.new("RGBA",(w,h));d=ImageDraw.Draw(im)
    box=(int(w*.12),int(h*.30),int(w*.86),int(h*.70));off=int(w*.025)
    d.rectangle(tuple(v+off for v in box),fill=ink)
    d.rectangle(box,fill=lime,outline=ink,width=max(3,w//90))
    f=font(int(w*.23));s=p["brand"]["masthead"];main=s.rstrip(".");dot="." if s.endswith(".") else ""
    tw=d.textlength(s,font=f);x=(w-tw)/2;y=h/2
    d.text((x,y),main,font=f,fill=ink,anchor="lm");d.text((x+d.textlength(main,font=f),y),dot,font=f,fill=red,anchor="lm")
    save(im);sys.exit(0)
if action!="poster":raise ValueError("Unknown action")
layout=p["layout"];bg=palette[layout["background"]];fg=palette[layout["foreground"]]
im=Image.new("RGBA",(w,h),bg);d=ImageDraw.Draw(im)
margin=int(min(w,h)*.055);border=max(3,margin//8)
d.rectangle((border,border,w-border-1,h-border-1),outline=ink,width=border)
def wrap(s,f,limit):
    lines=[];line=""
    for word in s.split():
        test=(line+" "+word).strip()
        if d.textlength(test,font=f)<=limit:line=test;continue
        if line:lines.append(line)
        line=""
        for ch in word:
            if line and d.textlength(line+ch,font=f)>limit:lines.append(line);line=""
            line+=ch
    if line:lines.append(line)
    return lines
def textblock(s,x,y,ww,hh,maxsize,color,bold=True):
    for size in range(maxsize,7,-2):
        f=font(size,bold);lines=wrap(s,f,ww);step=int(size*1.19)
        if step*len(lines)<=hh:
            for i,line in enumerate(lines):d.text((x,y+i*step),line,font=f,fill=color,anchor="lt")
            return y+step*len(lines)
    raise ValueError("Text too long for layout")
mast=p["brand"]["masthead"]+" / "+p["brand"]["name"].upper()
textblock(mast,margin,margin,w-2*margin,margin,int(min(w,h)*.028),fg)
footer=int(h-margin*1.7);d.line((margin,footer,w-margin,footer),fill=fg,width=border)
textblock(p["brand"]["publisher"].upper()+"  /  "+p.get("cta",""),margin,footer+margin//4,w-2*margin,margin,int(min(w,h)*.025),fg)
top=int(margin*2.2);bottom=footer-margin//2
source=load(p["source"])
if layout["mode"]=="split":
    panel=int((w-3*margin)*.46);ah=bottom-top;side=layout.get("art_side","right")
    ax=w-margin-panel if side=="right" else margin
    tx=margin if side=="right" else ax+panel+margin
    tw=w-3*margin-panel
    # Contain transparent cutouts; crop opaque art to panel.
    art=fit(source,(panel,ah),source.getextrema()[3][0]<255)
    im.alpha_composite(art,(ax,top));d.rectangle((ax,top,ax+panel-1,bottom-1),outline=ink,width=border)
    d.rectangle((tx,top,tx+tw,top+border*3),fill=lime if bg!=lime else ink)
    y=textblock(p["headline"].upper(),tx,top+margin//2,tw,int(ah*.64),int(min(w,h)*.105),fg)
    textblock(p.get("subtitle",""),tx,y+margin//3,tw,max(25,bottom-y-margin//3),int(min(w,h)*.035),fg,False)
else:
    tw=w-2*margin;available=bottom-top;art_h=int(available*.47)
    y=textblock(p["headline"].upper(),margin,top,tw,int(available*.34),int(min(w,h)*.10),fg)
    sy=y+margin//4
    end=textblock(p.get("subtitle",""),margin,sy,tw,max(20,int(available*.14)),int(min(w,h)*.032),fg,False)
    ay=max(end+margin//3,bottom-art_h);ah=bottom-ay
    if ah<20:raise ValueError("No artwork space")
    art=fit(source,(tw,ah),source.getextrema()[3][0]<255);im.alpha_composite(art,(margin,ay))
    d.rectangle((margin,ay,w-margin-1,bottom-1),outline=ink,width=border)
save(im)
