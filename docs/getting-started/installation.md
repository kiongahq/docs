# Installation

Kionga runs as one Docker Compose stack built from its component repositories
(see [Repositories](https://kiongahq.github.io/docs/engineering/components/)). You clone them side by side into
one workspace folder; every path and command in these docs is relative to that
folder.

## Prerequisites

| Requirement | Why | Notes |
| --- | --- | --- |
| **Docker Engine + Compose v2** | Runs the whole stack | Docker Desktop on macOS/Windows, Docker Engine on Linux |
| **~8 GB RAM free for Docker** | The full multi-service stack | Raise Docker Desktop's memory if services get OOM-killed; 12 GB is more comfortable |
| **25–35 GB free Docker storage** | First build downloads and compiles several large images | Cached rebuilds need less; check with `docker system df` |
| **Make** | Convenience targets | Optional: you can call `docker compose` and the scripts directly |
| **Go 1.26** (toolchain 1.26.10, fetched automatically by the `go` command) | Only for building Go binaries outside Docker or running Go tests | Not needed just to run the stack |
| **Python 3.11+** | Only for the SDK, tests, or docs outside Docker | Not needed just to run the stack |
| **Node.js** | Only for `make -C platform verify` and `make -C platform test-ui` (console checks) | Not needed to run the stack |

## Fastest path: the full stack

```bash
mkdir ~/kionga && cd ~/kionga
git clone https://github.com/kiongahq/deploy.git
KIONGA_GIT_BASE=https://github.com/kiongahq/ make -C deploy workspace   # clones the other repositories
make -C deploy local-up
```

`make -C deploy workspace` clones every component beside `deploy/` (over SSH by
default; `KIONGA_GIT_BASE` above switches to HTTPS). `make -C deploy local-up`:

1. Verifies that Docker and Compose v2 are available, the daemon is running, and
   every component checkout is present.
2. Downloads missing upstream images with conservative concurrency and retries
   transient registry/CDN failures such as `EOF`.
3. Reuses cached images or builds missing images, then starts every service in
   `deploy/compose.yaml`.
4. Waits for the control-plane health endpoint.
5. Creates the Kafka topics (`deploy/scripts/local-topics.sh`).

The shorter `make -C deploy local` alias does the same thing. The bootstrap is idempotent: if
a download fails even after the bounded retries, run the command again and Docker
resumes from layers already cached. Tune unusual environments with
`COMPOSE_PARALLEL_LIMIT`, `KIONGA_START_RETRIES`, and
`KIONGA_START_TIMEOUT_SECONDS` without editing the Compose file.

Routine `make -C deploy local-up` runs reuse cached images and rebuild only images
whose sources changed, including sources in another repository the image installs
(an SDK change rebuilds `agent-runtime` and `jupyter`). `make -C deploy local-rebuild`
rebuilds everything. `make -C deploy workspace-pull` fast-forwards clean checkouts.

The first run builds several images (Go services, MLflow, agent runtime, pipeline
runner, and Jupyter workbench). Allow roughly 10–25 minutes depending on bandwidth,
CPU architecture, and cache state. Subsequent runs are much faster.

When it finishes, open the landing page:

<http://localhost:8080>

The operational console is at <http://localhost:8080/console.html>.
Sign in with the local account `admin` / `mlaiops-local`, or with one of the
single sign-on test accounts described in
[Single sign-on](../operations/single-sign-on.md#try-it-locally).

Every published port binds to `127.0.0.1`, so the stack is reachable only from
this machine. To open it to other machines on a trusted network, set
`KIONGA_BIND_ADDRESS` (see [Local operations](../operations/local.md#network-exposure)).

If a default port is already used (8080, or 5432 by a native PostgreSQL),
`make -C deploy local-up` moves that service to a free port 10000 higher (18080,
15432) and prints it; see [Changing ports](../operations/local.md#changing-ports). To choose a port yourself without changing the container network:

```bash
GATEWAY_PORT=18080 make -C deploy local-up
export GATEWAY=http://localhost:18080
```

Bucket creation uses the `boto3` already included in the local MLflow image;
it does not pull a separate S3 client image. A registry error that says a
repository or tag does not exist fails immediately rather than consuming all
retry attempts.

### Verify it works

```bash
./deploy/scripts/demo-smoke.sh
```

This exercises the configured platform end to end: it signs in with the local
account (or uses `MLAIOPS_TOKEN` when set), creates a project, runs a real
pipeline, deploys a model and gets a live prediction, deploys and invokes an
agent, reads features from Redis, browses storage, and scores fraud events.
`make -C deploy smoke` runs the same script. Use
`GATEWAY=http://localhost:18080 ./deploy/scripts/demo-smoke.sh` when the port was
overridden. The pass/skip count is dynamic; the command must finish with zero
failures. OpenFaaS is skipped until an external gateway is configured.

### Service URLs

| Service | URL | Credentials (local defaults) |
| --- | --- | --- |
| Landing page | <http://localhost:8080> | none |
| Console + API | <http://localhost:8080/console.html> | `admin` / `mlaiops-local`, or single sign-on through Dex |
| Jupyter workbench | <http://localhost:8080/workspace.html?tool=workbench> | Kionga session |
| Browser IDE | <http://localhost:8080/workspace.html?tool=ide> | Kionga session; start with `make -C deploy ide-up` |
| Dex (single sign-on) | <http://localhost:5556/dex> | Test directory password `kionga-sso-dev` |
| MLflow | <http://localhost:15000> | none |
| Prefect | <http://localhost:4200> | none |
| Langfuse | <http://localhost:3000> | `admin@local.dev` / `mlaiops-local-admin` |
| RustFS console | <http://localhost:9001> | `mlaiops` / `mlaiops-local-secret` |

See [Configuration reference](../reference/configuration.md) for every port and setting, and
[Connecting all services](../reference/service-endpoints.md) for the full connection map.

## Stopping and restarting

```bash
make -C deploy local-down     # stop the stack (volumes persist)
make -C deploy local-up       # bring it back
make -C deploy local-status   # show every service, including completed one-shot jobs
make -C deploy local-logs     # show the latest logs from the stack
make -C deploy local-rebuild  # rebuild changed local source images, then start
```

Durable state lives in named volumes (`postgres-data`, `objectstore-data`, `redis-data`,
`prefect-data`, `jupyter-data`), so your projects, models, and notebooks survive
restarts.

Long-running services use `restart: unless-stopped`: after Docker Desktop or the
machine restarts, the whole stack comes back as it was. `make -C deploy local-down`
removes the containers, so a stopped stack stays stopped.

## Alternative: build and run the Go control plane only

For control-plane development without the full stack:

```bash
make -C platform run            # runs the gateway on :8080 (file-backed store)
```

In this mode there is no execution engine, serving, or agent runtime. The gateway
stores state in a local JSON file (`MLAIOPS_DATA_PATH`, default
`data/platform.json` relative to `platform/go`), single sign-on is off, and the
local account `admin` / `mlaiops-local` is the only sign-in. Downstream
integrations show as not configured. Use it for API and console work. Install
the SDK separately when you need it: `pip install -e "./sdk-python[dev]"`.

## Building the binaries

```bash
make -C platform build
```

Produces static binaries in `platform/bin/`:

```text
mlaiops-gateway  mlaiops-operator  mlaiops-integration-worker
mlaiops-feature-gateway  mlaiops-storage-proxy  mlaiops-metrics-collector
mlaiops-log-exporter  mlaiops-cli
```

The serving manager and the trace proxy live in their own repositories and build
with `make -C serving build` and `make -C trace-proxy build`.

The platform's Go services build from `platform/go/Dockerfile` with a `SERVICE`
build arg; every other image builds from its own repository's `Dockerfile` (see
[Repositories](https://kiongahq.github.io/docs/engineering/components/)):

```bash
docker build --build-arg SERVICE=gateway -t kionga/gateway platform/go
docker build -t kionga/serving-manager serving
```

## Running the test suites

```bash
make -C platform verify           # gofmt, go vet, go test -race, build, console JS syntax, banned-tech scan
make -C platform test-integration # PostgreSQL store tests in a throwaway pgvector container
make -C deploy test               # Compose wiring, Helm chart, and VM installer gate tests
make -C deploy test-e2e-kind      # Kind-based end to end (optional scale path)
make -C deploy test-load          # k6 load test against the gateway
```

Each Python repository (`sdk-python`, `agent-runtime`, `pipeline-runner`,
`workspace`, `contracts`) runs `python -m pytest -q && ruff check .` after
installing its development requirements.

## Public / production install

To host a gateway-only pilot on a public VM behind TLS with an external OIDC
provider, see **[Public VM](../operations/public-vm.md)**. After preparing
`/etc/kionga/deployment.json`, non-secret config, and mounted secret files:

```bash
python3 deploy/vm/up.py /etc/kionga/deployment.json --validate-only
make -C deploy public-up DEPLOYMENT=/etc/kionga/deployment.json
```

## Documentation site (this site)

```bash
make -C docs docs-install       # install the pinned MkDocs toolchain
make -C docs docs-serve         # live preview at http://localhost:8000
make -C docs docs-build         # strict static build into docs/site/
make -C docs docs-check         # check commands, paths, and names against the code
```
