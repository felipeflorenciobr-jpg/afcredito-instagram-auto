import json

from publicar import ACCOUNT, INSTAGRAM, PAGE, WEBSITE, graph, verify_adset

AD = "120248542277340144"
ADSET = "120248542275680144"
ORIGINAL = "29074363028929593"
PLACEMENT = "facebook_reels"
AD_FIELDS = "id,status,effective_status,adset_id,creative{id,asset_feed_spec,url_tags}"
ADSET_FIELDS = "id,status,daily_budget,targeting,destination_type,end_time,regional_regulation_identities"

def placement_label(spec):
    for rule in spec["asset_customization_rules"]:
        filters = rule["customization_spec"]
        if "facebook" in filters.get("publisher_platforms", []) and PLACEMENT in filters.get("facebook_positions", []):
            return rule["image_label"]["name"]
    return None

def update():
    adset = graph(ADSET, fields=ADSET_FIELDS)
    verify_adset(adset)
    if PLACEMENT not in adset["targeting"]["facebook_positions"]:
        raise RuntimeError("Os Reels do Facebook não estão selecionados no conjunto.")
    ad = graph(AD, fields=AD_FIELDS)
    if ad["adset_id"] != ADSET or ad["status"] != "ACTIVE":
        raise RuntimeError("O anúncio ativo do CP Auto não foi encontrado.")
    current = ad["creative"]
    spec = current["asset_feed_spec"]
    if placement_label(spec) != "vertical":
        if current["id"] != ORIGINAL or spec["link_urls"][0]["website_url"] != WEBSITE:
            raise RuntimeError("O criativo mudou desde a auditoria.")
        feed_fields = ("ad_formats", "optimization_type", "bodies", "titles", "descriptions", "link_urls", "call_to_action_types")
        replacement = {name: spec[name] for name in feed_fields if name in spec}
        replacement["images"] = [
            {"hash": item["hash"], "adlabels": [{"name": label["name"]} for label in item["adlabels"]]}
            for item in spec["images"]
        ]
        rules = []
        for rule in spec["asset_customization_rules"]:
            filters = {key: value for key, value in rule["customization_spec"].items() if key not in {"age_min", "age_max"}}
            rules.append({"customization_spec": filters, "image_label": {"name": rule["image_label"]["name"]}, "priority": len(rules) + 2})
        replacement["asset_customization_rules"] = [
            {"customization_spec": {"publisher_platforms": ["facebook"], "facebook_positions": [PLACEMENT]},
             "image_label": {"name": "vertical"}, "priority": 1},
            *rules,
        ]
        new = graph(f"{ACCOUNT}/adcreatives", "POST", name="CP Auto | Reels do Facebook 9x16",
                    url_tags=current["url_tags"], object_story_spec={"page_id": PAGE, "instagram_user_id": INSTAGRAM},
                    asset_feed_spec=replacement)
        created = graph(new["id"], fields="asset_feed_spec")
        if placement_label(created["asset_feed_spec"]) != "vertical":
            raise RuntimeError("A Meta não confirmou o formato vertical no criativo.")
        graph(AD, "POST", creative={"creative_id": new["id"]})
        ad = graph(AD, fields=AD_FIELDS)
    if placement_label(ad["creative"]["asset_feed_spec"]) != "vertical":
        raise RuntimeError("A Meta não confirmou o formato vertical no anúncio.")
    print("RESULT=" + json.dumps({"ad": ad["id"], "creative": ad["creative"]["id"],
                                 "status": ad["effective_status"], "facebook_reels": "vertical"}))

if __name__ == "__main__":
    update()
