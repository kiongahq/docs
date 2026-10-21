# Local operations

Day-to-day commands for running, verifying, and inspecting the local stack.

## Lifecycle

```bash
make -C deploy local-up       # build + start everything, create Kafka topics
make -C deploy local-down     # stop (named volumes persist)
make -C deploy local-status   # inspect running, unhealthy, and completed services
make -C deploy local-logs     # print the most recent stack logs
make -C deploy local-rebuild  # rebuild Dockerized source/dependency changes, then start
make -C deploy ide-up         # optional browser IDE sharing Jupyter's workspace
make -C deploy ide-down       # stop the IDE without deleting the workspace
```

Restarting is idempotent: `make -C deploy local-up` reconciles to the desired state and only
rebuilds changed images. It also caps concurrent downloads, retries transient image
registry failures, waits for the gateway, and creates Kafka topics. `make -C deploy local` is
an equivalent shorter alias. Durable state survives in the `postgres-data`,
`objectstore-data`, `redis-data`, `prefect-data`, and `jupyter-data` volumes.

## Status & health

```bash
export GATEWAY="${GATEWAY:-http://localhost:8080}"
docker compose -f deploy/compose.yaml ps                    # per-service state
curl -s "$GATEWAY/api/v1/health"                            # gateway
curl -s "$GATEWAY/api/v1/components" | python -m json.tool # component grid
```

## Logs

```bash
docker compose -f deploy/compose.yaml logs -f gateway
docker compose -f deploy/compose.yaml logs -f realtime-processor
docker compose -f deploy/compose.yaml logs --tail 100 serving-manager
```

## Rebuilding one service

After editing code for a single service:

```bash
docker compose -f deploy/compose.yaml up -d --build gateway
```

The console (HTML/JS/CSS) is embedded in the gateway binary, so console changes need
a gateway rebuild.

## Re-running one-shot jobs

```bash
docker compose -f deploy/compose.yaml up feature-materializer   # re-materialize features
docker compose -f deploy/compose.yaml up objectstore-init       # ensure buckets
```

## Verifying the whole platform

```bash
GATEWAY="$GATEWAY" ./deploy/scripts/demo-smoke.sh # configured end-to-end checks (or make -C deploy smoke)
make -C platform verify                      # Go format, vet, race tests, build, console JS syntax, banned-tech scan
make -C platform test-integration            # PostgreSQL store tests in a throwaway container
make -C deploy test                          # Compose wiring, Helm chart, VM installer
```

The pass/skip count varies with optional services. The required invariant is zero
failures; OpenFaaS is skipped when it is not configured.

## Kubernetes fidelity stack

`make -C deploy k8s-tools` installs pinned `kind` and `helm` binaries under
`.tools.nosync/bin` in the deploy checkout. `make -C deploy kind-up` installs the Kionga CRDs/controllers and loads the locally built
images. It also installs metrics-server with the Kind-specific kubelet TLS flag,
so elastic `KiongaAgent` deployments have a working resource-metrics API for their
CPU HorizontalPodAutoscalers. Run `make -C deploy test-e2e-kind` after bootstrap to exercise the
agent and workspace reconcilers.

## Changing ports

Every published port has a `*_PORT` override. Put them in `deploy/.env` (or export
them), then `make -C deploy local-up`.

When a default port is already taken (a native PostgreSQL on 5432, Redis on 6379,
another app on 8080), `make -C deploy local-up` moves only that service to the first
free port of default + 10000 to + 10004 and prints the change, for example
`Port 5432 is in use; postgres uses 15432 instead (POSTGRES_PORT=15432)`. A port
you set yourself is never moved: the script stops and names the variable to change.
A running stack keeps the ports it already holds.

To pin a port, for example to move the console off 8080:

```bash
echo "GATEWAY_PORT=8090" >> deploy/.env
make -C deploy local-up
export GATEWAY=http://localhost:8090
```

## Network exposure

The local stack ships well-known development credentials (PostgreSQL, the object
store, Langfuse, the internal service token). Every port it publishes therefore
binds to `127.0.0.1` by default: only this machine can reach the console, the API,
and the data services.

`KIONGA_BIND_ADDRESS` sets the host address for those ports. To reach the stack
from other machines on a trusted network, bind to all interfaces (or to one
interface's address) and restart:

```bash
echo "KIONGA_BIND_ADDRESS=0.0.0.0" >> deploy/.env
make -C deploy local-up
```

This exposes PostgreSQL, Redis, Kafka, the object store, MLflow, Langfuse, and
the other published services with their development credentials, not only the
console. Use it only on a network you trust, and change the credentials first
if anyone else shares it. Some ports stay on `127.0.0.1` regardless: Jupyter
(`JUPYTER_PORT`), the log exporter, and the `log-export-es` / `log-export-os`
test clusters. The browser IDE publishes no port.

Single sign-on redirects the browser to the URLs in `KIONGA_GATEWAY_URL`
(default `http://localhost:<GATEWAY_PORT>`) and `DEX_ISSUER` (default
`http://localhost:5556/dex`). For sign-in from another machine, set both to an
address that machine can reach, for example
`KIONGA_GATEWAY_URL=http://192.168.1.20:8080` and
`DEX_ISSUER=http://192.168.1.20:5556/dex`, then rerun `make -C deploy local-up`.
The local `admin` account works without those changes.

Public hosting does not use this setting: in the public overlay
(`compose.public.yaml`) only Caddy publishes ports 80 and 443.

## Switching your local role

The local `admin` account takes its role from `MLAIOPS_LOCAL_ROLE` (default
`admin`). To preview the console as a viewer:

```bash
MLAIOPS_LOCAL_ROLE=viewer docker compose -f deploy/compose.yaml up -d gateway
# ... then restore:
docker compose -f deploy/compose.yaml up -d gateway
```

Recreating the gateway ends existing local sessions; sign in again to get the
new role. An access
profile provisioned for the `admin` subject under **Users & access** replaces
this role.

## Data & backups

Durable platform state is in PostgreSQL (control plane, MLflow, Langfuse,
checkpoints) and the RustFS object store (artifacts). Notebooks and projects live
in `jupyter-data`. To back up the first two locally, snapshot their volumes:

```bash
docker run --rm -v mlaiops_postgres-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/postgres-data.tgz -C /data .
docker run --rm -v mlaiops_objectstore-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/objectstore-data.tgz -C /data .
```

## Resetting

To wipe all state and start clean (destructive):

```bash
docker compose -f deploy/compose.yaml down -v   # -v removes the named volumes
make -C deploy local-up
```

Do not add `-v` during routine restarts. It permanently deletes platform databases,
artifacts, models, notebooks, and IDE workspace data.
