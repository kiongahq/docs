---
description: arc42 section 8. Concepts that apply across Kionga's building blocks, including identity, authorization, tenancy, configuration, observability, errors and persistence.
---

# 8. Crosscutting concepts

These concepts apply to several building blocks at once. When you change one of
them, check every component that relies on it.

## Security and identity

Kionga recognizes four kinds of credential. The gateway resolves them in this order
(`platform/go/internal/auth/authenticator.go`, `platform/go/internal/auth/token.go`):

| Credential | Presented as | Principal |
| --- | --- | --- |
| Personal API key | `Authorization: Bearer nxs_...` | Role `user` limited to the key's services and projects; the key's scope can never exceed the creator's grants. Stored only as a SHA-256 digest. |
| Internal service token | `Authorization: Bearer <MLAIOPS_INTERNAL_TOKEN>` | `internal-service` with role `service`; compared in constant time |
| OIDC bearer token | `Authorization: Bearer <JWT>` | Subject, email, groups and roles from the verified token |
| Browser session | `kionga_local_session` (local account) or `kionga_session` (single sign-on) cookie | The signed-in subject |

Only the `Bearer` scheme counts as a credential. Other `Authorization` schemes, such
as the token header Jupyter sends through the workspace proxy, are ignored so the
browser session decides.

**Single sign-on.** The gateway is an OIDC relying party. It uses the authorization
code flow with PKCE (S256), a `state` cookie and an ID-token `nonce`, verifies tokens
against the issuer's JWKS (RSA keys, cached for 10 minutes), and checks issuer and
audience. `KIONGA_SSO_SINGLE_TENANT=true` assigns the configured tenant to tokens that
carry none (Dex cannot add a tenant claim); a token that names a different tenant is
rejected. Roles come from the token's `roles` claim when it has one. Otherwise
identity-provider groups map to roles through `KIONGA_SSO_GROUP_ROLES`, and a group
whose name equals a human role (`admin`, `operator`, `engineer`, `user`, `viewer`)
maps to that role directly; no group maps to `service`. A first sign-in with no profile follows the
sign-up policy (`KIONGA_SIGNUP`: `approval`, `open` or `off`). See
[decision 0006](../decisions/0006-oidc-single-sign-on-dex.md) and the
[sign-in sequence](06-runtime-view.md#sign-in-through-single-sign-on).

**Local accounts.** Without an issuer, local accounts are the development default.
Next to single sign-on they are break-glass access and require
`KIONGA_LOCAL_LOGIN=true` plus an explicit `MLAIOPS_LOCAL_PASSWORD`. Passwords for
provisioned local accounts are `bcrypt` hashes; verification of an unknown account still
runs a `bcrypt` comparison so timing does not reveal which accounts exist. After five
failures for one account, each attempt waits a doubling delay capped at one minute.
The throttle is per account, not per address, because every request behind the TLS
edge shares the proxy's address.

**Browser hardening.** Session cookies are `HttpOnly` and `SameSite=Lax`, and
`Secure` over HTTPS. Every response carries `X-Content-Type-Options: nosniff` and
`Referrer-Policy: strict-origin-when-cross-origin`; every response outside
`/workspaces/` also carries `X-Frame-Options: SAMEORIGIN`. CORS reflects
`MLAIOPS_ALLOWED_ORIGIN`, which production requires. Return-to targets pass through
`safeReturnTo`, so a login cannot redirect off-site.

**Workspace origins.** On Kubernetes with `KIONGA_WORKSPACE_BASE_DOMAIN`, each
workspace is served from its own host under that domain. `WorkspaceHostRouter` keeps
those requests away from the console and auth routes. Production requires the
workspace domain to differ from the console host but share its registrable site, so
workspace cookies stay host-only. A separate cluster-internal listener on port 8087
accepts only verified workspace identities and is never exposed through the Ingress.

**Editorial identity.** The engineering blog uses its own memberships and its own
`kionga_editorial` session on top of the platform identity. Platform roles neither
grant nor deny editorial access, and service identities and API keys never reach it
([decision 0002](../decisions/0002-blog-editor.md)).

**Supply chain.** Vendored browser libraries are loaded with integrity
hashes that a UI test recomputes. Images are built on `distroless` static bases for Go
services and published with provenance and an SBOM. CI fails on reachable
vulnerabilities, static-analysis findings and leaked secrets
([CI gates](../contributing/index.md#ci-gates)).

## Authorization, RBAC and IAM policies

Authorization has two layers (`platform/go/internal/httpapi/authorize.go`).

1. **Coarse gate.** `auth.Allowed` runs in the RBAC middleware on every `/api/` and
   `/workspaces/` request, in every deployment profile. It decides from the role,
   the provisioned services and the request path whether the caller may use that API
   surface at all. A normal `user` reaches only the services an administrator
   assigned; `/api/v1/admin/` requires `admin` or `operator`; `service` may only read
   and write the reporting paths. `auth.Permissions` derives the console's control
   gates from the same function, so the UI cannot drift from enforcement.
2. **Policy evaluation.** For the covered actions, the handler evaluates the caller's
   role baseline (a managed policy equivalent to the role, scoped to assigned projects)
   plus every policy attached to the caller or their groups. The evaluator in
   `platform/go/internal/policy` is pure: default deny, an explicit deny anywhere wins,
   otherwise any allow allows. Statements match actions and `kionga:` resource
   patterns and can carry IP CIDR, UTC hours, resource tag and resource profile
   conditions. A `403` names the deciding statement.

Policy evaluation currently covers pipelines, projects, workspace launch, features,
user provisioning, connections and IAM administration. Models, agents, functions and
storage rely on the role gate plus project assignment: their handlers return `404` for
an object outside the caller's projects. The `blog:*` actions in the catalog are not
enforced; the blog uses editorial memberships. Administration of policies has
anti-escalation, self-lockout and last-administrator protection.

The role and action reference is in the product documentation:
[permissions](https://kiongahq.github.io/docs/reference/rbac/) and
[users, roles and policies](https://kiongahq.github.io/docs/guides/access-control/).

## Multi-tenancy and isolation

Kionga isolates at three levels.

| Level | Mechanism | Limit |
| --- | --- | --- |
| Tenant | One tenant per gateway process (`MLAIOPS_TENANT`, default `default`). Every connection sets `app.tenant_id`; every table has a `tenant_id` column and a forced row-level security policy on it. | PostgreSQL superusers and roles with `BYPASSRLS` skip row-level security, so the gateway must connect as an ordinary role for the policy to isolate anything |
| Project | Resources belong to a project. Normal users see their owned and assigned projects; reads outside them return `404`, and the SSE digest counts only visible objects. | Administrators and operators see everything in the tenant |
| Workload | On Kubernetes, one `KiongaWorkspace` per access grant with its own PVC, credentials and resource limits, in a namespace with a ResourceQuota and default-deny network policies; agents get their own Deployments | Compose shares one workbench and one agent runtime; it is not a multi-user boundary |

**Quota admission.** For normal users the gateway checks requests against the
administrator's grant before persisting desired state: project templates against
service, profile and GPU grants; the widest concurrent layer of a pipeline against
CPU, memory and GPU; functions against CPU, memory and count quotas; and every owned
agent at maximum replicas, including `100m` CPU and `128Mi` memory per trace sidecar.
GPU types must be valid, domain-qualified Kubernetes extended-resource names that
match the grant. Administrators and operators bypass these limits explicitly. Details
are in [backend contracts](../contracts/backend.md).

## Configuration and secrets

Every Go service calls `runtimeconfig.Load` at startup
(`platform/go/internal/runtimeconfig/config.go`, copied into `serving` and
`trace-proxy`):

1. `KIONGA_CONFIG_FILE` names a JSON object of non-secret string values. A key that
   names a secret (`*PASSWORD*`, `*SECRET*`, `*TOKEN*` except `OIDC_TOKEN_URL`,
   `*API_KEY*`, any `*_FILE`, or a listed secret name) is rejected. Values never
   override an environment variable that is already set.
2. For each known secret name, `<NAME>_FILE` points at a file holding the value. Setting
   both the variable and the file is an error; an empty file is an error; files are
   capped at 64 KiB.

The gateway then runs `ValidateGateway`. With `KIONGA_ENVIRONMENT=production` it
refuses to start unless:

- the database, OIDC, internal token, credential key and allowed origin are all set;
- every OIDC URL and the allowed origin are HTTPS without user information;
- `OIDC_REDIRECT_URL` is the allowed origin's host plus `/auth/callback`;
- `DATABASE_URL` uses `sslmode=verify-full`;
- `OIDC_CLIENT_SECRET` and `MLAIOPS_INTERNAL_TOKEN` are at least 24 characters and do
  not contain `local` or `change-me`;
- a break-glass password, when enabled, is at least 16 characters and not a
  development default;
- `KIONGA_CREDENTIAL_KEY` decodes to 32 bytes (it seals connected-account tokens with
  AES-GCM);
- workspace domains, when set, satisfy the isolation rules above.

Locally, `deploy/.env` supplies values to Compose and every development default is
visible in `deploy/compose.yaml`. On a server and on Kubernetes, secrets arrive as
files (`vm/up.py`, or the chart's `/run/secrets` mount with `<NAME>_FILE`).

## Observability

| Signal | Where it comes from | Where it goes |
| --- | --- | --- |
| Audit events | Every mutation, in the same transaction as the change | `audit_events` table; `GET /api/v1/audit`; the `mlaiops.audit.operations` topic |
| Structured logs | Pipeline runner streaming, platform step events, Kubernetes Job events | `log_entries` (row-level security, cursor pagination, retention by `KIONGA_LOG_RETENTION_DAYS`); the Logs page and an SSE tail; optional export to Elasticsearch or OpenSearch |
| Secret redaction | `platform/go/internal/redact` masks known credential patterns and the exact values of secret environment variables | Applied before logs are stored or exported |
| Gateway metrics | `kionga_gateway_requests_total` and `kionga_gateway_request_duration_seconds`, by bounded route category | Separate listener on `METRICS_PORT` |
| Platform metrics | Metrics collector (pipeline outcomes, agent usage, real-time statistics, component health) | Prometheus; ServiceMonitors in the Helm chart |
| LLM traces | Trace proxy event per call; agent runtime session report with measured tokens and cost; Langfuse callbacks | `mlaiops.llm.traces`; agent sessions and traces in the gateway; Langfuse |
| Component health | Bounded active checks of connections and engines | `/api/v1/components`, the Platform page |
| Live updates | `GET /api/v1/events` sends a per-caller digest of visible state every three seconds | The console reloads the active view only when the digest changes |

Health endpoints: the gateway exposes `/api/v1/health` (health) and `/api/v1/ready`
(readiness, used by Caddy and Kubernetes); the Go services expose `/healthz`.

## Error handling and fail-closed behavior

- **Startup.** Unsafe or incomplete production configuration stops the process with a
  message that names the setting.
- **API errors.** Handlers answer with `{"error": "<code>", "message": "<text>"}`.
  Store errors map to `404 not_found`, `409 conflict` or `422 validation_error`;
  authorization failures to `401` or `403`; objects outside the caller's projects to
  `404`.
- **Engine failures.** When an engine rejects work, the control plane records the
  failure on the resource: a pipeline step fails with the engine's message, a model
  deployment is marked `failed` and returns `502 serving_failed`, an unready agent
  returns `503 agent_not_ready` before anything is forwarded. An not configured optional
  engine reports `configured: false` instead of an error.
- **Bounded waits.** Outbound calls carry explicit timeouts: agent readiness three
  seconds, list probes 1.5 seconds within a two-second budget, agent turns 120 seconds,
  serving deployment 90 seconds, predictions 30 seconds.
- **Best-effort observability.** Trace and session reporting never fails the
  operation it describes.

## Persistence and the Kafka outbox

PostgreSQL is the system of record ([decision 0005](../decisions/0005-postgresql-kafka-outbox.md)).
Resources are JSON documents in `platform_resources`, keyed by tenant, kind and ID.
`audit_events` and `outbox_events` are append-only. The migrations in
`platform/go/internal/store/migrations/` are embedded in the binary and all run at
every start under a PostgreSQL advisory lock, so they must stay idempotent.

A mutation calls `writeTx`, which in one transaction:

1. upserts the resource;
2. inserts the audit event;
3. inserts an outbox row for `mlaiops.audit.operations`;
4. for lifecycle actions, inserts a command row for the matching topic
   (`mlaiops.pipeline.commands`, `mlaiops.model.commands`, `mlaiops.agent.commands`,
   `mlaiops.tool.commands`, `mlaiops.connection.commands`,
   `mlaiops.workspace.commands`).

Either everything commits or nothing does, so there is no published event without a
stored change and no change without its audit record.

The **outbox worker** runs inside the gateway when `KAFKA_REST_URL` is set. Every
second it reads up to 100 unpublished rows in sequence order, publishes each through
the Kafka REST proxy, and marks it published. A row that fails increments `attempts`,
stores `last_error`, stays pending for the next pass, and does not block later rows.
Delivery is therefore at least once and not strictly ordered across failures.

The **integration worker** consumes the command topics on Kubernetes through an
explicit Kafka REST consumer with auto-commit off. It dispatches a polled batch in
order, retries a failed record up to five times with exponential backoff from 250 ms
capped at two seconds, and commits the highest processed offset plus one per
partition only after the whole batch succeeds. Commit retries do not redispatch. If
dispatch or commit still fails, the worker exits before polling again and restarts
from the last committed offset. Dispatch is an ID-keyed create-or-update of the
matching custom resource, so redelivery is harmless.

Without `DATABASE_URL` the gateway uses a local JSON file (`MLAIOPS_DATA_PATH`, default
`data/platform.json`). That mode has no outbox and no row-level security and exists
only for lightweight development and tests.

Leases built on the same store keep singletons safe across gateway replicas: the
pipeline scheduler and the editorial publisher each hold a row-locked lease document,
and each schedule slot is claimed with a create-only document before its run starts.
