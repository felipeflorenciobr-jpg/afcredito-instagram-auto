#!/usr/bin/env python3
"""Publica apenas as datas curadas de novembro de 2026, com dupla aprovação."""
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
    MEDIA.mkdir(parents=True, exist_ok=True)
    for item in posts():
        filename = MEDIA / (post_key(item) + ".jpg")
        if item["source"] == "official":
            origin = ROOT / "campanhas" / "assets_novembro_2026" / item["asset"]
            if not origin.exists():
                raise FileNotFoundError(origin)
            size = (1080, 1920) if item["type"] == "STORY" else (1080, 1350)
            with Image.open(origin) as f:
                art = ImageOps.contain(f.convert("RGB"), size, Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", size, (9, 39, 72))
                canvas.paste(art, ((size[0] - art.width) // 2, (size[1] - art.height) // 2))
                canvas.save(filename, "JPEG", quality=88, optimize=True)
        else:
            bot.image_for({"key": post_key(item), "type": item["type"], "theme": item["theme"],
                           "title": item["title"], "subtitle": item["subtitle"]})
        print("Preparada:", filename.name)
    (ROOT / "docs" / "nov2026_calendar.json").write_text(
        json.dumps(posts(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Nenhuma publicação enviada.")

def validate():
    for item in posts():
        filename = MEDIA / (post_key(item) + ".jpg")
        if not filename.is_file():
            raise RuntimeError("Mídia ausente: " + str(filename))
        with Image.open(filename) as image:
            expected = (1080, 1920) if item["type"] == "STORY" else (1080, 1350)
            if image.size != expected:
                raise RuntimeError("Dimensões incorretas em " + filename.name)
    print("Todas as artes têm a proporção esperada; nenhuma publicação enviada.")

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
        print("Já publicado:", key, history[key]["id"])
        return
    site = os.environ.get("PUBLIC_SITE_URL", "").rstrip("/") or "https://felipeflorenciobr-jpg.github.io/afcredito-instagram-auto"
    image_url = site + "/media/" + key + ".jpg"
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
    for attempt in range(12):
        status = bot.api(creation_id + "?fields=status_code").get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError("Contêiner recusado: " + status)
        time.sleep(5)
    else:
        raise RuntimeError("Contêiner pendente. Conferir Instagram antes de tentar novamente.")
    result = bot.api(instagram_id + "/media_publish", "POST", {"creation_id": creation_id})
    history[key] = {"id": result["id"], "when": datetime.now(TZ).isoformat()}
    LEDGER.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Publicado:", key, result["id"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "validate", "dry-run", "publish"))
    parser.add_argument("--date", default=datetime.now(TZ).date().isoformat())
    parser.add_argument("--slot", choices=("12", "19"), default="12")
    args = parser.parse_args()
    try:
        if args.mode == "prepare":
            prepare()
        elif args.mode == "validate":
            validate()
        else:
            publish(args.date, args.slot, args.mode == "dry-run")
    except Exception as e:
        safe = str(e).replace(bot.TOKEN, "[TOKEN OCULTO]") if bot.TOKEN else str(e)
        print("ERRO:", safe, file=sys.stderr)
        sys.exit(1)
