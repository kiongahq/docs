---
icon: material/robot-outline
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

To build visually, use the [native Agent Designer](agent-designer.md), which
tests, evaluates, publishes and deploys graphs, or a [Langflow canvas](langflow.md). Saved Langflow flows can be captured as
versioned Kionga snapshots, published as independent agents, and activated on a
stable managed endpoint. The [Langflow guide](langflow.md) covers that workflow.

## Before you begin

- **To deploy, chat with and change agents:** the `agents` service for a normal
  user, or the `engineer`, `operator` or `admin` role, and access to the agent's
  project. Viewers can see agents but cannot chat with or change them.
- **To register tools:** the `catalog` service for a normal user, or the
  `engineer`, `operator` or `admin` role.
- **Capacity:** for a normal user, every agent counts against the compute grant
  at its maximum replicas (see [Deploy an agent](#deploy-an-agent)).
- **For the API and SDK examples:** export `KIONGA_URL` and a personal API key
  with the needed scopes as `KIONGA_TOKEN`. See
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
    curl -s -X POST "$KIONGA_URL/api/v1/tools" \
      -H "Authorization: Bearer $KIONGA_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"name": "kb_search", "version": "1.0.0",
           "description": "Search the support knowledge base",
           "input_schema": {"type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"]},
           "tags": ["support"]}'
    ```

The console lists registered tools under **Catalog**, on the **tool** tab, but you register
them through the API or the SDK.

**Verify:** `kionga-cli tool list` includes the tool.

## Deploy an agent

=== "Console"

    1. Open **Agents** and click **Deploy agent**.
    2. Choose the **Framework**: LangGraph, Agno, NOOA or Custom adapter. The choice
       fills in the **Graph factory**. It does not install or start a runtime.
    3. Optional: expand **Import agent contract**, paste the generated `agent.json`
       contract (in the `platform` folder) from a `production-agent` project and
       click **Load contract**.
    4. Choose the **Project** and enter the **Name** and **Version**. Only
       projects assigned to you are listed.
    5. Check the **Image**, preferably pinned by digest, and enter the **Graph factory**
       (`package.module:attribute`). Choose the **Model backend**, and set the
       **Minimum replicas**, **Maximum replicas**, **Scale on** trigger, **CPU per
       replica**, **Memory per replica** and **GPUs per replica**.
    6. Under **Registered tools**, select the tools the agent may use.
    7. Click **Deploy agent**.

    The **Image** field is required. When your install sets a default agent
    runtime image, the form fills the field with it and you can change it. When
    it sets none, the field is empty and you enter an image. The Helm chart sets
    the default from its `agent-runtime` image. The Compose files do not set one.

    !!! info "Available in a later release"
        In platform v0.2.1 and earlier, the **Image** field is always empty.

=== "API"

    ```bash
    curl -s -X POST "$KIONGA_URL/api/v1/agents" \
      -H "Authorization: Bearer $KIONGA_TOKEN" \
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

- `image` is required. The gateway rejects a request without one. The console
  fills it in from `defaults.agent_image` in `GET /api/v1/me` when your install
  sets that value, and the API never fills it in for you.
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

**Verify:** the agent's row under **Agents** shows `ready` in the **Status** column.

## Chat with an agent

=== "Console"

    On a ready agent's row, click **Chat**, type a **Message** and click **Send**.
    Each turn shows the reply, the token count and the latency.

=== "SDK"

    ```python
    reply = client.invoke_agent(agent.id, "When are invoices issued?")
    print(reply["reply"])
    ```

=== "API"

    ```bash
    curl -s -X POST "$KIONGA_URL/api/v1/agents/<agent-id>/invoke" \
      -H "Authorization: Bearer $KIONGA_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"message": "When are invoices issued?", "session_id": "", "user_id": "console"}'
    ```

For each turn, Kionga checks the runtime's health for up to 3 seconds and returns
`503 agent_not_ready` without sending the turn if it fails. The runtime then loads
the session's checkpoint, so conversation state carries across turns in a
session, runs the graph and its tools, calls the LLM, and reports the session's
turns, tokens and cost.

**Verify:** the reply appears, and the session shows under **Sessions**.

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
    KIONGA_LLM_BACKEND=openai             # or openai-compatible
    KIONGA_LLM_MODEL=gpt-4o
    LLM_UPSTREAM_API_KEY=sk-...                 # the provider key; the trace proxy holds it
    # LLM_UPSTREAM_URL=https://api.openai.com   # where the trace proxy forwards

    # or Anthropic
    # KIONGA_LLM_BACKEND=anthropic
    # KIONGA_LLM_MODEL=claude-sonnet-4-5
    # ANTHROPIC_API_KEY=sk-ant-...
    ```

2. Apply the change. `local-up` recreates the services whose settings changed and
   generates the local project key:

    ```bash
    make -C deploy local-up
    ```

With `openai` and `openai-compatible`, every call goes through the trace proxy,
which forwards it to the provider and publishes a trace record (agent, version,
session, status code and duration, not the prompt or response) to the Kafka
topic `kionga.llm.traces`. With `anthropic`, the runtime calls Anthropic directly, so
the trace proxy does not capture the call; Langfuse tracing and measured token
usage still work. Keys stay in the environment and are never written to traces,
logs or the store.

### Project keys {#project-keys}

An agent never holds your provider key when its calls go through the trace proxy.
Two different keys are involved:

| Key | Who holds it | Where it goes |
| --- | --- | --- |
| Kionga project key | The agent, as its `OPENAI_API_KEY` | From the agent to the trace proxy |
| Provider key | The trace proxy, as `LLM_UPSTREAM_API_KEY` | From the trace proxy to the provider |

The proxy checks the project key, removes it, and adds the provider key. A leaked
project key can be revoked on its own and identifies which project made each call;
the provider key stays out of agent code, images and memory.

The proxy accepts `Authorization: Bearer <key>`, `x-api-key` or `api-key`. A missing
or unknown key returns `401` with `invalid_api_key`, and the provider never sees
the request. The proxy stores only SHA-256 hashes, in `TRACE_PROXY_KEYS`. Trace
records carry the entry's `project` and `key_id`, never the key or its hash. The
optional `agent` field overrides the agent name on those records.

`make -C deploy local-up` generates a key for local use. For any other deployment,
generate one and keep it private:

```bash
key=$(openssl rand -hex 32)
hash=$(printf %s "$key" | openssl dgst -sha256 -r | cut -d' ' -f1)
echo "TRACE_PROXY_PROJECT_KEY=$key"
echo "TRACE_PROXY_KEYS='[{\"key_id\":\"agents\",\"key_sha256\":\"$hash\",\"project\":\"default\"}]'"
```

An unknown field in an entry is rejected, so a typo cannot silently drop a setting.
See [Trace proxy](../reference/configuration.md#trace-proxy) for every setting.

**Verify:** a chat reply no longer starts with `[mock]`.

## Monitor sessions, traces and cost

=== "Console"

    Open **Agents**. **Sessions** lists each session with its agent, current
    node, status, turns, tokens and cost, and **Recent traces** lists traces. The
    **Prompt catalog** panel lists your Langfuse prompts. **Operations** on an
    agent's row opens its requests, latency, tokens and cost for a window of 1, 6, 24, 72 or
    168 hours. For full traces, open the Langfuse UI (on Compose,
    `http://localhost:3000`).

=== "API"

    | Route | Returns |
    | --- | --- |
    | `GET /api/v1/agents/{id}/sessions` | Live sessions with turns, node, tokens and cost |
    | `GET /api/v1/agents/{id}/traces` | Trace records |
    | `GET /api/v1/agents/{id}/usage` | Total tokens, cost and active sessions |

Token counts come from the model's usage metadata; Kionga never estimates them.
Cost uses the per-1,000-token rates in `KIONGA_COST_PER_1K_INPUT` and
`KIONGA_COST_PER_1K_OUTPUT`.

## Shift canary traffic {#shift-canary-traffic}

1. On the agent's row, click **Traffic**.
2. Set the **Canary weight (%)**, the percentage of requests routed to the canary
   version, and click **Update traffic**.

Or call the API:

```bash
curl -s -X PUT "$KIONGA_URL/api/v1/agents/<agent-id>/traffic" \
  -H "Authorization: Bearer $KIONGA_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"canary_weight": 10}'
```

On Kubernetes, the operator turns the weight into a stable and canary traffic
plan.

**Verify:** the **Canary** column shows the new weight, for example `10%`.

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
   factory. Define tools in code with `kionga.register_tool` and pass them
   to LangGraph with `langchain_tools([...])`. Register the same tools with Kionga
   (see [Register the agent's tools](#register-the-agents-tools)).
4. Build and push an image, pinned by digest, and
   [deploy it](#deploy-an-agent). The project's generated `agent.json` contract (in its `platform` folder) fills in the
   deploy form.

**Verify:** the deployed agent reaches `ready` and answers in **Chat**.

### Add memory

Short-term checkpoints and long-term memory are separate:

- **Checkpoints** keep one conversation's state across turns. They use the
  PostgreSQL URL in `KIONGA_CHECKPOINT_DSN`, or `DATABASE_URL` when that is not
  set.
- **Long-term memory** uses `AgentMemoryClient`, with `remember`, `recall` and
  `forget` over a pgvector table in the same PostgreSQL, isolated per user (pass
  the authenticated `user_id`), plus `get_entity_features` for
  [online features](features.md). Its default embedding function is deterministic, so
  memory tests run offline.

Keep artifacts and large context in object storage, not in prompts or queues.

### On Kubernetes

Kionga derives one DNS name per agent ID, so different agents can reuse a human
name without overwriting each other. The operator creates the agent's
Deployment and Service, and reports the agent ready when at least
`min_replicas` pods are available. On Compose, `AGENT_RUNTIME_URL` points
every agent at the shared runtime, so autoscaling does not apply.

## Scale agents automatically {#autoscale-agents}

On Kubernetes, an agent runs between `min_replicas` and `max_replicas` pods.
Choose what drives the scaling with `scaling`:

| Trigger | `scaling` | What it does |
| --- | --- | --- |
| Requests (default) | `{"metric": "requests", "target": 100}` | Adds pods when the average number of in-flight requests per pod goes above the target. The target is 1 to 10000. Needs the KEDA HTTP add-on. |
| CPU | `{"metric": "cpu", "target": 70}` | Adds pods when average CPU use goes above the target percent of the pod's CPU request. The target is 1 to 100. Needs the Kubernetes metrics API. |

Requests scaling suits agents, because an agent spends most of a request waiting
on a language model and uses little CPU, so CPU stays low while requests pile up.
Use CPU scaling for an agent that does heavy work in the process, or on a cluster
without KEDA. If the KEDA HTTP add-on isn't installed, a request-scaled agent runs
on CPU scaling instead, and its `ScalingReady` condition reports why.

Agents never scale to zero: `min_replicas` is at least 1. See
[Self-healing and autoscaling](../concepts/self-healing-and-autoscaling.md).

=== "API"

    ```bash
    curl -s -X POST "$KIONGA_URL/api/v1/agents" \
      -H "Authorization: Bearer $KIONGA_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"project_id": "prj-123", "name": "incident-response",
           "version": "1.0.0",
           "image": "ghcr.io/acme/incident-response@sha256:<digest>",
           "graph_module": "incident_response_agent.graph:build",
           "autoscaling": {"min_replicas": 2, "max_replicas": 6},
           "scaling": {"metric": "requests", "target": 20}}'
    ```

=== "SDK"

    ```python
    client.deploy_agent(
        "prj-123", "incident-response", "1.0.0",
        "ghcr.io/acme/incident-response@sha256:<digest>",
        "incident_response_agent.graph:build",
        replicas=2, max_replicas=6,
        scaling={"metric": "requests", "target": 20},
    )
    ```

The same `scaling` field works when you deploy a published Agent Designer
version through the API.

!!! info "Available in a later release"
    Request scaling counts requests that pass through the KEDA interceptor, so
    callers must use the address the operator reports for the agent. The gateway
    change that does this, and the `scaling` argument of the SDK's
    `deploy_agent_version`, are not in a released version yet. Until then, an
    agent scaled on requests may not see its traffic. Choose CPU scaling if you
    need autoscaling today.

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

## Verify

1. List your agents and find the new one:

    ```bash
    curl -s -H "Authorization: Bearer $KIONGA_TOKEN" "$KIONGA_URL/api/v1/agents"
    ```

    The response has `items` and `total`. The agent's `status` is `pending` until its
    runtime answers the health check, then `ready`.
2. Send one turn:

    ```bash
    curl -s -X POST "$KIONGA_URL/api/v1/agents/<agent-id>/invoke" \
      -H "Authorization: Bearer $KIONGA_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{"message": "When are invoices issued?"}'
    ```

    The reply has `reply`, `session_id`, `input_tokens`, `output_tokens`, `cost_usd`,
    `duration_ms` and `usage_available`. With the default `mock` backend, `reply`
    starts with `[mock]`. After you connect a real provider, it does not.
3. Read the usage the turn produced:

    ```bash
    curl -s -H "Authorization: Bearer $KIONGA_TOKEN" \
      "$KIONGA_URL/api/v1/agents/<agent-id>/usage"
    ```

    The response has `sessions`, `active`, `input_tokens`, `output_tokens` and
    `cost_usd`. `sessions` is at least 1 after your turn.
4. After a traffic change, the agent's `canary_weight` in the list response matches
   the weight you set, and the **Canary** column shows it, for example `10%`.

## Troubleshooting

- *The **Chat** button is disabled, or a turn returns `503` with `agent_not_ready` and "agent
  runtime is not ready."* The runtime did not pass its health check within 3
  seconds, so Kionga did not send the turn. The agent stays `pending` until it
  does. Check that the image can be pulled, that `graph_module` names an attribute
  the image contains, and that the runtime starts. Then send the turn again.
- *Deploy returns `422` with "agent references an unregistered tool: `<name>`."* The
  agent names a tool that is not registered. Register it as described in
  [Register the agent's tools](#register-the-agents-tools), then deploy again.
- *Deploy returns `403` with `access_denied` and "project is not assigned to this
  user."* You are not assigned to that project. Ask an administrator to assign it.
- *Deploy returns `403` with `resource_not_provisioned`.* The agent does not fit your
  compute grant. The message states the requested and granted CPU, memory or GPUs, or says that no
  compute grant has been provisioned. Lower the maximum replicas, CPU or memory, or ask
  an administrator for a larger grant.
- *A turn returns `409` with "This runtime serves a different entrypoint; deploy a
  dedicated runtime for this agent."* On Compose, the shared runtime serves one
  `KIONGA_GRAPH_MODULE`, and the agent names another. Set the variable to the
  agent's graph module and recreate the runtime, or deploy on Kubernetes.
- *A turn returns `502` with `runtime_unreachable`.* The gateway could not reach the
  runtime. Check that the runtime is running, then retry.
- *Replies still start with `[mock]`.* The agent uses the `mock` backend. Connect a
  provider as described in [Connect a real LLM provider](#using-a-real-llm), then
  recreate the services.
- *The trace proxy returns `401` with `invalid_api_key`.* The project key is missing or
  unknown. See [Project keys](#project-keys).

## Related pages

- [Run agents built with Agno, NOOA or your own framework](agent-frameworks.md)
- [Build agents in the Agent Designer](agent-designer.md)
- [Use the built-in feature store](features.md) for agent lookups
- [Process real-time events](realtime.md) with an agent
- [Self-healing and autoscaling](../concepts/self-healing-and-autoscaling.md)
