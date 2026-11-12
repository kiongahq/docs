import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_public_site import check


def site(root, entries=()):
    (root / "search").mkdir()
    (root / "search/search_index.json").write_text(json.dumps({"docs": list(entries)}))


def test_product_and_access_notice_can_be_published(tmp_path):
    site(tmp_path, [{"location": "engineering-access/"}, {"location": "changelog/"}])
    (tmp_path / "engineering").mkdir()
    (tmp_path / "engineering/index.html").write_text('redirect to /engineering-access/')
    check(tmp_path)


def test_engineering_pages_cannot_be_published(tmp_path):
    site(tmp_path)
    (tmp_path / "engineering/architecture").mkdir(parents=True)
    (tmp_path / "engineering/architecture/index.html").write_text("Internal content")
    with pytest.raises(ValueError, match="Engineering files"):
        check(tmp_path)


def test_engineering_search_entries_cannot_be_published(tmp_path):
    site(tmp_path, [{"location": "engineering/architecture/", "text": "Internal content"}])
    with pytest.raises(ValueError, match="public search"):
        check(tmp_path)
