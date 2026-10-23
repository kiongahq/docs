---
description: Create a project, train and deploy a model, get a live prediction, and chat with an agent on your local Kionga stack.
---

# Quickstart

In this tutorial you use a running Kionga stack to create a project, train a
model with a real pipeline, deploy it to a live endpoint, request a prediction,
and chat with an agent. Each step shows the console, and most also show the
Python SDK and the REST API. All three call the same API, so you can mix them.

## Before you begin

- Install and start Kionga: follow [Install Kionga](installation.md). The
  console must open at <http://localhost:8080/console.html>.
- To use the SDK tabs, open the **Jupyter workbench** from the console sidebar,
  create a notebook, and run the snippets in order. The SDK is installed there and
  already connected to your Kionga, so you do not need an API key.
- To use the curl tabs, sign in once from a terminal and keep the session cookie:

    ```bash
    export MLAIOPS_URL="${MLAIOPS_URL:-http://localhost:8080}"
    curl -fsS "$MLAIOPS_URL/api/v1/health"
    curl -fsS -o /dev/null -c kionga.cookies \
      --data-urlencode username=admin --data-urlencode password=mlaiops-local \
      "$MLAIOPS_URL/auth/local/login"
    curl -fsS -b kionga.cookies "$MLAIOPS_URL/api/v1/me"
    ```

    The health check returns `{"status":"ok",...}` and needs no sign-in. The last
    command returns your identity. If the stack started on a different port, set
    `MLAIOPS_URL` to the console URL that `make -C deploy local-up` printed.

!!! note "Personal API keys"
    Scripts and tools that run outside Kionga authenticate with a personal API key
    from **Settings → Personal API keys**, exported as `MLAIOPS_TOKEN`. A key acts
    as a normal `user`, limited to the services and projects it names and to its
    creator's provisioned access profile. The local `admin` account has no access
    profile until an administrator provisions one, so its keys cannot create
    projects. This tutorial uses the console session instead. See
    [Personal API keys](../reference/rbac.md#personal-api-keys).

## Step 1: Sign in

Open <http://localhost:8080/console.html> and sign in with the local account
`admin` and password `mlaiops-local`.

The console opens on **Overview**.

## Step 2: Create a project

A project owns everything you build in this tutorial.

=== "Console"

    1. Open **Projects** and click **＋ New project**.
    2. Enter the name `churn`.
    3. Choose the **Production ML system** template, the `scikit-learn`
       framework, and the `cpu` accelerator.
    4. Click **Create project**.

=== "SDK"

    ```python
    from mlaiops_sdk import MLAIOpsClient

    client = MLAIOpsClient()
    project = client.create_project(
        "churn",
        template="production-ml",
        framework="scikit-learn",
        accelerator="cpu",
    )
    print(project.id, project.template_version)
    ```

=== "curl"

    ```bash
    curl -s -b kionga.cookies -X POST "$MLAIOPS_URL/api/v1/projects" \
      -H 'Content-Type: application/json' \
      -d '{"name":"churn","template":"production-ml","framework":"scikit-learn","accelerator":"cpu"}'
    ```

The project appears in **Projects**. The response includes its `id`, the pinned
template version, and a `scaffold_command` that generates starter code for the
project. To compare templates, see [Project templates](../guides/project-templates.md).

## Step 3: Train a model with a pipeline

The built-in training pipeline validates a dataset, trains a scikit-learn model,
evaluates it, and registers it in your project as `churn-classifier`.

=== "Console"

    1. Open **Pipelines** and click **▶ Run pipeline**.
    2. Select the `churn` project and keep **Built-in training pipeline** as the flow.
    3. Click **Check run**, then **Start run**.
    4. Open the run in the **Runs** table to follow each step.

=== "SDK"

    ```python
    import time

    run = client.submit_pipeline(project.id)
    while run.status not in ("succeeded", "failed", "cancelled"):
        time.sleep(3)
        run = client.get_pipeline_run(run.id)
    print(run.id, run.status)
    ```

=== "curl"

    ```bash
    curl -s -b kionga.cookies -X POST "$MLAIOPS_URL/api/v1/pipelines/submit" \
      -H 'Content-Type: application/json' \
      -d '{"project_id":"<project-id>","name":"training-pipeline"}'
    curl -s -b kionga.cookies "$MLAIOPS_URL/api/v1/pipelines/runs/<run-id>"
    ```

The run moves through `validate-data`, `train-model`, `evaluate`, and
`register-model`, then reports `succeeded`. The trained model and its metrics are
also in MLflow at <http://localhost:15000>. If a step fails, open its log in the
run view to see the error.

## Step 4: Deploy the model

=== "Console"

    1. Open **Models** and find the `churn-classifier` card for your project. Its
       quality gate shows `passed`.
    2. Click **Promote** to move it to the `production` stage.
    3. Click **Deploy**.

=== "SDK"

    ```python
    model = next(m for m in client.list_models()
                 if m.name == "churn-classifier" and m.project_id == project.id)
    client.promote_model(model.id, stage="production")
    model = client.deploy_model(model.id)
    print(model.deployment_status, model.endpoint_url)
    ```

=== "curl"

    ```bash
    curl -s -b kionga.cookies "$MLAIOPS_URL/api/v1/models"
    curl -s -b kionga.cookies -X POST "$MLAIOPS_URL/api/v1/models/<model-id>/promote" \
      -H 'Content-Type: application/json' -d '{"stage":"production"}'
    curl -s -b kionga.cookies -X POST "$MLAIOPS_URL/api/v1/models/<model-id>/deploy" \
      -H 'Content-Type: application/json' -d '{"canary_weight":0}'
    ```

Kionga starts a model server for this version. The model's deployment status
becomes `serving` and the card shows a **live** tag and a **Test** button.
Kionga deploys only models whose quality gate passed.

## Step 5: Request a prediction

The model expects rows of 12 numeric features.

=== "Console"

    Click **Test** on the model card and send the sample payload.

=== "curl"

    ```bash
    curl -s -b kionga.cookies -X POST "$MLAIOPS_URL/api/v1/models/<model-id>/predict" \
      -H 'Content-Type: application/json' \
      -d '{"inputs": [[0.1,-1.2,0.5,2.0,0.3,-0.7,1.1,0.0,-0.4,0.9,-1.5,0.2]]}'
    ```

The response has this shape; the predicted class depends on the model:

```json
{"predictions": [1]}
```

The model server needs a short time to start after you deploy. If the first
request fails, wait a few seconds and send it again.

## Step 6: Chat with an agent {#talk-to-an-agent}

The local stack includes a customer-support agent built with LangGraph. Register
it in your project, then talk to it.

=== "Console"

    1. Open **Agents** and click **＋ Deploy agent**.
    2. Select the `churn` project and set the agent name to `customer-support`.
    3. Keep the default image `mlaiops/agent-runtime:latest`, graph module
       `agents.customer_support.graph:build`, and LLM backend **Mock**.
    4. Click **Deploy agent**.
    5. When the agent shows as ready, click **Chat** and ask
       `When are invoices issued?`.

=== "SDK"

    ```python
    agent = client.deploy_agent(
        project.id, "customer-support", "1.0",
        image="mlaiops/agent-runtime:latest",
        graph_module="agents.customer_support.graph:build",
    )
    reply = client.invoke_agent(agent.id, "When are invoices issued?")
    print(reply["reply"], reply["session_id"])
    ```

The agent answers, and the **Sessions** table records the conversation with its
turns and token usage. The local stack uses the `mock` language model, so the
reply starts with `[mock]` and needs no provider key. To use a real provider,
see [Using a real LLM](../guides/agents.md#using-a-real-llm).

!!! note "One shared agent runtime"
    On the local stack, every agent runs on one shared runtime that serves
    `agents.customer_support.graph:build` with the language model set by
    `MLAIOPS_LLM_BACKEND`. Kionga records the image and backend you choose, but uses
    them only on Kubernetes, where each agent gets its own runtime.

## What you built

You created a project, trained and registered a model with a real pipeline,
deployed it to a live endpoint, requested a prediction, and held a traced
conversation with an agent. Every action is in the audit log, and the
**Overview** page summarizes your work.

## Next steps

- Build your own flows: [Pipelines](../guides/pipelines.md).
- Work in notebooks: [Jupyter workbench](../guides/workbench.md).
- Serve your own models: [Models and serving](../guides/models-serving.md).
- Write your own agent: [Agents](../guides/agents.md).
- Explore online features and real-time scoring: [Features](../guides/features.md)
  and [Real-time processing](../guides/realtime.md).
- Automate Kionga: [Python SDK](../reference/python-sdk.md),
  [REST API](../reference/api.md), and [CLI](../reference/cli.md).
