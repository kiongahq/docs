# Agents

Agents are **LangGraph** graphs served by the shared agent-runtime. They answer via
a real LLM, keep session state in Postgres, retrieve features and long-term memory,
call tools, and emit full traces with measured token/cost accounting.

## Anatomy of an agent

An agent is a deployed record pointing at a **graph module** (`module:function`),
with an LLM backend, a tool list, a canary weight, and status. The default agent is
`agents.customer_support.graph:build` — a `StateGraph` with a reason → tools →
respond loop and two registered tools:

- `feature_store_lookup` — reads online features via the feature gateway (with a
  demo fallback).
- `kb_search` — a knowledge-base lookup.

## Invoking

=== "Console"

    **Agents → Chat** on an agent. Each turn shows the reply, token count, and
    latency; the Session Monitor lists live sessions with turns, tokens, and cost.

=== "SDK"

    ```python
    agents = client.list_agents()
    reply = client.invoke_agent(agents[0].id, message="When are invoices issued?")
    ```

=== "API"

    ```bash
    curl -s -X POST http://localhost:8080/api/v1/agents/<id>/invoke \
      -H 'Content-Type: application/json' \
      -d '{"message":"When are invoices issued?","session_id":"","user_id":"console"}'
    ```

## What happens per turn

1. The gateway proxies to the agent-runtime with the agent's identity headers.
2. The runtime loads the **Postgres checkpoint** for the session (state persists
   across turns; sessions are scoped per agent).
3. The graph runs — reasoning, tool calls, feature/memory retrieval.
4. The LLM is called **through the trace-proxy**, which forwards to the provider and
   publishes the call to Kafka.
5. The runtime reports the session (turns, current node, tokens, cost) to the
   gateway; the reply returns.

## Sessions, traces, cost

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/agents/{id}/sessions` | Live sessions (turns, node, tokens, cost) |
| `GET /api/v1/agents/{id}/traces` | Trace records |
| `GET /api/v1/agents/{id}/usage` | Aggregated tokens/cost/active sessions |

Tokens come from LangChain usage metadata — **measured, never estimated**. Cost uses
`MLAIOPS_COST_PER_1K_INPUT/OUTPUT`. The **Prompt Library** panel proxies Langfuse
prompts; deep observability lives in the Langfuse UI (<http://localhost:3000>).

## Using a real LLM

By default agents use the `mock` backend (replies prefixed `[mock]`) so the stack
runs with zero keys. To use a real provider, set in `.env`:

```bash
MLAIOPS_LLM_BACKEND=anthropic          # or openai / openai-compatible
MLAIOPS_LLM_MODEL=claude-sonnet-4-5
ANTHROPIC_API_KEY=sk-ant-...
LLM_UPSTREAM_URL=https://api.anthropic.com
```

Calls still egress through the trace-proxy, so tokens and cost land in Kafka and the
cost dashboard. Keys are env-only and never written to traces, logs, or the store.

## Canary traffic

```bash
curl -s -X PUT http://localhost:8080/api/v1/agents/<id>/traffic \
  -d '{"canary_weight":10}'
```

## Writing your own agent

Add a package under `python/agents/` exposing a `build(model, checkpointer)` that
returns a compiled graph, `StateGraph`, or factory. Register tools with
`mlaiops_sdk.register_tool` and convert them with `langchain_tools([...])`. Point the
runtime at it with `MLAIOPS_GRAPH_MODULE=agents.your_agent.graph:build`, or deploy it
as a distinct agent so the shared runtime serves it by identity.

## Long-term memory (pgvector)

`AgentMemoryClient` gives agents `remember`/`recall` over a pgvector table, plus
`get_entity_features`. It uses a deterministic `HashingEmbedder`, so memory tests run
offline. Checkpoints (session state) and memories (semantic recall) are distinct: one
is per-thread conversation state, the other is durable semantic memory.
