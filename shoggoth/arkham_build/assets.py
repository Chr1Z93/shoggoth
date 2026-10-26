import hashlib
from html import escape
import re
import shutil
from urllib.parse import quote

from shoggoth.files import default_export_folder, overlay_dir
from shoggoth.renderer.richtext.tags import parse_tag_attributes


_IMAGE_TAG_PATTERN = re.compile(r"<image(?=\s|>)", re.IGNORECASE)


class ImageAssetExporter:
    """Copy original image files once per export and map inline image tags."""

    def __init__(self, project, url_prefix):
        self.project = project
        self.url_prefix = url_prefix
        self._urls_by_path = {}

    def export(self, source):
        if not self.url_prefix or not source:
            return None

        path = self.project.find_file(source)
        if path is None:
            path = overlay_dir / source

        if not path.is_file():
            return None

        path = path.resolve()

        if path not in self._urls_by_path:
            with path.open("rb") as image:
                digest = hashlib.file_digest(image, "sha256").hexdigest()

            filename = f"{digest}{path.suffix}"
            folder = (
                default_export_folder(self.project)
                / "arkham-build"
                / self.project.id
                / "assets"
            )
            folder.mkdir(parents=True, exist_ok=True)

            destination = folder / filename
            if not destination.exists():
                shutil.copyfile(path, destination)

            self._urls_by_path[path] = (
                f"{self.url_prefix}/{self.project.id}/assets/{quote(filename)}"
            )

        return self._urls_by_path[path]

    def map_tag(self, face, tag):
        """Return image HTML, an empty string, or None for a non-image tag."""
        if _IMAGE_TAG_PATTERN.match(tag) is None:
            return None

        attributes = {
            key.lower(): value for key, value in parse_tag_attributes(tag).items()
        }
        source = attributes.get("src")

        url = self.export(source)
        if url is None:
            return ""

        return (
            f'<img src="{escape(url, quote=True)}" '
            'style="height:1em;vertical-align:middle">'
        )
