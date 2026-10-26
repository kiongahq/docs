---
icon: material/file-tree-outline
description: Reference for native agent graphs, covering schema version 2, components and typed ports, run events, published versions, REST routes, limits, security model and migration from version 1 drafts.
---

# Agent graph reference

The [kiongahq/contracts `agent-graph/`](https://github.com/kiongahq/contracts/tree/main/agent-graph)
directory defines every document listed here. The gateway validates and hashes
graphs. `agent-runtime` executes them. Both sides embed the same component
registry and test against the same fixtures.

## Graph document (schema version 2)

```json
{
  "schema_version": 2,
  "name": "Support agent",
  "nodes": [
    {"id": "input", "kind": "input", "name": "Question", "x": 40, "y": 160},
    {"id": "route", "kind": "condition", "name": "Refund?", "x": 260, "y": 160,
     "config": {"expression": "contains:refund"}, "group": "Routing"},
    {"id": "output", "kind": "output", "name": "Reply", "x": 480, "y": 160}
  ],
  "edges": [
    {"from": "input", "to": "route", "from_port": "out", "to_port": "in"},
    {"from": "route", "to": "output", "from_port": "true", "to_port": "in"}
  ],
  "settings": {"max_steps": 50, "timeout_seconds": 60, "max_tokens": 50000}
}
```

- Node IDs match `^[a-z][a-z0-9-]{0,62}$`. A graph has 2–100 nodes, at most 300
  edges, and exactly one `input` and one `output`. Config values are strings of
  at most 16,000 characters, with at most 30 keys per node.
- An edge's ports default to the source's first output (`true` for a condition)
  and the target's first input.
- Settings (all optional integers): `max_steps` 1–200 (default 50),
  `timeout_seconds` 1–300 (default 60), `max_tokens` 1–1,000,000 (default 50,000).
- Cycles are rejected. Bounded loops are not part of version 2.

## Components

| Kind | Input accepts | Output | Settings | Side effects | Timeout / retries |
| --- | --- | --- | --- | --- | --- |
| `input` | none | `out`: `text` | none | no | 1 s / 0 |
| `output` | `text`, `chat`, `json`, `documents` | none | none | no | 1 s / 0 |
| `prompt` | `text`, `chat`, `json`, `documents` | `out`: `text` | `template`* | no | 1 s / 0 |
| `model` | `text`, `chat` | `out`: `text` | `model` (`llm` or a Kionga model ID), `system` | no | 60 s / 1 |
| `tool` | `text`, `json` | `out`: `json` | `tool`* (registered tool) | **yes** | 30 s / 0 |
| `api` | `text`, `json` | `out`: `json` | `connection`*, `request` | **yes** | 15 s / 0 |
| `knowledge` | `text`, `chat` | `out`: `documents` | `knowledge_base`*, `query` (`{input}`), `limit` 1–20 (4) | no | 15 s / 1 |
| `storage` | any (optional) | `out`: `documents` | `dataset`*, `key`* | no | 15 s / 1 |
| `condition` | `text`, `chat`, `json`, `documents` | `true`, `false`: `text` | `expression`* | no | 1 s / 0 |
| `memory` | `text`, `chat` | `out`: `chat` | `strategy` (`window`, `none`), `turns` 1–50 (6) | no | 5 s / 0 |
| `extract` | `json`, `text` | `out`: `json` | `path`* (dotted keys and list indexes), `missing` (`fail`, `empty`) | no | 1 s / 0 |

`model`, `tool`, `api`, `knowledge` and `storage` also have an `error` output.
When one of these nodes fails with `node_error`, `resource_denied`,
`resource_unavailable` or a node `timeout`, and its `error` port is connected,
the redacted failure message (text) goes down that branch and the run
continues. Nodes fed only by its `out` port are skipped.

\* required. `GET /api/v1/agent-designs/components` returns the full registry,
including labels, help text and the conversion table.

**Conversions.** `json` → `text` (compact JSON), `documents` → `text` (texts
joined by blank lines), `chat` → `text` (newest turn), `text` → `chat` (one user
turn), `text` → `json` (parsed, or `{"input": text}`).

**Execution.** Nodes run in topological order. A node with inbound edges runs
when at least one edge carried a value; otherwise it is `skipped`. A node with
no inbound edges always runs. Only `timeout`, `node_error` and
`resource_unavailable` failures are retried.

**Conditions.** `contains`, `not_contains` and `equals` compare without regard
to case; `equals` also trims whitespace. `matches` takes a regular expression
of at most 200 characters (use the RE2 subset; Python evaluates it).
`longer_than` takes a whole number. `empty` and `not_empty` take no argument.

## Run events

Runs stream events that follow `run-event.v1.schema.json`: `run.started`,
`node.started`, `node.retrying`, `node.completed` (with `port` for a condition),
`node.skipped`, `node.failed`, and then exactly one of `run.completed`,
`run.failed` or `run.cancelled`. `seq` starts at 0 and increases by one per
event. Previews are redacted and truncated to 2,000 characters; the final
`output` is truncated at 64 KiB.

## Published versions

`artifact.v1.schema.json` defines a version. It records the version number,
`content_sha256`, the registry version, the normalized graph, the source
revision, the author, notes, the runtime module
`agents.native_graph:build_native` and an optional evaluation summary.

`content_sha256` hashes the graph's behavior only. Node IDs, kinds and non-empty
config, edges with their ports, and settings are serialized as canonical JSON
(sorted keys, no whitespace, UTF-8, no HTML escaping, U+2028/U+2029 escaped).
Names, positions and groups are excluded.

## REST API

| Method and path | Purpose |
| --- | --- |
| `GET /api/v1/agent-designs/components` | Component registry. |
| `GET /api/v1/agent-designs/templates` | Starter templates. |
| `GET /api/v1/agent-designs/overview?project_id=` | Metrics for the last 24 hours. |
| `POST /api/v1/agent-designs/validate` | Validate an unsaved graph (`project_id`, `nodes`, `edges`, `settings`). |
| `GET, POST /api/v1/agent-designs`; `GET, PUT /api/v1/agent-designs/{id}` | Designs and revisions (PUT sends the `revision` you read; a stale revision returns 409). |
| `POST /api/v1/agent-designs/{id}/validate` | Validate the saved revision, or the canvas in the body. Returns `{runnable, issues, content_sha256, graph}`. |
| `GET, POST /api/v1/agent-designs/{id}/runs` | List runs, or start one: `{input, session_id, history, allow_side_effects, stop_after, revision}`. Accepts an `Idempotency-Key` header. |
| `GET /api/v1/agent-designs/{id}/runs/{run_id}` | A run with its events. |
| `GET /api/v1/agent-designs/{id}/runs/{run_id}/events` | `Accept: text/event-stream` for SSE (resumes from `Last-Event-ID`); otherwise a JSON page from `?after=`. |
| `POST /api/v1/agent-designs/{id}/runs/{run_id}/cancel` | Cancel a run. |
| `GET, PUT /api/v1/agent-designs/{id}/fixtures` | Test cases (PUT sends the fixtures `revision`). |
| `GET, POST /api/v1/agent-designs/{id}/evaluations` | List evaluations, or start one: `{gate, version_id, cases, allow_side_effects, revision}`. |
| `GET /api/v1/agent-evaluations/{id}`; `POST .../cancel` | An evaluation with per-case results; cancel it. |
| `POST /api/v1/agent-designs/{id}/publish` | `{revision, notes, evaluation_id}`. Returns 201 for a new version, or 200 for an existing one with the same behavior. |
| `GET /api/v1/agent-designs/{id}/versions`; `GET /api/v1/agent-versions/{id}` | Versions and their deployments; one version's artifact. |
| `POST /api/v1/agent-versions/{id}/runs` | Run a published version. |
| `POST /api/v1/agent-versions/{id}/deploy` | `{autoscaling, resources, require_evaluation}`. Deploys to the managed runtime. |

## Security model

- **No code in graphs.** The runner interprets a fixed set of components.
  Templates are substituted once and literally.
- **Credentials stay on the gateway.** Graphs hold resource IDs. The playground
  runner receives a random, run-scoped credential. That credential works only on
  the gateway's internal listener, only for the resource calls listed below, and
  only while the run is active. It inherits the user's project and their live
  grants, which are re-read on every call. Cancelling or finishing a run revokes
  it.
- **Allowed resource calls:** `POST models/{id}/predict`,
  `POST functions/{name}/invoke`, `POST agent-api-connections/{id}/invoke`,
  `GET knowledge-bases`, `POST knowledge-bases/{id}/search` and
  `GET datasets/{id}/object`.
- **Side effects need approval.** Playground runs and evaluations execute tool
  and API nodes only with `allow_side_effects`. A published version was approved
  when you published it.
- **Tenant isolation.** Every route checks project access. Resource IDs from
  another project fail validation. Runs, evaluations and versions of another
  tenant return 404.
- **Isolation of the runner.** In Compose it has no published port, a read-only
  root filesystem, no capabilities and no Docker socket, and it has PID, memory
  and CPU limits. It caps concurrent runs (`KIONGA_DESIGNER_MAX_RUNS`, default 8)
  and bounds each run by its step, time and token budgets.
- **Audit.** Kionga writes an audit event when a run starts, finishes, is
  cancelled or is pruned, when an evaluation starts or finishes, and when a
  version is published.

## Configuration

| Variable | Where | Purpose |
| --- | --- | --- |
| `KIONGA_AGENT_DESIGNER_RUNNER_URL` | gateway | The runner's base URL. Leave it empty to disable runs. |
| `KIONGA_AGENT_DESIGNER_RUNNER_TOKEN` | gateway | Bearer token the gateway presents to the runner. |
| `KIONGA_AGENT_DESIGNER_CALLBACK_URL` | gateway | The internal listener the runner calls back to (default `http://gateway:8087/api/v1`). |
| `KIONGA_NATIVE_AGENT_IMAGE` | gateway | The `agent-runtime` image used for deployed versions. |
| `KIONGA_DESIGNER_RUNNER_TOKEN` | runner | Must equal the gateway's token. It must be at least 16 characters, or the runner refuses to start. |
| `KIONGA_DESIGNER_PORT`, `KIONGA_DESIGNER_MAX_RUNS` | runner | Listen port (9100) and the concurrency cap (8). |
| `MLAIOPS_LLM_BACKEND`, `MLAIOPS_LLM_MODEL`, `MLAIOPS_LLM_BASE_URL` | runner | The platform chat model used by `model` nodes set to `llm`. |

## Migration from version 1 drafts

Kionga never rewrites stored revisions. When it reads a version 1 draft, it:

- sets `schema_version` to 2;
- fills in edge ports and default settings;
- treats an empty model as `llm`;
- runs a free-text memory strategy as `window`, with a warning.

The next save stores version 2. A version 1 condition held free text, so it fails
validation until it uses the operator grammar.

## Troubleshooting

- **Run reports that the runner is not configured.** Set
  `KIONGA_AGENT_DESIGNER_RUNNER_URL` on the gateway and start
  `agent-designer-runner`.
- **Run fails because the runner is at capacity.** Wait for running graphs to
  finish, or raise `KIONGA_DESIGNER_MAX_RUNS`.
- **Every resource node fails with `resource_denied`.** The runner must reach
  the gateway's internal listener (port 8087) with the run credential, not
  through the public port.
- **Publish fails with a quality gate error.** The evaluation must be complete,
  must have passed, and must have evaluated the same behavior hash as the saved
  revision.
- **Deploy returns 503.** Deploying needs the Kubernetes managed runtime and
  `KIONGA_NATIVE_AGENT_IMAGE`, which Helm sets from `images.agent-runtime`.
  Locally, run the version from the designer.
- **Runs on Kubernetes report that the runner is not configured.** Set
  `agentDesigner.enabled` and create its token Secret; see
  [Enable the Agent Designer runner](../operations/managed-kubernetes.md#enable-the-agent-designer-runner).
