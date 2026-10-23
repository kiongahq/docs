---
description: Symptoms, causes and fixes for common problems with the local stack, the single-server deployment and Kubernetes deployments of Kionga.
---

# Troubleshooting

Find the symptom you see, then follow the fix. Entries are grouped by
deployment: [local stack](#local-stack), [single server](#single-server) and
[Kubernetes](#kubernetes).

## First checks

For the local stack, start with the state of every service, the logs of the
one that fails and the end-to-end smoke test:

```bash
make -C deploy local-status
docker compose -f deploy/compose.yaml logs --tail 100 <service>
make -C deploy smoke
```

For a single server, check the containers and gateway logs:

```bash
docker compose -p kionga-public ps
docker compose -p kionga-public logs --tail 100 gateway
```

For Kubernetes, check pods and events in the release namespace:

```bash
kubectl --context CONTEXT -n kionga-system get pods
kubectl --context CONTEXT -n kionga-system get events --sort-by=.lastTimestamp
```

## Local stack

### Image download ends with `EOF`

**Cause.** A registry or CDN ended an image transfer early. This is a network
problem, not a Kionga configuration error. `make -C deploy local-up` already
limits downloads to two at a time and retries four times.

**Fix.** Run `make -C deploy local-up` again; Docker keeps completed layers. On
a slow or unstable connection, lower the concurrency or raise the retries:

```bash
COMPOSE_PARALLEL_LIMIT=1 KIONGA_START_RETRIES=6 make -C deploy local-up
```

If a failure persists, the command prints the service state and recent
startup logs.

### Startup says a port is in use

**Symptom.** `make -C deploy local-up` prints
`<service> port <port> is in use. Set <VARIABLE> to a free port`, or says that
the port and its fallbacks are occupied.

**Cause.** A busy default port moves automatically to default + 10000 (5432
becomes 15432). The command stops instead when you set the port yourself, or
when all five fallback ports are taken. A native PostgreSQL or Redis is the
usual cause.

**Fix.** Find the process that owns the port, then stop it or choose another
port:

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
echo "GATEWAY_PORT=18080" >> deploy/.env
make -C deploy local-up
```

Tools on your machine that connect to `localhost:5432` reach the native server,
not Kionga's PostgreSQL; use the port `local-up` printed. See
[Change ports](local.md#changing-ports).

### Other machines cannot reach the stack

**Symptom.** "Connection refused" from another machine, while the stack works
locally.

**Cause.** Every published port binds to `127.0.0.1` by default.

**Fix.** Confirm the binding, then, on a trusted network only, widen it:

```bash
docker compose -f deploy/compose.yaml port gateway 8080   # 127.0.0.1:8080
echo "KIONGA_BIND_ADDRESS=0.0.0.0" >> deploy/.env
make -C deploy local-up
```

This also exposes the data services with their development credentials. For
single sign-on from another machine, also set `KIONGA_GATEWAY_URL` and
`DEX_ISSUER`; see [Network exposure](local.md#network-exposure). Jupyter
always stays on `127.0.0.1`; open it through the console.

### Services start again after Docker restarts

**Cause.** Long-running services use the restart policy `unless-stopped`, so a
Docker restart or a reboot brings them back.

**Fix.** Stop the stack with `make -C deploy local-down` when you want it to
stay down.

### A connection on the Platform page shows `unhealthy`

**Cause.** The gateway checks connections from inside its container, so
`localhost` there is the gateway itself.

**Fix.** Use in-stack host names, such as `http://mlflow:5000/health`. To see
what the check sees, probe from a throwaway container on the stack's network
(the gateway image has no shell):

```bash
docker run --rm --network mlaiops_default curlimages/curl:8.10.1 -fsS http://mlflow:5000/health
```

See [Service endpoints](../reference/service-endpoints.md) for the right
addresses.

### An address works in the console but not from your machine (or the reverse)

**Cause.** Inside the stack, services use service names
(`http://objectstore:9000`). From your machine, you use `localhost` and the
published port (`http://localhost:9000`).

**Fix.** Use the address for where the client runs; see
[Service endpoints](../reference/service-endpoints.md).

### MLflow returns 403 "Invalid Host header"

**Cause.** MLflow accepts only the host names in `MLFLOW_SERVER_ALLOWED_HOSTS`
(in `deploy/compose.yaml`): `mlflow` and `mlflow:5000` inside the stack, and
`localhost` or `127.0.0.1` on any port from this machine. Opening it by
another name or IP address, for example after you set `KIONGA_BIND_ADDRESS`,
is rejected.

**Fix.** Add the name to the list and recreate MLflow:

```bash
docker compose -f deploy/compose.yaml up -d mlflow
```

### A model fails to deploy or the endpoint does not serve

**Cause.** Usually training-serving skew: the model was trained with different
library versions than the serving image. The trainer, the serving image and
the workbench must pin the same versions (`mlflow==3.16.1`,
`scikit-learn==1.7.0`).

**Fix.** Check the logs:

```bash
docker compose -f deploy/compose.yaml logs serving-manager
docker compose -f deploy/compose.yaml logs mlflow
```

If you change a pin, change it in `pipeline-runner/requirements.txt`,
`deploy/mlflow/Dockerfile` (`ARG MLFLOW_VERSION`) and
`workspace/jupyter/Dockerfile`, then run `make -C deploy local-up`.

### The serving manager reports "permission denied" on the Docker socket

**Cause.** The serving manager starts model containers through the Docker
socket. It runs as `user: "0:0"` with `/var/run/docker.sock` mounted.

**Fix.** If you changed `deploy/compose.yaml`, restore both settings. On Docker
Desktop, make sure the socket path exists on the host.

### Prefect returns 404 when a flow run is created

**Cause.** `PREFECT_API_URL` was changed to an address without the `/api`
suffix.

**Fix.** Keep the suffix, for example `http://prefect-server:4200/api`. The
gateway handles the prefix for you.

### Agent replies start with `[mock]`

**Cause.** The default LLM backend is `mock`, so the stack runs without API
keys.

**Fix.** Set `MLAIOPS_LLM_BACKEND`, `MLAIOPS_LLM_MODEL` and the provider key in
`deploy/.env`, then recreate the agent runtime:

```bash
docker compose -f deploy/compose.yaml up -d agent-runtime
```

See [Agents](../guides/agents.md#using-a-real-llm).

### Real-time statistics stay empty

**Cause.** The processor is still starting, or events went to the wrong topic.

**Fix.**

- Give the processor about 10 seconds after a restart.
- Check that it is consuming:
  `docker compose -f deploy/compose.yaml logs realtime-processor` shows
  `realtime processor consuming [...]`.
- Produce events onto the input topic, not the output topic:
  `python -m realtime.produce --demo fraud --count 5`.

### The first build runs out of disk space

**Symptom.** The build fails with
`You don't have enough free space in /var/cache/apt/archives`.

**Cause.** The Jupyter and ML images install large system and Python
dependencies. A cold build needs 25 to 35 GB of Docker storage.

**Fix.** Inspect the Docker disk usage, remove only stale build cache and start
again:

```bash
docker system df
docker builder prune --force
make -C deploy local-up
```

Do not run `docker volume prune` or `docker compose down -v` unless you intend
to delete databases, artifacts and workspace files.

### Services are killed for memory or the stack is slow

**Cause.** The stack runs 21 services and one-shot jobs, and the first build
compiles several images in parallel.

**Fix.** Give Docker at least 8 GB of memory (Docker Desktop: **Settings** >
**Resources**). If Docker Desktop crashes, start it again (`open -a Docker` on
macOS), wait for the daemon, then run `make -C deploy local-up`.

### Sign-in says "Too many failed attempts for this account"

**Cause.** The gateway throttles local sign-in per account. After 5 failed
attempts, each further attempt waits a doubling delay (1, 2, 4 seconds and so
on, up to 60 seconds).

**Fix.** Wait a minute and use the correct password. Failures are forgotten
after 15 minutes, after a successful sign-in, or when the gateway restarts.

### The stack is broken after an update

**Fix.** Run `make -C deploy local-up` again first; it rebuilds changed images
and resumes the stack. If that does not help and you can lose all local data,
reset the stack:

```bash
docker compose -f deploy/compose.yaml down -v   # deletes all local data
make -C deploy local-up
make -C deploy smoke
```

## Single server

### `Deployment failed: ... must be pinned to a verified SHA256 image digest`

**Cause.** `gateway_image` or `caddy_image` in `deployment.json` uses a tag
instead of a digest.

**Fix.** Use `repository@sha256:<64 hex characters>` for both.

### `Deployment failed: config public origin must match the deployment domain`

**Cause.** `MLAIOPS_ALLOWED_ORIGIN` in the application configuration is not
exactly `https://` followed by `domain`.

**Fix.** Make them match, with no trailing slash or port.

### `Deployment failed: missing or empty secret file`, `must not be world-accessible` or `deploy user cannot read secret file`

**Cause.** One of the four secret files in `secrets_directory` is missing,
empty, readable by everyone, or unreadable by the user running the installer.

**Fix.** Have your secret agent write the file, then set ownership and modes
as in [Deliver the secret files](public-vm.md#steps). Never print secret
contents while you diagnose this.

### `Could not pull the pinned images`

**Cause.** The `ghcr.io/kiongahq` images are private, the digest is wrong, or
the server cannot reach the registry.

**Fix.** As the user running the installer, sign in with a token that has
`read:packages`, then check the digests and outbound HTTPS:

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u <github-user> --password-stdin
```

### `Readiness failed; check DNS, TLS, secrets, database and container logs`

**Cause.** The installer started the containers, but
`https://<domain>/api/v1/ready` never answered `200`. Common causes: DNS does
not point at the server, ports 80 and 443 are blocked so Caddy cannot get a
certificate, the gateway exited at startup, or PostgreSQL is unreachable.

**Fix.** Check the gateway and Caddy logs:

```bash
docker compose -p kionga-public logs --tail 100 gateway
docker compose -p kionga-public logs --tail 100 caddy
```

Then look up the gateway message below. The installer does not roll back data.

### The gateway exits at startup with a configuration error

| Message | Fix |
| --- | --- |
| `production requires <NAME>` | Set the missing value in the configuration file or as a secret file |
| `production requires an HTTPS URL for <NAME>` | Use an `https://` URL without credentials |
| `OIDC_REDIRECT_URL must match the public origin and /auth/callback` | Set it to `https://<domain>/auth/callback` |
| `production DATABASE_URL must use PostgreSQL with sslmode=verify-full` | Add `sslmode=verify-full` to the URI and make sure the server certificate verifies |
| `production <NAME> must be a strong non-development credential` | Use at least 24 random characters without `local` or `change-me` |
| `production MLAIOPS_LOCAL_PASSWORD (break-glass sign-in) must be at least 16 characters and not a development default` | Use a longer password without `local`, `change-me` or `password`, or turn off `KIONGA_LOCAL_LOGIN` |
| `KIONGA_CREDENTIAL_KEY must encode 32 bytes` | Generate it with `openssl rand -base64 32` |
| `config key <NAME> is invalid or must be supplied separately as a secret` | Move the value out of the JSON file into a secret file |
| `KIONGA_CONFIG_FILE must be a JSON object of string values` | Quote every value, including `true`, `false` and numbers |
| `set only one of <NAME> and <NAME>_FILE` | Remove the environment variable or the file reference |
| `<NAME>_FILE is empty` | Write the value into the file |

The same messages apply to the gateway on Kubernetes.

## Kubernetes

### Helm rendering fails with a values error

**Cause.** The chart refuses unsafe values. Common messages:

| Message | Fix |
| --- | --- |
| `images.<name> must be an immutable repository@sha256:digest` | Pin every image, including `jupyter` and `ide`, by digest |
| `storageClass must be explicitly configured` | Set `storageClass` |
| `production mode is required` | Keep `config.KIONGA_ENVIRONMENT: production` |
| `components.<name>.replicas must be at least 2` | Use two or more replicas |
| `workspaceIngress.baseDomain must match config.KIONGA_WORKSPACE_BASE_DOMAIN` | Set both to the same base domain |
| `workspaceIngress must be enabled when KIONGA_WORKSPACE_BASE_DOMAIN is configured` | Enable `workspaceIngress`, or clear the base domain |
| `isolated workspace ingress requires the trusted same-origin proxy disabled` | Set `config.KIONGA_TRUSTED_WORKSPACE_PROXY: "false"` |
| `workspaceNamespace must differ from the control-plane namespace` | Use a separate workload namespace |

### The deploy script stops at a `NotFound` error for a custom resource definition

**Cause.** `deploy/scripts/deploy-kubernetes.sh` checks prerequisites before it
installs: the namespace, the Kionga CRDs and, when your values use them, the
External Secrets and Prometheus Operator CRDs.

**Fix.** Create the namespace and apply `deploy/config/crd/` with a
cluster-administrator identity, and install External Secrets Operator or the
Prometheus Operator if your values need them. Then run the script again.

### Pods stay in `ImagePullBackOff` or `ErrImagePull`

**Cause.** The `ghcr.io/kiongahq` images are private, and the pull Secret is
missing from the namespace or from `imagePullSecrets`.

**Fix.** Create the pull Secret in both the release namespace and the
workload namespace, and set `imagePullSecrets: [{name: ghcr-pull}]` in your
values; see [Deploy on Kubernetes](managed-kubernetes.md#steps). Platform pods
and the workspace and agent pods the operator creates use the same Secret
name.

### Gateway pods are not ready

**Cause.** The gateway reports ready only when it can reach PostgreSQL. The
network policy denies external traffic that `networkPolicy.externalEgress`
does not allow, and a missing Secret or an invalid value stops the gateway at
startup.

**Fix.** Read the gateway logs for a [configuration error](#the-gateway-exits-at-startup-with-a-configuration-error),
check that the ExternalSecrets are synced, and add the database address and
port to `networkPolicy.externalEgress`:

```bash
kubectl --context CONTEXT -n kionga-system logs deployment/kionga-gateway --tail 100
kubectl --context CONTEXT -n kionga-system get externalsecrets
```

### A workspace is `Failed` with reason `StorageNotAllowed`

**Cause.** The storage class of the workspace is not on
`WORKSPACE_ALLOWED_STORAGE_CLASSES`, or a volume uses a source tenants may not
mount.

**Fix.** Add the chart's `storageClass` to the allowlist, or remove the
allowlist; see [Tenant storage on Kubernetes](external-storage.md#tenant-storage-on-kubernetes).
