from shoggoth.arkham_build.card_fields import export_face_fields
from shoggoth.arkham_build.card_types import (
    CARD_BACK_TYPE,
    UNSUPPORTED_TYPE,
    is_double_sided,
    resolve_card_types,
)


def export_card(card, *, image_mapper=None):
    front = card.front
    back = card.back

    front_type, back_type = resolve_card_types(front, back)

    if front_type == UNSUPPORTED_TYPE:
        return []

    front_face = _export_face(card.id, front, front_type, image_mapper)

    if back_type in {CARD_BACK_TYPE, UNSUPPORTED_TYPE}:
        return [front_face]

    if is_double_sided(front_type, back_type):
        front_face.update(
            {
                f"back_{field}": value
                for field, value in export_face_fields(
                    back, image_mapper=image_mapper
                ).items()
                if field
                in {
                    "name",
                    "subname",
                    "traits",
                    "text",
                    "flavor",
                    "illustrator",
                }
            }
        )
        front_face["double_sided"] = True
        return [front_face]

    back_face = _export_face(f"{card.id}_back", back, back_type, image_mapper)
    front_face["back_link"] = back_face["code"]
    back_face["hidden"] = True

    return [front_face, back_face]


def apply_card_metadata(card, records):
    """Apply explicit metadata after generated fields, without changing the source."""
    metadata = card.get_meta("arkham_build")
    if not records or not isinstance(metadata, dict):
        return

    records[0].update({key: value for key, value in metadata.items() if key != "back"})
    back_metadata = metadata.get("back")
    if len(records) == 2 and isinstance(back_metadata, dict):
        records[1].update(back_metadata)


def _export_face(code, face, card_type, image_mapper):
    type_code, _ = card_type
    assert type_code is not None

    return {
        "code": code,
        "pack_code": face.card.project.id,
        "type_code": type_code,
        **export_face_fields(face, image_mapper=image_mapper),
    }
