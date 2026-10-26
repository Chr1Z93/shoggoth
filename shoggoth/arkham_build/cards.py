from shoggoth.arkham_build.card_fields import export_face_fields
from shoggoth.arkham_build.card_types import is_double_sided, resolve_card_types
from shoggoth.arkham_build.constants import (
    CARD_BACK_TYPE,
    INDETERMINATE_TYPE,
    UNSUPPORTED_TYPE,
)


def export_card(card):
    front = card.front
    back = card.back

    front_type, back_type = resolve_card_types(front, back)

    if front_type == UNSUPPORTED_TYPE:
        return []

    front_face = _export_face(card.id, front, front_type)

    if back_type in {CARD_BACK_TYPE, UNSUPPORTED_TYPE}:
        # TODO: Export back_image_url for unsupported backs.
        return [front_face]

    if is_double_sided(front_type, back_type):
        front_face.update(
            {
                f"back_{field}": value
                for field, value in export_face_fields(back).items()
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

    back_face = _export_face(f"{card.id}_back", back, back_type)
    front_face["back_link"] = back_face["code"]
    back_face["hidden"] = True

    return [front_face, back_face]


def _export_face(code, face, card_type):
    type_code, _ = card_type
    assert type_code not in {None, INDETERMINATE_TYPE}

    return {
        "code": code,
        "pack_code": face.card.project.id,
        "type_code": type_code,
        **export_face_fields(face),
    }
