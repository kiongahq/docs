# Core concepts

The vocabulary you'll see throughout the console, the API, and this documentation.

## Control plane vs data plane

- The **control plane** is the Go gateway: it owns *state and orchestration*
  (projects, runs, models, agents, connections, audit) and drives downstream
  engines.
- The **data plane** is the set of stores that hold *durable data and events*:
  Postgres, Redis, Kafka, RustFS, and MLflow.

## Resources

These are the first-class objects the control plane manages. Each has list/create
endpoints and appears in the console.

| Resource | What it is |
| --- | --- |
| **Project template** | An immutable versioned contract describing supported frameworks, accelerators, capabilities, required services, recommended resource profile, and generator behavior. |
| **Project** | An ownership and isolation boundary with a namespace, pinned template/version, framework, accelerator intent, resource profile, capabilities, scaffold command, and optional credential-free Git repository reference. Workloads and assets belong to a project. |
| **User access profile** | An immutable identity subject plus role, services, projects, buckets, suspension state, and compute/storage/run/function quotas. |
| **Access request** | A user's request for selected services and a reason, resolved through the administrator approval queue and audit log. |
| **Workspace** | Jupyter and/or IDE development surface. Compose provides a shared volume; Kubernetes reconciles per-user `KiongaWorkspace` pods, PVCs, services, and credentials. |
| **Pipeline run** | One execution of a pipeline through the engine. Has a status, a progress percentage, an ordered set of **steps** (a DAG), and logs. |
| **Pipeline definition** | A reusable, versioned container/function DAG with dependencies, resources, retries, parameters, repository, and commit lineage. The backend validates the graph; Dagre only lays it out for the console. |
| **Model** | A registered model version with metrics, a **quality gate** status, a **stage** (candidate/production), and — once deployed — a live **endpoint URL** and deployment status. |
| **Agent** | A deployed LangGraph application: project, image, graph module, LLM backend, tool list, per-replica CPU/memory/GPU, min/max replicas, canary weight, and status. Produces sessions and traces; Kubernetes can reconcile an HPA when the range is elastic. |
| **Agent session** | One conversation/thread with an agent: turns, current node, token usage, and cost. |
| **Tool** | A registered capability an agent can call (name, description, schema). |
| **Feature view** | A named group of features for an entity, with a schema, TTL, and online materialization status. |
| **Connection** | A registered external service (MLflow, RustFS or S3, Kafka REST, Langfuse, Prefect, OpenFaaS, Redis/Feast, Kubernetes) that the control plane actively health-checks. Stores only a credential *reference* (`none` or `env:VARIABLE`), never raw credentials. |
| **Audit event** | An immutable record of a mutation — who did what, when. |
| **Function** | A project-owned OCI workload with CPU/memory limits and HTTP, async, Cron, or Kafka trigger metadata; deployed and invoked through OpenFaaS when configured. |

## Connections and health

A **connection** registers an external service so the gateway can verify it is
reachable. The check runs **from inside the gateway container**, so connection
endpoints use in-stack hostnames (`http://mlflow:5000/health`). Only a `2xx`
response counts as healthy; redirects, missing routes, and authentication
failures are reported as failures. Prefect and OpenFaaS connections can also be
activated to receive new operations.

**Onboarding readiness** (the ring on Overview and the checklist on Platform) is
derived from connections plus having at least one project. See
[Connecting services](../connecting-services.md).

## The quality gate and promotion

A model has a **gate status** (`passed` / `pending`). Promotion moves a model
between **stages** (typically `candidate` → `production`). Deployment starts a live
serving container; **canary weight** controls traffic splitting; **rollback**
removes the serving container and reverts. A deployed model answers live
predictions from the model card's **Test** dialog.

## Agents, sessions, and tracing

An **agent** is a LangGraph graph served by the runtime. Compose shares one runtime;
Kubernetes creates an immutable-ID-derived Service per agent. Live health, not the
persisted deploy record, determines whether Chat/invocation is enabled. The runtime
maintains a **session** (state checkpointed in Postgres, keyed per agent) and records
**turns**. LLM calls from the `openai` and `openai-compatible` backends egress
through the **trace proxy**, which captures them to Kafka; **Langfuse** provides
the observability UI. Token counts come from the model's
usage metadata (measured, never estimated); **cost** is computed from configured
per-1k rates.

## The feature store: online vs offline

- **Online** features are served from **Redis** through the feature-gateway for
  low-latency reads (real-time scoring).
- **Offline** features are materialized as **Parquet snapshots** in the object store for batch
  use.

The **feature-materializer** applies feature definitions and populates the online
store, reporting entity counts back to the control plane.

## Real-time processing

The **realtime-processor** is a Kafka consumer service that demonstrates three
patterns: **fraud detection**, **call-center analysis**, and **personalized
recommendations**. Each reads an input topic, enriches the event with online
features, scores it with a model or agent, and publishes to an output topic. The
console's Real-Time panel shows live throughput, latency, and recent scored events.

## Serverless

**Serverless** deployment uses **OpenFaaS / faasd**. Kionga owns the project/function
contract, quotas, trigger configuration, invocations, audit, UI, and function-DAG
composition. The execution gateway is external to the default Compose stack and
the capability remains **not configured** until `OPENFAAS_URL` is set.

!!! info "Serverless with OpenFaaS"
    Use faasd for a single node or OpenFaaS on Kubernetes at scale. Trigger
    connectors and their operational/licensing terms are selected by the operator.

## Trace-proxy egress

Compose points the agent runtime's OpenAI-protocol LLM calls at the
**trace proxy** (`MLAIOPS_LLM_BASE_URL=http://trace-proxy:8081/v1`). The proxy
forwards to the configured upstream provider (`LLM_UPSTREAM_URL`) and publishes
every call to the `mlaiops.llm.traces` Kafka topic, without changes to agent code.
Provider API keys never appear in traces, logs, or the control-plane store. The
`anthropic` backend calls Anthropic directly and is not captured by the proxy.

## Roles (RBAC)

Every API request is authorized against a **role**: `admin`/`operator` (full
control and user provisioning), `user` (only assigned services, projects and
quotas), `engineer` (legacy ML lifecycle role, not platform connections), `viewer`
(read-only), and `service` (internal reporting only, via the internal token). See
[RBAC & security](../reference/rbac.md).
