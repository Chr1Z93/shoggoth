from dataclasses import dataclass
import re

from shoggoth.card import Card
from shoggoth.card_translations import CARD_KEYWORD_DEFAULTS, load_card_translations


@dataclass(frozen=True)
class _LocalizedTag:
    key: str


_VALUE_MAP = {
    "<exn>": lambda face: face.card.project_number,
    "<esn>": lambda face: face.card.encounter_number,
    "<est>": lambda face: getattr(face.card.encounter, "total_cards", None),
    "<copyright>": lambda face: face.card.get("copyright"),
}
_VALUE_PATTERN = re.compile(
    r"<name>|<copy>|<:(?P<element_id>[^ >]*) (?P<field>[^>]+)>|"
    + "|".join(re.escape(tag) for tag in _VALUE_MAP),
    re.IGNORECASE,
)

_ICON_TAG_PATTERN = re.compile(
    r"""<(exi|esi|project\.icon|encounter\.icon)(?=\s|>)((?:[^<>"']|"[^"]*"|'[^']*')*)>""",
    re.IGNORECASE,
)

_ICON_SPAN_PATTERN = r"<icon>[\s\S]*?</icon>"

_TAG_PATTERN = re.compile(
    _ICON_SPAN_PATTERN + r"""|<(?:[^<>"']|"[^"]*"|'[^']*')*>""", re.IGNORECASE
)
TAG_REMOVALS = [
    _ICON_SPAN_PATTERN,
    "<icon>",
    "</icon>",
    "<unique>",
    "<center>",
    "</center>",
    "<left>",
    "</left>",
    "<right>",
    "</right>",
    r"<size\s+\d+>",
    "</size>",
    r'<font\s+"[^"\n]+">',
    "</font>",
    r"<indent\s+\d+>",
    "</indent>",
    r"<margin\s+\d+(?:\s+\d+)*>",
    r"<spacing\s+(?:\d+(?:\.\d*)?|\.\d+)>",
    "<valign>",
    r"<image(?:\s+[^>]*)?>",
    # TODO: Add glyphs to the arkham.build icon font.
    "<resource>",
    "<clues>",
    "<doom>",
    "<entry>",
    "<open>",
]
_TAG_MAP = {
    "<bi>": "<b><i>",
    "</bi>": "</i></b>",
    "<t>": "[[",
    "</t>": "]]",
    "<dbl>": "<u>",
    "</dbl>": "</u>",
    "<quote>": "'",
    "<quoteend>": "'",
    "<dquote>": '"',
    "<dquoteend>": '"',
    "<action>": "[action]",
    "<act>": "[action]",
    "<free>": "[fast]",
    "<reaction>": "[reaction]",
    "<willpower>": "[willpower]",
    "<wil>": "[willpower]",
    "<intellect>": "[intellect]",
    "<int>": "[intellect]",
    "<combat>": "[combat]",
    "<com>": "[combat]",
    "<agility>": "[agility]",
    "<agi>": "[agility]",
    "<wild>": "[wild]",
    "<skull>": "[skull]",
    "<cultist>": "[cultist]",
    "<tablet>": "[tablet]",
    "<elder_thing>": "[elder_thing]",
    "<elder_sign>": "[elder_sign]",
    "<auto_fail>": "[auto_fail]",
    "<blessing>": "[bless]",
    "<curse>": "[curse]",
    "<frost>": "[frost]",
    "<guardian>": "[guardian]",
    "<seeker>": "[seeker]",
    "<rogue>": "[rogue]",
    "<mystic>": "[mystic]",
    "<survivor>": "[survivor]",
    "<per>": "[per_investigator]",
    "<investigator>": "[per_investigator]",
    "<per_large>": "[per_investigator]",
    "<damage>": "[health]",
    "<horror>": "[sanity]",
    "<bullet>": "[bullet]",
    "<resolution>": "→",
    "<codex>": "[codex]",
    "<day>": "[day]",
    "<night>": "[night]",
    "<blood>": "[blood]",
    "<fleur>": "\u269c\ufe0e",
    "<star>": "[star]",
    "<dash>": "-",
    "<sign_1>": "[seal_a]",
    "<sign_2>": "[seal_b]",
    "<sign_3>": "[seal_c]",
    "<sign_4>": "[seal_d]",
    "<sign_5>": "[seal_e]",
    **{tag: _LocalizedTag(tag) for tag in CARD_KEYWORD_DEFAULTS},
}

_TEXT_MAP = {
    "---": "—",
    "--": "–",
    r"\"": '"',
    r"\'": "'",
}
_TEXT_PATTERN = re.compile(
    _TAG_PATTERN.pattern
    + "|"
    + "|".join(re.escape(text) for text in sorted(_TEXT_MAP, key=len, reverse=True))
)


def expand_icon_tags(value, face):
    """Expand project and encounter icon aliases into inline image tags."""
    def replace(match):
        kind = match[1].lower()
        project = face.card.project
        if kind in {"exi", "project.icon"}:
            source = project.icon
        else:
            encounter = face.card.encounter
            source = encounter.icon if encounter else None

        if not source:
            return "" if kind in {"exi", "esi"} else f'<image src=""{match[2]}>'

        source = project.find_file(source) or source
        attributes = ' color="inverted"' if kind in {"exi", "esi"} else match[2]
        return f'<image src="{source}"{attributes}>'

    return _ICON_TAG_PATTERN.sub(replace, value)


def map_text(face, field, value, *, tag_map=None, image_mapper=None):
    mapper = _TextMapper(tag_map, image_mapper)

    # Shoggoth supports references like <copy> or <name> and translations, resolve before mapping
    resolved_text = mapper.resolve_values(face, field, value)

    return _replace_plain_text(mapper.map_tags(face, resolved_text))


def _replace_plain_text(value):
    return _TEXT_PATTERN.sub(
        lambda match: _TEXT_MAP.get(match.group(0), match.group(0)), value
    )


class _TextMapper:
    """Keep translation catalogs and field overrides within one mapping call."""

    def __init__(self, tag_overrides, image_mapper):
        self._tag_overrides = tag_overrides or {}
        self._image_mapper = image_mapper
        self._translations_by_language = {}

    def resolve_values(self, face, field, value, reference_path=frozenset()):
        reference_key = (face.card.id, id(face.data), field, value)

        if reference_key in reference_path:
            raise ValueError(
                f"Circular text reference on card {face.card.id}, field {field}"
            )

        reference_path = reference_path | {reference_key}

        resolved_text = _VALUE_PATTERN.sub(
            lambda match: self._resolve_value(face, field, match, reference_path), value
        )

        return self._translate_asset_keys(face, resolved_text)

    def _resolve_value(self, face, field, match, reference_path):
        tag = match.group(0).lower()

        if tag in _VALUE_MAP:
            resolved_value = _VALUE_MAP[tag](face)
            return "" if resolved_value is None else str(resolved_value)

        if tag == "<name>":
            return self.resolve_values(face, "name", face.card.name, reference_path)

        if tag == "<copy>":
            other_face = face.other_side
            default = other_face.card.name if field == "name" else ""
            copied_value = other_face.get(field) or default
            return self.resolve_values(other_face, field, copied_value, reference_path)

        return self._resolve_reference(face, match, reference_path)

    def _resolve_reference(self, face, match, reference_path):
        element_id = match.group("element_id") or face.card.id

        element = face.card.project.get_by_id(element_id)
        if element is None:
            raise ValueError(f"Unknown text reference: {match.group(0)}")

        referenced_value = element.data
        reference_field = match.group("field").strip()

        field_path = reference_field.split(".")
        for part in field_path:
            if not isinstance(referenced_value, dict) or part not in referenced_value:
                raise ValueError(f"Unknown text reference: {match.group(0)}")
            referenced_value = referenced_value[part]

        if not isinstance(referenced_value, (str, int, float)):
            raise ValueError(f"Invalid text reference: {match.group(0)}")

        referenced_face = face

        if isinstance(element, Card):
            referenced_face = element.back if field_path[0] == "back" else element.front
            reference_field = field_path[-1]

        return self.resolve_values(
            referenced_face, reference_field, str(referenced_value), reference_path
        )

    def map_tags(self, face, value, keyword_path=frozenset()):
        return _TAG_PATTERN.sub(
            lambda match: self._map_tag(face, match.group(0), keyword_path), value
        )

    def _map_tag(self, face, tag, keyword_path):
        key = tag.lower()

        if key in self._tag_overrides:
            return self._tag_overrides[key]

        expanded = expand_icon_tags(tag, face)
        if expanded != tag:
            return self.map_tags(face, expanded, keyword_path)

        if self._image_mapper is not None:
            image = self._image_mapper(face, tag)
            if image is not None:
                return image

        if any(re.fullmatch(pattern, tag, re.IGNORECASE) for pattern in TAG_REMOVALS):
            return ""

        replacement = _TAG_MAP.get(key, tag)

        if isinstance(replacement, _LocalizedTag):
            return self._expand_keyword(face, replacement.key, keyword_path)

        return replacement

    def _expand_keyword(self, face, key, keyword_path):
        if key in keyword_path:
            raise ValueError(f"Circular keyword translation: {key}")

        catalog = self._get_translations(face.card.effective_language or "en")
        translated_text = catalog.get(key, CARD_KEYWORD_DEFAULTS[key])

        return self.map_tags(face, translated_text, keyword_path | {key})

    def _translate_asset_keys(self, face, value):
        if "%:" not in value:
            return value

        language = face.card.effective_language or "en"
        catalog = self._get_translations("en") | self._get_translations(language)

        keys = sorted((key for key in catalog if key), key=len, reverse=True)
        if not keys:
            return value

        pattern = re.compile(
            r"%:(?:" + "|".join(re.escape(key) for key in keys) + r")(?!\w)"
        )
        return pattern.sub(lambda match: catalog[match.group(0)[2:]], value)

    def _get_translations(self, language):
        if language not in self._translations_by_language:
            self._translations_by_language[language] = load_card_translations(language)

        return self._translations_by_language[language]
