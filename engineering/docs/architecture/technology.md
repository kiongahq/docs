---
description: Every runtime, library and image in Kionga, why it is there, and where its version is pinned.
---

# Technology

This page supports [section 4](04-solution-strategy.md) of the architecture. It lists
every technology in the stack, why it is here, and where it is pinned. Versions match
the images and dependency pins in the Kionga repositories; when you change a pin,
change it here in the same pull request.

## Languages and runtimes

| Technology | Version | Role |
| --- | --- | --- |
| Go | 1.26, toolchain and builder image 1.26.10 (`platform/go/go.mod`, `golang:1.26.10-alpine`); runtime image `gcr.io/distroless/static-debian12:nonroot` | Gateway, operator, integration worker, feature gateway, storage proxy, metrics collector, log exporter, CLI, serving manager, trace proxy ([decision 0004](../decisions/0004-go-control-plane-python-ml.md)) |
| Python | 3.11 or later (`requires-python` in the SDK); `python:3.11-slim` for the agent runtime, pipeline runner and Jupyter images | SDK, agent runtime, pipelines, features, real-time demos |
| JavaScript | Plain browser scripts, no framework and no build step | Embedded web console and public pages |

## Data plane

| Technology | Image or pin | Role |
| --- | --- | --- |
| PostgreSQL with pgvector | `pgvector/pgvector:pg16` | Control-plane state, outbox, MLflow and Langfuse backends, agent checkpoints, vector memory |
| Redis | `redis:7.4.5-alpine` | Online feature store |
| Apache Kafka | `apache/kafka:3.9.1` (`KRaft`) | Audit and lifecycle events, LLM traces, real-time topics |
| Kafka REST proxy | Karapace `ghcr.io/aiven-open/karapace:6.1.4` | Apache-licensed, Confluent v2 compatible HTTP access to Kafka, so Python services need only an HTTP client |
| RustFS | `rustfs/rustfs:1.0.1`, pinned by digest | S3-compatible object storage under Apache-2.0 ([decision 0003](../decisions/0003-object-store.md)) |
| MLflow | `mlflow==3.16.1`; the `mlaiops-mlflow` image is built from `deploy/mlflow/Dockerfile` on `ghcr.io/mlflow/mlflow:v3.16.1` | Experiment tracking and model registry; also the fallback serving image |

## Orchestration and serving

| Technology | Pin | Role |
| --- | --- | --- |
| Prefect | `prefect>=3.0` in `pipeline-runner/requirements.txt`; server image `prefecthq/prefect:3-latest` | Pipeline execution engine in Compose (the Compose-native stand-in for KFP and Argo) |
| scikit-learn | `scikit-learn==1.7.0` | Demo training; pinned identically in the runner, workbench and serving images to prevent training-serving skew |
| PyTorch DDP | Dependency of the `distributed-training` project template | Multi-process and multi-GPU training; `torchrun` owns process launch |
| `mlflow models serve` | Started by the serving manager | Live model endpoints (the Compose-native stand-in for KServe and Knative) |
| Docker Engine API | Version negotiated with the daemon, overridable with `DOCKER_API_VERSION` | The serving manager and pipeline runner start containers over the Docker socket |
| Dagre | `@dagrejs/dagre@2.0.0` (MIT), vendored with an integrity hash | Pipeline graph layout in the console; execution order stays on the server ([decision 0001](../decisions/0001-dag-layout-library.md)) |
| Editor.js, highlight.js | Editor.js 2.31.7, highlight.js 11.11.1, vendored with integrity hashes | Editorial workspace and public blog ([decision 0002](../decisions/0002-blog-editor.md)) |

## Agentic AI

| Technology | Pin | Role |
| --- | --- | --- |
| LangGraph | `langgraph>=0.2` | Agent graphs (`StateGraph`: reason, tools, respond) |
| LangGraph PostgreSQL checkpoint | `langgraph-checkpoint-postgres>=2.0` | Durable session state (`AsyncPostgresSaver`) |
| LangChain | `langchain-core>=0.3`, `langchain-openai>=0.2`, `langchain-anthropic>=0.2` | Chat model abstractions and tool conversion |
| Agno (optional) | SDK `agno` extra, `agno>=2,<3` | `arun` adapter with session and user context |
| NVIDIA OO-Agents, NOOA (optional) | SDK `nooa` extra; separate Python 3.12 or 3.13 image | Typed async method adapter; needs operator-provided isolation for generated code |
| Custom frameworks | SDK `CallableAdapter` | Stable request and result contract without control-plane schema changes |
| Langfuse | `langfuse>=2.0`; image `langfuse/langfuse:2` | LLM and agent observability on PostgreSQL (v2) |
| FastAPI and `Uvicorn` | `fastapi>=0.111`, `uvicorn>=0.30` | The agent runtime's HTTP service |
| `psycopg` | `psycopg[binary]>=3.1` | PostgreSQL access for memory and checkpoints |

## Edge and identity

| Technology | Image | Role |
| --- | --- | --- |
| Caddy | `caddy:2.8` in the legacy overlay; a digest supplied through `deploy/vm/up.py` on a single server | Automatic Let's Encrypt TLS and reverse proxy (stands in for Istio ingress) |
| Dex | `ghcr.io/dexidp/dex:v2.46.0`, pinned by digest | OIDC broker for single sign-on: LDAP, SAML, GitHub, Google, GitLab, Microsoft, OIDC ([decision 0006](../decisions/0006-oidc-single-sign-on-dex.md)) |
| GLAuth | `glauth/glauth:v2.5.4`, pinned by digest | Local LDAP test directory behind Dex |
| OpenFaaS or faasd | Installed outside Kionga | Open-source serverless functions (stands in for Knative) |
| code-server | `codercom/code-server:4.99.4` base for the `ide` image | Browser IDE sharing the Jupyter workspace volume |
| JupyterLab and Jupyter AI | `jupyter` image built from `workspace/jupyter/Dockerfile` | Notebook and terminal workbench with a natural-language coding surface |

## Client and SDK

| Technology | Pin | Role |
| --- | --- | --- |
| `httpx` | `httpx>=0.27` | HTTP client in the SDK and workloads |
| `pydantic` | `pydantic>=2.7` | Typed models in the SDK |
| `pgx` | `github.com/jackc/pgx/v5` | PostgreSQL driver for the Go services; see [Go packages](../components/go-packages.md) for the other direct dependencies |

## Development and CI

| Technology | Role |
| --- | --- |
| `pytest` and `pytest-asyncio` | Python tests |
| ruff | Python lint |
| `go test`, `go vet`, gofmt | Go tests, static checks, formatting |
| Node.js test runner, `jsdom`, Playwright, axe-core | Console unit tests (`npm run test:ui`) and browser acceptance tests in `platform/tests` |
| `govulncheck`, `gosec`, `gitleaks`, pip-audit, bandit | Security gates in CI ([contributing](../contributing/index.md#ci-gates)) |
| k6 | Load test with latency thresholds (`deploy/tests/load/gateway.js`) |
| kind and Helm | Local Kubernetes for the scale-path tests; chart linting |
| GitHub Actions | Reusable workflows in `kiongahq/.github`: `go.yml`, `python.yml`, `image.yml` |
| MkDocs Material, Vale | The documentation sites and their prose lint |

## Kubernetes workload path

Managed Kubernetes is required for isolated per-user workspaces and distributed team
workloads. It is not required for the local Compose stack or a gateway-only server.

| Asset | Location | Role |
| --- | --- | --- |
| CRDs | `deploy/config/crd/` | `KiongaAgent`, `KiongaPipelineRun`, `KiongaTool`, `KiongaConnection`, `KiongaModelPromotion`, `KiongaWorkspace` |
| Operator RBAC | `deploy/config/rbac/` | Scoped operator permissions, including owned agent autoscaling |
| NetworkPolicies | `deploy/config/network/`, `deploy/config/network-istio/` | Default deny with platform allow rules, and strict mTLS for Istio |
| Security | `deploy/config/security/` | Dex and Vault authentication assets |
| Backup | `deploy/config/backup/` | CloudNativePG backup |
| Helm chart | `deploy/helm/kionga` | The packaged platform services ([deployment view](07-deployment-view.md#kubernetes-through-helm)) |
| kind cluster | `deploy/kind/cluster.yaml` | Local Kubernetes cluster definition |

## Technology choices

Kionga uses open-source tools throughout. Where a capability is usually tied to a
Kubernetes-only tool, Kionga uses a Docker-friendly equivalent on a single host and
keeps the Kubernetes-native tool for the scale path.

| Capability | Single host | Kubernetes-native equivalent |
| --- | --- | --- |
| Model serving | `mlflow models serve` containers | KServe (created on promotion by the operator) |
| Pipelines | Prefect | KFP (through `KiongaPipelineRun`), or Kubernetes Jobs |
| Serverless | OpenFaaS or faasd | Knative |
| Edge and mesh | Caddy | Ingress, optionally Istio |
