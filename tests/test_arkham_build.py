def _project(**overrides):
    return {
        "id": "TST",
        "name": "Snapshot Test",
        "icon": "",
        "encounter_sets": [
            {"id": "enc-cult", "name": "Cult of Testing", "icon": "", "cards": []},
            {"id": "enc-rats", "name": "Swarm of Rats", "icon": "", "cards": []},
        ],
        "cards": [],
        **overrides,
    }


def test_project_meta_and_groups(export, snapshot):
    project = _project(
        meta={
            "author": "Test Author",
            "description": "A project used by the snapshot tests.",
            "website_url": "https://example.com/snapshot-test",
            # Not a known status, exported as "draft".
            "status": "playtesting",
            "tags": ["campaign", "fan-made"],
        },
    )

    snapshot(export(project))


def test_player_asset(export, snapshot):
    card = {
        "id": "asset-01",
        "name": "Codex of Testing",
        "amount": 2,
        "project_number": "12",
        "front": {
            "type": "asset",
            "name": "<unique><name>",
            "subtitle": "Proof of Concept",
            "classes": ["seeker", "mystic"],
            "level": "2",
            "cost": "3",
            "icons": "WWI",
            "traits": "Item. Tome.",
            "slots": ["hand", "arcane"],
            "text": "<action>: Investigate.",
            "flavor_text": "Every page is a test.",
            "illustrator": "Test Illustrator",
        },
        "back": {"type": "player"},
    }

    snapshot(export(_project(cards=[card]))["data"]["cards"])


def test_enemy_special_values(export, snapshot):
    card = {
        "id": "enemy-01",
        "name": "Test Acolyte",
        "amount": 2,
        "project_number": "20",
        "encounter_set": "enc-cult",
        "encounter_number": "4",
        "front": {
            "type": "enemy",
            "traits": "Humanoid. Cultist.",
            "attack": "X",
            "evade": "<dash>",
            "health": "3<per>",
            "damage": "1",
            "horror": "0",
            "victory": "Victory 1.",
            "text": "X is the number of cultists in play.",
        },
        "back": {"type": "encounter"},
    }

    snapshot(export(_project(cards=[card]))["data"]["cards"])


def test_text_conversion(export, snapshot):
    card = {
        "id": "event-01",
        "name": "Stand Firm",
        "amount": 2,
        "project_number": "30",
        "front": {
            "type": "event",
            "classes": ["guardian"],
            "cost": "1",
            "level": "0",
            "icons": "W",
            "traits": "Spirit.",
            "text": (
                "Exceptional.\n"
                "<free> When a <t>Cultist</t> enemy attacks you, play <name>: "
                "Cancel that attack---it gets -1 <willpower>.\n"
                "<for> After this card is played: "
                "<center><dquote>Not today.<dquoteend></center>"
            ),
        },
        "back": {"type": "player"},
    }

    snapshot(export(_project(cards=[card]))["data"]["cards"])
