---
description: Register tools, deploy an agent, chat with it, connect a real LLM provider, watch sessions, traces and cost, shift canary traffic, and build your own agent from the production-agent template.
---

# Build and deploy an agent

An agent in Kionga is a deployed record that points at an entry point
(`module:function`) in a runtime image, with an LLM backend, a list of registered
tools, per-replica resources, replica limits, and canary traffic. This guide
covers registering tools, deploying and chatting with an agent, connecting a real
LLM, monitoring usage, shifting traffic, and building your own agent.

Agents run on LangGraph, Agno, NOOA or your own adapter. LangGraph gets built-in
checkpoints and Langfuse callbacks. For the other frameworks, see
[Run agents built with other frameworks](agent-frameworks.md).

## Before you begin

- **To deploy, chat with and change agents:** the `agents` service for a normal
  user, or the `engineer`, `operator` or `admin` role, and access to the agent's
  project. Viewers can see agents but cannot chat with or change them.
- **To register tools:** the `catalog` service for a normal user, or the
  `engineer`, `operator` or `admin` role.
- **Capacity:** for a normal user, every agent counts against the compute grant
  at its maximum replicas (see [Deploy an agent](#deploy-an-agent)).
- **For the API and SDK examples:** export `MLAIOPS_URL` and a personal API key
  with the needed scopes as `MLAIOPS_TOKEN`. See
  [Authentication](../reference/api.md#authentication).

## Register the agent's tools

An agent can name only tools that are registered in Kionga; the gateway rejects
an agent that references an unregistered tool.

=== "SDK"

    ```python
    client.register_tool(
        "kb_search", "1.0.0", "Search the support knowledge base",
        {"type": "object", "properties": {"query": {"type": "string"}},
         "required": ["query"]},
        tags=["support"],
    )
    ```

=== "API"

    ```bash
    curl -s -X POST "$MLAIOPS_URL/api/v1/tools" \
      -H "Authorization: Bearer $MLAIOPS_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"name": "kb_search", "version": "1.0.0",
           "description": "Search the support knowledge base",
           "input_schema": {"type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"]},
           "tags": ["support"]}'
    ```

The console lists registered tools under **Catalog > Tools**, but you register
them through the API or the SDK.

**Verify:** `mlaiops tool list` includes the tool.

## Deploy an agent

=== "Console"

    1. Open **Agents** and click **＋ Deploy agent**.
    2. Optional: under **Load a generated contract**, paste the
       the generated `agent.json` contract (in the `platform` folder) from a `production-agent` project and click
       **Load JSON**.
    3. Under **Identity**, choose the **Project** and enter the **Agent name** and
       **Version**. Disabled or unassigned projects are not listed.
    4. Under **Runtime and capacity**, enter the **OCI image**, preferably pinned
       by digest, and the **Graph module** (`package.module:attribute`). Choose
       the **LLM backend** and set the replicas, CPU and memory per replica, and
       any GPUs.
    5. Under **Tools**, select registered tools.
    6. Click **Deploy agent**.

    **Example entrypoint** fills in the graph module for LangGraph, Agno, NOOA or
    a custom adapter. It does not install or start a runtime.

=== "API"

    ```bash
    curl -s -X POST "$MLAIOPS_URL/api/v1/agents" \
      -H "Authorization: Bearer $MLAIOPS_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{
        "project_id": "prj-123",
        "name": "incident-response",
        "version": "1.0.0",
        "image": "ghcr.io/acme/incident-response@sha256:<digest>",
        "graph_module": "incident_response_agent.graph:build",
        "llm_backend": "openai-compatible",
        "autoscaling": {"min_replicas": 2, "max_replicas": 6},
        "resources": {"cpu": "1", "memory": "2Gi", "gpu": 0},
        "tools": ["runbook_search", "create_escalation"]
      }'
    ```

=== "SDK"

    ```python
    agent = client.deploy_agent(
        "prj-123", "incident-response", "1.0.0",
        "ghcr.io/acme/incident-response@sha256:<digest>",
        "incident_response_agent.graph:build",
        llm_backend="openai-compatible",
        replicas=2, max_replicas=6, cpu="1", memory="2Gi",
        tools=["runbook_search", "create_escalation"],
    )
    ```

Field rules:

- `llm_backend` is `mock` (default), `openai`, `anthropic`, `openai-compatible`
  or `self-hosted`.
- CPU and memory use Kubernetes quantities. They default to `500m` and `1Gi` per
  replica.
- When `gpu` is above zero, `gpu_type` defaults to `nvidia.com/gpu`. Another type
  must be a domain-qualified Kubernetes extended resource, outside the
  Kubernetes-reserved domains, and not a native resource name such as `cpu`.
- `max_replicas` must be at least `min_replicas` and at most 100.

For a normal user, Kionga counts every agent the user owns at its maximum
replicas, plus the trace sidecar's CPU and memory for each possible pod. The
total CPU, memory, GPUs and replica count must fit the user's grant, and a GPU
type must match the grant. Administrators and operators skip the capacity check
but not the field rules.

The agent becomes `ready` only when its runtime answers its health check.
Until then it is `pending`, and **Chat** stays disabled.

**Verify:** the agent card under **Agents** shows `ready`, and the summary counts
it as a ready runtime.

## Chat with an agent

=== "Console"

    On a ready agent's card, click **Chat**, type a message and click **Send**.
    Each turn shows the reply, the token count and the latency.

=== "SDK"

    ```python
    reply = client.invoke_agent(agent.id, "When are invoices issued?")
    print(reply["reply"])
    ```

=== "API"

    ```bash
    curl -s -X POST "$MLAIOPS_URL/api/v1/agents/<agent-id>/invoke" \
      -H "Authorization: Bearer $MLAIOPS_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"message": "When are invoices issued?", "session_id": "", "user_id": "console"}'
    ```

For each turn, Kionga checks the runtime's health for up to 3 seconds and returns
`503 agent_not_ready` without sending the turn if it fails. The runtime then loads
the session's checkpoint, so conversation state carries across turns in a
session, runs the graph and its tools, calls the LLM, and reports the session's
turns, tokens and cost.

**Verify:** the reply appears, and the session shows under **Live sessions**.

On Compose, all agents share one runtime that serves the demo support agent,
`agents.customer_support.graph:build`, with the tools `feature_store_lookup`
and `kb_search`. Kionga creates no agent record for you; the
[quickstart](../getting-started/quickstart.md#talk-to-an-agent) registers one.
On Kubernetes, each agent gets its own Deployment and Service.

## Connect a real LLM provider {#using-a-real-llm}

By default, agents use the `mock` backend, which replies with a `[mock]` prefix
and needs no key. To use a real provider on Compose:

1. Add the provider to `deploy/.env`:

    ```bash
    # OpenAI, or any OpenAI-compatible server behind LLM_UPSTREAM_URL
    MLAIOPS_LLM_BACKEND=openai             # or openai-compatible
    MLAIOPS_LLM_MODEL=gpt-4o
    OPENAI_API_KEY=sk-...
    # LLM_UPSTREAM_URL=https://api.openai.com   # where the trace proxy forwards

    # or Anthropic
    # MLAIOPS_LLM_BACKEND=anthropic
    # MLAIOPS_LLM_MODEL=claude-sonnet-4-5
    # ANTHROPIC_API_KEY=sk-ant-...
    ```

2. Recreate the runtime:

    ```bash
    docker compose -f deploy/compose.yaml up -d agent-runtime
    ```

With `openai` and `openai-compatible`, every call goes through the trace proxy,
which forwards it to the provider and publishes it to the Kafka topic
`mlaiops.llm.traces`. With `anthropic`, the runtime calls Anthropic directly, so
the trace proxy does not capture the call; Langfuse tracing and measured token
usage still work. Keys stay in the environment and are never written to traces,
logs or the store.

**Verify:** a chat reply no longer starts with `[mock]`.

## Monitor sessions, traces and cost

=== "Console"

    Open **Agents**. **Live sessions** lists each session with its agent, current
    node, status, turns, tokens and cost. The **Prompt Library** panel lists your
    Langfuse prompts. For full traces, open the Langfuse UI (on Compose,
    `http://localhost:3000`).

=== "API"

    | Route | Returns |
    | --- | --- |
    | `GET /api/v1/agents/{id}/sessions` | Live sessions with turns, node, tokens and cost |
    | `GET /api/v1/agents/{id}/traces` | Trace records |
    | `GET /api/v1/agents/{id}/usage` | Total tokens, cost and active sessions |

Token counts come from the model's usage metadata; Kionga never estimates them.
Cost uses the per-1,000-token rates in `MLAIOPS_COST_PER_1K_INPUT` and
`MLAIOPS_COST_PER_1K_OUTPUT`.

## Shift canary traffic {#shift-canary-traffic}

1. On the agent card, click **Traffic**.
2. Set the **Canary weight**, the percentage of requests routed to the canary
   version, and click **Update traffic**.

Or call the API:

```bash
curl -s -X PUT "$MLAIOPS_URL/api/v1/agents/<agent-id>/traffic" \
  -H "Authorization: Bearer $MLAIOPS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"canary_weight": 10}'
```

On Kubernetes, the operator turns the weight into a stable and canary traffic
plan.

**Verify:** the agent card shows the new weight, for example `10% canary`.

## Build your own agent

Start from the `production-agent` template rather than an empty module. The
starter runs before you change it.

1. Create the project and copy its scaffold command:

    ```python
    project = client.create_project(
        "incident-response-agent",
        template="production-agent",
        framework="langgraph",
        accelerator="cpu",
    )
    print(project.scaffold_command)
    ```

2. Run the command in Jupyter or the IDE (see
   [Scaffold a project](scaffolding.md)). Add `--agent codex`, `--agent claude`
   or `--agent custom` to let a coding agent extend the generated folder.
3. Write your graph. The entry point must be a `build(model, checkpointer)`
   compatible callable that returns a compiled graph, a `StateGraph` or a
   factory. Define tools in code with `mlaiops_sdk.register_tool` and pass them
   to LangGraph with `langchain_tools([...])`. Register the same tools with Kionga
   (see [Register the agent's tools](#register-the-agents-tools)).
4. Build and push an image, pinned by digest, and
   [deploy it](#deploy-an-agent). The project's generated `agent.json` contract (in its `platform` folder) fills in the
   deploy form.

**Verify:** the deployed agent reaches `ready` and answers in **Chat**.

### Add memory

Short-term checkpoints and long-term memory are separate:

- **Checkpoints** keep one conversation's state across turns. They use the
  PostgreSQL URL in `MLAIOPS_CHECKPOINT_DSN`, or `DATABASE_URL` when that is not
  set.
- **Long-term memory** uses `AgentMemoryClient`, with `remember` and `recall`
  over a pgvector table in the same PostgreSQL, plus `get_entity_features` for
  [online features](features.md). Its default embedding function is deterministic, so
  memory tests run offline.

Keep artifacts and large context in object storage, not in prompts or queues.

### On Kubernetes

Kionga derives one DNS name per agent ID, so different agents can reuse a human
name without overwriting each other. The operator creates the agent's
Deployment and Service, and reports the agent ready when at least
`min_replicas` pods are available. When `max_replicas` is above `min_replicas`,
it also creates a HorizontalPodAutoscaler that targets 70% average CPU, which
needs a working Kubernetes metrics API. On Compose, `AGENT_RUNTIME_URL` points
every agent at the shared runtime, so autoscaling does not apply.

## Release checklist

Before you shift traffic to a new agent version:

1. Run the deterministic graph and tool tests with the mock model.
2. Run the golden evaluation cases and failure-path tests.
3. Check tool schemas, timeouts, permissions and safe retries.
4. Check that checkpoints and memory are isolated by agent and tenant.
5. Inspect Langfuse traces for secrets and unexpected tool payloads.
6. Deploy by image digest with a small canary weight.
7. Compare quality, latency, tokens, cost and error rate.
8. Promote the canary, or return traffic to the stable version.

## Next steps

- [Run agents built with Agno, NOOA or your own framework](agent-frameworks.md).
- [Use the built-in feature store](features.md) for agent lookups.
- [Process real-time events](realtime.md) with an agent.
