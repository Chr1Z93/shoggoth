from enum import StrEnum


class BuildMetaProjectStatus(StrEnum):
    DRAFT = "draft"
    ALPHA = "alpha"
    BETA = "beta"
    COMPLETE = "complete"
    FINAL = "final"


class BuildMetaContentType(StrEnum):
    CAMPAIGN = "campaign"
    INVESTIGATORS = "investigators"
    PLAYER_CARDS = "player_cards"
    REWORK = "rework"
    SCENARIO = "scenario"


NUMERICAL_MAP = {
    "<dash>": None,
    "---": None,
    "X": -2,
    "<star>": -3,
    "?": -4,
}


PER_INVESTIGATOR_MAP = {
    "clues": ("clues_fixed", False),
    "doom": ("doom_per_investigator", True),
    "enemy_evade": ("enemy_evade_per_investigator", True),
    "enemy_fight": ("enemy_fight_per_investigator", True),
    "health": ("health_per_investigator", True),
    "shroud": ("shroud_per_investigator", True),
}


SKILL_MAP = {
    "W": "skill_willpower",
    "I": "skill_intellect",
    "C": "skill_combat",
    "A": "skill_agility",
    "Q": "skill_wild",
}


MINI_TYPE = "mini_"


UNSUPPORTED_TYPE = (None, False)
CARD_BACK_TYPE = (None, True)
INDETERMINATE_TYPE = "indeterminate"
