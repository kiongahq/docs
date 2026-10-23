---
icon: material/laptop
description: Start, check, update, back up and reset the local Kionga stack that runs on one machine with Docker Compose.
---

# Run Kionga locally

This guide shows you how to run the local Kionga stack on one machine with
Docker Compose and how to operate it day to day: start and stop it, check its
health, change ports, back up its data and reset it. The local stack is for
evaluation and development by one person; to serve other people, see
[Choose a deployment](index.md).

## Before you begin

- Install Docker Engine or Docker Desktop with Compose v2 and Make.
- Give Docker about 8 GB of memory and 25 to 35 GB of free disk for the first
  build. Cached starts need much less.
- Clone the component repositories into one workspace folder, as described in
  [Install Kionga](../getting-started/installation.md). Run every command on
  this page from that folder (the one that holds `deploy/`).

## Start the stack

1. Start every service:

    ```bash
    make -C deploy local-up
    ```

    The command checks that Docker is running and that every checkout is
    present, downloads missing images with at most two concurrent downloads and
    retries, rebuilds only the images whose sources changed, starts the
    services, waits for the gateway and creates the Kafka topics. It is safe to
    run again at any time; `make -C deploy local` is a shorter alias.

    When it finishes, it prints the console address and the local sign-in:

    ```text
    Kionga is ready.
      Console:  http://localhost:8080
      Login:    admin / mlaiops-local
    ```

2. Open the console address and sign in as `admin` with password
   `mlaiops-local`.

## Verify

Check service state and the gateway health endpoint:

```bash
make -C deploy local-status
export GATEWAY="${GATEWAY:-http://localhost:8080}"
curl -s "$GATEWAY/api/v1/health"   # {"service":"mlaiops-gateway","status":"ok",...}
curl -s "$GATEWAY/api/v1/ready"    # {"status":"ready"} once PostgreSQL answers
```

Every long-running service shows `Up` (and `healthy` where it has a health
check). One-shot jobs such as `objectstore-init` and `feature-materializer`
show `Exited (0)`. In the console, the **Platform** page shows the state of
every connected component.

Run the end-to-end smoke test against the running stack:

```bash
make -C deploy smoke
```

Set `GATEWAY` first if the console is not on port 8080. The number of passed
and skipped checks depends on which optional services you configured; the stack
is healthy when there are zero failures. OpenFaaS checks are skipped unless you
[connect OpenFaaS](#connect-openfaas-functions).

## Stop, restart and inspect

| Task | Command |
| --- | --- |
| Stop the stack (data volumes are kept) | `make -C deploy local-down` |
| Show running, unhealthy and completed services | `make -C deploy local-status` |
| Print the most recent logs of every service | `make -C deploy local-logs` |
| Follow one service's logs | `docker compose -f deploy/compose.yaml logs -f gateway` |
| Start the optional browser IDE | `make -C deploy ide-up` |
| Stop the browser IDE (its workspace is kept) | `make -C deploy ide-down` |
| Rebuild every image, then start | `make -C deploy local-rebuild` |

Long-running services use the Compose restart policy `unless-stopped`: after a
crash, a Docker restart or a reboot, they start again on their own. One-shot
jobs do not restart. To keep the stack down, stop it with
`make -C deploy local-down`.

Durable state lives in the named volumes `postgres-data`, `objectstore-data`,
`redis-data`, `prefect-data` and `jupyter-data`. Stopping or restarting the
stack keeps them.

### Rebuild one service

After you change the source of one service, rebuild and restart only that
service:

```bash
docker compose -f deploy/compose.yaml up -d --build gateway
```

The console is part of the gateway image, so console changes also need a
gateway rebuild.

### Re-run a one-shot job

```bash
docker compose -f deploy/compose.yaml up feature-materializer   # materialize features again
docker compose -f deploy/compose.yaml up objectstore-init       # create missing buckets
```

## Update

1. Pull the latest changes into every clean checkout:

    ```bash
    make -C deploy workspace-pull
    ```

2. Start the stack again. Only images whose sources changed are rebuilt:

    ```bash
    make -C deploy local-up
    ```

MLflow upgrades its database schema with `mlflow db upgrade` before it starts,
so an existing tracking database keeps working after an MLflow version change.

## Change ports {#changing-ports}

Every published port has a `*_PORT` variable. Set it in `deploy/.env` (or export
it) and run `make -C deploy local-up` again. For example, to move the console
to port 8090:

```bash
echo "GATEWAY_PORT=8090" >> deploy/.env
make -C deploy local-up
export GATEWAY=http://localhost:8090
```

When a default port is already in use (a native PostgreSQL on 5432, Redis on
6379, another app on 8080), `make -C deploy local-up` moves only that service to
the first free port from default + 10000 to default + 10004 and prints the
change, for example:

```text
Port 5432 is in use; postgres uses 15432 instead (POSTGRES_PORT=15432).
```

A port you set yourself is never moved: the command stops and names the
variable to change. A running stack keeps the ports it already holds. See
[Services and ports](../reference/services.md) for every port and variable.

## Network exposure

The local stack ships well-known development credentials (PostgreSQL, the object
store, Langfuse, the internal service token). Every port it publishes therefore
binds to `127.0.0.1` by default: only this machine can reach the console, the
API and the data services.

`KIONGA_BIND_ADDRESS` sets the host address for those ports. To reach the stack
from other machines on a trusted network, bind to all interfaces (or to one
interface's address) and start the stack again:

```bash
echo "KIONGA_BIND_ADDRESS=0.0.0.0" >> deploy/.env
make -C deploy local-up
```

!!! warning
    This exposes PostgreSQL, Redis, Kafka, the object store, MLflow, Langfuse
    and the other published services with their development credentials, not
    only the console. Use it only on a network you trust, and change the
    credentials first if anyone else shares that network.

Some ports stay on `127.0.0.1` regardless: Jupyter (`JUPYTER_PORT`), the log
exporter and the `log-export-es` and `log-export-os` test clusters. The browser
IDE publishes no port; open Jupyter and the IDE through the console.

Single sign-on redirects the browser to `KIONGA_GATEWAY_URL` (default
`http://localhost:<GATEWAY_PORT>`) and `DEX_ISSUER` (default
`http://localhost:5556/dex`). For sign-in from another machine, set both to an
address that machine can reach, for example
`KIONGA_GATEWAY_URL=http://192.168.1.20:8080` and
`DEX_ISSUER=http://192.168.1.20:5556/dex`, then run `make -C deploy local-up`.
The local `admin` account works without these changes.

MLflow accepts only the host names in `MLFLOW_SERVER_ALLOWED_HOSTS`
(`localhost` and `127.0.0.1` on any port, and `mlflow` inside the stack). To
open MLflow by another address, add it to that list in `deploy/compose.yaml`;
see [Troubleshooting](troubleshooting.md#mlflow-returns-403-invalid-host-header).

## Preview the console as another role

The local `admin` account takes its role from `MLAIOPS_LOCAL_ROLE` (default
`admin`). To see the console as a viewer:

```bash
MLAIOPS_LOCAL_ROLE=viewer docker compose -f deploy/compose.yaml up -d gateway
# ... then restore the default:
docker compose -f deploy/compose.yaml up -d gateway
```

Recreating the gateway ends existing local sessions; sign in again to get the
new role. An access profile for the `admin` subject under **Users & access**
takes precedence over this role.

## Connect OpenFaaS functions

Functions are optional. On a Linux host, install faasd (OpenFaaS's single-node
mode) on the host, not in Compose. These commands need `sudo`:

```bash
git clone https://github.com/openfaas/faasd --depth=1 && cd faasd
sudo ./hack/install.sh
sudo cat /var/lib/faasd/secrets/basic-auth-password
```

Add the faasd gateway to `deploy/.env` and start the stack again:

```text
OPENFAAS_URL=http://<host-private-ip>:8080
OPENFAAS_USER=admin
OPENFAAS_PASSWORD=<the printed password>
```

faasd listens on port 8080. If the console's port is then busy,
`make -C deploy local-up` moves it to another port and prints it. The console's
**Functions** view then lists project-owned functions, and
`POST /api/v1/functions` deploys OCI images with limits and trigger
annotations. Connectors and scale to zero stay in OpenFaaS's own configuration.

## Back up local data

Platform state lives in PostgreSQL (control plane, MLflow, Langfuse,
checkpoints) and the RustFS object store (artifacts). Notebooks and projects
live in `jupyter-data`. To back up the first two, stop the stack and archive
their volumes:

```bash
make -C deploy local-down
docker run --rm -v mlaiops_postgres-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/postgres-data.tgz -C /data .
docker run --rm -v mlaiops_objectstore-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/objectstore-data.tgz -C /data .
make -C deploy local-up
```

## Reset the stack

To delete all local state and start clean:

```bash
docker compose -f deploy/compose.yaml down -v   # -v deletes the named volumes
make -C deploy local-up
```

!!! warning
    `down -v` permanently deletes platform databases, artifacts, models,
    notebooks and IDE workspace data. Never add `-v` to a routine restart.

## Next steps

- [Troubleshooting](troubleshooting.md#local-stack) for startup, port and
  connectivity problems.
- [Single sign-on](single-sign-on.md) to add OAuth providers or your own LDAP
  directory.
- [Single server](public-vm.md) or [Deploy on Kubernetes](managed-kubernetes.md)
  when other people need access.
- To run the platform test suites or the local Kubernetes (kind) cluster, see
  the [engineering handbook](https://kiongahq.github.io/docs/engineering/).
