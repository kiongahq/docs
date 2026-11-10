---
icon: material/puzzle-outline
description: Run agents built with Agno, NVIDIA-labs OO-Agents (NOOA) or your own framework on the Kionga agent runtime, through the same deployment API as LangGraph agents.
---

# Run agents built with other frameworks

Deploy an agent written with Agno, NVIDIA-labs OO-Agents (NOOA) or any other
Python framework, through the same agent record, `graph_module` field and API as
a LangGraph agent. Your factory returns an adapter, and the runtime calls it for
each turn. Kionga does not convert agents between frameworks, and no framework
code runs in the gateway: each runtime image brings its own code and
dependencies.

| Framework | Entry point | State and telemetry |
| --- | --- | --- |
| LangGraph | A compiled graph, or `build(model, checkpointer)` | Kionga's model factory, checkpoints and Langfuse callbacks |
| Agno | `AgnoAdapter(factory)` | Passes the session and user IDs to `arun`, and reports Agno's token metrics |
| NOOA | `NooaAdapter(factory, "method")` | Calls one async method; reports no token counts and stores no state |
| Any other | `CallableAdapter(run)` | Plain request and result; your handler owns provider calls and persistence |

The `production-agent` template generates LangGraph. For another framework, add
your own module to the project and image.

## Before you begin

- The permissions in [Build and deploy an agent](agents.md#before-you-begin).
- A runtime image that contains your module and your framework's dependencies.
- Provider credentials delivered through your deployment's environment or
  secret manager. The agent form does not accept secret values.

## Write an adapter for your framework

1. Write a factory that returns an adapter. This example runs offline:

    ```python
    from kionga.agent_adapters import AgentResult, CallableAdapter, agent_factory

    @agent_factory("my-framework")
    def build():
        async def run(request):
            # request.message, request.session_id, request.user_id
            # Call your framework here.
            return AgentResult(reply=f"Received: {request.message}")
        return CallableAdapter(run)
    ```

2. Point the runtime at it with `KIONGA_GRAPH_MODULE=my_project.agent:build`.

The `@agent_factory` decorator tells the runtime not to build a LangChain model or
a LangGraph checkpointer, so your factory owns its provider and state. Choosing an
LLM backend in the console does not configure another framework's client.

How the adapter behaves:

- Handlers can be `async` or regular functions; regular functions run on a worker
  thread.
- A reply can be text, a JSON-serializable value or a Pydantic object.
- Set `input_tokens` and `output_tokens` only when you measured them. Without
  them, the turn reports `usage_available=false`, and cost uses your configured
  per-token rates, not a provider bill.
- Replies are buffered. The `/stream` route announces `streaming_mode=buffered`,
  sends the completed reply as one delta, and then a summary. LangGraph keeps its
  incremental streaming.
- Native tool events, vendor trace trees, async generators, image or audio inputs and
  interactive approval pauses are not mapped automatically.

**Verify:** a chat turn with the agent returns `Received: <your message>`.

## Run an Agno agent

The ready-made factory `agents.framework_examples:build_agno` uses Agno's OpenAI
client. Replace it for other Agno providers, teams or tools. Each request gets a
fresh Agno object with explicit `session_id` and `user_id`.

1. Install the integration where you develop:

    ```bash
    pip install './sdk-python[runtime,agno]'
    ```

2. On Compose, add the runtime settings to `deploy/.env` (never committed):

    ```dotenv
    AGENT_RUNTIME_EXTRAS=runtime,agno
    KIONGA_GRAPH_MODULE=agents.framework_examples:build_agno
    AGNO_MODEL=your-provider-model-id
    # Set your provider key as LLM_UPSTREAM_API_KEY too; never put it in an image
    # or a contract. See "Project keys" in the agents guide.
    ```

3. Rebuild and recreate the runtime:

    ```bash
    docker compose -f deploy/compose.yaml up -d --build agent-runtime
    ```

4. [Deploy the agent](agents.md#deploy-an-agent) with the same graph module,
   `agents.framework_examples:build_agno`.

The Compose runtime serves one configured factory. It rejects a request for an
agent whose entry point differs, instead of silently running the demo agent.

The example keeps no history between calls. For durable conversation history,
configure Agno's own database in your factory. Kionga's turn records are for
observability, not a replacement for framework memory.

**Verify:** the agent reaches `ready`, and **Chat** returns a reply from your
Agno model.

## Run a NOOA agent

The example factory `agents.framework_examples:build_nooa` wraps an object whose
async `answer(message)` method NOOA runs. NOOA executes Python code that the
model writes, so the factory fails closed.

!!! warning "Code execution is turned off"
    `build_nooa` refuses to start in every environment, because Kionga does not
    yet provide a sandbox for model-written code. No setting turns it on:
    `KIONGA_ALLOW_CODE_EXECUTION` is no longer read. Kionga's standard pod
    security settings, a notebook or the gateway are not a sandbox for generated
    code.

To experiment with NOOA outside Kionga's runtime, use a dedicated container
sandbox or VM that you provision, with restricted network egress, resource and
time limits, minimal secrets, and no Docker socket or sensitive host or
workspace mounts. The NOOA image still builds with the `nooa` SDK extra on
Python 3.12 or 3.13:

```bash
docker build \
  --build-arg PYTHON_VERSION=3.12 \
  --build-arg SDK_SOURCE=local --build-context sdk=sdk-python \
  --build-arg SDK_EXTRAS=runtime,nooa \
  -t your-registry/nooa-agent:dev agent-runtime
```

NOOA support is experimental. The adapter does not export NOOA's trace tree or
keep its Python objects between turns.

## Deploy agents from several frameworks

- Package each framework's module and dependencies in its own image, and deploy
  it with the SDK's `deploy_agent(..., graph_module=..., image=...)`, the API or
  the console. Your administrator's CPU, memory and GPU grants still apply.
- On Kubernetes, the operator creates one workload per agent, so each agent can
  run a different framework. The Compose runtime hosts only one factory at a time.
- Third-party HTTP runtimes must reject requests for an entry point they do not
  serve, as the bundled runtime does.
- Use separate framework stores or namespaces for each team or tenant. The session
  and user IDs a client sends are routing context, not proof of identity, and an
  adapter does not make a framework's memory multi-tenant. Map identities and data
  access at your authenticated boundary.

## Related

- [Agno: running agents](https://docs.agno.com/agents/running-agents) and
  [run metrics](https://docs.agno.com/reference/run/metrics)
- [NOOA source and safety guidance](https://github.com/NVIDIA-NeMo/labs-OO-Agents)
- [Build and deploy an agent](agents.md)
