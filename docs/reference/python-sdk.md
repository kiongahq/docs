---
icon: material/language-python
description: Reference for the Kionga Python SDK, covering installation, configuration, every KiongaClient method, and the tracing, tools, pipeline, language model and agent helpers.
---

# Python SDK

The Python SDK is the `kionga` package (distribution name `kionga`). Use
it from notebooks, scripts, training jobs and agents to manage Kionga resources
and to build agents with tracing, tools, memory and a language model you choose.

```python
from kionga import KiongaClient

with KiongaClient() as client:
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
    pip install "kionga[agents] @ git+https://github.com/kiongahq/sdk-python.git"
    ```

    To pin the `v0.2.0` release instead:

    ```bash
    pip install "kionga[agents] @ https://github.com/kiongahq/sdk-python/archive/refs/tags/v0.2.0.tar.gz"
    ```

=== "From PyPI"

    PyPI publication is [on hold](https://github.com/kiongahq/sdk-python/issues/29)
    until a Kionga email is available. Use the GitHub installation above for now.

    After the first PyPI release is published, install the distribution with:

    ```bash
    python -m pip install "kionga[agents]"
    ```

    Check the [component changelog](../changelog.md) for available releases and
    pin the selected version in your dependency file. Until PyPI publication is
    configured and a release completes, use the GitHub installation above.

| Extra | Adds | Needed for |
| --- | --- | --- |
| *(none)* | `httpx`, `pydantic` | `KiongaClient`, `tracing`, `tools` registry, `pipelines` |
| `agents` | LangGraph, the LangGraph PostgreSQL checkpointer, LangChain with its OpenAI and Anthropic integrations, Langfuse, and `psycopg` | `build_chat_model`, `get_langgraph_checkpointer`, `AgentMemoryClient`, `langchain_tools`, Langfuse tracing |
| `huggingface` | `huggingface-hub` | `kionga.huggingface` |
| `agno` | Agno | Agno agents through `AgnoAdapter` |
| `nooa` | NOOA | NOOA agents through `NooaAdapter` |
| `runtime` | `agents` plus FastAPI and `uvicorn` | Running your own agent runtime |
| `dev` | `agents`, `huggingface`, `pytest`, `ruff` | Developing the SDK |

## Configure and authenticate

`KiongaClient()` reads its connection from the environment:

| Variable | Default | Purpose |
| --- | --- | --- |
| `KIONGA_URL` | `http://localhost:8080` | Kionga base URL. Used when you do not pass `base_url`. |
| `KIONGA_TOKEN` | *(unset)* | Personal API key, sent as `Authorization: Bearer <key>`. Used when you do not pass `token`. |
| `KIONGA_ALLOW_INSECURE_HTTP` | *(unset)* | Set to `1` to send the key over plain HTTP to a host the SDK would otherwise refuse. See [Plain HTTP](#plain-http). |

- **Inside a Kionga workspace** (Jupyter workbench or browser IDE), `KIONGA_URL`
  is preset to a workspace helper that signs your calls as the workspace owner.
  Do not set a token.
- **Outside Kionga**, set `KIONGA_URL` to your Kionga URL and `KIONGA_TOKEN` to
  a personal API key from **Settings → Personal API keys**. Keep the key in a
  secret manager or your OS keychain. A key acts as a normal `user` limited to
  its scopes; see [Personal API keys](rbac.md#personal-api-keys).

!!! note "Release v0.2.0 and `KIONGA_URL`"
    The `v0.2.0` release reads `KIONGA_TOKEN` but not `KIONGA_URL`. With that
    release, pass the URL explicitly: `KiongaClient("https://kionga.example.com")`.
    Installs from GitHub `main`, from your checkout, and in Kionga workspaces read
    both.

Other modules read these variables:

| Variable | Read by | Purpose |
| --- | --- | --- |
| `KIONGA_URL`, `KIONGA_TOKEN` | `tracing` | Where trace summaries are sent. Without `KIONGA_URL`, summaries are skipped. |
| `KIONGA_AGENT_ID`, `KIONGA_USER_ID`, `KIONGA_SESSION_ID` | `tracing` | Agent, user and session recorded on trace summaries |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` | `tracing` | Langfuse tracing. Without both keys, Langfuse is skipped. |
| `KIONGA_LLM_BACKEND` | `llm` | Default backend for `build_chat_model` (`openai` when unset) |
| `KIONGA_LLM_MODEL` | `llm` | Default model name |
| `KIONGA_LLM_BASE_URL`, then `OPENAI_BASE_URL` | `llm` | Base URL for OpenAI-protocol backends |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | `llm` | Provider keys |
| `KIONGA_CHECKPOINT_DSN`, then `DATABASE_URL` | `agents` | PostgreSQL for LangGraph checkpoints |
| `KIONGA_MEMORY_DSN`, then `DATABASE_URL` | `agents` | PostgreSQL with pgvector for long-term memory |
| `KIONGA_FEATURE_GATEWAY_URL` | `agents` | Online feature lookups |
| `HF_TOKEN` | `huggingface` | Hugging Face Hub token for non-interactive downloads |

## KiongaClient

```python
KiongaClient(
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
| `base_url` | Kionga base URL. Defaults to `KIONGA_URL`, then `http://localhost:8080`. |
| `token` | Personal API key. Defaults to `KIONGA_TOKEN`. |
| `actor` | Sent as the `X-Kionga-Actor` header. Kionga uses it for attribution only when the request has no authenticated identity. |
| `timeout` | Request timeout in seconds. `invoke_agent` has its own timeout. |
| `transport` | A custom `httpx` transport, for example for tests. |
| `allow_insecure_http` | `True` sends the key over plain HTTP to any host and logs a warning. `False` refuses even when `KIONGA_ALLOW_INSECURE_HTTP` is set. Defaults to that variable. |

### Plain HTTP {#plain-http}

The client raises `InsecureTransportError` when it has a key and the URL is plain
`http://` to another machine, because anyone on the network path could read the
key. `record_trace` skips the trace and logs a warning instead. Plain HTTP stays
allowed for loopback (`localhost`, `127.0.0.0/8`, `::1`) and for container and
cluster service names: a single-label host such as `gateway`, or a name ending in
`.svc` or `.svc.cluster.local`. Private addresses such as `192.168.1.20` are
refused. Use `https://` for them, or opt out on a network you trust.

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
| `agent_metrics(agent_id)` | Read live Kubernetes CPU and memory use for a managed agent, or `available: false`. |
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

All methods return Pydantic models from `kionga` (also importable from
`kionga.models`). Timestamps are `datetime` values.

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

Import from `kionga.tracing` (`trace_llm` and `LangfuseContext` are also
exported from `kionga`). Tracing never interrupts your code: if Kionga or
Langfuse is unreachable, the trace is dropped and your function still runs.

### `trace_llm(project)`

A decorator that records one trace summary per call: the function name, status
(`succeeded` or `failed`), duration, and `project`. It sets `KIONGA_TRACE_ID`
for the duration of the call and re-raises any exception.

```python
from kionga import trace_llm

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
from kionga import LangfuseContext

with LangfuseContext(project="support", session_id=session_id) as trace:
    result = graph.invoke(state, config=trace.langgraph_config)
    trace.score(name="user_rating", value=4.5)
```

`record_trace(payload)` sends a summary dictionary directly. It uses the same
best-effort delivery.

## Tools

Import from `kionga.tools` (`register_tool` is also exported from
`kionga`). The registry is local to your Python process.

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
from kionga import register_tool
from kionga.tools import langchain_tools

@register_tool(name="order_status", version="1.0", description="Look up an order")
def order_status(order_id: str) -> str:
    return "shipped"

tools = langchain_tools(["order_status"])
```

## Pipelines

`kionga.pipelines` builds pipeline definitions in Python.

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
from kionga.pipelines import Pipeline, PipelineStep, ResourceRequirements

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

`kionga.llm` builds a LangChain chat model for the configured provider
(needs the `agents` extra).

`build_chat_model(backend=None, model=None, *, base_url=None, api_key=None, temperature=0.0, **kwargs)`

| Backend | Model default | Requires |
| --- | --- | --- |
| `openai` | `gpt-4o` | `OPENAI_API_KEY` or `api_key` |
| `anthropic` | `claude-sonnet-4-5` | `ANTHROPIC_API_KEY` or `api_key` |
| `openai-compatible` | `default` | A base URL from `base_url`, `KIONGA_LLM_BASE_URL` or `OPENAI_BASE_URL` |
| `self-hosted` | `default` | Same as `openai-compatible` |
| `mock` | | Nothing. A deterministic model for tests. |

`backend` defaults to `KIONGA_LLM_BACKEND`, then `openai`. `model` defaults to
`KIONGA_LLM_MODEL`, then the backend default. Extra keyword arguments go to the
LangChain model. A missing key, URL or package raises `MissingLLMConfiguration`.

`MockChatModel(responses=None)` replies with the scripted responses in order and
repeats the last one. A response is a string or a tool call,
`{"tool_call": {"name": ..., "args": {...}}}`. Without a script, it replies
`[mock] acknowledged: <last message>`.

## Agent state and memory

`kionga.agents` needs the `agents` extra.

`get_langgraph_checkpointer(dsn=None)` returns the LangGraph PostgreSQL
checkpointer (an async context manager). The DSN defaults to
`KIONGA_CHECKPOINT_DSN`, then `DATABASE_URL`.

```python
from kionga import get_langgraph_checkpointer

async with get_langgraph_checkpointer() as saver:
    await saver.setup()
    app = graph.compile(checkpointer=saver)
```

`AgentMemoryClient(agent_name, session_id="", *, user_id=None, tenant_id="", dsn=None, feature_gateway_url=None, embedder=None)`
gives an agent long-term memory and feature lookups. Memory is isolated by tenant,
agent and user. Pass the authenticated user, never a value from model output or a
request body:

| Method | Description |
| --- | --- |
| `remember(text, *, metadata=None, scope="user")` | Stores a fact for this user and session in PostgreSQL with pgvector. Creates or upgrades the `agent_memories` table on first use. `scope="agent"` stores a fact with no owner. |
| `recall(query, *, top_k=3, scope="user")` | Returns the most similar memories as dictionaries with `text`, `metadata` and `score`. `user` reads this user's memories, `session` narrows to this session, and `agent` reads every memory of this agent and tenant. |
| `forget(*, user_id=None, session_id=None)` | Deletes one user's memories of this agent and tenant, optionally for one session, and returns the row count. A client bound to a user can delete only that user's rows. For a full erasure, run it once per agent. |
| `get_entity_features(entity_id, feature_view, *, timeout=5.0)` | Fetches online features for one entity from the feature gateway |
| `close()` | Closes the database connection. The client is also a context manager. |

`remember` and `recall` raise `MissingConfiguration` without a user, unless you
explicitly choose `scope="agent"`. `forget` always needs a user. Rows stored before
user scoping have no owner: they stay in the table, and only `scope="agent"` reads
them. Feature lookups need no user.

Memory uses `KIONGA_MEMORY_DSN`, then `DATABASE_URL`, and feature lookups use
`KIONGA_FEATURE_GATEWAY_URL`; a missing value raises `MissingConfiguration`. The
default embedding model, `HashingEmbedder`, is deterministic and runs offline. Pass any
object with an `embed(text) -> list[float]` method that returns 256 values to use
a different embedding.

## Other agent frameworks

`kionga.agent_adapters` lets agents built with other frameworks run behind
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

`kionga.huggingface` downloads models you imported into Kionga (needs the
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
