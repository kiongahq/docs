"""Gate tests for scripts/check_structure.py: the page-shape rules and the Markdown they must understand."""

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










def test_a_page_titled_troubleshooting_does_not_need_a_troubleshooting_section() -> None:
    page = HOW_TO.replace("# Deploy an application", "# Troubleshooting").replace("## Troubleshooting\n\nIf the address does not answer, check the status.\n\n", "")
    assert "## Troubleshooting" not in page
    assert rules("operations/troubleshooting.md", page) == set()
    # Any other page still needs the section.
    other = page.replace("# Troubleshooting", "# Deploy an application")
    assert rules("operations/upgrade.md", other) == {"section:troubleshooting"}


FENCE = "`" * 3
TILDES = "~" * 3
EM = chr(0x2014)
EN = chr(0x2013)


def page(body: str, front: str = "description: What is planned.") -> str:
    return f"---\n{front}\n---\n\n{body}"


def test_the_real_documentation_has_no_gaps() -> None:
    assert cs.collect(DOCS_REPO / "docs") == []


def test_there_is_no_baseline_to_hide_a_gap_in() -> None:
    assert not (DOCS_REPO / "scripts" / "structure-baseline.txt").exists()
    assert not hasattr(cs, "read_baseline") and not hasattr(cs, "evaluate")


def test_headings_inside_any_fence_do_not_count() -> None:
    missing_verify = HOW_TO.replace("## Verify\n\nOpen the address.\n", "")
    for fence in (FENCE, TILDES, "  " + FENCE, "   " + TILDES):
        hidden = missing_verify.replace("## Related pages", f"{fence}text\n## Verify\n{fence}\n\n## Related pages")
        assert "section:verify" in rules("guides/deploy.md", hidden), repr(fence)


def test_every_fence_style_needs_a_language() -> None:
    for fence in (FENCE, TILDES, "   " + FENCE):
        assert rules("roadmap.md", page(f"# Roadmap\n\n{fence}\nplain\n{fence}\n")) == {"fence-language"}, repr(fence)
        assert rules("roadmap.md", page(f"# Roadmap\n\n{fence}text\nplain\n{fence}\n")) == set(), repr(fence)
    attr = page(f"# Roadmap\n\n{FENCE}{{ .bash title=\"x\" }}\nls\n{FENCE}\n")
    assert rules("roadmap.md", attr) == set()


def test_a_longer_fence_is_not_closed_by_a_shorter_one() -> None:
    body = f"# Roadmap\n\n{FENCE}{FENCE[0]}text\n{FENCE}\n# not a heading\n{FENCE}{FENCE[0]}\n"
    assert rules("roadmap.md", page(body)) == set()


def test_numbered_steps_are_found_in_tabs_and_admonitions() -> None:
    tabbed = HOW_TO.replace("1. Open **Applications**.\n2. Select **Deploy**.\n", '=== "Compose"\n\n    1. Open **Applications**.\n    2. Select **Deploy**.\n')
    assert rules("guides/deploy.md", tabbed) == set()
    concept = page('# Idea\n\n=== "Compose"\n\n    1. First.\n    2. Second.\n')
    assert rules("concepts/idea.md", concept) == {"step-list"}


def test_numbers_inside_code_are_not_steps() -> None:
    concept = page(f"# Idea\n\n{FENCE}text\n1. not a step\n{FENCE}\n")
    assert rules("concepts/idea.md", concept) == set()


def test_only_a_real_table_satisfies_a_reference_page() -> None:
    ref = lambda body: rules("reference/x.md", page("# Settings\n\n" + body))  # noqa: E731
    assert ref("| not a table |\n") == {"table"}
    assert ref("A rule\n\n---\n\nText | with a pipe\n") == {"table"}
    assert ref("| Name | Value |\n| --- | --- |\n| a | b |\n") == set()
    assert ref("Name | Value\n--- | ---\na | b\n") == set()
    assert ref("| Left | Right |\n|:---|---:|\n| a | b |\n") == set()
    assert ref(f"{FENCE}text\n| Name | Value |\n| --- | --- |\n{FENCE}\n") == {"table"}


def test_heading_attributes_do_not_hide_a_required_section() -> None:
    attributed = HOW_TO.replace("## Verify", "## Verify {#verify}").replace("# Deploy an application", "# Deploy an application {#top}")
    assert rules("guides/deploy.md", attributed) == set()


def test_descriptions_are_judged_as_sentences() -> None:
    ok = ["Deploy a service at its own address.", 'Use the "Deploy" button.', "Deploy a service (see the guide).", "Version 2.1 of the API, with more detail."]
    for value in ok:
        assert rules("roadmap.md", page("# Roadmap\n", f"description: {value!r}".replace("'", '"') if '"' not in value else f"description: '{value}'")) == set(), value
    for value in ["Two sentences. Here.", "No full stop", "Ends with a question?"]:
        assert rules("roadmap.md", page("# Roadmap\n", f'description: "{value}"')) == {"description"}, value


def test_front_matter_with_crlf_line_endings_and_folded_yaml_is_read() -> None:
    crlf = "---\r\ndescription: What is planned.\r\n---\r\n\r\n# Roadmap\r\n"
    assert rules("roadmap.md", crlf) == set()
    folded = "---\ndescription: >\n  What is planned\n  for the next release.\n---\n\n# Roadmap\n"
    assert rules("roadmap.md", folded) == set()
    assert rules("roadmap.md", "---\ndescription: [unclosed\n---\n\n# Roadmap\n") == {"description"}
    assert rules("roadmap.md", "---\ndescription: 5\n---\n\n# Roadmap\n") == {"description"}


def test_only_em_dashes_are_rejected() -> None:
    assert rules("roadmap.md", page(f"# Roadmap\n\nBetween 2{EN}100 nodes.\n")) == set()
    assert rules("roadmap.md", page(f"# Roadmap\n\nA pause {EM} here.\n")) == {"dash"}


def test_abbreviations_in_a_description_do_not_split_the_sentence() -> None:
    for value in ["Use e.g. Linux.", "An i.e. example.", "Works on Linux, macOS, etc. for teams.", "Runs in the U.S. region.", "Compare vs. the old setup."]:
        assert rules("roadmap.md", page("# Roadmap\n", f'description: "{value}"')) == set(), value
    assert rules("roadmap.md", page("# Roadmap\n", 'description: "Use e.g. Linux. And more."')) == {"description"}


def test_headings_and_steps_inside_html_comments_do_not_count() -> None:
    hidden = HOW_TO.replace("## Verify\n\nOpen the address.\n", "<!--\n## Verify\n\nOpen the address.\n-->\n")
    assert rules("guides/deploy.md", hidden) == {"section:verify"}
    one_line = HOW_TO.replace("## Verify", "<!-- ## Verify -->")
    assert "section:verify" in rules("guides/deploy.md", one_line)
    steps = HOW_TO.replace("1. Open **Applications**.\n2. Select **Deploy**.\n", "<!--\n1. Open it.\n-->\nOpen Applications.\n")
    assert rules("guides/deploy.md", steps) == {"steps"}
    kept = HOW_TO.replace("## Verify", "## Verify <!-- shown -->")
    assert rules("guides/deploy.md", kept) == set()


def test_a_comment_can_contain_a_fence_marker_without_confusing_the_scan() -> None:
    body = f"# Roadmap\n\n<!--\n{FENCE}\n-->\n\n{FENCE}text\nok\n{FENCE}\n"
    assert rules("roadmap.md", page(body)) == set()


def test_indented_code_blocks_are_not_structure() -> None:
    no_steps = HOW_TO.replace("1. Open **Applications**.\n2. Select **Deploy**.\n", "Open Applications.\n\n    1. not a Markdown list\n")
    assert rules("guides/deploy.md", no_steps) == {"steps"}
    concept = page("# Idea\n\nThe layout is:\n\n    1. a line of sample output\n")
    assert rules("concepts/idea.md", concept) == set()
    reference = page("# Settings\n\nExample:\n\n    | Name | Value |\n    | --- | --- |\n")
    assert rules("reference/settings.md", reference) == {"table"}
    literal = page(f"# Roadmap\n\nExample:\n\n    {FENCE}\n    not a fence\n")
    assert rules("roadmap.md", literal) == set()


def test_indentation_inside_lists_tabs_and_admonitions_is_still_structure() -> None:
    tab = page('# Idea\n\n=== "Compose"\n\n    1. First.\n')
    assert rules("concepts/idea.md", tab) == {"step-list"}
    note = page("# Idea\n\n!!! note\n\n    1. First.\n")
    assert rules("concepts/idea.md", note) == {"step-list"}
    item = page("# Idea\n\n- Item\n\n    1. Nested.\n")
    assert rules("concepts/idea.md", item) == {"step-list"}
    table_in_tab = page('# Settings\n\n=== "Compose"\n\n    | Name | Value |\n    | --- | --- |\n')
    assert rules("reference/settings.md", table_in_tab) == set()


def test_a_lazy_continuation_line_is_not_a_code_block() -> None:
    body = HOW_TO.replace("Deploy a service so people can reach it.", "Deploy a service so people\n    can reach it.")
    assert rules("guides/deploy.md", body) == set()

