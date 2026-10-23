---
description: Choose a versioned project template and create a Kionga project from the console, the Python SDK, or the REST API.
---

# Create a project from a template

Create a Kionga project from one of five versioned templates. The template you
choose records the framework, accelerator, resource profile and capabilities on
the project, and gives you the exact `kionga scaffold` command that generates
the starter code. Runs, model versions and agent deployments in the project
keep that record.

Creating a project stores its record only. No files are written until you
[scaffold the project](scaffolding.md).

## Before you begin

- You need a role that can create projects:
    - `admin`, `operator` or `engineer` can create a project from any template.
    - A normal user (`user` role) needs the `projects` service, plus every
      service the template requires (see the [template catalog](#template-catalog)),
      and a free slot in the project quota of their resource grant.
- To connect a Git repository while you create the project, a normal user also
  needs the `git` service.
- To use the SDK or the API from outside a Kionga workspace, create a personal
  API key in **Settings > Personal API keys** with the `projects` scope, and
  export it as `MLAIOPS_TOKEN` together with the gateway address in
  `MLAIOPS_URL`. Inside Jupyter or the browser IDE, the SDK needs no key.

## Template catalog

| Template | Use it for | Frameworks | Accelerators | Recommended profile | Required services |
| --- | --- | --- | --- | --- | --- |
| `production-ml` | Reproducible training, evaluation gates, MLflow registration, batch inference, serving and monitoring | `scikit-learn`, `xgboost`, `pytorch` | `cpu`, `single-gpu` | `power` | `pipelines`, `models`, `features`, `storage`, `git`, `workbench` |
| `distributed-training` | Large deep-learning jobs with PyTorch DDP, mixed precision, durable checkpoints and reproducible evaluation | `pytorch-ddp` | `single-gpu`, `multi-gpu` | `gpu` | `pipelines`, `models`, `storage`, `git`, `workbench` |
| `production-agent` | Stateful LangGraph agents with tools, checkpoints, semantic memory, tracing, evaluations and an HTTP runtime | `langgraph` | `cpu`, `single-gpu` | `team` | `agents`, `storage`, `git`, `workbench` |
| `fullstack-ai` | A model or agent backend, an API, an event function, a browser client, containers, CI and tests | `fastapi-ml`, `fastapi-agent` | `cpu`, `single-gpu` | `power` | `models`, `agents`, `functions`, `storage`, `git`, `workbench`, `ide` |
| `blank-python` | A typed Python package with containers, CI, linting and tests, without an ML or agent structure | `python` | `cpu`, `single-gpu`, `multi-gpu` | `starter` | `git`, `workbench` |

Every template is at version `1.0.0`. A template version is immutable: a later
release can add a new version, but a project pinned to `1.0.0` keeps generating
the same starter.

When you leave a field empty, Kionga uses the template's first framework, its
first accelerator and its recommended profile. Kionga rejects combinations a
template does not support, for example `scikit-learn` with `single-gpu` in
`production-ml`, or `multi-gpu` in any template other than
`distributed-training` and `blank-python`.

## List the available templates

Use the catalog to compare templates before you create a project.

=== "Console"

    1. Open **Projects** and click **＋ New project**.
    2. Under **Starting architecture**, review each template's framework,
       accelerator, capabilities, required services and recommended profile.

=== "SDK"

    ```python
    from mlaiops_sdk import MLAIOpsClient

    with MLAIOpsClient() as client:
        for template in client.list_project_templates():
            print(template.id, template.frameworks, template.accelerators)
        print(client.get_project_template("distributed-training").required_services)
    ```

=== "API"

    ```bash
    curl -s -H "Authorization: Bearer $MLAIOPS_TOKEN" \
      "$MLAIOPS_URL/api/v1/project-templates" | python -m json.tool
    curl -s -H "Authorization: Bearer $MLAIOPS_TOKEN" \
      "$MLAIOPS_URL/api/v1/project-templates/production-agent" | python -m json.tool
    ```

=== "Workspace terminal"

    ```bash
    kionga templates
    kionga templates --json
    ```

**Verify:** the list contains the five templates in the catalog above.

## Create a project

=== "Console"

    1. Open **Projects** and click **＋ New project**.
    2. Enter a **Project name** and, optionally, what it is for.
    3. Under **Starting architecture**, select a template.
    4. Under **Runtime shape**, choose the **Framework**, **Accelerator** and
       **Requested profile**. Options that your grant does not cover are
       disabled and labeled, for example `not provisioned`.
    5. Optional: under **Source control**, enter the **Git repository** URL and
       the **Default branch**.
    6. Click **Create project**.

=== "SDK"

    ```python
    from mlaiops_sdk import MLAIOpsClient

    with MLAIOpsClient() as client:
        project = client.create_project(
            "churn-model",
            template="production-ml",
            framework="xgboost",
            accelerator="cpu",
            requested_profile="team",
            repository_url="https://github.com/acme/churn-model.git",
        )
        print(project.id, project.scaffold_command)
    ```

=== "API"

    ```bash
    curl -s -X POST "$MLAIOPS_URL/api/v1/projects" \
      -H "Authorization: Bearer $MLAIOPS_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"name": "churn-model", "template": "production-ml",
           "framework": "xgboost", "accelerator": "cpu",
           "requested_profile": "team"}'
    ```

The gateway checks every rule again, whatever client you use: an unsupported
combination returns `422`, and a missing service, a profile larger than your
grant, or too few GPUs returns `403` with the reason.

**Verify:** the project opens with a **Generate the starter code** panel that
shows the scaffold command, for example:

```bash
kionga scaffold churn-model --template production-ml --template-version 1.0.0 \
  --framework xgboost --accelerator cpu --profile team
```

## Create a GPU training project

Use `distributed-training` for PyTorch DDP workloads that need one or more
GPUs.

1. Make sure your grant has the GPUs the accelerator asks for: `single-gpu`
   needs at least one GPU and `multi-gpu` at least two, which usually means an
   administrator gives you the **GPU** or a **Custom** resource profile.
2. Create the project:

    ```python
    project = client.create_project(
        "foundation-model-evaluation",
        template="distributed-training",
        framework="pytorch-ddp",
        accelerator="multi-gpu",
        requested_profile="custom",
        repository_url="git@github.com:acme/foundation-model-evaluation.git",
    )
    print(project.scaffold_command)
    ```

3. [Scaffold the project](scaffolding.md) with the returned command.

The generated starter is shaped for production training:

- `torchrun` launches the PyTorch DDP processes, and the training module stays
  importable and testable without a cluster.
- Device and world-size settings come from the environment.
- Mixed precision is configurable, and a CPU path with `world_size=1` keeps smoke
  tests portable.
- Checkpoints go to workspace or object-store paths, so workers can resume after
  preemption.
- Only rank zero writes shared MLflow metadata and the final model artifacts.
- The pipeline manifest declares CPU, memory, GPU, retries and dependencies for
  each job.

A project's template never bypasses your grant, quotas, node capacity or the
cluster scheduler. When a normal user saves a pipeline, Kionga rejects it if the
widest set of jobs that can run at the same time needs more CPU, memory or GPUs
than the grant provides. Multi-node training runs on Kubernetes with a GPU
operator, a suitable storage class and a workload scheduler. Creating a
`multi-gpu` project on a laptop records the intent; it does not create GPUs.

**Verify:** the project record shows **Accelerator** `multi-gpu` and **Requested
profile** `custom`.

## Create an agent project

Use `production-agent` for a LangGraph agent you plan to deploy.

1. Create the project:

    ```python
    project = client.create_project(
        "incident-response-agent",
        template="production-agent",
        framework="langgraph",
        accelerator="cpu",
    )
    ```

2. Run `project.scaffold_command` in a workspace terminal. To let a coding agent
   extend the generated starter, add `--agent` and `--prompt`:

    ```bash
    kionga scaffold incident-response-agent \
      --template production-agent \
      --template-version 1.0.0 \
      --framework langgraph \
      --accelerator cpu \
      --profile team \
      --agent codex \
      --prompt "Add a read-only runbook search tool and escalation policy"
    ```

The starter runs before you change it. It includes a graph entry point, typed
state, a safe example tool, deterministic tests, an HTTP runtime with health and
invocation routes, container packaging, golden evaluation cases and a
deployable agent manifest. Provider keys stay in your environment, never in the
generated code.

**Verify:** the project page shows `PROJECT · production-agent v1.0.0`. After
you scaffold it, install the project with `python -m pip install -e ".[dev]"`
and run `pytest -q` in the generated folder: the tests use an offline model and
need no provider keys.

## What the scaffold generates

Every template generates a typed package, `pyproject.toml`, a Dockerfile,
`.env.example`, tests, a CI workflow with Ruff and `pytest`, `platform/project.yaml`,
an immutable `.kionga/template.json` record of the template choice, and a new
Git repository when `git` is available. Each template adds its own workload:

| Template | Adds |
| --- | --- |
| `production-ml` | Framework-specific training, model and metric output, a registration hook, a prediction API, tests and a pipeline manifest |
| `distributed-training` | A PyTorch DDP worker, a `torchrun` launcher, a CPU smoke path, mixed precision, resumable rank-zero checkpoints, rank-zero MLflow logging, tests and a container pipeline definition |
| `production-agent` | A LangGraph tool loop, a safe tool, an agent memory client, PostgreSQL or in-memory checkpoints, a Langfuse callback, an HTTP runtime, a deterministic graph test, a golden evaluation runner and an agent manifest with resources and replica limits |
| `fullstack-ai` | A FastAPI model or agent backend, a matching browser client, an event function with its Dockerfile, tests, an application container, CI and deployment requests |
| `blank-python` | A minimal typed, tested and container-ready Python service |

Scaffolding fails when the destination folder already has files, so it never
overwrites your work. To bring an existing repository into a workspace, use
`kionga project sync` instead (see
[Connect a project to Git](distributed-workspaces.md#connect-a-project-to-git)).

## Template aliases

The API accepts some older template names and stores the canonical ID instead:

| Alias | Canonical template |
| --- | --- |
| `tabular-classification`, `forecasting`, `ml` | `production-ml` |
| `rag-agent`, `agent` | `production-agent` |
| `fullstack` | `fullstack-ai` |
| `blank`, `python`, `api`, `function` | `blank-python` |

Use the canonical IDs in new automation.

## Next steps

- [Scaffold the project](scaffolding.md) into your workspace.
- [Connect the project to Git](distributed-workspaces.md#connect-a-project-to-git).
- [Build and deploy an agent](agents.md) from a `production-agent` project.
