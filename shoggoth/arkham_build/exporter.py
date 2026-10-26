import datetime
import logging

from shoggoth.arkham_build.cards import export_card
from shoggoth.arkham_build.constants import BuildMetaProjectStatus
from shoggoth.arkham_build.deckbuilding import add_deckbuilding_fields
from shoggoth.arkham_build.images import export_card_images
from shoggoth.arkham_build.serialization import compact
from shoggoth.card import Card
from shoggoth.updater import get_current_version as shoggoth_version


logger = logging.getLogger(__name__)


# FIXME: `meta.banner_credit` is missing in UI
# FIXME: `meta.types` is missing in UI
# FIXME: `meta.url` could be derived for Celeano cloud projects
# FIXME: `packs[].icon_url` is missing
# FIXME: `encounter_sets[].icon_url` is missing
def export_project(project, settings, renderer, *, card_executor):
    """Export data and images.

    card_executor(cards, export_card) must finish all tasks before it returns.
    It must raise on task failure or cancellation.
    """
    assert renderer is not None, "A configured renderer is required"
    assert callable(card_executor), "A card executor is required"
    data = project.data
    url_prefix = (settings.get("url_prefix") or "").strip().rstrip("/")

    return {
        "meta": _project_meta(data),
        "data": {
            "cards": list(_export_cards(project, url_prefix, renderer, card_executor)),
            "packs": [{"code": data["id"], "name": data["name"]}],
            "encounter_sets": [
                {"code": set["id"], "name": set["name"]}
                for set in data.get("encounter_sets", [])
            ],
        },
    }


def _export_cards(project, url_prefix, renderer, card_executor):
    project_language = project.language or "en"
    cards = [Card(data, project) for data in project.data["cards"]]
    exported_cards = []
    image_jobs = []

    for card in cards:
        language = card.effective_language or "en"
        if language != project_language:
            logger.warning(
                "Card language differs from project export language",
                extra={
                    "project_id": project.id,
                    "card_id": card.id,
                    "language": language,
                    "project_language": project_language,
                },
            )
        records = export_card(card)
        if url_prefix and records:
            image_jobs.append((card, records))
        exported_cards.extend(records)

    if image_jobs:
        records_by_id = {card.id: records for card, records in image_jobs}

        def export_images(card):
            export_card_images(card, records_by_id[card.id], url_prefix, renderer)

        card_executor([card for card, _ in image_jobs], export_images)

    add_deckbuilding_fields(cards, exported_cards)
    _apply_card_metadata(cards, exported_cards)
    yield from exported_cards


def _apply_card_metadata(cards, exported_cards):
    """Apply explicit metadata to primary and separate back export records."""
    by_code = {card["code"]: card for card in exported_cards}
    for card in cards:
        exported = by_code.get(card.id)
        metadata = card.get_meta("arkham_build")
        if exported is None or metadata is None:
            continue

        if not isinstance(metadata, dict):
            logger.warning(
                "Card arkham.build metadata must be a JSON object",
                extra={"project_id": card.project.id, "card_id": card.id},
            )
            continue

        back = by_code.get(exported.get("back_link"))

        primary_metadata = dict(metadata)

        back_metadata = primary_metadata.pop("back", None)
        exported.update(primary_metadata)

        if back_metadata is None:
            continue

        if not isinstance(back_metadata, dict):
            logger.warning(
                "Card arkham.build back metadata must be a JSON object",
                extra={"project_id": card.project.id, "card_id": card.id},
            )
            continue

        if back is not None:
            back.update(back_metadata)


def _project_meta(data):
    meta = data.get("meta", {})
    language = meta.get("language") or "en"

    return {
        "author": meta.get("author", ""),
        "code": data["id"],
        "date_updated": datetime.datetime.now().isoformat(),
        "language": language,
        "generator": f"Shoggoth/{shoggoth_version()}",
        "name": data["name"],
        **compact(
            {
                "author": meta.get("author"),
                "banner_url": meta.get("banner_url"),
                "description": meta.get("description"),
                "external_link": meta.get("website_url"),
                "status": meta.get("status")
                if meta.get("status") in BuildMetaProjectStatus
                else None,
                "tags": meta.get("tags"),
            }
        ),
    }
