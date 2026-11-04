"""Empacota artes revisadas para feed/Story; nunca inventa uma arte de fallback."""
import csv
import hashlib
import html
import json
from pathlib import Path
from datetime import date
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
NAVY = '#061c37'
RED = '#ed001d'

def validate_diversity(items, root=ROOT):
    """Detecta repetição pelo conteúdo da imagem, mesmo sob outro nome."""
    seen={}
    for p in items:
        path=(root/'campanhas'/p['artwork']).resolve()
        if not path.is_relative_to(root/'campanhas') or not path.is_file():
            raise ValueError('Arte ausente ou fora da campanha')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if p.get('source_sha256') and p['source_sha256']!=digest:
            raise ValueError('Master alterado depois da revisão')
        previous=seen.setdefault(digest,[])
        for q in previous:
            if q['type']==p['type']:
                raise ValueError('Arte repetida em '+p['type']+': '+q['date']+' / '+p['date'])
            gap=abs((date.fromisoformat(p['date'])-date.fromisoformat(q['date'])).days)
            if gap<12:
                raise ValueError('Reaproveitamento entre formatos exige intervalo de 12 dias')
        if p.get('theme')=='DATA INSTITUCIONAL' and p['date'] not in ('2026-11-15','2026-11-20'):
            raise ValueError('Arte de data institucional fora da data')
        previous.append(p)

def font(size, bold=False):
    suffix = '-Bold' if bold else ''
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+suffix+'.ttf', size)

def center(draw, text, y, size, fill='white', bold=False):
    f = font(size, bold)
    while draw.textbbox((0,0),text,font=f)[2] > 950:
        size -= 1
        f = font(size,bold)
    width = draw.textbbox((0,0),text,font=f)[2]
    draw.text(((1080-width)//2,y),text,font=f,fill=fill)

def render(item, filename):
    origin = (ROOT/'campanhas'/item['artwork']).resolve()
    if not origin.is_relative_to(ROOT/'campanhas') or not origin.is_file():
        raise ValueError('Arte revisada ausente: '+str(origin))
    with Image.open(origin) as f:
        master = f.convert('RGB')
    # A arte inteira é preservada, sem esticar fotografias nem cortar textos.
    if item['type'] == 'FEED':
        size = (1080,1350)
        art = ImageOps.contain(master,size,Image.Resampling.LANCZOS)
        canvas = Image.new('RGB',size,NAVY)
        canvas.paste(art,((1080-art.width)//2,(1350-art.height)//2))
    else:
        canvas = Image.new('RGB',(1080,1920),NAVY)
        art = ImageOps.contain(master,(1080,1350),Image.Resampling.LANCZOS)
        canvas.paste(art,((1080-art.width)//2,285+(1350-art.height)//2))
        d = ImageDraw.Draw(canvas)
        center(d,item['story_label'],205,34,bold=True)
        d.rectangle((85,265,995,268),fill=RED)
        if item['theme'] == 'DATA INSTITUCIONAL':
            center(d,'AF Vale do Ribeira',1685,35,bold=True)
            center(d,'Respeito que faz parte da nossa história.',1740,25)
        else:
            center(d,'Fale com a AF pelo WhatsApp',1680,36,bold=True)
            center(d,'(13) 99606-0498',1730,44,bold=True)
    canvas.save(filename,'JPEG',quality=94,optimize=True,subsampling=0)
    item['media_sha256'] = hashlib.sha256(Path(filename).read_bytes()).hexdigest()

def write_gallery(items):
    target = ROOT/'docs/previa-novembro-2026.html'
    # JSON vem do mesmo calendário usado para publicar, sem cópia manual divergente.
    template = (ROOT/'gallery_template.html').read_text(encoding='utf-8')
    content=template.replace('__POSTS__',json.dumps(items,ensure_ascii=False).replace('</','<\\/'))
    content=content.replace('__OFFICIAL_COUNT__',str(sum(p['source']=='official' for p in items)))
    target.write_text(content,encoding='utf-8')
    (ROOT/'docs/index.html').write_text('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=previa-novembro-2026.html"><title>AF Crédito — Novembro</title><a href="previa-novembro-2026.html">Abrir calendário de novembro</a></html>\n',encoding='utf-8')
    with (ROOT/'docs/calendario_novembro_2026.csv').open('w',encoding='utf-8-sig',newline='') as f:
        out=csv.writer(f,delimiter=';')
        out.writerow(['Data','Horário de Brasília','Formato','Tema','Título da arte','Origem','Arquivo','Legenda'])
        for p in items:
            out.writerow([p['date'],p['slot']+':14',p['type'],p['theme'],p['creative_title'],p['source'],'media/nov2026_'+p['date']+'_'+p['slot']+'.jpg',p['caption']])

def prepare(items):
    validate_diversity(items)
    media = ROOT/'docs/media'
    media.mkdir(exist_ok=True,parents=True)
    for p in items:
        render(p, media/('nov2026_'+p['date']+'_'+p['slot']+'.jpg'))
    # Sincroniza plano, prévia, CSV e hashes das mídias em uma mesma execução.
    data=json.dumps(items,ensure_ascii=False,indent=2)+'\n'
    (ROOT/'campanhas/novembro_2026.json').write_text(data,encoding='utf-8')
    (ROOT/'docs/nov2026_calendar.json').write_text(data,encoding='utf-8')
    write_gallery(items)
    print(f'{len(items)} mídias preparadas. Nenhuma publicação enviada.')
