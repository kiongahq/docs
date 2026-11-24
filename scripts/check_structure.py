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

Section landing pages (index.md) and the generated changelog are checked only for
the rules that apply to every page. A page titled Troubleshooting is the
troubleshooting content, so it does not repeat the section. Section headings must
match the standard exactly, so every page of a type reads the same way.

There is no list of exceptions: any gap fails the check, so a page cannot ship
without the shape of its type.

Usage:
  python scripts/check_structure.py [--docs docs]
Exit status: 0 clean, 1 findings.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

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

# A numbered list item at any indent: steps inside content tabs and admonitions are indented.
NUMBERED = re.compile(r"^[ \t]*\d+\. ", re.M)
# A fence opens with three or more backticks or tildes, indented when it sits in a list, tab or admonition.
FENCE = re.compile(r"^([ \t]*)(`{3,}|~{3,})(.*)$")
# The separator row of a Markdown table: dashes with at least one pipe, so a bare --- rule does not count.
TABLE_SEPARATOR = re.compile(r"^(?=[^\n]*\|)[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*(?:\|[ \t]*:?-{3,}:?[ \t]*)*\|?[ \t]*$")
# A sentence boundary: end punctuation, optional closing quotes or brackets, then the start of another sentence.
SENTENCE_BREAK = re.compile(r"[.!?][\"')\]]*\s+(?=[A-Z0-9`\"(\[])")
SENTENCE_END = re.compile(r"\.[\"')\]]*$")
HEADING_ATTRIBUTES = re.compile(r"\s*\{[^}]*\}\s*$")
# The start of a list item, content tab, admonition or collapsible block, after any indent.
CONTAINER_START = re.compile(r"(?:[-*+]|\d+\.)[ \t]|(?:===|\?\?\?\+?|!!!)[ ]")
# Words and initialisms whose full stop does not end a sentence.
ABBREVIATION = re.compile(r"\b(?:e\.g|i\.e|etc|vs|approx|Inc|Ltd|Dr|Mr|Ms|St|No)\.|\b(?:[A-Za-z]\.){2,}")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
DASHES = ("\u2014",)  # an em dash


@dataclass(frozen=True)
class Finding:
    page: str
    rule: str
    detail: str


def page_type(relative: Path) -> str:
    """tutorial, how-to, explanation, reference, index (a section landing page) or page."""
    if relative.name == "index.md" and len(relative.parts) > 1:
        return "index"
    if len(relative.parts) > 1:
        return SECTION_TYPES.get(relative.parts[0], "page")
    return "page"


def split_front_matter(text: str) -> tuple[dict | None, str]:
    """The parsed front matter (None when absent, an empty dict when it is not valid YAML) and the body."""
    text = text.replace("\r\n", "\n")
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None, text
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        data = {}
    return (data if isinstance(data, dict) else {}), text[match.end():]


def indent_width(line: str) -> int:
    """The indent of a line in columns, with tabs stopping every four columns."""
    width = 0
    for char in line:
        if char == " ":
            width += 1
        elif char == "\t":
            width += 4 - width % 4
        else:
            break
    return width


def scan_code(body: str) -> tuple[str, list[str]]:
    """The body reduced to what the site renders as structure, and the language of each fence.

    Fenced code, HTML comments and indented code blocks are blanked line for line, so a
    heading, step or table inside them does not count. Backtick and tilde fences are both
    recognised, at any indent. A fence closes only with the same character, at least as long,
    and nothing after it. An empty language means none.

    A list item, content tab or admonition opens a body indented four columns deeper than its
    first line, and bodies nest. Indentation up to that depth is structure. A line indented four
    columns beyond the current body, after a blank line, starts an indented code block that
    runs until a line indented less.
    """
    plain: list[str] = []
    languages: list[str] = []
    open_fence: tuple[str, int] | None = None
    in_comment = False
    bodies: list[int] = []
    code_indent: int | None = None
    previous_blank = True
    for raw in body.split("\n"):
        line = raw
        if open_fence is not None:
            match = FENCE.match(line)
            plain.append("")
            if match and match.group(2)[0] == open_fence[0] and len(match.group(2)) >= open_fence[1] and not match.group(3).strip():
                open_fence = None
            previous_blank = False
            continue
        if in_comment:
            end = line.find("-->")
            if end < 0:
                plain.append("")
                continue
            in_comment = False
            line = line[end + 3:]
        line = HTML_COMMENT.sub("", line)
        start = line.find("<!--")
        if start >= 0:
            in_comment = True
            line = line[:start]
        if not line.strip():
            plain.append("")
            previous_blank = True
            continue
        width = indent_width(line)
        if code_indent is not None:
            if width >= code_indent:
                plain.append("")
                previous_blank = False
                continue
            code_indent = None
        while bodies and width < bodies[-1]:
            bodies.pop()
        base = bodies[-1] if bodies else 0
        if previous_blank and width >= base + 4:
            code_indent = base + 4
            plain.append("")
            previous_blank = False
            continue
        if CONTAINER_START.match(line.lstrip()):
            bodies.append(width + 4)
        match = FENCE.match(line)
        if match:
            open_fence = (match.group(2)[0], len(match.group(2)))
            info = match.group(3).strip()
            if info.startswith("{"):
                classes = re.findall(r"\.([\w+#-]+)", info)
                languages.append(classes[0] if classes else "")
            else:
                languages.append(info.split(" ")[0] if info else "")
            plain.append("")
        else:
            plain.append(line)
        previous_blank = False
    return "\n".join(plain), languages


def has_table(plain: str) -> bool:
    """True when a header row with a pipe is followed by a table separator row."""
    lines = plain.split("\n")
    return any("|" in lines[i - 1] and TABLE_SEPARATOR.match(lines[i]) for i in range(1, len(lines)))


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def description_problem(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return "front matter needs a one-sentence description"
    text = " ".join(value.split())
    masked = ABBREVIATION.sub(lambda m: m.group(0).replace(".", ""), text)
    if SENTENCE_BREAK.search(masked) or not SENTENCE_END.search(text):
        return "the description must be exactly one sentence ending in a full stop"
    return None


def check_page(relative: Path, text: str) -> list[Finding]:
    page = relative.as_posix()
    kind = page_type(relative)
    front, body = split_front_matter(text)
    plain, languages = scan_code(body)
    findings: list[Finding] = []

    def add(rule: str, detail: str) -> None:
        findings.append(Finding(page, rule, detail))

    problem = description_problem((front or {}).get("description"))
    if problem:
        add("description", problem)

    headings = [
        (len(m.group(1)), HEADING_ATTRIBUTES.sub("", m.group(2)).strip())
        for m in re.finditer(r"^(#{1,6}) +(.+?)\s*$", plain, re.M)
    ]
    if sum(1 for level, _ in headings if level == 1) != 1:
        add("h1", "the page needs exactly one H1")
    previous = 1
    for level, title in headings:
        if level > previous + 1:
            add("heading-level", f"'{title}' skips from H{previous} to H{level}")
            break
        previous = level

    if any(language == "" for language in languages):
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
    if kind == "reference" and not has_table(plain):
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--docs", default="docs", type=Path)
    args = parser.parse_args(argv)

    findings = collect(args.docs)
    for finding in findings:
        print(f"{finding.page}: [{finding.rule}] {finding.detail}")
    pages = len({finding.page for finding in findings})
    status = "ok" if not findings else "failed"
    print(f"structure check {status}: {len(findings)} gaps in {pages} pages", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
