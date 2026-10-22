"""Every page URL published before the product/engineering split still resolves.

tests/legacy-pages.txt lists the pages of the site at feb583e (the last commit
before the split). Each must still exist in the product site or be a redirect
in mkdocs.yml whose target exists, in the product site or the engineering
handbook. Add new moves to mkdocs.yml redirects, never delete from the list."""

from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
ENGINEERING_URL = "https://kiongahq.github.io/docs/engineering/"


class Loader(yaml.SafeLoader):
    pass


# mkdocs.yml uses !!python/name tags for extensions; they are irrelevant here.
Loader.add_multi_constructor("tag:yaml.org,2002:python/", lambda loader, suffix, node: None)


def redirects():
    config = yaml.load((REPO / "mkdocs.yml").read_text(), Loader=Loader)
    for plugin in config["plugins"]:
        if isinstance(plugin, dict) and "redirects" in plugin:
            return plugin["redirects"]["redirect_maps"]
    return {}


def engineering_page(url: str) -> Path:
    path = url[len(ENGINEERING_URL):].split("#")[0].strip("/")
    candidates = [REPO / "engineering/docs" / f"{path}.md", REPO / "engineering/docs" / path / "index.md"]
    return next((c for c in candidates if c.is_file()), candidates[0])


LEGACY = (REPO / "tests/legacy-pages.txt").read_text().split()


@pytest.mark.parametrize("page", LEGACY)
def test_legacy_url_resolves(page):
    if (REPO / "docs" / page).is_file():
        return
    target = redirects().get(page)
    assert target, f"{page} was removed without a redirect in mkdocs.yml"
    if target.startswith(ENGINEERING_URL):
        assert engineering_page(target).is_file(), f"{page} redirects to a missing handbook page {target}"
    else:
        assert not target.startswith("http"), f"{page} redirects off-site to {target}"
        assert (REPO / "docs" / target.split("#")[0]).is_file(), f"{page} redirects to missing {target}"


def test_redirect_sources_are_not_live_pages():
    live = [source for source in redirects() if (REPO / "docs" / source).is_file()]
    assert not live, f"redirects shadow existing pages: {live}"


def test_both_sites_share_one_brand():
    for asset in ("assets/logo.svg", "assets/favicon.svg", "stylesheets/kionga.css"):
        assert (REPO / "docs" / asset).read_bytes() == (REPO / "engineering/docs" / asset).read_bytes(), \
            f"{asset} differs between the product site and the engineering handbook"
