---
description: The Go control-plane services from the platform repository, gateway, operator, integration worker, metrics collector and CLI, plus the Dex broker.
---

# Gateway and control-plane services

Each service below uses the same shape: responsibility, interfaces, dependencies,
configuration, code map and tests. Paths are relative to the workspace folder that
holds every Kionga repository.

## gateway

### Responsibility

The single Go binary that serves the REST API and the embedded web console, and
orchestrates every downstream engine. It:

- **owns state** for the versioned project-template catalog, Git-native projects,
  pipeline runs and definitions, functions, models, agents, tools, connections, feature
  views, user access, access requests, personal API keys, engineering posts, and
  immutable audit events;
- **writes in one transaction**: every mutation persists its resource, an audit record
  and Kafka outbox entries in one transaction (PostgreSQL mode,
  [decision 0005](../decisions/0005-postgresql-kafka-outbox.md));
- **orchestrates and proxies**: Prefect (pipelines), the serving manager (endpoints),
  the agent runtime (agent turns), the storage proxy (browse), the feature gateway
  (lookups), Langfuse (prompts), OpenFaaS (functions);
- **fails closed**: if a downstream engine rejects a request, the control plane records
  the failure (a run is marked failed, a deploy returns `502`);
- **validates project intent**: normalizes template aliases, pins the template
  version, rejects incompatible framework and accelerator selections, and records a
  resource-aware scaffold command without granting capacity;
- **validates execution graphs**: rejects duplicate or missing dependencies, cycles,
  invalid job resources and unresolved function references before persistence;
  browser layout never changes execution semantics;
- **admits agent workloads**: validates replica bounds and strict Kubernetes GPU
  extended-resource names; for normal users, every owned agent's maximum-replica CPU,
  memory and GPU plus per-pod trace-sidecar overhead must fit the aggregate grant;
- **routes live agents**: derives the Kubernetes Service from the immutable agent ID and
  `MLAIOPS_AGENT_NAMESPACE` (or uses the Compose `AGENT_RUNTIME_URL`), enriches list
  results with bounded health probes, and rejects invocation with
  `503 agent_not_ready` before forwarding to an unhealthy runtime;
- **authenticates and authorizes**: sign-in through single sign-on or local accounts,
  personal API keys, the internal service token; RBAC on every request in every mode;
  IAM policy decisions for covered actions
  ([security](../architecture/08-crosscutting-concepts.md#security-and-identity));
- **hardens responses**: `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: strict-origin-when-cross-origin`, and `X-Frame-Options: SAMEORIGIN`
  on every response except forwarded `/workspaces/` paths;
- **streams live updates**: `GET /api/v1/events` sends a per-caller state digest over
  SSE;
- **runs singletons under leases**: the pipeline scheduler, log retention and the
  editorial publisher;
- **publishes engineering writing**: block-content posts written in the editorial
  workspace (`/editorial.html`), public index and article pages
  ([decision 0002](../decisions/0002-blog-editor.md)).

### Interfaces

| Interface | Detail |
| --- | --- |
| HTTP `:8080` (`PORT`) | REST API under `/api/v1`, sign-in under `/auth/`, workspace proxy under `/workspaces/`, the console and public pages; host port `GATEWAY_PORT` bound to `KIONGA_BIND_ADDRESS` in Compose |
| Health | `GET /api/v1/health` (health), `GET /api/v1/ready` (readiness) |
| API description | `GET /api/openapi.json`, rendered at `/api-docs.html` |
| Metrics | Optional listener on `METRICS_PORT` |
| Workspace identity listener `:8087` | Cluster-internal; accepts only verified workspace identities; started when `KIONGA_WORKSPACE_NAMESPACE` or `KIONGA_WORKSPACE_API_TOKEN` is set |
| Outbound | PostgreSQL, Kafka REST, Prefect, serving manager, agent runtime, storage proxy, feature gateway, Langfuse, OpenFaaS, the OIDC issuer, the Kubernetes API (workspaces, opt-in Job executor) |

The full route list is in the [REST API reference](https://kiongahq.github.io/docs/reference/api/).

### Dependencies

PostgreSQL (or a local JSON file without `DATABASE_URL`), Kafka REST for the outbox,
an OIDC issuer for single sign-on. Every engine is optional at startup; an
not configured engine reports `configured: false`.

### Configuration

The essentials: `DATABASE_URL`, `KAFKA_REST_URL`, `PREFECT_API_URL`,
`SERVING_MANAGER_URL`, `AGENT_RUNTIME_URL` (Compose) or `MLAIOPS_AGENT_NAMESPACE`
(Kubernetes), `STORAGE_PROXY_URL`, `LANGFUSE_*`, `MLAIOPS_LOCAL_ROLE`,
`MLAIOPS_INTERNAL_TOKEN`, `OIDC_*`, `KIONGA_SSO_*`, `KIONGA_SIGNUP`,
`KIONGA_CREDENTIAL_KEY`, `MLAIOPS_ALLOWED_ORIGIN`, and `KIONGA_ENVIRONMENT=production`
for the startup checks. See the
[configuration reference](https://kiongahq.github.io/docs/reference/configuration/) and
[configuration and secrets](../architecture/08-crosscutting-concepts.md#configuration-and-secrets).

### Code map

| Path | Contents |
| --- | --- |
| `platform/go/cmd/gateway/main.go` | Wiring: config, repository, listeners, sign-in, middleware order |
| `platform/go/cmd/gateway/web/` | Embedded console and public pages (see below) |
| `platform/go/internal/httpapi` | Routes, handlers, middleware, OpenAPI, SSE |
| `platform/go/internal/auth`, `platform/go/internal/policy` | Identity, RBAC, IAM evaluator |
| `platform/go/internal/store` | Repositories, migrations, outbox worker |
| `platform/go/internal/scheduler`, `platform/go/internal/editorial` | Leased scheduler; blog |

The [Go packages](go-packages.md) page describes every package.

#### The embedded console

`platform/go/cmd/gateway/web/` holds the landing page (`index.html`, `landing.css`,
`landing.js`), the console (`console.html`, `styles.css`, and scripts under `js/`),
the login, workspace, blog, editorial and API-docs pages, and vendored libraries under
`vendor/`. It is embedded into the binary with `go:embed` and has no build step. It
renders role-aware views for the workload lifecycle, functions, workspaces, access
administration, settings and tokens, storage, the catalog and platform connections,
and drives them from the same API the SDK uses.

The pipeline view uses pinned open-source Dagre for node placement
([decision 0001](../decisions/0001-dag-layout-library.md)). The validated API graph
stays authoritative, and a compact fallback keeps step state and logs readable if the
layout asset is unavailable. `pipeline-graph.js` exposes a small, independently tested
analyzer and renderer, surfaces authoring errors, and emits keyboard-focusable SVG
nodes with accessible job, target and status labels.

### Tests

- `make -C platform test-go`: unit and handler tests with the race detector.
- `make -C platform test-integration`: the PostgreSQL integration suite in
  `platform/go/integration`, against a throwaway pgvector container.
- `make -C platform test-ui`: console tests in `platform/tests/ui` (Node.js test
  runner and `jsdom`).
- `make -C platform test-browser`: Playwright acceptance in `platform/tests/e2e`
  against a running stack.

## `dex`

### Responsibility

OIDC broker for single sign-on ([decision 0006](../decisions/0006-oidc-single-sign-on-dex.md)).
It translates LDAP or Active Directory, SAML, GitHub, Google, Microsoft, GitLab and
OIDC logins into ID tokens for the gateway. Not Kionga code: the upstream image,
configured by the `deploy` repository.

### Interfaces

Issuer at `http://localhost:5556/dex` locally (`DEX_ISSUER`, host port `DEX_PORT`); the
gateway exchanges codes and fetches keys in-stack at `http://dex:5556/dex/token` and
`http://dex:5556/dex/keys`.

### Dependencies

GLAuth (`glauth`) as the local test LDAP directory; any upstream identity provider whose
`KIONGA_*_CLIENT_ID` is set.

### Configuration

`deploy/sso/dex.yaml` is a template rendered at startup from the `KIONGA_*` connector
variables; it also writes the list of enabled providers to a volume the gateway reads
(`KIONGA_SSO_PROVIDERS_FILE`). After changing connector settings, run
`make -C deploy sso-reload`.

### Code map and tests

`deploy/sso/`, the `dex` and `glauth` services in `deploy/compose.yaml`;
`deploy/tests/test_sso.py` keeps the gateway and Dex settings in agreement.

## operator

### Responsibility

Kubernetes controller for the scale path: leader-elected reconcilers that turn Kionga
custom resources (`KiongaAgent`, `KiongaPipelineRun`, `KiongaTool`,
`KiongaConnection`, `KiongaModelPromotion`, `KiongaWorkspace`) into workloads.

- **Agents:** uses the immutable-ID-derived name for the Deployment and Service,
  applies CPU, memory and GPU requirements and health probes, and reports Ready only
  after the minimum replicas are available. It creates an owned 70%-CPU
  HorizontalPodAutoscaler when the maximum exceeds the minimum and does not reset
  replicas the autoscaler owns; clusters must provide resource metrics, for example
  metrics-server.
- **Workspaces:** one Deployment with Jupyter and the IDE sharing a PVC, a Service and a
  credentials Secret per grant; scaled to zero when the grant is suspended
  ([decision 0007](../decisions/0007-per-user-workspaces.md)). Storage admission
  rejects `hostPath` and limits StorageClasses.
- **Model promotions:** transitions the MLflow stage, then creates a KServe
  `InferenceService`.
- **Pipeline runs:** submits the run to KFP.

### Interfaces

Kubernetes API; health and readiness on port 8082 in the Helm chart (`/healthz`,
`/readyz`). Not part of the Compose stack.

### Dependencies

The CRDs in `deploy/config/crd/`, RBAC in `deploy/config/rbac/operator.yaml`, MLflow and
KFP for their reconcilers, metrics-server for agent autoscaling.

### Configuration

`MLAIOPS_TARGET_NAMESPACE`, `MLAIOPS_CONTROL_NAMESPACE`, `MLFLOW_URL`, `KFP_URL`,
`KFP_EXPERIMENT_ID`, `WORKBENCH_IMAGE`, `IDE_IMAGE`, `TRACE_PROXY_IMAGE`,
`WORKSPACE_STORAGE_CLASS`, `WORKSPACE_ALLOWED_STORAGE_CLASSES`, the `WORKSPACE_*_URL`
endpoints injected into workspaces, and `KIONGA_IMAGE_PULL_SECRETS`
([decision 0009](../decisions/0009-private-images-and-pull-secrets.md)).

### Code map

`platform/go/cmd/operator`, `platform/go/internal/operator` (`agent_controller.go`,
`workspace_controller.go`, `lifecycle_controllers.go`, `storage_admission.go`,
`reconciler.go`), typed CRDs in `platform/go/pkg/kube/v1alpha1`. Ships as the
`operator` image.

### Tests

Reconciler tests with the controller-runtime fake client in
`platform/go/internal/operator`; `make -C deploy test-e2e-kind` on a kind cluster.

## integration-worker

### Responsibility

Kafka lifecycle worker that translates durable outbox commands into Kionga custom
resources on the Kubernetes path, including access-grant-driven workspace create,
update, suspension and revocation. Its Kafka REST consumer disables auto-commit,
retries a failed record with bounded exponential backoff, and commits offsets only
after the whole poll batch succeeds. Exhausted dispatch or commit retries stop the
worker before another poll, so a restart replays from the last durable commit. This is
at-least-once delivery; ID-keyed create-or-update reconciliation makes replay harmless
([persistence and the outbox](../architecture/08-crosscutting-concepts.md#persistence-and-the-kafka-outbox)).

### Interfaces

Consumes the `mlaiops.*.commands` topics through Kafka REST; writes custom resources
through the Kubernetes API; health on port 8086 (`/healthz`, `/readyz`).

### Configuration

`KAFKA_REST_URL`, `KAFKA_REST_TOKEN`, `MLAIOPS_TARGET_NAMESPACE`.

### Code map

`platform/go/cmd/integration-worker`; `platform/go/internal/integrations`
(`lifecycle_worker.go`, `kafka_consumer.go`, `dispatcher.go`). Deployed by the Helm
chart and `deploy/config/deploy/integration-worker.yaml`.

### Tests

`platform/go/internal/integrations/lifecycle_worker_test.go`,
`platform/go/internal/integrations/dispatcher_test.go`,
`platform/go/internal/integrations/kafka_consumer_test.go`.

## metrics-collector

### Responsibility

Prometheus exposition of platform metrics: pipeline outcomes, agent usage, real-time
statistics and component health, read from the gateway.

### Interfaces

HTTP on port 9090 (`PORT`). Deployed by `deploy/config/deploy/platform-services.yaml`
(the kind environment); not part of the Compose stack or the Helm chart.

### Configuration

`MLAIOPS_URL`, `MLAIOPS_TOKEN`, `MLAIOPS_METRICS_TARGETS` (components to scrape).

### Code map and tests

`platform/go/cmd/metrics-collector`; `platform/go/internal/metrics` (`collector.go`,
`platform.go`) with their tests.

## log-exporter

Optional exporter of structured logs to Elasticsearch or OpenSearch, with an
at-least-once cursor, partial-failure retry and dead-letter counts. Compose profile
`log-export`; configured with `KIONGA_LOG_EXPORT_*`, credentials as files. Code:
`platform/go/cmd/log-exporter`, `platform/go/internal/logexport`. Tested against
protocol fakes only. See [log export](https://kiongahq.github.io/docs/operations/log-export/).

## `cli`

Single-binary operator and engineer CLI (`mlaiops`), built from
`platform/go/cmd/cli`. It reads `MLAIOPS_URL` and `MLAIOPS_TOKEN` and includes pipeline
export, validate and apply for Git-reviewed definitions. See the
[CLI reference](https://kiongahq.github.io/docs/reference/cli/).
