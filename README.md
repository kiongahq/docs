# docs

Source of the [Kionga documentation](https://kiongahq.github.io/docs/): architecture,
installation, guides, API and operations. Built with MkDocs Material and published
to GitHub Pages from `main`.

The [implementation-status page](docs/reference/implementation-status.md) separates
bundled code, optional integrations, and features that still need live-environment
validation. Do not describe a capability as production-ready based only on a local
build or mock-backed test.

```bash
make docs-install
make docs-serve      # http://127.0.0.1:8000, live reload
make docs-build      # strict: broken links and nav errors fail the build
```

Paths and commands in the docs are relative to a workspace folder holding every
Kionga repository (see [Repositories](docs/overview/repositories.md)). When a change
in another repository changes behaviour, update the matching page here in the same
pull-request cycle.
