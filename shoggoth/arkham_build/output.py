from urllib.parse import quote

from shoggoth.files import default_export_folder


def export_folder(project):
    """The folder an arkham.build export of the project is written to."""
    return default_export_folder(project) / "arkham-build"


def export_file(project, path):
    """The location of an exported project file, with its folder created."""
    destination = export_folder(project) / project.id / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def export_url(url_prefix, project, path):
    return f"{url_prefix}/{project.id}/{quote(path)}"
