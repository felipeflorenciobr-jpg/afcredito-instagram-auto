import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from publicar import ACCOUNT, INSTAGRAM, PAGE, graph, verify_adset

AD = "120248542277340144"
ADSET = "120248542275680144"
PREVIOUS = "1155715926854313"
DESTINATION = "https://afcreditovaledoribeira.com.br/?produto=cpauto"
CREATIVE_NAME = "CP Auto | Artes 27 de novembro"
AD_FIELDS = "id,adset_id,status,effective_status,creative{id,name,asset_feed_spec,url_tags}"
FORMAT_FILES = {"feed": "feed", "vertical": "vertical", "quadrada": "quadrada"}


def upload(filename):
    path = Path(__file__).with_name(filename + ".jpg")
    response = graph(f"{ACCOUNT}/adimages", "POST", bytes=base64.b64encode(path.read_bytes()).decode("ascii"))
    images = list(response.get("images", {}).values())
    if len(images) != 1 or not images[0].get("hash"):
        raise RuntimeError(f"A Meta não confirmou a imagem {filename}.")
    return images[0]["hash"]


def new_spec(previous, hashes):
    keys = ("ad_formats", "optimization_type", "bodies", "titles", "descriptions", "link_urls", "call_to_action_types")
    spec = {key: previous[key] for key in keys if key in previous}
    for key in ("bodies", "titles", "descriptions", "link_urls"):
        for item in spec.get(key, []):
            if "adlabels" in item:
                item["adlabels"] = [{"name": label["name"]} for label in item["adlabels"]]
    spec["images"] = [{"hash": value, "adlabels": [{"name": name}]} for name, value in hashes.items()]
    old_rules = {}
    for rule in previous["asset_customization_rules"]:
        filters = {key: value for key, value in rule["customization_spec"].items() if key not in {"age_min", "age_max"}}
        old_rules[tuple(filters.get("facebook_positions", []) + filters.get("instagram_positions", []))] = rule

    def rule(platform, positions, image, from_positions):
        source = old_rules[tuple(from_positions)]
        filters = {"publisher_platforms": [platform], f"{platform}_positions": positions} if platform else {}
        result = {"customization_spec": filters, "image_label": {"name": image}}
        for label in ("body_label", "title_label", "description_label", "link_url_label"):
            if label in source:
                result[label] = {"name": source[label]["name"]}
        return result

    rules = [
        rule("facebook", ["story", "facebook_reels"], "vertical", ["facebook_reels"]),
        rule("instagram", ["story", "reels"], "vertical", ["story", "reels"]),
        rule("messenger", ["story"], "vertical", ["story"]),
        rule("facebook", ["feed", "profile_feed"], "feed", []),
        rule("instagram", ["stream"], "feed", []),
        rule(None, [], "quadrada", []),
    ]
    spec["asset_customization_rules"] = [dict(item, priority=i) for i, item in enumerate(rules, 1)]
    return spec


def verify_creative(creative):
    spec = creative["asset_feed_spec"]
    if {link["website_url"] for link in spec["link_urls"]} != {DESTINATION}:
        raise RuntimeError("O endereço de destino do criativo é inesperado.")
    rules = spec["asset_customization_rules"]
    mapped = {}
    for rule in rules:
        filters = rule["customization_spec"]
        for platform in filters.get("publisher_platforms", []):
            for position in filters.get(f"{platform}_positions", []):
                mapped[platform, position] = rule["image_label"]["name"]
    expected = {
        ("facebook", "story"): "vertical", ("facebook", "facebook_reels"): "vertical",
        ("instagram", "story"): "vertical", ("instagram", "reels"): "vertical",
        ("messenger", "story"): "vertical", ("facebook", "feed"): "feed",
        ("instagram", "stream"): "feed",
    }
    if any(mapped.get(position) != label for position, label in expected.items()):
        raise RuntimeError("Os formatos por posicionamento ainda não foram confirmados.")
    return {label["name"]: image["hash"] for image in spec["images"] for label in image["adlabels"]}


def update():
    adset = graph(ADSET, fields="id,status,daily_budget,targeting,destination_type,end_time,regional_regulation_identities")
    verify_adset(adset)
    ad = graph(AD, fields=AD_FIELDS)
    if ad["adset_id"] != ADSET or ad["status"] != "ACTIVE":
        raise RuntimeError("O anúncio ativo esperado não foi encontrado.")
    current = ad["creative"]
    if current["id"] == PREVIOUS:
        verify_creative_destination = {entry["website_url"] for entry in current["asset_feed_spec"]["link_urls"]}
        if verify_creative_destination != {DESTINATION}:
            raise RuntimeError("O endereço de destino mudou.")
        hashes = {key: upload(filename) for key, filename in FORMAT_FILES.items()}
        new = graph(f"{ACCOUNT}/adcreatives", "POST", name=CREATIVE_NAME, url_tags=current["url_tags"],
                    object_story_spec={"page_id": PAGE, "instagram_user_id": INSTAGRAM},
                    asset_feed_spec=new_spec(current["asset_feed_spec"], hashes))
        created = graph(new["id"], fields="asset_feed_spec")
        if verify_creative(created) != hashes:
            raise RuntimeError("A Meta retornou imagens diferentes das enviadas.")
        graph(AD, "POST", creative={"creative_id": new["id"]})
        ad = graph(AD, fields=AD_FIELDS)
        if ad["creative"]["id"] != new["id"]:
            raise RuntimeError("A Meta não vinculou o novo criativo ao anúncio.")
    elif not current.get("name", "").startswith(CREATIVE_NAME):
        raise RuntimeError("O criativo foi alterado desde a conferência.")
    hashes = verify_creative(ad["creative"])
    print("RESULT=" + json.dumps({"ad": AD, "status": ad["effective_status"], "creative": ad["creative"]["id"],
                                 "formats": hashes, "destination": DESTINATION}))


if __name__ == "__main__":
    update()
