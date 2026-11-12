# Kionga documentation

Source for Kionga's public product documentation, built with
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/) and published from
`main` to [GitHub Pages](https://kiongahq.github.io/docs/).

The engineering handbook lives in the private
[kiongahq/engineering-docs](https://github.com/kiongahq/engineering-docs) repository.
It is available to Kionga organization members and is not included in this site's
HTML, search index, or deployment artifact.

Kionga is a self-hosted, open-source platform for machine learning, data and AI
agents. Its repositories use the [MIT License](LICENCE); third-party components keep
their own licenses.

## Build and check

```bash
make docs-install            # MkDocs and plugins from requirements-docs.txt
make docs-serve              # product site, http://127.0.0.1:8000
make docs-build              # strict product build and publication boundary check
make docs-lint               # Vale, Google developer documentation style
make docs-check              # references checked against the sibling checkouts
make docs-test               # reference checker and legacy URL tests (pytest)
```

`make docs-check` reads the code in the sibling repositories (`KIONGA_SRC=..` by
default). Clone them beside this one with `make -C ../deploy workspace`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The full standard is the handbook's
[documentation standard](https://github.com/kiongahq/engineering-docs/blob/main/docs/contributing/documentation.md).

## Documentation assistant

The product site has an **Ask Kionga** panel. Without an AI endpoint, it searches
MkDocs' generated index in the browser and links to matching pages. It does not
produce AI answers or send questions to an external service.

To enable AI answers, set `extra.assistant_endpoint` in `mkdocs.yml` to an HTTPS
endpoint you operate. The panel sends a JSON `POST` containing `question`, `page`
(the current URL) and `history` (up to six recent messages, each with `role` and
`content`). The endpoint returns:

```json
{
  "answer": "An answer grounded in the Kionga documentation.",
  "sources": [{"title": "Install Kionga", "url": "getting-started/installation/"}]
}
```

Source URLs resolve relative to the product documentation root. Only links within
that root are displayed. Answers render as plain text, not HTML or Markdown.
The service must retrieve the documentation, keep provider credentials on the
server, apply rate and request-size limits, and allow the site's origin through
CORS (including the JSON POST preflight). Use public documentation as context;
do not connect the public widget to a privileged Kionga control-plane endpoint.
No API key belongs in this static site. Conversation history stays in memory and
resets on a full reload. Requests time out after 30 seconds; service errors fall
back to documentation search. The site does not include or provision this service.

The documentation interface is implemented in React under `ui/src/`. Run
`make docs-ui` to build the navigation and assistant bundle before serving the
site directly with MkDocs. `make docs-build` and `make docs-serve` build the interface automatically. Public settings
are written into the generated site by `scripts/site_hooks.py`. Presentation
lives in `docs/stylesheets/kionga.css`; the private handbook maintains its own build and assets.

## Versions and changelog

The [release notes page](https://kiongahq.github.io/docs/changelog/) combines published component and documentation releases in one timeline.
The header link beside GitHub opens this page; legacy release URLs redirect here. Release Please proposes semantic version bumps
from conventional commits and creates a tag and GitHub release when the release
pull request is merged. The header displays `version.txt`, or **Development**
before the first release. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and
release checks. Documentation versions are independent of component versions.
