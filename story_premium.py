#!/usr/bin/env python3
"""Gera Stories editoriais premium 9:16 a partir do calendário curado de novembro.

Usa logo oficial fornecido pela unidade (campanhas/brand/af-credito-logo.png).
Não publica conteúdo nem acessa credenciais da Meta.
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "campanhas" / "brand" / "af-credito-logo.png"

NAVY = (7, 23, 43)
WHITE = (247, 249, 252)
MUTED = (193, 208, 223)
RED = (226, 35, 50)
GOLD = (232, 187, 107)

def font(size, bold=False):
    path = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    return ImageFont.truetype(path, size)

def wrap(draw, text, f, maxwidth, maxlines=None):
    lines, current = [], ""
    for word in str(text).split():
        trial = (current + " " + word).strip()
        if draw.textbbox((0,0), trial, font=f)[2] <= maxwidth:
            current=trial
        else:
            if current: lines.append(current)
            current=word
    if current: lines.append(current)
    if maxlines and len(lines)>maxlines:
        return None
    return lines

def category(item):
    theme = (item.get("theme","")+" "+item.get("title","")).upper()
    if "15 DE NOVEMBRO" in theme or "20 DE NOVEMBRO" in theme or "RESPEITO" in theme:
        return "INSTITUCIONAL","Institucional","INSTITUCIONAL", (234, 188, 108)
    if "CONTA DE LUZ" in theme or "ENERGIA" in theme:
        return "ENERGIA","Conta de luz","ENERGIA",(118, 202, 228)
    if "INSS" in theme:
        return "INSS","INSS","INSS",(234, 190, 113)
    if "CLT" in theme:
        return "CLT","Crédito CLT","CLT",(140, 202, 228)
    if "SERVIDOR" in theme:
        return "SERVIDOR","Servidor público","SERVIDOR",(173, 194, 249)
    if "CONSÓRCIO" in theme:
        return "CONSÓRCIO","Consórcios","CONSÓRCIO",(126, 220, 186)
    if "AUTO" in theme or "ESTRADA" in theme or "VEÍCULO" in theme:
        return "AUTO","Seguro auto","SEGURO",(228, 190, 126)
    if "RESIDENCIAL" in theme or "LAR" in theme or "CASA" in theme:
        return "CASA","Seguro residencial","SEGURO",(228, 190, 126)
    if "EMPRESARIAL" in theme or "NEGÓCIO" in theme or "EMPRESA" in theme:
        return "EMPRESA","Seguro empresarial","SEGURO",(228, 190, 126)
    if "SEGURO" in theme:
        return "SEGURO","Proteção e seguros","SEGURO",(228, 190, 126)
    if "EDUCAÇÃO" in theme or "FINANCEIR" in theme or "CRÉDITO CONSCIENTE" in theme:
        return "EDUCAÇÃO","Crédito consciente","ORIENTAÇÃO",(131, 213, 192)
    return "ATENDIMENTO","Atendimento AF","ATENDIMENTO",GOLD

def draw_icon(d, code, x, y, size, color):
    """Ícones vetoriais originais e neutros: não reproduzem brasões oficiais."""
    k=size/100
    lw=max(5,round(5*k))
    def line(pts):d.line([(round(x+a*k),round(y+b*k)) for a,b in pts],fill=color,width=lw,joint="curve")
    def rect(b,rad=0):d.rounded_rectangle((round(x+b[0]*k),round(y+b[1]*k),round(x+b[2]*k),round(y+b[3]*k)),radius=round(rad*k),outline=color,width=lw)
    if code in ("INSS","CLT"):
        rect((14,20,86,80),12)
        if code=="INSS":
            d.ellipse((x+38*k,y+31*k,x+62*k,y+55*k),outline=color,width=lw)
            line([(28,68),(38,59),(62,59),(72,68)])
        else:
            line([(30,20),(30,11),(70,11),(70,20)])
            line([(14,48),(45,55),(55,55),(86,48)])
    elif code=="ENERGIA":
        line([(55,10),(27,53),(48,53),(41,91),(76,42),(53,42),(55,10)])
    elif code=="SERVIDOR":
        line([(15,36),(50,12),(85,36)]);line([(17,41),(83,41)])
        for xc in (29,50,71):line([(xc,43),(xc,78)])
        line([(14,82),(86,82)])
    elif code=="CONSÓRCIO":
        d.ellipse((x+18*k,y+18*k,x+62*k,y+62*k),outline=color,width=lw)
        d.ellipse((x+40*k,y+40*k,x+85*k,y+85*k),outline=color,width=lw)
        line([(60,62),(69,70),(86,48)])
    elif code=="AUTO":
        line([(20,69),(20,50),(32,32),(68,32),(80,50),(80,69)])
        line([(20,53),(80,53)])
        for cx in (31,69):d.ellipse((x+(cx-7)*k,y+61*k,x+(cx+7)*k,y+75*k),outline=color,width=lw)
    elif code=="CASA":
        line([(12,51),(50,19),(88,51)]);line([(23,49),(23,86),(78,86),(78,49)])
        rect((44,61,60,86),2)
    elif code=="EMPRESA":
        rect((27,18,72,88),4);rect((13,47,27,88),1)
        for xx in (40,56):
            for yy in (34,50,66):line([(xx,yy),(xx+5,yy)])
    elif code=="SEGURO":
        line([(50,10),(83,22),(83,52),(70,73),(50,88),(30,73),(17,52),(17,22),(50,10)])
        line([(34,49),(46,61),(67,37)])
    elif code=="INSTITUCIONAL":
        line([(50,11),(59,40),(90,40),(65,58),(75,88),(50,71),(25,88),(35,58),(10,40),(41,40),(50,11)])
    else:
        for xx,hh in ((22,49),(43,75),(64,32)):
            d.rounded_rectangle((x+xx*k,y+(90-hh)*k,x+(xx+13)*k,y+90*k),radius=5*k,fill=color)

def render_story(item, filename):
    if not LOGO.exists():
        raise FileNotFoundError("Logo oficial ausente: " + str(LOGO))
    w,h=1080,1920
    code,label,keyword,accent=category(item)
    im=Image.new("RGB",(w,h))
    pixels=im.load()
    for yy in range(h):
        t=yy/(h-1)
        base=(int(7+7*t),int(24+10*t),int(47+14*t))
        for xx in range(w):
            pixels[xx,yy]=base
    d=ImageDraw.Draw(im)
    # Painel superior, halos e curvas premium discretas.
    glow=Image.new("RGBA",(w,h),(0,0,0,0));g=ImageDraw.Draw(glow)
    g.ellipse((580,20,1450,890),outline=(*accent,42),width=5)
    g.ellipse((660,100,1400,820),outline=(*accent,31),width=3)
    g.ellipse((-550,1210,520,2280),outline=(*accent,33),width=5)
    for dx in range(8):
        xx=750+dx*48
        g.line([(xx,65),(xx-130,290)],fill=(208,226,236,16),width=2)
    overlay=glow.filter(ImageFilter.GaussianBlur(1))
    im=Image.alpha_composite(im.convert("RGBA"),overlay)
    d=ImageDraw.Draw(im)

    # Logo oficial em cartão claro, para preservar a marca original e sua tagline.
    d.rounded_rectangle((72,232,1008,491),radius=32,fill=(246,248,251,255))
    d.rounded_rectangle((73,233,1007,490),radius=32,outline=(221,228,235,255),width=2)
    logo=Image.open(LOGO).convert("RGBA")
    logo.thumbnail((800,202),Image.Resampling.LANCZOS)
    im.alpha_composite(logo,(int((w-logo.width)/2),int(259+(202-logo.height)/2)))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((72,544,415,601),radius=19,fill=(*accent,245))
    d.text((95,555),label.upper(),font=font(29,True),fill=NAVY)
    d.text((74,648),"INFORMAÇÃO • CONFIANÇA",font=font(23,True),fill=accent)

    title=item["title"].strip()
    y=715
    for size in (83,78,73,68,62,58):
        ff=font(size,True)
        lines=wrap(d,title,ff,925,3)
        if lines:break
    if not lines:
        raise ValueError("Título longo para Story: "+title)
    for line in lines:
        d.text((72,y),line,font=ff,fill=WHITE,stroke_width=0)
        y+=size+23
    d.rounded_rectangle((74,y+20,275,y+31),radius=6,fill=accent)
    # Símbolo próprio por modalidade + texto de apoio.
    icon_y=max(1053,y+92)
    icon_y=min(icon_y,1200)
    d.rounded_rectangle((72,icon_y-10,256,icon_y+174),radius=42,fill=(19,48,73,255),outline=(*accent,255),width=3)
    draw_icon(d,code,106,icon_y+24,114,accent)
    sub=item["subtitle"].strip()
    fy=icon_y+12
    subf=font(36)
    sublines=wrap(d,sub,subf,710,4)
    if sublines is None:
        subf=font(32);sublines=wrap(d,sub,subf,710,4)
    if sublines is None:
        sublines=wrap(d,sub,font(28),710,5) or [sub]
        subf=font(28)
    for line in sublines:
        d.text((291,fy),line,font=subf,fill=MUTED)
        fy+=subf.size+14

    # CTA forte e específico, dentro da área segura para UI do Instagram.
    d.rounded_rectangle((72,1433,1008,1689),radius=39,fill=(239,244,249,255))
    d.rounded_rectangle((86,1452,994,1554),radius=28,fill=(*RED,255))
    d.text((130,1470),"CONSULTE PELO WHATSAPP",font=font(45,True),fill=WHITE)
    d.text((129,1586),"(13) 99606-0498",font=font(63,True),fill=NAVY)
    d.text((73,1740),"@afcredito.valedoribeira",font=font(28,True),fill=MUTED)
    if code!="INSTITUCIONAL":
        disclaimer="Sujeito à análise, elegibilidade e condições da instituição."
    else:
        disclaimer="AF Crédito Vale do Ribeira • Conteúdo institucional"
    d.text((73,1812),disclaimer,font=font(20),fill=(181,196,211))
    d.line((72,1872,1008,1872),fill=(*accent,255),width=2)
    filename=Path(filename)
    filename.parent.mkdir(parents=True,exist_ok=True)
    im.convert("RGB").save(filename,"JPEG",quality=90,optimize=True,subsampling=0)
    print("STORY PREMIUM:",filename.name,code)

if __name__=="__main__":
    import json,sys
    plan=json.loads((ROOT/"campanhas"/"novembro_2026.json").read_text(encoding="utf-8"))
    chosen=[x for x in plan if x.get("type")=="STORY"]
    for p in chosen:
        if len(sys.argv)>1 and p["date"]!=sys.argv[1]:continue
        filename=ROOT/"docs"/"media"/("nov2026_"+p["date"]+"_"+p["slot"]+".jpg")
        render_story(p,filename)
    print("Stories premium preparados; nenhuma postagem enviada.")
