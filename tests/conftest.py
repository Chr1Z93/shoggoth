import json
import os
from contextlib import contextmanager
from pathlib import Path

import pytest
from PIL import Image

from shoggoth import arkham_build
from shoggoth.project import Project

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS") == "1"


class _StubRenderer:
    """Render every face as a blank card, so exports with images stay fast."""

    locale = "en"

    @contextmanager
    def render_card_side(self, card, side, include_bleed=True):
        horizontal = side.get("orientation", "vertical") == "horizontal"
        yield Image.new("RGB", (2100, 1500) if horizontal else (1500, 2100))


def _normalize(data):
    """Replace values that change between runs."""
    data["meta"]["date_updated"] = "<date_updated>"
    data["meta"]["generator"] = "<generator>"
    return data


@pytest.fixture
def export(tmp_path):
    """Export a project dict to arkham.build JSON."""

    def run(project_data, settings=None):
        project = Project(str(tmp_path / "project.json"), project_data)
        data = arkham_build.export_project(
            project,
            settings or {},
            _StubRenderer(),
            card_executor=lambda cards, export_card: [
                export_card(card) for card in cards
            ],
        )
        return _normalize(data)

    return run


@pytest.fixture
def snapshot(request):
    """Compare data to the test's JSON snapshot; UPDATE_SNAPSHOTS=1 rewrites it."""
    path = SNAPSHOT_DIR / f"{request.node.name}.json"

    def check(data):
        actual = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if UPDATE_SNAPSHOTS:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(actual, encoding="utf-8")
            return

        assert path.exists(), (
            f"Missing snapshot {path.name}, run with UPDATE_SNAPSHOTS=1"
        )
        assert actual == path.read_text(encoding="utf-8")

    return check
