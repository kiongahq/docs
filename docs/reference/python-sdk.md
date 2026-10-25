---
icon: material/language-python
description: Reference for the Kionga Python SDK, covering installation, configuration, every MLAIOpsClient method, and the tracing, tools, pipeline, language model and agent helpers.
---

# Python SDK

The Python SDK is the `mlaiops_sdk` package (distribution name `mlaiops-sdk`). Use
it from notebooks, scripts, training jobs and agents to manage Kionga resources
and to build agents with tracing, tools, memory and a language model you choose.

```python
from mlaiops_sdk import MLAIOpsClient

with MLAIOpsClient() as client:
    project = client.create_project("customer-churn", template="production-ml")
    run = client.submit_pipeline(project.id)
    print(run.id, run.status)
```

This page describes version `0.2.0` and later. For how the package is organized
internally, see
[Python modules in the engineering handbook](https://kiongahq.github.io/docs/engineering/components/python-modules/).

## Install

The SDK requires Python 3.11 or later. Its core dependencies are `httpx` and
`pydantic`.

=== "Jupyter workbench and IDE"

    The SDK is already installed, with the `agents` and `huggingface` extras.

=== "From your workspace checkout"

    ```bash
    pip install -e "./sdk-python[agents]"
    ```

=== "From GitHub"

    ```bash
    pip install "mlaiops-sdk[agents] @ git+https://github.com/kiongahq/sdk-python.git"
    ```

    To pin the `v0.2.0` release instead:

    ```bash
    pip install "mlaiops-sdk[agents] @ https://github.com/kiongahq/sdk-python/archive/refs/tags/v0.2.0.tar.gz"
    ```

The package is not published on PyPI.

| Extra | Adds | Needed for |
| --- | --- | --- |
| *(none)* | `httpx`, `pydantic` | `MLAIOpsClient`, `tracing`, `tools` registry, `pipelines` |
| `agents` | LangGraph, the LangGraph PostgreSQL checkpointer, LangChain with its OpenAI and Anthropic integrations, Langfuse, and `psycopg` | `build_chat_model`, `get_langgraph_checkpointer`, `AgentMemoryClient`, `langchain_tools`, Langfuse tracing |
| `huggingface` | `huggingface-hub` | `mlaiops_sdk.huggingface` |
| `agno` | Agno | Agno agents through `AgnoAdapter` |
| `nooa` | NOOA | NOOA agents through `NooaAdapter` |
| `runtime` | `agents` plus FastAPI and `uvicorn` | Running your own agent runtime |
| `dev` | `agents`, `huggingface`, `pytest`, `ruff` | Developing the SDK |

## Configure and authenticate

`MLAIOpsClient()` reads its connection from the environment:

| Variable | Default | Purpose |
| --- | --- | --- |
| `MLAIOPS_URL` | `http://localhost:8080` | Kionga base URL. Used when you do not pass `base_url`. |
| `MLAIOPS_TOKEN` | *(unset)* | Personal API key, sent as `Authorization: Bearer <key>`. Used when you do not pass `token`. |

- **Inside a Kionga workspace** (Jupyter workbench or browser IDE), `MLAIOPS_URL`
  is preset to a workspace helper that signs your calls as the workspace owner.
  Do not set a token.
- **Outside Kionga**, set `MLAIOPS_URL` to your Kionga URL and `MLAIOPS_TOKEN` to
  a personal API key from **Settings → Personal API keys**. Keep the key in a
  secret manager or your OS keychain. A key acts as a normal `user` limited to
  its scopes; see [Personal API keys](rbac.md#personal-api-keys).

!!! note "Release v0.2.0 and `MLAIOPS_URL`"
    The `v0.2.0` release reads `MLAIOPS_TOKEN` but not `MLAIOPS_URL`. With that
    release, pass the URL explicitly: `MLAIOpsClient("https://kionga.example.com")`.
    Installs from GitHub `main`, from your checkout, and in Kionga workspaces read
    both.

Other modules read these variables:

| Variable | Read by | Purpose |
| --- | --- | --- |
| `MLAIOPS_URL`, `MLAIOPS_TOKEN` | `tracing` | Where trace summaries are sent. Without `MLAIOPS_URL`, summaries are skipped. |
| `MLAIOPS_AGENT_ID`, `MLAIOPS_USER_ID`, `MLAIOPS_SESSION_ID` | `tracing` | Agent, user and session recorded on trace summaries |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` | `tracing` | Langfuse tracing. Without both keys, Langfuse is skipped. |
| `MLAIOPS_LLM_BACKEND` | `llm` | Default backend for `build_chat_model` (`openai` when unset) |
| `MLAIOPS_LLM_MODEL` | `llm` | Default model name |
| `MLAIOPS_LLM_BASE_URL`, then `OPENAI_BASE_URL` | `llm` | Base URL for OpenAI-protocol backends |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | `llm` | Provider keys |
| `MLAIOPS_CHECKPOINT_DSN`, then `DATABASE_URL` | `agents` | PostgreSQL for LangGraph checkpoints |
| `MLAIOPS_MEMORY_DSN`, then `DATABASE_URL` | `agents` | PostgreSQL with pgvector for long-term memory |
| `MLAIOPS_FEATURE_GATEWAY_URL` | `agents` | Online feature lookups |
| `HF_TOKEN` | `huggingface` | Hugging Face Hub token for non-interactive downloads |

## MLAIOpsClient

```python
MLAIOpsClient(
    base_url: str | None = None,
    *,
    token: str | None = None,
    actor: str | None = None,
    timeout: float = 10.0,
    transport: httpx.BaseTransport | None = None,
)
```

| Parameter | Description |
| --- | --- |
| `base_url` | Kionga base URL. Defaults to `MLAIOPS_URL`, then `http://localhost:8080`. |
| `token` | Personal API key. Defaults to `MLAIOPS_TOKEN`. |
| `actor` | Sent as the `X-MLAIOps-Actor` header. Kionga uses it for attribution only when the request has no authenticated identity. |
| `timeout` | Request timeout in seconds. `invoke_agent` has its own timeout. |
| `transport` | A custom `httpx` transport, for example for tests. |

The client is a context manager; `close()` releases its connections. Every method
raises `httpx.HTTPStatusError` when Kionga returns an error status. The error
body is JSON with `error` and `message` fields; see
[REST API errors](api.md#conventions).

### Projects

| Method | Returns | API call |
| --- | --- | --- |
| `list_projects()` | `list[Project]` | `GET /api/v1/projects` |
| `get_project(project_id)` | `Project` | `GET /api/v1/projects/{id}` |
| `create_project(name, *, description="", template="production-ml", template_version="", framework="", accelerator="", requested_profile="", repository_url="", default_branch="main")` | `Project` | `POST /api/v1/projects` |
| `connect_repository(project_id, url, *, default_branch="main")` | `Project` | `PUT /api/v1/projects/{id}/repository` |
| `list_project_templates()` | `list[ProjectTemplate]` | `GET /api/v1/project-templates` |
| `get_project_template(template_id, *, version="")` | `ProjectTemplate` | `GET /api/v1/project-templates/{id}` |

Empty `framework`, `accelerator` and `requested_profile` take the template's
defaults. See [Project templates](../guides/project-templates.md).

### Pipelines

| Method | Returns | API call |
| --- | --- | --- |
| `submit_pipeline(project_id, name="training-pipeline", *, definition_id="", parameters=None)` | `PipelineRun` | `POST /api/v1/pipelines/submit` |
| `list_pipeline_runs()` | `list[PipelineRun]` | `GET /api/v1/pipelines/runs` |
| `get_pipeline_run(run_id)` | `PipelineRun` | `GET /api/v1/pipelines/runs/{id}` |
| `cancel_pipeline_run(run_id)` | `PipelineRun` | `POST /api/v1/pipelines/runs/{id}/cancel` |
| `retry_pipeline_run(run_id)` | `PipelineRun` | `POST /api/v1/pipelines/runs/{id}/retry` |
| `list_pipeline_definitions()` | `list[PipelineDefinition]` | `GET /api/v1/pipelines/definitions` |
| `create_pipeline_definition(project_id, name, version, jobs, *, execution_mode="prefect", repository_url="", commit_sha="")` | `PipelineDefinition` | `POST /api/v1/pipelines/definitions` |

Without `definition_id`, `submit_pipeline` runs the built-in training pipeline.
A run's `status` is `queued`, `running`, `succeeded`, `failed` or `cancelled`.

```python
import time

run = client.submit_pipeline(project.id)
while run.status not in ("succeeded", "failed", "cancelled"):
    time.sleep(3)
    run = client.get_pipeline_run(run.id)
```

### Models

| Method | Returns | API call |
| --- | --- | --- |
| `list_models()` | `list[Model]` | `GET /api/v1/models` |
| `register_model(project_id, name, version, artifact_uri, *, metrics=None, serving_image=None)` | `Model` | `POST /api/v1/models` |
| `promote_model(model_id, stage)` | `Model` | `POST /api/v1/models/{id}/promote` |
| `deploy_model(model_id, *, canary_weight=0)` | `Model` | `POST /api/v1/models/{id}/deploy` |
| `rollback_model(model_id)` | `Model` | `POST /api/v1/models/{id}/rollback` |
| `search_huggingface_models(search="", *, task="")` | `list[dict]` | `GET /api/v1/models/huggingface` |
| `import_huggingface_model(project_id, repo_id, *, revision="main")` | `Model` | `POST /api/v1/models/huggingface/import` |

`stage` is `staging`, `production` or `archived`. A model reaches `production`
and can be deployed only when its quality gate is `passed`; see
[Quality gates and promotion](../concepts/core-concepts.md#quality-gates-and-promotion).
To request a prediction, call `POST /api/v1/models/{id}/predict` through the
[REST API](api.md#models).

### Agents

| Method | Returns | API call |
| --- | --- | --- |
| `list_agents()` | `list[Agent]` | `GET /api/v1/agents` |
| `deploy_agent(project_id, name, version, image, graph_module, *, llm_backend="mock", replicas=1, max_replicas=None, cpu="500m", memory="1Gi", gpu=0, gpu_type="nvidia.com/gpu", tools=None)` | `Agent` | `POST /api/v1/agents` |
| `invoke_agent(agent_id, message, *, session_id="", user_id="", timeout=120.0)` | `dict` | `POST /api/v1/agents/{id}/invoke` |
| `set_agent_traffic(agent_id, canary_weight)` | `Agent` | `PUT /api/v1/agents/{id}/traffic` |
| `agent_sessions(agent_id)` | `list[AgentSession]` | `GET /api/v1/agents/{id}/sessions` |
| `agent_traces(agent_id)` | `list[AgentTrace]` | `GET /api/v1/agents/{id}/traces` |

`deploy_agent` sends `replicas` as the minimum and `max_replicas` (default: the
same as `replicas`) as the maximum replica count. `gpu_type` is sent only when
`gpu` is greater than `0`. `tools` names tools already registered in Kionga.

`invoke_agent` returns the runtime's reply: `reply`, `session_id`,
`input_tokens`, `output_tokens`, `usage_available`, `cost_usd` and `duration_ms`.
Pass the returned `session_id` to continue the same conversation:

```python
first = client.invoke_agent(agent.id, "When are invoices issued?")
follow_up = client.invoke_agent(agent.id, "And refunds?", session_id=first["session_id"])
print(follow_up["reply"])
```

When the agent's runtime is not ready, Kionga answers `503` with
`agent_not_ready` and the call raises `httpx.HTTPStatusError`.

### Langflow and project resources

The SDK can discover the same project-scoped resources as the Langflow canvas.
These methods return JSON dictionaries; Kionga filters the catalogs and checks
access again for each operation. Connection credentials remain on the gateway.

| Method | Purpose |
| --- | --- |
| `list_knowledge_bases()` | List authorized Qdrant and pgvector bases. |
| `list_datasets()` | List project datasets in authorized storage buckets. |
| `list_dataset_objects(dataset_id, *, prefix="")` and `preview_dataset_object(dataset_id, key)` | Browse and preview data within a registered dataset prefix. |
| `list_registered_storage()` | Discover existing project-authorized S3-compatible connections. |
| `list_registered_objects(source_id, *, prefix="")` and `preview_registered_object(source_id, key)` | Browse and preview a registered source through the gateway. |
| `search_knowledge_base(base_id, vector, *, limit=5)` | Search with a matching embedding vector. |
| `add_knowledge_chunk(base_id, text, vector, *, metadata=None)` | Index one chunk. |
| `list_agent_api_connections()` | List approved project API operations without URLs or keys. |
| `invoke_agent_api_connection(connection_id, payload)` | Invoke one approved operation. |
| `list_langflow_flows(workspace_id)` | List saved flows in an assigned editor workspace. |
| `capture_langflow_flow(workspace_id, flow_id, project_id, *, snapshot_id="", revision=0)` | Capture a new or updated flow revision. |
| `list_langflow_snapshots()` and `get_langflow_snapshot(snapshot_id)` | Inspect version history and the active route. |
| `publish_langflow_snapshot(snapshot_id, *, revision=0, min_replicas=1, max_replicas=1, cpu="500m", memory="1Gi")` | Deploy a retained or current revision. |
| `activate_langflow_deployment(snapshot_id, agent_id)` | Switch the stable route to a ready deployment. |
| `invoke_langflow_snapshot(snapshot_id, message, *, session_id="", user_id="")` | Invoke the active revision. |

For example, after saving a flow in Langflow:

```python
snapshot = client.capture_langflow_flow("workspace-1", "flow-1", "prj-1")
agent = client.publish_langflow_snapshot(snapshot["id"], revision=snapshot["revision"])
# Wait until the deployment is ready before activation.
client.activate_langflow_deployment(snapshot["id"], agent["id"])
reply = client.invoke_langflow_snapshot(snapshot["id"], "Hello")
```

Publishing requires a Kubernetes-managed runtime. See the
[Langflow guide](../guides/langflow.md) for workspace setup and credentials.

### Tools, functions, connections and status

| Method | Returns | API call |
| --- | --- | --- |
| `list_tools()` | `list[Tool]` | `GET /api/v1/tools` |
| `register_tool(name, version, description, input_schema, *, tags=None)` | `Tool` | `POST /api/v1/tools` |
| `list_functions()` | `list[Function]` | `GET /api/v1/functions` |
| `deploy_function(project_id, name, image, *, cpu="500m", memory="512Mi", env_vars=None, annotations=None)` | `Function` | `POST /api/v1/functions` |
| `invoke_function(name, payload)` | `dict` | `POST /api/v1/functions/{name}/invoke` |
| `invoke_function_async(name, payload)` | `dict` | `POST /api/v1/functions/{name}/invoke-async` |
| `delete_function(name)` | `None` | `DELETE /api/v1/functions/{name}` |
| `list_connections()` | `list[Connection]` | `GET /api/v1/connections` |
| `create_connection(name, type, secret_ref, *, endpoint="")` | `Connection` | `POST /api/v1/connections` |
| `test_connection(connection_id)` | `Connection` | `POST /api/v1/connections/{id}/test` |
| `readiness()` | `Readiness` | `GET /api/v1/onboarding/readiness` |
| `audit_events()` | `list[AuditEvent]` | `GET /api/v1/audit` |
| `health()` | `dict` | `GET /api/v1/health` |

`client.register_tool` records a tool in Kionga's catalog. The
[`register_tool` decorator](#tools) registers a Python function locally so an
agent can call it. Creating and testing connections requires the `admin` or
`operator` role.

### Response models

All methods return Pydantic models from `mlaiops_sdk` (also importable from
`mlaiops_sdk.models`). Timestamps are `datetime` values.

| Model | Fields |
| --- | --- |
| `Project` | `id`, `name`, `description`, `template`, `template_version`, `framework`, `accelerator`, `requested_profile`, `capabilities`, `scaffold_command`, `namespace`, `status`, `created_at`, `owner_subject`, `repository` |
| `GitRepository` | `url`, `provider`, `default_branch`, `last_commit`, `synced_at` |
| `ProjectTemplate` | `id`, `version`, `name`, `category`, `description`, `frameworks`, `accelerators`, `capabilities`, `required_services`, `recommended_profile` |
| `PipelineRun` | `id`, `project_id`, `name`, `status`, `progress`, `created_at`, `updated_at`, `parent_run_id`, `engine_run_id`, `definition_id`, `execution_mode`, `parameters`, `steps`, `logs` |
| `PipelineDefinition` | `id`, `project_id`, `name`, `version`, `execution_mode`, `jobs`, `repository_url`, `commit_sha`, `created_at`, `updated_at` |
| `Model` | `id`, `project_id`, `name`, `version`, `stage`, `artifact_uri`, `serving_image`, `metrics`, `created_at`, `gate_status`, `deployment_status`, `canary_weight`, `endpoint_url`, `previous_stage`, `source` |
| `Agent` | `id`, `project_id`, `owner_subject`, `name`, `version`, `image`, `graph_module`, `llm_backend`, `status`, `endpoint_url`, `replicas`, `autoscaling`, `resources`, `canary_weight`, `tools`, `created_at` |
| `AgentAutoscaling` | `min_replicas`, `max_replicas` |
| `AgentResources` | `cpu`, `memory`, `gpu`, `gpu_type` |
| `AgentSession` | `id`, `agent_id`, `user_id`, `status`, `current_node`, `turns`, `input_tokens`, `output_tokens`, `cost_usd`, `started_at`, `updated_at` |
| `AgentTrace` | `id`, `agent_id`, `session_id`, `name`, `status`, `duration_ms`, `tokens`, `metadata`, `created_at` |
| `Tool` | `id`, `name`, `version`, `description`, `tags`, `input_schema`, `status`, `created_at` |
| `Function` | `name`, `project_id`, `image`, `status`, `replicas`, `env_vars`, `annotations`, `cpu`, `memory`, `created_at`, `updated_at` |
| `Connection` | `id`, `name`, `type`, `endpoint`, `secret_ref`, `status`, `created_at`, `checked_at`, `message` |
| `Readiness` | `percent`, `ready`, `items` (each with `key`, `label`, `status`, `description`, `action`) |
| `AuditEvent` | `id`, `action`, `resource`, `resource_id`, `actor`, `metadata`, `created_at` |

## Tracing

Import from `mlaiops_sdk.tracing` (`trace_llm` and `LangfuseContext` are also
exported from `mlaiops_sdk`). Tracing never interrupts your code: if Kionga or
Langfuse is unreachable, the trace is dropped and your function still runs.

### `trace_llm(project)`

A decorator that records one trace summary per call: the function name, status
(`succeeded` or `failed`), duration, and `project`. It sets `MLAIOPS_TRACE_ID`
for the duration of the call and re-raises any exception.

```python
from mlaiops_sdk import trace_llm

@trace_llm(project="support")
def answer(question: str) -> str:
    ...
```

### `LangfuseContext(project, *, session_id=None, user_id=None, agent_id=None)`

A context manager that connects LangChain and LangGraph runs to Langfuse and sends
a trace summary to Kionga when the block exits.

| Member | Description |
| --- | --- |
| `session_id` | The given session ID, or a new UUID |
| `langgraph_config` | A run config with `configurable.thread_id` set to the session and Langfuse session and user metadata; includes the Langfuse callback when configured |
| `callbacks` | The Langfuse callback handler in a list, or an empty list |
| `score(*, name, value)` | Records a score on the summary and, when configured, in Langfuse |

```python
from mlaiops_sdk import LangfuseContext

with LangfuseContext(project="support", session_id=session_id) as trace:
    result = graph.invoke(state, config=trace.langgraph_config)
    trace.score(name="user_rating", value=4.5)
```

`record_trace(payload)` sends a summary dictionary directly. It uses the same
best-effort delivery.

## Tools

Import from `mlaiops_sdk.tools` (`register_tool` is also exported from
`mlaiops_sdk`). The registry is local to your Python process.

| Name | Description |
| --- | --- |
| `register_tool(*, name, version, description, tags=None)` | Decorator. Registers a typed function and derives its JSON input schema from the type hints. Parameters without a default are required. Registering the same name and version twice raises `ValueError`. |
| `registered_tools()` | All registered `ToolDefinition` objects |
| `get_tool(name, version=None)` | One tool; without `version`, the highest registered version. Raises `KeyError` when missing. |
| `to_langchain_tool(definition)` | A LangChain `StructuredTool` for one definition (needs the `agents` extra) |
| `langchain_tools(names=None)` | LangChain tools for the named tools, or for every tool |

`ToolDefinition` has `name`, `version`, `description`, `tags`, `input_schema` and
`function`.

```python
from mlaiops_sdk import register_tool
from mlaiops_sdk.tools import langchain_tools

@register_tool(name="order_status", version="1.0", description="Look up an order")
def order_status(order_id: str) -> str:
    return "shipped"

tools = langchain_tools(["order_status"])
```

## Pipelines

`mlaiops_sdk.pipelines` builds pipeline definitions in Python.

| Class | Fields |
| --- | --- |
| `ResourceRequirements` | `cpu="500m"`, `memory="1Gi"`, `gpu=0` |
| `PipelineStep` | `name`, `image`, `command`, `depends_on=[]`, `environment={}`, `resources=ResourceRequirements()`, `retries=1` |
| `FunctionStep` | `name`, `function`, `depends_on=[]`, `environment={}`, `resources=ResourceRequirements()`, `retries=1` |
| `Pipeline` | `name`, `steps=[]` |

`Pipeline.add(step)` appends a step and returns the pipeline. It raises
`ValueError` for a duplicate step name or a dependency that is not already in the
pipeline. `Pipeline.definition(project_id, *, version="1", execution_mode=None, repository_url="", commit_sha="")`
returns the arguments for `create_pipeline_definition`. When you do not set
`execution_mode`, a pipeline made only of function steps uses `functions` and any
other uses `prefect`.

```python
from mlaiops_sdk.pipelines import Pipeline, PipelineStep, ResourceRequirements

pipeline = (
    Pipeline("nightly-train")
    .add(PipelineStep("prepare", "ghcr.io/acme/prepare@sha256:<digest>", ["python", "prepare.py"]))
    .add(PipelineStep(
        "train", "ghcr.io/acme/train@sha256:<digest>", ["python", "train.py"],
        depends_on=["prepare"], resources=ResourceRequirements(cpu="2", memory="8Gi"),
    ))
)
definition = client.create_pipeline_definition(**pipeline.definition(project.id))
run = client.submit_pipeline(project.id, definition_id=definition.id)
```

See [Pipelines](../guides/pipelines.md) for the YAML format and every flow option.

## Language models

`mlaiops_sdk.llm` builds a LangChain chat model for the configured provider
(needs the `agents` extra).

`build_chat_model(backend=None, model=None, *, base_url=None, api_key=None, temperature=0.0, **kwargs)`

| Backend | Model default | Requires |
| --- | --- | --- |
| `openai` | `gpt-4o` | `OPENAI_API_KEY` or `api_key` |
| `anthropic` | `claude-sonnet-4-5` | `ANTHROPIC_API_KEY` or `api_key` |
| `openai-compatible` | `default` | A base URL from `base_url`, `MLAIOPS_LLM_BASE_URL` or `OPENAI_BASE_URL` |
| `self-hosted` | `default` | Same as `openai-compatible` |
| `mock` | | Nothing. A deterministic model for tests. |

`backend` defaults to `MLAIOPS_LLM_BACKEND`, then `openai`. `model` defaults to
`MLAIOPS_LLM_MODEL`, then the backend default. Extra keyword arguments go to the
LangChain model. A missing key, URL or package raises `MissingLLMConfiguration`.

`MockChatModel(responses=None)` replies with the scripted responses in order and
repeats the last one. A response is a string or a tool call,
`{"tool_call": {"name": ..., "args": {...}}}`. Without a script, it replies
`[mock] acknowledged: <last message>`.

## Agent state and memory

`mlaiops_sdk.agents` needs the `agents` extra.

`get_langgraph_checkpointer(dsn=None)` returns the LangGraph PostgreSQL
checkpointer (an async context manager). The DSN defaults to
`MLAIOPS_CHECKPOINT_DSN`, then `DATABASE_URL`.

```python
from mlaiops_sdk import get_langgraph_checkpointer

async with get_langgraph_checkpointer() as saver:
    await saver.setup()
    app = graph.compile(checkpointer=saver)
```

`AgentMemoryClient(agent_name, session_id="", *, dsn=None, feature_gateway_url=None, embedder=None)`
gives an agent long-term memory and feature lookups:

| Method | Description |
| --- | --- |
| `remember(text, *, metadata=None)` | Stores a fact for this agent in PostgreSQL with pgvector. Creates the `agent_memories` table on first use. |
| `recall(query, *, top_k=3)` | Returns the most similar memories as dictionaries with `text`, `metadata` and `score` |
| `get_entity_features(entity_id, feature_view, *, timeout=5.0)` | Fetches online features for one entity from the feature gateway |
| `close()` | Closes the database connection. The client is also a context manager. |

Memory uses `MLAIOPS_MEMORY_DSN`, then `DATABASE_URL`, and feature lookups use
`MLAIOPS_FEATURE_GATEWAY_URL`; a missing value raises `MissingConfiguration`. The
default embedding model, `HashingEmbedder`, is deterministic and runs offline. Pass any
object with an `embed(text) -> list[float]` method that returns 256 values to use
a different embedding.

## Other agent frameworks

`mlaiops_sdk.agent_adapters` lets agents built with other frameworks run behind
Kionga's `graph_module` contract.

| Name | Description |
| --- | --- |
| `AgentRequest` | What your code receives: `message`, `session_id`, `user_id` |
| `AgentResult(reply, input_tokens=None, output_tokens=None)` | What your code returns. Give both token counts to report usage. |
| `CallableAdapter(run)` | Wraps a sync or async `run(AgentRequest) -> AgentResult` |
| `AgnoAdapter(factory)` | Wraps a factory that returns a new Agno agent or team per request |
| `NooaAdapter(factory, method)` | Wraps a factory that returns a NOOA object; calls its public async `method` with the message |
| `agent_factory(framework="custom")` | Decorator that marks a factory as framework-managed, so the runtime does not inject its own model or checkpointer |

Replies are returned whole, not streamed token by token. See
[Agent frameworks](../guides/agent-frameworks.md).

## Hugging Face

`mlaiops_sdk.huggingface` downloads models you imported into Kionga (needs the
`huggingface` extra).

| Function | Description |
| --- | --- |
| `connect(token=None)` | Signs this workspace in to the Hugging Face Hub (interactive when `token` is omitted) and returns the account details. Never stores a Git credential. |
| `download_model(model, *, token=None, cache_dir=None, allow_patterns=None, local_files_only=False)` | Downloads the exact commit recorded for an imported `Model` and returns the local snapshot directory. It does not import or run model code. |

`token=None` uses `HF_TOKEN` or the Hub sign-in saved in the workspace; `token=False`
downloads anonymously. See [Hugging Face models](../guides/huggingface.md).

## Related

- [REST API reference](api.md)
- [CLI reference](cli.md)
- [Quickstart](../getting-started/quickstart.md)
