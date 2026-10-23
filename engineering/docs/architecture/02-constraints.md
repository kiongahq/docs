---
description: arc42 section 2. The technical, organizational and convention constraints that Kionga's design works within.
---

# 2. Constraints

Constraints are fixed inputs to the design: a change to one of them is a decision in
its own right and gets a [decision record](../decisions/index.md).

## Technical constraints

| Constraint | Background | Where it is enforced |
| --- | --- | --- |
| Go 1.26 for control-plane services | One toolchain for the gateway, operator, workers, feature gateway, storage proxy, serving manager, trace proxy and CLI | `go 1.26.0` and `toolchain go1.26.10` in `platform/go/go.mod`; `golang:1.26.10-alpine` builder images |
| Python 3.11 or later for ML-facing code | The SDK, agent runtime, pipeline runner and workbench share one interpreter line; the optional NOOA adapter needs a separate Python 3.12 or 3.13 image | `requires-python = ">=3.11"` in `sdk-python/pyproject.toml`; `python:3.11-slim` base images |
| No frontend build step | The console, landing page, login, workspace, blog and editorial pages are plain HTML, CSS and JavaScript embedded in the gateway binary with `go:embed`; libraries are vendored browser builds | `platform/go/cmd/gateway/web/`; [decision 0001](../decisions/0001-dag-layout-library.md) and [decision 0002](../decisions/0002-blog-editor.md) |
| Open-source components only | Kionga bundles and integrates only open-source engines; specific proprietary ML operations products are excluded by name | The platform CI step "Enforce architecture exclusions" fails on a match; `make -C platform verify` runs the same scan |
| Runs on one Docker host | The complete local stack must start from one Compose file, without Kubernetes | `deploy/compose.yaml` |
| Runs on Kubernetes for isolation | Per-user workspaces and distributed team workloads need Kubernetes; the operator and CRDs exist only on that path | `deploy/helm/kionga`, `deploy/config/crd/` |
| PostgreSQL 16 with pgvector | One database engine backs control-plane state, the outbox, MLflow, Langfuse, agent checkpoints and vector memory | `pgvector/pgvector:pg16` in Compose and in the platform CI service container |
| Kafka through an HTTP REST proxy | Python services and the Go workers talk to Kafka over HTTP (Karapace, Confluent v2 compatible), so they need no native Kafka client | `kafka-rest` service in `deploy/compose.yaml`; `KAFKA_REST_URL` |
| Immutable images on servers and clusters | The single-server installer and the Helm chart refuse images that are not pinned by `sha256` digest | `deploy/vm/up.py`; `test_chart_refuses_unpinned_default_images` in `deploy/tests/test_production_deploy.py` |
| Private container registry | Kionga's images on `ghcr.io/kiongahq` are private packages, so every pull needs credentials | [Decision 0009](../decisions/0009-private-images-and-pull-secrets.md) |

## Organizational constraints

| Constraint | Background |
| --- | --- |
| MIT license | Every Kionga repository is MIT licensed; bundled third-party components keep their own licenses, which must be compatible with self-hosting |
| One repository per component | The platform, SDK, runtimes, workspace, contracts, deployment and docs build, test and release independently ([decision 0010](../decisions/0010-repository-per-component.md)) |
| Shared CI and security gates | Every repository calls the reusable workflows in `kiongahq/.github`; they fail on reachable vulnerabilities, medium or higher static-analysis findings, and secrets anywhere in the history ([contributing](../contributing/index.md#ci-gates)) |
| Documentation checked against code | The documentation repository's reference checker resolves commands, paths, environment variables, routes, CLI commands and SDK names against the code ([documentation standard](../contributing/documentation.md)) |

## Conventions

| Convention | Detail |
| --- | --- |
| REST API | Base path `/api/v1`, JSON bodies; unknown request fields are rejected; errors use `{"error": "<code>", "message": "<text>"}` |
| Kubernetes API | Group and version `mlaiops.io/v1alpha1`; kinds `KiongaAgent`, `KiongaPipelineRun`, `KiongaTool`, `KiongaConnection`, `KiongaModelPromotion`, `KiongaWorkspace` |
| Identifiers | Product-facing identifiers use the Kionga vocabulary (`kionga_` cookies, the `kionga` workspace command, `KIONGA_*` variables); the API group, Go module paths and `MLAIOPS_*` configuration keep their earlier names ([identifier migration](../status/identifier-migration.md)) |
| Secrets | Never in Helm values, the non-secret config file, or command lines; supplied as environment variables locally and as `<NAME>_FILE` paths on servers and clusters ([configuration and secrets](08-crosscutting-concepts.md#configuration-and-secrets)) |
| Commits | Conventional commit messages, for example `feat(auth): ...` or `fix(security): ...` ([contributing](../contributing/index.md#commit-conventions)) |
