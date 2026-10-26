from shoggoth.arkham_build.card_types import (
    CARD_BACK_TYPE,
    UNSUPPORTED_TYPE,
    resolve_card_types,
)
from shoggoth.arkham_build.thumbnails import extract_thumbnail
from shoggoth.files import default_export_folder
from shoggoth.renderer.card_renderer import renderer_for_card


def export_card_images(card, records, url_prefix, renderer):
    """Render each exported face once and add its image URL to its record."""
    folder = default_export_folder(card.project) / "arkham-build" / card.project.id
    folder.mkdir(parents=True, exist_ok=True)
    renderer = renderer_for_card(renderer, card)

    for face, record, prefix, suffix, card_type in _image_targets(card, records):
        filename = f"{card.id}{suffix}.webp"
        thumbnail_filename = f"{card.id}{suffix}_thumbnail.webp"

        with renderer.render_card_side(card, face, include_bleed=False) as image:
            image.save(folder / filename, format="WEBP", quality=80, method=6)

            with extract_thumbnail(image, face, card_type) as thumbnail:
                thumbnail.save(
                    folder / thumbnail_filename, format="WEBP", quality=80, method=6
                )

        record[f"{prefix}image_url"] = f"{url_prefix}/{card.project.id}/{filename}"
        record[f"{prefix}thumbnail_url"] = (
            f"{url_prefix}/{card.project.id}/{thumbnail_filename}"
        )


def _image_targets(card, records):
    primary = records[0]
    front_type, back_type = resolve_card_types(card.front, card.back)
    yield card.front, primary, "", "", front_type
    if back_type == CARD_BACK_TYPE:
        return

    if primary.get("double_sided") or back_type == UNSUPPORTED_TYPE:
        yield card.back, primary, "back_", "_back", back_type
    else:
        assert len(records) == 2, "A supported separate back requires two records"
        yield card.back, records[1], "", "_back", back_type
