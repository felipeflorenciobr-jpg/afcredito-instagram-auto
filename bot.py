#!/usr/bin/env python3
"""AF Crédito: geração de imagens e publicação via Graph API (Facebook Login)."""
import argparse, csv, json, os, sys, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
DOCS=ROOT/"docs"
MEDIA=DOCS/"media"
NAME="afcredito.valedoribeira"
API="https://graph.facebook.com/"+os.getenv("GRAPH_API_VERSION","v26.0")
TOKEN=os.getenv("META_ACCESS_TOKEN","").strip()
TZ=ZoneInfo("America/Sao_Paulo")
SLOTS=("09","12","15","19")
THEMES=[
 ("CRÉDITO CLT","Como funciona o crédito para trabalhadores CLT?","Confira as condições e os critérios de análise.","Quer simular seu crédito CLT?","Solicite informações pelo WhatsApp."),
 ("CONTA DE LUZ","Crédito pela conta de luz","Entenda a modalidade antes de contratar.","Minha conta de energia é elegível?","A disponibilidade depende das regras do parceiro."),
 ("INSS","Crédito para beneficiários do INSS","Consulte margem, prazo e custo efetivo total.","Como consultar minha margem?","Saiba quais dados são necessários para análise."),
 ("SERVIDORES","Crédito para servidores públicos","Condições variam conforme o convênio.","Meu convênio é atendido?","Solicite informações para sua situação."),
 ("FGTS","Modalidades de crédito com FGTS","Consulte as regras atuais e a elegibilidade.","Como funciona a análise do FGTS?","As condições dependem da instituição financeira."),
 ("EDUCAÇÃO FINANCEIRA","Antes de contratar crédito","Compare o custo efetivo total e o prazo.","O que é CET?","É o custo total anual expresso em percentual."),
 ("AF CRÉDITO","Atendimento AF Vale do Ribeira","Informações claras para uma escolha consciente.","Tem dúvidas sobre crédito?","Converse com a equipe pelo WhatsApp.")
]
def now(): return datetime.now(TZ)
def face(size,bold=False):
    paths=("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    return ImageFont.truetype(paths[0 if bold else 1],size)
def lines(draw,text,width,font):
    out=[]; part=""
    for word in text.split():
        attempt=(part+" "+word).strip()
        if draw.textbbox((0,0),attempt,font=font)[2]<=width: part=attempt
        else:
            if part: out.append(part)
            part=word
    if part: out.append(part)
    return out
def image_for(post):
    story=post["type"]=="STORY"; width=1080; height=1920 if story else 1350
    im=Image.new("RGB",(width,height),(8,27,49)); d=ImageDraw.Draw(im)
    d.ellipse((520,120,1380,980),outline=(47,116,176),width=8)
    d.ellipse((-470,height-500,330,height+300),outline=(230,177,64),width=8)
    d.rounded_rectangle((66,80,216,200),radius=23,fill=(246,189,54))
    d.text((109,109),"AF",font=face(59,True),fill=(8,27,49))
    d.text((241,88),"CRÉDITO",font=face(53,True),fill="white")
    d.text((245,152),"VALE DO RIBEIRA",font=face(27),fill=(202,220,239))
    label_font=face(29,True)
    d.rounded_rectangle((70,370 if story else 270,620,445 if story else 345),radius=22,fill=(246,189,54))
    d.text((99,389 if story else 289),post["theme"],font=label_font,fill=(8,27,49))
    y=550 if story else 440
    for size in (75,68,60,53,46):
        big=face(size,True); tlines=lines(d,post["title"],930,big)
        if len(tlines)<=4: break
    for s in tlines:
        d.text((70,y),s,font=big,fill="white");y+=size+22
    y+=35
    f=face(38)
    for s in lines(d,post["subtitle"],925,f)[:5]:
        d.text((72,y),s,font=f,fill=(219,233,248));y+=56
    bottom=height-(505 if story else 375)
    d.rounded_rectangle((70,bottom,1010,bottom+175),radius=28,fill=(246,189,54))
    d.text((115,bottom+30),"FALE PELO WHATSAPP",font=face(42,True),fill=(9,30,49))
    d.text((115,bottom+101),"(13) 99606-0498",font=face(32,True),fill=(9,30,49))
    d.text((72,height-170),"@afcredito.valedoribeira",font=face(28,True),fill="white")
    d.text((72,height-112),"Sujeito à análise e condições da instituição.",font=face(21),fill=(190,208,226))
    MEDIA.mkdir(parents=True,exist_ok=True)
    im.save(MEDIA/(post["key"]+".jpg"),"JPEG",quality=83,optimize=True)
def make_posts(start,days):
    old=[]
    target=DOCS/"content.json"
    if target.exists(): old=json.loads(target.read_text(encoding="utf-8"))
    posts=[]
    for i in range(days):
        date=start+timedelta(days=i)
        theme=THEMES[date.weekday()]
        for j,slot in enumerate(SLOTS):
            title=theme[1] if j<2 else (theme[3] if j==2 else "Converse com a AF Crédito")
            subtitle=theme[2] if j<2 else (theme[4] if j==2 else "Atendimento pelo WhatsApp (13) 99606-0498.")
            kind="FEED" if slot=="12" else "STORY"
            key=date.isoformat()+"_"+slot
            caption=(title+"\n\n"+subtitle+"\n\nFale com a AF Crédito Vale do Ribeira pelo WhatsApp (13) 99606-0498."
                     "\nCrédito sujeito à análise, elegibilidade, taxas, encargos e condições da instituição financeira."
                     "\n#AFCredito #ValeDoRibeira #CreditoConsciente")
            item={"key":key,"date":date.isoformat(),"slot":slot,"type":kind,"theme":theme[0],
                  "title":title,"subtitle":subtitle,"caption":caption}
            image_for(item);posts.append(item)
    found={p["key"]:p for p in old}
    found.update({p["key"]:p for p in posts})
    all_posts=sorted(found.values(),key=lambda p:p["key"])[-360:]
    DOCS.mkdir(exist_ok=True)
    target.write_text(json.dumps(all_posts,ensure_ascii=False,indent=2),encoding="utf-8")
    with (DOCS/"calendario.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.writer(f,delimiter=";")
        writer.writerow(["Data","Horário São Paulo","Formato","Produto","Título","Legenda"])
        for p in all_posts:writer.writerow([p["date"],p["slot"]+":14",p["type"],p["theme"],p["title"],p["caption"]])
    print("Gerados",len(posts),"conteúdos; nenhum conteúdo publicado.")
def api(path,method="GET",data=None):
    if not TOKEN:raise RuntimeError("META_ACCESS_TOKEN não configurado em GitHub Actions Secrets.")
    url=API+"/"+path.lstrip("/")
    payload=urllib.parse.urlencode(data).encode() if data is not None else None
    req=urllib.request.Request(url,data=payload,method=method,headers={"Authorization":"Bearer "+TOKEN})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg=e.read().decode("utf-8",errors="replace")[:650].replace(TOKEN,"[TOKEN OCULTO]")
        raise RuntimeError("Meta HTTP "+str(e.code)+": "+msg) from None
def find_account():
    explicit=os.getenv("IG_USER_ID","").strip()
    if explicit:return explicit
    # Um Page Access Token pode ser reconhecido como a Página em /me.
    for path in ("me?fields=id,name,instagram_business_account",
                 "me/accounts?fields=id,name,instagram_business_account&limit=100"):
        try:
            r=api(path)
            candidates=r.get("data",[]) if "data" in r else [r]
            for row in candidates:
                node=row.get("instagram_business_account") or {}
                if node.get("id"):
                    try:
                        ig=api(node["id"]+"?fields=id,username")
                        if ig.get("username","").lower()==NAME:return node["id"]
                    except Exception:pass
        except RuntimeError:pass
    raise RuntimeError("Não foi possível localizar o Instagram da AF pela Página. Configure IG_USER_ID no GitHub Secrets e confirme a Página conectada.")
def verify():
    ig_id=find_account()
    account=api(ig_id+"?fields=id,username,account_type")
    username=account.get("username","").lower().lstrip("@")
    if username!=NAME:raise RuntimeError("BLOQUEADO: token/ID pertence a @"+username+", não a @"+NAME)
    if account.get("account_type","").upper()!="BUSINESS":
        raise RuntimeError("Conta deve ser Instagram Business para publicar Stories pela API.")
    print("Instagram correto: @"+username+" | tipo Business | ID "+str(account.get("id")))
    needed={"instagram_basic","instagram_content_publish","pages_show_list","pages_read_engagement"}
    try:
        result=api("me/permissions")
        granted={p.get("permission") for p in result.get("data",[]) if p.get("status")=="granted"}
        if not result.get("data"):
            print("Lista de escopos indisponível neste tipo de token; validação de permissão de publicação ainda pendente.")
        else:
            missing=needed-granted
            if missing:raise RuntimeError("Permissões ausentes no token de usuário: "+", ".join(sorted(missing)))
            print("Permissões Facebook Login: confirmadas.")
    except RuntimeError as e:
        if "Permissões ausentes" in str(e):raise
        print("Permissões não consultáveis por este tipo de token; identidade validada. O teste real depende da Meta.")
    try:
        q=api(ig_id+"/content_publishing_limit?fields=quota_usage,config")
        print("Cota Meta:",json.dumps(q,ensure_ascii=False)[:250])
    except RuntimeError:
        print("A consulta de cota não está disponível para este token; ela não foi validada.")
    return ig_id
def publish(day,slot,dry_run=False):
    key=day+"_"+slot
    items=json.loads((DOCS/"content.json").read_text(encoding="utf-8"))
    post=next((p for p in items if p["key"]==key),None)
    if not post:raise RuntimeError("Arte ausente: "+key)
    history=DOCS/"published.json"
    done=json.loads(history.read_text(encoding="utf-8")) if history.exists() else {}
    if key in done:
        print("Já publicado:",key,done[key]["id"]);return
    repo=os.environ.get("GITHUB_REPOSITORY","")
    if "/" not in repo:raise RuntimeError("GITHUB_REPOSITORY ausente.")
    owner,name=repo.split("/",1)
    site=os.environ.get("PUBLIC_SITE_URL","").strip().rstrip("/") or "https://"+owner+".github.io/"+name
    url=site+"/media/"+key+".jpg"
    print("Publicação candidata:",key,post["type"],url)
    if dry_run:
        print("DRY RUN: nenhuma postagem enviada.");return
    if os.environ.get("PUBLISH_ENABLED")!="true":
        raise RuntimeError("PUBLISH_ENABLED não está true; publicação bloqueada.")
    ig_id=verify()
    req=urllib.request.Request(url,method="HEAD",headers={"User-Agent":"AF-Credito-Bot"})
    with urllib.request.urlopen(req,timeout=20) as resp:
        if resp.status!=200 or "image/jpeg" not in resp.headers.get("Content-Type",""):
            raise RuntimeError("JPG público inacessível: "+url)
    fields={"image_url":url}
    if post["type"]=="STORY":fields["media_type"]="STORIES"
    else:fields["caption"]=post["caption"]
    container=api(ig_id+"/media","POST",fields)["id"]
    for i in range(12):
        state=api(container+"?fields=status_code").get("status_code")
        if state=="FINISHED":break
        if state in ("ERROR","EXPIRED"):raise RuntimeError("Contêiner recusado pela Meta: "+state)
        time.sleep(5)
    else:raise RuntimeError("Processamento do contêiner não concluído; não publique novamente sem verificar o Instagram.")
    published=api(ig_id+"/media_publish","POST",{"creation_id":container})
    done[key]={"id":published["id"],"when":now().isoformat()}
    history.write_text(json.dumps(done,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Publicado:",key,"ID",published["id"])
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=("generate","validate","dry-run","publish"))
    p.add_argument("--start",default="")
    p.add_argument("--days",type=int,default=14)
    p.add_argument("--slot",choices=SLOTS,default="12")
    p.add_argument("--date",default="")
    a=p.parse_args()
    try:
        if a.action=="generate":
            if not 1<=a.days<=35:raise ValueError("days precisa ser entre 1 e 35")
            start=datetime.strptime(a.start,"%Y-%m-%d").date() if a.start else now().date()+timedelta(days=1)
            make_posts(start,a.days)
        elif a.action=="validate":verify()
        else:publish(a.date or now().date().isoformat(),a.slot,a.action=="dry-run")
    except Exception as e:
        print("ERRO:",str(e).replace(TOKEN,"[TOKEN OCULTO]") if TOKEN else str(e),file=sys.stderr)
        sys.exit(1)
