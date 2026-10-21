# RBAC & security

Authorization runs on **every** API request, in **every** deployment profile, local
and public alike. The rule table the console uses to enable/disable controls is
derived from the exact same `Allowed` function the API enforces, so the UI can never
drift from the backend.

## Roles

| Role | Can do |
| --- | --- |
| `admin`, `operator` | Everything, including user provisioning and platform connections |
| `user` | Only explicitly assigned services and projects, within assigned quotas |
| `engineer` | Full ML lifecycle (projects, pipelines, models, agents, tools, features, functions, realtime) but **not** platform connections |
| `viewer` | Read-only (all `GET` requests) |
| `service` | Internal reporting only: traces, pipeline step transitions, materialization reports, realtime stats |

The `engineer` write scope is the ML lifecycle paths; connections stay
admin/operator-only. The `service` role is deliberately narrow: it can report state
back to the control plane but cannot manage resources.

## User provisioning and entitlements

The `user` role is deny-by-default. An OIDC role alone does not grant access:
an administrator must create a profile whose `subject` exactly matches the
token's immutable `sub` claim. Profiles assign:

- platform services, including separate Jupyter workbench and IDE grants;
- existing project IDs, while projects created by the user are owned by them;
- storage capacity and an allow-list of buckets;
- vCPU, memory, VM, project, and concurrent-run limits;
- an immediate suspension switch.

Admins manage profiles in **Users & access** or through:

```text
GET    /api/v1/admin/users
PUT    /api/v1/admin/users/{subject}
DELETE /api/v1/admin/users/{subject}
```

Users who are not covered by an identity-provider group can submit a scoped
request from **My access → Request access**. Kionga prevents duplicate pending
requests, records the requested services and business reason, and exposes an
administrator approval queue. Provisioning from that queue marks the request
approved; rejection records the reviewer and note. Both actions are audited.

## Personal API keys

Signed-in users create personal API keys from **Settings → API keys**
for CLI, SDK, and automation running outside Kionga. The in-platform Jupyter
workbench and browser IDE do not need a personal key. A key:

- starts with `nxs_`, is generated from 256 bits of randomness, and is shown once;
- stores only a SHA-256 digest of the high-entropy secret;
- has explicit service/project scopes that cannot exceed the creator's access;
- must expire within 1–365 days;
- records last use and can be revoked immediately;
- acts as a normal `user` with the key's services and projects; its creator
  must have a provisioned access profile for quota-checked actions such as
  creating a project;
- cannot call settings/admin APIs or expand its own scope.

Use it as a bearer token:

```bash
export MLAIOPS_TOKEN='nxs_...'
curl -H "Authorization: Bearer $MLAIOPS_TOKEN" \
  "${MLAIOPS_URL:-http://localhost:8080}/api/v1/projects"
```

Store keys in an OS keychain or secret manager, never in source control.

Authorization is enforced in the gateway before handlers run. Collection
responses are project-filtered, direct resource lookups return `404` when the
resource is outside the user's scope, storage bucket requests are allow-listed,
and project/run creation fails when quota is exhausted. UI hiding is only a
convenience; it is never the security boundary.

The capacity fields are control-plane allocations consumed by workspace and
compute provisioners. They do not replace Kubernetes ResourceQuota, LimitRange,
network policy, or per-user workload identities in a multi-user deployment.

Project templates do not grant capacity. For normal users, project admission checks
every template-required service, verifies the requested profile fits the assigned
CPU/RAM/GPU/storage grant, requires at least one GPU for `single-gpu` and two for
`multi-gpu`, and preserves the existing project-count quota. Agent projects
similarly require the `agents` service and remain constrained to assigned project
IDs and tool/service access. Deploying an agent reserves the new request and every
existing agent owned by that subject at `max_replicas`. Each possible pod is charged
its agent CPU/RAM/GPU plus the trace sidecar's `100m` CPU and `128Mi` RAM; the summed
capacity and summed maximum replicas must fit the compute and workload (`max_vms`)
grants. GPU type must match a typed grant and must be a valid domain-qualified,
non-reserved Kubernetes extended resource name; it cannot alias native keys such as
`cpu` or `memory`.

Pipeline-definition admission calculates each potentially concurrent DAG layer and
rejects CPU, memory, or GPU totals above the grant. Function deployment separately
caps CPU and memory and enforces the function-count quota. Agent deployment applies
the replica-aware checks above before emitting desired state. These checks run before
calling Prefect/OpenFaaS or reconciling Kubernetes resources. Admin/operator roles
bypass admission limits so they can provision and recover platform workloads; the
normal `user` role never does.

## Where identity comes from

Every request except the public health, OpenAPI, blog, and `/auth/*` routes needs
a credential. The gateway resolves the principal in this order:

1. **Personal API key**: a bearer token starting with `nxs_`, resolved first and
   kept to its scoped permissions.
2. **Bearer token**: a bearer equal to `MLAIOPS_INTERNAL_TOKEN` (constant-time
   compared) yields the `service` role; otherwise, when `OIDC_ISSUER` is set,
   the gateway verifies the JWT (RS256, JWKS from `OIDC_JWKS_URL`, issuer,
   audience, expiry) and takes roles from its claims. An invalid bearer token
   fails; it never falls back to a cookie.
3. **Local session**: when local sign-in is enabled (no `OIDC_ISSUER`, or
   `KIONGA_LOCAL_LOGIN=true` next to single sign-on), the `kionga_local_session`
   cookie from `/auth/local/login`. The configured local username gets
   `MLAIOPS_LOCAL_ROLE` (default `admin`); other local accounts are `user`.
4. **Single sign-on session**: the `kionga_session` cookie set after the OIDC
   callback.

Anonymous `/api/` requests get `401`; other anonymous pages redirect to sign-in.
Logout invalidates the session for API calls as well. An administrator-managed
access profile for the subject then replaces the roles above.

Local sign-in is throttled per account: after 5 failed attempts each further
attempt waits a doubling delay (1 s, 2 s, 4 s, up to 60 s), and the login page
shows "Too many failed attempts for this account. Wait a minute and try again."
Failures are forgotten after 15 minutes or on success.

API keys and internal service credentials cannot open interactive developer
workspaces. Workspace requests require a browser identity and the matching
service grant.

### Roles from OIDC claims

Roles come from the token's `roles` claim. Without one, each `groups` entry is
mapped through `KIONGA_SSO_GROUP_ROLES`, and a group named exactly like a role
(`admin`, `operator`, `engineer`, `user`, `viewer`) counts as that role. Groups
never grant `service`. A signed-in person with no mapped group is an
unprovisioned `user`. See [Single sign-on](../operations/single-sign-on.md).

## Checking your identity

`GET /api/v1/me` returns your subject, email, roles, auth mode, and effective
permissions:

```json
{
  "subject": "you@example.com",
  "email": "you@example.com",
  "roles": ["user"],
  "services": ["overview", "projects", "pipelines", "workbench"],
  "provisioned": true,
  "mode": "oidc",
  "permissions": {
    "projects_write": true, "pipelines_write": true, "models_write": true,
    "agents_write": true, "tools_write": true, "features_write": true,
    "functions_write": true, "connections_write": false
  }
}
```

The console fetches this at load and disables any control your role cannot use
(with a tooltip explaining why), removes unassigned navigation, and hides
unassigned workbench links. Every signed-in user can open **My access** to see
their effective role, service grants, assigned projects and buckets, compute
allocation, quotas, and suspension/provisioning status.

## Trying it locally

Preview the read-only console by giving the local account the viewer role:

```bash
export MLAIOPS_URL="${MLAIOPS_URL:-http://localhost:8080}"
MLAIOPS_LOCAL_ROLE=viewer docker compose -f deploy/compose.yaml up -d gateway
curl -fsS -o /dev/null -c kionga.cookies \
  --data-urlencode username=admin --data-urlencode password=mlaiops-local \
  "$MLAIOPS_URL/auth/local/login"
```

Then a write is denied and a read succeeds:

```bash
curl -s -b kionga.cookies -o /dev/null -w "%{http_code}\n" -X POST "$MLAIOPS_URL/api/v1/projects" \
  -H 'Content-Type: application/json' -d '{"name":"x","template":"blank"}'   # 403
curl -s -b kionga.cookies -o /dev/null -w "%{http_code}\n" "$MLAIOPS_URL/api/v1/projects"  # 200
```

Restore admin by recreating the gateway without the override
(`docker compose -f deploy/compose.yaml up -d gateway`) and signing in again.

## The internal service token

In-platform reporters (agent runtime, pipeline flows, materializer, realtime
processor) authenticate with `MLAIOPS_INTERNAL_TOKEN` and get the `service` role:
enough to report sessions, steps, materializations, and stats, and nothing more.
Compose sets a development default (`kionga-local-service-token`). For anything
shared, generate one with `openssl rand -hex 24` and set it in `deploy/.env`;
production startup rejects tokens shorter than 24 characters or containing
`local` or `change-me`.

## Other security controls

| Control | Local | Public |
| --- | --- | --- |
| **Transport** | HTTP on localhost | HTTPS via Caddy (automatic Let's Encrypt) |
| **AuthN** | Local account session and single sign-on through Dex | OIDC authorization-code session and bearer tokens; optional break-glass local account |
| **Session cookies** | HttpOnly, SameSite=Lax | Also Secure: the local session cookie when the request arrives over HTTPS (directly or with `X-Forwarded-Proto: https`), the single sign-on cookie when `OIDC_REDIRECT_URL` is https |
| **Response headers** | `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and `X-Frame-Options: SAMEORIGIN` (except proxied `/workspaces/` paths) | Same |
| **CORS** | `*` | Pinned to `MLAIOPS_ALLOWED_ORIGIN` (your domain) |
| **Ports** | Published on `127.0.0.1` only (`KIONGA_BIND_ADDRESS` widens them) | Only Caddy (80/443); everything else internal-only |
| **Secrets** | Development defaults | `.env` on the VM; connections store only a secret *reference* |
| **LLM keys** | Environment only | Environment only; never written to traces, logs, or the store |
| **Object-store credentials** | Storage proxy and Jupyter mount | Storage proxy is the application credential holder; isolate per-user mounts |

## Network isolation (scale path)

On Kubernetes, `deploy/config/network/default-deny.yaml` + `platform-allow.yaml` provide
scoped NetworkPolicies, and `deploy/config/network-istio/strict-mtls.yaml` enables strict
mTLS. On Compose, the single private network plus the closed internal ports provide
the isolation boundary.

## Audit

Every mutation writes an immutable audit event (who, what, when), queryable at
`GET /api/v1/audit`. In Postgres mode, the audit write is part of the same
transaction as the resource change and the Kafka outbox entry.
