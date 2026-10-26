from pathlib import Path

from shoggoth.arkham_build.constants import UNSUPPORTED_TYPE
from shoggoth.renderer.card_renderer import CARD_SIZES


# Crop coordinates use Shoggoth's 1500 x 2100 canvas, without bleed.
# Each tuple contains x, y, and the square's side length.
_REGIONS = {
    "investigator": (15, 235, 1100),
    "investigator_back": (10, 5, 755),
    "asset": (320, 250, 870),
    "event": (325, 130, 870),
    "skill": (245, 215, 1085),
    "enemy": (390, 1330, 715),
    "location": (425, 275, 660),
    "enemy_location": (385, 405, 765),
    "treachery": (335, 10, 830),
    "scenario": (45, 35, 1415),
    "story": (35, 15, 1440),
    "key": (350, 205, 810),
    "act": (1290, 335, 820),
    "agenda": (0, 335, 820),
    "agenda_back": (15, 60, 320),
    "full": (640, 5, 820),
}


def extract_thumbnail(image, face, card_type):
    """Crop a thumbnail from the rendered face without another render."""
    if card_type == UNSUPPORTED_TYPE:
        size = max(1, round(min(image.size) * 0.8))
        left = (image.width - size) // 2
        top = (image.height - size) // 2
        return image.crop((left, top, left + size, top + size))

    layout = _layout(face, card_type, image.width > image.height)
    x, y, size = _REGIONS[layout]
    canvas = CARD_SIZES["standard"]
    base_width, base_height = canvas["width"], canvas["height"]
    if image.width > image.height:
        base_width, base_height = base_height, base_width

    left = round(x * image.width / base_width)
    top = round(y * image.height / base_height)
    width = round(size * image.width / base_width)
    height = round(size * image.height / base_height)
    overflow = max(left + width - image.width, top + height - image.height, 0)
    width -= overflow
    height -= overflow
    assert width > 0 and height > 0, "Thumbnail region must fit the rendered image"
    return image.crop((left, top, left + width, top + height))


def _layout(face, card_type, horizontal):
    type_code, is_backside = card_type
    template = Path(face.get("type") or "").stem
    if template.removesuffix("_back") == "act_agenda_full":
        return "full"
    if type_code == "enemy" and horizontal:
        return "location"
    if is_backside and type_code in {"act", "agenda"}:
        return "agenda_back"
    if is_backside and type_code == "investigator":
        return "investigator_back"
    return type_code
