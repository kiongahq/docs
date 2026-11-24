#!/usr/bin/env python3
"""Check that every documentation page has the shape its page type requires.

The documentation standard sorts product pages into four Diátaxis types by the
section they sit in. This script checks the parts of that standard a machine can
check, so structure does not depend on a reviewer remembering it:

  every page   front matter with a one-sentence description, one H1, no skipped
               heading levels, a language on every code fence, no em dashes
  tutorial     Before you begin, numbered steps, Next steps
  how-to       Before you begin, numbered steps, Verify, Troubleshooting, Related pages
  explanation  no numbered step lists
  reference    at least one table

A page titled Troubleshooting is the troubleshooting content, so it does not repeat the section.
Section landing pages (index.md) and the generated changelog are checked only for
the rules that apply to every page. Section headings must match the standard
exactly, so every page of a type reads the same way.

Known gaps live in scripts/structure-baseline.txt, one `<page> <rule>` per line
with a comment saying why the page cannot meet the rule yet. The check fails on a
gap that is not in the baseline, and on a baseline line whose gap no longer
exists, so the list can only shrink.

Usage:
  python scripts/check_structure.py [--docs docs] [--baseline scripts/structure-baseline.txt]
Exit status: 0 clean, 1 findings.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Section directory -> page type, from the documentation standard.
SECTION_TYPES = {
    "getting-started": "tutorial",
    "guides": "how-to",
    "operations": "how-to",
    "concepts": "explanation",
    "reference": "reference",
}

BEFORE = "Before you begin"
VERIFY = "Verify"
TROUBLESHOOTING = "Troubleshooting"
RELATED = "Related pages"
NEXT = "Next steps"

# Required H2 headings, in the order they must appear.
REQUIRED_SECTIONS = {
    "tutorial": [BEFORE, NEXT],
    "how-to": [BEFORE, VERIFY, TROUBLESHOOTING, RELATED],
}

# Pages the build generates, so their source cannot follow the page shapes.
GENERATED = {"changelog.md"}

NUMBERED = re.compile(r"^\s{0,3}\d+\. ", re.M)
TABLE_ROW = re.compile(r"^\|.+\|\s*$", re.M)
DASHES = ("\u2014",)  # an em dash


@dataclass(frozen=True)
class Finding:
    page: str
    rule: str
    detail: str

    def key(self) -> str:
        return f"{self.page} {self.rule}"


def page_type(relative: Path) -> str:
    """tutorial, how-to, explanation, reference, index (a section landing page) or page."""
    if relative.name == "index.md" and len(relative.parts) > 1:
        return "index"
    if len(relative.parts) > 1:
        return SECTION_TYPES.get(relative.parts[0], "page")
    return "page"


def split_front_matter(text: str) -> tuple[str | None, str]:
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    return (match.group(1), text[match.end():]) if match else (None, text)


def blank_code(body: str) -> str:
    """The body with fenced code replaced by blank lines, so headings inside code do not count."""
    return re.sub(r"^```.*?^```[ \t]*$", lambda m: "\n" * m.group(0).count("\n"), body, flags=re.S | re.M)


def fence_languages(body: str) -> list[str]:
    """The language of each opening code fence, in order. An empty string means none."""
    languages: list[str] = []
    inside = False
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("```"):
            continue
        if inside:
            inside = False
        else:
            inside = True
            languages.append(stripped[3:].strip().split(" ")[0].split("{")[0])
    return languages


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?](?:\s|$)", text.strip()))


def check_page(relative: Path, text: str) -> list[Finding]:
    page = relative.as_posix()
    kind = page_type(relative)
    front, body = split_front_matter(text)
    plain = blank_code(body)
    findings: list[Finding] = []

    def add(rule: str, detail: str) -> None:
        findings.append(Finding(page, rule, detail))

    description = re.search(r"^description:\s*(.+)$", front or "", re.M)
    if not description:
        add("description", "front matter needs a one-sentence description")
    else:
        value = description.group(1).strip().strip("\"'")
        if sentence_count(value) != 1 or not value.endswith("."):
            add("description", "the description must be exactly one sentence ending in a full stop")

    headings = [(len(m.group(1)), m.group(2).strip()) for m in re.finditer(r"^(#{1,6}) +(.+?)\s*$", plain, re.M)]
    if sum(1 for level, _ in headings if level == 1) != 1:
        add("h1", "the page needs exactly one H1")
    previous = 1
    for level, title in headings:
        if level > previous + 1:
            add("heading-level", f"'{title}' skips from H{previous} to H{level}")
            break
        previous = level

    if any(language == "" for language in fence_languages(body)):
        add("fence-language", "every code fence needs a language; use text for plain output")
    if any(dash in text for dash in DASHES):
        add("dash", "no em dashes; use a comma, colon, period or parentheses")

    if kind in ("tutorial", "how-to"):
        h2 = [title for level, title in headings if level == 2]
        h1 = next((title for level, title in headings if level == 1), "")
        # A page titled Troubleshooting is the troubleshooting content, so it needs no section of that name.
        required = [name for name in REQUIRED_SECTIONS[kind] if not (name == TROUBLESHOOTING and h1 == TROUBLESHOOTING)]
        positions = [h2.index(name) if name in h2 else -1 for name in required]
        for name, position in zip(required, positions):
            if position < 0:
                add(f"section:{slug(name)}", f"missing the H2 '{name}'")
        present = [p for p in positions if p >= 0]
        if present != sorted(present):
            add("section-order", "required sections must appear in this order: " + ", ".join(required))
        if not NUMBERED.search(plain):
            add("steps", f"a {kind} needs numbered steps")
    if kind == "explanation" and NUMBERED.search(plain):
        add("step-list", "an explanation describes what and why; move numbered steps to a how-to")
    if kind == "reference" and not TABLE_ROW.search(plain):
        add("table", "a reference page is scannable: use at least one table")
    return findings


def collect(docs: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(docs.rglob("*.md")):
        relative = path.relative_to(docs)
        if relative.as_posix() in GENERATED:
            continue
        findings.extend(check_page(relative, path.read_text(encoding="utf-8")))
    return findings


def read_baseline(path: Path) -> set[str]:
    if not path.exists():
        return set()
    entries: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            entries.add(" ".join(line.split()))
    return entries


def evaluate(findings: list[Finding], baseline: set[str]) -> tuple[list[Finding], list[str]]:
    """The findings the baseline does not cover, and the baseline lines nothing matches."""
    keys = {finding.key() for finding in findings}
    new = [finding for finding in findings if finding.key() not in baseline]
    stale = sorted(entry for entry in baseline if entry not in keys)
    return new, stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--docs", default="docs", type=Path)
    parser.add_argument("--baseline", default=Path("scripts/structure-baseline.txt"), type=Path)
    parser.add_argument("--list", action="store_true", help="print every gap, including the baselined ones")
    args = parser.parse_args(argv)

    findings = collect(args.docs)
    baseline = read_baseline(args.baseline)
    if args.list:
        for finding in findings:
            print(f"{finding.key()}  {finding.detail}")
        print(f"{len(findings)} gaps in {len({f.page for f in findings})} pages", file=sys.stderr)
        return 0
    new, stale = evaluate(findings, baseline)
    for finding in new:
        print(f"{finding.page}: [{finding.rule}] {finding.detail}")
    for entry in stale:
        print(f"{args.baseline}: stale entry '{entry}'; the gap is fixed, so remove the line")
    covered = len(findings) - len(new)
    status = "ok" if not new and not stale else "failed"
    print(f"structure check {status}: {len(new)} new gaps, {len(stale)} stale baseline entries, {covered} known gaps remaining", file=sys.stderr)
    return 1 if new or stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
