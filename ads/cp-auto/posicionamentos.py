import base64
import json
import sys
from pathlib import Path

from publicar import ACCOUNT, ADVERTISER, INSTAGRAM, PAGE, REGION, REGIONAL_CATEGORIES, TOKEN, WEBSITE, graph, verify_adset

AD = "120248542277340144"
ADSET = "120248542275680144"
CAMPAIGN = "120248542265170144"
ORIGINAL_CREATIVE = "4574932976062562"
CREATIVE_NAME = "CP Auto | Feed, Stories e Reels | SP"
FB_POSITIONS = ["feed", "story", "facebook_reels_overlay"]
IG_POSITIONS = ["stream", "story", "reels"]
AD_FIELDS = "id,status,effective_status,adset_id,campaign_id,creative{id,name}"
ADSET_FIELDS = "id,status,daily_budget,targeting,destination_type,end_time,regional_regulation_identities,regional_regulated_categories"


def upload_jpeg(name):
    raw_bytes = Path(__file__).with_name(name).read_bytes()
    response = graph(f"{ACCOUNT}/adimages", "POST", bytes=base64.b64encode(raw_bytes).decode("ascii"))
    images = list(response.get("images", {}).values())
    if len(images) != 1 or not images[0].get("hash"):
        raise RuntimeError(f"A Meta não confirmou a imagem {name}.")
    return images[0]["hash"]


def rule(priority, label, platform=None, positions=None):
    filters = {} if platform is None else {"publisher_platforms": [platform], f"{platform}_positions": positions}
    return {"customization_spec": filters, "image_label": {"name": label}, "priority": priority}


def create_placement_creative(original):
    link_data = original["object_story_spec"]["link_data"]
    if link_data["link"] != WEBSITE:
        raise RuntimeError("Destino inesperado no criativo original.")
    format_images = {
        "feed": link_data["image_hash"],
        "vertical": upload_jpeg("arte-vertical.jpg"),
        "facebook_reels": upload_jpeg("arte-quadrada.jpg"),
    }
    return graph(
        f"{ACCOUNT}/adcreatives", "POST", name=CREATIVE_NAME,
        url_tags=original["url_tags"], object_story_spec={"page_id": PAGE, "instagram_user_id": INSTAGRAM},
        asset_feed_spec={
            "ad_formats": ["SINGLE_IMAGE"], "optimization_type": "PLACEMENT",
            "images": [{"hash": image_hash, "adlabels": [{"name": label}]} for label, image_hash in format_images.items()],
            "bodies": [{"text": link_data["message"]}],
            "titles": [{"text": link_data["name"]}],
            "link_urls": [{"website_url": WEBSITE}],
            "call_to_action_types": ["LEARN_MORE"],
            "asset_customization_rules": [
                rule(1, "vertical", "facebook", ["story"]),
                rule(2, "vertical", "instagram", ["story", "reels"]),
                rule(3, "facebook_reels", "facebook", ["facebook_reels_overlay"]),
                rule(4, "feed"),
            ],
        },
    )["id"]


def update():
    if not TOKEN:
        raise RuntimeError("O segredo META_ACCESS_TOKEN não está disponível.")
    adset = graph(ADSET, fields=ADSET_FIELDS)
    ad = graph(AD, fields=AD_FIELDS)
    verify_adset(adset)
    if ad["adset_id"] != ADSET or ad["campaign_id"] != CAMPAIGN:
        raise RuntimeError("O anúncio não está no conjunto CP Auto esperado.")
    if ad["status"] != "ACTIVE" or adset["status"] != "ACTIVE":
        raise RuntimeError("O anúncio ou conjunto não está ativo.")

    creative_id = ad["creative"]["id"]
    if creative_id == ORIGINAL_CREATIVE:
        original = graph(ORIGINAL_CREATIVE, fields="object_story_spec,url_tags")
        creative_id = create_placement_creative(original)
        print(f"CREATIVE_ID={creative_id}", flush=True)
        graph(AD, "POST", creative={"creative_id": creative_id})
    elif ad["creative"].get("name") != CREATIVE_NAME:
        raise RuntimeError("O criativo original foi substituído desde a última verificação.")

    verified = graph(AD, fields=AD_FIELDS)
    if verified["creative"]["id"] != creative_id:
        raise RuntimeError("A Meta não confirmou a troca de criativo.")
    targeting = adset["targeting"]
    if set(targeting.get("facebook_positions", [])) != set(FB_POSITIONS) or set(targeting.get("instagram_positions", [])) != set(IG_POSITIONS):
        locations = {"regions": [{"key": REGION}]}
        if targeting["geo_locations"].get("location_types"):
            locations["location_types"] = targeting["geo_locations"]["location_types"]
        graph(
            ADSET, "POST", name="CP Auto | São Paulo | Feed, Stories e Reels | R$30/dia",
            regional_regulated_categories=REGIONAL_CATEGORIES, regional_regulation_identities=ADVERTISER,
            targeting={"geo_locations": locations, "publisher_platforms": ["facebook", "instagram"],
                       "facebook_positions": FB_POSITIONS, "instagram_positions": IG_POSITIONS,
                       "targeting_automation": targeting["targeting_automation"]},
        )
    final = graph(ADSET, fields=ADSET_FIELDS)
    verify_adset(final)
    if adset["end_time"] != final["end_time"]:
        raise RuntimeError("A Meta alterou o horário de término.")
    targeting = final["targeting"]
    if set(targeting.get("facebook_positions", [])) != set(FB_POSITIONS) or set(targeting.get("instagram_positions", [])) != set(IG_POSITIONS):
        raise RuntimeError("A Meta retornou posicionamentos diferentes dos solicitados.")
    print("RESULT=" + json.dumps({"ad": graph(AD, fields=AD_FIELDS), "adset": final}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        update()
    except Exception as exc:
        message = str(exc).replace(TOKEN, "[redigido]") if TOKEN else str(exc)
        print(f"ERRO: {message}", file=sys.stderr)
        raise SystemExit(1) from None
