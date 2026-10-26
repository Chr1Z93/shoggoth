from html import unescape
import re

from shoggoth.arkham_build.text import map_text


def add_deckbuilding_fields(cards, records_by_id):
    """Add requirements and restrictions from investigator links and back entries."""
    investigators = {}
    signatures = {}

    for card in cards:
        records = records_by_id[card.id]
        if not records or records[0]["type_code"] != "investigator":
            continue

        link = card.get("investigator") or card.name
        investigators.setdefault(link, []).append(card)

        signatures[card.id] = []

    for card in cards:
        records = records_by_id[card.id]
        if not records or records[0]["type_code"] == "investigator":
            continue

        owners = investigators.get(card.get("investigator"), [])
        if not owners:
            continue

        restriction = "investigator:" + ":".join(owner.id for owner in owners)
        for record in records:
            record["restrictions"] = restriction

        if not card.get_meta("bonded"):
            for owner in owners:
                signatures[owner.id].append(f"card:{card.id}")

    for group in investigators.values():
        for investigator in group:
            requirements = (
                _deck_size_requirements(investigator.back)
                + signatures[investigator.id]
                + ["random:subtype:basicweakness"]
            )
            records_by_id[investigator.id][0]["deck_requirements"] = ", ".join(
                requirements
            )


def _plain_text(face, value):
    mapped = map_text(face, "entries", str(value or ""))
    return " ".join(unescape(re.sub(r"<[^>]*>", "", mapped)).split())


def _deck_size_requirements(face):
    """The size requirement from the last valid "Deck Size" entry, if any."""
    # TODO: Match localized "Deck Size" labels.
    requirements = []
    for header, value in face.get("entries", []):
        if _plain_text(face, header).casefold().rstrip(": ") != "deck size":
            continue

        match = re.fullmatch(r"(\d+)\.?", _plain_text(face, value))
        if match:
            requirements = [f"size:{int(match[1])}"]
    return requirements
