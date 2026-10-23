---
description: What is implemented in the Kionga repositories, how each capability is delivered, and how far it is verified.
---

# Implementation status

This page records the implementation scope in the Kionga repositories. “Implemented”
means the named code path exists; it does not certify a production deployment or
mean every upstream engine is bundled with Compose. The delivery labels and
evidence below distinguish local tests, live integration tests, and unverified
external systems. Before admitting users, complete the
[production acceptance checklist](https://kiongahq.github.io/docs/operations/production-operations/).

## Capability matrix

| Capability | Delivery | Current behavior |
| --- | --- | --- |
| Control plane, console, landing page, API docs | **Bundled** | Go gateway with PostgreSQL persistence, audit/outbox, throttled local login, single sign-on through Dex (OIDC/JWKS), RBAC, SSE updates, security response headers, and the embedded web surfaces |
| Projects and Git metadata | **Bundled** | Create/read projects; connect credential-free HTTPS/SSH repository metadata; scaffold or synchronize source inside a workspace |
| Versioned project templates | **Bundled** | Catalog/API/SDK contracts for production ML, distributed PyTorch training, production agents, full-stack AI, and blank expert projects; framework/accelerator/profile validation, required-service/GPU admission for normal users, and returned scaffold command |
| User access and resource provisioning | **Bundled control plane** | Admin profiles, service/project/bucket grants, CPU/RAM/GPU/storage/run/function quotas, access requests, personal API keys, and enforcement at the gateway |
| Users, groups, roles and IAM-style policies | **Bundled control plane** | Pure evaluator (default deny, explicit deny wins, `kionga:` resource patterns, IP/UTC-hours/resource-tag/resource-profile conditions) with managed role baselines; groups, versioned policies with immutable revisions and attachments stored as audited documents; anti-escalation, self-lockout and last-admin protection; `authorize()` enforces pipelines, projects, workspace launch, features, user provisioning, connections and IAM administration (the `blog:*` catalog actions are not enforced; the engineering blog uses editorial memberships); 403 denials carry the deciding statement; explain/effective APIs and a console simulator. Models, agents, functions and storage stay on role + project assignment. See [access control](https://kiongahq.github.io/docs/guides/access-control/). |
| Shared Jupyter workbench | **Bundled** | Persistent `/workspace`, Jupyter AI, SDK/modules, coding-agent CLIs, and S3FS-mounted object-store buckets |
| Shared browser IDE | **Optional Compose profile** | `make -C deploy ide-up`; code-server mounts the same persistent workspace as Jupyter |
| Per-user Jupyter/IDE workspaces | **Kubernetes scale path** | `KiongaWorkspace` reconciles bounded workloads, PVC, service, credentials, suspension, and revocation from user grants |
| Container pipelines | **Implemented and verified (trusted Compose profile)** | Prefect runs validated container DAGs with ready-set scheduling (a node starts when its own dependencies succeed), bounded parallelism, per-node timeout/retry backoff, `when` conditions, skip-downstream-on-failure, rerun-from-failure; nodes report start/end, attempt, exit code, container id and image digest. Verified end to end in the browser with parallel-branch overlap. |
| Pipeline definitions | **Implemented and verified** | `kionga.dev/v1 Pipeline` YAML and form editors over one canonical definition; field/node/line validation (cycle paths, missing dependencies, cron/timezone); immutable revisions with diff and rollback; runs pin revision + SHA-256, overrides, policy decision and image digests; JSON Schema in `contracts/pipeline`. Git: export/import through the YAML API; Kionga never commits for you. |
| Schedules | **Implemented and verified** | Cron + IANA timezone triggers, leased single scheduler, exactly once slot claims, bounded catch-up, runs as the schedule owner with quotas; pause/resume in the console |
| Manual run configuration | **Implemented and verified** | Server-enforced preflight: overridable parameters, digest-pinned and registry-allowlisted images, resources within quota, retries/timeouts, node selection, parallelism, rerun-from-failure; preflight summary before start |
| Logs and events | **Implemented and verified locally** | Structured `log_entries` (PostgreSQL, RLS) with runner streaming, platform step events, redaction, filters, cursor pagination, SSE tail, retention, project isolation; node log panel and Logs page |
| Log export to Elasticsearch/OpenSearch | **Implemented, unverified against a live cluster** | Separate adapters (data stream vs daily index), at-least-once cursor, partial-failure retry, dead-letter counts, TLS/API key/basic auth from files, health states on the Platform page; tested against protocol fakes only |
| Kubernetes execution of pipeline nodes | **Implemented, unverified on a live cluster** | Opt-in (`pipelineExecutor.kubernetes`): one hardened Job per node attempt, ready-set scheduling, timeouts, retries, exit codes/OOM reasons, Pod and Job events as `k8s` log events, namespace-scoped RBAC. Tested with the client-go fake. Pod stdout streaming into Kionga logs is planned. |
| General container-DAG execution | **Bundled locally; Kubernetes scale path** | `pipeline-definition/mlaiops` translates validated container jobs into Docker workloads in the trusted single-operator profile. Its socket is root-equivalent, so distributed teams use Kubernetes-native workers/KFP rather than exposing a node runtime socket |
| Workload resource admission | **Bundled control plane** | For normal users, project templates must fit service/profile/GPU grants; the widest concurrent pipeline layer must fit CPU/RAM/GPU; functions must fit CPU/RAM and count quotas; all owned agents reserve aggregate CPU/RAM/GPU and trace-sidecar capacity at maximum replicas; GPU types use strict Kubernetes extended-resource names; admin/operator capacity bypass is explicit |
| Experiments and model registry | **Bundled** | MLflow with PostgreSQL backend and RustFS artifacts |
| Local model serving | **Bundled** | Serving manager launches live `mlflow models serve` containers and proxies predictions |
| Agents, memory, tools, and observability | **Bundled LangGraph; opt-in framework adapters** | LangGraph checkpoints and callbacks; Agno, NOOA, and custom request/result adapters with example factories. Non-LangGraph persistence/provider setup is application-owned, SSE is buffered, and unknown usage is explicit. NOOA needs a separate Python 3.12–3.13 image and operator-provided isolation. Compose serves one factory; Kubernetes uses isolated per-agent workloads. See [framework guide](https://kiongahq.github.io/docs/guides/agent-frameworks/). |
| Functional agent project starter | **Bundled developer tooling** | `production-agent` generates runnable graph/runtime boundaries, typed tool/state examples, deterministic tests/evals, container packaging, and a platform manifest; provider access remains external configuration |
| Heavy/distributed training project | **Bundled starter; Kubernetes scale path for multi-node** | `distributed-training` establishes PyTorch DDP launch, mixed precision, checkpoints, rank-aware tracking, and GPU intent; actual GPU topology/capacity comes from provisioned profiles and the target scheduler |
| Feature store | **Bundled** | Redis online retrieval plus Parquet snapshots in the object store; Feast-compatible online request shape; immutable definition versions, materialization lineage, freshness (fresh/stale/never), point-in-time join and Redis TTL sweep in `agent-runtime/features`, usage/failure Prometheus counters on the feature gateway. See [feature stores](https://kiongahq.github.io/docs/guides/feature-stores/) |
| Real-time processing | **Bundled demos** | Kafka fraud, call-center, and recommendation flows with live stats; deterministic fallbacks until a model/agent is selected |
| Object storage filesystem in Jupyter | **Bundled local workbench** | S3FS mounts configured object-store buckets under `/workspace/object-store`; production multi-user mounts require per-workspace isolation |
| Functions and event-driven microservices | **External integration** | Project-owned OCI functions, quotas, HTTP/async/Cron/Kafka trigger metadata, invocation, and function DAG execution require `OPENFAAS_URL` |
| Public VM edge | **Gateway-only pilot** | `make -C deploy public-up` runs the digest-pinned gateway behind Caddy TLS with external OIDC, PostgreSQL, and ML services. The separate legacy Compose/Dex overlay is a development compatibility path, not the recommended public package. |
| Engineering blog and editorial workspace | **Bundled** | Editor.js block content with a server renderer sanitized by `bluemonday`, separate `/editorial.html` workspace with its own `kionga_editorial` session and author/editor/editorial_admin memberships, draft → review → scheduled/published workflow with a leased scheduled publisher, immutable revisions with compare/restore, autosave with 409 conflicts and local recovery, image uploads (sniffed, EXIF stripped, 480/960/1600 variants) to S3 (RustFS locally) or the filesystem, public search/tag/author pages with highlighted code. See [engineering blog](https://kiongahq.github.io/docs/guides/engineering-blog/) |
| Kubernetes-native execution/serving | **Scale path** | CRDs, operator, RBAC, NetworkPolicy, workspace reconciliation, KFP/Argo and KServe contracts, plus an at-least-once lifecycle worker with manual Kafka commits; elastic agent scaling requires resource metrics |

## Scaffolding, feature stores and external storage

| Item | Status | Evidence |
| --- | --- | --- |
| Structured scaffold jobs (`/api/v1/projects/{id}/scaffold-jobs`), catalog-derived `argv`, project access, one job per project, stale-job recovery | **Implemented** | Go unit + PostgreSQL integration tests; live run against a local gateway, the real sidecar and `kionga.py` |
| Console Run in workspace (confirmation with exact `argv`, live progress, files, git status, errors) | **Implemented** | `jsdom` tests; Playwright `features-scaffold.spec.cjs` against a local gateway |
| Workspace sidecar `POST /scaffold-jobs` (`argv` allowlist, token, no shell, scrubbed `env`, timeout) | **Implemented** | `workspace/tests/test_workspace_directories.py` incl. a real HTTP server |
| Sidecar reached through `jupyter-server-proxy` in the Jupyter image and `/proxy/8890` in the IDE | **Implemented, unverified live** | Image and entrypoint changes need `make -C deploy local-rebuild`; exercised locally with a Jupyter stand-in |
| One project path for Jupyter, IDE and scaffold | **Implemented** | `TestProjectPathIsSharedByJupyterIDEAndScaffold` |
| Scaffold as Kubernetes Jobs | **Planned** | Per-user workspace sidecars run jobs today |
| Feature store adapter registry; `internal` and `feast` adapters; other providers listed as contract only | **Implemented** | Adapter conformance suite with Feast HTTP fakes |
| Feature store connections (admin CRUD, test, scoped summaries, secrets by reference only) | **Implemented** | Go handler tests, PostgreSQL integration, Playwright against a local Feast stand-in |
| Feature definition versions, lineage, freshness API and console cards | **Implemented** | Go tests, `jsdom`, Playwright |
| Point-in-time join, Redis TTL/retention sweep | **Implemented** | Python leakage fixture and sweep tests (no live Redis run) |
| External S3-compatible storage connections with signed `HEAD` health check and CA bundles | **Implemented** | Signature-verifying fake S3, TLS CA tests, handler tests; not run against a real cloud bucket |
| Operator tenant storage admission (no `hostPath`, allowlisted StorageClasses) | **Implemented** | Unit test and fake-client reconcile test |
| StorageClass allowlists per tenant resource profile | **Planned** | Operator-wide allowlist today |

## Honest readiness rules

- A bundled service is ready only after its health check passes.
- An external integration remains visibly **not configured** until its endpoint and
  credentials are supplied.
- Control-plane records do not claim that an external workload exists when its
  engine rejected creation.
- Compose is the quickest complete single-user/single-VM experience. Kubernetes is
  required for isolated per-user workspaces and distributed-team resource
  reconciliation.

## Local verification commands

From the workspace folder, run these commands against the exact revision to be
released. A command listed here is not a claim that the current CI run passed:

```bash
make -C platform verify              # Go, console and unit tests
make -C platform test-integration    # PostgreSQL
make -C serving verify && make -C trace-proxy verify
make -C deploy test                  # compose wiring, cross-repo contracts, Helm chart
make -C docs docs-build docs-check   # strict site build, references against the code
make -C deploy local-up
make -C deploy smoke                 # end-to-end against the running stack
```

The Python repositories (`sdk-python`, `agent-runtime`, `pipeline-runner`,
`workspace`, `contracts`) each run `python -m pytest -q && ruff check .` after
installing their `requirements-dev.txt` (or `.[dev]` for the SDK).

The smoke test reports a dynamic pass/skip count. OpenFaaS is skipped unless it is
configured; optional observability checks may also skip while an upstream service
is initializing. Treat any **failure** as a real integration problem.

See [Installation](https://kiongahq.github.io/docs/getting-started/installation/) for host requirements and
[Troubleshooting](https://kiongahq.github.io/docs/operations/troubleshooting/) for Docker disk, port, and DNS
diagnostics.
