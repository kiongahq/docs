# What is Kionga

Kionga is an **open-source, self-hosted control plane and console for ML and AI
workloads**. It brings together three areas often run on separate tooling:

1. **Classical MLOps**: data validation, training pipelines, experiment tracking,
   a model registry, quality-gated promotion, and live model serving.
2. **Data-centric AI**: a feature store (online + offline), artifact storage, and
   real-time stream processing.
3. **Agentic AI**: LangGraph agents with persistent session state, long-term
   memory, tool use, LLM cost accounting, and tracing.

The local development environment is delivered as a Docker Compose stack. The
recommended public VM package runs a gateway and TLS edge against separately
operated identity, database, and ML services. Managed Kubernetes is the path for
distributed, isolated user workspaces and workload controllers.

## The problem it solves

Teams typically stitch together many tools (an orchestrator, a registry, a
serving system, a feature store, a tracing backend, an agent framework, a secrets
manager, an object store) and then spend a long time making them work together.
Kionga wires them together:

- A **single API and console** covers projects, pipelines, models, agents, tools,
  features, connections, and audit.
- **Real integrations, not placeholder UI**: `make -C deploy local-up` runs the
  bundled engines end to end; external services such as OpenFaaS remain visibly
  unconfigured until an operator connects them.
- **Checked infrastructure**: nothing shows as connected unless it passes an
  active health check.

## Capability map

Kionga builds these capabilities from open-source, non-proprietary tools:

| Capability | How Kionga delivers it |
| --- | --- |
| **AI orchestration**: the ML and GenAI lifecycle, automated and managed | Go control plane + Prefect pipelines + agent runtime + model registry/serving, one SDK and console |
| **Real-time processing**: fraud, call-center, recommendations | Kafka stream consumers → online feature lookup → live model/agent → result, with three runnable demos |
| **Deployment flexibility**: build once, deploy to cloud or on-premises | Containerized and config-driven; storage and database targets are set by configuration; the same images run on a laptop, a VM, or Kubernetes |
| **Integrated feature store**: real-time and batch | Online store in Redis via the feature gateway; offline Parquet snapshots in object storage |
| **Open-source serverless**: deploy project functions | OpenFaaS / faasd (single-node, Docker-native), carrying to OpenFaaS-on-Kubernetes at scale |
| **Governed team workspaces**: give each user only what they need | OIDC identities, deny-by-default entitlements, resource profiles, access requests, tokens, and Kubernetes `KiongaWorkspace` reconciliation |
| **Version-control-native delivery**: trace code to runs and deployments | Git repository metadata, workspace sync/scaffolding, commit lineage, reusable DAGs, and project-owned functions |
| **Heavy ML project foundations**: move beyond toy notebooks | Versioned production-ML and distributed-training templates, explicit accelerator/profile intent, checkpointed artifacts, MLflow lineage, and Kubernetes multi-node execution |
| **Production agent foundations**: build agents as applications | Runnable LangGraph project template with tools, memory, tracing, evaluations, HTTP runtime, containers, and Git lineage |
| **Readable pipeline topology**: inspect the real execution graph | Server-validated dependency edges rendered with the open-source Dagre layout engine; scheduling remains authoritative in the backend |

## What Kionga is *not*

- **It is not a managed cloud service.** It is software you host. Compose is the
  development path; a gateway-only VM pilot and managed Kubernetes are distinct
  deployment packages.
- **It does not require Kubernetes to be useful.** Capabilities usually associated
  with Kubernetes-only tools (KServe/Knative for serving, KFP/Argo for pipelines,
  Istio for the mesh) have Compose-native equivalents (mlflow-serve, Prefect,
  Caddy). Kubernetes is required for isolated per-user workspaces; a Kind
  environment is available for local fidelity testing.
- **It does not ship its own LLM.** Agents call external provider APIs (OpenAI,
  Anthropic, or any OpenAI-compatible endpoint); OpenAI-protocol calls go through
  a trace-capturing proxy. A `mock` backend lets the whole stack run with no API
  keys.
- **It does not bundle OpenFaaS in Compose.** Kionga implements its function API,
  persistence, quotas, triggers, UI, and pipeline integration; an operator supplies
  a faasd or OpenFaaS gateway.

## Two languages, clear ownership

Kionga follows a deliberate split:

- **Go owns infrastructure**: the gateway/control-plane API, the Kubernetes
  operator, the integration worker, the feature gateway, the storage proxy, the
  trace proxy, the serving manager, the metrics collector, the log exporter, and
  the CLI. Go's strengths (single static
  binaries, concurrency, strong typing) fit long-running services.
- **Python owns ML-facing work**: the typed SDK, the agent runtime, pipeline
  flows, feature definitions, the real-time demos, and the `kionga` workspace CLI. Python is where the ML and
  agent ecosystems live (LangGraph, LangChain, MLflow, scikit-learn, Prefect).

The web console is intentionally **vanilla JavaScript embedded in the Go gateway
binary**, with no build toolchain.

## Where to go next

- **[Architecture](architecture.md)**: the component diagram and data flows.
- **[Core concepts](concepts.md)**: the vocabulary (projects, runs, connections,
  the control plane, the data plane).
- **[Technology & modules used](technology.md)**: the stack, with versions.
- **[Installation](../getting-started/installation.md)**: get it running.
- **[Project templates](../guides/project-templates.md)**: choose and generate a
  production ML, distributed training, agent, or full-stack project.
- **[Implementation status](../reference/implementation-status.md)**: what is
  bundled, optional, external, or Kubernetes-only.
