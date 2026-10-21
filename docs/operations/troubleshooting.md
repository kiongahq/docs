# Troubleshooting

Common issues and how to resolve them. Most problems are one of: a service still
starting, an in-stack-vs-localhost hostname mixup, or Docker resource limits.

## Image pull ends with `EOF`

An `EOF` from a registry CDN means the remote image transfer ended early; it is not
a Kionga configuration error. The bundled object store is RustFS from Docker Hub. `make -C deploy local-up`
automatically limits parallel downloads to two and retries missing images four times. Docker
keeps completed layers, so if all attempts are exhausted, run the same command again:

```bash
make -C deploy local-up
```

For a slow or unstable connection, reduce concurrency or increase the bounded retry
count:

```bash
COMPOSE_PARALLEL_LIMIT=2 KIONGA_START_RETRIES=6 make -C deploy local-up
```

The startup script prints service state and recent bootstrap logs when a non-network
failure persists.

## First checks

```bash
docker compose -f deploy/compose.yaml ps          # is everything Up / healthy?
docker compose -f deploy/compose.yaml logs -f <service>
./deploy/scripts/demo-smoke.sh                            # what actually fails, end to end
```

## A connection shows "unhealthy"

The gateway health-checks connections **from inside its container**, so the endpoint
must resolve there. Use in-stack hostnames (`http://mlflow:5000/health`), not
`localhost`. Reproduce exactly what the check sees:

The gateway image is distroless and intentionally contains no shell or `wget`.
Probe from a disposable container on the same Compose network instead:

```bash
docker run --rm --network mlaiops_default curlimages/curl:8.10.1 \
  -fsS http://mlflow:5000/health
```

See [Connecting all services](../connecting-services.md) for the correct endpoints.

## Works in the console, fails from my laptop (or vice versa)

You crossed the two DNS worlds. **Inside the stack** use service names
(`http://objectstore:9000`); **from your machine** use localhost ports
(`http://localhost:9000`). See the table in
[Connecting services](../connecting-services.md).

## Model deploy fails or the endpoint won't serve

Almost always **training-serving skew**: the model was trained under different
library versions than the serving image. The trainer, serving image, and workbench
must pin identical versions (`mlflow==3.1.1`, `scikit-learn==1.7.0`). Check:

```bash
docker compose -f deploy/compose.yaml logs serving-manager
docker compose -f deploy/compose.yaml logs mlflow
```

If you changed a pin, change it in `pipeline-runner/requirements.txt`,
`deploy/mlflow/Dockerfile`, and `workspace/jupyter/Dockerfile`.

## Serving-manager: "permission denied" on the Docker socket

The serving-manager needs Docker access and runs as `user: "0:0"` with
`/var/run/docker.sock` mounted. If you customized the compose, ensure both are
present. On Docker Desktop, make sure the socket path exists on the host.

## Docker API "client version too old"

The serving-manager negotiates the Docker API version by default. If your daemon
rejects it, pin one:

```bash
echo "DOCKER_API_VERSION=1.44" >> .env
docker compose -f deploy/compose.yaml up -d serving-manager
```

## Prefect returns 404 on flow-run creation

The gateway normalizes `PREFECT_API_URL` (which ends in `/api`) so client paths don't
double-prefix `/api`. If you overrode it, keep the `/api` suffix
(`http://prefect-server:4200/api`).

## Agent replies are prefixed `[mock]`

That is the default `mock` LLM backend, so the stack runs without keys. Set a real
provider in `deploy/.env` (`MLAIOPS_LLM_BACKEND`, `MLAIOPS_LLM_MODEL`, and the
provider key) and recreate the agent runtime
(`docker compose -f deploy/compose.yaml up -d agent-runtime`). See
[Agents](../guides/agents.md#using-a-real-llm).

## Real-time stats stay empty

- The processor may still be draining after a restart; give it about 10 seconds
  after producing events.
- Confirm it's consuming: `docker compose -f deploy/compose.yaml logs realtime-processor`
  should show `realtime processor consuming [...]`.
- Produce events onto the input topic, not the output topic:
  `python -m realtime.produce --demo fraud --count 5`.

## Sessions don't appear after chatting

Sessions are scoped per agent. If you reuse a session id across agents you won't see
cross-contamination (by design). Start a new chat (empty `session_id`) to create a
fresh session.

## First build says there is not enough space

Jupyter and ML images install substantial system/Python dependencies. If the build
fails with `You don't have enough free space in /var/cache/apt/archives`, inspect
Docker's storage and remove only stale build cache:

```bash
docker system df
docker builder prune --force
make -C deploy local-up
```

This keeps named volumes. Do **not** run `docker volume prune` or Compose `down -v`
unless you intend to delete databases, artifacts, and workspace files. Allocate
25–35 GB of Docker storage for a cold build.

## Services get OOM-killed / the stack is slow

The default stack runs 21 regular and one-shot services. Give Docker more memory
(Docker Desktop → Settings → Resources; aim for at least 8 GB). Large parallel image builds on first `local-up` can also
strain the daemon. If Docker Desktop crashes, relaunch it (`open -a Docker` on
macOS), wait for the daemon, then `make -C deploy local-up`.

## Port already in use

Another process holds a published port. Override it in `deploy/.env` (for example
`GATEWAY_PORT=8090`) and run `make -C deploy local-up`, or stop the conflicting
process.

Identify the owner before stopping anything:

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
GATEWAY_PORT=18080 make -C deploy local-up
GATEWAY=http://localhost:18080 ./deploy/scripts/demo-smoke.sh
```

## Can't reach the stack from another machine

Every port the local stack publishes binds to `127.0.0.1` by default, so other
machines get "connection refused" even when the stack is healthy. Check the
binding:

```bash
docker compose -f deploy/compose.yaml port gateway 8080   # 127.0.0.1:8080
```

On a trusted network, set `KIONGA_BIND_ADDRESS=0.0.0.0` in `deploy/.env` and run
`make -C deploy local-up`. That exposes the data services with their development
credentials too. For single sign-on from another machine also set
`KIONGA_GATEWAY_URL` and `DEX_ISSUER`; see
[Network exposure](local.md#network-exposure). Jupyter stays on loopback; open it
through the gateway.

## Local sign-in says "Too many failed attempts for this account"

The gateway throttles local sign-in per account. After 5 failed attempts each
further attempt waits a doubling delay (1 s, 2 s, 4 s, up to 60 s). Wait a minute
and try again with the correct password; failures are forgotten after 15 minutes
or on a successful sign-in. Restarting the gateway also clears them.

## `make -C platform verify` fails the banned-tech scan

The build forbids certain proprietary product names in the Go source
(`platform/go`). If you referenced one (even in a comment), reword it: serverless
is OpenFaaS, serving is mlflow-serve, pipelines are Prefect.

## Everything is broken after an update

Reset to a clean state (destructive: wipes volumes):

```bash
docker compose -f deploy/compose.yaml down -v
make -C deploy local-up
./deploy/scripts/demo-smoke.sh
```
