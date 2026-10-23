---
description: Kionga is an open-source, self-hosted platform for machine learning, data and AI agents, with one API and console on infrastructure you control.
---

# What is Kionga

Kionga is an open-source, self-hosted platform for machine learning, data and AI
agents. It gives a team one API and one console to build, run and govern three
kinds of work that usually need separate tools:

- **Machine learning**: data validation, training pipelines, experiment tracking,
  a model registry, quality-gated promotion, and live model serving.
- **Data**: a feature store with online and offline features, object storage, and
  real-time stream processing.
- **AI agents**: LangGraph agents with conversation state, long-term memory,
  tools, tracing, and token and cost accounting.

You run Kionga on your own infrastructure: a laptop, a single server, or
Kubernetes in any cloud or data center.

## The problem it solves

A typical ML and AI stack combines an orchestrator, a model registry, a serving
system, a feature store, a tracing backend, an agent framework, an object store and
an identity provider. Each has its own API, its own access model and its own idea
of who owns what. Teams spend a long time connecting them and still lack one view
of what is running, who changed it, and who may use it.

Kionga puts a single control plane in front of these systems:

- **One API and console** for projects, pipelines, models, agents, tools,
  features, functions, storage, connections and audit.
- **One access model**: roles, per-user access profiles, quotas and policies that
  apply to every action, whether it comes from the console, the SDK, the CLI or a
  script.
- **Real engines, checked continuously**: Kionga drives Prefect, MLflow, LangGraph
  and the other engines directly, and a service shows as connected only after it
  passes a live health check.

## Capabilities

| Capability | What you get |
| --- | --- |
| Projects and templates | Versioned templates for production ML, distributed training, production agents, full-stack AI applications and blank Python projects, with Git integration and generated starter code |
| Workspaces | JupyterLab and a browser IDE opened from the console, preconfigured to reach every service; isolated per user on Kubernetes |
| Pipelines | Versioned flows of container and function steps with dependencies, retries, parameters, schedules, revisions and rollback |
| Models | Registration, quality gates, promotion stages, one-click deployment to a live endpoint, test predictions and rollback; Hugging Face model import |
| Agents | Deployment of LangGraph and other framework agents, chat, sessions, traces, token usage and cost, canary traffic and replica autoscaling on Kubernetes |
| Features | Online features in Redis for low-latency lookups, offline snapshots in object storage, and connections to external feature stores |
| Real-time processing | Kafka stream consumers that enrich events with online features and score them with a model or agent, with three runnable examples: fraud detection, call-center analysis and recommendations |
| Serverless functions | Project-owned functions with resource limits and HTTP, asynchronous, scheduled or Kafka triggers, run on an OpenFaaS or faasd gateway you provide |
| Governance | Single sign-on, deny-by-default access profiles, resource quotas, access requests, policies, personal API keys and an immutable audit log |
| Deployment | The same images on a laptop, a single server or Kubernetes, configured by environment and configuration files |

## What Kionga is not

- **It is not a managed cloud service.** Kionga is software you host and operate.
- **It does not require Kubernetes.** The local stack and the single-server
  package run without it. Kubernetes adds isolated per-user workspaces,
  per-agent runtimes and autoscaling.
- **It does not ship its own language model.** Agents call the provider you
  configure: OpenAI, Anthropic, or any OpenAI-compatible server. A built-in `mock`
  model lets you run everything without a provider key.
- **It does not bundle a serverless engine.** Kionga manages functions end to end,
  but runs them on an OpenFaaS or faasd gateway that you provide.

## Next steps

- [Core concepts](core-concepts.md): the vocabulary used throughout Kionga.
- [How Kionga works](how-it-works.md): how the parts fit together.
- [Install Kionga](../getting-started/installation.md): run it on your machine.
