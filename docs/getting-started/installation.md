---
icon: material/download-outline
description: Install Kionga on Linux, macOS or Windows with Docker or Podman and confirm that it works.
---

# Install Kionga

In this tutorial you install the complete Kionga platform on your own machine,
sign in to the console, and run a check that exercises every bundled capability.
Kionga runs locally as one Compose stack that it builds from its component
repositories. Docker is the default engine; Podman is optional.

## Before you begin

| Requirement | Notes |
| --- | --- |
| Container engine and Compose provider | Docker Desktop on macOS or Windows with WSL 2, Docker Engine on Linux, or Podman with a Compose provider. Docker is the default. |
| At least 8 GB of memory for the container engine | Allocate this to the desktop VM, or make it available on the Linux host. |
| 25 to 35 GB of free disk space | The first build downloads and compiles several large images. Later starts need much less. |
| Bash, Git, Make, and Python 3 | Git clones the repositories, Make runs the commands, and the startup script uses Python 3 (standard library only). |
| curl | Optional. The startup script uses it to wait until the console is ready. |

For OS-specific prerequisites and Podman instructions, see
[Choose an operating system and container engine](../operations/local.md#choose-an-operating-system-and-container-engine).
On Windows, run the commands below in WSL 2, not PowerShell. The examples use
Docker by default; Podman users should keep `KIONGA_ENGINE=podman` set for
local Make targets.

## Step 1: Get the code

Create a workspace folder, clone the `deploy` repository into it, and let it
clone the other component repositories beside it:

```bash
mkdir ~/kionga && cd ~/kionga
git clone https://github.com/kiongahq/deploy.git
KIONGA_GIT_BASE=https://github.com/kiongahq/ make -C deploy workspace
```

`make -C deploy workspace` clones over SSH by default. `KIONGA_GIT_BASE`
switches it to HTTPS. Each repository prints `cloned`, or `present` when it is
already there. Every command in this documentation runs from this workspace
folder.

## Step 2: Start the stack

```bash
make -C deploy local-up
```

The command:

1. Checks that the selected engine and Compose are available, that the engine is
   running, and that every component repository is present.
2. Keeps each default port, or moves a busy one to a free port 10000 higher and
   prints the change (for example, `8080` becomes `18080`).
3. Downloads missing upstream images, a few at a time, and retries transient
   network failures.
4. Builds the images that are missing or whose sources changed, then starts every
   service.
5. Waits for the console and API to become healthy, then creates the Kafka topics.

The first run builds several images and takes the longest. Later runs reuse the
built images and start much faster. If a download fails even after the retries,
run the command again: the engine reuses the layers it already has.

When the stack is ready, the command prints:

```text
Kionga is ready.
  Console:  http://localhost:8080
  Login:    admin / mlaiops-local
```

The port in the console URL differs when the default port was busy. `make -C deploy local` is an alias for
`make -C deploy local-up`.

## Step 3: Sign in

Open <http://localhost:8080> for the landing page, or go straight to the console
at <http://localhost:8080/console>. Sign in with the local account `admin` and
password `mlaiops-local`, or with one of the single sign-on test accounts described in
[Single sign-on](../operations/single-sign-on.md#try-it-locally).

You see the console's **Overview** page.

## Step 4: Check the whole platform

```bash
./deploy/scripts/demo-smoke.sh
```

The check signs in with the local account (or uses `MLAIOPS_TOKEN` when you set
it), creates a project, runs a real training pipeline, deploys the trained model
and requests a live prediction, deploys and invokes an agent, reads online
features, browses storage, and scores real-time events. `make -C deploy smoke`
runs the same script.

The script ends with a `RESULT: <passed> passed, <failed> failed, <skipped> skipped`
line; the counts depend on what your stack has configured. The check succeeds when
`failed` is `0`. Serverless functions are skipped until you connect an OpenFaaS
gateway.

If the console uses a different port, pass it to the check:

```bash
GATEWAY=http://localhost:18080 ./deploy/scripts/demo-smoke.sh
```

## Service URLs

| Service | URL | Sign-in (local defaults) |
| --- | --- | --- |
| Landing page | <http://localhost:8080> | None |
| Console and API | <http://localhost:8080/console> | `admin` / `mlaiops-local`, or single sign-on |
| Jupyter workbench | <http://localhost:8080/workspace?tool=workbench> | Your console session |
| Browser IDE | <http://localhost:8080/workspace?tool=ide> | Your console session. Start it first with `make -C deploy ide-up`. |
| Dex (single sign-on) | <http://localhost:5556/dex> | Test directory password `kionga-sso-dev` |
| MLflow | <http://localhost:15000> | None |
| Prefect | <http://localhost:4200> | None |
| Langfuse | <http://localhost:3000> | `admin@local.dev` / `mlaiops-local-admin` |
| RustFS console | <http://localhost:9001> | `mlaiops` / `mlaiops-local-secret` |

[Service endpoints](../reference/service-endpoints.md) lists every service, and
[Services and ports](../reference/services.md) lists every port.

## Local credentials and network access {#local-credentials-and-network-access}

!!! warning "Development credentials"
    The local stack starts with the well-known credentials below so that it works
    without setup. Anyone who can reach these ports can use them. Every port binds
    to `127.0.0.1` by default, so only your machine can connect. Keep that
    default unless you change these credentials, and never put the local stack on
    a network you do not trust.

| Port (variable) | Service | Default credential |
| --- | --- | --- |
| `8080` (`GATEWAY_PORT`) | Console and API | `admin` / `mlaiops-local`; internal service token `kionga-local-service-token` |
| `5432` (`POSTGRES_PORT`) | PostgreSQL | `mlaiops` / `mlaiops-local` |
| `6379` (`REDIS_PORT`) | Redis | None |
| `9092` (`KAFKA_PORT`) | Kafka broker | None (plaintext listener) |
| `8082` (`KAFKA_REST_PORT`) | Kafka REST proxy | None |
| `9000` / `9001` (`OBJECTSTORE_PORT` / `OBJECTSTORE_CONSOLE_PORT`) | RustFS S3 API and console | `mlaiops` / `mlaiops-local-secret` |
| `15000` (`MLFLOW_PORT`) | MLflow | None |
| `4200` (`PREFECT_PORT`) | Prefect | None |
| `3000` (`LANGFUSE_PORT`) | Langfuse | `admin@local.dev` / `mlaiops-local-admin`; project keys `pk-lf-local-dev` / `sk-lf-local-dev` |
| `5556` (`DEX_PORT`) | Dex single sign-on | Test directory password `kionga-sso-dev` |
| `8083` (`FEATURE_GATEWAY_PORT`) | Feature gateway | Internal service token |
| `8084` (`STORAGE_PROXY_PORT`) | Storage proxy | Internal service token |
| `8085` (`SERVING_MANAGER_PORT`) | Serving manager | Internal service token |
| `8081` (`TRACE_PROXY_PORT`) | Trace proxy | None |
| `19000` (`AGENT_RUNTIME_PORT`) | Agent runtime | None |
| `8888` (`JUPYTER_PORT`), always `127.0.0.1` | Jupyter workbench | Token `mlaiops-local` |

To check that a data service is not reachable from your network, run this from
another machine on the same network, with your machine's address in place of
`192.168.1.20`:

```bash
nc -vz -w 3 192.168.1.20 5432
```

If startup moved PostgreSQL to another port (for example `15432`), use that port.
With the default binding the connection is refused or times out. A `succeeded`
or `open` result means the port is published on that interface; see
[Network exposure](../operations/local.md#network-exposure).

To open the stack to other machines on a trusted network, set
`KIONGA_BIND_ADDRESS`, as described in
[Network exposure](../operations/local.md#network-exposure).

To choose a port yourself, set its variable when you start the stack:

```bash
GATEWAY_PORT=18080 make -C deploy local-up
```

A port that you set explicitly is never moved. If it is busy, the startup stops and
names the variable to change. See [Changing ports](../operations/local.md#changing-ports).

## Stop and restart

```bash
make -C deploy local-down     # stop and remove the containers; data volumes stay
make -C deploy local-up       # start again
make -C deploy local-status   # every service, including finished one-shot jobs
make -C deploy local-logs     # the latest 100 log lines of each service
make -C deploy local-rebuild  # rebuild every image, then start
make -C deploy workspace-pull # fast-forward clean repository checkouts
```

Your projects, models, object storage, online features, pipeline history, and
notebooks live in named container volumes (`postgres-data`, `objectstore-data`,
`redis-data`, `prefect-data`, `jupyter-data`), so they survive restarts.

Services use `restart: unless-stopped`. Restart behavior after a host or VM
reboot also depends on the engine and its startup settings. Start the engine,
then run `make -C deploy local-up` to bring the stack back and check readiness.
A stack you stopped with `make -C deploy local-down` stays stopped until you
start it again.

## What you built

You now have the full Kionga platform on your machine: the console and API, the
pipeline engine, the model registry and serving, the agent runtime, the feature
store, object storage, event streaming, and the Jupyter workbench.

## Next steps

- Follow the [Quickstart](quickstart.md) to create a project, deploy a model, and
  chat with an agent.
- Run Kionga for a team: [Single server](../operations/public-vm.md) or
  [Kubernetes](../operations/managed-kubernetes.md).
- Operate the local stack: [Run locally](../operations/local.md).
