from pathlib import Path

from shoggoth.arkham_build.constants import (
    CARD_BACK_TYPE,
    INDETERMINATE_TYPE,
    UNSUPPORTED_TYPE,
)


_TYPE_MAP = {
    "act_agenda_full": INDETERMINATE_TYPE,
    "chaos": "scenario",
}


_SUPPORTED_TYPES = {
    "act",
    "agenda",
    "asset",
    "enemy",
    "enemy_location",
    "event",
    "investigator",
    "key",
    "location",
    "scenario",
    "skill",
    "story",
    "treachery",
    INDETERMINATE_TYPE,
}


_UNSUPPORTED_TEMPLATES = {
    "enemy_deck",
    "scanning",
    "fullart_scanning",
    "fullart_encounter_with_connections",
}


def resolve_card_types(front, back):
    mapped_front_type = _card_type(front)
    mapped_back_type = _card_type(back)

    return (
        _resolve_indeterminate_type(mapped_front_type, mapped_back_type),
        _resolve_indeterminate_type(mapped_back_type, mapped_front_type),
    )


def is_double_sided(front_type, back_type):
    if front_type == back_type == ("scenario", False):
        return True

    type_code, is_front_backside = front_type
    back_type_code, is_back_backside = back_type
    return (
        type_code in {"act", "agenda", "investigator", "location"}
        and type_code == back_type_code
        and not is_front_backside
        and is_back_backside
    )


def _card_type(card_face):
    template = Path(card_face.get("type") or "").stem
    if template.removesuffix("_back") in _UNSUPPORTED_TEMPLATES:
        return UNSUPPORTED_TYPE

    roles = card_face.card_types
    if not roles:
        return UNSUPPORTED_TYPE

    is_backside = template.endswith("_back")

    if {"act", "agenda"}.issubset(roles):
        return INDETERMINATE_TYPE, is_backside

    if {"enemy", "location"}.issubset(roles):
        return "enemy_location", is_backside

    if roles[0] in {"player", "encounter"}:
        return CARD_BACK_TYPE

    type_code = _TYPE_MAP.get(roles[0], roles[0])
    if type_code not in _SUPPORTED_TYPES:
        return UNSUPPORTED_TYPE

    return type_code, is_backside


def _resolve_indeterminate_type(card_type, other_type):
    """Some card types can only be resolved via the other card side."""
    type_code, is_backside = card_type
    if type_code != INDETERMINATE_TYPE:
        return card_type

    other_type_code, _ = other_type
    if other_type_code not in {"act", "agenda"}:
        return UNSUPPORTED_TYPE

    return other_type_code, is_backside
