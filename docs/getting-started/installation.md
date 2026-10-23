---
icon: material/download-outline
description: Install the full Kionga platform on one machine with Docker Compose and confirm that it works.
---

# Install Kionga

In this tutorial you install the complete Kionga platform on your own machine,
sign in to the console, and run a check that exercises every bundled capability.
Kionga runs locally as one Docker Compose stack that it builds from its component
repositories.

## Before you begin

| Requirement | Notes |
| --- | --- |
| Docker Engine with Docker Compose v2 | Docker Desktop on macOS or Windows, Docker Engine on Linux. The Docker daemon must be running. |
| At least 8 GB of memory for Docker | On Docker Desktop, set it under **Settings → Resources**. |
| 25 to 35 GB of free disk space | The first build downloads and compiles several large images. Later starts need much less. |
| Git, Make, and Python 3 | Git clones the repositories, Make runs the commands, and the startup script uses Python 3 (standard library only). |
| curl | Optional. The startup script uses it to wait until the console is ready. |

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

1. Checks that Docker and Compose v2 are available, that the Docker daemon is
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
run the command again: Docker resumes from the layers it already has.

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
at <http://localhost:8080/console.html>. Sign in with the local account `admin` and
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
| Console and API | <http://localhost:8080/console.html> | `admin` / `mlaiops-local`, or single sign-on |
| Jupyter workbench | <http://localhost:8080/workspace.html?tool=workbench> | Your console session |
| Browser IDE | <http://localhost:8080/workspace.html?tool=ide> | Your console session. Start it first with `make -C deploy ide-up`. |
| Dex (single sign-on) | <http://localhost:5556/dex> | Test directory password `kionga-sso-dev` |
| MLflow | <http://localhost:15000> | None |
| Prefect | <http://localhost:4200> | None |
| Langfuse | <http://localhost:3000> | `admin@local.dev` / `mlaiops-local-admin` |
| RustFS console | <http://localhost:9001> | `mlaiops` / `mlaiops-local-secret` |

[Service endpoints](../reference/service-endpoints.md) lists every service, and
[Services and ports](../reference/services.md) lists every port.

## Change ports and network access

Every published port binds to `127.0.0.1`, so only your machine can reach the
stack. To open it to other machines on a trusted network, set
`KIONGA_BIND_ADDRESS`; see [Network exposure](../operations/local.md#network-exposure).

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
notebooks live in named Docker volumes (`postgres-data`, `objectstore-data`,
`redis-data`, `prefect-data`, `jupyter-data`), so they survive restarts.

Services restart automatically (`restart: unless-stopped`): after Docker or the
machine restarts, the stack comes back as it was. A stack you stopped with
`make -C deploy local-down` stays stopped.

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
