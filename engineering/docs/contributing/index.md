---
description: How to contribute to Kionga, from setting up the workspace and running each repository's tests to the CI gates and commit conventions.
---

# Contributing

Kionga is developed in separate repositories in the
[kiongahq](https://github.com/kiongahq) organization
([decision 0010](../decisions/0010-repository-per-component.md)). This page shows how to
set up a workspace, run the tests of the repository you change, and pass CI. The
documentation standard has [its own page](documentation.md).

## Set up the workspace

Every repository lives side by side in one folder, the layout the Compose stack builds
from:

```text
kionga/
  deploy/  platform/  contracts/  sdk-python/  agent-runtime/
  pipeline-runner/  serving/  trace-proxy/  workspace/  docs/
```

1. Clone `deploy` into an empty folder, then clone the rest beside it:

    ```bash
    mkdir kionga && cd kionga
    git clone git@github.com:kiongahq/deploy.git
    make -C deploy workspace
    ```

    `deploy/scripts/workspace.sh` clones each missing repository (with submodules, so
    `platform/contracts` is populated). `KIONGA_SRC` overrides the target folder and
    `KIONGA_GIT_BASE` the clone URL prefix (SSH by default). Later,
    `make -C deploy workspace-pull` fast-forwards every clean checkout.

2. Start the stack from your checkouts:

    ```bash
    make -C deploy local-up
    make -C deploy smoke
    ```

    `local-up` rebuilds only the images whose sources changed, including a change in a
    repository another image depends on (the SDK, for example).

Paths in this handbook are relative to that folder.

## Run the tests

Run the gate tests of every repository you change before you push.

| Repository | Gate tests |
| --- | --- |
| `platform` | `make -C platform verify` (gofmt, `go vet`, race tests, build, console syntax check, architecture-exclusion scan); `make -C platform test-ui`; `make -C platform test-integration` (PostgreSQL in a throwaway container, needs Docker); `make -C platform test-security` (the CI scanners) |
| `serving`, `trace-proxy` | `make -C serving verify`, `make -C trace-proxy verify` (gofmt, vet, race tests, build) |
| `sdk-python` | `pip install -e ".[dev]"`, then `python -m pytest -q` and `ruff check .` |
| `agent-runtime`, `pipeline-runner`, `workspace`, `contracts` | `pip install -r requirements-dev.txt`, then `python -m pytest -q` and `ruff check .` |
| `deploy` | `make -C deploy test` (Compose wiring, cross-repository contracts, Helm chart, VM installer); `helm lint helm/kionga --strict` |
| `docs` | See the [documentation standard](documentation.md#checks) |

Optional lanes against a running system: `make -C platform test-browser` (Playwright),
`make -C deploy test-load` (k6), `make -C deploy test-stress`, and
`make -C deploy test-e2e-kind` after `make -C deploy kind-up`.

Gate tests are deterministic and network-free: the mock LLM backend and the hashing
embedding function stand in for providers. The paid evaluation lane in `agent-runtime` runs only
with `MLAIOPS_RUN_EVALS=1` and a real provider key.

## CI gates

Each repository's workflow calls the reusable workflows in `kiongahq/.github`.

| Workflow | Steps |
| --- | --- |
| `go.yml` | gofmt, `go vet`, `go test -race`, `go build`, then `govulncheck` v1.8.0 (fails on any reachable vulnerability), `gosec` v2.29.0 (medium severity and confidence and above), `gitleaks` v8.30.1 over the full history |
| `python.yml` | Install, `ruff check .`, `python -m pytest -q`, then pip-audit 2.10.1 on installed dependencies, bandit 1.9.4 (`-ll`, tests excluded), `gitleaks` over the full history |
| `image.yml` | Build; on `main` and `v*` tags publish `ghcr.io/kiongahq/<image>` tagged `sha-<short>`, `latest` and semantic version, with provenance and an SBOM |

The platform runs its own workflow with the same security tools, the PostgreSQL
integration suite, the console tests and the architecture-exclusion scan. The `deploy`
CI clones every component's `main` branch and runs the cross-repository tests; its
Pressure workflow (nightly and on `main`) boots the stack and runs the smoke, stress and
k6 load tests.

A reviewed false positive is annotated where it occurs, with the reason:
`// #nosec G704 -- host is operator config` in Go, and in Python a comment with the
reason above a line that ends in `# nosec B104`. Fake credentials in tests go in the
repository's `.gitleaksignore` by fingerprint, so a new finding still fails.

## Changes across repositories

1. Land the provider side first (usually `platform`), keeping the old behavior working.
2. Release it, then update and release the consumer (for example `sdk-python`).
3. Bump the pins that reference it: `SDK_VERSION` in `agent-runtime` and `workspace`,
   image digests in `deploy`.

A contract change bumps the schema version in `contracts` and is called out in every
pull request it touches.

## Commit conventions

Use [Conventional Commits](https://www.conventionalcommits.org/): a type, an optional
scope, and an imperative summary, for example `feat(auth): sign up on first single
sign-on` or `fix(security): bind local-mode ports to loopback by default`. Types in use
are `feat`, `fix`, `docs`, `test`, `ci`, `chore`, `build`, `perf` and `refactor`.

- Explain the problem and the change in the body when it is not obvious, and name the
  test that proves it.
- Never commit secrets, generated sites, binaries or local tool state.
- Never skip hooks or force-push to `main`.
- Ship tests with the change, and update the handbook and the product documentation in
  the same pull-request cycle when behavior changes.
