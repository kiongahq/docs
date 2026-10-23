---
icon: material/application-brackets-outline
description: Every Kionga REST API route, with its method, who can call it, and what it does.
---

# REST API reference

Kionga exposes one JSON API under `/api/v1`. The console, the
[Python SDK](python-sdk.md) and the [CLI](cli.md) all use it. A running Kionga also
serves an interactive explorer at `/api-docs.html` and the OpenAPI document at
`/api/openapi.json`.

## Conventions

| Item | Value |
| --- | --- |
| Base URL | Your Kionga URL. Locally `http://localhost:8080`, or the port in `GATEWAY_PORT`. Examples use `$MLAIOPS_URL`. |
| Request body | JSON with `Content-Type: application/json`. Unknown fields are rejected with `400 invalid_request`. |
| Errors | Non-2xx responses return `{"error": "<code>", "message": "<detail>"}`. A policy denial (`403 access_denied`) also returns the `decision` that denied it. |
| Common error codes | `400 invalid_request`, `401` (no or invalid credential), `403` (`Forbidden` when your role or services do not open the route, `access_denied` for a policy denial, `resource_not_provisioned` for a quota), `404 not_found`, `409 conflict`, `422 validation_error`, `502` when an engine fails, `503` when a runtime is not ready |
| Lists | Most list routes return `{"items": [...], "total": N}`. `GET /api/v1/projects` and `GET /api/v1/pipelines/runs` return a JSON array. |
| Scope | Lists contain only what the caller may see. A single resource outside the caller's scope returns `404`. |

## Authentication

Only these routes answer without a credential: `/api/v1/health`,
`/api/v1/ready`, `/api/openapi.json`, `/api-docs.html`, the published blog reads
(`GET /api/v1/blogs`, `GET /api/v1/blogs/{slug}`, and attached blog media), and
the `/auth/*` sign-in routes. Any other `/api/` request without a credential
returns `401`.

| Credential | How to send it | Acts as |
| --- | --- | --- |
| Browser session | The `kionga_local_session` cookie (local sign-in) or the `kionga_session` cookie (single sign-on) | The signed-in person, with their role and access profile |
| Personal API key | `Authorization: Bearer nxs_...`, created under **Settings → Personal API keys** | A normal `user` limited to the key's services and projects and to its creator's access profile. Never reaches `/api/v1/admin/*`, `/api/v1/settings/*`, the editorial API, or workspaces. |
| OIDC token | `Authorization: Bearer <JWT>` from the configured issuer | The token's subject and roles |
| Workspace identity | Automatic inside the Jupyter workbench and browser IDE, through their preset `MLAIOPS_URL` | The workspace owner. On the local stack, the local `admin` account. |
| Internal service token | `Authorization: Bearer <MLAIOPS_INTERNAL_TOKEN>` | The `service` role, for Kionga's own services |

To call the API with curl on the local stack, sign in once and reuse the cookie:

```bash
curl -fsS -o /dev/null -c kionga.cookies \
  --data-urlencode username=admin --data-urlencode password=mlaiops-local \
  "$MLAIOPS_URL/auth/local/login"
curl -s -b kionga.cookies "$MLAIOPS_URL/api/v1/me"
```

With a personal API key, send `-H "Authorization: Bearer $MLAIOPS_TOKEN"` instead.
Examples on other pages often leave the credential out for brevity.

### Sign-in routes

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/auth/providers` | Sign-in options for the sign-in page (`local` and single sign-on providers) |
| `GET` | `/auth/login` | Start sign-in. Shows the sign-in page, or redirects to the only provider. |
| `GET` | `/auth/sso/login?connector=<id>` | Start single sign-on with one provider |
| `GET` | `/auth/callback` | OIDC authorization-code callback |
| `POST` | `/auth/local/login` | Local sign-in with form fields `username`, `password` and optional `return_to`. Throttled per account after 5 failures. |
| `GET` | `/auth/logout` | End the session, including workspace sessions |

## Who can call a route

The **Access** column uses these terms. `admin` and `operator` can call every
route. A normal `user` also needs the service named in the **Service** column in
their access profile, and the project in their scope.

| Term | Who |
| --- | --- |
| public | Anyone, without a credential |
| signed-in | Any authenticated person, including a `user` without an access profile |
| read | Every role: `viewer`, `engineer`, `user` (with the service), `admin`, `operator`, and `service` |
| write | `engineer`, `admin`, `operator`, and a `user` with the service |
| admin | `admin` and `operator` only |
| reporting | The `service` role, used by Kionga's own services. `engineer`, `admin` and `operator` also pass; a normal `user` cannot call these routes. |

Policies attached to a person or group can further allow or deny specific
actions; see [Permissions](rbac.md).

## Identity, access and settings

| Method | Path | Access | Service | Purpose |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/health` | public | | Health check: `{"status":"ok",...}` |
| `GET` | `/api/v1/ready` | public | | Readiness, including the database |
| `GET` | `/api/openapi.json` | public | | OpenAPI document |
| `GET` | `/api/v1/me` | signed-in | | Caller identity, roles, services and effective permissions |
| `GET` | `/api/v1/project-options` | signed-in | | Minimal list of the caller's projects, for selectors |
| `GET` | `/api/v1/workspaces` | signed-in | | Jupyter and IDE availability for the caller |
| `POST` | `/api/v1/workspaces/{kind}/launch` | `engineer`, `admin`, `operator`, or a `user` with the service; browser sessions only | `workbench` or `ide` | Launch the Jupyter workbench (`workbench`) or browser IDE (`ide`) |
| `GET` | `/api/v1/access-requests` | signed-in | | The caller's access requests |
| `POST` | `/api/v1/access-requests` | signed-in | | Request one or more services, with a reason |
| `GET` | `/api/v1/settings/tokens` | signed-in, not with an API key | | List your personal API keys. Secrets are never returned. |
| `POST` | `/api/v1/settings/tokens` | signed-in, not with an API key | | Create a scoped, expiring personal API key |
| `DELETE` | `/api/v1/settings/tokens/{id}` | key owner | | Revoke a personal API key immediately |
| `GET`, `PUT`, `DELETE` | `/api/v1/settings/huggingface` | signed-in, not with an API key | | Read, connect, or forget your encrypted Hugging Face token |
| `GET` | `/api/v1/dashboard` | read | `overview` | Overview counts and recent runs |
| `GET` | `/api/v1/onboarding/readiness` | read | `overview` | Onboarding readiness score and checklist |
| `GET` | `/api/v1/events` | read | `overview` | Server-Sent Events stream that signals when data changed |
| `GET` | `/api/v1/audit` | read, except a normal `user` | | Immutable audit log |

## Administration

All routes in this section require the `admin` or `operator` role.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/admin/users` | List access profiles |
| `PUT` | `/api/v1/admin/users/{subject}` | Create or change an access profile: role, services, projects, buckets, compute and storage quotas, suspension |
| `DELETE` | `/api/v1/admin/users/{subject}` | Revoke all access |
| `PUT` | `/api/v1/admin/users/{subject}/local-password` | Set a provisioned user's local password (local sign-in must be enabled) |
| `DELETE` | `/api/v1/admin/users/{subject}/local-password` | Remove a user's local password |
| `GET` | `/api/v1/admin/resource-profiles` | The `starter`, `team`, `power`, `gpu` and `custom` resource profiles |
| `GET` | `/api/v1/admin/access-requests` | The access-request approval queue |
| `PATCH` | `/api/v1/admin/access-requests/{id}` | Approve or reject an access request |

### Policies and groups

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/v1/iam/catalog` | signed-in | Actions, resource formats, condition keys and resource profiles |
| `GET` | `/api/v1/iam/explain` | signed-in | The decision and its reasons for one action on one resource. Asking about another person needs `policy:Read`. |
| `GET` | `/api/v1/iam/effective` | signed-in | The policies that apply to a principal |
| `GET`, `POST` | `/api/v1/admin/iam/groups` | admin | List or create groups |
| `GET`, `PUT`, `DELETE` | `/api/v1/admin/iam/groups/{id}` | admin | Read, change or delete a group |
| `GET`, `POST` | `/api/v1/admin/iam/policies` | admin | List or create policies |
| `GET`, `PUT`, `DELETE` | `/api/v1/admin/iam/policies/{id}` | admin | Read, change or delete a policy |
| `GET` | `/api/v1/admin/iam/policies/{id}/revisions` | admin | A policy's immutable revisions |
| `GET` | `/api/v1/admin/iam/policies/{id}/revisions/{version}` | admin | One policy revision |
| `GET`, `POST` | `/api/v1/admin/iam/attachments` | admin | List attachments, or attach a policy to a user or group |
| `DELETE` | `/api/v1/admin/iam/attachments/{id}` | admin | Detach a policy |

Request and response bodies are in
[Users, roles and policies](../guides/access-control.md#api).

## Projects

| Method | Path | Access | Service | Purpose |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/project-templates` | read | `projects` | List project templates |
| `GET` | `/api/v1/project-templates/{id}` | read | `projects` | One template. Optional `version` query parameter. |
| `GET` | `/api/v1/projects` | read | `projects` | List projects (JSON array) |
| `POST` | `/api/v1/projects` | write | `projects` | Create a project from a template, optionally connected to Git |
| `GET` | `/api/v1/projects/{id}` | read | `projects` | A project and its repository |
| `PUT` | `/api/v1/projects/{id}/repository` | write | `git` | Connect a Git repository (`url`, `default_branch`). Credentials are never stored. |
| `GET` | `/api/v1/projects/{id}/scaffold-plan` | read | `projects` | What a starter-code job would run, and where |
| `GET` | `/api/v1/projects/{id}/scaffold-jobs` | read | `projects` | List starter-code jobs |
| `POST` | `/api/v1/projects/{id}/scaffold-jobs` | write, browser sessions only | `projects` | Generate starter code in your workspace ([Scaffolding](../guides/scaffolding.md)) |
| `GET` | `/api/v1/projects/{id}/scaffold-jobs/{job}` | read | `projects` | One starter-code job |

Create a project with explicit framework, accelerator and profile:

```bash
curl -s -X POST "$MLAIOPS_URL/api/v1/projects" \
  -H 'Content-Type: application/json' \
  -d '{
    "name":"vision-foundation-eval",
    "description":"Multi-GPU evaluation and fine-tuning",
    "template":"distributed-training",
    "framework":"pytorch-ddp",
    "accelerator":"multi-gpu",
    "requested_profile":"gpu",
    "repository_url":"git@github.com:acme/vision-foundation-eval.git",
    "default_branch":"main"
  }'
```

| Field | Default |
| --- | --- |
| `template` | `production-ml` |
| `template_version` | The template's current version |
| `framework` | The template's first framework |
| `accelerator` | The template's first accelerator |
| `requested_profile` | The template's recommended profile; one of `starter`, `team`, `power`, `gpu`, `custom` |

The response pins `template_version`, the resolved framework, accelerator and
profile, the template's capabilities, and a `scaffold_command`. An unsupported
combination returns `422 validation_error`. For a normal user, a missing required
service or too little compute or GPU capacity returns `403
resource_not_provisioned`: `single-gpu` needs one provisioned GPU and `multi-gpu`
needs at least two. Administrators and operators are not subject to these checks.

## Pipelines and logs

| Method | Path | Access | Service | Purpose |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/pipelines/runs` | read | `pipelines` | List runs (JSON array) |
| `GET` | `/api/v1/pipelines/runs/{id}` | read | `pipelines` | One run with its steps and logs. Logs are removed when `logs:Read` is denied. |
| `POST` | `/api/v1/pipelines/submit` | write | `pipelines` | Start a run of the built-in pipeline (`name`) or a flow (`definition_id`), with `parameters` and optional `overrides` |
| `POST` | `/api/v1/pipelines/preflight` | write | `pipelines` | Check a run's configuration without starting it |
| `POST` | `/api/v1/pipelines/runs/{id}/cancel` | write | `pipelines` | Cancel a run, including in the engine |
| `POST` | `/api/v1/pipelines/runs/{id}/retry` | write | `pipelines` | Retry a run |
| `POST` | `/api/v1/pipelines/runs/{id}/steps` | reporting | | Report a step transition |
| `POST` | `/api/v1/pipelines/runs/{id}/logs` | reporting | | Report log lines |
| `GET` | `/api/v1/pipelines/definitions` | read | `pipelines` | List flows |
| `POST` | `/api/v1/pipelines/definitions` | write | `pipelines` | Create a flow from JSON |
| `POST` | `/api/v1/pipelines/definitions/yaml` | write | `pipelines` | Create a flow from `kionga.dev/v1` `Pipeline` YAML |
| `GET` | `/api/v1/pipelines/definitions/{id}` | read | `pipelines` | One flow |
| `PUT` | `/api/v1/pipelines/definitions/{id}` | write | `pipelines` | Save a new revision from JSON |
| `GET` | `/api/v1/pipelines/definitions/{id}/yaml` | read | `pipelines` | Export the current revision as canonical YAML |
| `PUT` | `/api/v1/pipelines/definitions/{id}/yaml` | write | `pipelines` | Save a new revision from YAML |
| `POST` | `/api/v1/pipelines/validate` | write | `pipelines` | Validate a flow; returns canonical YAML, SHA-256, stages and issues |
| `GET` | `/api/v1/pipelines/definitions/{id}/revisions` | read | `pipelines` | List immutable revisions |
| `GET` | `/api/v1/pipelines/definitions/{id}/revisions/{revision}` | read | `pipelines` | One revision |
| `POST` | `/api/v1/pipelines/definitions/{id}/revisions/{revision}/rollback` | write | `pipelines` | Save an old revision as the new current revision |
| `POST` | `/api/v1/pipelines/definitions/{id}/triggers/{index}/pause` | write | `pipelines` | Pause a schedule |
| `POST` | `/api/v1/pipelines/definitions/{id}/triggers/{index}/resume` | write | `pipelines` | Resume a schedule |
| `GET` | `/api/v1/logs` | read | `pipelines` | Filtered, paginated logs ([Logs and events](../guides/logs.md)) |
| `GET` | `/api/v1/logs/stream` | read | `pipelines` | Server-Sent Events log tail |

A flow's steps form a dependency graph through `jobs[].depends_on`. Kionga
rejects duplicate step names, missing dependencies, cycles, invalid resource
quantities and unknown function references before saving.

For a normal user, Kionga adds up the CPU, memory and GPU of the steps that can
run at the same time. If the widest such group exceeds the user's grant, the
request returns `403 resource_not_provisioned`. Steps that run one after another
are not added together. See [Pipelines](../guides/pipelines.md).

## Models

| Method | Path | Access | Service | Purpose |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/models` | read | `models` | List models |
| `POST` | `/api/v1/models` | write, or the `service` role | `models` | Register a model version: `project_id`, `name`, `version`, `artifact_uri`, `metrics`, optional `serving_image` |
| `POST` | `/api/v1/models/{id}/promote` | write | `models` | Move to `stage`: `staging`, `production` or `archived` |
| `POST` | `/api/v1/models/{id}/deploy` | write | `models` | Start a model server; `canary_weight` from 0 to 100 |
| `POST` | `/api/v1/models/{id}/rollback` | write | `models` | Return to the previous stage and remove the model server |
| `POST` | `/api/v1/models/{id}/predict` | write | `models` | Send a prediction request to the live endpoint (MLflow `/invocations` format) |
| `GET` | `/api/v1/models/huggingface` | read | `models` | Search the Hugging Face Hub (`search`, `task`) |
| `POST` | `/api/v1/models/huggingface/import` | write | `models` | Register a pinned Hub revision in a project ([Hugging Face models](../guides/huggingface.md)) |

Registering the same project, name and version twice returns `409 conflict`. A
model whose registered `accuracy` is below `0.8` gets the gate `failed`, and a
Hugging Face import gets `needs_evaluation`. Only a model with the gate `passed`
can be promoted to `production` or deployed. `predict` returns `409 not_serving`
when the model has no live endpoint.

`serving_image` pins the version to a container image that provides the `mlflow`
command and the exact libraries needed to load the model. Without it, the serving
manager uses its `SERVE_IMAGE`.

## Agents and tools

| Method | Path | Access | Service | Purpose |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/agents` | read | `agents` | List agents with live `status` and `endpoint_url` |
| `POST` | `/api/v1/agents` | write | `agents` | Deploy an agent |
| `PUT` | `/api/v1/agents/{id}/traffic` | write | `agents` | Set `canary_weight` |
| `POST` | `/api/v1/agents/{id}/invoke` | write, or the `service` role | `agents` | Run one turn: `message`, optional `session_id` and `user_id` |
| `GET` | `/api/v1/agents/{id}/sessions` | read | `agents` | List sessions |
| `GET` | `/api/v1/agents/{id}/traces` | read | `agents` | List traces |
| `GET` | `/api/v1/agents/{id}/usage` | read | `agents` | Session count, active sessions, tokens and cost |
| `POST` | `/api/v1/traces` | reporting | | Record a session turn or trace |
| `GET` | `/api/v1/tools` | read | `catalog` | List tools |
| `POST` | `/api/v1/tools` | write | `catalog` | Register a tool: `name`, `version`, `description`, `tags`, `input_schema` |

`POST /api/v1/agents` fields:

| Field | Required | Default and rules |
| --- | --- | --- |
| `project_id` | Yes | A project in your scope |
| `name` | Yes | Lowercase DNS label |
| `version` | Yes | Letters, digits, `.`, `_`, `+` and `-` |
| `image` | Yes | Container image reference, up to 512 characters |
| `graph_module` | Yes | `package.module:attribute` |
| `llm_backend` | No | `mock`, `openai`, `anthropic`, `openai-compatible` or `self-hosted` |
| `tools` | No | Names of tools registered in Kionga |
| `autoscaling` | No | `min_replicas` and `max_replicas`; default 1 and 1. The maximum must be at least the minimum and at most 100. |
| `resources` | No | `cpu` (default `500m`), `memory` (default `1Gi`), `gpu` (default 0), `gpu_type` (default `nvidia.com/gpu` when `gpu` is above 0) |
| `replicas` | No | Older form of `autoscaling.min_replicas` |

`gpu_type` must be a domain-qualified extended resource name. Kubernetes-reserved
domains and native names such as `cpu` and `memory` are rejected. Invalid values
return `422 validation_error`.

For a normal user, Kionga reserves every agent the user owns at its maximum
replica count. Each possible replica counts the agent's request plus `100m` CPU and
`128Mi` memory for its trace sidecar. The total, including GPUs and replicas, must
fit the user's compute and workload grant, or the request returns `403
resource_not_provisioned`.

`GET /api/v1/agents` reports `ready` only when the agent's runtime answers its
health check at request time. `invoke` checks health again and returns `503
agent_not_ready` without sending the turn when the runtime is unavailable.

## Features

| Method | Path | Access | Service | Purpose |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/features` | read | `features` | List feature views |
| `POST` | `/api/v1/features` | write, or the `service` role | `features` | Apply a feature view |
| `POST` | `/api/v1/features/{name}/materialized` | reporting | | Report online materialization and entity count |
| `POST` | `/api/v1/features/{name}/materializations` | write, or the `service` role | `features` | Report a materialization run for lineage |
| `GET` | `/api/v1/features/{name}/versions` | read | `features` | Immutable definition versions |
| `GET` | `/api/v1/features/{name}/lineage` | read | `features` | Materialization lineage |
| `GET` | `/api/v1/features/views` | read | `features` | Views with store, freshness, version and failures |
| `GET` | `/api/v1/features/stores` | read | `features` | Feature stores shared with the caller's projects |
| `GET`, `POST` | `/api/v1/admin/feature-stores` | admin | | List or connect feature stores ([Feature store integrations](../guides/feature-stores.md)) |
| `GET`, `PUT`, `DELETE` | `/api/v1/admin/feature-stores/{id}` | admin | | Read, change or remove a feature store |
| `POST` | `/api/v1/admin/feature-stores/{id}/test` | admin | | Check a feature store |
| `GET` | `/api/v1/admin/feature-store-providers` | admin | | Supported providers and their capabilities |

## Storage

| Method | Path | Access | Service | Purpose |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/storage/buckets` | read | `storage` | List buckets |
| `GET` | `/api/v1/storage/objects` | read | `storage` | List objects (`bucket`, `prefix`) |
| `GET` | `/api/v1/storage/object` | read | `storage` | Preview the start of an object (`bucket`, `key`) |
| `GET`, `POST` | `/api/v1/admin/storage-connections` | admin | | List or register external S3-compatible buckets ([External object storage](../operations/external-storage.md)) |
| `GET`, `PUT`, `DELETE` | `/api/v1/admin/storage-connections/{id}` | admin | | Read, change or remove a storage connection |
| `POST` | `/api/v1/admin/storage-connections/{id}/test` | admin | | Check access to the bucket |

A normal user sees only the buckets in their access profile.

## Platform, catalog and prompts

| Method | Path | Access | Service | Purpose |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/connections` | read | `platform` | List connections |
| `POST` | `/api/v1/connections` | admin | | Create a connection: `name`, `type`, `endpoint`, `secret_ref` (`none` or `env:VARIABLE`) |
| `POST` | `/api/v1/connections/{id}/test` | admin | | Health-check a connection now |
| `POST` | `/api/v1/connections/{id}/activate` | admin | | Use a Prefect or OpenFaaS connection for new operations |
| `GET` | `/api/v1/components` | read | `platform` | Live health of each platform component |
| `GET` | `/api/v1/observability/log-export` | read | `platform` | Log exporter state ([Log export](../operations/log-export.md)) |
| `GET` | `/api/v1/catalog` | read | `catalog` | Shared catalog; `kind` filter: `model`, `feature`, `agent`, `tool` |
| `GET` | `/api/v1/prompts` | read | `catalog` | Langfuse prompt library |

## Real-time and functions

| Method | Path | Access | Service | Purpose |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/realtime` | read | `realtime` | Live statistics for the real-time examples |
| `POST` | `/api/v1/realtime/{demo}` | reporting | | Report stream statistics |
| `GET` | `/api/v1/functions` | read | `functions` | List functions and whether OpenFaaS is configured |
| `POST` | `/api/v1/functions` | write | `functions` | Deploy a function: `project_id`, `name`, `image`, optional `cpu`, `memory`, `env_vars`, `labels`, `annotations` |
| `DELETE` | `/api/v1/functions/{name}` | write | `functions` | Remove a function |
| `POST` | `/api/v1/functions/{name}/invoke` | write | `functions` | Invoke a function with the request body as payload |
| `POST` | `/api/v1/functions/{name}/invoke-async` | write | `functions` | Queue an invocation and return its call ID |

For a normal user, a function's CPU or memory above the user's grant returns
`403 resource_not_provisioned`, and the function count is limited by the user's
quota.

## Engineering blog

Published posts are public. Writing uses a separate editorial membership and
session, not platform roles; personal API keys and the `service` role cannot
use it. See [Engineering blog](../guides/engineering-blog.md).

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/v1/blogs` | public | List published posts |
| `GET` | `/api/v1/blogs/{slug}` | public | Read a published post |
| `GET` | `/media/blog/{id}/{variant}` | public once attached to a published post | Image variant: `480`, `960` or `1600` pixels wide |
| `GET`, `POST` | `/api/v1/editorial/bootstrap` | local `admin` or an ML admin, once | Check or grant the first editorial admin |
| `POST`, `GET`, `DELETE` | `/api/v1/editorial/session` | editorial member with a verified identity | Open, read or end the editorial session (`kionga_editorial` cookie) |
| `GET`, `POST` | `/api/v1/editorial/posts` | editorial session | List posts, or create a draft |
| `GET`, `PUT` | `/api/v1/editorial/posts/{id}` | editorial session | Read, or save with `base_revision`. A conflict returns `409` with the `latest` revision. |
| `POST` | `/api/v1/editorial/posts/{id}/transition` | editorial session, role-checked | `submit`, `withdraw`, `request_changes`, `publish`, `schedule`, `unpublish`, `archive` or `restore` |
| `GET` | `/api/v1/editorial/posts/{id}/revisions` | editorial session | List revisions |
| `GET` | `/api/v1/editorial/posts/{id}/revisions/{number}` | editorial session | One revision |
| `POST` | `/api/v1/editorial/posts/{id}/revisions/{number}/restore` | editorial session | Restore a revision |
| `GET` | `/api/v1/editorial/posts/{id}/compare` | editorial session | Compare revisions (`from`, `to`) |
| `GET` | `/api/v1/editorial/posts/{id}/markdown` | editorial session | Export a post as Markdown |
| `POST` | `/api/v1/editorial/markdown` | editorial session | Import Markdown |
| `POST` | `/api/v1/editorial/preview` | editorial session | Render a preview |
| `GET`, `POST` | `/api/v1/editorial/media` | editorial session | List media, or upload an image (up to 10 MB) |
| `PATCH` | `/api/v1/editorial/media/{id}` | editorial session | Change alt text, caption or attribution |
| `GET` | `/api/v1/editorial/members` | editorial session | List editorial members |
| `PUT`, `DELETE` | `/api/v1/editorial/members/{subject}` | editorial admin | Add, change or remove a member |
| `GET`, `PUT` | `/api/v1/editorial/settings` | editorial session; editorial admin to change | Blog headline and description |

## Attribution

Changes are attributed to the authenticated caller: the email when known,
otherwise the subject. Kionga's own services are recorded as `internal-service`.
The `X-MLAIOps-Actor` header that the SDK and CLI can send is used only when the
request has no authenticated identity.
