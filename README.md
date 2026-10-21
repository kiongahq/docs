# Kionga documentation

Source for the [Kionga documentation](https://kiongahq.github.io/docs/), built with
MkDocs Material and published from `main`. Kionga's repositories use the
[MIT License](LICENCE); third-party components keep their own licenses.

The site is organized by reader task:

| Section | Purpose |
| --- | --- |
| Getting started | Install a private local stack and complete the first workflow |
| Understand | Concepts, architecture, repositories, and technology choices |
| Build | Task-based guides for projects, ML/data, agents, and collaboration |
| Reference | Exact APIs, configuration, RBAC, service and code contracts |
| Operations | Deployment choices, acceptance, recovery, and troubleshooting |

The [implementation-status page](docs/reference/implementation-status.md) separates
bundled code, optional integrations, and features that still need live-environment
validation. Do not describe a capability as production-ready based only on a local
build or mock-backed test.

```bash
make docs-install
make docs-serve      # http://127.0.0.1:8000, live reload
make docs-build      # strict: broken links and nav errors fail the build
make docs-check      # references checked against the sibling checkouts
make docs-test       # gate tests for the reference checker (needs pytest)
```

`make docs-check` runs `scripts/check_references.py`. It reads every page and
verifies `make` targets, paths into other repositories, environment variable
names, REST routes, CLI commands, and Python SDK names against the code in the
sibling checkouts (`KIONGA_SRC=..` by default). Known false positives go in
`scripts/reference-allowlist.txt` with a comment saying why; when a reference is
wrong, fix the page instead.

Paths and commands in the docs are relative to a workspace folder holding every
Kionga repository (see [Repositories](docs/overview/repositories.md)). When a change
in another repository changes behaviour, update the matching page here in the same
pull-request cycle. Follow [CONTRIBUTING.md](CONTRIBUTING.md) for page structure,
terminology, and verification.
