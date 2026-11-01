"""Publish the repository's release metadata inside the static documentation."""

import re
import json
import html
from urllib.parse import quote
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = "<!-- release-notes -->"
COMPONENT_MARKER = "<!-- component-releases -->"


def component_releases(data):
    """Render release text as escaped content, never executable Markdown or HTML."""
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported release snapshot schema")
    sections = [f"Last refreshed: {html.escape(data['updated_at'][:10])}.\n"]
    for repository, releases in data["repositories"].items():
        if not re.fullmatch(r"[a-z0-9.-]+", repository):
            raise ValueError("Invalid repository name")
        url = f"https://github.com/kiongahq/{repository}/releases"
        sections.append(f"## {repository}\n\n[All releases]({url})\n")
        if not releases:
            sections.append("No published release yet. Development commits and tags are not release announcements.\n")
        for release in releases:
            title = html.escape(release["name"])
            link = url + "/tag/" + quote(release["tag"], safe="")
            date = html.escape(release["published_at"][:10])
            status = "Preview" if release["prerelease"] else "Release"
            notes = html.escape(release["body"] or "See the release page for details.")
            assets = ", ".join(html.escape(name) for name in release["assets"])
            sections.append(
                f'<section class="kg-release">\n<h3><a href="{link}">{title}</a></h3>\n'
                f'<p>{status} · {date}</p>\n<pre class="kg-release-notes">{notes}</pre>\n'
                f'<p>Attached files: {assets or "None; check the publishing workflow before installing."}</p>\n'
                '</section>\n'
            )
    return "\n".join(sections)


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
    if COMPONENT_MARKER in markdown:
        markdown = markdown.replace(COMPONENT_MARKER, component_releases(
            json.loads((ROOT / "releases.json").read_text())))
    if MARKER not in markdown:
        return markdown
    return markdown.replace(MARKER, release_notes((ROOT / "CHANGELOG.md").read_text()))


def on_post_build(config):
    """Expose non-secret configuration to the React documentation interface."""
    root = Path(config.site_dir) / "javascripts"
    root.mkdir(parents=True, exist_ok=True)
    settings = {
        "site_name": config.site_name,
        "version": config.extra.get("docs_version", ""),
        "assistant_enabled": config.extra.get("assistant_enabled", False),
        "assistant_endpoint": config.extra.get("assistant_endpoint", ""),
        "product_url": "https://kiongahq.github.io/docs/",
    }
    (root / "ui-config.json").write_text(json.dumps(settings))
