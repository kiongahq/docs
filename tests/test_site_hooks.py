"""Release notes stay readable, linkable and consistent with release metadata."""

import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import site_hooks  # noqa: E402


def test_version_files_match_release_manifest():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / ".release-please-manifest.json").read_text())
    assert manifest["."] == (root / "version.txt").read_text().strip()


@pytest.mark.parametrize("version,label", [("0.0.0", "Development"), ("1.2.3", "v1.2.3")])
def test_version_badge(monkeypatch, tmp_path, version, label):
    monkeypatch.setattr(site_hooks, "ROOT", tmp_path)
    (tmp_path / "version.txt").write_text(version + "\n")
    config = SimpleNamespace(extra={})
    site_hooks.on_config(config)
    assert config.extra["docs_version"] == label


def test_invalid_version_fails_build(monkeypatch, tmp_path):
    monkeypatch.setattr(site_hooks, "ROOT", tmp_path)
    (tmp_path / "version.txt").write_text("not-a-version")
    with pytest.raises(ValueError, match="semantic version"):
        site_hooks.on_config(SimpleNamespace(extra={}))


def test_no_releases_does_not_invent_a_version_or_date():
    result = site_hooks.release_notes("# Changelog\n\nDocumentation releases.\n")
    assert "kg-release-empty" in result
    assert "first documentation release" in result
    assert "0.1.0" not in result


def test_release_timeline_keeps_order_sections_dates_and_links():
    result = site_hooks.release_notes(
        "# Changelog\n\nIntroduction.\n\n"
        "## [1.1.0](https://github.com/kiongahq/docs/compare/v1.0.0...v1.1.0) (2026-10-23)\n\n"
        "### New features\n\n* Added a guide ([abc123](https://github.com/kiongahq/docs/commit/abc123)).\n\n"
        "## 1.0.0 (2026-10-20)\n\n### Fixes\n\n* Corrected a link.\n"
    )
    assert result.count('<section class="kg-release" markdown>') == 2
    assert result.index("1.1.0") < result.index("## 1.0.0")
    assert "### New features" in result and "### Fixes" in result
    assert "(2026-10-23)" in result
    assert "https://github.com/kiongahq/docs/commit/abc123" in result
    assert "Introduction" not in result


def test_changelog_injection_preserves_page_intro(monkeypatch, tmp_path):
    monkeypatch.setattr(site_hooks, "ROOT", tmp_path)
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## 1.0.0\n\n### Fixes\n\n* Fixed.\n")
    page = "# Changelog\n\nIntro.\n\n<!-- release-notes -->\n"
    result = site_hooks.on_page_markdown(page, None, None, None)
    assert result.startswith("# Changelog\n\nIntro.")
    assert "<!-- release-notes -->" not in result
    assert "## 1.0.0" in result
    assert site_hooks.on_page_markdown("# Other page", None, None, None) == "# Other page"


def test_both_sites_use_the_shared_template_directory():
    root = Path(__file__).resolve().parents[1]
    for name in ("mkdocs.yml", "engineering/mkdocs.yml"):
        config = root / name
        custom_dir = re.search(r"^  custom_dir: (.+)$", config.read_text(), re.MULTILINE)
        assert custom_dir
        assert (config.parent / custom_dir.group(1)).resolve() == root / "overrides"


def test_explanatory_headings_are_not_release_entries():
    result = site_hooks.release_notes(
        "# Changelog\n\n## 1.0.0 (2026-10-23)\n\n### New features\n\n* A guide.\n\n"
        "## Changelog\n\nExplanatory text.\n"
    )
    assert result.count('<section class="kg-release" markdown>') == 1
    assert "Explanatory text" not in result
