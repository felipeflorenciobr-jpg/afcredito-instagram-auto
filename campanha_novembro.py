#!/usr/bin/env python3
"""Campanha revisada de novembro, com mídias curadas e registro por formato."""
import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageOps
import bot

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / "campanhas" / "novembro_2026.json"
MEDIA = ROOT / "docs" / "media"
LEDGER = ROOT / "docs" / "nov2026_published.json"
TZ = ZoneInfo("America/Sao_Paulo")

def posts():
    items = json.loads(PLAN.read_text(encoding="utf-8"))
    keys = [(x["date"], x["slot"]) for x in items]
    if len(keys) != len(set(keys)):
        raise RuntimeError("Datas/horários repetidos")
    if any(any(word in str(x).lower() for word in ("fgts", "loas")) for x in items):
        raise RuntimeError("Conteúdo não autorizado: FGTS ou LOAS")
    return items

def post_key(item):
    return "nov2026_" + item["date"] + "_" + item["slot"]

def prepare():
    from premium_campaign import prepare as prepare_reviewed
    prepare_reviewed(posts())

def validate():
    import hashlib
    from collections import Counter
    from premium_campaign import validate_diversity
    items = posts()
    validate_diversity(items)
    days = Counter(x['date'] for x in items)
    if len(items) != 81 or len(days) != 27 or any(n != 3 for n in days.values()):
        raise RuntimeError('Calendário deve conter 27 dias com três publicações')
    for day in days:
        if {p['slot'] for p in items if p['date']==day} != {'10','14','18'}:
            raise RuntimeError('O dia deve ter os horários 10h14, 14h14 e 18h14')
    for item in posts():
        if item['type'] != ('STORY' if item['slot']=='18' else 'FEED'):
            raise RuntimeError('Formato incompatível com horário')
        if not item.get('artwork') or not item.get('media_sha256'):
            raise RuntimeError('Arte revisada ou hash ausente')
        if '\\n' in item['caption']:
            raise RuntimeError('Legenda contém quebras de linha escapadas')
        filename = MEDIA / (post_key(item) + ".jpg")
        if not filename.is_file():
            raise RuntimeError("Mídia ausente: " + str(filename))
        with Image.open(filename) as image:
            expected = (1080, 1920) if item["type"] == "STORY" else (1080, 1350)
            if image.size != expected:
                raise RuntimeError("Dimensões incorretas em " + filename.name)
        if hashlib.sha256(filename.read_bytes()).hexdigest() != item['media_sha256']:
            raise RuntimeError('Arquivo diverge da prévia revisada: '+filename.name)
    if json.loads((ROOT/'docs/nov2026_calendar.json').read_text()) != items:
        raise RuntimeError('Prévia e calendário divergentes')
    print("Todas as artes têm a proporção esperada; nenhuma publicação enviada.")

def check():
    """Verifica conta/token e mídias hospedadas, sem criar contêiner nem publicar."""
    import hashlib
    validate()
    bot.verify()
    site = os.environ.get('PUBLIC_SITE_URL','').rstrip('/') or 'https://felipeflorenciobr-jpg.github.io/afcredito-instagram-auto'
    # Conferir os três horários do primeiro dia, inclusive bytes após o deploy.
    for item in posts()[:3]:
        req=urllib.request.Request(site+'/media/'+post_key(item)+'.jpg',headers={'User-Agent':'AF-Preflight'})
        with urllib.request.urlopen(req,timeout=30) as response:
            data=response.read()
        if hashlib.sha256(data).hexdigest()!=item['media_sha256']:
            raise RuntimeError('Pages ainda não contém a versão revisada')
    print('PREFLIGHT_OK: identidade e mídias confirmadas; nenhuma publicação enviada.')

def publish(day, slot, dry_run=False):
    item = next((x for x in posts() if x["date"] == day and x["slot"] == slot), None)
    if item is None:
        print("Nenhuma postagem curada prevista:", day, slot)
        return
    key = post_key(item)
    if not (MEDIA / (key + ".jpg")).is_file():
        raise RuntimeError("Mídia ainda não gerada: " + key)
    history = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}
    if key in history:
        print("Registro existente; não repetir:", key, history[key].get("id", history[key].get('status')))
        return
    site = os.environ.get("PUBLIC_SITE_URL", "").rstrip("/") or "https://felipeflorenciobr-jpg.github.io/afcredito-instagram-auto"
    image_url = site + "/media/" + key + ".jpg?v=" + item['media_sha256'][:12]
    print("Candidato:", key, item["type"], image_url)
    if dry_run:
        print("DRY RUN sem publicação:", item["caption"])
        return
    if (os.environ.get("PUBLISH_ENABLED") != "true"
            or os.environ.get("CAMPANHA_NOVEMBRO_APPROVED") != "true"):
        print("Publicação bloqueada: requer as duas variáveis de aprovação.")
        return
    instagram_id = bot.verify()
    request = urllib.request.Request(image_url, method="HEAD", headers={"User-Agent": "AF-Curadoria"})
    with urllib.request.urlopen(request, timeout=25) as response:
        if response.status != 200 or "image/jpeg" not in response.headers.get("Content-Type", ""):
            raise RuntimeError("JPG indisponível no GitHub Pages: " + image_url)
    fields = {"image_url": image_url}
    if item["type"] == "STORY":
        fields["media_type"] = "STORIES"
    else:
        fields["caption"] = item["caption"]
    creation_id = bot.api(instagram_id + "/media", "POST", fields)["id"]
    history[key]={'creation_id':creation_id,'status':'container_created','when':datetime.now(TZ).isoformat()}
    LEDGER.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for attempt in range(12):
        status = bot.api(creation_id + "?fields=status_code").get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError("Contêiner recusado: " + status)
        time.sleep(5)
    else:
        raise RuntimeError("Contêiner pendente. Conferir Instagram antes de tentar novamente.")
    history[key]['status']='publish_attempted'
    LEDGER.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    result = bot.api(instagram_id + "/media_publish", "POST", {"creation_id": creation_id})
    history[key] = {"id": result["id"], "status":"published", "when": datetime.now(TZ).isoformat()}
    LEDGER.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Publicado:", key, result["id"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "validate", "check", "dry-run", "publish"))
    parser.add_argument("--date", default=datetime.now(TZ).date().isoformat())
    parser.add_argument("--slot", choices=("10", "14", "18"), default="10")
    args = parser.parse_args()
    try:
        if args.mode == "prepare":
            prepare()
        elif args.mode == "validate":
            validate()
        elif args.mode == "check":
            check()
        else:
            publish(args.date, args.slot, args.mode == "dry-run")
    except Exception as e:
        safe = str(e).replace(bot.TOKEN, "[TOKEN OCULTO]") if bot.TOKEN else str(e)
        print("ERRO:", safe, file=sys.stderr)
        sys.exit(1)
