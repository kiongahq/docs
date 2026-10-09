# Quickstart

This guide takes you from a new project to a running pipeline, a model endpoint,
and an agent conversation. Start the local stack with `make -C deploy local-up`
first. You can use the console, the SDK, or the
[Jupyter workbench](../guides/workbench.md); they use the same gateway API.

## Check the gateway

```bash
export MLAIOPS_URL="${MLAIOPS_URL:-http://localhost:8080}"
curl -fsS "$MLAIOPS_URL/api/v1/health"
curl -fsS "$MLAIOPS_URL/api/v1/me"
```

The health endpoint should return a JSON response with `status: "ok"`. Open the
URL printed by `local-up` and sign in to the console with the local development
account `admin` / `mlaiops-local`. The local API development principal is separate
from that browser session. If the gateway chose a different port, set
`MLAIOPS_URL` to the printed URL before using the API examples below.

## Create a project

=== "Console"

    Click **＋ New project**, choose a versioned template, framework, accelerator,
    and resource profile, then create it. You land in the Projects view.

=== "SDK"

    ```python
    from mlaiops_sdk import MLAIOpsClient

    with MLAIOpsClient(base_url="http://localhost:8080",
                       actor="you@example.com") as client:
        project = client.create_project(
            "churn",
            template="production-ml",
            framework="scikit-learn",
            accelerator="cpu",
        )
        print(project.id)
    ```

=== "curl"

    ```bash
    curl -s -X POST "$MLAIOPS_URL/api/v1/projects" \
      -H 'Content-Type: application/json' \
      -d '{"name":"churn","template":"production-ml","framework":"scikit-learn","accelerator":"cpu"}'
    ```

The response includes the resolved template and a `kionga scaffold ...` command.
To see the available templates:

```bash
curl -s "$MLAIOPS_URL/api/v1/project-templates" | python -m json.tool
```

For multi-GPU work choose `distributed-training` + `pytorch-ddp` + `multi-gpu`;
for a runnable LangGraph service choose `production-agent`. These selections record
intent but never bypass the administrator's CPU/RAM/GPU/service grants. See the
[project-template catalog](../guides/project-templates.md).

## Run a pipeline

=== "Console"

    Open **Pipelines**, select your project and the `training-pipeline` definition,
    then submit a run. The graph shows each step's current state. Dagre lays out
    the graph in the browser; Prefect executes the flow:
    `validate → train → evaluate → register`.

=== "SDK"

    ```python
    run = client.submit_pipeline(project.id, name="training-pipeline")
    print(run.id, run.status)          # queued
    # poll until it completes
    run = client.get_pipeline_run(run.id)
    ```

The training step fits a scikit-learn model, records it in MLflow, and registers
it against your project. Open the run to inspect each step and its logs. If a
step fails, use the node log to find the underlying error before retrying.

## Promote and deploy a model

=== "Console"

    Open **Models** and select the version created by the pipeline. Review its
    metrics and quality gate before choosing **Promote** and **Deploy**. The
    serving manager starts a model-serving container and reports its status.

=== "SDK"

    ```python
    models = client.list_models()
    model = models[0]
    client.promote_model(model.id, stage="production")
    client.deploy_model(model.id, canary_weight=0)
    ```

## Request a prediction

=== "Console"

    Open the deployed model and use **Test** to send a payload to its live
    endpoint. A successful response has the same shape as this example; the
    predicted value depends on the model:

    ```json
    {"predictions": [1]}
    ```

=== "curl"

    ```bash
    curl -s -X POST "$MLAIOPS_URL/api/v1/models/<model-id>/predict" \
      -H 'Content-Type: application/json' \
      -d '{"inputs": [[0.1,-1.2,0.5,2.0,0.3,-0.7,1.1,0.0,-0.4,0.9,-1.5,0.2]]}'
    ```

## Talk to an agent

The stack ships a customer-support agent (`agents.customer_support.graph:build`).

=== "Console"

    Open **Agents**, select the customer-support agent, and start a chat. The
    session view records the turn and any usage information the backend reports.

=== "SDK"

    ```python
    agents = client.list_agents()
    reply = client.invoke_agent(agents[0].id, message="When are invoices issued?")
    print(reply)
    ```

!!! note "Mock vs real LLM"
    The local stack defaults to a `mock` backend, so this step does not need a
    provider key. To use a real provider in development, configure
    `MLAIOPS_LLM_BACKEND` and its key as described in
    [Configuration](configuration.md#llm-providers). Do not reuse local secrets
    in a public deployment.

## Explore features, storage, and real-time data

- **Features:** the Feature Catalog shows `customer_profile` and
  `transaction_stats_5m` with online entity counts (served from Redis).
- **Storage:** browse object-store buckets (models, artifacts, features, …) and preview
  objects.
- **Real-time:** produce demo events and watch them scored live —

    ```bash
    docker compose -f deploy/compose.yaml exec jupyter \
      python -m realtime.produce --demo fraud --count 5
    ```

    Then open the **Real-Time** panel to see throughput, latency, and flagged events.

## Open the workbench

Open the **Jupyter workbench** from the console. It has a browser terminal and a
seeded `quickstart.ipynb` for exploring the platform in code. You can also use
the direct local URL <http://localhost:8888> with the development token
`mlaiops-local`. See the [workbench guide](../guides/workbench.md).

## Continue with Git and reusable flows

Connect a project to an HTTPS/SSH Git remote from its detail panel. Open
**Pipelines → Define flow** to persist a versioned container or function DAG with
resources, retries, parameters, and commit lineage. Functions become deployable and
invocable after an administrator configures `OPENFAAS_URL`; until then the console
correctly reports that serverless is not configured.

For a distributed team, an administrator provisions each OIDC subject under
**Users & access**, choosing services and a starter/team/power/GPU/custom resource
profile. Compose provides the shared workbench; Kubernetes reconciles those grants
into isolated `KiongaWorkspace` workloads.

## Where to go next

- [Connecting all services](../connecting-services.md) — the full connection map.
- [Models & serving](../guides/models-serving.md), [Agents](../guides/agents.md),
  [Feature store](../guides/features.md), [Real-time](../guides/realtime.md).
- [REST API reference](../reference/api.md) and [CLI](../reference/cli.md).
- [Implementation status](../reference/implementation-status.md) — bundled versus
  optional, external, and scale-path capabilities.
