import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import site_hooks
import sync_releases


def release(**overrides):
    return {"tag_name": "v1.2.3", "name": "Version 1.2.3", "draft": False,
            "published_at": "2026-11-01T12:00:00Z", "prerelease": False,
            "body": "Fixed a problem", "assets": [{"name": "package.tar.gz"}], **overrides}


def test_catalog_excludes_unpublished_and_draft_releases():
    data = sync_releases.snapshot(lambda repo: [release(), release(draft=True), release(published_at=None)])
    assert set(data["repositories"]) == set(sync_releases.REPOSITORIES)
    assert all(len(items) == 1 for items in data["repositories"].values())
    assert data["repositories"]["sdk-python"][0]["assets"] == ["package.tar.gz"]


def test_release_notes_cannot_inject_html_or_links():
    malicious = release(name='<img src=x onerror="alert(1)">',
                        body='</pre><script>alert(1)</script> [click](javascript:alert(1))',
                        tag_name='v1.2.3" onclick="alert(1)', assets=[{"name": "<script>"}])
    html = site_hooks.component_releases(sync_releases.snapshot(lambda repo: [malicious]))
    assert "<script>" not in html and "<img" not in html
    assert "&lt;script&gt;" in html
    assert 'href="javascript:' not in html
    assert '%22%20onclick%3D%22' in html


def test_unknown_repository_is_rejected_before_network_access():
    with pytest.raises(ValueError, match="catalog"):
        sync_releases.fetch_releases("../private-repo")


def test_no_releases_does_not_invent_published_versions():
    html = site_hooks.component_releases(sync_releases.snapshot(lambda repo: []))
    assert "No published release yet" in html
    assert "v0.1.0" not in html


def test_refresh_failure_preserves_previous_snapshot(tmp_path, monkeypatch):
    target = tmp_path / "releases.json"
    target.write_text('{"previous": true}')
    monkeypatch.setattr(sys, "argv", ["sync_releases", "--output", str(target)])
    def unavailable():
        raise OSError("API unavailable")
    monkeypatch.setattr(sync_releases, "snapshot", unavailable)
    with pytest.raises(OSError):
        sync_releases.main()
    assert json.loads(target.read_text()) == {"previous": True}


def test_preview_label_and_component_marker(monkeypatch, tmp_path):
    data = sync_releases.snapshot(lambda repo: [release(prerelease=True)])
    (tmp_path / "releases.json").write_text(json.dumps(data))
    monkeypatch.setattr(site_hooks, "ROOT", tmp_path)
    rendered = site_hooks.on_page_markdown("# Changes\n<!-- component-releases -->", None, None, None)
    assert "Preview" in rendered and "<!-- component-releases -->" not in rendered
