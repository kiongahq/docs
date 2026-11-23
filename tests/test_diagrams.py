"""Gate tests for Mermaid diagrams. Keep this file identical in docs and engineering-docs.

The Kionga diagram theme lives in two shared files:
  docs/stylesheets/diagrams.css   color tokens (--kd-*) for light and dark schemes
  docs/javascripts/mermaid-theme.js  turns those tokens into Mermaid themeCSS
Material renders diagrams inside a closed shadow root, so per-diagram colors or page CSS
selectors silently stop working. These tests keep diagram sources limited to structure and
semantic roles, and make every diagram describe itself to screen readers.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BLOCK = re.compile(r"^```mermaid\n(.*?)\n```", re.S | re.M)
ROLES = {"core", "data", "runtime", "external"}
GENERIC = {
    "System components grouped by responsibility; arrows show their dependencies.",
    "Ordered interactions between the named participants.",
}


def diagrams():
    for path in sorted(DOCS.rglob("*.md")):
        for n, match in enumerate(BLOCK.finditer(path.read_text()), 1):
            yield f"{path.relative_to(ROOT)} #{n}", match.group(1)


class MermaidDiagrams(unittest.TestCase):
    def setUp(self):
        self.all = list(diagrams())

    def test_diagrams_exist(self):
        self.assertTrue(self.all, "expected at least one Mermaid diagram")

    def test_theme_is_central_not_per_diagram(self):
        banned = [
            (re.compile(r"#[0-9a-fA-F]{3,8}\b"), "hex color"),
            (re.compile(r"^\s*classDef\b", re.M), "classDef"),
            (re.compile(r"^\s*style\s", re.M), "inline style"),
            (re.compile(r"^\s*linkStyle\b", re.M), "linkStyle"),
            (re.compile(r"%%\{\s*init"), "init directive"),
            (re.compile(r"\A---\n"), "front-matter config"),
        ]
        for name, src in self.all:
            for pattern, label in banned:
                with self.subTest(diagram=name, rule=label):
                    self.assertIsNone(pattern.search(src), f"{name}: {label}; theme lives in mermaid-theme.js")

    def test_only_semantic_roles(self):
        for name, src in self.all:
            for line in re.findall(r"^\s*class\s+\S+\s+(\S+)\s*$", src, re.M):
                with self.subTest(diagram=name):
                    self.assertIn(line, ROLES, f"{name}: unknown role {line!r}")

    def test_every_diagram_describes_itself(self):
        seen = {}
        for name, src in self.all:
            with self.subTest(diagram=name):
                title = re.search(r"^\s*accTitle:\s*(.+)$", src, re.M)
                descr = re.search(r"^\s*accDescr:\s*(.+)$", src, re.M)
                self.assertTrue(title, f"{name}: missing accTitle")
                self.assertTrue(descr, f"{name}: missing accDescr")
                text = descr.group(1).strip()
                self.assertNotIn(text, GENERIC, f"{name}: accDescr is boilerplate")
                self.assertGreaterEqual(len(text.split()), 12, f"{name}: accDescr too short to explain the diagram")
                self.assertNotIn(text, seen, f"{name}: accDescr duplicates {seen.get(text)}")
                seen[text] = name

    def test_sequence_numbering_declared_once(self):
        for name, src in self.all:
            with self.subTest(diagram=name):
                self.assertLessEqual(len(re.findall(r"^\s*autonumber\b", src, re.M)), 1)

    def test_no_browser_only_syntax(self):
        # `box` color parsing needs a DOM (new Option()), which breaks the Node parse check.
        for name, src in self.all:
            with self.subTest(diagram=name):
                self.assertIsNone(re.search(r"^\s*box\b", src, re.M), f"{name}: sequence box")


class DiagramTheme(unittest.TestCase):
    def test_theme_files_are_wired(self):
        config = (ROOT / "mkdocs.yml").read_text()
        css = (DOCS / "stylesheets" / "diagrams.css").read_text()
        js = (DOCS / "javascripts" / "mermaid-theme.js").read_text()
        self.assertIn("stylesheets/diagrams.css", config)
        pinned = re.search(r"mermaid@(\d+\.\d+\.\d+)/dist/mermaid\.min\.js", config)
        self.assertTrue(pinned, "pin an exact Mermaid version so Material does not load mermaid@11 latest")
        self.assertLess(config.index(pinned.group(0)), config.index("javascripts/mermaid-theme.js"),
                        "Mermaid must load before the theme wrapper")
        for role, token in (("core", "core"), ("data", "data"), ("runtime", "run"), ("external", "ext")):
            with self.subTest(role=role):
                for part in ("bg", "line", "ink"):
                    self.assertEqual(css.count(f"--kd-{token}-{part}:"), 2, f"--kd-{token}-{part} needs light and dark values")
        self.assertIn("mermaid.initialize", js)


if __name__ == "__main__":
    unittest.main()
