# Python SDK & workload modules

Python owns the ML-facing surface: a typed SDK, the agent runtime, pipeline flows,
feature definitions, and the real-time demos. The package is `mlaiops-sdk`
(`sdk-python/pyproject.toml`), importable as `mlaiops_sdk`, with optional extras for the
heavier agent/runtime dependencies.

```bash
pip install -e ./sdk-python                 # core SDK
pip install -e "./sdk-python[agents]"       # + LangGraph/LangChain/Langfuse/psycopg
pip install -e "./sdk-python[runtime]"      # + FastAPI/Uvicorn (agent runtime)
```

## `mlaiops_sdk`: the client SDK

A small, typed entry point to the control plane. Core imports are light; heavy agent
dependencies load lazily only when used.

### `client.py`: `MLAIOpsClient`

The typed REST client. `MLAIOpsClient(base_url=None, *, token=None, actor=None,
timeout=10.0)` reads `MLAIOPS_URL` (default `http://localhost:8080`) and
`MLAIOPS_TOKEN` from the environment when the arguments are omitted, sends the
token as a bearer credential, and works as a context manager.

```python
from mlaiops_sdk import MLAIOpsClient

with MLAIOpsClient() as c:
    project = c.create_project("churn", template="production-ml",
                               framework="xgboost", accelerator="cpu")
    run = c.submit_pipeline(project.id)
    for model in c.list_models():
        c.promote_model(model.id, "production")
        c.deploy_model(model.id)
```

| Area | Methods |
| --- | --- |
| Health | `health()`, `readiness()` (onboarding readiness) |
| Projects | `list_project_templates()`, `get_project_template()`, `list_projects()`, `create_project()`, `get_project()`, `connect_repository()` |
| Pipelines | `submit_pipeline()`, `list_pipeline_runs()`, `get_pipeline_run()`, `cancel_pipeline_run()`, `retry_pipeline_run()`, `list_pipeline_definitions()`, `create_pipeline_definition()` |
| Functions | `list_functions()`, `deploy_function()`, `invoke_function()`, `invoke_function_async()`, `delete_function()` |
| Models | `list_models()`, `register_model(..., serving_image=...)`, `promote_model()`, `deploy_model()`, `rollback_model()`, `search_huggingface_models()`, `import_huggingface_model()` |
| Agents | `list_agents()`, resource/autoscaling-aware `deploy_agent()`, `invoke_agent()`, `set_agent_traffic()`, `agent_sessions()`, `agent_traces()` |
| Tools | `list_tools()`, `register_tool()` |
| Connections | `list_connections()`, `create_connection()`, `test_connection()` |
| Audit | `audit_events()` |

Inside Kionga's Jupyter or browser IDE workspace, `MLAIOPS_URL` is already set and
`MLAIOpsClient()` needs no personal key. Set `MLAIOPS_TOKEN` to a scoped personal
key when calling a hosted platform from your own machine. The gateway applies
the same current project/service grants to in-workspace SDK calls as to the console.

### `models.py`: typed resources

Pydantic models returned by the client: `ProjectTemplate`, `Project`, `GitRepository`,
`PipelineDefinition`, `PipelineRun`, `Function`, `Model`, `Agent`,
`AgentAutoscaling`, `AgentResources`, `AgentSession`, `AgentTrace`, `Tool`,
`Connection`, `Readiness`, `AuditEvent`.

`deploy_agent()` accepts fixed/minimum replicas, optional `max_replicas`, CPU and
memory quantities, GPU count, and GPU resource type. It sends the canonical nested
`autoscaling` and `resources` objects used by the console and Go API.

### `agents.py`: agent memory and checkpoints

- `get_langgraph_checkpointer()`: an `AsyncPostgresSaver` from
  `MLAIOPS_CHECKPOINT_DSN`/`DATABASE_URL` for durable session state.
- `AgentMemoryClient`: pgvector-backed long-term memory (`remember` / `recall`)
  plus `get_entity_features` via the feature gateway. Uses a deterministic
  `HashingEmbedder` so tests need no network.

### `llm.py`: LLM factory

- `build_chat_model(backend, model, *, base_url, api_key, temperature)`: returns
  a LangChain chat model for `openai`, `anthropic`, `openai-compatible`
  (alias `self-hosted`), or `mock`. The backend defaults to
  `MLAIOPS_LLM_BACKEND` (else `openai`). OpenAI-protocol backends use
  `MLAIOPS_LLM_BASE_URL`, which Compose points at the trace proxy; `anthropic`
  calls Anthropic directly.
- `MockChatModel`: a deterministic mock backend (supports scripted tool calls) so
  gate tests run offline and free.

### `tracing.py`: Langfuse integration

- `langfuse_handler()` / `LangfuseContext`: LangChain callback and LangGraph
  config wiring for tracing.
- `trace_llm(project)`: decorator that traces a function's LLM calls.
- `record_trace(...)`: posts a session summary to the gateway (`/api/v1/traces`).

### `tools.py`: tool registry

- `register_tool(...)`: register a callable as a platform tool.
- `to_langchain_tool()` / `langchain_tools(names)`: convert registered tools to
  LangChain `StructuredTool`s for agents.

### `agent_adapters.py`: framework adapters

`CallableAdapter`, `AgnoAdapter`, `NooaAdapter`, the `agent_factory` decorator,
and the `AgentRequest` / `AgentResult` contract. See
[framework adapters](https://kiongahq.github.io/docs/guides/agent-frameworks/).

### `huggingface.py`: Hub downloads

`connect()` (interactive Hub login) and `download_model()` (pinned-commit
snapshot download). Install the `huggingface` extra. See
[Hugging Face models](https://kiongahq.github.io/docs/guides/huggingface/).

### `pipelines.py`: pipeline compiler

Defines container `PipelineStep` and reusable `FunctionStep` jobs. `definition()`
compiles either form to the validated control-plane contract and infers function or
Prefect execution mode.

## `kionga`: workspace scaffolder

The workbench and optional IDE include the `kionga` command. It consumes the same
versioned template IDs as the API and creates deterministic production-ML,
distributed-training, production-agent, full-stack-AI, or blank expert starters.
It synchronizes project Git remotes and can hand only the bounded generated
directory to Codex, Claude Code, or a configured custom command. Credentials remain
in environment/config volumes rather than the generated repository.

The `distributed-training` starter separates a portable training function from
`torchrun` launch, rank-aware MLflow logging, mixed precision, and checkpoint
storage. The `production-agent` starter includes an executable graph/runtime,
tool loop, `AgentMemoryClient` boundary, selectable Postgres/in-memory checkpointing,
Langfuse callback, deterministic tests and evaluation runner, and container
packaging. See the [template catalog](https://kiongahq.github.io/docs/guides/project-templates/).

## `agent_runtime`: the agent service

The FastAPI service that serves LangGraph agents and framework-neutral adapters (see
[AI services](ai-observability.md#agent-runtime)).

| Module | Role |
| --- | --- |
| `app.py` | FastAPI app: `POST /invoke`, `POST /stream` (SSE), `GET /healthz`; wires checkpointer + memory + tracing; prefers per-request `X-MLAIOps-Agent-*` headers |
| `graphs.py` | `build_graph(spec, *, model, checkpointer)` handles compiled graphs, `StateGraph`, or factory callables |
| `reporting.py` | `Usage` (measured tokens → cost), `usage_from_messages`, `report_session` back to the gateway |
| `__main__.py` | Entrypoint |

## `agents`: demo agent

`agents.customer_support.graph:build` is a LangGraph `StateGraph`
(reason → tools → respond) with registered tools `feature_store_lookup` (feature
gateway, with a demo fallback) and `kb_search`. The Compose agent runtime serves
it by default (`MLAIOPS_GRAPH_MODULE`); register an agent record that points at it
to chat with it. `agents/framework_examples.py` holds the Agno, NOOA, and custom
adapter examples.

## `pipelines`: flow definitions (`pipeline-runner`)

| Module | Role |
| --- | --- |
| `training.py` | The `training_pipeline` flow: `validate → train → evaluate → register`; deterministic scikit-learn training; logs to MLflow; registers with the control plane |
| `definition.py` | The `pipeline-definition` flow: runs validated container DAGs with ready-set scheduling, retries, timeouts, and log streaming |
| `report.py` | `report_step` / `reported_step` report step transitions to the gateway; `LogShipper` streams container output |
| `serve.py` | Serves the flows as Prefect deployments (the pipeline-runner entrypoint) |

## `features`: feature store (`agent-runtime`)

| Module | Role |
| --- | --- |
| `definitions.py` | Feature views (`customer_profile`, `transaction_stats_5m`) with entity schemas and deterministic source rows |
| `materialize.py` | Applies definitions, writes the online store, snapshots Parquet to the object store, reports counts and lineage |
| `point_in_time.py` | `point_in_time_join` for leakage-free training sets |
| `retention.py` | Redis TTL and retention sweep (`python -m features.retention`) |

## `realtime`: real-time demos (`agent-runtime`)

| Module | Role |
| --- | --- |
| `service.py` | The consumer loop: poll Kafka → enrich → score → produce → report stats (resilient to REST timeouts) |
| `demos.py` | `score_fraud`, `analyze_transcript`, `recommend`, `get_features` |
| `kafka.py` | `KafkaRest` producer + `Consumer` (via the REST proxy, httpx only) |
| `produce.py` | CLI to produce demo events (`python -m realtime.produce --demo fraud --count 5`) |

## Tests

Each repository has its own `tests/` (`sdk-python`, `agent-runtime`,
`pipeline-runner`, `workspace`, `contracts`), and its CI runs `ruff check` and
`pytest -q`. Gate tests use the mock LLM and deterministic embedder: fast, free,
no network. The paid eval lane (LLM-as-judge) runs only when `MLAIOPS_RUN_EVALS=1`
with a real provider key.
