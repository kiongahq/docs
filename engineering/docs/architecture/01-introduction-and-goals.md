---
description: arc42 section 1. What Kionga must do, the quality goals that shape its design, and the stakeholders the architecture serves.
---

# 1. Introduction and goals

Kionga gives a team one self-hosted place to build, run and govern machine learning,
data and AI-agent workloads. It is a control plane over open-source engines rather
than a replacement for them: it validates intent, enforces who may do what,
persists desired state with an audit trail, and delegates execution.

## Requirements overview

The capabilities below exist in code today. The
[implementation status](../status/implementation-status.md) records how far each one
has been verified (local tests, live integration, or unverified against an external
system).

| Area | What Kionga provides |
| --- | --- |
| Identity and access | Sign-in through single sign-on (an OIDC broker, Dex in the bundled stack) or local accounts; roles, per-user service and project grants, quotas; IAM-style policies with explicit deny; personal API keys; an audit record for every mutation |
| Projects | Versioned project templates, Git repository metadata, scaffolding inside a workspace |
| Workspaces | A shared Jupyter workbench and optional browser IDE in Compose; isolated per-user workspaces reconciled by an operator on Kubernetes |
| Pipelines | `kionga.dev/v1 Pipeline` definitions with validation, revisions, schedules, manual run preflight, structured logs; execution through Prefect (Compose), OpenFaaS (function DAGs), or opt-in Kubernetes Jobs |
| Models | Experiment tracking and a model registry in MLflow; promotion; serving through `mlflow models serve` containers locally and KServe on Kubernetes |
| Features | Online retrieval from Redis (or a Feast feature server), Parquet snapshots in object storage, point-in-time joins, freshness |
| Agents | LangGraph agents served over HTTP with PostgreSQL checkpoints, optional Agno, NOOA and custom adapters, LLM egress through a tracing proxy, Langfuse observability, measured token usage and cost |
| Real-time | Kafka consumers that enrich events with online features and score them (fraud, call-center and recommendation demos) |
| Editorial | An engineering blog with a separate editorial workspace, memberships and session |

## Quality goals

These five goals, in priority order, explain most of the design. Section 10 refines
them into [scenarios](10-quality-requirements.md) tied to tests.

| Priority | Quality goal | What it means in Kionga |
| --- | --- | --- |
| 1 | Security and isolation | Default deny. Authorization runs on every API request in every deployment profile. A normal user reaches only the services and projects an administrator granted. Production refuses to start with development credentials. |
| 2 | Truthful state | The control plane never reports that external work exists or succeeded because desired state was accepted. Writes are transactional with their audit record and outbox events; failed engine calls are recorded as failures. |
| 3 | Operability on one machine and at scale | The full stack runs from one `docker compose` file on a laptop or single server; the same API and contracts run on Kubernetes with an operator, Helm chart and network policies. |
| 4 | Openness and portability | Open-source components only, with permissive licenses where Kionga bundles them; standard interfaces (S3, OIDC, OCI images, Kafka, OpenAI-compatible HTTP) so engines can be replaced. |
| 5 | Reproducibility | Images pinned by digest for servers and clusters; ML libraries pinned identically across training, notebooks and serving to prevent training-serving skew; deterministic, network-free gate tests. |

## Stakeholders

| Stakeholder | Role in Kionga | Expectations of the architecture |
| --- | --- | --- |
| Platform administrator | `admin` or `operator` role | Grant and revoke access quickly, see an audit trail, keep users inside quotas, recover the system |
| ML and data engineer | `engineer` or provisioned `user` role | Create projects, run pipelines, register and serve models, open a workspace, without waiting on an administrator for each step |
| Agent developer | `engineer` or `user` with the agents service | Deploy an agent image with a graph entry point, call it, and see sessions, traces, tokens and cost |
| Viewer | `viewer` role | Read projects, runs, logs and features without changing anything |
| In-platform service | `service` machine identity | Report step transitions, traces, materializations and real-time statistics back to the control plane |
| Editorial author, editor, administrator | Editorial membership, separate from platform roles | Write, review and publish engineering posts without platform administration rights |
| Operator of an installation | Runs Compose, the single-server package or the Helm chart | Clear prerequisites, pinned releases, health checks, secrets kept out of configuration |
| Contributor and maintainer | Changes the code in the Kionga repositories | Independent repositories with fast gate tests, explicit contracts, and this handbook |

The roles and their exact permissions are in the
[permissions reference](https://kiongahq.github.io/docs/reference/rbac/); the editorial
model is in [decision 0002](../decisions/0002-blog-editor.md).
