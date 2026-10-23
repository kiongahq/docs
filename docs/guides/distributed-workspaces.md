---
icon: material/source-branch
description: Provision a teammate's workspace and resource profile, connect a project to Git and sync it into a workspace, and deploy serverless functions you can compose into pipelines.
---

# Set up team workspaces, Git and functions

Use this guide to get a teammate from sign-in to a reproducible, event-driven
application. It covers four tasks:

- [Provision a teammate's workspace](#provision-a-teammates-workspace) with
  services and a resource profile.
- [Connect a project to Git](#connect-a-project-to-git).
- [Sync a project into a workspace](#sync-a-project-into-a-workspace).
- [Deploy a function](#deploy-a-function) and compose functions into a pipeline.

## Before you begin

| Task | Who can do it |
| --- | --- |
| Provision a teammate | `admin` or `operator` |
| Connect a project to Git | `admin`, `operator` or `engineer`, or a normal user with the `git` service and access to the project |
| Sync a project into a workspace | Anyone who can open a workspace and see the project |
| Deploy or invoke a function | `admin`, `operator` or `engineer`, or a normal user with the `functions` service and access to the project |

Functions also need an OpenFaaS gateway that an operator connects to Kionga
(see [Deploy a function](#deploy-a-function)).

## Provision a teammate's workspace

An administrator gives each person a role, the services they may use, the
projects they may see, and a resource profile that bounds their compute.

1. Open **Users & access** and click **＋ Provision user**.
2. Under **Identity**, enter the **Identity subject**. With single sign-on, it
   must match the identity provider's `sub` claim exactly; with local sign-in, it
   is the username. Choose a **Role**.
3. Under **Services and projects**, select only the services the person needs
   (for example `projects`, `pipelines`, `workbench`, `ide`) and enter any
   **Assigned project IDs**. People always see the projects they own.
4. Under **Resource allocation**, choose a **Resource profile**:

    | Profile | CPU cores | Memory | GPUs | Storage | Projects | Concurrent runs | Functions |
    | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
    | Starter | 2 | 4 GB | 0 | 25 GB | 2 | 1 | 3 |
    | Team | 4 | 8 GB | 0 | 100 GB | 5 | 3 | 10 |
    | Power | 8 | 16 GB | 0 | 250 GB | 10 | 6 | 25 |
    | GPU | 8 | 32 GB | 1 | 500 GB | 10 | 4 | 15 |

    Choose **Custom** only when no preset fits, and then set each limit. Memory
    in the grant is a whole number of GB.

5. Click **Save access**.

On Kubernetes, Kionga then creates a workspace for the person: a persistent
volume claim sized from the storage grant, a pod with only the JupyterLab and
IDE containers they are assigned, CPU and memory from the profile (and any GPU
on the JupyterLab container), an internal service and a generated workspace
credential. Suspending the person scales the workspace to zero. Revoking access
removes the workspace and its workloads.

On Compose, everyone shares one JupyterLab volume, which suits a laptop or a
single-user server. Per-user workspaces need Kubernetes.

The gateway enforces project, service, run, function and bucket limits on every
API request, whether the person uses the console or the API.

**Verify:** the person appears under **Users** with the role, services and
compute you set. On Kubernetes, their workspace exists:

```bash
kubectl get kiongaworkspaces -A
kubectl get deployment,pvc,service -l app.kubernetes.io/component=workspace -A
```

## Connect a project to Git

Kionga stores the repository URL, provider, default branch and sync metadata.
Credentials stay in the Git credential helper of each workspace. Kionga rejects URLs
that contain credentials.

=== "Console"

    1. Open **Projects** and select the project.
    2. Click **Connect Git repository** (or **Update repository** to change it).
    3. Enter the **Repository URL** (HTTPS or SSH) and the **Default branch**.
    4. Click **Connect repository**.

    You can also set the repository when you create the project.

=== "CLI"

    ```bash
    mlaiops project connect prj-123 https://github.com/acme/risk-app.git main
    ```

=== "SDK"

    ```python
    client.connect_repository("prj-123", "https://github.com/acme/risk-app.git",
                              default_branch="main")
    ```

**Verify:** the project's **Repository** field shows the URL and the branch.

## Sync a project into a workspace

`kionga project sync` clones a project's connected repository into your
workspace, or fast-forwards an existing clone.

1. Open a terminal in JupyterLab or the browser IDE. Inside a workspace,
   `kionga` calls Kionga as you, with no API key.
2. Sync into the folder that the console's **Open in Jupyter** and **Open in
   IDE** buttons open:

    ```bash
    KIONGA_WORKSPACE=/workspace/projects kionga project sync prj-123
    ```

    Without the variable, the clone goes to `/workspace/<namespace>`.

3. Optional: from a machine outside Kionga, set the gateway address and a
   personal API key with the `projects` scope first:

    ```bash
    export MLAIOPS_URL=https://kionga.example.com
    export MLAIOPS_TOKEN='<personal API key>'
    ```

An existing clone is updated with `git fetch`, a checkout of the default branch,
and `git pull --ff-only`. The command stops without changes when the folder's
`origin` points somewhere else, or when the folder has files but is not a Git
clone. Private-repository credentials come from your workspace Git credential
helper and never reach Kionga.

**Verify:** the command prints `Cloned ...` or `Updated ...` with the folder and
branch.

To start a new application in the same workspace instead, generate a starter:

```bash
kionga scaffold risk-app --template fullstack-ai --agent none
```

See [Scaffold a project](scaffolding.md).

## Deploy a function

A function is any OCI image that serves HTTP. Kionga deploys it to OpenFaaS
with the CPU and memory you set, checks it against your function quota, and
records its owner and project.

**Operator setup:** set `OPENFAAS_URL`, `OPENFAAS_USER` and `OPENFAAS_PASSWORD`
on the gateway. Kionga works with a Kubernetes OpenFaaS gateway or a `faasd`
gateway on a single server. Until `OPENFAAS_URL` is set, deploys return
`OPENFAAS_URL is not configured`.

1. Build and push your image, preferably pinned by digest.
2. Deploy it:

    === "Console"

        1. Open **Functions** and click **＋ Deploy function**.
        2. Choose the **Project**, a **Function name** (lowercase letters,
           digits and hyphens) and the **OCI image**.
        3. Set **CPU** and **Memory** as Kubernetes quantities, such as `500m`
           and `512Mi`, and optional **Environment** as a JSON object.
        4. Choose a **Trigger**:
            - **HTTP / webhook**: invoke synchronously.
            - **Asynchronous queue**: queue work and get an OpenFaaS call ID.
            - **Cron schedule**: a five-field cron expression, run by the
              OpenFaaS cron connector.
            - **Kafka topic**: every message on the topic, forwarded by the
              OpenFaaS Kafka connector.
        5. Click **Deploy function**.

    === "CLI"

        ```bash
        mlaiops function deploy prj-123 score-events ghcr.io/acme/score-events:1.4.0
        ```

    === "SDK"

        ```python
        client.deploy_function("prj-123", "score-events",
                               "ghcr.io/acme/score-events:1.4.0",
                               cpu="500m", memory="512Mi")
        ```

3. Invoke it:

    ```bash
    export MLAIOPS_FUNCTION_PAYLOAD='{"customer_id":"c-42"}'
    mlaiops function invoke score-events
    mlaiops function invoke-async score-events
    ```

Cron and Kafka triggers depend on OpenFaaS connectors that you install and
license separately. See the OpenFaaS documentation on
[triggers](https://docs.openfaas.com/reference/triggers/),
[asynchronous calls](https://docs.openfaas.com/reference/async/) and
[cron](https://docs.openfaas.com/reference/cron/).

**Verify:** the function card under **Functions** shows its image, resources and
trigger, and **Invoke** returns the function's response.

### Compose functions into a pipeline

A pipeline in functions mode runs deployed functions as the nodes of a DAG.
Ready nodes run in parallel, and each node receives its dependencies' output.

```yaml
apiVersion: kionga.dev/v1
kind: Pipeline
metadata: {name: event-score, project: prj-123, version: "4"}
spec:
  executionMode: functions
  nodes:
    - {id: extract, type: function, function: extract-events,
       retry: {max: 2}}
    - {id: score, type: function, function: score-events, dependsOn: [extract],
       retry: {max: 1}}
```

Save it from **Pipelines > ＋ Define flow** with **Execution** set to
**Functions · OpenFaaS**, or with `mlaiops pipeline apply`. Kionga rejects a
flow that references a function that is not deployed in the same project. See
[Define and run pipelines](pipelines.md).

## Next steps

- [Define and run pipelines](pipelines.md).
- [Manage users, groups and policies](access-control.md).
- Review the [production readiness checklist](../operations/production-operations.md)
  before you onboard a team.
