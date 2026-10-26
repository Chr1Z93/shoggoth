from shoggoth.arkham_build.output import export_file, export_url
from shoggoth.arkham_build.thumbnails import extract_thumbnail
from shoggoth.renderer.card_renderer import renderer_for_card


_WEBP_OPTIONS = {"format": "WEBP", "quality": 80, "method": 6}


def export_card_images(card, targets, url_prefix, renderer):
    """Render each image target once and add its image URLs to its record."""
    renderer = renderer_for_card(renderer, card)

    for target in targets:
        filename = f"{card.id}{target.file_suffix}.webp"
        thumbnail_filename = f"{card.id}{target.file_suffix}_thumbnail.webp"

        with renderer.render_card_side(card, target.face, include_bleed=False) as image:
            image.save(export_file(card.project, filename), **_WEBP_OPTIONS)

            with extract_thumbnail(image, target.face, target.card_type) as thumbnail:
                thumbnail.save(
                    export_file(card.project, thumbnail_filename), **_WEBP_OPTIONS
                )

        prefix = target.field_prefix
        record = target.record
        record[f"{prefix}image_url"] = export_url(url_prefix, card.project, filename)
        record[f"{prefix}thumbnail_url"] = export_url(
            url_prefix, card.project, thumbnail_filename
        )
