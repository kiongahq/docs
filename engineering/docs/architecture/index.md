---
icon: material/sitemap-outline
description: Kionga's architecture documented in the twelve arc42 sections, from goals and constraints to risks and the glossary.
---

# Architecture

This part of the handbook describes Kionga's architecture using the
[arc42](https://arc42.org/overview) template. Each section is a separate page, so you
can link to one view without pulling in the rest. Every statement is grounded in the
code of the Kionga repositories or in an existing record; where the code and a plan
differ, the code wins and the gap appears in [risks and technical debt](11-risks-and-technical-debt.md).

## Kionga in one paragraph

Kionga is a self-hosted, open-source (MIT) platform for machine learning, data and AI
agents. A Go control plane (the gateway) owns desired state, identity, authorization
and audit. It delegates execution to open-source engines (Prefect, MLflow, LangGraph,
Langfuse, OpenFaaS, and on Kubernetes KFP and KServe) and records what they report back.
PostgreSQL is the system of record, Kafka carries lifecycle and audit events through a
transactional outbox, Redis serves online features, and RustFS provides S3-compatible
object storage. The same contracts run on one machine with Docker Compose and on
Kubernetes through Helm.

## Sections

| Section | What it answers |
| --- | --- |
| [1. Introduction and goals](01-introduction-and-goals.md) | What Kionga must do, the quality goals that shape it, and who cares |
| [2. Constraints](02-constraints.md) | Technical, organizational and convention constraints the design accepts |
| [3. Context and scope](03-context-and-scope.md) | Users and external systems, and the protocols at the boundary |
| [4. Solution strategy](04-solution-strategy.md) | The few decisions that shape everything else |
| [5. Building block view](05-building-block-view.md) | The static decomposition, from repositories down to control-plane packages |
| [6. Runtime view](06-runtime-view.md) | Sign-in, a pipeline run, model promotion and serving, and an agent turn |
| [7. Deployment view](07-deployment-view.md) | Local Compose, a single server, and Kubernetes through Helm |
| [8. Crosscutting concepts](08-crosscutting-concepts.md) | Identity, authorization, tenancy, configuration, observability, errors, persistence |
| [9. Architecture decisions](09-architecture-decisions.md) | The decision log, with links to each record |
| [10. Quality requirements](10-quality-requirements.md) | The quality tree and scenarios, each tied to a test or a check |
| [11. Risks and technical debt](11-risks-and-technical-debt.md) | Known weaknesses, read from the code and the implementation status |
| [12. Glossary](12-glossary.md) | Terms with a specific meaning in Kionga |

Supporting pages:

- [Technology](technology.md): every runtime, library and image with its pin.
- [Components](../components/index.md): one page per repository and service.
- [Backend contracts](../contracts/backend.md): the interfaces between the control
  plane, its clients and its workers.
- [Implementation status](../status/implementation-status.md): what is bundled,
  optional, verified, or planned.

## Keep it current

Update the affected section in the same pull request as the code change. A new
building block changes section 5; a new external system changes section 3; a reversed
decision adds a record under [decisions](../decisions/index.md) and a row in
section 9. The [documentation standard](../contributing/documentation.md) describes the
checks that run on these pages.
