---
description: What to configure, monitor, back up and test before you admit users to a single-server or Kubernetes deployment of Kionga, ending with the acceptance checklist.
---

# Production readiness

Use this page before you admit users to a [single-server](public-vm.md) or
[Kubernetes](managed-kubernetes.md) deployment. A successful install, a passing
health check or a green verifier run does not prove that an installation is
secure, recoverable or highly available. Record your installation's owners,
cloud, cluster, identity mappings, release digests, dependency versions and
acceptance results.

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
`DATABASE_URL`, `OIDC_CLIENT_SECRET`, `MLAIOPS_INTERNAL_TOKEN`,
`KIONGA_CREDENTIAL_KEY`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `REDIS_URL`, `KAFKA_REST_TOKEN`, `KFP_TOKEN`,
`MLFLOW_TOKEN`, `OPENFAAS_PASSWORD`, `LANGFUSE_SECRET_KEY`, `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `LLM_UPSTREAM_API_KEY`, `KIONGA_JUPYTER_TOKEN`,
`KIONGA_IDE_PASSWORD` and `TRACE_SINK_TOKEN`. The gateway also reads
`MLAIOPS_LOCAL_PASSWORD`. This is not a general loader: Python services and
third-party images read their own configuration.

Services read secret files once, at startup. After you rotate a secret,
restart or roll out every service that uses it.

### What the gateway requires in production

With `KIONGA_ENVIRONMENT=production` (set by both hosted deployments), the
gateway refuses to start unless:

- `DATABASE_URL`, `OIDC_ISSUER`, `OIDC_JWKS_URL`, `OIDC_AUDIENCE`,
  `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_AUTH_URL`, `OIDC_TOKEN_URL`,
  `OIDC_REDIRECT_URL`, `MLAIOPS_INTERNAL_TOKEN`, `KIONGA_CREDENTIAL_KEY` and
  `MLAIOPS_ALLOWED_ORIGIN` are all set.
- The OIDC endpoints and `MLAIOPS_ALLOWED_ORIGIN` are HTTPS URLs without
  embedded credentials.
- `OIDC_REDIRECT_URL` is on the same host as `MLAIOPS_ALLOWED_ORIGIN`, with the
  path `/auth/callback`.
- `DATABASE_URL` is a PostgreSQL URI with `sslmode=verify-full`.
- `OIDC_CLIENT_SECRET` and `MLAIOPS_INTERNAL_TOKEN` have at least 24 characters
  and contain neither `local` nor `change-me`.
- `KIONGA_CREDENTIAL_KEY` is the base64 encoding of exactly 32 bytes.
- When `KIONGA_LOCAL_LOGIN=true` (break-glass sign-in next to single sign-on),
  `MLAIOPS_LOCAL_PASSWORD` has at least 16 characters and contains none of
  `local`, `change-me` or `password`. It can come from
  `MLAIOPS_LOCAL_PASSWORD_FILE`.
- When `KIONGA_WORKSPACE_BASE_DOMAIN` is set, it is a DNS name distinct from
  the console host but on the same registrable domain, Kubernetes workspace
  discovery is configured, and `KIONGA_TRUSTED_WORKSPACE_PROXY` is not `true`.

## Security boundaries

- **Secrets in memory.** After loading, secret values live in process memory
  and environment. Mounted files do not protect against a compromised
  process. Never put secrets in ConfigMaps, Helm values, deployment JSON,
  traces or CI logs.
- **Internal token.** `MLAIOPS_INTERNAL_TOKEN` is one shared credential for
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
  generated code need a separately reviewed sandbox and egress policy.

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

On Kubernetes, `deploy/scripts/verify-production.py` automates the read-only
control-plane checks, and `--test-workspace-handoff` adds a workspace session
check; see [Verify](managed-kubernetes.md#verify). Record the result, then run
the stateful, disruptive and recovery cases in staging.
