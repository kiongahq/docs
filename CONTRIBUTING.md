# Contributing to the documentation

Thank you for improving Kionga's documentation. The full standard (page types, style,
checks and URL rules) is the handbook's
[documentation standard](https://github.com/kiongahq/engineering-docs/blob/main/docs/contributing/documentation.md).
This page is the short version.

## Where a page goes

- **Product documentation** (`docs/`): what Kionga does and how to use, deploy and
  operate it, organized by Diátaxis (tutorials, how-to guides, concepts, reference).
- **Engineering handbook** (private `kiongahq/engineering-docs` repository): how Kionga is built. Architecture in
  arc42 sections, decisions as MADR records, one page per component, contribution
  workflow.

Product pages do not name Go packages or source files; they link to the handbook
instead. Links within a site are relative; links between sites are absolute URLs.

## Writing rules

- Front matter with a one-sentence `description:`, one H1, sentence-case headings.
- Google developer documentation style: second person, present tense, active voice.
- No em dashes, no Latin abbreviations, no marketing language.
- Check every command, path, variable, route and default against the code.
- Keep published URLs working: when you move a product page, add a redirect in
  `mkdocs.yml`.

## Before you open a pull request

```bash
make docs-build docs-lint docs-check docs-test
```

All four must pass. Commit with a conventional message, for example
`docs(guides): add the feature store guide`.

## Documentation releases

Use conventional commits so the release workflow can group changes and choose a
semantic version:

- `feat:` adds a feature and increments the minor version.
- `fix:` corrects a defect and increments the patch version.
- `docs:` updates documentation and increments the patch version.
- `!` after a type or a `BREAKING CHANGE:` footer increments the major version.

Release Please opens or updates a release pull request after changes reach
`main`. Review its generated `CHANGELOG.md`, `version.txt` and
`.release-please-manifest.json` together. Merge the release pull request to create
the version tag and GitHub release. The normal Pages workflow publishes the
updated changelog and version badge. Until the first release, the badge reads
**Development**. These versions apply to this documentation repository, not the
component repositories. Historical tags preserve documentation sources; the live
site follows `main` and does not host separate copies of older versions.

The organization prevents the default workflow token from creating or approving
pull requests. Set `RELEASE_PLEASE_TOKEN` to a GitHub App token or a
fine-grained personal access token with contents, issues, and pull request write
permissions for this repository. This dedicated token lets Release Please create
release pull requests and trigger their required checks. It has no branch-rule
bypass; a maintainer must review each release.

Without this secret, the workflow fails with an explicit configuration error.
Configure it before enabling release automation. Keep the organization restriction
enabled; never merge a release pull request with missing checks or reviews.

The public changelog page reads the root changelog during the MkDocs build. Edit
release notes in the release pull request; do not copy them into a second page.
Run `make docs-test docs-build` before merging changes to release metadata or the
site hook. `docs-test` also needs Node.js 22 for the assistant tests.

The [release process](https://github.com/kiongahq/engineering-docs/blob/main/docs/contributing/releases.md) covers component
versions, package publication, PyPI setup and the aggregated product changelog.


## Diagram design

Keep architecture diagrams as Mermaid blocks in Markdown, one question per
diagram. Use short labels, one reading direction, and subgraphs only for real
boundaries. Split a dense view into focused diagrams rather than shrinking text.

Diagram sources hold structure and meaning only. Tag nodes with one of four
roles and let the shared theme color them in both schemes:

| Role | Use for | Example |
| --- | --- | --- |
| `core` | the component the diagram is about | `class gw core` |
| `runtime` | services that execute work | `class runner,sm runtime` |
| `data` | stores, queues and registries | `class pg,kafka data` |
| `external` | things outside Kionga (dashed) | `class idp external` |

Labels must still make sense without color. Every diagram needs an `accTitle`
and an `accDescr` that explains what the diagram shows in a sentence or two.

Do not add `classDef`, `style`, `linkStyle`, hex colors, `%%{init}%%` or
front-matter config: Material renders diagrams inside a closed shadow root, so
those either break dark mode or silently do nothing. Theme changes go in
`docs/stylesheets/diagrams.css` (color tokens) and
`docs/javascripts/mermaid-theme.js` (Mermaid themeCSS and layout defaults). Both
files and `tests/test_diagrams.py` are shared with the other documentation site;
change them in both. Avoid sequence `box` groups; the Node parse check cannot
evaluate their colors.

Layout tips that hold up in Mermaid's Dagre layout:

- Links into a subgraph make Mermaid ignore that subgraph's `direction`.
- To stack groups as rows, chain their first nodes with invisible links
  (`a ~~~ b ~~~ c`).
- A longer arrow (`--->`, `---->`) pushes its target one or two ranks further,
  which turns side-by-side groups into columns.

Check a change with `tests/test_diagrams.py`, the Mermaid parse check, and a look
at the built page in both color schemes.
