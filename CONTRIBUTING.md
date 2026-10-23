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
