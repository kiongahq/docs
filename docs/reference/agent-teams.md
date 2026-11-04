---
icon: material/account-group-outline
description: Reference for agent teams, covering agent definitions, teams, runs, workers, routes, built-in and sandbox tools, events, error codes and limits.
---

# Agent teams reference

For step-by-step instructions, see [Build and run an agent team](../guides/agent-teams.md). All
resources are scoped to a project.

## Agent definition

Route: `/api/v1/agent-definitions`. IDs start with `agd-`.

```json
{
  "id": "agd-...",
  "project_id": "p",
  "revision": 1,
  "name": "bug-fixer",
  "description": "When to use this agent. Shown to the coordinator.",
  "instructions": "System prompt.",
  "model": "llm",
  "tools": [
    {"kind": "sandbox"},
    {"kind": "git", "repository": "https://github.com/o/r", "connection": "apc-..."},
    {"kind": "tool", "ref": "lookup"},
    {"kind": "connection", "ref": "apc-..."},
    {"kind": "knowledge", "ref": "kb-..."},
    {"kind": "dataset", "ref": "ds-..."}
  ],
  "workspace": "none",
  "limits": {"max_turns": 100, "max_tokens": 200000, "max_seconds": 3600}
}
```

| Field | Rule |
| --- | --- |
| `name` | Matches `^[a-z][a-z0-9-]{0,62}$`. Unique in the project. |
| `description` | At most 1000 characters. |
| `instructions` | At most 32000 characters. |
| `workspace` | `none` or `sandbox`. `sandbox` and `git` grants require `sandbox`. |
| `limits.max_turns` | 1 to 500. |
| `limits.max_tokens` | 1 to 5,000,000. |
| `limits.max_seconds` | 60 to 14400. |

Every save increments `revision`. Kionga keeps the last 20 revisions.

## Team

Route: `/api/v1/agent-teams`. IDs start with `agt-`.

```json
{
  "id": "agt-...",
  "project_id": "p",
  "revision": 1,
  "name": "code-change",
  "description": "...",
  "coordinator": {"instructions": "...", "model": "llm"},
  "members": ["agd-..."],
  "brief": "Shared rules appended to every agent's system prompt.",
  "limits": {"max_workers_total": 20, "max_concurrent_workers": 5, "max_tokens": 2000000, "max_seconds": 14400}
}
```

| Field | Rule |
| --- | --- |
| `members` | 1 to 16 agent definitions. |
| `brief` | At most 16000 characters. |
| `limits.max_workers_total` | 1 to 50. |
| `limits.max_concurrent_workers` | 1 to 16. |
| `limits.max_tokens` | 1 to 20,000,000. |
| `limits.max_seconds` | 60 to 86400. |

## Team run

Route: `/api/v1/team-runs`. IDs start with `atr-`. To start a run, send
`team_id`, `input`, `allow_side_effects` and, optionally, `idempotency_key`.

A run stores an immutable snapshot of the team and its member definitions with a
`content_sha256`, so later edits never change it. It also records `subject`, `roles`,
`usage` and `resume_count`.

| Run status | Meaning |
| --- | --- |
| `running` | Active, including while a worker waits on a retry or an approval. |
| `succeeded` | The coordinator finished. |
| `failed` | A team limit was reached, access was lost, or the run could not continue. |
| `cancelling` | Cancel was requested, and live workers are stopping. |
| `cancelled` | Stopped by a person. |

## Worker

IDs start with `atw-`. The coordinator is a worker with `role: coordinator`. Fields:
`agent`, `task`, `transcript`, `inbox`, `usage`, `turns`, `next_attempt_at`,
`lease_owner`, `lease_expires_at`, `report`, `last_error` and `sandbox_id`.

| Worker status | Meaning |
| --- | --- |
| `queued` | Waiting for a slot. |
| `running` | Holding a lease and taking turns. |
| `waiting_retry` | Waiting until `next_attempt_at` after a rate limit or provider failure. |
| `waiting_approval` | Waiting for a person to decide on a side effect. |
| `idle` | A coordinator with an empty inbox and live workers. |
| `completed` | Handed back a report. A new message resumes it. |
| `failed` | See `last_error`. |
| `cancelled` | Stopped with the run. |

## Routes

| Method and path | Purpose |
| --- | --- |
| `GET`, `POST /api/v1/agent-definitions` | List and create agents. |
| `GET`, `PUT`, `DELETE /api/v1/agent-definitions/{id}` | Read, update and delete an agent. |
| `GET /api/v1/agent-definitions/{id}/revisions` | List revisions. |
| `GET`, `POST /api/v1/agent-teams` | List and create teams. |
| `GET`, `PUT`, `DELETE /api/v1/agent-teams/{id}` | Read, update and delete a team. |
| `GET /api/v1/agent-teams/{id}/revisions` | List revisions. |
| `POST /api/v1/team-runs` | Start a run. |
| `GET /api/v1/team-runs?team_id=` | List runs. |
| `GET /api/v1/team-runs/{id}` | Read a run. |
| `GET /api/v1/team-runs/{id}/events?after=` | Read events by polling. |
| `GET /api/v1/team-runs/{id}/events/stream` | Stream events with server-sent events. |
| `GET /api/v1/team-runs/{id}/workers` | List workers. |
| `GET /api/v1/team-runs/{id}/workers/{wid}` | Read a worker. |
| `POST /api/v1/team-runs/{id}/messages` | Send a message as a person, with `to` and `text`. |
| `POST /api/v1/team-runs/{id}/cancel` | Cancel a run. |
| `POST /api/v1/team-runs/{id}/resume` | Put failed workers back in the queue after you fix the cause. |

Viewers can only read. Every route requires the `agents` service.

## Built-in tools

The server defines these tools. A graph or a model cannot add to them.

| Tool | Available to | Behavior |
| --- | --- | --- |
| `spawn_worker {agent, task}` | Coordinator | Starts a member. `agent` must be in the snapshot. `task` is at most 32000 characters. Never blocks. |
| `send_message {to, text}` | All | The coordinator can message any worker. A worker can message only the coordinator. A message to a `completed` worker resumes it. |
| `list_workers {}` | Coordinator | Returns name, status and last error. |
| `read_worker_file {worker, path}` | Coordinator | Read-only view of a file in a worker's sandbox. |
| `worker_diff {worker}` | Coordinator | Read-only view of a worker's changes. |
| `finish {report}` | All | A worker hands back to the coordinator. The coordinator ends the run, which is refused while workers are live. |

## Sandbox tools

Available when `workspace` is `sandbox`. Kionga creates one sandbox per worker on first
use.

| Tool | Behavior | Approval |
| --- | --- | --- |
| `exec {command, cwd?, timeout_seconds?}` | Runs a command. Default timeout 120 seconds, maximum 1800. | No |
| `read_file {path}` | Reads a file under `/workspace`. | No |
| `write_file {path, content}` | Writes a file under `/workspace`. | No |
| `edit_file {path, old, new}` | Replaces an exact, unique match. | No |
| `list_files {path}` | Lists a directory. | No |
| `search_files {pattern, path?}` | Searches files. | No |
| `git_clone {repository, ref?}` | Clones a granted repository. The host must be allowed. | No |
| `git_diff {}` | Shows changes in the workspace. | No |
| `git_push {branch}` | Pushes to `kionga/<run-id>/<name>`. Never the default branch, never force, never delete. | Yes |

Paths must stay under `/workspace`. Kionga rejects `..` and symlinks that escape it.
Tool output is capped at 64 KiB, keeping the head and tail and marking the result as
truncated, and is redacted before it is stored or sent to a model.

## Events

Events go to a paged log with a strictly increasing `seq`. Previews are redacted and at
most 2000 characters.

| Type | Meaning |
| --- | --- |
| `run.started` | The run started. |
| `run.resumed` | The run resumed. |
| `run.finished` | The run reached a final status. |
| `worker.spawned` | A worker was created. |
| `worker.turn` | A worker completed a model call. |
| `worker.tool_call` | A worker called a tool. |
| `worker.tool_result` | A tool returned. |
| `worker.retrying` | A worker is waiting to retry. |
| `worker.waiting_approval` | A worker is waiting for a person. |
| `worker.message` | A message was delivered. |
| `worker.finished` | A worker reached a final status. |

## Error codes

| Code | Meaning | What to do |
| --- | --- | --- |
| `context_exhausted` | Input is over the compaction threshold with only the 10 protected recent turns left. | Raise `KIONGA_TEAM_COMPACT_THRESHOLD_TOKENS`, or narrow the task. |
| `sandbox_unavailable` | The runtime or image allowlist is not ready. | See [Sandboxes and gVisor](../operations/sandboxes.md). |
| `side_effects_not_approved` | The run does not allow side effects. | Start a new run that allows them. |
| `outcome_unknown` | A side effect was interrupted and was not repeated. | Check the external system. |
| `budget_exceeded` | A worker or team limit was reached. | Raise the limit in a new run, or narrow the task. |
| `owner_access_lost` | The person who started the run lost access. | Restore access and start a new run. |
| `rate_limited` | The provider limited the call. Retried without using a turn. | Usually nothing. |
| `provider_unavailable` | The provider failed. Retried for up to 30 minutes. | After a failure, fix the provider and resume. |

## Settings

For gateway tuning variables and how to supply connection credentials, see
[Agent teams settings](configuration.md#agent-teams) and
[Secret references](configuration.md#secret-references).

## Message framing

Kionga wraps every inbound message and tool result in a `kionga-data` tag that names its
source, with a fresh nonce for each delivery. Only content with `source="person"` counts as
instructions. A claim of approval inside any other source is not approval.

## Not included

Agent teams do not include egress allowlists for sandboxes, nested teams, teams as a canvas
node, operator deployment of a team as a long-lived service, or per-tenant sandbox node
pools. Teams run from the console and the API.
