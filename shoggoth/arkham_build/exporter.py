import datetime

from shoggoth.arkham_build.assets import ImageAssetExporter
from shoggoth.arkham_build.card_fields import compact
from shoggoth.arkham_build.cards import apply_card_metadata, export_card
from shoggoth.arkham_build.deckbuilding import add_deckbuilding_fields
from shoggoth.arkham_build.images import export_card_images
from shoggoth.card import Card
from shoggoth.updater import get_current_version as shoggoth_version


_STATUSES = {"draft", "alpha", "beta", "complete", "final"}


# FIXME: `meta.banner_credit` is missing in UI
# FIXME: `meta.types` is missing in UI
# FIXME: `meta.url` could be derived for Celeano cloud projects
def export_project(project, settings, renderer, *, card_executor):
    assert renderer is not None, "A configured renderer is required"
    assert callable(card_executor), "A card executor is required"

    data = project.data
    url_prefix = (settings.get("url_prefix") or "").strip().rstrip("/")
    assets = ImageAssetExporter(project, url_prefix)

    return {
        "meta": _project_meta(data),
        "data": {
            "cards": _export_cards(
                project, url_prefix, renderer, card_executor, assets
            ),
            "packs": [_export_group(data, assets)],
            "encounter_sets": [
                _export_group(encounter_set, assets)
                for encounter_set in data.get("encounter_sets", [])
            ],
        },
    }


def _export_group(data, assets):
    return {
        "code": data["id"],
        "name": data["name"],
        **compact({"icon_url": assets.export(data.get("icon"))}),
    }


def _export_cards(project, url_prefix, renderer, card_executor, assets):
    cards = [Card(data, project) for data in project.data["cards"]]
    records_by_id = {}
    targets_by_id = {}
    for card in cards:
        records_by_id[card.id], targets_by_id[card.id] = export_card(
            card, image_mapper=assets.map_tag
        )

    def export_images(card):
        export_card_images(card, targets_by_id[card.id], url_prefix, renderer)

    image_cards = [card for card in cards if url_prefix and targets_by_id[card.id]]
    if image_cards:
        card_executor(image_cards, export_images)

    add_deckbuilding_fields(cards, records_by_id)
    for card in cards:
        apply_card_metadata(card, records_by_id[card.id])

    return [record for records in records_by_id.values() for record in records]


def _project_meta(data):
    meta = data.get("meta", {})
    language = meta.get("language") or "en"
    status = meta.get("status")

    return {
        "author": meta.get("author", ""),
        "code": data["id"],
        "date_updated": datetime.datetime.now().isoformat(),
        "language": language,
        "generator": f"Shoggoth/{shoggoth_version()}",
        "name": data["name"],
        **compact(
            {
                "banner_url": meta.get("banner_url"),
                "description": meta.get("description"),
                "external_link": meta.get("website_url"),
                "status": status if status in _STATUSES else "draft",
                "tags": meta.get("tags"),
            }
        ),
    }
