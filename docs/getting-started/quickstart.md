# Quickstart

This guide takes you from a new project to a running pipeline, a model endpoint,
and an agent conversation. Start the local stack with `make -C deploy local-up`
first. You can use the console, the SDK, or the
[Jupyter workbench](../guides/workbench.md); they use the same gateway API.

## Check the gateway and sign in

```bash
export MLAIOPS_URL="${MLAIOPS_URL:-http://localhost:8080}"
curl -fsS "$MLAIOPS_URL/api/v1/health"
```

The health endpoint is public and returns `{"status":"ok",...}`. If the gateway
chose a different port, set `MLAIOPS_URL` to the URL that `local-up` printed.

Open that URL and sign in to the console with the local development account
`admin` / `mlaiops-local`. Every other API route requires a credential:

- **curl:** sign in once with the same local account and keep the session cookie.

    ```bash
    curl -fsS -o /dev/null -c kionga.cookies \
      --data-urlencode username=admin --data-urlencode password=mlaiops-local \
      "$MLAIOPS_URL/auth/local/login"
    curl -fsS -b kionga.cookies "$MLAIOPS_URL/api/v1/me"
    ```

- **SDK:** run the SDK examples in a notebook in the Jupyter workbench (open
  **Jupyter** from the console). The workbench's preconfigured `MLAIOPS_URL`
  forwards each call as the workspace owner, so no key is needed.

Personal API keys (**Settings → API keys**, exported as `MLAIOPS_TOKEN`) are for
the CLI, SDK, and scripts outside Kionga. A key acts as a normal `user`, limited
to the services it names and to its creator's provisioned access profile, so
the local bootstrap administrator cannot create projects with one until an
access profile is provisioned. See [RBAC and security](../reference/rbac.md#personal-api-keys).

## Create a project

=== "Console"

    Click **＋ New project**, choose a versioned template, framework, accelerator,
    and resource profile, then create it. You land in the Projects view.

=== "SDK"

    ```python
    from mlaiops_sdk import MLAIOpsClient

    client = MLAIOpsClient()  # uses the workbench's MLAIOPS_URL
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
    curl -s -b kionga.cookies -X POST "$MLAIOPS_URL/api/v1/projects" \
      -H 'Content-Type: application/json' \
      -d '{"name":"churn","template":"production-ml","framework":"scikit-learn","accelerator":"cpu"}'
    ```

The response includes the resolved template and a `kionga scaffold ...` command.
To see the available templates:

```bash
curl -s -b kionga.cookies "$MLAIOPS_URL/api/v1/project-templates" | python -m json.tool
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
    import time

    run = client.submit_pipeline(project.id, name="training-pipeline")
    while run.status not in ("succeeded", "failed"):
        time.sleep(3)
        run = client.get_pipeline_run(run.id)
    print(run.id, run.status)
    ```

The training step fits a scikit-learn model, records it in MLflow, and registers
it against your project as `churn-classifier`. Open the run to inspect each step and its logs. If a
step fails, use the node log to find the underlying error before retrying.

## Promote and deploy a model

=== "Console"

    Open **Models** and select the version created by the pipeline. Review its
    metrics and quality gate before choosing **Promote** and **Deploy**. The
    serving manager starts a model-serving container and reports its status.

=== "SDK"

    ```python
    model = next(m for m in client.list_models()
                 if m.name == "churn-classifier" and m.project_id == project.id)
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
    curl -s -b kionga.cookies -X POST "$MLAIOPS_URL/api/v1/models/<model-id>/predict" \
      -H 'Content-Type: application/json' \
      -d '{"inputs": [[0.1,-1.2,0.5,2.0,0.3,-0.7,1.1,0.0,-0.4,0.9,-1.5,0.2]]}'
    ```

## Talk to an agent

The agent runtime serves a customer-support graph
(`agents.customer_support.graph:build`). Register it as an agent in your project
once, then chat with it.

=== "Console"

    Open **Agents → Deploy agent**, choose your project, enter the name
    `customer-support`, version `1.0`, image `mlaiops/agent-runtime`, and graph
    entry point `agents.customer_support.graph:build`, then deploy. Select the
    agent and start a chat. The session view records the turn and any usage the
    backend reports.

=== "SDK"

    ```python
    agent = client.deploy_agent(
        project.id, "customer-support", "1.0",
        image="mlaiops/agent-runtime",
        graph_module="agents.customer_support.graph:build",
    )
    reply = client.invoke_agent(agent.id, message="When are invoices issued?")
    print(reply["reply"])
    ```

In Compose every agent record routes to the one shared runtime, so the image
field is recorded but not pulled.

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
- **Real-time:** produce demo events and watch them scored live:

    ```bash
    docker compose -f deploy/compose.yaml exec jupyter \
      python -m realtime.produce --demo fraud --count 5
    ```

    Then open the **Real-Time** panel to see throughput, latency, and flagged events.

## Open the workbench

Open the **Jupyter workbench** from the console. It has a browser terminal and a
seeded `quickstart.ipynb` for exploring the platform in code. For diagnostics,
Jupyter also listens on
<http://127.0.0.1:8888/workspaces/workbench/lab?token=mlaiops-local> (loopback
only). See the [workbench guide](../guides/workbench.md).

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

- [Connecting all services](../connecting-services.md): the full connection map.
- [Models & serving](../guides/models-serving.md), [Agents](../guides/agents.md),
  [Feature store](../guides/features.md), [Real-time](../guides/realtime.md).
- [REST API reference](../reference/api.md) and [CLI](../reference/cli.md).
- [Implementation status](../reference/implementation-status.md): bundled versus
  optional, external, and scale-path capabilities.
