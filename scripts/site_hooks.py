"""Publish the repository's release metadata inside the static documentation."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = "<!-- release-notes -->"


def on_config(config):
    version = (ROOT / "version.txt").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version):
        raise ValueError("version.txt must contain a semantic version")
    config.extra["docs_version"] = "Development" if version == "0.0.0" else f"v{version}"
    return config


def release_notes(changelog):
    """Keep generated headings and commit links; add timeline containers."""
    entries = [
        entry
        for entry in re.split(r"(?=^## )", changelog, flags=re.MULTILINE)[1:]
        if re.match(r"## \[?v?[0-9]+\.[0-9]+\.[0-9]+(?:\]|\s|$|[-+])", entry)
    ]
    if not entries:
        return (
            '<div class="kg-release-empty" markdown>\n\n'
            "**The first documentation release is on its way.**\n\n"
            "Release notes appear here when a documentation release is published. "
            "Until then, see the "
            "[latest changes](https://github.com/kiongahq/docs/commits/main/).\n\n"
            "</div>"
        )
    return "\n\n".join(
        f'<section class="kg-release" markdown>\n\n{entry.strip()}\n\n</section>'
        for entry in entries
    )


def on_page_markdown(markdown, page, config, files):
    if MARKER not in markdown:
        return markdown
    return markdown.replace(MARKER, release_notes((ROOT / "CHANGELOG.md").read_text()))
