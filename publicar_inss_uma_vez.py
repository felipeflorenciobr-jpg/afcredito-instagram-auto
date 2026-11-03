#!/usr/bin/env python3
"""Campanha pontual de consignado INSS, com controle de duplicacao por formato."""
import argparse
import json
import time
from pathlib import Path
from bot import api, verify
from campanha_conta_luz import media_check

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "docs" / "inss-2026-11-03-publicacoes.json"
BASE = "https://felipeflorenciobr-jpg.github.io/afcredito-instagram-auto/media/"
IMAGES = {"feed": BASE + "inss-feed-2026-11-03.jpg", "story": BASE + "inss-story-2026-11-03.jpg"}
CAPTION = """👴👵 APOSENTADO OU PENSIONISTA DO INSS? 💙❤️

💰 Você ainda não tem empréstimo consignado ativo?

Pode existir margem consignável disponível no seu benefício! Na AF Crédito Vale do Ribeira, você recebe orientação para consultar as condições e avaliar se essa modalidade faz sentido para seus planos.

✅ Simulação gratuita e sem compromisso
✅ Parcelas descontadas diretamente do benefício
✅ Atendimento personalizado pelo WhatsApp
✅ Orientação sobre taxas, prazos e custo efetivo total (CET)

📲 Quer consultar sua margem? Envie QUERO SIMULAR no WhatsApp!
📞 (13) 99606-0498
🔗 https://wa.me/5513996060498

⚠️ Crédito sujeito à análise, margem, elegibilidade e condições da instituição financeira. A AF Crédito não integra nem representa o INSS.

#ConsignadoINSS #AposentadosINSS #PensionistasINSS #CreditoConsignado #MargemConsignavel #EmprestimoConsignado #AFCredito #ValeDoRibeira #Cajati #CreditoResponsavel"""

def publish_one(ig_user_id, kind, state):
    if kind in state:
        print("JA_PUBLICADO_NAO_REPETIR", kind, state[kind], flush=True)
        return
    url = IMAGES[kind]
    fields = {"image_url": url}
    if kind == "story":
        fields["media_type"] = "STORIES"
    else:
        fields["caption"] = CAPTION
    container = api(ig_user_id + "/media", "POST", fields)
    creation_id = container.get("id")
    if not creation_id:
        raise RuntimeError("A Meta não retornou ID do contêiner. Conferir antes de repetir.")
    for _ in range(16):
        status = api(creation_id + "?fields=status_code").get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError("A Meta recusou o contêiner " + str(status))
        time.sleep(5)
    else:
        raise RuntimeError("A preparação excedeu o prazo. Conferir na Meta antes de repetir.")
    result = api(ig_user_id + "/media_publish", "POST", {"creation_id": creation_id})
    post_id = result.get("id")
    if not post_id:
        raise RuntimeError("Publicação sem ID de retorno. Conferir Instagram antes de repetir.")
    state[kind] = {"id": post_id, "image_url": url}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("INSS_PUBLICADO", kind, post_id, flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("check", "publish"))
    mode = parser.parse_args().mode
    ig_user_id = verify()  # impede publicar fora de @afcredito.valedoribeira
    for kind, url in IMAGES.items():
        media_check(url)
        print("IMAGEM_OK", kind, flush=True)
    if mode == "check":
        print("VALIDACAO_INSS_OK_SEM_PUBLICACAO")
        return
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    for kind in ("feed", "story"):
        publish_one(ig_user_id, kind, state)
    print("CAMPANHA_INSS_CONCLUIDA", list(state), flush=True)

if __name__ == "__main__":
    main()
