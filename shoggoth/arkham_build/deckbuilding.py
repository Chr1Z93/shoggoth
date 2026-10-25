from html import unescape
import re

from shoggoth.arkham_build.text import map_text


def add_deckbuilding_fields(cards, exported_cards):
    """Add requirements and restrictions from investigator links and back entries."""
    by_code = {card["code"]: card for card in exported_cards}

    investigators = {}
    signatures = {}

    for card in cards:
        exported = by_code.get(card.id)
        if exported is None or exported["type_code"] != "investigator":
            continue

        link = _investigator_link(card) or card.name
        investigators.setdefault(link, []).append(card)

        signatures[card.id] = []

    for card in cards:
        exported = by_code.get(card.id)
        if exported is None or exported["type_code"] == "investigator":
            continue

        owners = investigators.get(_investigator_link(card), [])
        if not owners:
            continue

        restriction = "investigator:" + ":".join(owner.id for owner in owners)
        exported["restrictions"] = restriction

        back = by_code.get(exported.get("back_link"))
        if back is not None:
            back["restrictions"] = restriction

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
            by_code[investigator.id]["deck_requirements"] = ", ".join(requirements)


def _investigator_link(card):
    return card.get_meta("investigator", card.get("investigator"))


def _plain_text(face, value):
    mapped = map_text(face, "entries", str(value or ""))
    return " ".join(unescape(re.sub(r"<[^>]*>", "", mapped)).split())


def _deck_size_requirements(face):
    size = []
    for header, value in face.get("entries", []) or []:
        header = _plain_text(face, header).casefold()

        if header.rstrip(": ") == "deck size":
            match = re.fullmatch(r"(\d+)\.?", _plain_text(face, value))
            if match:
                size = [f"size:{int(match[1])}"]
    return size
