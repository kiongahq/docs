# Troubleshooting

Common issues and how to resolve them. Most problems are one of: a service still
starting, an in-stack-vs-localhost hostname mixup, or Docker resource limits.

## First checks

```bash
docker compose -f deploy/compose.yaml ps          # is everything Up / healthy?
docker compose -f deploy/compose.yaml logs -f <service>
./scripts/demo-smoke.sh                            # what actually fails, end to end
```

## A connection shows "unhealthy"

The gateway health-checks connections **from inside its container**, so the endpoint
must resolve there. Use in-stack hostnames (`http://mlflow:5000/health`), not
`localhost`. Reproduce exactly what the check sees:

```bash
docker compose -f deploy/compose.yaml exec gateway wget -qO- http://mlflow:5000/health
```

See [Connecting all services](../connecting-services.md) for the correct endpoints.

## Works in the console, fails from my laptop (or vice versa)

You crossed the two DNS worlds. **Inside the stack** use service names
(`http://minio:9000`); **from your machine** use localhost ports
(`http://localhost:9000`). See the table in
[Connecting services](../connecting-services.md).

## Model deploy fails or the endpoint won't serve

Almost always **training-serving skew** — the model was trained under different
library versions than the serving image. The trainer, serving image, and workbench
must pin identical versions (`mlflow==3.1.1`, `scikit-learn==1.7.0`). Check:

```bash
docker compose -f deploy/compose.yaml logs serving-manager
docker compose -f deploy/compose.yaml logs mlflow
```

If you changed a pin, change it in `python/pipelines/Dockerfile`,
`deploy/mlflow/Dockerfile`, and `deploy/jupyter/Dockerfile`.

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

That's the default `mock` LLM backend — the stack runs keyless. Set a real provider
in `.env` (`MLAIOPS_LLM_BACKEND`, `MLAIOPS_LLM_MODEL`, the key, `LLM_UPSTREAM_URL`)
and restart the agent runtime. See [Agents](../guides/agents.md#using-a-real-llm).

## Real-time stats stay empty

- The processor may still be draining after a restart — give it ~10s after producing
  events.
- Confirm it's consuming: `docker compose -f deploy/compose.yaml logs realtime-processor`
  should show `realtime processor consuming [...]`.
- Produce events onto the input topic, not the output topic:
  `python -m realtime.produce --demo fraud --count 5`.

## Sessions don't appear after chatting

Sessions are scoped per agent. If you reuse a session id across agents you won't see
cross-contamination (by design). Start a new chat (empty `session_id`) to create a
fresh session.

## Services get OOM-killed / the stack is slow

The full stack is ~17 services. Give Docker more memory (Docker Desktop → Settings →
Resources; aim for 6–8 GB). Large parallel image builds on first `local-up` can also
strain the daemon — if Docker Desktop crashes, relaunch it (`open -a Docker` on
macOS), wait for the daemon, then `make local-up`.

## Port already in use

Another process holds a published port. Override it in `.env` (e.g.
`GATEWAY_PORT=8090`) and `make local-up`, or stop the conflicting process.

## `make verify` fails the banned-tech scan

The build forbids certain proprietary product names in the Go source and `config/`.
If you referenced one (even in a comment), reword it — serverless is OpenFaaS,
serving is mlflow-serve, pipelines are Prefect.

## macOS: git stalls / "not a git repository"

The repo is under an iCloud-managed folder and files were evicted. Recover with
`brctl download <repo>/.git`; if the downloader is wedged, `killall bird` (and
`fileproviderd`) resets it. Better: move the repo out of `~/Documents`/`~/Desktop`
entirely.

## Everything is broken after an update

Reset to a clean state (destructive — wipes volumes):

```bash
docker compose -f deploy/compose.yaml down -v
make local-up
./scripts/demo-smoke.sh
```
