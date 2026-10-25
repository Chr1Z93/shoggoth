import datetime
import logging

from shoggoth.arkham_build.cards import export_card
from shoggoth.arkham_build.constants import BuildMetaProjectStatus
from shoggoth.arkham_build.serialization import compact
from shoggoth.card import Card
from shoggoth.updater import get_current_version as shoggoth_version


logger = logging.getLogger(__name__)


# FIXME: `meta.banner_credit` is missing in UI
# FIXME: `meta.types` is missing in UI
# FIXME: `meta.url` could be derived for Celeano cloud projects
# FIXME: `packs[].icon_url` is missing
# FIXME: `encounter_sets[].icon_url` is missing
def export_project(project, settings):
    # TODO: Export card image_url values from settings.url_pattern.
    # TODO: Export back_image_url for combined double-sided cards.
    # TODO: Export thumbnail_url after a hosted thumbnail URL convention is defined.
    # TODO: Export back_thumbnail_url after back-thumbnail URLs are defined.
    data = project.data

    return {
        "meta": _project_meta(data),
        "data": {
            "cards": list(_export_cards(project)),
            "packs": [{"code": data["id"], "name": data["name"]}],
            "encounter_sets": [
                {"code": set["id"], "name": set["name"]}
                for set in data.get("encounter_sets", [])
            ],
        },
    }


def _export_cards(project):
    project_language = project.language or "en"
    for data in project.data["cards"]:
        card = Card(data, project)
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
        yield from export_card(card)


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
