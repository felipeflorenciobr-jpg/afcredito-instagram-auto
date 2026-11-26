import base64
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

ACCOUNT = "act_1226091822578248"
PAGE = "518959527965739"
INSTAGRAM = "17841471091739370"
REGION = "460"
CATEGORY = "FINANCIAL_PRODUCTS_SERVICES"
CAMPAIGN_NAME = "AF | CP Auto Crefaz | Site | SP | Nov 2026"
ADSET_NAME = "CP Auto | São Paulo | Feeds | R$30/dia"
AD_NAME = "CP Auto | Carro quitado | Arte 4:5"
WEBSITE = "https://afcreditovaledoribeira.com.br/"
URL_TAGS = "utm_source={{site_source_name}}&utm_medium=paid_social&utm_campaign=cp_auto_crefaz_sp&utm_content=arte_feed"
DAILY_BUDGET = 3000
TOKEN = os.environ.get("META_ACCESS_TOKEN", "").strip()


def graph(path, method="GET", **fields):
    params = {}
    for key, value in fields.items():
        params[key] = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list, bool)) else value
    encoded = urlencode(params)
    url = f"https://graph.facebook.com/v24.0/{path}"
    body = None
    if method == "GET" and encoded:
        url += "?" + encoded
    elif method == "POST":
        body = encoded.encode()
    request = Request(url, data=body, headers={"Authorization": f"Bearer {TOKEN}"}, method=method)
    try:
        with urlopen(request, timeout=35) as response:
            return json.load(response)
    except HTTPError as exc:
        try:
            error = json.loads(exc.read()).get("error", {})
        except (ValueError, TypeError):
            error = {}
        details = " | ".join(str(error.get(key) or "") for key in ("error_user_title", "error_user_msg", "message"))
        details = re.sub(r"https?://\S+", "[URL]", details.replace(TOKEN, "[redigido]"))
        raise RuntimeError(f"Meta {method} {path}: HTTP {exc.code}; código {error.get('code')}, subcódigo {error.get('error_subcode')}; {details[:600]}") from None


def find_named(path, name, fields):
    cursor = None
    results = []
    while True:
        query = {"fields": fields, "limit": 100}
        if cursor:
            query["after"] = cursor
        data = graph(path, **query)
        results.extend(item for item in data["data"] if item["name"] == name and item.get("status") not in {"ARCHIVED", "DELETED"})
        paging = data.get("paging", {})
        next_cursor = paging.get("cursors", {}).get("after")
        if not paging.get("next") or not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    if len(results) > 1:
        raise RuntimeError(f"Há mais de um objeto chamado {name}.")
    return next(iter(results), None)


def verify_adset(adset):
    locations = adset["targeting"]["geo_locations"]
    region_keys = [str(region["key"]) for region in locations.get("regions", [])]
    if region_keys != [REGION] or any(locations.get(key) for key in ("countries", "cities", "custom_locations", "zips", "geo_markets", "country_groups", "places")):
        raise RuntimeError("A região efetiva do conjunto não corresponde ao estado de São Paulo.")
    if int(adset["daily_budget"]) != DAILY_BUDGET or adset["destination_type"] != "WEBSITE":
        raise RuntimeError("Orçamento ou destino não corresponde à campanha solicitada.")
    if datetime.strptime(adset["end_time"], "%Y-%m-%dT%H:%M:%S%z") <= datetime.now(timezone.utc):
        raise RuntimeError("O conjunto atingiu a data de término.")


def create_creative():
    image = Path(__file__).with_name("arte.jpg").read_bytes()
    response = graph(f"{ACCOUNT}/adimages", "POST", bytes=base64.b64encode(image).decode("ascii"))
    images = list(response.get("images", {}).values())
    if len(images) != 1 or not images[0].get("hash"):
        raise RuntimeError("A Meta não confirmou o envio da imagem.")
    return graph(
        f"{ACCOUNT}/adcreatives", "POST", name=AD_NAME,
        url_tags=URL_TAGS,
        object_story_spec={
            "page_id": PAGE,
            "instagram_user_id": INSTAGRAM,
            "link_data": {
                "image_hash": images[0]["hash"],
                "link": WEBSITE,
                "name": "Crédito com garantia de veículo",
                "message": "Conheça o crédito pessoal Crefaz com garantia de veículo. Carro quitado e em nome do solicitante, com possibilidade de continuar usando o veículo. Confira no site da AF Crédito Vale do Ribeira. Crédito sujeito à análise.",
                "call_to_action": {"type": "LEARN_MORE", "value": {"link": WEBSITE}},
            },
        },
    )["id"]


def publish():
    if not TOKEN:
        raise RuntimeError("O segredo META_ACCESS_TOKEN não está disponível.")
    account = graph(ACCOUNT, fields="id,account_status,currency")
    if account["account_status"] != 1 or account["currency"] != "BRL":
        raise RuntimeError("A conta autorizada precisa estar ativa e em reais.")
    campaign = find_named(f"{ACCOUNT}/campaigns", CAMPAIGN_NAME, "id,name,status,objective,special_ad_categories,special_ad_category_country")
    if campaign is None:
        campaign_id = graph(
            f"{ACCOUNT}/campaigns", "POST", name=CAMPAIGN_NAME, objective="OUTCOME_TRAFFIC",
            status="PAUSED", buying_type="AUCTION", special_ad_categories=[CATEGORY],
            special_ad_category_country=["BR"], is_adset_budget_sharing_enabled=False,
        )["id"]
        campaign = graph(campaign_id, fields="id,status,objective,special_ad_categories,special_ad_category_country")
    campaign_id = campaign["id"]
    print(f"CAMPAIGN_ID={campaign_id}", flush=True)
    if campaign["objective"] != "OUTCOME_TRAFFIC" or campaign["special_ad_categories"] != [CATEGORY] or campaign["special_ad_category_country"] != ["BR"]:
        raise RuntimeError("A campanha existente não corresponde ao objetivo e à categoria solicitados.")
    adset_fields = "id,name,status,daily_budget,targeting,destination_type,end_time"
    adset = find_named(f"{campaign_id}/adsets", ADSET_NAME, adset_fields)
    if adset is None:
        end = datetime.now(timezone.utc) + timedelta(days=7)
        adset_id = graph(
            f"{ACCOUNT}/adsets", "POST", name=ADSET_NAME, campaign_id=campaign_id,
            status="ACTIVE", daily_budget=DAILY_BUDGET, end_time=end.isoformat(timespec="seconds"),
            billing_event="IMPRESSIONS", optimization_goal="LINK_CLICKS", bid_strategy="LOWEST_COST_WITHOUT_CAP",
            destination_type="WEBSITE",
            targeting={"geo_locations": {"regions": [{"key": REGION}]}, "publisher_platforms": ["facebook", "instagram"],
                       "facebook_positions": ["feed"], "instagram_positions": ["stream"],
                       "targeting_automation": {"advantage_audience": 1}},
        )["id"]
        adset = graph(adset_id, fields=adset_fields)
    verify_adset(adset)
    adset_id = adset["id"]
    print(f"ADSET_ID={adset_id}", flush=True)
    if adset["status"] != "ACTIVE":
        raise RuntimeError("O conjunto existente foi pausado. Confira seu estado no Gerenciador de Anúncios.")
    ad_fields = "id,name,status,effective_status,creative{object_story_spec}"
    ad = find_named(f"{adset_id}/ads", AD_NAME, ad_fields)
    if ad is None:
        creative_id = create_creative()
        ad_id = graph(f"{ACCOUNT}/ads", "POST", name=AD_NAME, adset_id=adset_id, status="ACTIVE", creative={"creative_id": creative_id})["id"]
        ad = graph(ad_id, fields=ad_fields)
    ad_id = ad["id"]
    print(f"AD_ID={ad_id}", flush=True)
    if ad["status"] != "ACTIVE":
        raise RuntimeError("O anúncio existente está pausado. Confira seu estado no Gerenciador de Anúncios.")
    story = ad.get("creative", {}).get("object_story_spec", {})
    link = urlsplit(story.get("link_data", {}).get("link", ""))
    if (link.scheme, link.netloc, link.path or "/") != ("https", "afcreditovaledoribeira.com.br", "/"):
        raise RuntimeError("A Meta não confirmou o destino do anúncio.")
    if campaign["status"] != "ACTIVE":
        graph(campaign_id, "POST", status="ACTIVE")
    state = graph(campaign_id, fields="status,effective_status")
    delivery = graph(ad_id, fields="status,effective_status")
    print("RESULT=" + json.dumps({"campaign": state, "ad": delivery, "adset": adset_id,
                                  "end_time": adset["end_time"], "budget_brl": DAILY_BUDGET / 100,
                                  "website": WEBSITE}, ensure_ascii=False))
    if state.get("status") != "ACTIVE":
        raise RuntimeError("A Meta não confirmou a ativação da campanha.")


if __name__ == "__main__":
    try:
        publish()
    except Exception as exc:
        message = str(exc).replace(TOKEN, "[redigido]") if TOKEN else str(exc)
        print(f"ERRO: {message}", file=sys.stderr)
        raise SystemExit(1) from None
