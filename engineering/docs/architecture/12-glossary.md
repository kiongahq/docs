---
description: arc42 section 12. Terms that have a specific meaning in Kionga's code and documentation.
---

# 12. Glossary

| Term | Meaning in Kionga |
| --- | --- |
| Access profile | The administrator-managed record for a subject (`UserAccess`): role, assigned services and projects, compute and storage grants, and whether the subject is disabled. The RBAC middleware loads it on every request. |
| Access request | A request from a signed-in but unprovisioned user for services, reviewed by an administrator. |
| Agent DNS name | A collision-safe, hash-suffixed DNS label derived from an agent's immutable ID; the name of its Deployment and Service on Kubernetes. |
| Audit event | An immutable record of a mutation: action, resource, resource ID, actor, metadata, time. Written in the same transaction as the change. |
| Break-glass account | A local account enabled next to single sign-on (`KIONGA_LOCAL_LOGIN=true`) for access when the identity provider is unavailable. |
| Building block | arc42 term for a component in the static structure; see [section 5](05-building-block-view.md). |
| Catalog | The live list of connections, models, features, agents and tools, derived from stored resources rather than fixed data. |
| Connection | A registered endpoint of an external or bundled system, with a health check run from inside the gateway. |
| Control plane | The Go services that own desired state and orchestration: the gateway, and on Kubernetes the operator and integration worker. |
| Data plane | The stores that hold durable state and carry events (PostgreSQL, Redis, Kafka, RustFS, MLflow), plus the feature gateway and storage proxy. |
| Desired state | What a user asked for, as persisted by the gateway. It is not evidence that an engine has done the work. |
| Digest | The SSE payload from `/api/v1/events`: a per-caller summary of visible state. The console reloads a view only when it changes. |
| Editorial membership | A per-person role in the blog workspace (`author`, `editor`, `editorial_admin`), separate from platform roles. |
| Function DAG | A pipeline whose steps call project-owned OpenFaaS functions instead of containers. |
| Grant | An administrator's allocation to a user: services, projects, CPU, memory, GPU, storage, and run or function quotas. |
| IAM policy | A versioned set of allow and deny statements over actions and `kionga:` resources, attached to users or groups. |
| In-stack hostname | A Compose service name such as `objectstore` or `mlflow`, reachable only from inside the Compose network. |
| Integration worker | The Kubernetes process that consumes lifecycle commands from Kafka and creates or updates Kionga custom resources. |
| Internal service token | The shared bearer token (`MLAIOPS_INTERNAL_TOKEN`) that in-platform services use to report to the gateway as the `service` role. |
| Kionga custom resource | One of `KiongaAgent`, `KiongaPipelineRun`, `KiongaTool`, `KiongaConnection`, `KiongaModelPromotion`, `KiongaWorkspace` in API group `mlaiops.io/v1alpha1`. |
| Lease | A row-locked document that lets exactly one gateway replica run a singleton loop, such as the scheduler or the editorial publisher. |
| Lifecycle command | An outbox event on a `mlaiops.<kind>.commands` topic that describes a change the Kubernetes path must reconcile. |
| Outbox | The `outbox_events` table. Rows are written in the mutation's transaction and published to Kafka by a background worker. |
| Personal API key | A user-created bearer credential with the `nxs_` prefix, scoped to a subset of the creator's services and projects. |
| Preflight | The server-side check before a manual run: parameters, image pins and allowlist, quotas, concurrency, and resources. |
| Principal | The resolved caller of a request: subject, roles, groups, services, projects, and the credential type. |
| Project template | A versioned starter (production ML, distributed training, production agent, full-stack AI, blank) that fixes framework, accelerator, profile and scaffold command. |
| Ready-set scheduling | Running every pipeline node whose own dependencies have succeeded, up to a parallelism limit. |
| Resource profile | A named size for compute and storage that a project or workspace requests and a grant must cover. |
| Role baseline | A built-in managed policy that reproduces a role's permissions; evaluated together with attached policies. |
| Scale path | The Kubernetes deployment with the operator, CRDs and per-user workloads, as opposed to single-host Compose. |
| Serving image | The container image used for a deployed model; the model's `serving_image`, or `SERVE_IMAGE` as a fallback. |
| Service role | The machine role (`service`) for in-platform reporting; it may read and post to reporting paths only. |
| Sidecar (workspace) | The loopback helper inside the Jupyter and IDE containers that runs structured scaffold jobs for the gateway. |
| Tenant | The isolation unit for stored data, one per gateway process (`MLAIOPS_TENANT`), enforced with PostgreSQL row-level security. |
| Trace proxy | The OpenAI-compatible HTTP proxy that forwards LLM calls and publishes one event per call. |
| Trusted Compose profile | The single-operator local or single-host stack in which the Docker socket is mounted into engine-control services. |
| Two DNS worlds | Services reach each other by Compose service name inside the stack and by `localhost` ports from the host; health checks run inside the gateway. |
| Workspace | A user's development environment: Jupyter workbench and optional IDE sharing one persistent volume. |
