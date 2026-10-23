---
description: arc42 section 9. A summary of Kionga's architecture decisions, each linked to its MADR record.
---

# 9. Architecture decisions

Kionga records decisions as [MADR](https://adr.github.io/madr/) files under
[decisions](../decisions/index.md). This page is the summary; the record holds the
context, the options and the consequences.

| Record | Decision | Status | Date | Main consequence |
| --- | --- | --- | --- | --- |
| [0001](../decisions/0001-dag-layout-library.md) | Lay out pipeline graphs with vendored Dagre and a Kionga SVG renderer | Accepted | 2026-10-09 | Layout is presentation only; edges come from `depends_on` and a fallback layout keeps the graph readable without the library |
| [0002](../decisions/0002-blog-editor.md) | Editor.js block content rendered on the server, with a separate editorial identity | Accepted | 2026-10-09 | Publishing is a separate trust domain from ML administration |
| [0003](../decisions/0003-object-store.md) | RustFS replaces MinIO as the bundled object store | Accepted | 2026-10-09 | Fresh installs and CI start again; the service and DNS name is `objectstore` |
| [0004](../decisions/0004-go-control-plane-python-ml.md) | Go for the control plane and its services, Python for ML-facing code | Accepted | 2026-06-27 | Two toolchains, joined only by HTTP contracts and images |
| [0005](../decisions/0005-postgresql-kafka-outbox.md) | PostgreSQL as the system of record, Kafka fed by a transactional outbox | Accepted | 2026-06-28 | No event without a stored change; consumers must be idempotent |
| [0006](../decisions/0006-oidc-single-sign-on-dex.md) | Single sign-on through OIDC, with Dex as the bundled broker | Accepted | 2026-10-10 | The gateway implements one protocol; enterprise directories plug in through Dex connectors |
| [0007](../decisions/0007-per-user-workspaces.md) | Per-user workspaces reconciled from access grants on Kubernetes; a shared workbench in Compose | Accepted | 2026-07-20 | Real isolation requires Kubernetes |
| [0008](../decisions/0008-loopback-local-ports.md) | Bind local published ports to loopback by default | Accepted | 2026-10-21 | Development credentials are not reachable from the network unless you widen the bind address |
| [0009](../decisions/0009-private-images-and-pull-secrets.md) | Private GHCR images, pulled with registry credentials everywhere | Accepted | 2026-10-23 | Every deployment needs a pull secret or a registry login |
| [0010](../decisions/0010-repository-per-component.md) | One repository per component, with shared CI and versioned contracts | Accepted | 2026-10-09 | Cross-repository changes land provider first, then consumers |

Records 0004 to 0010 were written after the fact from the code and commit history.
Each one cites its evidence in its "More information" section. Where the history does not
record the alternatives that were weighed, the record says so and lists the usual
alternative only to explain the choice.

## Decisions recorded elsewhere

Some smaller choices are documented next to the code they affect rather than as
records:

- **Compose-native engines locally.** Prefect, `mlflow models serve`, OpenFaaS and
  Caddy stand in for KFP or Argo, KServe, Knative and Istio on one host
  ([technology](technology.md#technology-choices)).
- **Langfuse v2.** Pinned to the major version that self-hosts on the platform
  PostgreSQL; v3 needs ClickHouse, Redis and workers
  ([AI and observability](../components/ai-observability.md#langfuse)).
- **Karapace as the Kafka REST proxy.** Apache-licensed and Confluent v2 compatible
  ([data plane](../components/data-plane.md#kafka-and-kafka-rest)).
- **Identical ML library pins.** MLflow and scikit-learn versions match across the
  trainer, workbench and serving images to prevent training-serving skew
  ([execution and serving](../components/execution.md#pipeline-runner)).
