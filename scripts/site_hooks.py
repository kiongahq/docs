"""Publish the repository's release metadata inside the static documentation."""

import re
import json
import html
from urllib.parse import quote
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = "<!-- release-notes -->"
COMPONENT_MARKER = "<!-- component-releases -->"


# Sections a reader of the public changelog cares about, in display order.
# Maintenance, automation, dependency bumps and refactors stay on GitHub.
SIGNIFICANT = {
    "breaking changes": "Breaking changes", "features": "New features", "new features": "New features",
    "fixes": "Fixes", "bug fixes": "Fixes", "performance": "Performance", "reverts": "Reverts",
}
SECTION_ORDER = ["Breaking changes", "New features", "Fixes", "Performance", "Reverts"]
OUR_LINK = re.compile(r"https://github\.com/kiongahq/[A-Za-z0-9._/#?=&%-]+")
INLINE = re.compile(r"\*\*(?P<bold>[^*\n]+)\*\*|`(?P<code>[^`\n]+)`|\[(?P<label>[^\]\n]+)\]\((?P<url>[^)\s]+)\)")
COMMIT = re.compile(r",?\s*\(\[[0-9a-f]{7,40}\]\(https://github\.com/kiongahq/[^)]+/commit/[0-9a-f]+\)\)")


def inline(text):
    """Escape everything, then allow bold, code and links to kiongahq on GitHub."""
    out, last = [], 0
    for match in INLINE.finditer(text):
        out.append(html.escape(text[last:match.start()]))
        if match["bold"]:
            out.append(f"<strong>{html.escape(match['bold'])}</strong>")
        elif match["code"]:
            out.append(f"<code>{html.escape(match['code'])}</code>")
        elif OUR_LINK.fullmatch(match["url"]):
            out.append(f'<a href="{html.escape(match["url"])}">{html.escape(match["label"])}</a>')
        else:
            out.append(html.escape(match["label"]))
        last = match.end()
    out.append(html.escape(text[last:]))
    return "".join(out)


def significant_changes(body, repository):
    """Group release-please notes into the sections that matter, as HTML lists.

    Returns None when the notes aren't in release-please form, so the caller can
    fall back to plain paragraphs.
    """
    sections, current, structured = {}, None, False
    wanted = dict(SIGNIFICANT, **({"documentation": "Documentation"} if repository == "docs" else {}))
    for line in body.splitlines():
        heading = re.match(r"^#{3,4}\s+(?:\W+\s*)?(.+?)\s*$", line)
        if heading:
            structured = True
            current = wanted.get(heading.group(1).strip().lower())
            continue
        item = re.match(r"^\s*[*-]\s+(.+)$", line)
        if item and current:
            sections.setdefault(current, []).append(COMMIT.sub("", item.group(1)).strip())
    if not structured:
        return None
    order = SECTION_ORDER + ["Documentation"]
    return "".join(
        f'<h4>{name}</h4>\n<ul>\n' + "".join(f"<li>{inline(text)}</li>\n" for text in sections[name]) + "</ul>\n"
        for name in order if name in sections
    )


def plain_notes(body):
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    paragraphs = [p for p in paragraphs if not re.match(r"^#{1,2}\s", p)]
    return "".join(f"<p>{inline(p)}</p>\n" for p in paragraphs) or "<p>See the release page for details.</p>\n"


def component_releases(data):
    """One timeline of every component's releases, newest first, with formatted notes.

    Release text is escaped before the few allowed constructs are turned into
    HTML, so a release body can't inject markup or links outside kiongahq.
    """
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported release snapshot schema")
    timeline = []
    for repository, releases in data["repositories"].items():
        if not re.fullmatch(r"[a-z0-9.-]+", repository):
            raise ValueError("Invalid repository name")
        timeline.extend((release["published_at"], repository, release) for release in releases)
    sections = [f"Last refreshed: {html.escape(data['updated_at'][:10])}.\n"]
    if not timeline:
        sections.append("No published release yet. Development commits and tags are not release announcements.\n")
    for published, repository, release in sorted(timeline, key=lambda item: item[0], reverse=True):
        url = f"https://github.com/kiongahq/{repository}/releases"
        link = url + "/tag/" + quote(release["tag"], safe="")
        status = "Preview" if release["prerelease"] else "Release"
        notes = significant_changes(release["body"], repository)
        if notes is None:
            notes = plain_notes(release["body"])
        elif not notes:
            notes = "<p>Maintenance only: no user-facing changes.</p>\n"
        assets = ", ".join(html.escape(name) for name in release["assets"])
        # A Markdown heading, so the release is in the page's table of contents.
        # Only the repository (validated above) and a tag reduced to safe characters reach it.
        safe_tag = re.sub(r"[^A-Za-z0-9.+-]", "-", release["tag"])
        sections.append(
            f"## {repository} {safe_tag} {{#{repository}-{safe_tag} .kg-release-title}}\n\n"
            f'<div class="kg-release" markdown="0">\n'
            f'<p class="kg-release-meta">{status} · {html.escape(published[:10])} · '
            f'<a href="{link}">Release page</a>' + (f" · Files: {assets}" if assets else "") + "</p>\n"
            f'<div class="kg-release-notes">\n{notes}</div>\n</div>\n'
        )
    links = " · ".join(f"[{name}](https://github.com/kiongahq/{name}/releases)" for name in data["repositories"])
    sections.append(f"## All releases by component\n\n{links}\n")
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
