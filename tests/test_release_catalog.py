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


NOTES = """## [0.3.1](https://github.com/kiongahq/sdk-python/compare/v0.3.0...v0.3.1) (2026-11-11)


### ⚠ BREAKING CHANGES

* rename `mlaiops` to kionga

### Features

* **teams:** typed errors and `RetryPolicy` ([#53](https://github.com/kiongahq/sdk-python/issues/53)) ([5c690b2](https://github.com/kiongahq/sdk-python/commit/5c690b2b58cae5de8a0a108caa80b193b96a41c2))

### Fixes

* keep the [evil](https://evil.example/x) link text only

### Maintenance

* bump the lockfile
"""


def render(*releases_by_repo):
    data = {"schema_version": 1, "updated_at": "2026-11-11T00:00:00+00:00",
            "repositories": {repo: [dict({"tag": "v1.0.0", "name": "n", "published_at": "2026-11-01T00:00:00+00:00",
                                         "prerelease": False, "body": "", "assets": []}, **r) for r in rs]
                             for repo, rs in releases_by_repo}}
    return site_hooks.component_releases(data)


def test_release_please_notes_become_formatted_sections_in_reading_order():
    html = render(("sdk-python", [{"tag": "v0.3.1", "body": NOTES}]))
    assert html.index("<h4>Breaking changes</h4>") < html.index("<h4>New features</h4>") < html.index("<h4>Fixes</h4>")
    assert "<li><strong>teams:</strong> typed errors and <code>RetryPolicy</code> " \
           '(<a href="https://github.com/kiongahq/sdk-python/issues/53">#53</a>)</li>' in html
    assert "<code>mlaiops</code>" in html and "<pre" not in html and "## [0.3.1]" not in html


def test_maintenance_and_commit_hashes_are_left_to_github():
    html = render(("sdk-python", [{"tag": "v0.3.1", "body": NOTES}]))
    assert "lockfile" not in html and "Maintenance" not in html and "5c690b2" not in html


def test_links_outside_kiongahq_keep_only_their_text():
    html = render(("sdk-python", [{"tag": "v0.3.1", "body": NOTES}]))
    assert "evil.example" not in html and "keep the evil link text only" in html


def test_a_release_with_only_maintenance_says_so():
    html = render(("deploy", [{"body": "## 1.0.1\n\n### Maintenance\n\n* bump\n"}]))
    assert "Maintenance only: no user-facing changes." in html


def test_documentation_counts_only_for_the_docs_component():
    body = "## 1.0.0\n\n### Documentation\n\n* new guide\n"
    assert "new guide" in render(("docs", [{"body": body}]))
    assert "new guide" not in render(("platform", [{"body": body}]))


def test_releases_from_every_component_form_one_timeline_newest_first():
    html = render(("platform", [{"tag": "v0.1.0", "published_at": "2026-11-02T00:00:00+00:00"}]),
                  ("sdk-python", [{"tag": "v0.3.1", "published_at": "2026-11-11T00:00:00+00:00"},
                                  {"tag": "v0.3.0", "published_at": "2026-11-10T00:00:00+00:00"}]))
    order = [html.index(f"## {name}") for name in ("sdk-python v0.3.1", "sdk-python v0.3.0", "platform v0.1.0")]
    assert order == sorted(order)


def test_a_hostile_tag_cannot_break_out_of_the_heading():
    html = render(("sdk-python", [{"tag": "v1 {#x onclick=alert(1)} <b>"}]))
    heading = next(line for line in html.splitlines() if line.startswith("## "))
    assert "{" not in heading.split("{#", 1)[0] and "<" not in heading and "onclick=" not in heading.split("{#")[0]
