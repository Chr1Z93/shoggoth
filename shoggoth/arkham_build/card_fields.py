from html import unescape
import re

from shoggoth.arkham_build.text import map_text, resolve_text
from shoggoth.card_translations import load_card_translations


_NUMERICAL_MAP = {
    "<dash>": None,
    "---": None,
    "X": -2,
    "<star>": -3,
    "?": -4,
}


_PER_INVESTIGATOR_MAP = {
    "clues": ("clues_fixed", False),
    "doom": ("doom_per_investigator", True),
    "enemy_evade": ("enemy_evade_per_investigator", True),
    "enemy_fight": ("enemy_fight_per_investigator", True),
    "health": ("health_per_investigator", True),
    "shroud": ("shroud_per_investigator", True),
}


_SKILL_MAP = {
    "W": "skill_willpower",
    "I": "skill_intellect",
    "C": "skill_combat",
    "A": "skill_agility",
    "Q": "skill_wild",
}


_ENCOUNTER_ROLES = {
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


_FACTIONS = (
    "guardian",
    "seeker",
    "rogue",
    "mystic",
    "survivor",
    "neutral",
    "mythos",
)


# Chaos tokens are named after Shoggoth's chaos_<token>.png overlays.
_CHAOS_TOKEN_ICONS = {
    "fail": "auto_fail",
    "blessing": "bless",
}


_SLOT_MAP = {
    "hands": "Hand x2",
    "arcanes": "Arcane x2",
}


def compact(values):
    """Drop fields without a value."""
    return {key: value for key, value in values.items() if value is not None}


# TODO: Parse deck requirements that use custom text or localized labels.
# TODO: add programmatic deck_options parser.
# TODO: Link customization cards to their parent cards and export
# customization_text, customization_options, and customization_change.
def export_face_fields(face, *, image_mapper=None):
    text = _text(face, image_mapper)
    keywords = _keywords(text)
    return {
        **keywords,
        **compact(
            {
                "name": _name(face, image_mapper),
                "subname": _optional_text(face, "subtitle", image_mapper),
                "subtype_code": _subtype(face),
                "traits": _optional_text(face, "traits", image_mapper),
                "text": text,
                "deck_limit": _deck_limit(face, keywords.get("exceptional", False)),
                "is_unique": _is_unique(face),
                "illustrator": _optional_text(face, "illustrator", image_mapper),
                "flavor": _optional_text(face, "flavor_text", image_mapper),
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
    classes = face.get("classes", [])
    factions = list(dict.fromkeys(c for c in classes if c in _FACTIONS))
    factions = factions or [_default_faction(face)]
    return dict(zip(("faction_code", "faction2_code", "faction3_code"), factions))


def _subtype(face):
    classes = face.get("classes", [])
    if "basic weakness" in classes:
        return "basicweakness"
    if "weakness" in classes:
        return "weakness"
    return None


def _default_faction(face):
    card = face.card
    if card.get("encounter_set") and (
        _ENCOUNTER_ROLES.intersection(card.card_types)
        or card.back.card_type == "encounter"
    ):
        return "mythos"
    return "neutral"


def _raw_name(face):
    return face.get("name") or face.card.name


def _name(face, image_mapper):
    return map_text(face, "name", _raw_name(face), image_mapper=image_mapper).strip()


def _is_unique(face):
    name = resolve_text(face, "name", _raw_name(face))
    return "<unique>" in name.lower() or None


def _optional_text(face, field, image_mapper=None):
    value = face.get(field, None)
    if value is None:
        return None
    return map_text(face, field, value, image_mapper=image_mapper).strip() or None


def _text(face, image_mapper):
    text = _optional_text(face, "text", image_mapper)
    if text is not None:
        return text

    entries = face.get("entries", [])
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
    return map_text(face, "text", text, image_mapper=image_mapper).strip() or None


def _chaos_entry(entry):
    tokens = entry.get("token", [])
    if not isinstance(tokens, list):
        tokens = [tokens]

    labels = []
    for token in tokens:
        if token is None or not str(token).strip():
            continue
        token = str(token).strip()
        token = _CHAOS_TOKEN_ICONS.get(token, token)
        labels.append(token if re.fullmatch(r"[+-]?\d+", token) else f"[{token}]")

    label = ", ".join(labels)
    text = entry.get("text") or ""
    return f"{label}: {text}".strip() if label else text.strip()


def _collapse_tags(text):
    return " ".join(re.sub(r"<[^>]*>", "", text).split())


def _keywords(text):
    # TODO: Add localized keyword labels to the asset translation catalogs.
    if text is None:
        return {}
    text = re.sub(
        r"<(?:br|hr)\b[^>]*>|</(?:p|div|blockquote)>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )
    text = unescape(re.sub(r"<[^>]*>", "", text))
    first_line = text.split("\n", 1)[0]
    return {
        keyword.lower(): True
        for keyword in ("Permanent", "Exceptional", "Myriad")
        if f"{keyword}." in first_line
    }


def _deck_limit(face, is_exceptional):
    card = face.card
    if card.back.card_type == "encounter":
        return None
    if card.back.card_type != "player" and not {
        "asset",
        "event",
        "skill",
        "investigator",
    }.intersection(card.card_types):
        return None
    return 1 if is_exceptional else card.amount


def _slots(face):
    slots = [slot.strip().lower() for slot in face.get("slots", []) if slot.strip()]
    return ". ".join(_SLOT_MAP.get(slot, slot.title()) for slot in slots) or None


def _skills(face):
    is_investigator = face.card_type == "investigator"
    skills = {}

    for icon in face.get("icons", ""):
        key = _SKILL_MAP.get(icon)
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

    text = _collapse_tags(text)
    parsed = _parse_numeric_value(text)
    if parsed is not None:
        return {"victory": parsed[0]}

    translations = load_card_translations(face.card.effective_language or "en")
    return compact(
        {
            field: _labeled_points(text, label, field, translations)
            for field, label in (("victory", "Victory"), ("vengeance", "Vengeance"))
        }
    )


def _labeled_points(text, label, field, translations):
    """Parse e.g. "Victory 2." using the English or translated label."""
    templates = (
        f"{label} {{input}}",
        f"{translations.get(field.upper(), label)} {{input}}",
        translations.get(f"{field} format", ""),
    )
    for template in dict.fromkeys(templates):
        if "{input}" not in template:
            continue
        pattern = re.escape(_collapse_tags(template)).replace(r"\{input\}", r"(\d+)")
        match = re.search(rf"(?<!\w){pattern}(?!\d)", text, re.IGNORECASE)
        if match:
            return int(match[1])
    return None


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

    flag, flag_when = _PER_INVESTIGATOR_MAP.get(field, (None, None))
    if flag and value is not None and per_investigator == flag_when:
        values[flag] = True

    return values


def _parse_numeric_value(raw_value):
    if raw_value is None:
        return None

    text = str(raw_value).strip()
    per_investigator = text.endswith("<per>")
    text = text.removesuffix("<per>").strip()

    if text in _NUMERICAL_MAP:
        return _NUMERICAL_MAP[text], per_investigator

    try:
        return int(text), per_investigator
    except ValueError:
        return None
