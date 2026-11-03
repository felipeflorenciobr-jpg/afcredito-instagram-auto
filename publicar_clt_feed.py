#!/usr/bin/env python3
"""Publicação pontual e idempotente do feed CLT da AF Crédito."""
import argparse, json, time
from pathlib import Path
from bot import verify, api
from campanha_conta_luz import media_check

URL="https://felipeflorenciobr-jpg.github.io/afcredito-instagram-auto/media/clt-feed-2026-11-03.jpg"
STATE=Path("docs/clt-feed-2026-11-03-published.json")
CAPTION="""💼 TRABALHA DE CARTEIRA ASSINADA?

Você pode ter opções de crédito disponíveis para o seu perfil!

Na AF Crédito Vale do Ribeira, orientamos você a consultar condições de crédito CLT com atendimento personalizado.

✅ Simulação personalizada
✅ Atendimento pelo WhatsApp
✅ Condições conforme análise e elegibilidade

📲 Quer consultar suas condições?
Fale com a AF Crédito Vale do Ribeira.

📞 (13) 99606-0498
🔗 https://wa.me/5513996060498

⚠️ Crédito sujeito à análise, elegibilidade, taxas, encargos e condições da instituição financeira.

#AFCredito #CreditoCLT #CarteiraAssinada #ValeDoRibeira #Cajati #CreditoConsciente"""

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["check","publish"],required=True)
    mode=parser.parse_args().mode
    if STATE.exists():
        print("JA_PUBLICADO_NAO_REPETIR",STATE.read_text(encoding="utf-8")[:300])
        return
    ig_id=verify()
    media_check(URL)
    if mode=="check":
        print("VALIDACAO_OK_SEM_PUBLICACAO")
        return
    print("Iniciando publicação única FEED CLT",flush=True)
    created=api(ig_id+"/media","POST",{"image_url":URL,"caption":CAPTION})
    cid=created.get("id")
    if not cid:
        raise RuntimeError("Sem ID do contêiner Meta; verificar antes de repetir.")
    for i in range(16):
        status=api(cid+"?fields=status_code").get("status_code")
        if status=="FINISHED":break
        if status in ("ERROR","EXPIRED"):
            raise RuntimeError("Meta não preparou a imagem: "+str(status))
        time.sleep(5)
    else:
        raise RuntimeError("Preparação pendente; não repetir sem conferir a Meta.")
    pub=api(ig_id+"/media_publish","POST",{"creation_id":cid})
    pid=pub.get("id")
    if not pid:
        raise RuntimeError("Resposta sem ID de publicação. Conferir feed antes de repetir.")
    STATE.write_text(json.dumps({"type":"FEED","id":pid,"image_url":URL},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("FEED_CLT_PUBLICADO ID",pid,flush=True)

if __name__=="__main__":
    main()
