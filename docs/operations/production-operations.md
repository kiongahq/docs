---
description: What to configure, monitor, back up and test before you admit users to a single-server or Kubernetes deployment of Kionga, ending with the acceptance checklist.
---

# Production readiness

This guide shows you what to configure, monitor, back up and test before you
admit users to a [single-server](public-vm.md) or
[Kubernetes](managed-kubernetes.md) deployment, and ends with the acceptance
checklist. A successful install, a passing
health check or a green verifier run does not prove that an installation is
secure, recoverable or highly available. Record your installation's owners,
cloud, cluster, identity mappings, release digests, dependency versions and
acceptance results.

## Before you begin

- A completed install of a [single server](public-vm.md) or
  [Kubernetes](managed-kubernetes.md) deployment.
- An owner for each part of the installation, and a staging environment that
  matches production.
- An administrator, a provisioned user, an unprovisioned user and a suspended
  user in your identity provider, so you can run the acceptance checklist.
- On Kubernetes, `kubectl` and Python 3 on the machine you work from, and a
  checkout of the `deploy` repository.

## Configuration and secrets

Kionga's services take non-secret settings from a JSON file and secrets from
mounted files:

- `KIONGA_CONFIG_FILE` points at a JSON object whose values are all strings.
  The file may not contain secrets: a key that is a secret name, ends in
  `_FILE`, or contains `PASSWORD`, `SECRET`, `TOKEN` (other than
  `OIDC_TOKEN_URL`) or `API_KEY` stops the service at startup. An environment
  variable with the same name overrides the file.
- For each secret, `NAME_FILE` points at a file that holds the value. Setting
  both `NAME` and `NAME_FILE` stops the service, and so does an empty file.
  Files are limited to 64 KiB.

The gateway, operator, integration worker, feature gateway, storage proxy,
serving manager and trace proxy read secret files for these names:
`DATABASE_URL`, `OIDC_CLIENT_SECRET`, `KIONGA_INTERNAL_TOKEN`,
`KIONGA_CREDENTIAL_KEY`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `REDIS_URL`, `KAFKA_REST_TOKEN`, `KFP_TOKEN`,
`MLFLOW_TOKEN`, `OPENFAAS_PASSWORD`, `LANGFUSE_SECRET_KEY`, `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `LLM_UPSTREAM_API_KEY`, `KIONGA_JUPYTER_TOKEN`,
`KIONGA_IDE_PASSWORD` and `TRACE_SINK_TOKEN`. The gateway also reads
`KIONGA_LOCAL_PASSWORD`. This is not a general loader: Python services and
third-party images read their own configuration.

Services read secret files once, at startup. After you rotate a secret,
restart or roll out every service that uses it.

### What the gateway requires in production

With `KIONGA_ENVIRONMENT=production` (set by both hosted deployments), the
gateway refuses to start unless:

- `DATABASE_URL`, `OIDC_ISSUER`, `OIDC_JWKS_URL`, `OIDC_AUDIENCE`,
  `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_AUTH_URL`, `OIDC_TOKEN_URL`,
  `OIDC_REDIRECT_URL`, `KIONGA_INTERNAL_TOKEN`, `KIONGA_CREDENTIAL_KEY` and
  `KIONGA_ALLOWED_ORIGIN` are all set.
- The OIDC endpoints and `KIONGA_ALLOWED_ORIGIN` are HTTPS URLs without
  embedded credentials.
- `OIDC_REDIRECT_URL` is on the same host as `KIONGA_ALLOWED_ORIGIN`, with the
  path `/auth/callback`.
- `DATABASE_URL` is a PostgreSQL URI with `sslmode=verify-full`.
- `OIDC_CLIENT_SECRET` and `KIONGA_INTERNAL_TOKEN` have at least 24 characters
  and contain neither `local` nor `change-me`.
- `KIONGA_CREDENTIAL_KEY` is the base64 encoding of exactly 32 bytes.
- When `KIONGA_LOCAL_LOGIN=true` (break-glass sign-in next to single sign-on),
  `KIONGA_LOCAL_PASSWORD` has at least 16 characters and contains none of
  `local`, `change-me` or `password`. It can come from
  `KIONGA_LOCAL_PASSWORD_FILE`.
- When `KIONGA_WORKSPACE_BASE_DOMAIN` is set, it is a DNS name distinct from
  the console host but on the same registrable domain, Kubernetes workspace
  discovery is configured, and `KIONGA_TRUSTED_WORKSPACE_PROXY` is not `true`.

### What the agent runtime requires in production

With `KIONGA_ENVIRONMENT=production`, the agent runtime requires the gateway's
bearer token on `/invoke` and `/stream`, and refuses to start unless
`KIONGA_INTERNAL_TOKEN` is set to at least 16 characters. Give every agent
runtime the same `KIONGA_INTERNAL_TOKEN` as the gateway.

## Security boundaries

- **Secrets in memory.** After loading, secret values live in process memory
  and environment. Mounted files do not protect against a compromised
  process. Never put secrets in ConfigMaps, Helm values, deployment JSON,
  traces or CI logs.
- **Internal token.** `KIONGA_INTERNAL_TOKEN` is one shared credential for
  platform services, not a per-workload identity. Rotate it across every
  consumer at once.
- **Credential encryption key.** `KIONGA_CREDENTIAL_KEY` encrypts users' stored
  personal credentials. Kionga does not rotate it or wrap it with a KMS for
  you. Losing or replacing it means restoring from backup or having users
  reconnect their accounts.
- **Namespaces are not a sandbox.** The operator and the gateway's service
  account have sensitive permissions in their namespaces. Namespace RBAC and
  restricted pods do not isolate workloads from cluster administrators or
  contain hostile code. Add tenant-aware network policies, admission
  controls, image policies and resource limits. Agent frameworks that run
  generated code need a separately reviewed sandbox and egress policy. Agent teams
  have their own [sandboxes](sandboxes.md), which have no network.

### Notebook and IDE isolation

In production, the gateway does not proxy workspaces on the console's own
origin. On Kubernetes, each workspace gets its own subdomain and a host-only
session that never carries the console cookie; see
[How workspace access works](managed-kubernetes.md#how-workspace-access-works).
Test DNS, wildcard TLS, redirects, iframe cookies and WebSockets with your
ingress controller. The single-server deployment has no workspaces.

`KIONGA_TRUSTED_WORKSPACE_PROXY=true` turns the same-origin proxy back on. Use
it only in a deliberately trusted environment; it cannot be combined with
isolated workspace subdomains. If a user signs out at the identity provider
without signing out of Kionga, an existing workspace session lasts up to 30
minutes unless you revoke the user's grant first.

## Availability and monitoring

Monitor at least:

- Public gateway readiness, HTTP error rates and latency.
- Integration worker readiness (recent successful polling) and Kafka consumer
  lag.
- Outbox backlog and operator reconciliation failures.
- Pod restarts, scheduling failures, resource quotas and PVC capacity.
- Certificate expiry and secret synchronization.

Health probes of the service proxies do not check every upstream dependency.
The Helm chart can create ServiceMonitors and two availability alerts when the
Prometheus Operator is installed (`monitoring.enabled`); it does not provide a
full monitoring stack or alert routing. Confirm in staging that your alerts
are selected, routed and actually fire.

Test node drains, replica loss and dependency outages in staging. Disruption
budgets cover voluntary disruptions only. Keep spare scheduling capacity and
redundant databases, storage and engines. The single-server deployment has no
gateway failover. Use private connectivity and TLS to external services, and
verify each engine's own authentication and tenancy.

## Backups and recovery

- Define a recovery point objective and recovery time objective you can
  measure.
- Use PostgreSQL point-in-time recovery, object storage versioning and tested
  snapshots of workspace volumes. See the
  [PostgreSQL backup documentation](https://www.postgresql.org/docs/current/backup.html).
- Back up the credential encryption key and your configuration securely,
  alongside compatible data versions.
- Include MLflow, Langfuse, Prefect and other engine state in the plan. Kafka
  retention is not a database backup.
- Restore into a separate environment regularly. Check identity configuration,
  encrypted credentials, artifacts, workspace files and job reconciliation,
  measure the recovery time and keep the evidence.

Helm rollback does not restore database schemas, object data, external secret
versions or custom resource definitions.

## Release controls

- Build once and promote the same immutable image digests through staging.
- Scan images and dependencies and verify provenance and software bills of materials with your own
  tooling. Build attestations alone do not block anything at admission.
- Keep deployment permissions separate from application credentials. Deploy
  through reviewed GitOps or short-lived CI federation with protected
  environments.
- Test migrations against a copy of production data first, and prevent
  incompatible downgrades. Gateway replicas apply database migrations one at a
  time under a PostgreSQL lock, but compatibility across versions still needs
  a staged rollout check.

## Acceptance checklist

Treat every failure as a release blocker.

1. Confirm HTTPS, matching callback and origin, and sign-in and sign-out with
   the real identity provider. Anonymous console and API access fails while
   the public health endpoints still answer.
2. Test an administrator, a provisioned user, an unprovisioned user and a
   suspended user. Try cross-project reads and writes through the API directly,
   not only through the console.
3. Provision CPU, memory, storage and services; confirm limits, and confirm
   that requests beyond a user's grants are rejected. Create, stop and resume a
   workspace without losing files.
4. Run a job and a multi-step pipeline, consume events, register and download a
   model, access approved object storage and invoke an agent. Check real
   engine results.
5. Confirm that denied network paths stay denied and allowed destinations work,
   including workspace object access, model downloads, Kafka REST and the
   Kubernetes API.
6. Drain a node or stop a replica and interrupt a dependency. Confirm recovery,
   alerts, bounded retries and no fallback to broader privileges.
7. Rotate credentials with a coordinated restart. Restore a backup into staging
   and check both encrypted credentials and user artifacts.
8. Test workspace subdomain sign-in, ownership checks, revoked access and cookie
   isolation before you allow untrusted notebook or IDE users.

Steps 3 to 5 and step 8 need a workload plane, so they do not apply to the
single-server deployment unless you have integrated a separate one.

Record the result of each step, then run the stateful, disruptive and recovery
cases in staging. [Verify](#verify) lists the checks you can automate.

## Migrate a stored reference

Registered records name their credential as `env:NAME`, and each record type has its own
[scope](../reference/configuration.md#secret-references). This stops a registered endpoint from
receiving a gateway secret such as `DATABASE_URL`.

A saved record whose variable is outside its scope stops authenticating when you deploy this
change. Kionga does not change the record, and sends the credential nowhere.

| Record | What you see |
| --- | --- |
| Knowledge base | 503 `backend_unavailable` on add and search |
| Agent API connection | 503 `credential_unavailable` on invoke |
| Platform connection | The test fails with `not permitted`. An active Prefect connection falls back to no base address, and an active OpenFaaS connection reports not configured. |
| Feature store | Health is `configured` with `not permitted`, and `secret_present` is false |
| Storage connection | 503 `connection_unavailable`, and `secret_present` is false |

To find affected records before anyone hits them, search the gateway's startup logs for
`secret reference refused`. Each line gives the record's kind, ID and variable name, never its value.

Then fix each record:

1. **An ordinary variable**: add its name to the scope's allowlist
   and restart the gateway. The record keeps working unchanged.
2. **A gateway secret**, such as `env:DATABASE_URL`: you cannot allowlist it. The endpoint that record
   names has received that secret, so consider rotating it. Issue a dedicated credential if you can,
   set it as `KIONGA_<SCOPE>_SECRET_<NAME>`, and register the record again. You can update a storage
   connection with `PUT`. The other record types have no update route, so create a new record and
   move its users to it.

!!! warning "A reference is not bound to its endpoint"
    An administrator who can register an endpoint can still read any variable in that scope by
    pointing a new record at their own server. Give each secret only to people you would trust
    with its value.

## Verify

1. On Kubernetes, run the read-only verifier. It automates the control-plane
   checks in the checklist, and `--test-workspace-handoff` adds a workspace
   session check. See [Verify](managed-kubernetes.md#verify) in the Kubernetes
   guide for the full command:

    ```bash
    python3 deploy/scripts/verify-production.py --context CONTEXT --namespace kionga-system \
      --origin https://console.example.com --workspace-host https://<workspace-host> \
      --admin-token-file /secure/admin-id-token --user-token-file /secure/user-id-token \
      --forbidden-project PROJECT_ID --expect-monitoring
    ```

    The command prints one line for each group of checks, for example
    `Cluster: replicas, probes, digests, TLS ingress, HPA, isolation, and node spread pass`
    and `HTTP: TLS, identity, provisioning, project denial, and workspace origin checks pass`.
    A failed check prints `Acceptance failed: <reason>` and exits with status 1.

2. On either deployment, check readiness and anonymous denial from outside:

    ```bash
    curl -s https://<your-domain>/api/v1/ready                                  # {"status":"ready"}
    curl -s -o /dev/null -w '%{http_code}\n' https://<your-domain>/api/v1/me     # 401
    ```

3. Work through the [acceptance checklist](#acceptance-checklist) and keep the
   evidence. Treat every failure as a release blocker.

## Troubleshooting

Each service reads its configuration at startup and exits with one of these
messages. Read the log of the service that exits.

| Symptom | Cause | Fix |
| --- | --- | --- |
| `production requires <NAME>` | A value the gateway needs in production is empty | Set it. See [What the gateway requires in production](#what-the-gateway-requires-in-production) |
| `production requires an HTTPS URL for <NAME>` | An OIDC endpoint or `KIONGA_ALLOWED_ORIGIN` is not an `https://` URL, or embeds credentials | Use an `https://` URL without credentials |
| `OIDC_REDIRECT_URL must match the public origin and /auth/callback` | The redirect URL has another host than `KIONGA_ALLOWED_ORIGIN`, or another path | Set it to `https://<console-host>/auth/callback` |
| `production DATABASE_URL must use PostgreSQL with sslmode=verify-full` | The URI uses another scheme or `sslmode` | Add `sslmode=verify-full` and make sure the server certificate verifies |
| `production <NAME> must be a strong non-development credential` | `OIDC_CLIENT_SECRET` or `KIONGA_INTERNAL_TOKEN` is short, or contains `local` or `change-me` | Use at least 24 random characters |
| `production KIONGA_LOCAL_PASSWORD (break-glass sign-in) must be at least 16 characters and not a development default` | Local sign-in is on with a weak password | Use a longer password without `local`, `change-me` or `password`, or turn off `KIONGA_LOCAL_LOGIN` |
| `KIONGA_CREDENTIAL_KEY must encode 32 bytes` | The key is not the base64 encoding of 32 bytes | Generate it with `openssl rand -base64 32` |
| `isolated workspaces require a distinct DNS base domain, Kubernetes discovery and the trusted proxy disabled` | The workspace base domain is invalid, equals the console host, or the trusted proxy is on | Set a DNS name distinct from the console host, and keep `KIONGA_TRUSTED_WORKSPACE_PROXY` off |
| `workspace and console hosts must share a registrable site for host-only workspace cookies` | The workspace domain is on another registrable domain than the console | Use a workspace domain under the console's registrable domain |
| `config key <NAME> is invalid or must be supplied separately as a secret` | A secret-like key is in the JSON configuration file | Move the value to a secret file |
| `KIONGA_CONFIG_FILE must be a JSON object of string values` | A value in the file is not a string | Quote every value, including `true`, `false` and numbers |
| `set only one of <NAME> and <NAME>_FILE` or `<NAME>_FILE is empty` | Both forms are set, or the file has no content | Keep one form, and write the value into the file |
| `file exceeds 64 KiB` | A configuration or secret file is larger than the limit | Shrink the file |
| `KIONGA_RUNTIME_AUTH=required needs KIONGA_INTERNAL_TOKEN of at least 16 characters` | An agent runtime runs in production without the gateway's token | Give it the same `KIONGA_INTERNAL_TOKEN` as the gateway |
| Startup log line `secret reference refused, record will not authenticate until migrated` | A saved record names a variable outside its scope | See [Migrate a stored reference](#migrate-a-stored-reference) |

## Related pages

- [Single server](public-vm.md)
- [Deploy on Kubernetes](managed-kubernetes.md)
- [Updates and rollback](updates.md)
- [Single sign-on](single-sign-on.md)
- [Sandboxes and gVisor](sandboxes.md)
- [Troubleshooting](troubleshooting.md)
- [Configuration reference](../reference/configuration.md#secret-references)
- [PostgreSQL backup documentation](https://www.postgresql.org/docs/current/backup.html)
