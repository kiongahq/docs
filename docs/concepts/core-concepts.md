---
icon: material/cube-outline
description: The vocabulary used across the Kionga console, API and documentation, from projects and runs to connections, roles and features.
---

# Core concepts

These terms appear throughout the console, the API and this documentation.

## Control plane and data plane

The **control plane** is the Kionga API and console. It owns state and
orchestration: projects, runs, models, agents, connections, users and audit. It
records what you ask for and drives the engines that carry it out.

The **data plane** is where durable data and events live: PostgreSQL, object
storage, Redis, Kafka and MLflow. See [How Kionga works](how-it-works.md#where-data-lives).

## Resources

| Resource | What it is |
| --- | --- |
| **Project template** | A versioned, immutable description of a project type: supported frameworks and accelerators, capabilities, required services, recommended resource profile, and how starter code is generated. |
| **Project** | The unit of ownership and access. It pins a template version, framework, accelerator and resource profile, and can reference a Git repository. Pipelines, models, agents and functions belong to a project. |
| **Workspace** | Where you write code: the Jupyter workbench and the browser IDE. The local stack has one shared workspace; Kubernetes gives each user an isolated workspace. |
| **Pipeline definition** | A reusable, versioned flow of container and function steps with dependencies, resources, retries, parameters, schedules and Git commit lineage. Every save creates an immutable revision. |
| **Pipeline run** | One execution of a pipeline. It has a status (`queued`, `running`, `succeeded`, `failed` or `cancelled`), a progress percentage, a graph of steps, and logs. |
| **Model** | A registered model version with metrics, a quality gate, a stage, and, once deployed, a live endpoint. |
| **Agent** | A deployed agent application: project, version, image, graph entry point, language model backend, tools, per-replica CPU, memory and GPU, replica range, and canary weight. |
| **Agent session** | One conversation with an agent: turns, the current graph node, token usage and cost. |
| **Tool** | A registered capability that agents can call, with a name, version, description and input schema. |
| **Feature view** | A named group of features for an entity, with a schema, a time to live, and online materialization status. |
| **Function** | A project-owned container workload with CPU and memory limits and HTTP, asynchronous, scheduled or Kafka trigger settings. It runs on an OpenFaaS gateway when one is configured. |
| **Connection** | A registered external service that Kionga health-checks. It stores a credential reference (`none` or `env:VARIABLE`), never the credential itself. |
| **Access profile** | What an administrator grants a person: role, services, projects, storage buckets, compute and run quotas, and a suspension switch. |
| **Access request** | A person's request for services, with a reason, reviewed in the administrator approval queue. |
| **Policy** | A set of allow or deny statements on actions and resources, attached to users or groups. |
| **Audit event** | An immutable record of a change: who did what, to which resource, and when. |

## Connections and health

A connection registers an external service, such as MLflow, S3-compatible
storage, Kafka REST, Langfuse, Prefect, OpenFaaS, Redis or a Kubernetes cluster,
so Kionga can check that it is reachable. Only a `2xx` response counts as healthy;
redirects, missing routes and authentication failures are reported as failures
with the reason. You can make a Prefect or OpenFaaS connection the active engine
for new operations.

On the local stack, Kionga runs the check from inside the stack, so connection
addresses use service names such as `http://mlflow:5000/health`. The
**onboarding readiness** score on the Overview page is based on these
connections and on having at least one project. See
[Service endpoints](../reference/service-endpoints.md).

## Quality gates and promotion

When a model is registered, Kionga sets its quality gate:

| Gate | Meaning |
| --- | --- |
| `passed` | The model can be promoted to production and deployed. |
| `failed` | The registered `accuracy` metric is below `0.8`. |
| `needs_evaluation` | The model was imported from Hugging Face and must be evaluated before serving. |

A model starts in the `candidate` stage. **Promotion** moves it to `staging`,
`production` or `archived`; only a model whose gate passed can reach
`production`. **Deployment** starts a model server for the version and records
its live endpoint and a canary weight from 0 to 100. **Rollback** returns the
model to its previous stage and removes its model server.

## Agents, sessions and tracing

An agent is a graph served by the agent runtime. Each conversation is a
**session**: the runtime saves the conversation state in PostgreSQL after every
turn and reports the session's turns, tokens and cost to Kionga.

Token counts come from the usage the model reports; Kionga does not estimate
them. **Cost** is computed from the per-1,000-token rates you configure
(`MLAIOPS_COST_PER_1K_INPUT` and `MLAIOPS_COST_PER_1K_OUTPUT`).

Calls from the `openai` and `openai-compatible` backends go through the **trace
proxy**, which forwards each call to your provider and publishes a trace of it to
Kafka without any change to agent code. Langfuse provides detailed traces and a
prompt library when its keys are configured. The `anthropic` backend calls
Anthropic directly, so the trace proxy does not capture those calls.

On the local stack, all agents share one runtime. On Kubernetes, each agent gets
its own runtime, and an agent with a replica range scales automatically. The
console enables **Chat** only when the agent's runtime passes a live health check.

## Online and offline features

- **Online** features are served from Redis for low-latency lookups, for example
  during real-time scoring or inside an agent.
- **Offline** features are stored as Parquet snapshots in object storage for
  training and batch use.

Materialization applies feature definitions, fills the online store, and reports
entity counts back to Kionga. You can also connect external feature stores; see
[Feature store integrations](../guides/feature-stores.md).

## Real-time processing

The real-time processor consumes Kafka topics, enriches each event with online
features, scores it with a model or an agent, and publishes the result. It ships
with three examples: fraud detection, call-center analysis and personalized
recommendations. The console's **Real-time** page shows throughput, latency and
recent scored events. See [Real-time processing](../guides/realtime.md).

## Serverless functions

Kionga manages functions end to end: the registry, quotas, triggers, invocation,
audit, the console, and their use as pipeline steps. Functions run on an OpenFaaS
gateway (or faasd on a single server) that an administrator provides and
connects with `OPENFAAS_URL`. Until then, functions show as not configured.

## Roles

Every request is checked against the caller's role:

| Role | Summary |
| --- | --- |
| `admin`, `operator` | Full control, including users, policies and platform connections |
| `engineer` | Builds across the ML lifecycle (projects, pipelines, models, agents, tools, features, functions); cannot manage connections or users |
| `user` | Only the services, projects and quotas an administrator assigns |
| `viewer` | Read-only |
| `service` | Kionga's own services reporting status; not for people |

See [Permissions](../reference/rbac.md) for the exact rules.
