---
icon: material/shield-lock-outline
description: Kionga roles, services, access profiles, resource profiles, personal API keys, policy actions, and the security controls enforced on every request.
---

# Permissions

Kionga checks every API request, in every deployment, local and production alike.
The console shows or disables controls based on the same rules, but the API is
what enforces them: hiding a button is never the security boundary.

A request is allowed when all of these hold:

1. The caller is identified (see [How Kionga identifies callers](#how-kionga-identifies-callers)).
2. The caller's **role**, and for a normal `user` their **services**, open the route.
3. The resource is within the caller's **project scope**.
4. No **policy** denies the action, and the caller's role or a policy allows it.
5. **Quotas and resource limits** have room for the request.

To manage users, groups and policies, see
[Users, roles and policies](../guides/access-control.md).

## Roles

| Role | Can do |
| --- | --- |
| `admin` | Everything, including users, policies, connections and every project. Not subject to quotas. |
| `operator` | The same as `admin`. |
| `engineer` | Read everything; create and change projects, pipelines, models, agents, tools, features and functions; open workspaces. Cannot manage connections, users or policies. Limited to assigned projects when the access profile lists any. |
| `user` | Only the services and projects in their access profile, within its quotas. Without an access profile, only their identity, access requests and personal settings. |
| `viewer` | Read only. Cannot open workspaces. Limited to assigned projects when the access profile lists any. |
| `service` | Kionga's own services. Reads, and reports runs, steps, logs, traces, materializations and real-time statistics. Not for people. |

## Services

An access profile grants a normal `user` these services. A personal API key is
limited to the services it names.

| Service | Opens |
| --- | --- |
| `overview` | Overview dashboard, onboarding readiness, live event stream |
| `projects` | Projects and project templates |
| `git` | Connecting a project to a Git repository |
| `pipelines` | Pipeline flows, runs and logs |
| `models` | Models, serving, predictions and Hugging Face import |
| `agents` | Agents, sessions, traces and usage |
| `features` | Feature views and feature stores |
| `storage` | Object storage browsing, limited to the profile's buckets |
| `realtime` | Real-time statistics |
| `catalog` | Shared catalog, tools and prompts |
| `platform` | Connections, component health and log export status (read) |
| `functions` | Serverless functions |
| `workbench` | Opening the Jupyter workbench |
| `ide` | Opening the browser IDE |

## Access profiles

A normal `user` has no access until an administrator creates an access profile
whose `subject` exactly matches the person's identity (the OIDC `sub` claim, or
the local username). A role from the identity provider alone grants nothing. A
profile sets:

| Field | Meaning |
| --- | --- |
| `role` | The platform role |
| `services` | The services above |
| `project_ids` | Existing projects the person may use. Projects the person creates are theirs automatically. |
| `storage.size_gb`, `storage.buckets` | Storage capacity and the buckets the person may browse |
| `compute` | A resource profile, or custom limits: `vcpus`, `memory_gb`, `gpus`, `gpu_type`, `max_vms`, `max_projects`, `max_concurrent_runs`, `max_functions` |
| `disabled` | Suspends the person immediately |

Administrators manage profiles in **Users & access** or with
`PUT /api/v1/admin/users/{subject}`. A person without a profile can ask for
services from **My access → Request access**. Kionga blocks duplicate pending
requests, and records the reviewer and outcome of each approval or rejection in
the audit log.

### Resource profiles

| Profile | CPU (`vcpus`) | Memory | GPUs | Workloads (`max_vms`) | Projects | Concurrent runs | Functions | Storage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `starter` | 2 | 4 GB | 0 | 1 | 2 | 1 | 3 | 25 GB |
| `team` | 4 | 8 GB | 0 | 2 | 5 | 3 | 10 | 100 GB |
| `power` | 8 | 16 GB | 0 | 4 | 10 | 6 | 25 | 250 GB |
| `gpu` | 8 | 32 GB | 1 (`nvidia.com/gpu`) | 2 | 10 | 4 | 15 | 500 GB |
| `custom` | Set each limit yourself | | | | | | | |

### Quotas and resource admission

For a normal `user`, Kionga checks capacity before it starts any work:

| Request | Check |
| --- | --- |
| Create a project | Every service the template requires is granted; the requested profile fits the grant; `single-gpu` needs at least one GPU and `multi-gpu` at least two; the project count stays within `max_projects`. |
| Run a pipeline | Concurrent runs stay within `max_concurrent_runs`; the CPU, memory and GPU of the steps that can run at the same time fit the grant. |
| Deploy an agent | Every agent the person owns is counted at its maximum replicas, each replica with the agent's request plus `100m` CPU and `128Mi` memory for its trace sidecar. The total CPU, memory, GPUs and replicas must fit the compute grant and `max_vms`, and the GPU type must match a typed grant. |
| Deploy a function | CPU and memory fit the grant, and the function count stays within `max_functions`. |

A failed check returns `403 resource_not_provisioned`. `admin` and `operator`
are not limited, so they can provision and recover workloads. These limits are
Kionga's own allocations; on Kubernetes, also use resource quotas, limit ranges,
and network policies in the cluster.

## Personal API keys

Signed-in people create personal API keys under **Settings → Personal API keys**
for the CLI, the SDK, and automation outside Kionga. The Jupyter workbench and
browser IDE do not need a key. A key:

- starts with `nxs_`, is generated from 256 bits of randomness, and is shown once;
- is stored only as a SHA-256 hash;
- names services and projects that cannot exceed its creator's access;
- expires after 1 to 365 days;
- records when it was last used, and can be revoked immediately;
- acts as a normal `user` with the key's services and projects. Actions that
  check quotas, such as creating a project, need the creator to have an access
  profile;
- cannot call `/api/v1/admin/*`, `/api/v1/settings/*`, the editorial API, or
  open workspaces, and cannot widen its own scope.

```bash
export MLAIOPS_TOKEN='nxs_...'
curl -H "Authorization: Bearer $MLAIOPS_TOKEN" \
  "${MLAIOPS_URL:-http://localhost:8080}/api/v1/projects"
```

Keep keys in a secret manager or your OS keychain, never in source control.

## How Kionga identifies callers

Every request except the public routes (health, readiness, the OpenAPI document,
published blog posts and the `/auth/*` sign-in routes) needs a credential. Kionga
checks credentials in this order:

1. **Personal API key**: a bearer token that starts with `nxs_`.
2. **Bearer token**: the internal service token (`MLAIOPS_INTERNAL_TOKEN`) gives
   the `service` role. Otherwise, when `OIDC_ISSUER` is set, the token must be a
   valid RS256 JWT from that issuer (signature from `OIDC_JWKS_URL`, issuer,
   audience and expiry checked). An invalid bearer token is rejected; Kionga does
   not fall back to a cookie.
3. **Local session**: the `kionga_local_session` cookie from `/auth/local/login`,
   when local sign-in is enabled (no `OIDC_ISSUER`, or `KIONGA_LOCAL_LOGIN=true`
   next to single sign-on). The configured local username gets
   `MLAIOPS_LOCAL_ROLE` (default `admin`); other local accounts are `user`.
4. **Single sign-on session**: the `kionga_session` cookie set after sign-in
   through the identity provider.

When the person has an access profile, its role, services and projects replace
the ones from the credential. API keys and the `service` role keep their own
scopes.

Anonymous `/api/` requests get `401`; other pages redirect to sign-in. Signing out
also ends the session for API calls.

Local sign-in is throttled per account: after 5 failed attempts, each further
attempt waits twice as long as the previous one (1 s, 2 s, 4 s, up to 60 s), and
the sign-in page shows "Too many failed attempts for this account. Wait a minute
and try again." Failures are forgotten after 15 minutes or on a successful
sign-in.

Workspaces need a browser identity and the matching service. API keys and the
internal service token cannot open them.

### Roles from single sign-on

Roles come from the token's `roles` claim. Without one, each entry in the
`groups` claim maps to a role through `KIONGA_SSO_GROUP_ROLES`, and a group named
exactly like a role (`admin`, `operator`, `engineer`, `user`, `viewer`) counts as
that role. Groups never grant `service`. A person with no mapped group signs in
as a `user` without an access profile. See
[Single sign-on](../operations/single-sign-on.md).

## Policies

Policies refine what roles allow. Each statement allows or denies actions on
resources, optionally under conditions (source IP range, UTC hours, project tags,
resource profile). An explicit deny overrides every allow; with no matching allow,
the action is denied. Each role has a built-in baseline policy, so with no extra
policies, the role rules above apply unchanged. See
[Users, roles and policies](../guides/access-control.md) for the syntax and
examples.

| Action | Resource | Allows |
| --- | --- | --- |
| `project:Read` | `kionga:project/<project>` | Seeing a project and its metadata |
| `project:Create` | `kionga:project/*` | Creating a project; quotas still apply |
| `pipeline:Read` | `kionga:project/<project>/pipeline/<pipeline>` | Seeing flows, revisions and runs |
| `pipeline:Write` | `kionga:project/<project>/pipeline/<pipeline>` | Creating and changing flows, schedules and rollbacks; reporting run steps |
| `pipeline:Run` | `kionga:project/<project>/pipeline/<pipeline>` | Submitting, cancelling and retrying runs |
| `pipeline:OverrideParameters` | `kionga:project/<project>/pipeline/<pipeline>` | Overriding parameters for one run |
| `pipeline:OverrideResources` | `kionga:project/<project>/pipeline/<pipeline>` | Overriding a step's CPU, memory or GPU for one run |
| `pipeline:OverrideImage` | `kionga:project/<project>/pipeline/<pipeline>` | Overriding a step's container image for one run |
| `logs:Read` | `kionga:project/<project>/pipeline/<pipeline>` | Reading run logs |
| `workspace:Open` | `kionga:workspace/<kind>` or `kionga:project/<project>/workspace/<kind>` | Opening JupyterLab or the browser IDE |
| `feature:Read` | `kionga:feature/<name>` | Seeing feature views |
| `feature:Write` | `kionga:feature/<name>` | Applying feature views and reporting materializations |
| `secret:Read` | `kionga:connection/<id>` | Reserved; Kionga never returns secrets |
| `infra:Provision` | `kionga:connection/<id>` | Creating, testing and activating connections |
| `blog:Write` | `kionga:blog/<id>` | Creating and editing blog drafts |
| `blog:Publish` | `kionga:blog/<id>` | Publishing a blog post |
| `policy:Read` | `kionga:policy/<id>`, `kionga:user/<subject>` | Reading policies, groups and attachments; explaining another person's access |
| `policy:Write` | `kionga:policy/<id>`, `kionga:group/<id>` | Creating, changing and deleting policies and groups |
| `policy:Attach` | `kionga:policy/<id>` | Attaching or detaching a policy. You must already hold every action it grants. |
| `user:Manage` | `kionga:user/<subject>` | Provisioning, changing, suspending and revoking access and passwords; reviewing access requests |

`GET /api/v1/iam/catalog` returns this catalog from your running Kionga, and
`GET /api/v1/iam/explain` explains any single decision.

## Check your own access

`GET /api/v1/me` returns your identity and what you can do:

```json
{
  "subject": "you@example.com",
  "email": "you@example.com",
  "roles": ["user"],
  "mode": "oidc",
  "services": ["overview", "projects", "pipelines", "workbench"],
  "project_ids": ["prj-..."],
  "provisioned": true,
  "permissions": {
    "projects_write": true, "pipelines_write": true, "models_write": false,
    "agents_write": false, "tools_write": false, "features_write": false,
    "functions_write": false, "git_write": false, "connections_write": false,
    "access_manage": false, "iam_manage": false
  }
}
```

The response also includes `local_accounts`, `connector`, `access_request` and
`entitlements`. In the console, **My access** shows your role, services,
projects, buckets, compute allocation, quotas, and whether your account is
provisioned or suspended.

## Try a role locally

Give the local account the `viewer` role to see the read-only console:

```bash
export MLAIOPS_URL="${MLAIOPS_URL:-http://localhost:8080}"
MLAIOPS_LOCAL_ROLE=viewer docker compose -f deploy/compose.yaml up -d gateway
curl -fsS -o /dev/null -c kionga.cookies \
  --data-urlencode username=admin --data-urlencode password=mlaiops-local \
  "$MLAIOPS_URL/auth/local/login"
```

A write is denied and a read succeeds:

```bash
curl -s -b kionga.cookies -o /dev/null -w "%{http_code}\n" -X POST "$MLAIOPS_URL/api/v1/projects" \
  -H 'Content-Type: application/json' -d '{"name":"x","template":"blank"}'   # 403
curl -s -b kionga.cookies -o /dev/null -w "%{http_code}\n" "$MLAIOPS_URL/api/v1/projects"  # 200
```

To restore `admin`, recreate the gateway without the variable
(`docker compose -f deploy/compose.yaml up -d gateway`) and sign in again.

## The internal service token

Kionga's own services (the agent runtime, pipeline runner, feature materializer
and real-time processor) authenticate with `MLAIOPS_INTERNAL_TOKEN` and get the
`service` role: enough to report status, and nothing more. The local stack uses
the development value `kionga-local-service-token`. Anywhere else, generate a new
value, for example with `openssl rand -hex 24`. With
`KIONGA_ENVIRONMENT=production`, Kionga refuses to start with a token shorter
than 24 characters or one that contains `local` or `change-me`.

## Security controls

| Control | Local stack | Production |
| --- | --- | --- |
| Transport | HTTP on `localhost` | HTTPS, terminated by Caddy on a single server or by your ingress on Kubernetes |
| Sign-in | Local account and single sign-on through the bundled Dex | Single sign-on through your OIDC provider; optional break-glass local account |
| Session cookies | `HttpOnly`, `SameSite=Lax` | Also `Secure`: the local session cookie when the request arrives over HTTPS (directly or with `X-Forwarded-Proto: https`), the single sign-on cookie when `OIDC_REDIRECT_URL` is HTTPS |
| Response headers | `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and `X-Frame-Options: SAMEORIGIN` (except workspace pages served through Kionga) | Same |
| CORS | `*` | Your origin, from `MLAIOPS_ALLOWED_ORIGIN` |
| Network | Ports bind to `127.0.0.1` unless `KIONGA_BIND_ADDRESS` widens them | Single server: only ports 80 and 443. Kubernetes: default-deny network policies (`deploy/config/network/`) and optional strict mTLS (`deploy/config/network-istio/strict-mtls.yaml`). |
| Secrets | Development defaults | Mounted secret files; connections store only a reference to an environment variable |
| LLM provider keys | Environment only | Environment only; never written to traces, logs or Kionga's records |
| Object storage credentials | Held by the storage proxy and mounted into the shared workbench | Held by the storage proxy; isolate per-user access |

## Audit

Every change writes an immutable audit event (who, what, which resource, when),
available at `GET /api/v1/audit`. With PostgreSQL, the audit event is written in
the same transaction as the change itself.
