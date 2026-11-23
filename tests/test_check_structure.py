"""Gate tests for scripts/check_structure.py: the page-shape rules and the baseline ratchet."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_structure as cs  # noqa: E402

DOCS_REPO = Path(__file__).resolve().parent.parent

HOW_TO = """\
---
description: Deploy an application at its own address.
---

# Deploy an application

Deploy a service so people can reach it.

## Before you begin

You need a project.

## Deploy

1. Open **Applications**.
2. Select **Deploy**.

```bash
kionga apps deploy web
```

## Verify

Open the address.

## Troubleshooting

If the address does not answer, check the status.

## Related pages

- [Functions](functions.md)
"""


def rules(relative: str, text: str) -> set[str]:
    return {finding.rule for finding in cs.check_page(Path(relative), textwrap.dedent(text))}


def test_a_complete_how_to_has_no_findings() -> None:
    assert rules("guides/deploy.md", HOW_TO) == set()
    assert rules("operations/upgrade.md", HOW_TO) == set()


def test_page_types_come_from_the_section() -> None:
    kind = lambda p: cs.page_type(Path(p))  # noqa: E731
    assert kind("getting-started/quickstart.md") == "tutorial"
    assert kind("guides/x.md") == "how-to"
    assert kind("operations/providers/aws-eks.md") == "how-to"
    assert kind("concepts/x.md") == "explanation"
    assert kind("reference/x.md") == "reference"
    assert kind("guides/index.md") == "index"
    assert kind("roadmap.md") == "page"
    assert kind("index.md") == "page"


def test_each_missing_how_to_section_is_reported_by_name() -> None:
    bare = HOW_TO.replace("## Verify\n\nOpen the address.\n\n", "").replace("## Related pages\n\n- [Functions](functions.md)\n", "")
    found = rules("guides/deploy.md", bare)
    assert found == {"section:verify", "section:related-pages"}


def test_section_headings_must_match_the_standard_exactly() -> None:
    renamed = HOW_TO.replace("## Troubleshooting", "## Common problems").replace("## Verify", "## Verify it works")
    assert rules("guides/deploy.md", renamed) == {"section:verify", "section:troubleshooting"}


def test_required_sections_must_come_in_order() -> None:
    swapped = HOW_TO.replace("## Verify", "## Troubleshooting X").replace("## Troubleshooting\n", "## Verify\n").replace("## Troubleshooting X", "## Troubleshooting")
    assert "section-order" in rules("guides/deploy.md", swapped)


def test_a_how_to_and_a_tutorial_need_numbered_steps() -> None:
    no_steps = HOW_TO.replace("1. Open **Applications**.\n2. Select **Deploy**.\n", "Open Applications, then select Deploy.\n")
    assert rules("guides/deploy.md", no_steps) == {"steps"}
    tutorial = no_steps.replace("## Related pages", "## Next steps").replace("## Verify\n\nOpen the address.\n\n## Troubleshooting\n\nIf the address does not answer, check the status.\n\n", "")
    assert rules("getting-started/first.md", tutorial) == {"steps"}


def test_a_tutorial_needs_next_steps_not_related_pages() -> None:
    tutorial = "---\ndescription: Build your first project.\n---\n\n# First project\n\n## Before you begin\n\nInstall.\n\n## Steps\n\n1. Run it.\n"
    assert rules("getting-started/first.md", tutorial) == {"section:next-steps"}


def test_an_explanation_has_no_step_list() -> None:
    page = "---\ndescription: How the parts fit.\n---\n\n# How it fits\n\n1. First this.\n2. Then that.\n"
    assert rules("concepts/fit.md", page) == {"step-list"}
    assert rules("concepts/fit.md", page.replace("1. First this.\n2. Then that.\n", "The parts fit together.\n")) == set()


def test_a_reference_page_needs_a_table() -> None:
    page = "---\ndescription: The settings.\n---\n\n# Settings\n\nOne setting.\n"
    assert rules("reference/settings.md", page) == {"table"}
    assert rules("reference/settings.md", page + "\n| Name | Value |\n| --- | --- |\n| a | b |\n") == set()


def test_front_matter_and_headings_apply_to_every_page() -> None:
    assert rules("roadmap.md", "# Roadmap\n") == {"description"}
    assert rules("roadmap.md", "---\ndescription: Two. Sentences.\n---\n\n# Roadmap\n") == {"description"}
    assert rules("roadmap.md", "---\ndescription: No full stop\n---\n\n# Roadmap\n") == {"description"}
    assert rules("roadmap.md", "---\ndescription: What is planned.\n---\n\n# A\n\n# B\n") == {"h1"}
    assert rules("roadmap.md", "---\ndescription: What is planned.\n---\n\n# A\n\n### Deep\n") == {"heading-level"}


def test_landing_pages_skip_the_shape_rules_but_keep_the_universal_ones() -> None:
    page = "---\ndescription: The guides.\n---\n\n# Guides\n\nPick one.\n"
    assert rules("guides/index.md", page) == set()
    assert rules("guides/index.md", "# Guides\n") == {"description"}


def test_code_fences_need_a_language_and_headings_in_code_do_not_count() -> None:
    page = "---\ndescription: What is planned.\n---\n\n# Roadmap\n\n```\nplain\n```\n\n```bash\n# not a heading\n```\n"
    assert rules("roadmap.md", page) == {"fence-language"}
    labelled = page.replace("```\nplain", "```text\nplain")
    assert rules("roadmap.md", labelled) == set()


def test_em_dashes_are_rejected_and_en_dash_ranges_are_allowed() -> None:
    page = "---\ndescription: What is planned.\n---\n\n# Roadmap\n\nBetween 2–100 nodes.\n"
    assert rules("roadmap.md", page) == set()
    assert rules("roadmap.md", page.replace("–", "—")) == {"dash"}


def test_the_generated_changelog_is_not_checked(tmp_path: Path) -> None:
    (tmp_path / "changelog.md").write_text("no front matter\n")
    assert cs.collect(tmp_path) == []


def test_the_baseline_ratchet_fails_on_new_gaps_and_on_fixed_ones() -> None:
    found = [cs.Finding("guides/a.md", "section:verify", "x"), cs.Finding("guides/b.md", "steps", "y")]
    assert cs.evaluate(found, {"guides/a.md section:verify", "guides/b.md steps"}) == ([], [])
    new, stale = cs.evaluate(found, {"guides/a.md section:verify"})
    assert [f.key() for f in new] == ["guides/b.md steps"] and stale == []
    new, stale = cs.evaluate(found, {"guides/a.md section:verify", "guides/b.md steps", "guides/c.md steps"})
    assert new == [] and stale == ["guides/c.md steps"]


def test_baseline_files_allow_comments_and_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "baseline.txt"
    path.write_text("# header\n\nguides/a.md   section:verify  # why\n")
    assert cs.read_baseline(path) == {"guides/a.md section:verify"}
    assert cs.read_baseline(tmp_path / "missing.txt") == set()


def test_the_real_documentation_passes_against_its_baseline() -> None:
    findings = cs.collect(DOCS_REPO / "docs")
    baseline = cs.read_baseline(DOCS_REPO / "scripts" / "structure-baseline.txt")
    new, stale = cs.evaluate(findings, baseline)
    assert [f.key() for f in new] == [] and stale == []


def test_every_baseline_line_names_a_real_page_and_a_known_rule() -> None:
    known = {"description", "h1", "heading-level", "fence-language", "dash", "section-order", "steps", "step-list", "table"}
    known |= {f"section:{cs.slug(name)}" for names in cs.REQUIRED_SECTIONS.values() for name in names}
    for entry in cs.read_baseline(DOCS_REPO / "scripts" / "structure-baseline.txt"):
        page, rule = entry.split(" ", 1)
        assert (DOCS_REPO / "docs" / page).is_file(), entry
        assert rule in known, entry
