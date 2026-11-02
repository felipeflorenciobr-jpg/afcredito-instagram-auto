#!/usr/bin/env python3
"""Publicação manual e pontual da campanha Conta de Luz (sem agendamento)."""
import argparse, json, os, time, urllib.request, urllib.error
from pathlib import Path
from bot import verify, api

ROOT=Path(__file__).resolve().parent
STATE=ROOT/"docs"/"campanha-conta-luz-publicadas.json"
BASE="https://felipeflorenciobr-jpg.github.io/afcredito-instagram-auto/media/"
CAPTION="""💡⚡ CRÉDITO NA CONTA DE LUZ!

💰 Precisando de um dinheiro extra para organizar suas finanças ou colocar seus planos em prática?

Na AF Crédito Vale do Ribeira, você pode consultar condições de crédito com parcelas incluídas na conta de energia elétrica!

✅ Simulação personalizada
✅ Parcelamento na conta de luz
✅ Atendimento pelo WhatsApp
✅ Orientação durante a contratação

📲 Quer saber se sua conta de luz é elegível?

Entre em contato e solicite sua simulação!

📞 (13) 99606-0498
🔗 https://wa.me/5513996060498

🔴🔵 AF Crédito Vale do Ribeira
Soluções financeiras para você.

⚠️ Crédito sujeito à análise, elegibilidade, taxas e condições da instituição financeira.

#AFCredito #CreditoNaContaDeLuz #Emprestimo #ValeDoRibeira #Cajati #CreditoPessoal"""

def media_check(url):
    for attempt in range(8):
        try:
            req=urllib.request.Request(url,method="HEAD",headers={"User-Agent":"AF-Credito-Campaign/1"})
            with urllib.request.urlopen(req,timeout=20) as res:
                ct=res.headers.get("Content-Type","")
                if res.status==200 and "image/jpeg" in ct:
                    print("Imagem pública confirmada:",url,"tipo:",ct)
                    return
                raise RuntimeError("URL da imagem não é JPG público: HTTP "+str(res.status)+", tipo "+ct)
        except Exception as e:
            if attempt==7:raise RuntimeError("Imagem ainda não acessível por HTTPS: "+url+" ("+str(e)[:200]+")")
            time.sleep(8)

def push_container(ig,url,is_story):
    fields={"image_url":url}
    if is_story:fields["media_type"]="STORIES"
    else:fields["caption"]=CAPTION
    container=api(ig+"/media","POST",fields)
    if not container.get("id"):raise RuntimeError("Meta não retornou ID do contêiner.")
    cid=container["id"]
    for _ in range(16):
        s=api(cid+"?fields=status_code").get("status_code")
        if s=="FINISHED":break
        if s in ("ERROR","EXPIRED"):raise RuntimeError("Meta não processou a imagem: "+str(s))
        time.sleep(5)
    else:raise RuntimeError("Tempo de preparação esgotado; consultar Meta antes de repetir.")
    result=api(ig+"/media_publish","POST",{"creation_id":cid})
    return result.get("id")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=["check","publish"],required=True)
    mode=p.parse_args().mode
    ig=verify() # bloqueia perfil errado, consulta permissões
    items=[
      ("feed","campanha-conta-luz-feed.jpg",False),
      ("story","campanha-conta-luz-story.jpg",True),
    ]
    for key,name,_ in items:media_check(BASE+name)
    if mode=="check":
        print("VALIDAÇÃO CONCLUÍDA. NADA PUBLICADO.")
        return
    state=json.loads(STATE.read_text()) if STATE.exists() else {}
    for key,name,is_story in items:
        if key in state:
            print("PULADO (já consta publicado):",key,state[key])
            continue
        print("Publicando:",key)
        post_id=push_container(ig,BASE+name,is_story)
        if not post_id:raise RuntimeError("A Meta não retornou ID de publicação. Não repetir sem conferir Instagram.")
        state[key]=post_id
        STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("PUBLICADO",key,"ID",post_id,flush=True)
    print("CAMPANHA CONCLUÍDA",list(state.keys()))

if __name__=="__main__":main()
