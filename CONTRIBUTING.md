# Contributing to the documentation

Thank you for improving Kionga's documentation. The full standard (page types, style,
checks and URL rules) is the handbook's
[documentation standard](https://kiongahq.github.io/docs/engineering/contributing/documentation/).
This page is the short version.

## Where a page goes

- **Product documentation** (`docs/`): what Kionga does and how to use, deploy and
  operate it, organized by Diátaxis (tutorials, how-to guides, concepts, reference).
- **Engineering handbook** (`engineering/docs/`): how Kionga is built. Architecture in
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

The repository must allow GitHub Actions to create pull requests under
**Settings > Actions > General > Workflow permissions**. The workflow uses the
repository token by default. GitHub does not run CI automatically for release
pull requests opened by that token. To trigger normal pull request checks, set
`RELEASE_PLEASE_TOKEN` to a GitHub App token or fine-grained personal access token
with repository contents, issues and pull request write permissions. Do not merge
a release pull request with required checks missing. A maintainer can close and
reopen the pull request to trigger its checks when using the repository token.

The public changelog page reads the root changelog during the MkDocs build. Edit
release notes in the release pull request; do not copy them into a second page.
Run `make docs-test docs-build` before merging changes to release metadata or the
site hook. `docs-test` also needs Node.js 22 for the assistant tests.
