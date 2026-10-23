---
description: arc42 section 4. The key decisions behind Kionga's design and how each one serves the quality goals.
---

# 4. Solution strategy

Kionga's design follows from a small number of decisions. Each row links the
approach to the [quality goals](01-introduction-and-goals.md#quality-goals) it serves
and to the record or code that establishes it.

## Key decisions

| Decision | Approach | Serves | Evidence |
| --- | --- | --- | --- |
| A control plane, not an engine | The gateway validates intent, authorizes, persists desired state and audit, then delegates execution to Prefect, MLflow, OpenFaaS, KFP, KServe, LangGraph and Langfuse. It records what those engines report instead of predicting it. | Truthful state, openness | `platform/go/internal/httpapi`, `platform/go/internal/integrations` |
| Go for the control plane, Python for ML-facing code | Static binaries on `distroless` images for long-running services; Python where the ML and agent ecosystems are | Operability, openness | [Decision 0004](../decisions/0004-go-control-plane-python-ml.md) |
| PostgreSQL as the system of record, Kafka through a transactional outbox | A mutation writes its resource, an audit event and outbox rows in one transaction; a background worker publishes the outbox to Kafka | Truthful state | [Decision 0005](../decisions/0005-postgresql-kafka-outbox.md) |
| Single sign-on through an OIDC broker | The gateway speaks one protocol (OIDC); Dex translates LDAP, SAML and social logins locally; production can point at any OIDC issuer | Security, openness | [Decision 0006](../decisions/0006-oidc-single-sign-on-dex.md) |
| Authorization in one place | RBAC middleware on every API request, then IAM-style policy evaluation in handlers; the console renders permissions derived from the same function the API enforces | Security | [Authorization](08-crosscutting-concepts.md#authorization-rbac-and-iam-policies) |
| One contract, two runtimes | Compose-native engines locally, Kubernetes-native engines at scale, behind the same REST API and resource model | Operability, portability | Table below |
| Per-user isolation only where it is real | A shared workbench in Compose; per-user workspaces reconciled from access grants on Kubernetes | Security | [Decision 0007](../decisions/0007-per-user-workspaces.md) |
| Fail closed, report honestly | Production refuses unsafe configuration at startup; an engine rejection marks the run or model failed; an unready agent returns `503` before any work is forwarded | Security, truthful state | [Error handling](08-crosscutting-concepts.md#error-handling-and-fail-closed-behavior) |
| Pin everything that ships | Images by digest on servers and clusters; ML libraries pinned identically in trainer, notebook and serving images | Reproducibility | [Technology](technology.md) |

## Decomposition

The system splits into four groups. [Section 5](05-building-block-view.md) shows them
as building blocks.

- **Control plane (Go).** The gateway (API, console, identity, authorization, store,
  scheduler, pipeline validation), and on Kubernetes the operator and integration
  worker.
- **Data plane.** PostgreSQL, Redis, Kafka with its REST proxy, RustFS, MLflow, plus
  two Go services that front storage and features: the storage proxy and the feature
  gateway.
- **Execution and serving.** Prefect and the pipeline runner, the serving manager and
  its model containers, OpenFaaS when configured.
- **AI and observability.** The agent runtime, the trace proxy, Langfuse and the
  real-time processor.

Workloads and the control plane never import each other's code. They meet at the
REST API (with a service token for machine reports), at versioned schemas in the
`contracts` repository, and at container images.

## One contract, two runtimes

| Capability | Compose (single host) | Kubernetes (scale path) |
| --- | --- | --- |
| Pipeline execution | Prefect with the bundled pipeline runner | KFP through `KiongaPipelineRun`, or opt-in Kubernetes Jobs per node |
| Model serving | `mlflow models serve` containers started by the serving manager | KServe `InferenceService` created on promotion |
| Agents | One shared agent runtime, identity passed per request | One Deployment and Service per agent, named from the immutable agent ID |
| Workspaces | Shared Jupyter workbench and optional IDE on one volume | One `KiongaWorkspace` per user grant, with its own PVC and credentials |
| Serverless functions | External OpenFaaS or faasd | External OpenFaaS |
| Edge | Loopback ports locally; Caddy with TLS on a single server | Ingress with TLS; a separate wildcard host for workspaces |

Kionga records the same desired state in both runtimes, so a project, pipeline
definition or model keeps its identity when an installation moves from Compose to
Kubernetes.

## Technology

The full list of runtimes, libraries and images, with versions and the reason each
one is there, is on the [technology](technology.md) page.
