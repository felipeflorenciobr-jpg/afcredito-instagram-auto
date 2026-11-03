#!/usr/bin/env python3
"""Publicação ÚNICA do Story CLT da AF Crédito, sem ativar agendamento."""
import argparse, json
from pathlib import Path
from bot import verify
from campanha_conta_luz import media_check, push_container

IMAGE="https://felipeflorenciobr-jpg.github.io/afcredito-instagram-auto/media/clt-story-2026-11-03.jpg"
STATE=Path("docs/clt-story-2026-11-03-published.json")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",required=True,choices=("check","publish"))
    args=parser.parse_args()
    if STATE.exists():
        print("JA_PUBLICADO",STATE.read_text(encoding="utf-8")[:300])
        return
    ig=verify()
    media_check(IMAGE)
    if args.mode=="check":
        print("VALIDACAO_OK, nenhuma publicacao enviada.")
        return
    print("Iniciando publicação pontual de STORY CLT.",flush=True)
    post_id=push_container(ig,IMAGE,True)
    if not post_id:
        raise RuntimeError("Meta não retornou ID do Story; antes de repetir consulte a conta.")
    STATE.write_text(json.dumps({"type":"STORY","image":IMAGE,"id":post_id},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("STORY_CLT_PUBLICADO ID",post_id,flush=True)

if __name__=="__main__":
    main()
