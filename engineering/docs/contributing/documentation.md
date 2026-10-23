---
description: The documentation standard for Kionga, covering Diátaxis for product docs, arc42 and MADR for the handbook, the Google style guide through Vale, and the reference and URL checks.
---

# Documentation standard

The `docs` repository holds two MkDocs Material sites:

| Site | Source | Published at | Audience |
| --- | --- | --- | --- |
| Product documentation | `docs/`, config `mkdocs.yml` | <https://kiongahq.github.io/docs/> | People who install, use, administer and operate Kionga |
| Engineering handbook | `engineering/docs/`, config `engineering/mkdocs.yml` | <https://kiongahq.github.io/docs/engineering/> | People who change Kionga's code |

Links within a site are relative `.md` links; links between the sites are absolute URLs.

## Structure

**Product documentation follows [Diátaxis](https://diataxis.fr/).**

| Type | Section | Shape |
| --- | --- | --- |
| Tutorial | Get started | An outcome-oriented lesson: before you begin, numbered steps with the expected result, what you built, next steps |
| How-to guide | Guides, Deploy and operate | One task: the goal in the first sentence, before you begin, numbered imperative steps, verify, troubleshooting, related pages |
| Explanation | Concepts | What it is and why; no step lists |
| Reference | Reference | Complete, exact, scannable; tables; one shape per entry |

Product pages describe what Kionga does and how to use it. How it is built (Go package
names, source file paths) belongs in the handbook; a product page links here with one
sentence when internals help.

**The handbook follows [arc42](https://arc42.org/overview) and [MADR](https://adr.github.io/madr/).**
Architecture lives in the twelve arc42 sections under `architecture/`, decisions are
MADR 4 records under `decisions/` (start from the [template](../decisions/template.md)),
and each component page has the same shape: responsibility, interfaces, dependencies,
configuration, code map, tests.

**Every page** starts with YAML front matter containing `description:` (one sentence,
used for search and link previews), has one H1, and uses sentence-case headings.

## Style

Follow the [Google developer documentation style guide](https://developers.google.com/style):
second person, present tense, active voice, short sentences, code formatting for
anything literal (commands, paths, environment variables, service names, values).
House rules on top:

- No em dashes; no "e.g." or "i.e."; product names capitalized in prose (PostgreSQL,
  Kafka, MLflow, Prefect, Redis, Dex, Langfuse, Jupyter).
- No marketing superlatives or filler. The reference checker rejects a list of banned
  words in prose.
- Admonitions sparingly; content tabs for alternatives such as Compose and Kubernetes.
- Accuracy over coverage: every command, flag, variable, route, port and default must
  match the code. If something is unclear, describe less.

Vale enforces the Google style (`.vale.ini`, the Google package plus the `Kionga`
vocabulary in `.vale/styles/config/vocabularies/Kionga/accept.txt`). Errors fail;
warnings and suggestions are advisory.

## Checks

Run these from the `docs` repository:

| Command | What it checks |
| --- | --- |
| `make docs-install` | Installs MkDocs and the plugins from `requirements-docs.txt` |
| `make docs-serve`, `make docs-serve-engineering` | Live preview at `http://127.0.0.1:8000` and `http://127.0.0.1:8001` |
| `make docs-build` | Strict builds of both sites; broken links, anchors and missing navigation entries fail |
| `make docs-lint` | Vale with `--minAlertLevel=error` over both sites |
| `make docs-check` | `docs/scripts/check_references.py` against the sibling checkouts (`KIONGA_SRC`, default `..`) |
| `make docs-test` | `pytest` over `tests/`: the reference checker's own tests and the legacy URL tests |

`docs/scripts/check_references.py` reads every page and resolves what a reader would copy:
`make` targets, paths into sibling repositories (checked against git-tracked files),
environment variable names, REST routes the gateway registers, `mlaiops` and `kionga`
CLI commands, and Python SDK names and call signatures. It also enforces the house
style (no em dashes, no banned words). With `--product` it adds the boundary rule:
product pages may not mention Go package paths or `.go` files, and must link to the
handbook instead. `make docs-check` runs it twice: with `--product` over `docs/`, and
with `--docs engineering/docs` over the handbook. A known false positive goes in
`docs/scripts/reference-allowlist.txt` with a comment saying why; when a reference is wrong,
fix the page.

## Moving pages

Published URLs stay valid. `docs/tests/legacy-pages.txt` lists every page published before
the product and handbook split; `docs/tests/test_site_urls.py` fails if one of them no longer
exists and has no redirect, if a redirect points at a missing page (in either site), or
if a redirect shadows a live page. When you move a product page, add an entry to the
`redirects` plugin's `redirect_maps` in `mkdocs.yml`; a page that moves to the handbook
redirects to its absolute handbook URL.

## Review checklist

- [ ] The page has front matter with `description:`, one H1, sentence-case headings, and
  is in the right site and section of the navigation.
- [ ] Every command, path, variable, route and default was checked against the code.
- [ ] No secrets, machine-specific paths or generated site files.
- [ ] `make docs-build`, `make docs-lint`, `make docs-check` and `make docs-test` pass.
