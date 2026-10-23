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
