# Kionga documentation

Source for Kionga's two documentation sites, built with
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/) and published from
`main` to GitHub Pages.

| Site | Source | Published at | For |
| --- | --- | --- | --- |
| Product documentation | `docs/`, `mkdocs.yml` | <https://kiongahq.github.io/docs/> | People who install, use, administer and operate Kionga |
| Engineering handbook | `engineering/docs/`, `engineering/mkdocs.yml` | <https://kiongahq.github.io/docs/engineering/> | People who change Kionga's code |

Kionga is a self-hosted, open-source platform for machine learning, data and AI
agents. Its repositories use the [MIT License](LICENCE); third-party components keep
their own licenses.

## Build and check

```bash
make docs-install            # MkDocs and plugins from requirements-docs.txt
make docs-serve              # product site, http://127.0.0.1:8000
make docs-serve-engineering  # handbook, http://127.0.0.1:8001
make docs-build              # strict build of both sites
make docs-lint               # Vale, Google developer documentation style
make docs-check              # references checked against the sibling checkouts
make docs-test               # reference checker and legacy URL tests (pytest)
```

`make docs-check` reads the code in the sibling repositories (`KIONGA_SRC=..` by
default). Clone them beside this one with `make -C ../deploy workspace`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The full standard is the handbook's
[documentation standard](https://kiongahq.github.io/docs/engineering/contributing/documentation/).

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

The theme override lives in `overrides/main.html`; presentation and interaction
live in `docs/stylesheets/kionga.css` and `docs/javascripts/assistant.js`.
The engineering handbook shares the stylesheet; keep both copies identical.
