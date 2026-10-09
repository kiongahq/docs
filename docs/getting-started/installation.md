# Installation

Kionga runs as one Docker Compose stack built from its component repositories
(see [Repositories](../overview/repositories.md)). You clone them side by side into
one workspace folder; every path and command in these docs is relative to that
folder.

## Prerequisites

| Requirement | Why | Notes |
| --- | --- | --- |
| **Docker Engine + Compose v2** | Runs the whole stack | Docker Desktop on macOS/Windows, Docker Engine on Linux |
| **~8 GB RAM free for Docker** | The full multi-service stack | Raise Docker Desktop's memory if services get OOM-killed; 12 GB is more comfortable |
| **25–35 GB free Docker storage** | First build downloads and compiles several large images | Cached rebuilds need less; check with `docker system df` |
| **Make** | Convenience targets | Optional — you can call `docker compose` directly |
| **Go 1.26+** | Only for building Go binaries outside Docker or running Go tests | Not needed just to run the stack |
| **Python 3.11+** | Only for the SDK, tests, or docs outside Docker | Not needed just to run the stack |
| **Node.js** | Only for `make -C platform verify` (JS syntax check) | Not needed to run the stack |

!!! tip "macOS + iCloud"
    Don't keep the checkouts under an iCloud-managed folder (`~/Documents`,
    `~/Desktop`). iCloud can evict files and stall `git` and image builds. Use a plain
    path like `~/kionga`.

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
Sign in with `admin` / `mlaiops-local`.

If port 8080 is already used, `make -C deploy local-up` selects a free port in 18080–18084
and prints the URL. To choose a port yourself without changing the container network:

```bash
GATEWAY_PORT=18080 make -C deploy local-up
export GATEWAY=http://localhost:18080
```

Bucket creation uses the `boto3` already included in the local MLflow image;
it does not pull a separate S3 client image. A registry error that says a
repository or tag does not exist fails immediately rather than consuming all
retry attempts. On macOS, if iCloud has evicted `.dockerignore` or `Dockerfile`,
download those files in Finder before a cold build; the startup preflight will
report the affected file.

### Verify it works

```bash
./deploy/scripts/demo-smoke.sh
```

This exercises the configured platform end to end — creates a project, runs a real
pipeline, deploys a model and gets a live prediction, invokes an agent, reads
features from Redis, browses storage, and scores fraud events. Use
`GATEWAY=http://localhost:18080 ./deploy/scripts/demo-smoke.sh` when the port was
overridden. The pass/skip count is dynamic; the command must finish with zero
failures. OpenFaaS is skipped until an external gateway is configured.

### Service URLs

| Service | URL | Credentials (local defaults) |
| --- | --- | --- |
| Landing page | <http://localhost:8080> | none |
| Console + API | <http://localhost:8080/console.html> | `admin` / `mlaiops-local` locally; OIDC when hosted |
| Jupyter workbench | <http://localhost:8080/workspace.html?tool=workbench> | Kionga session |
| Browser IDE | <http://localhost:8080/workspace.html?tool=ide> | Kionga session; start with `make -C deploy ide-up` |
| MLflow | <http://localhost:15000> | none |
| Prefect | <http://localhost:4200> | none |
| Langfuse | <http://localhost:3000> | `admin@local.dev` / `mlaiops-local-admin` |
| RustFS console | <http://localhost:9001> | `mlaiops` / `mlaiops-local-secret` |

See [Configuration reference](configuration.md) for every port and setting, and
[Connecting all services](../connecting-services.md) for the full connection map.

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

## Alternative: build and run the Go control plane only

For control-plane development without the full stack:

```bash
pip install -e "sdk-python[dev]" # the SDK and its test dependencies
make -C platform run            # runs the gateway on :8080 (file-backed store)
```

In this mode there is no execution engine, serving, or agent runtime — the gateway
uses a local JSON file (`MLAIOPS_DATA_PATH`, default `data/platform.json`) and
downstream integrations are simply not configured. Good for API and console work.

## Building the binaries

```bash
make -C platform build
```

Produces static binaries in `bin/`:

```
mlaiops-gateway  mlaiops-operator  mlaiops-integration-worker
mlaiops-trace-proxy  mlaiops-feature-gateway  mlaiops-storage-proxy
mlaiops-metrics-collector  mlaiops-serving-manager  mlaiops-cli
```

The platform's Go services build from `platform/go/Dockerfile` with a `SERVICE`
build arg; every other image builds from its own repository's `Dockerfile` (see
[Repositories](../overview/repositories.md)):

```bash
docker build --build-arg SERVICE=gateway -t mlaiops/gateway platform/go
docker build -t mlaiops/serving-manager serving
```

## Running the test suites

```bash
make -C platform verify           # Go/Python tests + vet/ruff, builds, JS check, banned-tech scan
make -C platform test-integration # Postgres outbox + pgvector round-trip
make -C deploy test-e2e-kind         # Kind-based end-to-end (optional scale path)
make -C deploy test-load        # k6 load test against the gateway
```

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
make -C docs docs-install       # pip install mkdocs-material
make -C docs docs-serve         # live preview at http://localhost:8000
make -C docs docs-build         # static build into site/ (strict)
```
