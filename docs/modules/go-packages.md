# Go packages

The Go module is `github.com/kiongahq/platform` (Go 1.26, toolchain 1.26.10).
Direct dependencies include `github.com/jackc/pgx/v5` (PostgreSQL),
`github.com/golang-jwt/jwt/v5` (OIDC tokens), `golang.org/x/oauth2`,
`github.com/redis/go-redis/v9`, `github.com/robfig/cron/v3` (schedules),
`github.com/microcosm-cc/bluemonday` (blog HTML sanitizing),
`github.com/prometheus/client_golang`, and the Kubernetes client and
controller-runtime libraries for the scale path. Commands live under
`platform/go/cmd/`, reusable logic under `platform/go/internal/`, and public API
types under `platform/go/pkg/`.

The serving manager (`serving`) and the trace proxy (`trace-proxy`) are separate
Go modules in their own repositories; they are described at the end of this page.

## Commands (`platform/go/cmd`)

Each builds to a `mlaiops-<name>` binary in `platform/bin/` (`make -C platform build`)
and to a container image via `platform/go/Dockerfile` (`--build-arg SERVICE=<name>`).

| Command | Binary | Role |
| --- | --- | --- |
| `gateway` | `mlaiops-gateway` | REST API + embedded console |
| `operator` | `mlaiops-operator` | Kubernetes reconcilers (scale path) |
| `integration-worker` | `mlaiops-integration-worker` | Kafka → CRD lifecycle worker (scale path) |
| `feature-gateway` | `mlaiops-feature-gateway` | Online feature retrieval |
| `storage-proxy` | `mlaiops-storage-proxy` | SigV4 S3 URLs + browse |
| `metrics-collector` | `mlaiops-metrics-collector` | Prometheus platform metrics |
| `log-exporter` | `mlaiops-log-exporter` | Log export to Elasticsearch or OpenSearch |
| `cli` | `mlaiops-cli` | Operator/engineer CLI (`mlaiops`) |

## Internal packages (`platform/go/internal`)

### `auth`

Authentication and authorization. OIDC/JWKS verification (`Verifier`), the RBAC
model (`Allowed` and the role constants), the sign-in `Authenticator`, local and
single sign-on browser sessions (with per-account throttling of local sign-in),
personal-key verification (`APITokenMiddleware`), and the `RBAC` middleware that
runs on every request. Roles: `admin`, `operator`, `user`, `engineer`, `viewer`,
`service`. See [RBAC & security](../reference/rbac.md).

### `httpapi`

The gateway's HTTP layer on the standard library `net/http` ServeMux. `server.go`
creates the router, registers the core routes, and holds the JSON helpers
(`writeJSON`, `writeMutation`, `decode`) and the security-header and CORS
middleware. Domain files (`pipeline_definitions.go`, `iam.go`, `editorial.go`,
`feature_stores.go`, `scaffold_jobs.go`, `logs.go`, ...) add their own routes
through `registerRoutes` in `routes.go` and document them for `openapi.go`, which
serves `/api/openapi.json`.

`GET /api/v1/project-templates` exposes the same versioned project contract used by
the Python SDK and workspace generator. Project creation returns the resolved
framework, accelerator, profile, capabilities, template version, and scaffold
command.

### `policy`

The IAM evaluator (`policy.go`) and the managed role baselines (`baseline.go`):
actions, `kionga:` resource patterns, conditions, explicit-deny precedence. See
[Access control](../guides/access-control.md).

### `pipelinespec`, `execution`, `scheduler`, `k8sexec`

`pipelinespec` parses and validates `kionga.dev/v1 Pipeline` YAML; `execution`
holds the ready-set scheduling shared by the executors; `scheduler` fires cron
triggers under a database lease; `k8sexec` runs container nodes as Kubernetes
Jobs (opt-in).

### `editorial`

Engineering blog blocks, server rendering and sanitizing, revisions and diffs,
workflow transitions, media processing and storage, and the one-time Markdown
migration.

### `logexport`, `redact`, `runtimeconfig`

`logexport` implements the Elasticsearch and OpenSearch adapters behind
`log-exporter`; `redact` removes secrets from logs before storage;
`runtimeconfig` loads `KIONGA_CONFIG_FILE`, the supported `NAME_FILE` secret
files, and the production startup checks.

### `store`

Persistence. `repository.go` is the interface contract; `store.go` is the local
file implementation; `postgres.go` is the PostgreSQL implementation with the
transactional **outbox** (`outbox.go`): every mutation writes resource + audit +
outbox atomically. Handles user grants/access requests, personal-key digests, Git
metadata, functions and DAG definitions, run steps, agent sessions, model endpoints,
blog posts, and feature views.

### `integrations`

HTTP clients for external systems: MLflow, KFP, Langfuse, Prefect (`client.go`),
the Kafka REST producer/consumer (`kafka_consumer.go`), and OpenFaaS. `dispatcher.go`
routes durable commands and derives collision-safe agent resource names from the
immutable control-plane ID. `lifecycle_worker.go` is the at-least-once boundary: it
retries record dispatch, commits Kafka offsets manually only after the complete
batch succeeds, retries commit without redispatch, and returns a terminal error so
the process restarts from the last commit when retries are exhausted. `NewPrefect`
normalizes the API base URL so paths don't double-prefix `/api`.

### `storage`

Object-store access. `presign.go` builds AWS SigV4 URLs (with a verified,
signature-correct path); `browse.go` lists buckets/objects and previews objects.
Backs the storage-proxy command.

### `feature`

Online feature retrieval and store adapters. `adapter.go` and `adapters.go`
(the `feature.Adapter` contract and registry), `redis.go` (online store),
`feast.go` (Feast feature-server client), `service.go` (HTTP handlers). Backs the
feature-gateway command.

### `metrics`

`collector.go` (component health scraping) and `platform.go` (`PlatformCollector`,
the platform metric set: pipeline outcomes, agent usage, real-time stats).
Prometheus exposition. Backs the metrics-collector command.

### `operator`

Kubernetes controllers for the scale path: `agent_controller.go`,
`lifecycle_controllers.go`, workspace reconciliation, and deterministic plans
(`reconciler.go`) for the Kionga CRDs. Agent reconciliation applies Kubernetes
resource requirements and probes to the immutable-ID-derived Deployment/Service,
owns a 70%-CPU HorizontalPodAutoscaler when maximum replicas exceed minimum
replicas without fighting its replica writes, and derives CR readiness from
available pods. Operator RBAC includes the autoscaling resource; a resource-metrics
API is required for elastic scaling.

### `platform`

Live derivation of the component-health grid (`Components`) and the shared
**catalog** (`Catalog`) from real connections, models, features, agents, and tools
(`catalog.go`), with no hardcoded data.

## Public API types (`platform/go/pkg`)

| Package | Contents |
| --- | --- |
| `pkg/api` | Request/response types shared by the gateway, CLI, and clients (`ProjectTemplate`, `Project`, `PipelineRun`, `Model`, `Agent`, `Connection`, request bodies, `Page[T]`, `APIError`); `project_templates.go` owns versioned template resolution and framework/accelerator/profile validation |
| `pkg/kube/v1alpha1` | Typed Kubernetes CRD definitions (scale path) |

## Separate Go repositories

| Repository | Package | Role |
| --- | --- | --- |
| `serving` | `serving/internal/serving` (`manager.go`) | Model serving over the Docker Engine API. `Manager.Deploy` replaces, creates, and starts a container with labels and restart policy, chooses the model's `serving_image` or the configured fallback, and applies capability, privilege-escalation, and PID hardening. Supports an API-version override (`DOCKER_API_VERSION`). Command: `serving/cmd/serving-manager` |
| `trace-proxy` | `trace-proxy/internal/traceproxy` (`proxy.go`) | The OpenAI-compatible reverse proxy that forwards LLM calls upstream and asynchronously publishes each call to the Kafka traces topic. Command: `trace-proxy/cmd/trace-proxy` |

Both build with `make -C <repo> build` and test with `make -C <repo> verify`.

## Testing

Packages have table-driven `_test.go` files. The platform CI runs `gofmt -l`
(must be empty), `go vet`, `go test -race`, the tagged integration suite against a
real PostgreSQL, `go build ./cmd/...`, the banned-tech scan, `govulncheck`, and
the console UI tests. Run locally with `make -C platform test-go`,
`make -C platform test-integration`, and `make -C platform test-ui`.
