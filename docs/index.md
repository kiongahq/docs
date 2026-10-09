# Kionga documentation

Kionga is an open-source, self-hosted platform that brings projects, pipelines,
models, features, and AI agents into one control plane. It connects the tools
your team already uses and gives
engineers a shared place to build, run, and inspect their work.

Start with the local Compose stack to explore the platform. For a team deployment,
plan around managed Kubernetes and complete the
[production acceptance checks](operations/production-operations.md) before
admitting users. The [implementation status](reference/implementation-status.md)
distinguishes bundled features from optional integrations and paths that have not
been verified on a live cluster.

<div class="grid cards" markdown>

- :material-rocket-launch: **[Install locally](getting-started/installation.md)**

    Clone the component repositories and start the development stack.

- :material-play-circle: **[Follow the quickstart](getting-started/quickstart.md)**

    Create a project, run a pipeline, and explore the connected services.

- :material-sitemap: **[Understand the architecture](overview/architecture.md)**

    See how the gateway, workloads, and data services fit together.

- :material-cloud-check: **[Plan a deployment](hosting.md)**

    Compare the public VM pilot with the managed Kubernetes path.

</div>

## What is included

The local stack includes the gateway and console, PostgreSQL, Redis, Kafka,
RustFS object storage, MLflow, Prefect, Jupyter, and the Kionga workload services.
You can create projects, define and run pipelines, register and serve models,
work with features, and develop agents. The optional browser IDE shares the
Jupyter workspace.

Some capabilities need infrastructure you provide. For example, function
deployment needs an OpenFaaS gateway, and real LLM responses need a provider
account. The console should show these integrations as unavailable until they are
configured. See [connecting services](connecting-services.md) for the local
service map and [implementation status](reference/implementation-status.md) for
the current boundaries.

## Find the right guide

| If you want to… | Start here |
| --- | --- |
| Learn the platform's terminology | [Core concepts](overview/concepts.md) |
| Use notebooks or the browser IDE | [Workbench](guides/workbench.md) |
| Define a pipeline or inspect a run | [Pipelines](guides/pipelines.md) |
| Provision users and resources | [Access control](guides/access-control.md) |
| Integrate from a script or application | [REST API](reference/api.md) or [Python SDK](modules/python.md) |
| Operate or troubleshoot the stack | [Local operations](operations/local.md) and [troubleshooting](operations/troubleshooting.md) |

!!! warning "Local credentials are for development only"
    The passwords and tokens shown in local examples are defaults for a private
    development stack. Do not use them on a public deployment. Use the
    [hosting guide](hosting.md) and [production checklist](operations/production-operations.md)
    when preparing an environment for other users.
