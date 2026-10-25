from html import unescape
import re

from shoggoth.arkham_build.constants import (
    NUMERICAL_MAP,
    PER_INVESTIGATOR_MAP,
    SKILL_MAP,
)
from shoggoth.arkham_build.serialization import compact
from shoggoth.arkham_build.text import map_text
from shoggoth.card_translations import load_card_translations


_ENCOUNTER_TYPES = {
    "enemy",
    "enemy_location",
    "treachery",
    "location",
    "act",
    "agenda",
    "chaos",
    "scenario",
    "story",
}


_SLOT_MAP = {
    "hands": "Hand x2",
    "arcanes": "Arcane x2",
}


# TODO: Add a UI JSON field for deck_requirements, deck_options,
# side_deck_requirements, side_deck_options, exile, starts_in_hand,
# deck_options, starts_in_play, sticky_mulligan, attachments,
# card_pool_extension, custom_behavior, and related deckbuilding data.
# Export these values without parsing display text.
# TODO: Parse deck requirements that use custom text or localized labels.
# TODO: Link customization cards to their parent cards and export
# customization_text, customization_options, and customization_change.
def export_face_fields(face):
    text = _text(face)
    return {
        **compact(
            {
                "name": _name(face),
                "subname": _optional_text(face, "subtitle"),
                "subtype_code": _subtype(face),
                "traits": _optional_text(face, "traits"),
                "text": text,
                # TODO: Add localized keyword labels to the asset translation catalogs.
                "permanent": _has_keyword(text, "Permanent"),
                "exceptional": _has_keyword(text, "Exceptional"),
                "myriad": _has_keyword(text, "Myriad"),
                "deck_limit": _deck_limit(face, text),
                "is_unique": _is_unique(face),
                "illustrator": _optional_text(face, "illustrator"),
                "flavor": _optional_text(face, "flavor_text"),
                "position": _parse_position(face.card.project_number) or 0,
                "quantity": face.card.amount,
                "encounter_code": face.card.get("encounter_set") or None,
                "encounter_position": _encounter_position(face),
                "bonded_to": face.card.get_meta("bonded") or None,
                "bonded_count": (
                    face.card.amount if face.card.get_meta("bonded") else None
                ),
                "stage": _stage(face),
                "slot": _slots(face),
                **_factions(face),
            }
        ),
        **_numeric_field(face, "cost"),
        **_xp(face),
        **_numeric_field(face, "health"),
        **_numeric_field(face, "attack", target="enemy_fight"),
        **_numeric_field(face, "evade", target="enemy_evade"),
        **_numeric_field(face, "damage", target="enemy_damage"),
        **_numeric_field(face, "horror", target="enemy_horror"),
        **_numeric_field(face, "clues"),
        **_numeric_field(face, "doom"),
        **_numeric_field(face, "shroud"),
        **_victory(face),
        # TODO: Add sanity_per_investigator to the arkham.build card schema.
        **_numeric_field(face, "sanity"),
        **_skills(face),
    }


def _parse_position(value):
    match = re.match(r"\d+", str(value).strip())
    return int(match[0]) if match else None


def _encounter_position(face):
    if not face.card.get("encounter_set"):
        return None
    return _parse_position(face.card.get("encounter_number"))


def _stage(face):
    if not {"act", "agenda"}.intersection(face.card_types):
        return None
    return _parse_position(face.get("index", None))


def _factions(face):
    classes = face.get("classes", []) or []
    factions = []
    for faction in classes:
        if (
            faction
            in (
                "guardian",
                "seeker",
                "rogue",
                "mystic",
                "survivor",
                "neutral",
                "mythos",
            )
            and faction not in factions
        ):
            factions.append(faction)

    if not factions:
        factions = [_default_faction(face)]

    return dict(zip(("faction_code", "faction2_code", "faction3_code"), factions))


def _subtype(face):
    classes = face.get("classes", []) or []
    if "basic weakness" in classes:
        return "basicweakness"
    if "weakness" in classes:
        return "weakness"
    return None


def _default_faction(face):
    card = face.card
    if card.data.get("encounter_set") and (
        _ENCOUNTER_TYPES.intersection(card.card_types)
        or card.back.card_type == "encounter"
    ):
        return "mythos"
    return "neutral"


def _name(face):
    return map_text(face, "name", face.get("name") or face.card.name).strip()


def _is_unique(face):
    name = map_text(
        face,
        "name",
        face.get("name") or face.card.name,
        tag_map={"<unique>": "<unique>"},
    )
    return "<unique>" in name or None


def _optional_text(face, field):
    value = face.get(field, None)
    if value is None:
        return None
    return map_text(face, field, value).strip() or None


def _text(face):
    text = _optional_text(face, "text")
    if text is not None:
        return text

    entries = face.get("entries", []) or []
    lines = []
    if face.card_type == "investigator":
        for header, value in entries:
            if value is not None and str(value).strip():
                lines.append(f"{header or ''} {value}".strip())
    elif face.card_type in {"chaos", "scenario"}:
        difficulty = face.get("difficulty", None)
        if difficulty:
            lines.append(difficulty)
        lines.extend(_chaos_entry(entry) for entry in entries)
    else:
        return None

    text = "\n".join(line for line in lines if line)
    return map_text(face, "text", text).strip() or None


def _chaos_entry(entry):
    tokens = entry.get("token", [])
    if not isinstance(tokens, list):
        tokens = [tokens]

    labels = []
    for token in tokens:
        if token is None or not str(token).strip():
            continue
        token = str(token).strip()
        token = {"fail": "auto_fail", "blessing": "bless"}.get(token, token)
        labels.append(token if re.fullmatch(r"[+-]?\d+", token) else f"[{token}]")

    label = ", ".join(labels)
    text = entry.get("text") or ""
    return f"{label}: {text}".strip() if label else text.strip()


def _has_keyword(text, keyword):
    if text is None:
        return None
    text = re.sub(
        r"<(?:br|hr)\b[^>]*>|</(?:p|div|blockquote)>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )
    text = unescape(re.sub(r"<[^>]*>", "", text))
    first_line = text.split("\n", 1)[0]
    return f"{keyword}." in first_line or None


def _deck_limit(face, text):
    card = face.card
    if card.back.card_type == "encounter":
        return None
    if card.back.card_type != "player" and not {
        "asset", "event", "skill", "investigator"
    }.intersection(card.card_types):
        return None
    return 1 if _has_keyword(text, "Exceptional") else card.amount


def _slots(face):
    slots = [
        slot.strip().lower()
        for slot in face.get("slots", []) or []
        if slot.strip()
    ]
    return ". ".join(_SLOT_MAP.get(slot, slot.title()) for slot in slots) or None


def _skills(face):
    is_investigator = face.card_type == "investigator"
    skills = {}

    for icon in face.get("icons", ""):
        key = SKILL_MAP.get(icon)
        if key and (not is_investigator or key == "skill_wild"):
            skills[key] = skills.get(key, 0) + 1

    if is_investigator:
        for skill in ("willpower", "intellect", "combat", "agility"):
            skills.update(_numeric_field(face, skill, target=f"skill_{skill}"))

    return skills


def _victory(face):
    values = _numeric_field(face, "victory")
    if values:
        return values

    text = _optional_text(face, "victory")
    if text is None:
        return {}
    text = " ".join(re.sub(r"<[^>]*>", "", text).split())
    parsed = _parse_numeric_value(text)
    if parsed is not None:
        return {"victory": parsed[0]}
    translations = load_card_translations(face.card.effective_language or "en")

    for field, label in (("victory", "Victory"), ("vengeance", "Vengeance")):
        templates = (
            f"{label} {{input}}",
            f"{translations.get(field.upper(), label)} {{input}}",
            translations.get(f"{field} format", ""),
        )
        for template in templates:
            if "{input}" not in template:
                continue
            template = " ".join(re.sub(r"<[^>]*>", "", template).split())
            pattern = re.escape(template).replace(r"\{input\}", r"(\d+)")
            match = re.search(rf"(?<!\w){pattern}(?!\d)", text, re.IGNORECASE)
            if match:
                values[field] = int(match[1])
                break

    return values


def _xp(face):
    if face.get("level") in {"None", "Custom"}:
        return {"xp": None}
    return _numeric_field(face, "level", target="xp")


def _numeric_field(face, key, *, target=None):
    parsed = _parse_numeric_value(face.get(key))
    if parsed is None:
        return {}

    value, per_investigator = parsed
    field = target or key
    values = {field: value}

    if field in PER_INVESTIGATOR_MAP:
        mapping_key, mapping_criteria = PER_INVESTIGATOR_MAP[field]
        if per_investigator == mapping_criteria:
            values[mapping_key] = True

    return values


def _parse_numeric_value(raw_value):
    if raw_value is None:
        return None

    text = str(raw_value).strip()
    per_investigator = text.endswith("<per>")
    text = text.removesuffix("<per>").strip()

    if text in NUMERICAL_MAP:
        return NUMERICAL_MAP[text], per_investigator

    try:
        return int(text), per_investigator
    except ValueError:
        return None
